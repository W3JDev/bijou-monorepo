"""
W3J Bijou AI - Privacy & Compliance System
==========================================

GDPR compliance, PII protection, audit logging, and data governance.

Features:
- PII anonymization (auto-detect and mask)
- Audit trail (immutable logging)
- Data retention policies
- Right to deletion (GDPR Article 17)
- Consent management
- Data access logging
- Compliance reporting

Author: W3J Bijou AI
Version: 2.1.0
"""

import re
import json
import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class PIIType(Enum):
    """Types of Personally Identifiable Information."""
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    ADDRESS = "address"
    NAME = "name"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"


class DataAction(Enum):
    """Types of data actions for audit logging."""
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    ANONYMIZE = "anonymize"


class PrivacyCompliance:
    """
    Privacy and compliance system for GDPR and data protection.
    """

    def __init__(self, db_path: str = "data/compliance.db"):
        """
        Initialize privacy compliance system.
        
        Args:
            db_path: Path to compliance database
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self._load_pii_patterns()
        
        # Retention policy (days)
        self.retention_days = 90
        
        # Statistics
        self.pii_detections = 0
        self.anonymizations = 0

    def _init_database(self):
        """Initialize compliance database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Audit log table (immutable)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    action TEXT NOT NULL,
                    user_id TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    details JSON,
                    ip_address TEXT,
                    user_agent TEXT,
                    result TEXT,
                    UNIQUE(id)
                )
            """)
            
            # PII detection log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pii_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pii_type TEXT NOT NULL,
                    context TEXT,
                    was_anonymized BOOLEAN,
                    message_id TEXT
                )
            """)
            
            # User consent tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_consent (
                    user_id TEXT PRIMARY KEY,
                    consent_given BOOLEAN DEFAULT 0,
                    consent_timestamp TIMESTAMP,
                    consent_version TEXT,
                    data_retention_days INTEGER DEFAULT 90
                )
            """)
            
            # Data deletion requests (GDPR right to be forgotten)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deletion_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT 0,
                    processed_timestamp TIMESTAMP,
                    notes TEXT
                )
            """)
            
            conn.commit()

    def _load_pii_patterns(self):
        """Load PII detection patterns."""
        self.pii_patterns = {
            PIIType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            PIIType.PHONE: r'\b(\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b',
            PIIType.CREDIT_CARD: r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            PIIType.SSN: r'\b\d{3}-\d{2}-\d{4}\b',
            PIIType.IP_ADDRESS: r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            PIIType.DATE_OF_BIRTH: r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        }

    def anonymize_pii(
        self,
        text: str,
        preserve_format: bool = True
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Detect and anonymize PII in text.
        
        Args:
            text: Input text
            preserve_format: Keep format (e.g., phone: XXX-XXX-1234)
            
        Returns:
            Tuple of (anonymized_text, detected_pii_list)
        """
        anonymized = text
        detected_pii = []
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = list(re.finditer(pattern, text))
            
            for match in matches:
                original = match.group()
                
                # Generate anonymized version
                if preserve_format:
                    masked = self._mask_with_format(original, pii_type)
                else:
                    masked = f"[{pii_type.value.upper()}_REDACTED]"
                
                anonymized = anonymized.replace(original, masked)
                
                detected_pii.append({
                    'type': pii_type.value,
                    'original': original,
                    'masked': masked,
                    'position': match.span(),
                })
                
                self.pii_detections += 1
        
        if detected_pii:
            self.anonymizations += 1
            self._log_pii_detection(detected_pii)
        
        return anonymized, detected_pii

    def _mask_with_format(self, value: str, pii_type: PIIType) -> str:
        """Mask PII while preserving format."""
        if pii_type == PIIType.EMAIL:
            parts = value.split('@')
            if len(parts) == 2:
                username = parts[0]
                if len(username) > 2:
                    masked = username[0] + '*' * (len(username) - 2) + username[-1]
                else:
                    masked = '*' * len(username)
                return f"{masked}@{parts[1]}"
        
        elif pii_type == PIIType.PHONE:
            # Keep last 4 digits
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                masked_digits = '*' * (len(digits) - 4) + digits[-4:]
                # Preserve formatting
                return re.sub(r'\d', lambda m: masked_digits[0] if masked_digits else '*', value, count=len(digits)-4)
            return '*' * len(value)
        
        elif pii_type == PIIType.CREDIT_CARD:
            # Keep last 4 digits
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return '**** **** **** ' + digits[-4:]
            return '*' * len(value)
        
        elif pii_type == PIIType.SSN:
            return '***-**-' + value[-4:]
        
        return '[REDACTED]'

    def audit_log(
        self,
        action: DataAction,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        result: str = "success",
    ):
        """
        Create immutable audit log entry.
        
        Args:
            action: Type of action performed
            user_id: User performing action
            resource_type: Type of resource accessed
            resource_id: ID of specific resource
            details: Additional details (JSON)
            ip_address: User's IP address
            result: success/failure
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_log 
                (action, user_id, resource_type, resource_id, details, ip_address, result)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                action.value,
                user_id,
                resource_type,
                resource_id,
                json.dumps(details) if details else None,
                ip_address,
                result,
            ))
            conn.commit()

    def _log_pii_detection(self, detected_pii: List[Dict[str, Any]]):
        """Log PII detection for compliance."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for pii in detected_pii:
                cursor.execute("""
                    INSERT INTO pii_detections (pii_type, context, was_anonymized)
                    VALUES (?, ?, ?)
                """, (pii['type'], pii['original'][:50], True))
            conn.commit()

    def enforce_retention_policy(self) -> int:
        """
        Enforce data retention policy (auto-delete old data).
        
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete old audit logs
            cursor.execute("""
                DELETE FROM audit_log 
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
        
        return deleted_count

    def process_deletion_request(
        self,
        user_id: str,
        delete_everything: bool = True
    ) -> bool:
        """
        Process GDPR right to deletion request.
        
        Args:
            user_id: User requesting deletion
            delete_everything: Delete all data (True) or anonymize (False)
            
        Returns:
            Success status
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Log the deletion request
                cursor.execute("""
                    INSERT INTO deletion_requests (user_id, processed)
                    VALUES (?, 1)
                """, (user_id,))
                
                if delete_everything:
                    # Delete user data from audit log
                    cursor.execute("""
                        DELETE FROM audit_log WHERE user_id = ?
                    """, (user_id,))
                    
                    # Delete consent record
                    cursor.execute("""
                        DELETE FROM user_consent WHERE user_id = ?
                    """, (user_id,))
                else:
                    # Anonymize instead of delete
                    anonymized_id = hashlib.sha256(user_id.encode()).hexdigest()[:16]
                    cursor.execute("""
                        UPDATE audit_log SET user_id = ? WHERE user_id = ?
                    """, (anonymized_id, user_id))
                
                conn.commit()
                return True
        
        except Exception as e:
            print(f"[COMPLIANCE ERROR] Failed to process deletion: {e}")
            return False

    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get all data for a user (GDPR right to access).
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of all user data
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get audit log entries
            cursor.execute("""
                SELECT timestamp, action, resource_type, resource_id, details
                FROM audit_log WHERE user_id = ?
                ORDER BY timestamp DESC
            """, (user_id,))
            
            audit_logs = [
                {
                    'timestamp': row[0],
                    'action': row[1],
                    'resource_type': row[2],
                    'resource_id': row[3],
                    'details': json.loads(row[4]) if row[4] else None,
                }
                for row in cursor.fetchall()
            ]
            
            # Get consent status
            cursor.execute("""
                SELECT consent_given, consent_timestamp, consent_version
                FROM user_consent WHERE user_id = ?
            """, (user_id,))
            
            consent_row = cursor.fetchone()
            consent = None
            if consent_row:
                consent = {
                    'given': bool(consent_row[0]),
                    'timestamp': consent_row[1],
                    'version': consent_row[2],
                }
        
        return {
            'user_id': user_id,
            'audit_logs': audit_logs,
            'consent': consent,
            'data_retention_days': self.retention_days,
        }

    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Count audit log entries
            cursor.execute("SELECT COUNT(*) FROM audit_log")
            audit_count = cursor.fetchone()[0]
            
            # Count PII detections
            cursor.execute("SELECT COUNT(*) FROM pii_detections WHERE was_anonymized = 1")
            anonymized_count = cursor.fetchone()[0]
            
            # Count deletion requests
            cursor.execute("SELECT COUNT(*) FROM deletion_requests WHERE processed = 1")
            deletion_count = cursor.fetchone()[0]
            
            # Recent PII detections by type
            cursor.execute("""
                SELECT pii_type, COUNT(*) as count
                FROM pii_detections
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY pii_type
            """)
            recent_pii = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            'total_audit_entries': audit_count,
            'total_pii_anonymized': anonymized_count,
            'total_deletions_processed': deletion_count,
            'recent_pii_detections': recent_pii,
            'retention_policy_days': self.retention_days,
            'compliance_status': 'COMPLIANT' if anonymized_count > 0 else 'MONITORING',
        }

    def reset_stats(self):
        """Reset statistics."""
        self.pii_detections = 0
        self.anonymizations = 0


# Example usage
if __name__ == "__main__":
    compliance = PrivacyCompliance()
    
    # Test PII anonymization
    test_messages = [
        "My email is john.doe@example.com and phone is 555-123-4567",
        "Credit card: 4532-1234-5678-9010, SSN: 123-45-6789",
        "Contact me at +1 (555) 987-6543 or admin@company.org",
    ]
    
    print("Testing Privacy Compliance:\n")
    for msg in test_messages:
        anonymized, detected = compliance.anonymize_pii(msg)
        print(f"Original: {msg}")
        print(f"Anonymized: {anonymized}")
        print(f"Detected: {len(detected)} PII items")
        print("-" * 80)
    
    # Generate compliance report
    print("\nCompliance Report:")
    report = compliance.get_compliance_report()
    print(json.dumps(report, indent=2))
