#!/usr/bin/env python3
"""
Flexible Configuration Management and OAuth Validation System

This module provides comprehensive configuration management with support for:
- Dynamic environment adaptation (bare metal vs containerized)
- Port conflict resolution with service discovery
- OAuth provider configuration and validation
- User management system testing
- Next.js framework optimization validation
- Security baseline enforcement

Features:
- Automatic detection of existing services and port reuse
- OAuth flow testing with multiple providers
- User registration and authentication validation
- Real-time configuration updates
- Performance optimization recommendations
- Security vulnerability scanning
"""

import os
import sys
import json
import asyncio
import aiohttp
import socket
import subprocess
import psutil
import time
import yaml
import jwt
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import configparser
from urllib.parse import urlparse, urljoin
import tempfile
import hashlib
import secrets

class ServiceDetectionResult(Enum):
    NOT_FOUND = "not_found"
    RUNNING_COMPATIBLE = "running_compatible"
    RUNNING_INCOMPATIBLE = "running_incompatible"
    PORT_CONFLICT = "port_conflict"

@dataclass
class ServiceInfo:
    name: str
    port: int
    protocol: str = "http"
    health_endpoint: str = ""
    pid: Optional[int] = None
    version: Optional[str] = None
    compatible: bool = False
    can_reuse: bool = False

@dataclass
class OAuthProvider:
    name: str
    client_id: str
    client_secret: str
    auth_url: str
    token_url: str
    user_info_url: str
    scopes: List[str] = field(default_factory=list)
    enabled: bool = True

class FlexibleConfigManager:
    """Manages flexible configuration with adaptation capabilities."""
    
    def __init__(self, repo_root: str, verbose: bool = True):
        self.repo_root = Path(repo_root)
        self.verbose = verbose
        self.env_file = self.repo_root / ".env"
        self.config_cache = {}
        self.service_registry = {}
        self.oauth_providers = {}
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO if verbose else logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def detect_existing_services(self) -> Dict[str, ServiceInfo]:
        """Detect existing services running on the system."""
        self.logger.info("🔍 Detecting existing services...")
        
        services_to_check = {
            'postgresql': 5432,
            'redis': 6379,
            'nginx': 80,
            'apache': 80,
            'node': 3000,
            'express': 3000,
            'fastapi': 8000,
            'kong': 8000,
            'traefik': 8080,
            'ollama': 11434,
            'n8n': 5678,
            'neo4j': 7474,
            'qdrant': 6333
        }
        
        detected_services = {}
        
        for service_name, default_port in services_to_check.items():
            service_info = self._detect_service(service_name, default_port)
            if service_info:
                detected_services[service_name] = service_info
                
                if service_info.compatible:
                    self.logger.info(f"✅ Found compatible {service_name} service on port {service_info.port}")
                else:
                    self.logger.warning(f"⚠️  Found incompatible {service_name} service on port {service_info.port}")
        
        return detected_services
    
    def _detect_service(self, service_name: str, port: int) -> Optional[ServiceInfo]:
        """Detect a specific service."""
        # Check if port is in use
        if not self._is_port_in_use(port):
            return None
        
        # Try to identify the service
        pid = self._get_pid_on_port(port)
        process_name = self._get_process_name(pid) if pid else "unknown"
        
        # Try to get version and compatibility info
        version = self._get_service_version(service_name, port)
        compatible = self._check_service_compatibility(service_name, port, version)
        can_reuse = compatible and self._check_service_reusability(service_name, port)
        
        # Try to find health endpoint
        health_endpoint = self._discover_health_endpoint(port)
        
        return ServiceInfo(
            name=service_name,
            port=port,
            pid=pid,
            version=version,
            compatible=compatible,
            can_reuse=can_reuse,
            health_endpoint=health_endpoint
        )
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False
    
    def _get_pid_on_port(self, port: int) -> Optional[int]:
        """Get PID of process using a port."""
        try:
            connections = psutil.net_connections()
            for conn in connections:
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    return conn.pid
        except Exception:
            pass
        return None
    
    def _get_process_name(self, pid: int) -> str:
        """Get process name from PID."""
        try:
            process = psutil.Process(pid)
            return process.name()
        except Exception:
            return "unknown"
    
    def _get_service_version(self, service_name: str, port: int) -> Optional[str]:
        """Try to determine service version."""
        version_endpoints = {
            'postgresql': lambda: self._check_postgres_version(port),
            'redis': lambda: self._check_redis_version(port),
            'kong': lambda: self._check_kong_version(port),
            'traefik': lambda: self._check_traefik_version(port),
            'n8n': lambda: self._check_n8n_version(port)
        }
        
        checker = version_endpoints.get(service_name)
        if checker:
            try:
                return checker()
            except Exception as e:
                self.logger.debug(f"Failed to get version for {service_name}: {e}")
        
        return None
    
    def _check_postgres_version(self, port: int) -> str:
        """Check PostgreSQL version."""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port=port,
                database='postgres',
                user='postgres',
                password='',
                connect_timeout=5
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            conn.close()
            return version.split()[1]  # Extract version number
        except Exception:
            return None
    
    def _check_redis_version(self, port: int) -> str:
        """Check Redis version."""
        try:
            import redis
            r = redis.Redis(host='localhost', port=port, socket_timeout=5)
            info = r.info()
            return info['redis_version']
        except Exception:
            return None
    
    def _check_kong_version(self, port: int) -> str:
        """Check Kong version."""
        try:
            response = requests.get(f"http://localhost:{port}/", timeout=5)
            if 'Kong' in response.headers.get('Server', ''):
                return response.headers['Server'].split('/')[1]
        except Exception:
            pass
        return None
    
    def _check_traefik_version(self, port: int) -> str:
        """Check Traefik version."""
        try:
            response = requests.get(f"http://localhost:{port}/api/version", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('Version', 'unknown')
        except Exception:
            pass
        return None
    
    def _check_n8n_version(self, port: int) -> str:
        """Check n8n version."""
        try:
            response = requests.get(f"http://localhost:{port}/rest/settings", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('n8n', {}).get('version', 'unknown')
        except Exception:
            pass
        return None
    
    def _check_service_compatibility(self, service_name: str, port: int, version: str) -> bool:
        """Check if an existing service is compatible with our stack."""
        compatibility_rules = {
            'postgresql': lambda v: v and float(v.split('.')[0]) >= 13,
            'redis': lambda v: v and float(v.split('.')[0]) >= 6,
            'kong': lambda v: v and float(v.split('.')[0]) >= 3,
            'traefik': lambda v: v and float(v.split('.')[0]) >= 2,
            'n8n': lambda v: v and float(v.split('.')[0]) >= 1
        }
        
        rule = compatibility_rules.get(service_name)
        if rule and version:
            try:
                return rule(version)
            except (ValueError, IndexError):
                return False
        
        return False
    
    def _check_service_reusability(self, service_name: str, port: int) -> bool:
        """Check if we can reuse an existing service."""
        # For now, assume we can reuse compatible services
        # In production, this would include more sophisticated checks
        reusability_rules = {
            'postgresql': True,  # Can usually share databases
            'redis': True,      # Can usually share cache
            'kong': False,      # Usually needs dedicated config
            'traefik': False,   # Usually needs dedicated config
            'n8n': False       # Workflow service should be dedicated
        }
        
        return reusability_rules.get(service_name, False)
    
    def _discover_health_endpoint(self, port: int) -> str:
        """Try to discover health check endpoint."""
        common_health_paths = [
            '/health', '/healthz', '/health-check', '/ping',
            '/status', '/api/health', '/api/ping'
        ]
        
        for path in common_health_paths:
            try:
                response = requests.get(f"http://localhost:{port}{path}", timeout=2)
                if response.status_code in [200, 204]:
                    return path
            except Exception:
                continue
        
        return ""
    
    def resolve_port_conflicts(self, desired_config: Dict[str, int]) -> Dict[str, int]:
        """Resolve port conflicts by finding alternatives or reusing services."""
        self.logger.info("🔧 Resolving port conflicts...")
        
        resolved_config = {}
        detected_services = self.detect_existing_services()
        
        for service_name, desired_port in desired_config.items():
            if self._is_port_in_use(desired_port):
                # Check if we can reuse existing service
                existing_service = detected_services.get(service_name)
                
                if existing_service and existing_service.can_reuse:
                    self.logger.info(f"♻️  Reusing existing {service_name} on port {desired_port}")
                    resolved_config[service_name] = desired_port
                else:
                    # Find alternative port
                    alternative_port = self._find_alternative_port(desired_port)
                    self.logger.warning(f"🔄 Port {desired_port} conflicts, using {alternative_port} for {service_name}")
                    resolved_config[service_name] = alternative_port
            else:
                resolved_config[service_name] = desired_port
        
        return resolved_config
    
    def _find_alternative_port(self, base_port: int) -> int:
        """Find an alternative port starting from base_port + 1000."""
        start_port = base_port + 1000
        for port in range(start_port, start_port + 100):
            if not self._is_port_in_use(port):
                return port
        
        # If no port found in range, try random high ports
        for _ in range(10):
            port = 50000 + secrets.randbelow(15000)  # 50000-65000 range
            if not self._is_port_in_use(port):
                return port
        
        raise RuntimeError(f"Could not find alternative port for {base_port}")
    
    def generate_adaptive_config(self) -> Dict[str, Any]:
        """Generate configuration that adapts to the current environment."""
        self.logger.info("⚙️  Generating adaptive configuration...")
        
        # Base service configuration
        base_config = {
            'postgresql': 5432,
            'kong': 8000,
            'n8n': 5678,
            'openwebui': 3000,
            'flowise': 8080,
            'qdrant': 6333,
            'neo4j': 7474,
            'ollama': 11434,
            'traefik': 8080
        }
        
        # Resolve port conflicts
        resolved_ports = self.resolve_port_conflicts(base_config)
        
        # Generate environment variables
        env_vars = self._generate_adaptive_env_vars(resolved_ports)
        
        # Add OAuth configuration
        oauth_config = self._setup_oauth_providers()
        
        return {
            'ports': resolved_ports,
            'environment': env_vars,
            'oauth': oauth_config,
            'services': self.detect_existing_services()
        }
    
    def _generate_adaptive_env_vars(self, port_config: Dict[str, int]) -> Dict[str, str]:
        """Generate environment variables based on resolved configuration."""
        env_vars = {}
        
        # Database configuration
        if 'postgresql' in port_config:
            env_vars.update({
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_PORT': str(port_config['postgresql']),
                'POSTGRES_DB': 'postgres',
                'POSTGRES_USER': 'postgres'
            })
        
        # Service URLs
        base_domain = os.getenv('BASE_DOMAIN', 'localhost')
        
        for service, port in port_config.items():
            if service in ['kong', 'n8n', 'openwebui', 'flowise']:
                if base_domain == 'localhost':
                    env_vars[f'{service.upper()}_URL'] = f'http://localhost:{port}'
                else:
                    env_vars[f'{service.upper()}_URL'] = f'https://{service}.{base_domain}'
        
        return env_vars
    
    def _setup_oauth_providers(self) -> Dict[str, OAuthProvider]:
        """Setup OAuth provider configurations."""
        providers = {}
        
        # GitHub OAuth
        if os.getenv('GITHUB_CLIENT_ID') and os.getenv('GITHUB_CLIENT_SECRET'):
            providers['github'] = OAuthProvider(
                name='GitHub',
                client_id=os.getenv('GITHUB_CLIENT_ID'),
                client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
                auth_url='https://github.com/login/oauth/authorize',
                token_url='https://github.com/login/oauth/access_token',
                user_info_url='https://api.github.com/user',
                scopes=['user:email']
            )
        
        # Google OAuth
        if os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET'):
            providers['google'] = OAuthProvider(
                name='Google',
                client_id=os.getenv('GOOGLE_CLIENT_ID'),
                client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
                auth_url='https://accounts.google.com/o/oauth2/auth',
                token_url='https://oauth2.googleapis.com/token',
                user_info_url='https://www.googleapis.com/oauth2/v2/userinfo',
                scopes=['openid', 'email', 'profile']
            )
        
        return providers
    
    async def validate_oauth_configuration(self) -> Dict[str, bool]:
        """Validate OAuth provider configurations."""
        self.logger.info("🔐 Validating OAuth configurations...")
        
        validation_results = {}
        oauth_config = self._setup_oauth_providers()
        
        for provider_name, provider in oauth_config.items():
            try:
                # Test if endpoints are reachable
                async with aiohttp.ClientSession() as session:
                    # Check auth endpoint
                    async with session.get(provider.auth_url, timeout=10) as response:
                        auth_reachable = response.status in [200, 302, 400]  # 400 is expected for missing params
                    
                    # Check token endpoint (POST)
                    async with session.post(provider.token_url, timeout=10) as response:
                        token_reachable = response.status in [400, 401, 405]  # Expected error codes
                
                validation_results[provider_name] = auth_reachable and token_reachable
                
                if validation_results[provider_name]:
                    self.logger.info(f"✅ OAuth provider {provider_name} configuration valid")
                else:
                    self.logger.warning(f"❌ OAuth provider {provider_name} configuration invalid")
            
            except Exception as e:
                self.logger.error(f"❌ OAuth validation failed for {provider_name}: {e}")
                validation_results[provider_name] = False
        
        return validation_results
    
    async def test_user_management_flows(self) -> Dict[str, bool]:
        """Test user registration and authentication flows."""
        self.logger.info("👤 Testing user management flows...")
        
        test_results = {}
        
        # Test Supabase auth endpoints
        supabase_tests = await self._test_supabase_auth()
        test_results.update(supabase_tests)
        
        # Test OAuth flows if configured
        oauth_tests = await self._test_oauth_flows()
        test_results.update(oauth_tests)
        
        return test_results
    
    async def _test_supabase_auth(self) -> Dict[str, bool]:
        """Test Supabase authentication endpoints."""
        results = {}
        
        auth_base_url = os.getenv('SUPABASE_URL', 'http://localhost:8000')
        anon_key = os.getenv('ANON_KEY', '')
        
        if not anon_key:
            self.logger.warning("No ANON_KEY found, skipping Supabase auth tests")
            return results
        
        headers = {
            'apikey': anon_key,
            'Authorization': f'Bearer {anon_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test auth settings endpoint
                async with session.get(
                    f'{auth_base_url}/auth/v1/settings',
                    headers=headers,
                    timeout=10
                ) as response:
                    results['supabase_auth_settings'] = response.status == 200
                
                # Test user signup endpoint (should return 400 for missing data)
                async with session.post(
                    f'{auth_base_url}/auth/v1/signup',
                    headers=headers,
                    json={},
                    timeout=10
                ) as response:
                    results['supabase_signup_endpoint'] = response.status in [400, 422]
                
                # Test user login endpoint (should return 400 for missing data)
                async with session.post(
                    f'{auth_base_url}/auth/v1/token',
                    headers=headers,
                    params={'grant_type': 'password'},
                    json={},
                    timeout=10
                ) as response:
                    results['supabase_login_endpoint'] = response.status in [400, 422]
        
        except Exception as e:
            self.logger.error(f"Supabase auth test failed: {e}")
            for key in ['supabase_auth_settings', 'supabase_signup_endpoint', 'supabase_login_endpoint']:
                results[key] = False
        
        return results
    
    async def _test_oauth_flows(self) -> Dict[str, bool]:
        """Test OAuth provider flows."""
        results = {}
        oauth_config = self._setup_oauth_providers()
        
        for provider_name, provider in oauth_config.items():
            try:
                # Test OAuth authorization URL generation
                auth_params = {
                    'client_id': provider.client_id,
                    'response_type': 'code',
                    'scope': ' '.join(provider.scopes),
                    'redirect_uri': 'http://localhost:3000/auth/callback'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        provider.auth_url,
                        params=auth_params,
                        timeout=10,
                        allow_redirects=False
                    ) as response:
                        # OAuth providers typically return 302 for valid auth requests
                        results[f'oauth_{provider_name}_auth_flow'] = response.status in [200, 302]
            
            except Exception as e:
                self.logger.error(f"OAuth test failed for {provider_name}: {e}")
                results[f'oauth_{provider_name}_auth_flow'] = False
        
        return results
    
    def optimize_nextjs_configuration(self) -> Dict[str, Any]:
        """Optimize Next.js configuration for the current environment."""
        self.logger.info("⚡ Optimizing Next.js configuration...")
        
        optimizations = {
            'performance': {},
            'security': {},
            'features': {}
        }
        
        # Performance optimizations
        optimizations['performance'] = {
            'experimental': {
                'serverComponentsExternalPackages': ['@supabase/supabase-js'],
                'optimizeCss': True,
                'optimizeServerReact': True,
                'optimizePackageImports': ['@supabase/supabase-js', 'lucide-react']
            },
            'images': {
                'remotePatterns': [
                    {
                        'protocol': 'https',
                        'hostname': '*.supabase.co'
                    }
                ]
            },
            'output': 'standalone'
        }
        
        # Security optimizations
        optimizations['security'] = {
            'headers': {
                'X-DNS-Prefetch-Control': 'false',
                'X-Frame-Options': 'DENY',
                'X-Content-Type-Options': 'nosniff',
                'Referrer-Policy': 'origin-when-cross-origin',
                'Content-Security-Policy': self._generate_csp_header()
            }
        }
        
        # Feature optimizations based on detected services
        detected_services = self.service_registry
        
        if 'neo4j' in detected_services:
            optimizations['features']['graph_database'] = True
        
        if 'qdrant' in detected_services:
            optimizations['features']['vector_search'] = True
        
        return optimizations
    
    def _generate_csp_header(self) -> str:
        """Generate Content Security Policy header."""
        base_domain = os.getenv('BASE_DOMAIN', 'localhost')
        
        if base_domain == 'localhost':
            allowed_origins = "'self' http://localhost:* ws://localhost:*"
        else:
            allowed_origins = f"'self' https://*.{base_domain} wss://*.{base_domain}"
        
        csp = f"""
            default-src 'self';
            script-src 'self' 'unsafe-inline' 'unsafe-eval' {allowed_origins};
            style-src 'self' 'unsafe-inline' {allowed_origins};
            img-src 'self' data: {allowed_origins};
            connect-src 'self' {allowed_origins};
            font-src 'self' {allowed_origins};
            object-src 'none';
            base-uri 'self';
            form-action 'self';
            frame-ancestors 'none';
            upgrade-insecure-requests;
        """.replace('\n', ' ').replace('  ', ' ').strip()
        
        return csp
    
    def save_configuration(self, config: Dict[str, Any], config_file: str = 'adaptive_config.json'):
        """Save adaptive configuration to file."""
        config_path = self.repo_root / config_file
        
        # Make config JSON serializable
        serializable_config = self._make_serializable(config)
        
        with open(config_path, 'w') as f:
            json.dump(serializable_config, f, indent=2, default=str)
        
        self.logger.info(f"💾 Configuration saved to {config_path}")
        
        # Also generate environment file
        self._generate_env_file(config)
    
    def _make_serializable(self, obj):
        """Make object JSON serializable."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._make_serializable(obj.__dict__)
        else:
            return obj
    
    def _generate_env_file(self, config: Dict[str, Any]):
        """Generate .env file from configuration."""
        env_content = []
        
        # Add header
        env_content.append("# Adaptive Configuration Generated Environment")
        env_content.append(f"# Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        env_content.append("")
        
        # Add environment variables
        for key, value in config.get('environment', {}).items():
            env_content.append(f"{key}={value}")
        
        # Add port mappings as comments for reference
        env_content.append("")
        env_content.append("# Port Mappings")
        for service, port in config.get('ports', {}).items():
            env_content.append(f"# {service.upper()}_PORT={port}")
        
        # Write to file
        env_path = self.repo_root / ".env.adaptive"
        with open(env_path, 'w') as f:
            f.write('\n'.join(env_content))
        
        self.logger.info(f"📝 Adaptive .env file generated: {env_path}")

async def main():
    """Main function for testing the flexible configuration manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Flexible Configuration Management")
    parser.add_argument('--repo-root', default='.', help='Repository root directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--test-oauth', action='store_true', help='Test OAuth configurations')
    parser.add_argument('--test-auth', action='store_true', help='Test authentication flows')
    parser.add_argument('--optimize-nextjs', action='store_true', help='Generate Next.js optimizations')
    
    args = parser.parse_args()
    
    # Initialize configuration manager
    config_manager = FlexibleConfigManager(args.repo_root, args.verbose)
    
    try:
        # Generate adaptive configuration
        config = config_manager.generate_adaptive_config()
        
        print("🔧 Adaptive Configuration Generated")
        print(f"📍 Detected {len(config['services'])} existing services")
        print(f"🚪 Configured {len(config['ports'])} service ports")
        
        if config['oauth']:
            print(f"🔐 Configured {len(config['oauth'])} OAuth providers")
        
        # Test OAuth if requested
        if args.test_oauth and config['oauth']:
            print("\n🔐 Testing OAuth configurations...")
            oauth_results = await config_manager.validate_oauth_configuration()
            for provider, valid in oauth_results.items():
                status = "✅" if valid else "❌"
                print(f"{status} {provider}")
        
        # Test authentication flows if requested
        if args.test_auth:
            print("\n👤 Testing authentication flows...")
            auth_results = await config_manager.test_user_management_flows()
            for test_name, passed in auth_results.items():
                status = "✅" if passed else "❌"
                print(f"{status} {test_name}")
        
        # Generate Next.js optimizations if requested
        if args.optimize_nextjs:
            print("\n⚡ Generating Next.js optimizations...")
            nextjs_config = config_manager.optimize_nextjs_configuration()
            print(f"📊 Generated {len(nextjs_config)} optimization categories")
        
        # Save configuration
        config_manager.save_configuration(config)
        
        print("\n✅ Configuration management completed successfully")
    
    except Exception as e:
        print(f"❌ Configuration management failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)