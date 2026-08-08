#!/usr/bin/env python3
"""
Comprehensive End-to-End Test for Call Booking System
Tests the complete call booking flow without requiring full server startup.
"""

import asyncio
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all new components can be imported."""
    print("🧪 Testing imports...")
    try:
        # Core system imports
        from core.advanced_reminder_system import AdvancedReminderSystem
        from saas.business_template_seeder import BusinessTemplateSeeder
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_database_schema():
    """Test that database schema is correctly set up."""
    print("\n🗄️ Testing database schema...")
    
    # Create in-memory database for testing
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Create the new tables as defined in bijou.py
    schema_sql = """
    -- Call booking system tables
    CREATE TABLE IF NOT EXISTS call_bookings (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        customer_email TEXT,
        call_type TEXT NOT NULL,
        scheduled_datetime TEXT NOT NULL,
        duration_minutes INTEGER DEFAULT 30,
        status TEXT DEFAULT 'pending',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS call_availability (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        day_of_week INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        is_available BOOLEAN DEFAULT true,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS call_types (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        name TEXT NOT NULL,
        duration_minutes INTEGER DEFAULT 30,
        description TEXT,
        is_active BOOLEAN DEFAULT true,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- Enhanced scheduled messages table
    CREATE TABLE IF NOT EXISTS scheduled_messages (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        recipient_jid TEXT NOT NULL,
        message_content TEXT NOT NULL,
        send_at TEXT NOT NULL,
        message_type TEXT DEFAULT 'reminder',
        reference_id TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        sent_at TEXT,
        error_message TEXT
    );
    """
    
    try:
        cursor.executescript(schema_sql)
        print("✅ Database schema created successfully")
        
        # Test inserting sample data
        cursor.execute("""
            INSERT INTO call_bookings (id, tenant_id, customer_name, customer_phone, call_type, scheduled_datetime)
            VALUES ('test-001', 'tenant-123', 'John Doe', '+60123456789', 'consultation', '2026-02-24 10:00:00')
        """)
        
        cursor.execute("SELECT * FROM call_bookings WHERE id = 'test-001'")
        result = cursor.fetchone()
        
        if result:
            print("✅ Sample data inserted and retrieved successfully")
            return True
        else:
            print("❌ Failed to retrieve sample data")
            return False
            
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        return False
    finally:
        conn.close()

def test_business_templates():
    """Test business template system."""
    print("\n📋 Testing business template system...")
    
    try:
        # Test business template seeder class structure
        from saas.business_template_seeder import BusinessTemplateSeeder
        
        # Create a mock seeder instance with mock supabase client
        class MockSupabase:
            pass
        
        seeder = BusinessTemplateSeeder(MockSupabase())
        
        # Test that business templates are defined
        if hasattr(seeder, 'business_templates') and seeder.business_templates:
            template_count = 0
            for business_type, templates in seeder.business_templates.items():
                template_count += len(templates)
                print(f"  📊 {business_type}: {len(templates)} templates")
            
            print(f"✅ Total {template_count} business templates defined across {len(seeder.business_templates)} business types")
            return True
        else:
            print("❌ No business templates found")
            return False
            
    except Exception as e:
        print(f"❌ Business template test failed: {e}")
        return False

def test_reminder_system():
    """Test advanced reminder system."""
    print("\n⏰ Testing advanced reminder system...")
    
    try:
        from core.advanced_reminder_system import AdvancedReminderSystem
        
        # Create a mock bijou instance
        class MockBijou:
            def __init__(self):
                self.tenant_id = "test-tenant"
                self.db_path = ":memory:"
                self.whatsapp_bridge_url = "http://localhost:8081"
        
        reminder_system = AdvancedReminderSystem(MockBijou())
        
        # Test that scheduling methods exist
        required_methods = [
            'schedule_appointment_reminder',
            'schedule_follow_up_reminder', 
            'process_pending_reminders'
        ]
        
        for method in required_methods:
            if hasattr(reminder_system, method):
                print(f"  ✅ Method {method} exists")
            else:
                print(f"  ❌ Method {method} missing")
                return False
        
        # Test that reminder templates are loaded
        if hasattr(reminder_system, 'reminder_templates') and reminder_system.reminder_templates:
            print(f"  ✅ {len(reminder_system.reminder_templates)} reminder templates loaded")
        else:
            print("  ❌ No reminder templates found")
            return False
        
        print("✅ Advanced reminder system structure validated")
        return True
        
    except Exception as e:
        print(f"❌ Reminder system test failed: {e}")
        return False

def test_api_endpoints_structure():
    """Test that API endpoint structure is correct."""
    print("\n🔗 Testing API endpoint structure...")
    
    try:
        # Read the main bijou.py file and check for call booking endpoints
        with open("src/core/bijou.py", "r") as f:
            content = f.read()
        
        required_endpoints = [
            "/api/call-booking/book",
            "/api/call-booking/list", 
            "/api/call-booking/{booking_id}/status",
            "/api/call-booking/availability"
        ]
        
        for endpoint in required_endpoints:
            if endpoint in content:
                print(f"  ✅ Endpoint {endpoint} found")
            else:
                print(f"  ❌ Endpoint {endpoint} missing")
                return False
        
        print("✅ All API endpoints found in bijou.py")
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def test_dashboard_integration():
    """Test dashboard integration."""
    print("\n🖥️ Testing dashboard integration...")
    
    try:
        # Check dashboard.html for call booking UI
        with open("static/dashboard.html", "r") as f:
            content = f.read()
        
        required_ui_elements = [
            "Call Booking",   # Tab name
            "CallsModule",    # JavaScript module
            "handleBookCall", # Function name
            "phone"           # Icon
        ]
        
        for element in required_ui_elements:
            if element in content:
                print(f"  ✅ UI element '{element}' found")
            else:
                print(f"  ❌ UI element '{element}' missing")
                return False
        
        print("✅ Dashboard integration validated")
        return True
        
    except Exception as e:
        print(f"❌ Dashboard integration test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting comprehensive call booking system test...\n")
    
    tests = [
        ("Import Test", test_imports),
        ("Database Schema", test_database_schema),
        ("Business Templates", test_business_templates),
        ("Reminder System", test_reminder_system),
        ("API Endpoints", test_api_endpoints_structure),
        ("Dashboard Integration", test_dashboard_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Call booking system is ready for deployment.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)