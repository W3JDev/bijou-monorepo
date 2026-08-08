"""
Synthetic Test Tenant Fixtures
================================

Pre-configured test tenants for automated testing:
1. Property/Real Estate (Harmoni Residence - Shawny)
2. Gaming/Esports (GameHub Arena)
3. Dental Clinic (SmileCare Dental)
4. F&B Restaurant (Bistro Delights)

Each tenant has realistic configurations for testing all features.

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Date: 2026-02-07
"""

from datetime import datetime
from typing import Dict, List

# ════════════════════════════════════════════════════════════════
# TENANT FIXTURES
# ════════════════════════════════════════════════════════════════


def get_test_tenants() -> List[Dict]:
    """
    Get all 4 synthetic test tenants with realistic data.

    Returns:
        List of tenant dictionaries ready for database insertion
    """
    return [
        get_property_tenant(),
        get_gaming_tenant(),
        get_dental_tenant(),
        get_fnb_tenant(),
    ]


# ════════════════════════════════════════════════════════════════
# 1. PROPERTY / REAL ESTATE - Harmoni Residence
# ════════════════════════════════════════════════════════════════


def get_property_tenant() -> Dict:
    """
    Harmoni Residence - Property Sales (Shawny's business)

    Features tested:
    - Property listings and availability
    - Booking/viewing appointments
    - Price inquiries
    - Location and amenities questions
    - Multi-language support (English/Malay/Mandarin)
    """
    return {
        "name": "Harmoni Residence",
        "slug": "harmoni-residence-test",
        "business_name": "Harmoni Residence",
        "email": "test+harmoni@w3jconsulting.com",
        "phone": "+60143856929",
        "status": "active",
        "plan": "professional",
        "business_type": "property",
        "description": "Luxury condominium development in Kuala Lumpur with 2-3 bedroom units, pool, gym, and security.",
        "onboarding_completed": True,
        "testing_mode": True,
        "test_numbers": ["+60100000001", "+60100000002"],  # Mock test numbers
        "ignore_numbers": ["+60116060963"],  # Jewel's number (always ignored)
        "private_numbers": [],
        "auto_reply_enabled": True,
        "business_hours": {
            "enabled": True,
            "timezone": "Asia/Kuala_Lumpur",
            "schedule": {
                "monday": {"start": "09:00", "end": "18:00", "enabled": True},
                "tuesday": {"start": "09:00", "end": "18:00", "enabled": True},
                "wednesday": {"start": "09:00", "end": "18:00", "enabled": True},
                "thursday": {"start": "09:00", "end": "18:00", "enabled": True},
                "friday": {"start": "09:00", "end": "13:00", "enabled": True},
                "saturday": {"start": "10:00", "end": "17:00", "enabled": True},
                "sunday": {"start": "10:00", "end": "17:00", "enabled": True},
            },
            "out_of_hours_message": "Thank you for your interest in Harmoni Residence! Our sales team is available Monday-Sunday. We'll respond during business hours.",
        },
        "welcome_message": "Welcome to Harmoni Residence! 🏡 How can I help you today? Ask about units, pricing, or schedule a viewing!",
        "persona_config": {
            "name": "Shawny",
            "role": "Property Sales Agent",
            "tone": "professional yet friendly",
            "expertise": "property sales, unit availability, pricing, viewing appointments",
        },
        "created_by": "test-fixture",
        "created_at": datetime.utcnow().isoformat(),
    }


def get_property_knowledge() -> str:
    """Knowledge base for Harmoni Residence"""
    return """
# Harmoni Residence - Property Information

## Overview
Harmoni Residence is a luxury condominium development located in the heart of Kuala Lumpur, offering modern living with world-class amenities.

## Unit Types & Pricing
- **2 Bedroom (900 sqft)**: RM 580,000 - RM 650,000
- **3 Bedroom (1,200 sqft)**: RM 780,000 - RM 880,000
- **Penthouse (1,800 sqft)**: RM 1.2M - RM 1.5M

## Facilities
- Swimming Pool (Olympic size)
- Gymnasium (24/7 access)
- Sky Lounge & BBQ area
- Children's playground
- 24-hour security with CCTV
- Covered parking (2 bays per unit)
- Smart home features

## Location
Address: Jalan Ampang, 50450 Kuala Lumpur
- 5 minutes to KLCC
- 10 minutes to Pavilion KL
- Walking distance to LRT station
- Near international schools

## Availability
**Phase 1 (Ready 2026)**: 80% sold, 15 units remaining
**Phase 2 (2027)**: Booking open, early bird discount 10%

## Viewing Appointments
Available Mon-Sun by appointment. Contact us to schedule!

## Payment Plan
- Booking fee: RM 5,000
- Down payment: 10% within 14 days
- Progressive payment: Following construction milestones
- Bank loan assistance available
"""


# ════════════════════════════════════════════════════════════════
# 2. GAMING / ESPORTS - GameHub Arena
# ════════════════════════════════════════════════════════════════


def get_gaming_tenant() -> Dict:
    """
    GameHub Arena - Gaming & Esports Center

    Features tested:
    - PC gaming session bookings
    - Tournament registrations
    - Membership inquiries
    - Gaming equipment questions
    - Event schedules
    """
    return {
        "name": "GameHub Arena",
        "slug": "gamehub-arena-test",
        "business_name": "GameHub Arena",
        "email": "test+gamehub@w3jconsulting.com",
        "phone": "+60123456001",
        "status": "active",
        "plan": "basic",
        "business_type": "gaming",
        "description": "Premier gaming and esports center with high-end PCs, PS5, tournaments, and community events.",
        "onboarding_completed": True,
        "testing_mode": True,
        "test_numbers": ["+60100000003", "+60100000004"],
        "ignore_numbers": [],
        "auto_reply_enabled": True,
        "business_hours": {
            "enabled": True,
            "timezone": "Asia/Kuala_Lumpur",
            "schedule": {
                "monday": {"start": "14:00", "end": "02:00", "enabled": True},
                "tuesday": {"start": "14:00", "end": "02:00", "enabled": True},
                "wednesday": {"start": "14:00", "end": "02:00", "enabled": True},
                "thursday": {"start": "14:00", "end": "02:00", "enabled": True},
                "friday": {"start": "14:00", "end": "04:00", "enabled": True},
                "saturday": {"start": "12:00", "end": "04:00", "enabled": True},
                "sunday": {"start": "12:00", "end": "02:00", "enabled": True},
            },
            "out_of_hours_message": "GameHub Arena opens at 2 PM daily! Book your gaming session or ask about tournaments.",
        },
        "welcome_message": "Welcome to GameHub Arena! 🎮 Book a PC, join a tournament, or ask about our VIP membership!",
        "persona_config": {
            "name": "Alex",
            "role": "Gaming Center Manager",
            "tone": "casual and energetic",
            "expertise": "gaming, tournaments, PC specs, memberships",
        },
        "created_by": "test-fixture",
        "created_at": datetime.utcnow().isoformat(),
    }


def get_gaming_knowledge() -> str:
    """Knowledge base for GameHub Arena"""
    return """
# GameHub Arena - Gaming Center

## Our Setup
- 50 High-End Gaming PCs (RTX 4090, i9-13900K, 32GB RAM)
- 10 PS5 Stations
- VR Gaming Zone (Meta Quest 3)
- Private Gaming Rooms for teams

## Hourly Rates
- **Standard PC**: RM 8/hour
- **VIP PC (RTX 4090)**: RM 12/hour
- **PS5**: RM 10/hour
- **VR Gaming**: RM 15/hour

## Memberships
- **Bronze (RM 50/month)**: 10% discount on all bookings
- **Silver (RM 100/month)**: 20% discount + 5 free hours
- **Gold (RM 200/month)**: 30% discount + 15 free hours + tournament priority

## Tournaments
- Weekly FIFA tournaments (RM 20 entry, RM 500 prize)
- Monthly Valorant 5v5 (RM 100/team, RM 2,000 prize)
- CS2 Community League (Free entry, glory only!)

## Upcoming Events
- Feb 14-16: Valentine's Couple Tournament (Overcooked 2)
- Feb 21: Mobile Legends Bang Bang Championship
- March 1-3: Annual Dota 2 Grand Finals

## Booking
Book via WhatsApp or walk in! Peak hours (6 PM - 12 AM) recommended to book ahead.

## Location
Lot 3-12, Mid Valley Megamall, Kuala Lumpur
Open 2 PM - 2 AM daily (Fri/Sat till 4 AM)
"""


# ════════════════════════════════════════════════════════════════
# 3. DENTAL CLINIC - SmileCare Dental
# ════════════════════════════════════════════════════════════════


def get_dental_tenant() -> Dict:
    """
    SmileCare Dental - Family Dental Clinic

    Features tested:
    - Appointment bookings
    - Treatment inquiries
    - Insurance questions
    - Emergency dental care
    - Pricing transparency
    """
    return {
        "name": "SmileCare Dental",
        "slug": "smilecare-dental-test",
        "business_name": "SmileCare Dental Clinic",
        "email": "test+smilecare@w3jconsulting.com",
        "phone": "+60123456002",
        "status": "active",
        "plan": "professional",
        "business_type": "healthcare",
        "description": "Family-friendly dental clinic with experienced dentists, modern equipment, and painless treatments.",
        "onboarding_completed": True,
        "testing_mode": True,
        "test_numbers": ["+60100000005", "+60100000006"],
        "ignore_numbers": [],
        "auto_reply_enabled": True,
        "business_hours": {
            "enabled": True,
            "timezone": "Asia/Kuala_Lumpur",
            "schedule": {
                "monday": {"start": "09:00", "end": "18:00", "enabled": True},
                "tuesday": {"start": "09:00", "end": "18:00", "enabled": True},
                "wednesday": {"start": "09:00", "end": "18:00", "enabled": True},
                "thursday": {"start": "09:00", "end": "18:00", "enabled": True},
                "friday": {"start": "09:00", "end": "17:00", "enabled": True},
                "saturday": {"start": "09:00", "end": "13:00", "enabled": True},
                "sunday": {"start": "00:00", "end": "00:00", "enabled": False},
            },
            "out_of_hours_message": "SmileCare Dental is closed. For dental emergencies, call our hotline: +60123456999. We'll respond to messages during business hours.",
        },
        "welcome_message": "Welcome to SmileCare Dental! 😁 Book an appointment, ask about treatments, or check our pricing!",
        "persona_config": {
            "name": "Dr. Sarah",
            "role": "Dental Receptionist",
            "tone": "warm and reassuring",
            "expertise": "dental appointments, treatments, insurance, pricing",
        },
        "created_by": "test-fixture",
        "created_at": datetime.utcnow().isoformat(),
    }


def get_dental_knowledge() -> str:
    """Knowledge base for SmileCare Dental"""
    return """
# SmileCare Dental Clinic

## Our Services
- General Checkup & Cleaning
- Tooth Filling & Restoration
- Root Canal Treatment
- Teeth Whitening
- Braces (Metal & Invisible)
- Dental Implants
- Wisdom Tooth Extraction
- Emergency Dental Care

## Pricing (Starting From)
- **Checkup + Scaling**: RM 80
- **Tooth Filling**: RM 120
- **Root Canal**: RM 600 - RM 1,200
- **Teeth Whitening**: RM 800 (1-hour laser)
- **Braces**: RM 3,500 - RM 8,000 (full treatment)
- **Dental Implant**: RM 4,500 per tooth

## Our Dentists
- Dr. Sarah Lee (15 years experience, General & Cosmetic)
- Dr. Ahmad Rahman (Orthodontics specialist)
- Dr. Priya Kumar (Pediatric dentist)

## Insurance Accepted
- Prudential
- AIA
- Great Eastern
- Allianz
- Company panel doctors (check with HR)

## Appointment Booking
Available slots Mon-Sat. Book at least 1 day ahead for general checkup, 3-5 days for specialist treatments.

## Emergency Services
For dental emergencies (severe pain, broken tooth, bleeding), call our hotline immediately: +60123456999

## Location
23-2, Jalan SS15/4D, Subang Jaya, 47500 Selangor
Ample parking available
10 minutes from LRT SS15 station

## Opening Hours
Mon-Thu: 9 AM - 6 PM
Friday: 9 AM - 5 PM
Saturday: 9 AM - 1 PM
Sunday: Closed
"""


# ════════════════════════════════════════════════════════════════
# 4. F&B RESTAURANT - Bistro Delights
# ════════════════════════════════════════════════════════════════


def get_fnb_tenant() -> Dict:
    """
    Bistro Delights - Casual Dining Restaurant

    Features tested:
    - Table reservations
    - Menu inquiries
    - Delivery orders
    - Special dietary requests
    - Event catering
    """
    return {
        "name": "Bistro Delights",
        "slug": "bistro-delights-test",
        "business_name": "Bistro Delights Restaurant",
        "email": "test+bistro@w3jconsulting.com",
        "phone": "+60123456003",
        "status": "active",
        "plan": "basic",
        "business_type": "fnb",
        "description": "Cozy bistro serving fusion cuisine, artisan coffee, and homemade desserts in a relaxed atmosphere.",
        "onboarding_completed": True,
        "testing_mode": True,
        "test_numbers": ["+60100000007", "+60100000008"],
        "ignore_numbers": [],
        "auto_reply_enabled": True,
        "business_hours": {
            "enabled": True,
            "timezone": "Asia/Kuala_Lumpur",
            "schedule": {
                "monday": {"start": "11:00", "end": "22:00", "enabled": False},
                "tuesday": {"start": "11:00", "end": "22:00", "enabled": True},
                "wednesday": {"start": "11:00", "end": "22:00", "enabled": True},
                "thursday": {"start": "11:00", "end": "22:00", "enabled": True},
                "friday": {"start": "11:00", "end": "23:00", "enabled": True},
                "saturday": {"start": "10:00", "end": "23:00", "enabled": True},
                "sunday": {"start": "10:00", "end": "22:00", "enabled": True},
            },
            "out_of_hours_message": "Bistro Delights is currently closed. We're open Tue-Sun! Check our menu and reserve a table for your next visit.",
        },
        "welcome_message": "Welcome to Bistro Delights! 🍽️ Reserve a table, check our menu, or ask about today's specials!",
        "persona_config": {
            "name": "Emma",
            "role": "Restaurant Host",
            "tone": "friendly and hospitality-focused",
            "expertise": "reservations, menu, dietary needs, catering",
        },
        "created_by": "test-fixture",
        "created_at": datetime.utcnow().isoformat(),
    }


def get_fnb_knowledge() -> str:
    """Knowledge base for Bistro Delights"""
    return """
# Bistro Delights Restaurant

## Menu Highlights

**Appetizers**
- Truffle Mushroom Soup: RM 18
- Crispy Calamari: RM 22
- Cheese Platter: RM 35

**Mains**
- Grilled Salmon (with lemon butter): RM 45
- Wagyu Beef Burger: RM 38
- Chicken Aglio Olio Pasta: RM 28
- Vegetarian Risotto: RM 26

**Desserts**
- Chocolate Lava Cake: RM 16
- Tiramisu: RM 18
- Panna Cotta: RM 14

**Beverages**
- Artisan Coffee (Latte/Cappuccino): RM 12
- Fresh Juices: RM 10
- Craft Sodas: RM 8

## Daily Specials (Tuesday-Friday)
Lunch Set: RM 25 (Soup + Main + Drink)
Happy Hour (4-6 PM): Buy 1 Get 1 on selected drinks

## Dietary Options
We accommodate:
- Vegetarian & Vegan options
- Gluten-free pasta available
- Halal-friendly (no pork, no alcohol in cooking)
- Allergy-friendly (inform our chef)

## Table Reservations
- Walk-ins welcome (subject to availability)
- Reservations recommended for weekends & dinner
- Group bookings (10+ people): 2 days advance notice
- Private room available for events (20-30 pax)

## Delivery & Takeaway
- Delivery via GrabFood, Foodpanda
- Direct takeaway: Call ahead, 10% discount
- Catering available for events (50+ pax)

## Location
15-G, Plaza Damansara, Damansara Heights, KL
Valet parking available
Near Damansara Heights MRT

## Opening Hours
Closed Mondays
Tue-Thu: 11 AM - 10 PM
Fri-Sat: 11 AM - 11 PM
Sunday: 10 AM - 10 PM
Weekend brunch starts at 10 AM!

## Special Events
- Valentine's Day: Special 5-course menu (RM 180/couple)
- Wine Tasting Nights: Last Friday of every month
- Live Acoustic Music: Saturday evenings (7-9 PM)
"""


# ════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════


def get_tenant_by_type(business_type: str) -> Dict:
    """Get tenant fixture by business type"""
    type_map = {
        "property": get_property_tenant,
        "gaming": get_gaming_tenant,
        "dental": get_dental_tenant,
        "healthcare": get_dental_tenant,  # Alias
        "fnb": get_fnb_tenant,
        "restaurant": get_fnb_tenant,  # Alias
    }

    getter = type_map.get(business_type.lower())
    if not getter:
        raise ValueError(
            f"Unknown business type: {business_type}. Valid types: {list(type_map.keys())}"
        )

    return getter()


def get_knowledge_by_type(business_type: str) -> str:
    """Get knowledge fixture by business type"""
    type_map = {
        "property": get_property_knowledge,
        "gaming": get_gaming_knowledge,
        "dental": get_dental_knowledge,
        "healthcare": get_dental_knowledge,  # Alias
        "fnb": get_fnb_knowledge,
        "restaurant": get_fnb_knowledge,  # Alias
    }

    getter = type_map.get(business_type.lower())
    if not getter:
        raise ValueError(
            f"Unknown business type: {business_type}. Valid types: {list(type_map.keys())}"
        )

    return getter()


def get_all_knowledge() -> Dict[str, str]:
    """Get all knowledge bases as a dictionary"""
    return {
        "property": get_property_knowledge(),
        "gaming": get_gaming_knowledge(),
        "dental": get_dental_knowledge(),
        "fnb": get_fnb_knowledge(),
    }
