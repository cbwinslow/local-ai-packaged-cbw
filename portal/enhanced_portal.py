#!/usr/bin/env python3
"""
Enhanced Local AI Portal with Configuration Management and Deployment Controls

This enhanced portal provides:
- Service dashboard and links
- Environment variable configuration
- Deployment controls and status
- Password generation and management
- Health checks and monitoring
- Troubleshooting guides
"""

import os
import json
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import threading
import hashlib
import secrets
import string

PORT = int(os.getenv("PORTAL_PORT", "8085"))
REPO_ROOT = Path(__file__).parent.parent

class ConfigurationManager:
    """Handles environment configuration and validation."""
    
    def __init__(self):
        self.env_file = REPO_ROOT / ".env"
        self.env_backup_dir = REPO_ROOT / "env_backups"
        self.env_backup_dir.mkdir(exist_ok=True)
    
    def load_env(self):
        """Load environment variables from .env file."""
        env_vars = {}
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        return env_vars
    
    def save_env(self, env_vars):
        """Save environment variables to .env file with backup."""
        # Create backup
        if self.env_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.env_backup_dir / f".env.backup.{timestamp}"
            self.env_file.rename(backup_file)
        
        # Write new .env file
        with open(self.env_file, 'w') as f:
            f.write(f"# Local AI Package Configuration\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write(f"# Portal: Enhanced Configuration Manager\n\n")
            
            for key, value in sorted(env_vars.items()):
                f.write(f"{key}={value}\n")
    
    def generate_secure_credentials(self):
        """Generate secure credentials for all required services."""
        def generate_password(length=32, symbols=True):
            charset = string.ascii_letters + string.digits
            if symbols:
                charset += "!@#$%^&*-_="
            return ''.join(secrets.choice(charset) for _ in range(length))
        
        def generate_postgres_password(length=32):
            # PostgreSQL passwords should be alphanumeric only
            charset = string.ascii_letters + string.digits
            return ''.join(secrets.choice(charset) for _ in range(length))
        
        def generate_jwt_secret(length=64):
            return secrets.token_urlsafe(length)
        
        return {
            'POSTGRES_PASSWORD': generate_postgres_password(32),
            'NEO4J_PASSWORD': generate_postgres_password(24),
            'JWT_SECRET': generate_jwt_secret(64),
            'N8N_ENCRYPTION_KEY': generate_jwt_secret(48),
            'N8N_USER_MANAGEMENT_JWT_SECRET': generate_jwt_secret(48),
            'SERVICE_ROLE_KEY': generate_jwt_secret(64),
            'ANON_KEY': generate_jwt_secret(64),
            'GRAFANA_ADMIN_PASSWORD': generate_password(24),
            'N8N_BASIC_AUTH_PASSWORD': generate_password(24),
            'FLOWISE_PASSWORD': generate_password(24),
        }

class DeploymentManager:
    """Handles deployment operations and status monitoring."""
    
    def __init__(self):
        self.start_services_script = REPO_ROOT / "start_services.py"
        self.deployment_status = {
            'status': 'stopped',
            'last_action': None,
            'last_error': None,
            'services': {}
        }
    
    def get_deployment_status(self):
        """Get current deployment status."""
        # Check Docker containers
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "json"], 
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        containers.append(json.loads(line))
                
                # Update service status
                for container in containers:
                    name = container.get('Names', '')
                    state = container.get('State', 'unknown')
                    self.deployment_status['services'][name] = {
                        'status': state,
                        'image': container.get('Image', ''),
                        'ports': container.get('Ports', '')
                    }
                
                if containers:
                    self.deployment_status['status'] = 'running'
                else:
                    self.deployment_status['status'] = 'stopped'
        except Exception as e:
            self.deployment_status['last_error'] = str(e)
        
        return self.deployment_status
    
    def start_deployment(self, profile='cpu', environment='private'):
        """Start deployment with specified profile."""
        try:
            cmd = [sys.executable, str(self.start_services_script)]
            if profile and profile != 'cpu':
                cmd.extend(['--profile', profile])
            if environment and environment != 'private':
                cmd.extend(['--environment', environment])
            
            # Run in background
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.deployment_status['status'] = 'starting'
            self.deployment_status['last_action'] = f"Starting with profile={profile}, environment={environment}"
            return True, "Deployment started"
        except Exception as e:
            self.deployment_status['last_error'] = str(e)
            return False, f"Failed to start deployment: {e}"
    
    def stop_deployment(self):
        """Stop all deployment containers."""
        try:
            subprocess.run(
                ["docker", "compose", "-p", "localai", "down"],
                capture_output=True, text=True, timeout=60
            )
            self.deployment_status['status'] = 'stopped'
            self.deployment_status['last_action'] = "Stopped deployment"
            return True, "Deployment stopped"
        except Exception as e:
            self.deployment_status['last_error'] = str(e)
            return False, f"Failed to stop deployment: {e}"

class HealthChecker:
    """Performs health checks on services."""
    
    def __init__(self):
        self.health_endpoints = {
            'Supabase Auth': 'http://localhost:9999/health',
            'Supabase Rest': 'http://localhost:8000/rest/v1/',
            'n8n': 'http://localhost:5678/healthz',
            'Open WebUI': 'http://localhost:3000/health',
            'Flowise': 'http://localhost:3001/health',
            'Neo4j': 'http://localhost:7474/db/system/tx/commit',
            'Ollama': 'http://localhost:11434/api/version'
        }
    
    def check_health(self):
        """Check health of all services."""
        health_results = {}
        
        for service, endpoint in self.health_endpoints.items():
            try:
                import urllib.request
                req = urllib.request.Request(endpoint)
                with urllib.request.urlopen(req, timeout=5) as response:
                    status_code = response.getcode()
                    health_results[service] = {
                        'status': 'healthy' if status_code < 400 else 'unhealthy',
                        'status_code': status_code,
                        'response_time': 'N/A'  # Could implement timing
                    }
            except Exception as e:
                health_results[service] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'status_code': None
                }
        
        return health_results

class EnhancedPortalHandler(BaseHTTPRequestHandler):
    """Enhanced HTTP request handler for the portal."""
    
    def __init__(self, *args, **kwargs):
        self.config_manager = ConfigurationManager()
        self.deployment_manager = DeploymentManager()
        self.health_checker = HealthChecker()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.serve_dashboard()
        elif self.path == '/config':
            self.serve_config_page()
        elif self.path == '/deployment':
            self.serve_deployment_page()
        elif self.path == '/health':
            self.serve_health_page()
        elif self.path == '/api/status':
            self.serve_api_status()
        elif self.path == '/api/health':
            self.serve_api_health()
        elif self.path.startswith('/static/'):
            self.serve_static()
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/api/config/save':
            self.handle_config_save()
        elif self.path == '/api/config/generate':
            self.handle_config_generate()
        elif self.path == '/api/deployment/start':
            self.handle_deployment_start()
        elif self.path == '/api/deployment/stop':
            self.handle_deployment_stop()
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        """Serve the main dashboard."""
        env_vars = self.config_manager.load_env()
        deployment_status = self.deployment_manager.get_deployment_status()
        
        # Generate service links
        service_links = self.generate_service_links(env_vars)
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Local AI Portal - Enhanced</title>
            <style>
                body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .nav {{ display: flex; gap: 20px; margin: 20px 0; }}
                .nav a {{ padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
                .nav a:hover {{ background: #0056b3; }}
                .card {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .status {{ padding: 10px; border-radius: 4px; margin: 10px 0; }}
                .status.running {{ background: #d4edda; color: #155724; }}
                .status.stopped {{ background: #f8d7da; color: #721c24; }}
                .status.starting {{ background: #fff3cd; color: #856404; }}
                .service-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}
                .service-item {{ padding: 15px; background: #f8f9fa; border-radius: 4px; border-left: 4px solid #007bff; }}
                .service-item a {{ color: #007bff; text-decoration: none; font-weight: 500; }}
                .service-item a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 Local AI Portal - Enhanced</h1>
                    <p>Comprehensive dashboard for Local AI Package deployment and management</p>
                    <div class="nav">
                        <a href="/">Dashboard</a>
                        <a href="/config">Configuration</a>
                        <a href="/deployment">Deployment</a>
                        <a href="/health">Health Check</a>
                    </div>
                </div>
                
                <div class="card">
                    <h2>Deployment Status</h2>
                    <div class="status {deployment_status['status']}">
                        Status: {deployment_status['status'].upper()}
                    </div>
                    {f"<p>Last Action: {deployment_status['last_action']}</p>" if deployment_status['last_action'] else ""}
                    {f"<p style='color: red;'>Last Error: {deployment_status['last_error']}</p>" if deployment_status['last_error'] else ""}
                </div>
                
                <div class="card">
                    <h2>Services</h2>
                    <div class="service-grid">
                        {service_links}
                    </div>
                </div>
                
                <div class="card">
                    <h2>Quick Actions</h2>
                    <button onclick="startDeployment()" style="padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 4px; margin-right: 10px;">Start Services</button>
                    <button onclick="stopDeployment()" style="padding: 10px 20px; background: #dc3545; color: white; border: none; border-radius: 4px; margin-right: 10px;">Stop Services</button>
                    <button onclick="window.location.href='/health'" style="padding: 10px 20px; background: #17a2b8; color: white; border: none; border-radius: 4px;">Health Check</button>
                </div>
            </div>
            
            <script>
                function startDeployment() {{
                    fetch('/api/deployment/start', {{ method: 'POST' }})
                        .then(response => response.json())
                        .then(data => {{
                            alert(data.message);
                            window.location.reload();
                        }});
                }}
                
                function stopDeployment() {{
                    if (confirm('Are you sure you want to stop all services?')) {{
                        fetch('/api/deployment/stop', {{ method: 'POST' }})
                            .then(response => response.json())
                            .then(data => {{
                                alert(data.message);
                                window.location.reload();
                            }});
                    }}
                }}
                
                // Auto-refresh status every 30 seconds
                setInterval(() => {{
                    window.location.reload();
                }}, 30000);
            </script>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def generate_service_links(self, env_vars):
        """Generate HTML for service links."""
        services = [
            ("n8n", "N8N_HOSTNAME", "n8n", "/"),
            ("Open WebUI", "WEBUI_HOSTNAME", "webui", "/"),
            ("Flowise", "FLOWISE_HOSTNAME", "flowise", "/"),
            ("Supabase Studio", "SUPABASE_STUDIO_HOSTNAME", "studio", "/"),
            ("Langfuse", "LANGFUSE_HOSTNAME", "langfuse", "/"),
            ("Neo4j Browser", "NEO4J_HOSTNAME", "neo4j", "/browser/"),
            ("SearXNG", "SEARXNG_HOSTNAME", "searxng", "/"),
            ("Traefik Dashboard", "TRAEFIK_DASHBOARD_HOST", "traefik", "/"),
        ]
        
        links_html = ""
        base_domain = env_vars.get('BASE_DOMAIN', 'localhost')
        
        for service_name, hostname_var, subdomain, path in services:
            hostname = env_vars.get(hostname_var, f"{subdomain}.{base_domain}")
            
            # Determine protocol
            protocol = "https" if base_domain != "localhost" else "http"
            url = f"{protocol}://{hostname}{path}"
            
            links_html += f"""
            <div class="service-item">
                <a href="{url}" target="_blank">{service_name}</a>
                <br><small>{hostname}</small>
            </div>
            """
        
        return links_html
    
    def serve_config_page(self):
        """Serve the configuration management page."""
        env_vars = self.config_manager.load_env()
        
        # Generate form fields for configuration
        config_form = ""
        sensitive_vars = ['PASSWORD', 'SECRET', 'KEY', 'TOKEN']
        
        categories = {
            'Domain & Email': ['BASE_DOMAIN', 'ACME_EMAIL', 'ENVIRONMENT'],
            'Database': ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD'],
            'Authentication': ['JWT_SECRET', 'ANON_KEY', 'SERVICE_ROLE_KEY'],
            'Service Credentials': ['N8N_BASIC_AUTH_PASSWORD', 'FLOWISE_PASSWORD', 'NEO4J_PASSWORD', 'GRAFANA_ADMIN_PASSWORD'],
            'Hostnames': [k for k in env_vars.keys() if 'HOSTNAME' in k],
            'Other': [k for k in env_vars.keys() if k not in sum([
                ['BASE_DOMAIN', 'ACME_EMAIL', 'ENVIRONMENT'],
                ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD'],
                ['JWT_SECRET', 'ANON_KEY', 'SERVICE_ROLE_KEY'],
                ['N8N_BASIC_AUTH_PASSWORD', 'FLOWISE_PASSWORD', 'NEO4J_PASSWORD', 'GRAFANA_ADMIN_PASSWORD']
            ], []) and 'HOSTNAME' not in k]
        }
        
        for category, vars_list in categories.items():
            if not vars_list:
                continue
                
            config_form += f"<h3>{category}</h3>"
            for var_name in vars_list:
                if var_name in env_vars:
                    value = env_vars[var_name]
                    is_sensitive = any(sens in var_name for sens in sensitive_vars)
                    input_type = "password" if is_sensitive else "text"
                    
                    config_form += f"""
                    <div style="margin-bottom: 15px;">
                        <label for="{var_name}" style="display: block; font-weight: bold; margin-bottom: 5px;">{var_name}</label>
                        <input type="{input_type}" id="{var_name}" name="{var_name}" value="{value}" 
                               style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                    """
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Configuration - Local AI Portal</title>
            <style>
                body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .nav {{ display: flex; gap: 20px; margin: 20px 0; }}
                .nav a {{ padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
                .nav a:hover {{ background: #0056b3; }}
                .card {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .btn {{ padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-success {{ background: #28a745; color: white; }}
                .btn-warning {{ background: #ffc107; color: black; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚙️ Configuration Management</h1>
                    <div class="nav">
                        <a href="/">Dashboard</a>
                        <a href="/config">Configuration</a>
                        <a href="/deployment">Deployment</a>
                        <a href="/health">Health Check</a>
                    </div>
                </div>
                
                <div class="card">
                    <h2>Environment Configuration</h2>
                    <p>Manage your Local AI Package configuration. Changes will be saved to .env file with automatic backup.</p>
                    
                    <form id="configForm">
                        {config_form}
                        
                        <div style="margin-top: 30px;">
                            <button type="submit" class="btn btn-primary">Save Configuration</button>
                            <button type="button" onclick="generateCredentials()" class="btn btn-success">Generate New Credentials</button>
                            <button type="button" onclick="resetForm()" class="btn btn-warning">Reset Form</button>
                        </div>
                    </form>
                </div>
            </div>
            
            <script>
                document.getElementById('configForm').addEventListener('submit', function(e) {{
                    e.preventDefault();
                    const formData = new FormData(this);
                    const config = {{}};
                    for (let [key, value] of formData.entries()) {{
                        config[key] = value;
                    }}
                    
                    fetch('/api/config/save', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(config)
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        alert(data.message);
                        if (data.success) {{
                            window.location.reload();
                        }}
                    }});
                }});
                
                function generateCredentials() {{
                    if (confirm('This will generate new secure credentials for all services. Continue?')) {{
                        fetch('/api/config/generate', {{ method: 'POST' }})
                            .then(response => response.json())
                            .then(data => {{
                                alert(data.message);
                                if (data.success) {{
                                    window.location.reload();
                                }}
                            }});
                    }}
                }}
                
                function resetForm() {{
                    if (confirm('Reset form to current saved values?')) {{
                        window.location.reload();
                    }}
                }}
            </script>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def handle_config_save(self):
        """Handle configuration save request."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            config_data = json.loads(post_data.decode('utf-8'))
            
            self.config_manager.save_env(config_data)
            
            response = {'success': True, 'message': 'Configuration saved successfully!'}
        except Exception as e:
            response = {'success': False, 'message': f'Failed to save configuration: {e}'}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def handle_config_generate(self):
        """Handle credential generation request."""
        try:
            env_vars = self.config_manager.load_env()
            new_credentials = self.config_manager.generate_secure_credentials()
            
            # Update existing environment with new credentials
            env_vars.update(new_credentials)
            self.config_manager.save_env(env_vars)
            
            response = {'success': True, 'message': 'New credentials generated successfully!'}
        except Exception as e:
            response = {'success': False, 'message': f'Failed to generate credentials: {e}'}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def serve_health_page(self):
        """Serve the health check page."""
        health_results = self.health_checker.check_health()
        
        health_html = ""
        for service, result in health_results.items():
            status_class = "healthy" if result['status'] == 'healthy' else "unhealthy"
            health_html += f"""
            <div class="health-item {status_class}">
                <h4>{service}</h4>
                <p>Status: {result['status']}</p>
                {f"<p>Status Code: {result['status_code']}</p>" if result.get('status_code') else ""}
                {f"<p>Error: {result['error']}</p>" if result.get('error') else ""}
            </div>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Health Check - Local AI Portal</title>
            <style>
                body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .nav {{ display: flex; gap: 20px; margin: 20px 0; }}
                .nav a {{ padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
                .nav a:hover {{ background: #0056b3; }}
                .card {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .health-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}
                .health-item {{ padding: 15px; border-radius: 4px; border-left: 4px solid #007bff; }}
                .health-item.healthy {{ background: #d4edda; border-left-color: #28a745; }}
                .health-item.unhealthy {{ background: #f8d7da; border-left-color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏥 Health Check</h1>
                    <div class="nav">
                        <a href="/">Dashboard</a>
                        <a href="/config">Configuration</a>
                        <a href="/deployment">Deployment</a>
                        <a href="/health">Health Check</a>
                    </div>
                </div>
                
                <div class="card">
                    <h2>Service Health Status</h2>
                    <p>Real-time health status of all Local AI Package services.</p>
                    <button onclick="window.location.reload()" style="padding: 10px 20px; background: #17a2b8; color: white; border: none; border-radius: 4px; margin-bottom: 20px;">Refresh</button>
                    
                    <div class="health-grid">
                        {health_html}
                    </div>
                </div>
            </div>
            
            <script>
                // Auto-refresh every 15 seconds
                setInterval(() => {{
                    window.location.reload();
                }}, 15000);
            </script>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def handle_deployment_start(self):
        """Handle deployment start request."""
        success, message = self.deployment_manager.start_deployment()
        response = {'success': success, 'message': message}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def handle_deployment_stop(self):
        """Handle deployment stop request."""
        success, message = self.deployment_manager.stop_deployment()
        response = {'success': success, 'message': message}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def serve_api_status(self):
        """Serve deployment status API."""
        status = self.deployment_manager.get_deployment_status()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status).encode())
    
    def serve_api_health(self):
        """Serve health check API."""
        health = self.health_checker.check_health()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(health).encode())

def main():
    """Main function to start the enhanced portal server."""
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, EnhancedPortalHandler)
    
    print(f"Enhanced Local AI Portal starting on port {PORT}")
    print(f"Access at: http://localhost:{PORT}")
    print("Features: Dashboard, Configuration, Deployment, Health Check")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Enhanced Portal...")
        httpd.shutdown()

if __name__ == '__main__':
    main()