#!/usr/bin/env python3
"""
Comprehensive Security and Bare Metal Deployment Validation

This script provides comprehensive security validation and bare metal deployment testing:
- Security baseline enforcement and vulnerability scanning
- Bare metal installation compatibility testing
- Credential validation and rotation management
- Network security configuration validation
- SSL/TLS certificate management testing
- Database security and access control validation
- Container security and image vulnerability scanning
"""

import os
import sys
import ssl
import socket
import subprocess
import hashlib
import secrets
import json
import yaml
import time
import asyncio
import aiohttp
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import urllib.parse
import docker
import psycopg2
import requests
from datetime import datetime, timedelta
import re

class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TestCategory(Enum):
    SECURITY = "security"
    BARE_METAL = "bare_metal"
    NETWORK = "network"
    CREDENTIALS = "credentials"
    CERTIFICATES = "certificates"
    DATABASE = "database"
    CONTAINERS = "containers"

@dataclass
class SecurityFinding:
    category: TestCategory
    severity: SecurityLevel
    title: str
    description: str
    remediation: str
    affected_component: str = ""
    technical_details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BareMetalCompatibility:
    component: str
    compatible: bool
    version_detected: Optional[str] = None
    installation_method: str = ""
    configuration_path: Optional[str] = None
    service_status: str = ""
    notes: str = ""

class SecurityValidator:
    """Comprehensive security validation for the Local AI package."""
    
    def __init__(self, repo_root: str, verbose: bool = True):
        self.repo_root = Path(repo_root)
        self.verbose = verbose
        self.findings: List[SecurityFinding] = []
        self.bare_metal_results: List[BareMetalCompatibility] = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO if verbose else logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            self.logger.warning(f"Docker client initialization failed: {e}")
            self.docker_client = None
    
    def validate_environment_security(self) -> List[SecurityFinding]:
        """Validate environment file security."""
        self.logger.info("🔒 Validating environment security...")
        
        findings = []
        env_file = self.repo_root / ".env"
        
        if not env_file.exists():
            findings.append(SecurityFinding(
                category=TestCategory.SECURITY,
                severity=SecurityLevel.HIGH,
                title="Missing .env file",
                description="No .env file found in repository root",
                remediation="Create .env file with proper credentials using enhanced_env_generator.py"
            ))
            return findings
        
        # Check file permissions
        file_stat = env_file.stat()
        file_mode = oct(file_stat.st_mode)[-3:]
        
        if file_mode != '600':
            findings.append(SecurityFinding(
                category=TestCategory.SECURITY,
                severity=SecurityLevel.MEDIUM,
                title="Insecure .env file permissions",
                description=f"File permissions are {file_mode}, should be 600",
                remediation="Run: chmod 600 .env",
                technical_details={'current_permissions': file_mode}
            ))
        
        # Check if .env is in git
        try:
            git_result = subprocess.run(
                ['git', 'ls-files', '--error-unmatch', '.env'],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            if git_result.returncode == 0:
                findings.append(SecurityFinding(
                    category=TestCategory.SECURITY,
                    severity=SecurityLevel.CRITICAL,
                    title=".env file tracked by git",
                    description="Environment file containing secrets is tracked by git",
                    remediation="Run: git rm --cached .env && git commit -m 'Remove .env from tracking'"
                ))
        except Exception:
            pass
        
        # Validate credential strength
        credential_findings = self._validate_credential_strength(env_file)
        findings.extend(credential_findings)
        
        # Check for exposed secrets
        secret_findings = self._check_exposed_secrets(env_file)
        findings.extend(secret_findings)
        
        return findings
    
    def _validate_credential_strength(self, env_file: Path) -> List[SecurityFinding]:
        """Validate strength of credentials in .env file."""
        findings = []
        
        try:
            env_content = env_file.read_text()
            
            # Define credential patterns and requirements
            credential_patterns = {
                'POSTGRES_PASSWORD': {'min_length': 16, 'require_special': True},
                'JWT_SECRET': {'min_length': 32, 'require_special': False},
                'ANON_KEY': {'min_length': 100, 'require_special': False},
                'SERVICE_ROLE_KEY': {'min_length': 100, 'require_special': False},
                'N8N_ENCRYPTION_KEY': {'min_length': 24, 'require_special': False},
                'MINIO_ROOT_PASSWORD': {'min_length': 16, 'require_special': True},
                'CLICKHOUSE_PASSWORD': {'min_length': 16, 'require_special': True}
            }
            
            for var_name, requirements in credential_patterns.items():
                pattern = f'{var_name}=(.+)'
                match = re.search(pattern, env_content)
                
                if not match:
                    findings.append(SecurityFinding(
                        category=TestCategory.CREDENTIALS,
                        severity=SecurityLevel.HIGH,
                        title=f"Missing credential: {var_name}",
                        description=f"Required credential {var_name} not found in .env",
                        remediation="Regenerate .env file with all required credentials"
                    ))
                    continue
                
                credential_value = match.group(1).strip('"\'')
                
                # Check length
                if len(credential_value) < requirements['min_length']:
                    findings.append(SecurityFinding(
                        category=TestCategory.CREDENTIALS,
                        severity=SecurityLevel.MEDIUM,
                        title=f"Weak credential: {var_name}",
                        description=f"Credential too short ({len(credential_value)} chars, minimum {requirements['min_length']})",
                        remediation="Regenerate credential with sufficient length",
                        technical_details={'actual_length': len(credential_value), 'required_length': requirements['min_length']}
                    ))
                
                # Check for special characters if required
                if requirements['require_special'] and not re.search(r'[!@#$%^&*()_+=\-\[\]{};:,.<>?]', credential_value):
                    findings.append(SecurityFinding(
                        category=TestCategory.CREDENTIALS,
                        severity=SecurityLevel.LOW,
                        title=f"Credential lacks complexity: {var_name}",
                        description="Credential should include special characters for better security",
                        remediation="Regenerate credential with special characters"
                    ))
                
                # Check for common weak patterns
                weak_patterns = ['password', 'secret', 'admin', 'changeme', '123456']
                if any(pattern in credential_value.lower() for pattern in weak_patterns):
                    findings.append(SecurityFinding(
                        category=TestCategory.CREDENTIALS,
                        severity=SecurityLevel.HIGH,
                        title=f"Weak credential pattern: {var_name}",
                        description="Credential contains common weak patterns",
                        remediation="Generate a completely random credential"
                    ))
        
        except Exception as e:
            findings.append(SecurityFinding(
                category=TestCategory.CREDENTIALS,
                severity=SecurityLevel.MEDIUM,
                title="Could not validate credentials",
                description=f"Error reading .env file: {e}",
                remediation="Check .env file format and permissions"
            ))
        
        return findings
    
    def _check_exposed_secrets(self, env_file: Path) -> List[SecurityFinding]:
        """Check for potentially exposed secrets."""
        findings = []
        
        try:
            env_content = env_file.read_text()
            
            # Check for example/placeholder values
            placeholder_patterns = [
                'change_me', 'changeme', 'your_password', 'your_secret',
                'example', 'test', 'demo', 'admin', 'password123'
            ]
            
            for pattern in placeholder_patterns:
                if pattern in env_content.lower():
                    findings.append(SecurityFinding(
                        category=TestCategory.CREDENTIALS,
                        severity=SecurityLevel.HIGH,
                        title="Placeholder credentials detected",
                        description=f"Found placeholder pattern: {pattern}",
                        remediation="Replace all placeholder values with secure random credentials"
                    ))
            
            # Check for hardcoded production values
            production_indicators = [
                'prod', 'production', 'live', 'api.supabase.co'
            ]
            
            for indicator in production_indicators:
                if indicator in env_content.lower():
                    findings.append(SecurityFinding(
                        category=TestCategory.SECURITY,
                        severity=SecurityLevel.MEDIUM,
                        title="Potential production configuration",
                        description=f"Found production indicator: {indicator}",
                        remediation="Ensure production credentials are properly secured"
                    ))
        
        except Exception as e:
            self.logger.warning(f"Could not check for exposed secrets: {e}")
        
        return findings
    
    def validate_network_security(self) -> List[SecurityFinding]:
        """Validate network security configuration."""
        self.logger.info("🌐 Validating network security...")
        
        findings = []
        
        # Check for open ports
        findings.extend(self._check_open_ports())
        
        # Check SSL/TLS configuration
        findings.extend(self._check_ssl_configuration())
        
        # Check firewall status
        findings.extend(self._check_firewall_status())
        
        return findings
    
    def _check_open_ports(self) -> List[SecurityFinding]:
        """Check for unnecessarily open ports."""
        findings = []
        
        # Define expected ports for different deployment types
        expected_ports = {
            'development': [3000, 5678, 8000, 8001, 5432, 6333, 7474, 11434],
            'production': [80, 443]
        }
        
        deployment_type = os.getenv('ENVIRONMENT', 'development')
        allowed_ports = expected_ports.get(deployment_type, expected_ports['development'])
        
        # Scan for open ports
        open_ports = []
        for port in range(80, 9000):  # Common port range
            if self._is_port_open('localhost', port):
                open_ports.append(port)
        
        # Check for unexpected open ports
        unexpected_ports = [port for port in open_ports if port not in allowed_ports]
        
        if unexpected_ports:
            findings.append(SecurityFinding(
                category=TestCategory.NETWORK,
                severity=SecurityLevel.MEDIUM,
                title="Unexpected open ports detected",
                description=f"Found open ports not in expected list: {unexpected_ports}",
                remediation="Review and close unnecessary ports or update firewall rules",
                technical_details={'open_ports': open_ports, 'unexpected': unexpected_ports}
            ))
        
        return findings
    
    def _is_port_open(self, host: str, port: int) -> bool:
        """Check if a port is open."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception:
            return False
    
    def _check_ssl_configuration(self) -> List[SecurityFinding]:
        """Check SSL/TLS configuration."""
        findings = []
        
        # Check if SSL is properly configured for production
        base_domain = os.getenv('BASE_DOMAIN', 'localhost')
        
        if base_domain != 'localhost':
            # Check for ACME email configuration
            acme_email = os.getenv('ACME_EMAIL', '')
            if not acme_email or 'change_me' in acme_email:
                findings.append(SecurityFinding(
                    category=TestCategory.CERTIFICATES,
                    severity=SecurityLevel.HIGH,
                    title="Missing ACME email for SSL certificates",
                    description="ACME_EMAIL not configured for Let's Encrypt",
                    remediation="Set ACME_EMAIL to a valid email address"
                ))
            
            # Check Cloudflare token if using Cloudflare
            cf_token = os.getenv('CLOUDFLARE_API_TOKEN', '')
            if 'change_me' in cf_token:
                findings.append(SecurityFinding(
                    category=TestCategory.CERTIFICATES,
                    severity=SecurityLevel.MEDIUM,
                    title="Placeholder Cloudflare token",
                    description="Cloudflare API token appears to be a placeholder",
                    remediation="Configure valid Cloudflare API token for DNS challenges"
                ))
        
        return findings
    
    def _check_firewall_status(self) -> List[SecurityFinding]:
        """Check firewall configuration."""
        findings = []
        
        try:
            # Check if ufw is installed and active
            ufw_result = subprocess.run(['ufw', 'status'], capture_output=True, text=True)
            
            if ufw_result.returncode == 0:
                if 'Status: active' not in ufw_result.stdout:
                    findings.append(SecurityFinding(
                        category=TestCategory.NETWORK,
                        severity=SecurityLevel.MEDIUM,
                        title="Firewall not active",
                        description="UFW firewall is installed but not active",
                        remediation="Enable firewall with: sudo ufw enable"
                    ))
            else:
                # Check for other firewalls (iptables, firewalld)
                iptables_result = subprocess.run(['iptables', '-L'], capture_output=True, text=True)
                
                if iptables_result.returncode == 0:
                    # Basic check for any rules
                    if 'Chain INPUT (policy ACCEPT)' in iptables_result.stdout:
                        findings.append(SecurityFinding(
                            category=TestCategory.NETWORK,
                            severity=SecurityLevel.LOW,
                            title="Default iptables policy is ACCEPT",
                            description="Iptables INPUT chain has default ACCEPT policy",
                            remediation="Consider implementing stricter firewall rules"
                        ))
        
        except Exception as e:
            self.logger.debug(f"Could not check firewall status: {e}")
        
        return findings
    
    def validate_database_security(self) -> List[SecurityFinding]:
        """Validate database security configuration."""
        self.logger.info("🗄️  Validating database security...")
        
        findings = []
        
        # Check PostgreSQL configuration
        findings.extend(self._check_postgresql_security())
        
        return findings
    
    def _check_postgresql_security(self) -> List[SecurityFinding]:
        """Check PostgreSQL security configuration."""
        findings = []
        
        postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        postgres_port = int(os.getenv('POSTGRES_PORT', '5432'))
        postgres_user = os.getenv('POSTGRES_USER', 'postgres')
        postgres_password = os.getenv('POSTGRES_PASSWORD', '')
        postgres_db = os.getenv('POSTGRES_DB', 'postgres')
        
        if not postgres_password:
            findings.append(SecurityFinding(
                category=TestCategory.DATABASE,
                severity=SecurityLevel.CRITICAL,
                title="Missing PostgreSQL password",
                description="No password configured for PostgreSQL connection",
                remediation="Set POSTGRES_PASSWORD in .env file"
            ))
            return findings
        
        try:
            # Test connection
            conn = psycopg2.connect(
                host=postgres_host,
                port=postgres_port,
                database=postgres_db,
                user=postgres_user,
                password=postgres_password,
                connect_timeout=10
            )
            
            cursor = conn.cursor()
            
            # Check for default passwords
            cursor.execute("SELECT usename FROM pg_user WHERE usename = 'postgres';")
            if cursor.fetchone():
                # Try connecting with common default passwords
                default_passwords = ['', 'postgres', 'password', 'admin']
                for default_pwd in default_passwords:
                    if default_pwd == postgres_password:
                        findings.append(SecurityFinding(
                            category=TestCategory.DATABASE,
                            severity=SecurityLevel.HIGH,
                            title="Default PostgreSQL password",
                            description=f"PostgreSQL is using default password: {default_pwd}",
                            remediation="Change to a strong, unique password"
                        ))
            
            # Check for unnecessary privileges
            cursor.execute("""
                SELECT usename, usesuper, usecreatedb, usecanlogin 
                FROM pg_user 
                WHERE usename != 'postgres';
            """)
            
            for user_info in cursor.fetchall():
                usename, usesuper, usecreatedb, usecanlogin = user_info
                if usesuper:
                    findings.append(SecurityFinding(
                        category=TestCategory.DATABASE,
                        severity=SecurityLevel.MEDIUM,
                        title=f"User {usename} has superuser privileges",
                        description="Non-postgres user has superuser privileges",
                        remediation="Review and minimize user privileges"
                    ))
            
            # Check for public schema permissions
            cursor.execute("""
                SELECT grantee, privilege_type 
                FROM information_schema.schema_privileges 
                WHERE schema_name = 'public' AND grantee = 'PUBLIC';
            """)
            
            public_perms = cursor.fetchall()
            if public_perms:
                findings.append(SecurityFinding(
                    category=TestCategory.DATABASE,
                    severity=SecurityLevel.LOW,
                    title="Public schema has PUBLIC permissions",
                    description="Public schema may be accessible to all users",
                    remediation="Review and restrict public schema permissions"
                ))
            
            conn.close()
        
        except psycopg2.Error as e:
            if "authentication failed" in str(e):
                findings.append(SecurityFinding(
                    category=TestCategory.DATABASE,
                    severity=SecurityLevel.HIGH,
                    title="PostgreSQL authentication failed",
                    description="Could not connect to PostgreSQL with provided credentials",
                    remediation="Verify POSTGRES_PASSWORD and connection details"
                ))
            else:
                self.logger.warning(f"Could not connect to PostgreSQL: {e}")
        
        except Exception as e:
            self.logger.warning(f"Error checking PostgreSQL security: {e}")
        
        return findings
    
    def validate_container_security(self) -> List[SecurityFinding]:
        """Validate container security configuration."""
        self.logger.info("🐳 Validating container security...")
        
        findings = []
        
        if not self.docker_client:
            findings.append(SecurityFinding(
                category=TestCategory.CONTAINERS,
                severity=SecurityLevel.MEDIUM,
                title="Cannot access Docker daemon",
                description="Docker client not available for security validation",
                remediation="Ensure Docker is running and accessible"
            ))
            return findings
        
        # Check running containers
        findings.extend(self._check_running_containers())
        
        # Check image vulnerabilities
        findings.extend(self._check_image_vulnerabilities())
        
        return findings
    
    def _check_running_containers(self) -> List[SecurityFinding]:
        """Check security of running containers."""
        findings = []
        
        try:
            containers = self.docker_client.containers.list()
            
            for container in containers:
                # Check if container is running as root
                if container.attrs.get('Config', {}).get('User') == '':
                    findings.append(SecurityFinding(
                        category=TestCategory.CONTAINERS,
                        severity=SecurityLevel.MEDIUM,
                        title=f"Container {container.name} running as root",
                        description="Container is running with root privileges",
                        remediation="Configure container to run with non-root user",
                        affected_component=container.name
                    ))
                
                # Check for privileged containers
                if container.attrs.get('HostConfig', {}).get('Privileged', False):
                    findings.append(SecurityFinding(
                        category=TestCategory.CONTAINERS,
                        severity=SecurityLevel.HIGH,
                        title=f"Privileged container: {container.name}",
                        description="Container is running in privileged mode",
                        remediation="Remove --privileged flag unless absolutely necessary",
                        affected_component=container.name
                    ))
                
                # Check for excessive capabilities
                capabilities = container.attrs.get('HostConfig', {}).get('CapAdd', [])
                dangerous_caps = ['SYS_ADMIN', 'SYS_PTRACE', 'NET_ADMIN', 'SYS_MODULE']
                
                for cap in capabilities:
                    if cap in dangerous_caps:
                        findings.append(SecurityFinding(
                            category=TestCategory.CONTAINERS,
                            severity=SecurityLevel.MEDIUM,
                            title=f"Dangerous capability in {container.name}",
                            description=f"Container has dangerous capability: {cap}",
                            remediation="Review and minimize container capabilities",
                            affected_component=container.name
                        ))
        
        except Exception as e:
            self.logger.warning(f"Error checking running containers: {e}")
        
        return findings
    
    def _check_image_vulnerabilities(self) -> List[SecurityFinding]:
        """Check for known vulnerabilities in container images."""
        findings = []
        
        # This is a simplified vulnerability check
        # In production, you'd integrate with tools like Trivy, Clair, or Snyk
        
        try:
            images = self.docker_client.images.list()
            
            for image in images:
                # Check for latest tag usage
                for tag in image.tags:
                    if tag.endswith(':latest'):
                        findings.append(SecurityFinding(
                            category=TestCategory.CONTAINERS,
                            severity=SecurityLevel.LOW,
                            title=f"Image using 'latest' tag: {tag}",
                            description="Using 'latest' tag can lead to unpredictable updates",
                            remediation="Pin images to specific versions",
                            affected_component=tag
                        ))
                
                # Check image age (simplified check)
                created = image.attrs.get('Created', '')
                if created:
                    try:
                        created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        age_days = (datetime.now(created_date.tzinfo) - created_date).days
                        
                        if age_days > 365:  # More than a year old
                            findings.append(SecurityFinding(
                                category=TestCategory.CONTAINERS,
                                severity=SecurityLevel.LOW,
                                title=f"Old image detected",
                                description=f"Image is {age_days} days old, may contain vulnerabilities",
                                remediation="Update to newer image version",
                                affected_component=str(image.tags)
                            ))
                    except Exception:
                        pass
        
        except Exception as e:
            self.logger.warning(f"Error checking image vulnerabilities: {e}")
        
        return findings
    
    def validate_bare_metal_compatibility(self) -> List[BareMetalCompatibility]:
        """Validate bare metal installation compatibility."""
        self.logger.info("🖥️  Validating bare metal compatibility...")
        
        results = []
        
        # Check system components
        results.extend(self._check_system_packages())
        results.extend(self._check_system_services())
        results.extend(self._check_system_configuration())
        
        return results
    
    def _check_system_packages(self) -> List[BareMetalCompatibility]:
        """Check for installed system packages."""
        results = []
        
        required_packages = {
            'docker': {'commands': ['docker', 'docker.io'], 'service': 'docker'},
            'docker-compose': {'commands': ['docker-compose', 'docker compose'], 'service': None},
            'python3': {'commands': ['python3'], 'service': None},
            'git': {'commands': ['git'], 'service': None},
            'curl': {'commands': ['curl'], 'service': None},
            'postgresql': {'commands': ['psql', 'pg_config'], 'service': 'postgresql'},
            'nginx': {'commands': ['nginx'], 'service': 'nginx'},
            'redis': {'commands': ['redis-server', 'redis-cli'], 'service': 'redis'}
        }
        
        for package_name, config in required_packages.items():
            compatibility = self._check_package_compatibility(package_name, config)
            results.append(compatibility)
        
        return results
    
    def _check_package_compatibility(self, package_name: str, config: Dict[str, Any]) -> BareMetalCompatibility:
        """Check compatibility of a specific package."""
        commands = config['commands']
        service_name = config.get('service')
        
        # Check if any of the commands exist
        version_detected = None
        installation_method = ""
        compatible = False
        
        for command in commands:
            try:
                # Check if command exists
                which_result = subprocess.run(['which', command], capture_output=True, text=True)
                if which_result.returncode == 0:
                    compatible = True
                    installation_path = which_result.stdout.strip()
                    
                    # Try to get version
                    version_result = subprocess.run([command, '--version'], capture_output=True, text=True)
                    if version_result.returncode == 0:
                        version_detected = version_result.stdout.strip().split('\n')[0]
                    
                    # Determine installation method
                    if '/usr/bin/' in installation_path:
                        installation_method = "system package"
                    elif '/usr/local/bin/' in installation_path:
                        installation_method = "manually installed"
                    elif '/snap/' in installation_path:
                        installation_method = "snap package"
                    else:
                        installation_method = "unknown"
                    
                    break
            
            except Exception:
                continue
        
        # Check service status if applicable
        service_status = ""
        if service_name and compatible:
            try:
                systemctl_result = subprocess.run(
                    ['systemctl', 'is-active', service_name],
                    capture_output=True, text=True
                )
                service_status = systemctl_result.stdout.strip()
            except Exception:
                service_status = "unknown"
        
        return BareMetalCompatibility(
            component=package_name,
            compatible=compatible,
            version_detected=version_detected,
            installation_method=installation_method,
            service_status=service_status,
            configuration_path=self._find_config_path(package_name) if compatible else None
        )
    
    def _find_config_path(self, package_name: str) -> Optional[str]:
        """Find configuration file path for a package."""
        config_paths = {
            'nginx': ['/etc/nginx/nginx.conf', '/usr/local/nginx/conf/nginx.conf'],
            'postgresql': ['/etc/postgresql/*/main/postgresql.conf', '/var/lib/pgsql/data/postgresql.conf'],
            'redis': ['/etc/redis/redis.conf', '/usr/local/etc/redis.conf'],
            'docker': ['/etc/docker/daemon.json']
        }
        
        paths = config_paths.get(package_name, [])
        
        for path in paths:
            if '*' in path:
                # Handle glob patterns
                import glob
                matches = glob.glob(path)
                if matches:
                    return matches[0]
            else:
                if os.path.exists(path):
                    return path
        
        return None
    
    def _check_system_services(self) -> List[BareMetalCompatibility]:
        """Check system services status."""
        results = []
        
        important_services = ['systemd', 'networkd', 'resolved', 'ssh']
        
        for service in important_services:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True, text=True
                )
                
                status = result.stdout.strip()
                compatible = status in ['active', 'running']
                
                results.append(BareMetalCompatibility(
                    component=f"service_{service}",
                    compatible=compatible,
                    service_status=status,
                    notes=f"System service {service} status"
                ))
            
            except Exception as e:
                results.append(BareMetalCompatibility(
                    component=f"service_{service}",
                    compatible=False,
                    notes=f"Could not check service status: {e}"
                ))
        
        return results
    
    def _check_system_configuration(self) -> List[BareMetalCompatibility]:
        """Check system configuration for compatibility."""
        results = []
        
        # Check system resources
        try:
            import psutil
            
            # Memory check
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            
            results.append(BareMetalCompatibility(
                component="system_memory",
                compatible=memory_gb >= 4.0,
                notes=f"Available memory: {memory_gb:.1f}GB (minimum 4GB recommended)"
            ))
            
            # Disk space check
            disk = psutil.disk_usage('/')
            disk_gb = disk.free / (1024**3)
            
            results.append(BareMetalCompatibility(
                component="system_disk",
                compatible=disk_gb >= 20.0,
                notes=f"Available disk space: {disk_gb:.1f}GB (minimum 20GB recommended)"
            ))
            
            # CPU check
            cpu_count = psutil.cpu_count()
            
            results.append(BareMetalCompatibility(
                component="system_cpu",
                compatible=cpu_count >= 2,
                notes=f"CPU cores: {cpu_count} (minimum 2 recommended)"
            ))
        
        except Exception as e:
            results.append(BareMetalCompatibility(
                component="system_resources",
                compatible=False,
                notes=f"Could not check system resources: {e}"
            ))
        
        return results
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        self.logger.info("📊 Generating security report...")
        
        # Run all validations
        env_findings = self.validate_environment_security()
        network_findings = self.validate_network_security()
        database_findings = self.validate_database_security()
        container_findings = self.validate_container_security()
        bare_metal_results = self.validate_bare_metal_compatibility()
        
        all_findings = env_findings + network_findings + database_findings + container_findings
        
        # Categorize findings by severity
        findings_by_severity = {
            SecurityLevel.CRITICAL: [],
            SecurityLevel.HIGH: [],
            SecurityLevel.MEDIUM: [],
            SecurityLevel.LOW: []
        }
        
        for finding in all_findings:
            findings_by_severity[finding.severity].append(finding)
        
        # Generate report
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_findings': len(all_findings),
                'critical': len(findings_by_severity[SecurityLevel.CRITICAL]),
                'high': len(findings_by_severity[SecurityLevel.HIGH]),
                'medium': len(findings_by_severity[SecurityLevel.MEDIUM]),
                'low': len(findings_by_severity[SecurityLevel.LOW])
            },
            'findings': [
                {
                    'category': finding.category.value,
                    'severity': finding.severity.value,
                    'title': finding.title,
                    'description': finding.description,
                    'remediation': finding.remediation,
                    'affected_component': finding.affected_component,
                    'technical_details': finding.technical_details
                }
                for finding in all_findings
            ],
            'bare_metal_compatibility': [
                {
                    'component': result.component,
                    'compatible': result.compatible,
                    'version_detected': result.version_detected,
                    'installation_method': result.installation_method,
                    'service_status': result.service_status,
                    'configuration_path': result.configuration_path,
                    'notes': result.notes
                }
                for result in bare_metal_results
            ]
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = 'security_report.json'):
        """Save security report to file."""
        report_path = self.repo_root / filename
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"📄 Security report saved to {report_path}")

async def main():
    """Main function for security validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive Security and Bare Metal Validation")
    parser.add_argument('--repo-root', default='.', help='Repository root directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--output', default='security_report.json', help='Output report filename')
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = SecurityValidator(args.repo_root, args.verbose)
    
    try:
        # Generate comprehensive report
        report = validator.generate_security_report()
        
        # Save report
        validator.save_report(report, args.output)
        
        # Print summary
        summary = report['summary']
        print(f"\n🔒 Security Validation Complete")
        print(f"📊 Total findings: {summary['total_findings']}")
        
        if summary['critical'] > 0:
            print(f"🚨 Critical: {summary['critical']}")
        if summary['high'] > 0:
            print(f"❗ High: {summary['high']}")
        if summary['medium'] > 0:
            print(f"⚠️  Medium: {summary['medium']}")
        if summary['low'] > 0:
            print(f"ℹ️  Low: {summary['low']}")
        
        # Print bare metal compatibility summary
        bare_metal = report['bare_metal_compatibility']
        compatible_count = sum(1 for item in bare_metal if item['compatible'])
        total_count = len(bare_metal)
        
        print(f"\n🖥️  Bare Metal Compatibility: {compatible_count}/{total_count} components compatible")
        
        # Exit with appropriate code
        if summary['critical'] > 0:
            return 1
        elif summary['high'] > 0:
            return 2
        else:
            return 0
    
    except Exception as e:
        print(f"❌ Security validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)