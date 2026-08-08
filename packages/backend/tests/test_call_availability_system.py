#!/usr/bin/env python3
"""
Test Call Availability Management System - Task #4
=================================================

Comprehensive test suite for the enhanced call availability system including:
- Default business hours setup
- Available slots calculation
- Booking validation against availability
- Holiday and exception management
- UI integration testing

Author: W3J Bijou AI
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8080"
TEST_TENANT_ID = "00000000-0000-0000-0000-000000000002"

class CallAvailabilitySystemTest:
    """Test suite for call availability management system."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Tenant-ID': TEST_TENANT_ID
        })
        self.test_results = []

    def log_result(self, test_name: str, success: bool, message: str = ""):
        """Log a test result."""
        status = "✅" if success else "❌"
        logger.info(f"{status} {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })

    def test_setup_default_availability(self) -> bool:
        """Test setting up default business hours for a tenant."""
        try:
            logger.info("🧪 Testing default availability setup...")
            
            response = self.session.post(f"{BASE_URL}/api/call-booking/availability/default")
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                if success:
                    self.log_result(
                        "Default Availability Setup",
                        True,
                        f"Created {data.get('slots_created', 0)} default slots"
                    )
                    return True
                else:
                    self.log_result("Default Availability Setup", False, "API returned success=False")
                    return False
            else:
                self.log_result(
                    "Default Availability Setup", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Default Availability Setup", False, str(e))
            return False

    def test_get_availability_schedule(self) -> Dict:
        """Test retrieving the complete availability schedule."""
        try:
            logger.info("🧪 Testing availability schedule retrieval...")
            
            response = self.session.get(f"{BASE_URL}/api/call-booking/availability/schedule")
            
            if response.status_code == 200:
                data = response.json()
                weekly_schedule = data.get("weekly_schedule", [])
                settings = data.get("settings", {})
                holidays = data.get("holidays", [])
                
                if weekly_schedule and settings:
                    self.log_result(
                        "Get Availability Schedule",
                        True,
                        f"Retrieved {len(weekly_schedule)} slots, {len(holidays)} holidays"
                    )
                    return data
                else:
                    self.log_result("Get Availability Schedule", False, "Missing schedule data")
                    return {}
            else:
                self.log_result(
                    "Get Availability Schedule",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return {}
                
        except Exception as e:
            self.log_result("Get Availability Schedule", False, str(e))
            return {}

    def test_get_available_slots(self) -> List[Dict]:
        """Test getting available time slots for booking."""
        try:
            logger.info("🧪 Testing available slots retrieval...")
            
            # Test for next week to avoid weekend/holiday issues
            start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
            
            response = self.session.get(
                f"{BASE_URL}/api/call-booking/available-slots?"
                f"start_date={start_date}&end_date={end_date}&duration_minutes=30"
            )
            
            if response.status_code == 200:
                data = response.json()
                available_slots = data.get("available_slots", [])
                total_slots = data.get("total_slots", 0)
                
                self.log_result(
                    "Get Available Slots",
                    True,
                    f"Found {total_slots} available slots from {start_date} to {end_date}"
                )
                return available_slots
            else:
                self.log_result(
                    "Get Available Slots",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return []
                
        except Exception as e:
            self.log_result("Get Available Slots", False, str(e))
            return []

    def test_booking_validation(self, available_slots: List[Dict]) -> bool:
        """Test booking validation against available slots."""
        try:
            logger.info("🧪 Testing booking validation...")
            
            if not available_slots:
                self.log_result("Booking Validation", False, "No available slots to test with")
                return False
            
            # Test valid booking
            valid_slot = available_slots[0]
            valid_booking_data = {
                "customer_jid": "60123456789@s.whatsapp.net",
                "customer_name": "Test Customer",
                "customer_phone": "+60123456789",
                "scheduled_time": f"{valid_slot['date']}T{valid_slot['start_time']}:00Z",
                "duration_minutes": 30,
                "call_type": "consultation",
                "notes": "Test booking for availability validation"
            }
            
            response = self.session.post(
                f"{BASE_URL}/api/call-booking/book",
                json=valid_booking_data
            )
            
            if response.status_code == 200:
                booking_data = response.json()
                booking_id = booking_data.get("booking_id")
                
                self.log_result(
                    "Valid Booking Test",
                    True,
                    f"Successfully booked call at {valid_slot['date']} {valid_slot['start_time']}"
                )
                
                # Test invalid booking (same slot should now be unavailable)
                invalid_response = self.session.post(
                    f"{BASE_URL}/api/call-booking/book",
                    json={
                        **valid_booking_data,
                        "customer_name": "Test Customer 2"
                    }
                )
                
                if invalid_response.status_code == 409:  # Conflict
                    self.log_result(
                        "Invalid Booking Test",
                        True,
                        "Correctly rejected booking for unavailable slot"
                    )
                else:
                    self.log_result(
                        "Invalid Booking Test",
                        False,
                        f"Should have rejected duplicate booking: HTTP {invalid_response.status_code}"
                    )
                
                # Clean up - cancel the test booking
                if booking_id:
                    try:
                        self.session.put(
                            f"{BASE_URL}/api/call-booking/{booking_id}/status",
                            json={"status": "cancelled"}
                        )
                    except:
                        pass  # Cleanup failure is not critical
                
                return True
            else:
                self.log_result(
                    "Valid Booking Test",
                    False,
                    f"Failed to book valid slot: HTTP {response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Booking Validation", False, str(e))
            return False

    def test_holiday_management(self) -> bool:
        """Test holiday and exception management."""
        try:
            logger.info("🧪 Testing holiday management...")
            
            # Add a test holiday
            test_holiday = {
                "date": (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d"),
                "title": "Test Holiday",
                "description": "Automated test holiday",
                "is_recurring": False
            }
            
            response = self.session.post(
                f"{BASE_URL}/api/call-booking/availability/holidays",
                json=[test_holiday]
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_result(
                        "Holiday Management",
                        True,
                        f"Successfully added holiday for {test_holiday['date']}"
                    )
                    
                    # Verify holiday appears in schedule
                    schedule_data = self.test_get_availability_schedule()
                    holidays = schedule_data.get("holidays", [])
                    
                    holiday_found = any(
                        h.get("date") == test_holiday["date"] 
                        for h in holidays
                    )
                    
                    if holiday_found:
                        self.log_result(
                            "Holiday Retrieval",
                            True,
                            "Holiday correctly appears in schedule"
                        )
                    else:
                        self.log_result(
                            "Holiday Retrieval",
                            False,
                            "Holiday not found in schedule"
                        )
                    
                    return holiday_found
                else:
                    self.log_result("Holiday Management", False, "API returned success=False")
                    return False
            else:
                self.log_result(
                    "Holiday Management",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Holiday Management", False, str(e))
            return False

    def test_settings_update(self) -> bool:
        """Test updating call settings."""
        try:
            logger.info("🧪 Testing call settings update...")
            
            new_settings = {
                "tenant_id": TEST_TENANT_ID,
                "timezone": "Asia/Kuala_Lumpur",
                "buffer_minutes": 20,
                "max_calls_per_day": 10,
                "max_calls_per_hour": 3,
                "advance_booking_days": 45,
                "allow_same_day_booking": False
            }
            
            response = self.session.put(
                f"{BASE_URL}/api/call-booking/availability/settings",
                json=new_settings
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_result(
                        "Settings Update",
                        True,
                        "Successfully updated call settings"
                    )
                    
                    # Verify settings are updated
                    schedule_data = self.test_get_availability_schedule()
                    updated_settings = schedule_data.get("settings", {})
                    
                    buffer_correct = updated_settings.get("buffer_minutes") == 20
                    max_calls_correct = updated_settings.get("max_calls_per_day") == 10
                    
                    if buffer_correct and max_calls_correct:
                        self.log_result(
                            "Settings Verification",
                            True,
                            "Settings correctly updated and retrieved"
                        )
                        return True
                    else:
                        self.log_result(
                            "Settings Verification",
                            False,
                            f"Settings mismatch: buffer={updated_settings.get('buffer_minutes')}, max_calls={updated_settings.get('max_calls_per_day')}"
                        )
                        return False
                else:
                    self.log_result("Settings Update", False, "API returned success=False")
                    return False
            else:
                self.log_result(
                    "Settings Update",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Settings Update", False, str(e))
            return False

    def test_dashboard_integration(self) -> bool:
        """Test that dashboard can load availability data."""
        try:
            logger.info("🧪 Testing dashboard integration...")
            
            # Test if basic availability endpoint works (used by dashboard)
            response = self.session.get(f"{BASE_URL}/api/call-booking/availability")
            
            if response.status_code == 200:
                data = response.json()
                availability = data.get("availability", [])
                
                self.log_result(
                    "Dashboard Integration",
                    True,
                    f"Dashboard can load {len(availability)} availability slots"
                )
                return True
            else:
                self.log_result(
                    "Dashboard Integration",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Dashboard Integration", False, str(e))
            return False

    def run_all_tests(self) -> Dict:
        """Run all availability management tests."""
        logger.info("🚀 Starting Call Availability Management System Tests...")
        
        # Test sequence
        tests = [
            ("Setup Default Availability", self.test_setup_default_availability),
            ("Get Availability Schedule", self.test_get_availability_schedule),
            ("Dashboard Integration", self.test_dashboard_integration),
            ("Holiday Management", self.test_holiday_management),
            ("Settings Update", self.test_settings_update),
        ]
        
        # Run basic tests first
        for test_name, test_func in tests:
            try:
                if test_name == "Get Availability Schedule":
                    schedule_data = test_func()
                    continue
                test_func()
            except Exception as e:
                self.log_result(test_name, False, f"Test execution error: {e}")
        
        # Run slot and booking tests
        available_slots = self.test_get_available_slots()
        if available_slots:
            self.test_booking_validation(available_slots)
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"\n{'='*60}")
        logger.info(f"CALL AVAILABILITY SYSTEM TEST SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            logger.info(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    logger.info(f"  - {result['test']}: {result['message']}")
        
        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": passed_tests / total_tests * 100,
            "all_passed": failed_tests == 0
        }


def main():
    """Run the test suite."""
    print("🧪 Call Availability Management System - Test Suite")
    print("=" * 60)
    
    test_suite = CallAvailabilitySystemTest()
    results = test_suite.run_all_tests()
    
    if results["all_passed"]:
        print("\n🎉 ALL TESTS PASSED! Call availability system is ready for production.")
        return 0
    else:
        print(f"\n⚠️ {results['failed']} tests failed. Please review and fix issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())