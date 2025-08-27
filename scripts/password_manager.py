#!/usr/bin/env python3
"""
Password Management System for Local AI Package

This module provides secure password storage and management capabilities,
including Bitwarden integration for enterprise-grade secret management.

Features:
- Local secure storage with encryption
- Bitwarden CLI integration
- Password generation and rotation
- Backup and restore functionality
- Audit logging for password access
"""

import os
import json
import subprocess
import secrets
import string
import hashlib
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import getpass

class SecurePasswordManager:
    """Local secure password storage with encryption."""
    
    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path) if storage_path else Path.home() / ".local_ai_secrets"
        self.storage_path.mkdir(mode=0o700, exist_ok=True)
        
        self.password_file = self.storage_path / "passwords.enc"
        self.audit_file = self.storage_path / "audit.log"
        self.key_file = self.storage_path / ".key"
        
        self._fernet = None
        self._master_password = None
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from master password."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create new one."""
        salt_file = self.storage_path / ".salt"
        if salt_file.exists():
            return salt_file.read_bytes()
        else:
            salt = os.urandom(16)
            salt_file.write_bytes(salt)
            salt_file.chmod(0o600)
            return salt
    
    def initialize(self, master_password: str = None) -> bool:
        """Initialize the password manager with a master password."""
        if not master_password:
            master_password = getpass.getpass("Enter master password for Local AI secrets: ")
        
        salt = self._get_or_create_salt()
        key = self._derive_key(master_password, salt)
        self._fernet = Fernet(key)
        self._master_password = master_password
        
        # Test encryption/decryption
        try:
            test_data = "test"
            encrypted = self._fernet.encrypt(test_data.encode())
            decrypted = self._fernet.decrypt(encrypted).decode()
            if decrypted != test_data:
                raise Exception("Encryption test failed")
            
            self._log_audit("INIT", "Password manager initialized successfully")
            return True
        except Exception as e:
            print(f"Failed to initialize password manager: {e}")
            return False
    
    def _log_audit(self, action: str, details: str):
        """Log audit events."""
        timestamp = datetime.now().isoformat()
        audit_entry = f"{timestamp} - {action}: {details}\n"
        
        with open(self.audit_file, "a") as f:
            f.write(audit_entry)
    
    def store_password(self, service: str, username: str, password: str, metadata: Dict = None) -> bool:
        """Store a password securely."""
        if not self._fernet:
            print("Password manager not initialized")
            return False
        
        try:
            # Load existing passwords
            passwords = self._load_passwords()
            
            # Store new password
            password_entry = {
                "username": username,
                "password": password,
                "created": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            passwords[service] = password_entry
            
            # Encrypt and save
            encrypted_data = self._fernet.encrypt(json.dumps(passwords).encode())
            self.password_file.write_bytes(encrypted_data)
            self.password_file.chmod(0o600)
            
            self._log_audit("STORE", f"Password stored for service: {service}")
            return True
        except Exception as e:
            print(f"Failed to store password: {e}")
            return False
    
    def retrieve_password(self, service: str) -> Optional[Tuple[str, str]]:
        """Retrieve password for a service."""
        if not self._fernet:
            print("Password manager not initialized")
            return None
        
        try:
            passwords = self._load_passwords()
            if service in passwords:
                entry = passwords[service]
                self._log_audit("RETRIEVE", f"Password retrieved for service: {service}")
                return entry["username"], entry["password"]
            else:
                print(f"No password found for service: {service}")
                return None
        except Exception as e:
            print(f"Failed to retrieve password: {e}")
            return None
    
    def list_services(self) -> List[str]:
        """List all services with stored passwords."""
        if not self._fernet:
            return []
        
        try:
            passwords = self._load_passwords()
            return list(passwords.keys())
        except Exception:
            return []
    
    def _load_passwords(self) -> Dict:
        """Load and decrypt password storage."""
        if not self.password_file.exists():
            return {}
        
        try:
            encrypted_data = self.password_file.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception:
            return {}
    
    def backup_passwords(self, backup_path: str) -> bool:
        """Create encrypted backup of passwords."""
        try:
            if self.password_file.exists():
                backup_file = Path(backup_path)
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy encrypted file
                backup_file.write_bytes(self.password_file.read_bytes())
                backup_file.chmod(0o600)
                
                self._log_audit("BACKUP", f"Passwords backed up to: {backup_path}")
                return True
            return False
        except Exception as e:
            print(f"Backup failed: {e}")
            return False

class BitwardenManager:
    """Bitwarden CLI integration for enterprise password management."""
    
    def __init__(self):
        self.cli_available = self._check_cli_available()
        self.session_token = None
    
    def _check_cli_available(self) -> bool:
        """Check if Bitwarden CLI is installed."""
        try:
            result = subprocess.run(["bw", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def login(self, email: str, password: str, server: str = None) -> bool:
        """Login to Bitwarden."""
        if not self.cli_available:
            print("Bitwarden CLI not available. Install from: https://bitwarden.com/help/cli/")
            return False
        
        try:
            cmd = ["bw", "login", email, password]
            if server:
                cmd.extend(["--server", server])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("Bitwarden login successful")
                return self.unlock(password)
            else:
                print(f"Bitwarden login failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"Bitwarden login error: {e}")
            return False
    
    def unlock(self, password: str) -> bool:
        """Unlock Bitwarden vault."""
        try:
            result = subprocess.run(
                ["bw", "unlock", password], 
                capture_output=True, text=True
            )
            if result.returncode == 0:
                # Extract session token from output
                for line in result.stdout.split('\n'):
                    if 'BW_SESSION' in line and 'export' in line:
                        # Extract token from: export BW_SESSION="token"
                        self.session_token = line.split('"')[1]
                        break
                
                if self.session_token:
                    print("Bitwarden vault unlocked")
                    return True
                else:
                    print("Failed to extract session token")
                    return False
            else:
                print(f"Bitwarden unlock failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"Bitwarden unlock error: {e}")
            return False
    
    def store_password(self, name: str, username: str, password: str, notes: str = "", folder: str = "Local AI") -> bool:
        """Store password in Bitwarden."""
        if not self.session_token:
            print("Bitwarden not unlocked")
            return False
        
        try:
            # Create item JSON
            item = {
                "object": "item",
                "type": 1,  # Login type
                "name": name,
                "notes": notes,
                "login": {
                    "username": username,
                    "password": password
                }
            }
            
            # Create item via CLI
            result = subprocess.run(
                ["bw", "create", "item", json.dumps(item)],
                env={**os.environ, "BW_SESSION": self.session_token},
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                print(f"Password stored in Bitwarden: {name}")
                return True
            else:
                print(f"Failed to store in Bitwarden: {result.stderr}")
                return False
        except Exception as e:
            print(f"Bitwarden store error: {e}")
            return False
    
    def retrieve_password(self, name: str) -> Optional[Tuple[str, str]]:
        """Retrieve password from Bitwarden."""
        if not self.session_token:
            print("Bitwarden not unlocked")
            return None
        
        try:
            # Search for item
            result = subprocess.run(
                ["bw", "get", "item", name],
                env={**os.environ, "BW_SESSION": self.session_token},
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                item = json.loads(result.stdout)
                login = item.get("login", {})
                return login.get("username"), login.get("password")
            else:
                print(f"Item not found in Bitwarden: {name}")
                return None
        except Exception as e:
            print(f"Bitwarden retrieve error: {e}")
            return None
    
    def sync(self) -> bool:
        """Sync with Bitwarden server."""
        if not self.session_token:
            return False
        
        try:
            result = subprocess.run(
                ["bw", "sync"],
                env={**os.environ, "BW_SESSION": self.session_token},
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False

class UnifiedPasswordManager:
    """Unified interface for both local and Bitwarden password management."""
    
    def __init__(self, prefer_bitwarden: bool = False):
        self.local_manager = SecurePasswordManager()
        self.bitwarden_manager = BitwardenManager()
        self.prefer_bitwarden = prefer_bitwarden and self.bitwarden_manager.cli_available
    
    def initialize(self, bitwarden_email: str = None, bitwarden_password: str = None, 
                   master_password: str = None) -> bool:
        """Initialize password management systems."""
        # Always initialize local manager
        local_success = self.local_manager.initialize(master_password)
        
        bitwarden_success = False
        if self.prefer_bitwarden and bitwarden_email and bitwarden_password:
            bitwarden_success = self.bitwarden_manager.login(bitwarden_email, bitwarden_password)
        
        return local_success or bitwarden_success
    
    def store_password(self, service: str, username: str, password: str, 
                      metadata: Dict = None) -> bool:
        """Store password using preferred method."""
        success = False
        
        # Try Bitwarden first if preferred
        if self.prefer_bitwarden and self.bitwarden_manager.session_token:
            success = self.bitwarden_manager.store_password(
                f"LocalAI-{service}", username, password, 
                notes=json.dumps(metadata) if metadata else ""
            )
        
        # Always store locally as backup
        local_success = self.local_manager.store_password(service, username, password, metadata)
        
        return success or local_success
    
    def retrieve_password(self, service: str) -> Optional[Tuple[str, str]]:
        """Retrieve password using preferred method."""
        # Try Bitwarden first if preferred
        if self.prefer_bitwarden and self.bitwarden_manager.session_token:
            result = self.bitwarden_manager.retrieve_password(f"LocalAI-{service}")
            if result:
                return result
        
        # Fallback to local storage
        return self.local_manager.retrieve_password(service)
    
    def generate_and_store_env_passwords(self, env_file: str = ".env") -> bool:
        """Generate secure passwords for all environment variables and store them."""
        from .enhanced_env_generator import CredentialValidator
        
        validator = CredentialValidator()
        
        # Define services that need passwords
        services = {
            'postgres': ('postgres', validator.generate_postgres_password(32)),
            'neo4j': ('neo4j', validator.generate_postgres_password(24)),
            'grafana': ('admin', validator.generate_secure_string(24)),
            'n8n': ('n8n', validator.generate_secure_string(24)),
            'flowise': ('flowise', validator.generate_secure_string(24)),
        }
        
        # Store all passwords
        success_count = 0
        for service, (username, password) in services.items():
            if self.store_password(service, username, password, {
                'generated': datetime.now().isoformat(),
                'env_file': env_file,
                'service_type': 'local_ai_package'
            }):
                success_count += 1
        
        print(f"Successfully stored {success_count}/{len(services)} passwords")
        return success_count == len(services)

def main():
    """CLI interface for password management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Local AI Package Password Manager")
    parser.add_argument("--bitwarden", action="store_true", help="Use Bitwarden for storage")
    parser.add_argument("--generate-env", action="store_true", help="Generate and store environment passwords")
    parser.add_argument("--list", action="store_true", help="List stored services")
    parser.add_argument("--store", nargs=3, metavar=("SERVICE", "USERNAME", "PASSWORD"), 
                       help="Store password for service")
    parser.add_argument("--retrieve", metavar="SERVICE", help="Retrieve password for service")
    parser.add_argument("--backup", metavar="PATH", help="Backup passwords to path")
    
    args = parser.parse_args()
    
    # Initialize password manager
    manager = UnifiedPasswordManager(prefer_bitwarden=args.bitwarden)
    
    if args.bitwarden:
        email = input("Bitwarden email: ")
        password = getpass.getpass("Bitwarden password: ")
        manager.initialize(bitwarden_email=email, bitwarden_password=password)
    else:
        manager.initialize()
    
    # Execute requested action
    if args.generate_env:
        manager.generate_and_store_env_passwords()
    elif args.list:
        services = manager.local_manager.list_services()
        print("Stored services:", ", ".join(services))
    elif args.store:
        service, username, password = args.store
        success = manager.store_password(service, username, password)
        print(f"Password {'stored' if success else 'failed to store'} for {service}")
    elif args.retrieve:
        result = manager.retrieve_password(args.retrieve)
        if result:
            username, password = result
            print(f"Service: {args.retrieve}")
            print(f"Username: {username}")
            print(f"Password: {password}")
        else:
            print(f"No password found for {args.retrieve}")
    elif args.backup:
        success = manager.local_manager.backup_passwords(args.backup)
        print(f"Backup {'successful' if success else 'failed'}")

if __name__ == "__main__":
    main()