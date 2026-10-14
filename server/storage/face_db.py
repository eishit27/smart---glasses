"""
Face database persistence module.
Handles saving and loading known faces encodings and metadata.
"""

import json
import logging
import os
import shutil
from typing import Dict, Any

logger = logging.getLogger(__name__)

class FaceDatabase:
    """Manages the face database on disk."""

    @staticmethod
    def save_db(encodings_data: Dict[str, Any], path: str):
        """
        Save face encodings and metadata to disk.
        
        Args:
            encodings_data (dict): Dictionary mapping face IDs/names to data.
            path (str): Path to the JSON file.
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            # Use SecurityManager for AES-256-GCM encrypted persistence
            from security.crypto import SecurityManager
            sec_mgr = SecurityManager()

            json_bytes = json.dumps(encodings_data, indent=2).encode('utf-8')
            encrypted_payload = sec_mgr.encrypt_data(json_bytes)
            
            # Write to temporary file first, then atomic rename
            temp_path = f"{path}.tmp"
            with open(temp_path, 'wb') as f:
                f.write(encrypted_payload)
            os.replace(temp_path, path)
            logger.info(f"Successfully saved encrypted face database to {path}")
        except Exception as e:
            logger.error(f"Failed to save face database to {path}: {e}")
            raise

    @staticmethod
    def load_db(path: str) -> Dict[str, Any]:
        """
        Load face encodings from disk, decrypting if encrypted.
        
        Args:
            path (str): Path to the database file.
            
        Returns:
            dict: The loaded database, or an empty dict if it doesn't exist.
        """
        if not os.path.exists(path):
            logger.info(f"Face database {path} not found. Returning empty database.")
            return {}
            
        try:
            from security.crypto import SecurityManager
            sec_mgr = SecurityManager()

            with open(path, 'rb') as f:
                raw_bytes = f.read()

            # Attempt decryption first; if it's plaintext JSON (legacy), fallback gracefully
            try:
                decrypted_bytes = sec_mgr.decrypt_data(raw_bytes)
                data = json.loads(decrypted_bytes.decode('utf-8'))
            except Exception:
                # Legacy plaintext JSON fallback
                data = json.loads(raw_bytes.decode('utf-8'))

            logger.info(f"Successfully loaded and decrypted face database from {path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Face database {path} is corrupted: {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load face database from {path}: {e}")
            return {}

    @staticmethod
    def export_db(path: str, export_path: str):
        """
        Backup/export the face database to another location.
        
        Args:
            path (str): Current database path.
            export_path (str): Destination path for the backup.
        """
        try:
            if not os.path.exists(path):
                logger.warning(f"Cannot export: database {path} does not exist.")
                return
                
            os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)
            shutil.copy2(path, export_path)
            logger.info(f"Successfully exported face database to {export_path}")
        except Exception as e:
            logger.error(f"Failed to export face database: {e}")
            raise
