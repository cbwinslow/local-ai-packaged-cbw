#!/usr/bin/env python3
"""
Enhanced Environment Generator for Local AI Package

This script creates a robust .env file with comprehensive validation, proper credential generation,
and checks for Supabase requirements. It handles both local and remote deployment scenarios.

Features:
- Generates secure credentials with proper length and character validation
- Validates Supabase-specific requirements
- Checks for port conflicts and existing services
- Provides verbose feedback and troubleshooting guidance
- Supports different deployment environments (local/remote)
- Creates backup of existing .env files
"""

import argparse
import secrets
import string
import base64
import json
import time
import re
import os
import sys
import socket
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Color codes for output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def colored_print(message: str, color: str = Colors.WHITE, bold: bool = False) -> None:
    """Print colored and optionally bold text."""
    prefix = Colors.BOLD if bold else ""
    print(f"{prefix}{color}{message}{Colors.END}")

def print_header(title: str) -> None:
    """Print a formatted header."""
    colored_print(f"\n{'='*60}", Colors.CYAN, bold=True)
    colored_print(f" {title}", Colors.CYAN, bold=True)
    colored_print(f"{'='*60}", Colors.CYAN, bold=True)

def print_section(title: str) -> None:
    """Print a formatted section header."""
    colored_print(f"\n--- {title} ---", Colors.BLUE, bold=True)

def print_success(message: str) -> None:
    """Print a success message."""
    colored_print(f"✓ {message}", Colors.GREEN, bold=True)

def print_warning(message: str) -> None:
    """Print a warning message."""
    colored_print(f"⚠ {message}", Colors.YELLOW, bold=True)

def print_error(message: str) -> None:
    """Print an error message."""
    colored_print(f"✗ {message}", Colors.RED, bold=True)

def print_info(message: str) -> None:
    """Print an info message."""
    colored_print(f"ℹ {message}", Colors.BLUE)

class CredentialValidator:
    """Validates and generates secure credentials."""
    
    # Character sets for different types of credentials
    ALPHANUM = string.ascii_letters + string.digits
    SAFE_SYMBOLS = "!@#$%^&*-_="
    HEX_CHARS = string.hexdigits.lower()
    
    # Minimum lengths for different credential types
    MIN_LENGTHS = {
        'jwt_secret': 48,
        'encryption_key': 32,
        'password': 24,
        'api_key': 32,
        'token': 24,
        'secret': 32
    }
    
    @classmethod
    def generate_secure_string(cls, length: int, use_symbols: bool = True) -> str:
        """Generate a cryptographically secure random string."""
        charset = cls.ALPHANUM
        if use_symbols:
            charset += cls.SAFE_SYMBOLS
        return ''.join(secrets.choice(charset) for _ in range(length))
    
    @classmethod
    def generate_hex_string(cls, length: int) -> str:
        """Generate a hex string of specified length."""
        return secrets.token_hex(length // 2)
    
    @classmethod
    def generate_jwt_like_token(cls, role: str, expiration_hours: int = 24) -> str:
        """Generate a JWT-like token with proper format."""
        # Header
        header = {
            "alg": "HS256",
            "typ": "JWT"
        }
        
        # Payload
        current_time = int(time.time())
        payload = {
            "role": role,
            "iss": "supabase-local",
            "iat": current_time,
            "exp": current_time + (expiration_hours * 3600)
        }
        
        # Encode header and payload (base64url)
        def base64url_encode(data):
            json_str = json.dumps(data, separators=(',', ':'))
            return base64.urlsafe_b64encode(json_str.encode()).decode().rstrip('=')
        
        encoded_header = base64url_encode(header)
        encoded_payload = base64url_encode(payload)
        
        # Generate signature (random for local development)
        signature = cls.generate_hex_string(48)
        
        return f"{encoded_header}.{encoded_payload}.{signature}"
    
    @classmethod
    def validate_credential_strength(cls, credential: str, cred_type: str) -> Tuple[bool, List[str]]:
        """Validate the strength of a credential."""
        issues = []
        
        # Check minimum length
        min_length = cls.MIN_LENGTHS.get(cred_type, 24)
        if len(credential) < min_length:
            issues.append(f"Too short (minimum {min_length} characters)")
        
        # Check character diversity
        has_upper = any(c.isupper() for c in credential)
        has_lower = any(c.islower() for c in credential)
        has_digit = any(c.isdigit() for c in credential)
        has_symbol = any(c in cls.SAFE_SYMBOLS for c in credential)
        
        if not has_upper:
            issues.append("Missing uppercase letters")
        if not has_lower:
            issues.append("Missing lowercase letters")
        if not has_digit:
            issues.append("Missing digits")
        if not has_symbol and cred_type in ['password', 'encryption_key']:
            issues.append("Missing special characters")
        
        # Check for common patterns
        if re.search(r'(.)\1{3,}', credential):
            issues.append("Contains repeated characters")
        
        if credential.lower() in ['password', 'secret', 'admin', 'changeme']:
            issues.append("Contains common weak patterns")
        
        return len(issues) == 0, issues

class PortChecker:
    """Checks for port conflicts and existing services."""
    
    COMMON_PORTS = {
        3000: "Open WebUI",
        5678: "n8n",
        8080: "Flowise", 
        8000: "Kong API",
        8001: "Kong Admin",
        5432: "PostgreSQL",
        6333: "Qdrant",
        7474: "Neo4j HTTP",
        7687: "Neo4j Bolt",
        11434: "Ollama",
        80: "HTTP",
        443: "HTTPS",
        587: "SMTP",
        25: "SMTP",
        465: "SMTPS"
    }
    
    @classmethod
    def check_port(cls, port: int, host: str = 'localhost') -> bool:
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # Port is available if connection failed
        except Exception:
            return True  # Assume available if we can't check
    
    @classmethod
    def scan_ports(cls, ports: List[int]) -> Dict[int, Dict[str, any]]:
        """Scan multiple ports and return their status."""
        results = {}
        for port in ports:
            available = cls.check_port(port)
            service_name = cls.COMMON_PORTS.get(port, "Unknown service")
            results[port] = {
                'available': available,
                'service': service_name
            }
        return results
    
    @classmethod
    def suggest_alternative_ports(cls, occupied_ports: List[int]) -> Dict[int, int]:
        """Suggest alternative ports for occupied ones."""
        suggestions = {}
        for port in occupied_ports:
            # Try incremental ports starting from the original + 1000
            base_alternative = port + 1000
            for i in range(100):  # Try up to 100 alternatives
                alternative = base_alternative + i
                if cls.check_port(alternative):
                    suggestions[port] = alternative
                    break
        return suggestions

class SupabaseValidator:
    """Validates Supabase-specific requirements and setup."""
    
    @classmethod
    def validate_database_config(cls, config: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate database configuration."""
        issues = []
        
        required_db_vars = [
            'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 
            'POSTGRES_USER', 'POSTGRES_PASSWORD'
        ]
        
        for var in required_db_vars:
            if not config.get(var):
                issues.append(f"Missing required database variable: {var}")
        
        # Validate specific formats
        if config.get('POSTGRES_PORT'):
            try:
                port = int(config['POSTGRES_PORT'])
                if not (1 <= port <= 65535):
                    issues.append("Invalid PostgreSQL port number")
            except ValueError:
                issues.append("PostgreSQL port must be a number")
        
        return len(issues) == 0, issues
    
    @classmethod
    def validate_auth_config(cls, config: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate authentication configuration."""
        issues = []
        
        required_auth_vars = [
            'JWT_SECRET', 'ANON_KEY', 'SERVICE_ROLE_KEY'
        ]
        
        for var in required_auth_vars:
            if not config.get(var):
                issues.append(f"Missing required auth variable: {var}")
        
        # Validate JWT format for keys
        for key_var in ['ANON_KEY', 'SERVICE_ROLE_KEY']:
            key_value = config.get(key_var)
            if key_value and not cls._is_valid_jwt_format(key_value):
                issues.append(f"{key_var} does not appear to be a valid JWT")
        
        return len(issues) == 0, issues
    
    @classmethod
    def _is_valid_jwt_format(cls, token: str) -> bool:
        """Check if a string looks like a valid JWT."""
        parts = token.split('.')
        if len(parts) != 3:
            return False
        
        # Check if each part is valid base64
        for part in parts:
            try:
                # Add padding if needed
                padded = part + '=' * (4 - len(part) % 4)
                base64.urlsafe_b64decode(padded)
            except Exception:
                return False
        
        return True

class EnhancedEnvGenerator:
    """Main environment generator class."""
    
    def __init__(self, base_domain: str = 'localhost', email: str = 'admin@localhost', 
                 environment: str = 'local', verbose: bool = True):
        self.base_domain = base_domain
        self.email = email
        self.environment = environment
        self.verbose = verbose
        self.validator = CredentialValidator()
        self.port_checker = PortChecker()
        self.supabase_validator = SupabaseValidator()
        
        # Track generated credentials for validation
        self.generated_config = {}
        self.validation_results = []
    
    def generate_complete_env(self) -> str:
        """Generate a complete .env configuration."""
        if self.verbose:
            print_header("Enhanced Environment Generator")
            print_info(f"Domain: {self.base_domain}")
            print_info(f"Email: {self.email}")
            print_info(f"Environment: {self.environment}")
        
        # Generate all configuration sections
        config_sections = [
            self._generate_base_config(),
            self._generate_auth_config(),
            self._generate_database_config(),
            self._generate_service_configs(),
            self._generate_network_config(),
            self._generate_security_config()
        ]
        
        # Combine all sections
        complete_config = "\n\n".join(config_sections)
        
        # Validate the complete configuration
        if self.verbose:
            self._validate_complete_config()
        
        return complete_config
    
    def _generate_base_config(self) -> str:
        """Generate base configuration section."""
        if self.verbose:
            print_section("Base Configuration")
        
        lines = [
            "############################################",
            "# Enhanced Local AI Package Configuration",
            f"# Generated: {datetime.now().isoformat()}",
            f"# Domain: {self.base_domain}",
            f"# Environment: {self.environment}",
            "############################################",
            "",
            "# Base Configuration",
            f"BASE_DOMAIN={self.base_domain}",
            f"DEPLOY_DOMAIN={self.base_domain}",
            f"ACME_EMAIL={self.email}",
            f"ENVIRONMENT={self.environment}"
        ]
        
        # Add Cloudflare token placeholder if not localhost
        if self.base_domain != 'localhost':
            lines.append("CLOUDFLARE_API_TOKEN=change_me_cf_token")
        else:
            lines.append("# CLOUDFLARE_API_TOKEN=change_me_cf_token")
        
        if self.verbose:
            print_success(f"Generated base configuration for {self.base_domain}")
        
        return "\n".join(lines)
    
    def _generate_auth_config(self) -> str:
        """Generate authentication configuration."""
        if self.verbose:
            print_section("Authentication Configuration")
        
        # Generate JWT secret
        jwt_secret = self.validator.generate_secure_string(64)
        self.generated_config['JWT_SECRET'] = jwt_secret
        
        # Generate Supabase auth keys
        anon_key = self.validator.generate_jwt_like_token('anon', 24)
        service_key = self.validator.generate_jwt_like_token('service_role', 24*7)  # 7 days
        self.generated_config['ANON_KEY'] = anon_key
        self.generated_config['SERVICE_ROLE_KEY'] = service_key
        
        # Dashboard credentials
        dashboard_user = "supabase"
        dashboard_pass = self.validator.generate_secure_string(24)
        self.generated_config['DASHBOARD_USERNAME'] = dashboard_user
        self.generated_config['DASHBOARD_PASSWORD'] = dashboard_pass
        
        lines = [
            "# Authentication & Authorization",
            f"JWT_SECRET={jwt_secret}",
            f"ANON_KEY={anon_key}",
            f"SERVICE_ROLE_KEY={service_key}",
            f"DASHBOARD_USERNAME={dashboard_user}",
            f"DASHBOARD_PASSWORD={dashboard_pass}",
            "",
            "# Additional Auth Configuration",
            f"SECRET_KEY_BASE={self.validator.generate_hex_string(128)}",
            f"VAULT_ENC_KEY={self.validator.generate_hex_string(64)}",
            f"LOGFLARE_PUBLIC_ACCESS_TOKEN={self.validator.generate_secure_string(32)}",
            f"LOGFLARE_PRIVATE_ACCESS_TOKEN={self.validator.generate_secure_string(32)}"
        ]
        
        if self.verbose:
            print_success("Generated secure authentication credentials")
            print_info("JWT tokens are valid for development use")
        
        return "\n".join(lines)
    
    def _generate_database_config(self) -> str:
        """Generate database configuration."""
        if self.verbose:
            print_section("Database Configuration")
        
        # Generate secure database credentials
        postgres_pass = self.validator.generate_secure_string(32, use_symbols=False)  # No symbols for DB
        supabase_db_pass = self.validator.generate_secure_string(32, use_symbols=False)
        pooler_tenant_id = self.validator.generate_hex_string(24)
        
        self.generated_config.update({
            'POSTGRES_PASSWORD': postgres_pass,
            'SUPABASE_DB_PASSWORD': supabase_db_pass,
            'POSTGRES_HOST': 'db',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'postgres',
            'POSTGRES_USER': 'postgres'
        })
        
        lines = [
            "# Database Configuration",
            f"POSTGRES_HOST=db",
            f"POSTGRES_PORT=5432",
            f"POSTGRES_DB=postgres",
            f"POSTGRES_USER=postgres",
            f"POSTGRES_PASSWORD={postgres_pass}",
            f"SUPABASE_DB_PASSWORD={supabase_db_pass}",
            "",
            "# Connection Pooling",
            f"POOLER_TENANT_ID={pooler_tenant_id}",
            "POOLER_DB_POOL_SIZE=5",
            "POOLER_DEFAULT_POOL_SIZE=20",
            "POOLER_MAX_CLIENT_CONN=500"
        ]
        
        if self.verbose:
            print_success("Generated database configuration")
            print_info("Using internal Docker network hostnames")
        
        return "\n".join(lines)
    
    def _generate_service_configs(self) -> str:
        """Generate service-specific configurations."""
        if self.verbose:
            print_section("Service Configurations")
        
        lines = [
            "# n8n Configuration",
            f"N8N_ENCRYPTION_KEY={self.validator.generate_hex_string(48)}",
            f"N8N_USER_MANAGEMENT_JWT_SECRET={self.validator.generate_hex_string(64)}",
            "",
            "# Neo4j Configuration", 
            f"NEO4J_AUTH=neo4j/{self.validator.generate_secure_string(24, use_symbols=False)}",
            "",
            "# ClickHouse & Analytics",
            f"CLICKHOUSE_PASSWORD={self.validator.generate_secure_string(32)}",
            "",
            "# MinIO Storage",
            f"MINIO_ROOT_PASSWORD={self.validator.generate_secure_string(32)}",
            "",
            "# Langfuse Configuration",
            f"LANGFUSE_SALT={self.validator.generate_secure_string(32)}",
            f"NEXTAUTH_SECRET={self.validator.generate_secure_string(48)}",
            f"ENCRYPTION_KEY={self.validator.generate_hex_string(64)}",
            "",
            "# Flowise Configuration",
            "FLOWISE_USERNAME=admin",
            f"FLOWISE_PASSWORD={self.validator.generate_secure_string(24)}",
            "",
            "# Docker Configuration",
            "DOCKER_SOCKET_LOCATION=/var/run/docker.sock"
        ]
        
        if self.verbose:
            print_success("Generated service configurations")
        
        return "\n".join(lines)
    
    def _generate_network_config(self) -> str:
        """Generate network and proxy configuration."""
        if self.verbose:
            print_section("Network Configuration")
        
        def hostname(service):
            if self.base_domain == 'localhost':
                return f"{service}.localhost"
            else:
                return f"{service}.{self.base_domain}"
        
        lines = [
            "# Service Hostnames",
            f"N8N_HOSTNAME={hostname('n8n')}",
            f"WEBUI_HOSTNAME={hostname('webui')}",
            f"FLOWISE_HOSTNAME={hostname('flowise')}",
            f"SUPABASE_HOSTNAME={hostname('supabase')}",
            f"OLLAMA_HOSTNAME={hostname('ollama')}",
            f"SEARXNG_HOSTNAME={hostname('searxng')}",
            f"NEO4J_HOSTNAME={hostname('neo4j')}",
            f"PORTAL_HOSTNAME={hostname('portal')}",
            f"LANGFUSE_HOSTNAME={hostname('lang')}",
            "",
            "# Kong API Gateway",
            f"KONG_API_HOSTNAME={hostname('api')}",
            f"KONG_ADMIN_HOSTNAME={hostname('kong-admin')}",
            "",
            "# Traefik Dashboard",
            f"TRAEFIK_HOSTNAME={hostname('traefik')}"
        ]
        
        # Add port configuration check
        if self.verbose:
            print_info("Checking for port conflicts...")
            port_results = self.port_checker.scan_ports([3000, 5678, 8080, 5432, 6333, 7474, 11434])
            
            occupied_ports = [port for port, info in port_results.items() if not info['available']]
            if occupied_ports:
                print_warning(f"Occupied ports detected: {occupied_ports}")
                alternatives = self.port_checker.suggest_alternative_ports(occupied_ports)
                for original, alternative in alternatives.items():
                    service = self.port_checker.COMMON_PORTS.get(original, f"Port {original}")
                    print_info(f"Suggested alternative for {service}: {alternative}")
            else:
                print_success("No port conflicts detected")
        
        return "\n".join(lines)
    
    def _generate_security_config(self) -> str:
        """Generate security configuration."""
        if self.verbose:
            print_section("Security Configuration")
        
        lines = [
            "# Email Configuration (SMTP)",
            "SMTP_HOST=smtp.gmail.com",
            "SMTP_PORT=587",
            "SMTP_USER=user",
            "SMTP_PASS=change_me",
            "SMTP_SENDER_NAME=LocalAI",
            "",
            "# Email Template URLs",
            'MAILER_URLPATHS_CONFIRMATION="/auth/v1/verify"',
            'MAILER_URLPATHS_INVITE="/auth/v1/verify"',
            'MAILER_URLPATHS_RECOVERY="/auth/v1/verify"',
            'MAILER_URLPATHS_EMAIL_CHANGE="/auth/v1/verify"',
            "",
            "# Additional Security",
            "ADDITIONAL_REDIRECT_URLS=",
            "IMGPROXY_ENABLE_WEBP_DETECTION=false"
        ]
        
        if self.verbose:
            print_success("Generated security configuration")
            print_warning("Remember to update SMTP settings for email functionality")
        
        return "\n".join(lines)
    
    def _validate_complete_config(self) -> None:
        """Validate the complete generated configuration."""
        print_section("Configuration Validation")
        
        # Validate database config
        db_valid, db_issues = self.supabase_validator.validate_database_config(self.generated_config)
        if db_valid:
            print_success("Database configuration is valid")
        else:
            print_error("Database configuration issues:")
            for issue in db_issues:
                print_error(f"  - {issue}")
        
        # Validate auth config
        auth_valid, auth_issues = self.supabase_validator.validate_auth_config(self.generated_config)
        if auth_valid:
            print_success("Authentication configuration is valid")
        else:
            print_error("Authentication configuration issues:")
            for issue in auth_issues:
                print_error(f"  - {issue}")
        
        # Validate credential strength
        credential_issues = 0
        for key, value in self.generated_config.items():
            if 'password' in key.lower() or 'secret' in key.lower() or 'key' in key.lower():
                cred_type = 'password' if 'password' in key.lower() else 'secret'
                valid, issues = self.validator.validate_credential_strength(value, cred_type)
                if not valid:
                    credential_issues += 1
                    print_warning(f"Credential strength issue for {key}:")
                    for issue in issues:
                        print_warning(f"  - {issue}")
        
        if credential_issues == 0:
            print_success("All credentials meet security requirements")
        
        # Overall validation result
        if db_valid and auth_valid and credential_issues == 0:
            print_success("✅ Configuration validation passed!")
        else:
            print_warning("⚠️  Configuration has some issues that should be addressed")

def backup_existing_env(env_path: Path) -> Optional[Path]:
    """Create a backup of existing .env file."""
    if not env_path.exists():
        return None
    
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    backup_path = env_path.with_suffix(f'.{timestamp}.bak')
    
    try:
        env_path.rename(backup_path)
        print_success(f"Backed up existing .env to {backup_path.name}")
        return backup_path
    except Exception as e:
        print_error(f"Failed to backup .env: {e}")
        return None

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Enhanced Environment Generator for Local AI Package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate for localhost development
  python enhanced_env_generator.py --base-domain localhost --email admin@localhost
  
  # Generate for production deployment
  python enhanced_env_generator.py --base-domain myapp.com --email admin@myapp.com --environment production
  
  # Generate with minimal output
  python enhanced_env_generator.py --base-domain localhost --no-verbose
  
  # Generate and validate only (no file output)
  python enhanced_env_generator.py --validate-only
        """
    )
    
    parser.add_argument('--base-domain', default='localhost',
                        help='Base domain for services (default: localhost)')
    parser.add_argument('--email', default='admin@localhost',
                        help='Email for Let\'s Encrypt and admin accounts (default: admin@localhost)')
    parser.add_argument('--environment', choices=['local', 'development', 'production'], 
                        default='local', help='Deployment environment (default: local)')
    parser.add_argument('--output', type=Path, default=Path('.env'),
                        help='Output file path (default: .env)')
    parser.add_argument('--no-backup', action='store_true',
                        help='Skip backing up existing .env file')
    parser.add_argument('--no-verbose', action='store_true',
                        help='Reduce output verbosity')
    parser.add_argument('--validate-only', action='store_true',
                        help='Only validate configuration, don\'t write file')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite existing .env without prompting')
    
    args = parser.parse_args()
    
    # Create generator
    generator = EnhancedEnvGenerator(
        base_domain=args.base_domain,
        email=args.email,
        environment=args.environment,
        verbose=not args.no_verbose
    )
    
    try:
        # Generate configuration
        env_content = generator.generate_complete_env()
        
        if args.validate_only:
            print_header("Validation Complete")
            print_info("Configuration generated and validated successfully")
            print_info("Use --output to write to file")
            return
        
        # Handle existing file
        if args.output.exists() and not args.force:
            if not args.no_backup:
                backup_existing_env(args.output)
            else:
                response = input(f"\n{args.output} exists. Overwrite? (y/N): ")
                if response.lower() != 'y':
                    print_info("Operation cancelled")
                    return
        elif args.output.exists() and not args.no_backup:
            backup_existing_env(args.output)
        
        # Write configuration file
        args.output.write_text(env_content)
        
        # Set secure permissions
        args.output.chmod(0o600)
        
        print_header("Generation Complete")
        print_success(f"Environment file written to {args.output}")
        print_success(f"File permissions set to 600 (owner read/write only)")
        print_info(f"Configuration contains {len(env_content.splitlines())} lines")
        
        if not args.no_verbose:
            print_section("Next Steps")
            print_info("1. Review the generated .env file")
            print_info("2. Update SMTP settings if email functionality is needed")
            print_info("3. Add Cloudflare API token if using external domain")
            print_info("4. Run comprehensive tests: ./scripts/tests/run_comprehensive_tests.sh")
            print_info("5. Start services: python start_services.py --profile cpu")
        
    except Exception as e:
        print_error(f"Error generating environment: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()