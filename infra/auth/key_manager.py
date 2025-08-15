"""
Service Authentication Key Management

Manages RSA key pairs for service-to-service authentication.
Backend services get public/private key pairs from MAS and use them for JWT signing.
"""

import os
import json
from datetime import timedelta
from typing import Dict, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from src.utils import get_current_datetime, format_timestamp, format_datetime


class ServiceKeyManager:
    """Manages RSA key pairs for service authentication."""
    
    def __init__(self, storage_path: str = "data/service_keys"):
        """
        Initialize key manager.
        
        Args:
            storage_path: Directory to store key pairs
        """
        self.storage_path = storage_path
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self):
        """Ensure storage directory exists."""
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _get_key_file_path(self, app_key: str) -> str:
        """Get file path for service key storage."""
        return os.path.join(self.storage_path, f"{app_key}.json")
    
    def generate_key_pair(self, app_key: str, ttl_days: int = 30) -> Dict:
        """
        Generate new RSA key pair for service.
        
        Args:
            app_key: Service app key identifier
            ttl_days: Key pair time-to-live in days
            
        Returns:
            Dict with public key, private key, and metadata
        """
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Create key pair data
        now = get_current_datetime()
        expires_at = now + timedelta(days=ttl_days)
        
        key_data = {
            "app_key": app_key,
            "public_key": public_pem.decode('utf-8'),
            "private_key": private_pem.decode('utf-8'),
            "created_at": format_timestamp(now),
            "expires_at": format_timestamp(expires_at),
            "status": "active"
        }
        
        # Store key pair
        key_file = self._get_key_file_path(app_key)
        with open(key_file, 'w') as f:
            json.dump(key_data, f, indent=2)
        
        return {
            "app_key": app_key,
            "public_key": key_data["public_key"],
            "private_key": key_data["private_key"],
            "created_at": key_data["created_at"],
            "expires_at": key_data["expires_at"],
            "algorithm": "RS256"
        }
    
    def get_public_key(self, app_key: str) -> Optional[str]:
        """
        Get public key for service verification.
        
        Args:
            app_key: Service app key identifier
            
        Returns:
            Public key PEM string or None if not found/expired
        """
        key_file = self._get_key_file_path(app_key)
        if not os.path.exists(key_file):
            return None
        
        try:
            with open(key_file, 'r') as f:
                key_data = json.load(f)
            
            # Check expiration
            expires_at = format_datetime(key_data["expires_at"])
            if get_current_datetime() > expires_at:
                return None
            
            return key_data["public_key"]
        except Exception:
            return None
    
    def is_key_valid(self, app_key: str) -> bool:
        """
        Check if key pair is valid and not expired.
        
        Args:
            app_key: Service app key identifier
            
        Returns:
            True if key is valid, False otherwise
        """
        return self.get_public_key(app_key) is not None
    
    def revoke_key(self, app_key: str) -> bool:
        """
        Revoke key pair for service.
        
        Args:
            app_key: Service app key identifier
            
        Returns:
            True if revoked successfully, False if not found
        """
        key_file = self._get_key_file_path(app_key)
        if not os.path.exists(key_file):
            return False
        
        try:
            with open(key_file, 'r') as f:
                key_data = json.load(f)
            
            key_data["status"] = "revoked"
            key_data["revoked_at"] = get_current_datetime().isoformat()
            
            with open(key_file, 'w') as f:
                json.dump(key_data, f, indent=2)
            
            return True
        except Exception:
            return False
    
    def cleanup_expired_keys(self) -> int:
        """
        Remove expired key files.
        
        Returns:
            Number of files cleaned up
        """
        cleaned = 0
        for filename in os.listdir(self.storage_path):
            if not filename.endswith('.json'):
                continue
            
            key_file = os.path.join(self.storage_path, filename)
            try:
                with open(key_file, 'r') as f:
                    key_data = json.load(f)
                
                expires_at = format_datetime(key_data["expires_at"])
                if get_current_datetime() > expires_at:
                    os.remove(key_file)
                    cleaned += 1
            except Exception:
                # Remove corrupted files
                os.remove(key_file)
                cleaned += 1
        
        return cleaned


# Global key manager instance
key_manager = ServiceKeyManager()