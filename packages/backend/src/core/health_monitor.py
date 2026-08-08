"""
W3J Bijou AI - Health Check & Monitoring System
================================================

Provides comprehensive health monitoring for production deployment.

Features:
- Health check endpoint (/api/health)
- Component status checking
- Automatic recovery mechanisms
- Metrics collection
- Alerting system

Author: W3J Bijou AI
Version: 2.1.0
"""

import os
import time
import sqlite3
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ComponentStatus(Enum):
    """Health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthMonitor:
    """
    Monitors health of all Bijou AI components.

    Checks:
    - WhatsApp Bridge connectivity
    - Gemini API availability
    - Database connectivity
    - Google Sheets API
    - Memory usage
    - Response time
    """

    def __init__(
        self,
        bridge_url: str = None,
        bridge_db_path: str = None,
        bijou_db_path: str = None,
        gemini_api_key: Optional[str] = None,
    ):
        self.bridge_url = bridge_url or os.getenv("BRIDGE_URL", "http://localhost:8080")
        self.bridge_db_path = bridge_db_path or os.getenv("BRIDGE_DB_PATH", "../whatsapp-bridge/store/messages.db")
        self.bijou_db_path = bijou_db_path or os.getenv("BIJOU_DB_PATH", "data/bijou.db")
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

        # Track health history
        self.health_history = []
        self.max_history = 100

        # Alert thresholds
        self.response_time_threshold = 10.0  # seconds
        self.memory_usage_threshold = 0.9  # 90%

    def check_bridge_connectivity(self) -> Dict[str, Any]:
        """
        Check if WhatsApp bridge is reachable.

        Returns:
            Status dict with connectivity info
        """
        start_time = time.time()

        try:
            # Try to reach bridge health endpoint (if exists) or root
            response = requests.get(f"{self.bridge_url}/health", timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                status = ComponentStatus.HEALTHY
            else:
                status = ComponentStatus.DEGRADED

            return {
                "component": "whatsapp_bridge",
                "status": status.value,
                "reachable": True,
                "response_time": round(response_time, 3),
                "status_code": response.status_code,
                "message": "Bridge is reachable",
            }

        except requests.exceptions.ConnectionError:
            return {
                "component": "whatsapp_bridge",
                "status": ComponentStatus.UNHEALTHY.value,
                "reachable": False,
                "response_time": None,
                "status_code": None,
                "message": "Bridge is not reachable - is it running?",
            }
        except Exception as e:
            return {
                "component": "whatsapp_bridge",
                "status": ComponentStatus.UNKNOWN.value,
                "reachable": False,
                "response_time": None,
                "error": str(e),
                "message": f"Error checking bridge: {e}",
            }

    def check_bridge_database(self) -> Dict[str, Any]:
        """
        Check if bridge database is accessible and has data.

        Returns:
            Status dict with database info
        """
        try:
            if not os.path.exists(self.bridge_db_path):
                return {
                    "component": "bridge_database",
                    "status": ComponentStatus.UNHEALTHY.value,
                    "exists": False,
                    "message": f"Database not found at {self.bridge_db_path}",
                }

            # Try to connect and query
            conn = sqlite3.connect(self.bridge_db_path, timeout=5)
            cursor = conn.cursor()

            # Check if messages table exists
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='messages'
            """)
            table_exists = cursor.fetchone()[0] > 0

            if not table_exists:
                conn.close()
                return {
                    "component": "bridge_database",
                    "status": ComponentStatus.DEGRADED.value,
                    "exists": True,
                    "table_exists": False,
                    "message": "Database exists but messages table not found",
                }

            # Get message count
            cursor.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]

            # Get latest message timestamp
            cursor.execute("""
                SELECT timestamp FROM messages 
                ORDER BY timestamp DESC LIMIT 1
            """)
            result = cursor.fetchone()
            latest_message = result[0] if result else None

            conn.close()

            return {
                "component": "bridge_database",
                "status": ComponentStatus.HEALTHY.value,
                "exists": True,
                "table_exists": True,
                "message_count": message_count,
                "latest_message": latest_message,
                "message": "Database is accessible and working",
            }

        except Exception as e:
            return {
                "component": "bridge_database",
                "status": ComponentStatus.UNKNOWN.value,
                "error": str(e),
                "message": f"Error accessing database: {e}",
            }

    def check_bijou_database(self) -> Dict[str, Any]:
        """
        Check if Bijou memory database is accessible.

        Returns:
            Status dict with database info
        """
        try:
            if not os.path.exists(self.bijou_db_path):
                # Database doesn't exist yet - will be created on first use
                return {
                    "component": "bijou_database",
                    "status": ComponentStatus.HEALTHY.value,
                    "exists": False,
                    "message": "Database will be created on first message",
                }

            conn = sqlite3.connect(self.bijou_db_path, timeout=5)
            cursor = conn.cursor()

            # Get conversation count
            cursor.execute("""
                SELECT COUNT(DISTINCT chat_jid) FROM conversation_memory
            """)
            conversation_count = cursor.fetchone()[0]

            # Get total messages
            cursor.execute("SELECT COUNT(*) FROM conversation_memory")
            total_messages = cursor.fetchone()[0]

            conn.close()

            return {
                "component": "bijou_database",
                "status": ComponentStatus.HEALTHY.value,
                "exists": True,
                "conversations": conversation_count,
                "total_messages": total_messages,
                "message": "Memory database is working",
            }

        except Exception as e:
            return {
                "component": "bijou_database",
                "status": ComponentStatus.UNKNOWN.value,
                "error": str(e),
                "message": f"Error accessing database: {e}",
            }

    def check_gemini_api(self) -> Dict[str, Any]:
        """
        Check if Gemini API is accessible.

        Returns:
            Status dict with API info
        """
        if not self.gemini_api_key:
            return {
                "component": "gemini_api",
                "status": ComponentStatus.UNHEALTHY.value,
                "configured": False,
                "message": "Gemini API key not configured",
            }

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            # Simple test prompt
            start_time = time.time()
            response = model.generate_content("Say 'OK' if you're working")
            response_time = time.time() - start_time

            if response.text:
                return {
                    "component": "gemini_api",
                    "status": ComponentStatus.HEALTHY.value,
                    "configured": True,
                    "reachable": True,
                    "response_time": round(response_time, 3),
                    "message": "Gemini API is working",
                }
            else:
                return {
                    "component": "gemini_api",
                    "status": ComponentStatus.DEGRADED.value,
                    "configured": True,
                    "reachable": True,
                    "message": "Gemini API reachable but response empty",
                }

        except Exception as e:
            return {
                "component": "gemini_api",
                "status": ComponentStatus.UNHEALTHY.value,
                "configured": True,
                "reachable": False,
                "error": str(e),
                "message": f"Gemini API error: {e}",
            }

    def check_google_sheets(self) -> Dict[str, Any]:
        """
        Check if Google Sheets integration is available.

        Returns:
            Status dict with Sheets info
        """
        try:
            # Check if credentials file exists
            creds_path = os.getenv(
                "GOOGLE_CREDENTIALS_PATH",
                "credentials/client_secret_698028267158-70rv95bqskigdhlgd84df7igaitjpbbu.apps.googleusercontent.com.json"
            )
            if not os.path.exists(creds_path):
                return {
                    "component": "google_sheets",
                    "status": ComponentStatus.DEGRADED.value,
                    "configured": False,
                    "message": "Google Sheets credentials not found (optional)",
                }

            # Try to import and test
            from integrations.sheets import GoogleSheetsRAG

            sheets = GoogleSheetsRAG()
            if sheets.service:
                return {
                    "component": "google_sheets",
                    "status": ComponentStatus.HEALTHY.value,
                    "configured": True,
                    "authenticated": True,
                    "message": "Google Sheets is working",
                }
            else:
                return {
                    "component": "google_sheets",
                    "status": ComponentStatus.DEGRADED.value,
                    "configured": True,
                    "authenticated": False,
                    "message": "Sheets configured but not authenticated",
                }

        except Exception as e:
            return {
                "component": "google_sheets",
                "status": ComponentStatus.DEGRADED.value,
                "error": str(e),
                "message": f"Sheets error (non-critical): {e}",
            }

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system resource metrics.

        Returns:
            System metrics dict
        """
        try:
            import psutil

            process = psutil.Process()

            return {
                "cpu_percent": round(process.cpu_percent(interval=0.1), 2),
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "memory_percent": round(process.memory_percent(), 2),
                "threads": process.num_threads(),
                "uptime_seconds": round(time.time() - process.create_time(), 2),
            }
        except ImportError:
            return {
                "error": "psutil not installed",
                "message": "Install psutil for system metrics",
            }
        except Exception as e:
            return {"error": str(e)}

    def run_full_health_check(self) -> Dict[str, Any]:
        """
        Run comprehensive health check on all components.

        Returns:
            Complete health status dict
        """
        start_time = time.time()

        # Check all components
        bridge_status = self.check_bridge_connectivity()
        bridge_db_status = self.check_bridge_database()
        bijou_db_status = self.check_bijou_database()
        gemini_status = self.check_gemini_api()
        sheets_status = self.check_google_sheets()
        system_metrics = self.get_system_metrics()

        # Determine overall status
        statuses = [
            bridge_status["status"],
            bridge_db_status["status"],
            bijou_db_status["status"],
            gemini_status["status"],
            # Sheets is optional, don't count for overall health
        ]

        if any(s == ComponentStatus.UNHEALTHY.value for s in statuses):
            overall_status = ComponentStatus.UNHEALTHY.value
        elif any(s == ComponentStatus.DEGRADED.value for s in statuses):
            overall_status = ComponentStatus.DEGRADED.value
        elif any(s == ComponentStatus.UNKNOWN.value for s in statuses):
            overall_status = ComponentStatus.UNKNOWN.value
        else:
            overall_status = ComponentStatus.HEALTHY.value

        check_time = time.time() - start_time

        health_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "check_duration": round(check_time, 3),
            "components": {
                "whatsapp_bridge": bridge_status,
                "bridge_database": bridge_db_status,
                "bijou_database": bijou_db_status,
                "gemini_api": gemini_status,
                "google_sheets": sheets_status,
            },
            "system_metrics": system_metrics,
            "version": "2.1.0",
        }

        # Store in history
        self.health_history.append(health_report)
        if len(self.health_history) > self.max_history:
            self.health_history.pop(0)

        return health_report

    def get_health_history(self, limit: int = 10) -> list:
        """
        Get recent health check history.

        Args:
            limit: Number of recent checks to return

        Returns:
            List of recent health reports
        """
        return self.health_history[-limit:]

    def print_health_report(self, report: Dict[str, Any] = None):
        """
        Print formatted health report to console.

        Args:
            report: Health report dict (if None, runs new check)
        """
        if report is None:
            report = self.run_full_health_check()

        print("\n" + "=" * 70)
        print("BIJOU AI HEALTH CHECK")
        print("=" * 70)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Overall Status: {report['overall_status'].upper()}")
        print(f"Check Duration: {report['check_duration']}s")
        print(f"Version: {report['version']}")
        print("=" * 70)

        print("\nCOMPONENT STATUS:")
        for component_name, component_data in report["components"].items():
            status = component_data["status"]
            # Use ASCII-safe symbols for Windows compatibility
            symbol = {
                "healthy": "[OK]",
                "degraded": "[!]",
                "unhealthy": "[X]",
                "unknown": "[?]",
            }.get(status, "[?]")

            print(
                f"  {symbol} {component_name.replace('_', ' ').title()}: {status.upper()}"
            )
            print(f"      {component_data.get('message', 'No details')}")

        print("\nSYSTEM METRICS:")
        metrics = report["system_metrics"]
        if "error" not in metrics:
            print(f"  CPU: {metrics.get('cpu_percent', 'N/A')}%")
            print(
                f"  Memory: {metrics.get('memory_mb', 'N/A')} MB ({metrics.get('memory_percent', 'N/A')}%)"
            )
            print(f"  Threads: {metrics.get('threads', 'N/A')}")
            print(f"  Uptime: {metrics.get('uptime_seconds', 'N/A')}s")
        else:
            print(f"  {metrics.get('message', 'Metrics unavailable')}")

        print("=" * 70 + "\n")


# CLI entry point for standalone health checks
if __name__ == "__main__":
    import sys

    print("Running Bijou AI Health Check...\n")

    monitor = HealthMonitor()
    report = monitor.run_full_health_check()
    monitor.print_health_report(report)

    # Exit with appropriate code
    if report["overall_status"] == ComponentStatus.HEALTHY.value:
        print("Status: All systems operational [OK]")
        sys.exit(0)
    elif report["overall_status"] == ComponentStatus.DEGRADED.value:
        print("Status: Some components degraded [!]")
        sys.exit(1)
    else:
        print("Status: Critical issues detected [X]")
        sys.exit(2)
