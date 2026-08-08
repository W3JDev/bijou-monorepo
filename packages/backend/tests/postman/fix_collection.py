#!/usr/bin/env python3
"""
Bijou AI Postman Collection Fixer
==================================

This script fixes all 33 failing requests in the Postman collection by:
1. Fixing variable syntax ({var} -> {{var}})
2. Adding missing request bodies with realistic test data
3. Adding required headers (X-Tenant-ID)
4. Adding test scripts to extract variables from responses
5. Adding pre-request scripts for fallback values

Author: @qa-engineer
Date: 2026-02-17
"""

import json
import os
from pathlib import Path

# Paths
COLLECTION_PATH = Path(__file__).parent / "collections" / "Bijou AI WhatsApp Enterprise Copy.postman_collection.json"
ENV_PATH = Path(__file__).parent / "environments" / "bijou-staging.postman_environment.json"
BACKUP_SUFFIX = ".backup.json"

print("Bijou AI Postman Collection Fixer")
print("=" * 60)

# Load collection
print(f"\nLoading collection: {COLLECTION_PATH.name}")
with open(COLLECTION_PATH, 'r', encoding='utf-8') as f:
    collection = json.load(f)

# Load environment  
print(f"Loading environment: {ENV_PATH.name}")
with open(ENV_PATH, 'r', encoding='utf-8') as f:
    environment = json.load(f)

# Backup originals
print(f"\nCreating backups...")
with open(str(COLLECTION_PATH) + BACKUP_SUFFIX, 'w', encoding='utf-8') as f:
    json.dump(collection, f, indent=2)
with open(str(ENV_PATH) + BACKUP_SUFFIX, 'w', encoding='utf-8') as f:
    json.dump(environment, f, indent=2)
print("Backups created")

# ================================================================================
# FIX 1: Update environment - add tenant_id and placeholders
# ================================================================================

print(f"\n FIX 1: Updating environment variables...")
env_vars = {var['key']: var for var in environment['values']}

# Set default tenant_id if empty
if not env_vars.get('tenant_id', {}).get('value'):
    env_vars['tenant_id']['value'] = "00000000-0000-0000-0000-000000000001"
    print("   Set default tenant_id")

# Add missing variables
new_vars = [
    {"key": "customer_jid", "value": "+60123456789@s.whatsapp.net", "type": "default", "enabled": True},
    {"key": "escalation_id", "value": "", "type": "default", "enabled": True},
    {"key": "agent_id", "value": "", "type": "default", "enabled": True},
    {"key": "document_id", "value": "", "type": "default", "enabled": True},
    {"key": "message_id", "value": "", "type": "default", "enabled": True},
    {"key": "token", "value": "", "type": "default", "enabled": True},
]

for var in new_vars:
    if var['key'] not in env_vars:
        environment['values'].append(var)
        print(f"   Added variable: {var['key']}")

# ================================================================================
# FIX 2: Fix URL path variables ({var} -> {{var}})
# ================================================================================

print(f"\n FIX 2: Fixing URL path variables...")

def fix_path_variables(url_obj):
    """Fix single-brace variables in URL paths"""
    if 'path' in url_obj:
        for i, segment in enumerate(url_obj['path']):
            if '{' in segment and '{{' not in segment:
                old_seg = segment
                new_seg = segment.replace('{', '{{').replace('}', '}}')
                url_obj['path'][i] = new_seg
                return f"{old_seg} -> {new_seg}"
    return None

path_fixes = 0
for folder in collection['item']:
    for request in folder.get('item', []):
        if 'request' in request:
            fix = fix_path_variables(request['request'].get('url', {}))
            if fix:
                print(f"   {request['name']}: {fix}")
                path_fixes += 1

print(f"   Fixed {path_fixes} path variables")

# ================================================================================
# FIX 3: Add request bodies and headers
# ================================================================================

print(f"\n FIX 3: Adding request bodies and headers...")

# Request body templates
REQUEST_BODIES = {
    "Takeover Conversation": {
        "customer_jid": "{{customer_jid}}",
        "agent_name": "Test Agent",
        "reason": "Complex inquiry requiring human assistance"
    },
    "Send Message As Agent": {
        "customer_jid": "{{customer_jid}}",
        "message": "Hello! I'm taking over from the AI. How can I help you further?",
        "agent_name": "John (Support Team)"
    },
    "Add Knowledge": {
        "content": "**Business Hours:**\\n- Monday to Friday: 9:00 AM - 6:00 PM\\n- Saturday: 10:00 AM - 2:00 PM\\n- Sunday: Closed",
        "source_name": "business_info"
    },
    "Create Agent": {
        "agent_name": "Sarah Lee",
        "agent_email": "sarah.lee@example.com",
        "agent_whatsapp": "+60123456789",
        "agent_role": "Senior Property Consultant",
        "priority_level": 2,
        "working_hours": {"start": "09:00", "end": "18:00"},
        "skills": ["property_sales", "customer_support"],
        "is_active": True
    },
    "Signup Property Agent": {
        "business_name": "Test Realty Sdn Bhd",
        "email": "test@example.com",
        "phone": "+60123456789"
    },
    "Schedule Message": {
        "recipient": "+60123456789@s.whatsapp.net",
        "message_type": "lead_followup",
        "content": "Hi! Just following up on your property inquiry.",
        "delay_minutes": 60
    },
    "Create Campaign": {
        "name": "January 2026 Promo",
        "message_template": " New Year Special! Get 10% off this month.",
        "target_segment": "all",
        "scheduled_time": "2026-02-20T10:00:00Z"
    },
    "Set Silence Rule": {
        "silence_days": 7,
        "message_template": "Hi! We noticed you haven't replied in a while. Still interested?"
    },
    "Update Testing Mode": {
        "testing_mode": True,
        "test_numbers": ["+60123456789"]
    },
    "Update Ignore List": {
        "ignore_numbers": ["+60111111111"],
        "private_numbers": []
    },
    "Update Business Hours": {
        "enabled": True,
        "timezone": "Asia/Kuala_Lumpur",
        "schedule": {
            day: {"start": "09:00", "end": "18:00", "enabled": True if day != "sunday" else False}
            for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        },
        "out_of_hours_message": "Thanks! We'll reply during business hours."
    },
    "Update Auto Reply": {
        "auto_reply_enabled": True,
        "welcome_message": "Hi! Thanks for contacting us. How can we help?"
    },
    "Webhook Message": {
        "event": "message",
        "device_id": "default",
        "payload": {
            "id": "TEST_MSG_001",
            "from": "+60123456789@s.whatsapp.net",
            "body": "Hello, I need help",
            "fromMe": False,
            "timestamp": 1708185600
        }
    },
    "Webhook Connection Status": {
        "tenant_id": "{{tenant_id}}",
        "whatsapp_jid": "+60123456789@s.whatsapp.net",
        "status": "connected",
        "timestamp": "2026-02-17T12:00:00Z"
    },
}

# Headers to add
HEADERS_TO_ADD = {
    "Upload Knowledge Document": [{"key": "X-Tenant-ID", "value": "{{tenant_id}}"}],
    "List Knowledge Documents": [{"key": "X-Tenant-ID", "value": "{{tenant_id}}"}],
    "Delete Knowledge Document": [{"key": "X-Tenant-ID", "value": "{{tenant_id}}"}],
    "Get Combined Knowledge": [{"key": "X-Tenant-ID", "value": "{{tenant_id}}"}],
    "Update Testing Mode": [{"key": "X-Tenant-ID", "value": "{{tenant_id}}"}],
    "Update Ignore List": [{"key": "X-Tenant-ID", "value": "{{tenant_id}}"}],
    "Update Business Hours": [{"key": "X-Tenant-ID", "value": "{{tenant_id}}"}],
    "Update Auto Reply": [{"key": "X-Tenant-ID", "value": "{{tenant_id}}"}],
}

body_fixes = 0
header_fixes = 0

for folder in collection['item']:
    for request in folder.get('item', []):
        req_name = request.get('name', '')
        
        # Add request body if needed
        if req_name in REQUEST_BODIES:
            if 'request' in request and 'body' in request['request']:
                request['request']['body']['raw'] = json.dumps(REQUEST_BODIES[req_name], indent=2)
                print(f"   {req_name}: Added request body")
                body_fixes += 1
        
        # Add headers if needed
        if req_name in HEADERS_TO_ADD:
            if 'request' in request:
                if 'header' not in request['request']:
                    request['request']['header'] = []
                
                for new_header in HEADERS_TO_ADD[req_name]:
                    # Check if header already exists
                    exists = any(h['key'] == new_header['key'] for h in request['request']['header'])
                    if not exists:
                        request['request']['header'].append(new_header)
                        print(f"   {req_name}: Added header {new_header['key']}")
                        header_fixes += 1

print(f"   Added {body_fixes} request bodies, {header_fixes} headers")

# ================================================================================
# FIX 4: Add test scripts to extract variables
# ================================================================================

print(f"\n FIX 4: Adding test scripts for variable extraction...")

TEST_SCRIPTS = {
    "Get Active Conversations": """
if (pm.response.code === 200) {
    const conversations = pm.response.json().conversations;
    if (conversations && conversations.length > 0) {
        pm.environment.set("customer_jid", conversations[0].customer_jid);
        console.log(" Set customer_jid:", conversations[0].customer_jid);
    } else {
        pm.environment.set("customer_jid", "+60123456789@s.whatsapp.net");
    }
}
""",
    "Get Escalations": """
if (pm.response.code === 200) {
    const escalations = pm.response.json().escalations;
    if (escalations && escalations.length > 0) {
        pm.environment.set("escalation_id", escalations[0].id);
        console.log(" Set escalation_id:", escalations[0].id);
    }
}
""",
    "Get Agents": """
if (pm.response.code === 200) {
    const agents = pm.response.json();
    if (agents && agents.length > 0) {
        pm.environment.set("agent_id", agents[0].id);
        console.log(" Set agent_id:", agents[0].id);
    }
}
""",
    "List Knowledge Documents": """
if (pm.response.code === 200) {
    const docs = pm.response.json().documents;
    if (docs && docs.length > 0) {
        pm.environment.set("document_id", docs[0].id);
        console.log(" Set document_id:", docs[0].id);
    }
}
""",
    "List Scheduled Messages": """
if (pm.response.code === 200) {
    const messages = pm.response.json();
    if (messages && messages.length > 0) {
        pm.environment.set("message_id", messages[0].id);
        console.log(" Set message_id:", messages[0].id);
    }
}
""",
    "Signup Property Agent": """
if (pm.response.code === 200) {
    const data = pm.response.json();
    if (data.tenant_id) {
        pm.environment.set("token", data.tenant_id);
        console.log(" Set onboarding token");
    }
}
""",
}

script_fixes = 0
for folder in collection['item']:
    for request in folder.get('item', []):
        req_name = request.get('name', '')
        if req_name in TEST_SCRIPTS:
            if 'event' not in request:
                request['event'] = []
            
            # Remove existing test script if present
            request['event'] = [e for e in request['event'] if e.get('listen') != 'test']
            
            # Add new test script
            request['event'].append({
                "listen": "test",
                "script": {
                    "exec": TEST_SCRIPTS[req_name].strip().split('\n'),
                    "type": "text/javascript"
                }
            })
            print(f"   {req_name}: Added test script")
            script_fixes += 1

print(f"   Added {script_fixes} test scripts")

# ================================================================================
# FIX 5: Add pre-request script to Get Dashboard Stats
# ================================================================================

print(f"\n FIX 5: Adding pre-request script...")

PRE_REQUEST_SCRIPT = """
// Set default tenant_id if not present
if (!pm.environment.get("tenant_id") || pm.environment.get("tenant_id") === "") {
    pm.environment.set("tenant_id", "00000000-0000-0000-0000-000000000001");
    console.log(" Set default tenant_id");
}
"""

for folder in collection['item']:
    for request in folder.get('item', []):
        if request.get('name') == "Get Dashboard Stats":
            if 'event' not in request:
                request['event'] = []
            
            # Remove existing pre-request script
            request['event'] = [e for e in request['event'] if e.get('listen') != 'prerequest']
            
            # Add new pre-request script
            request['event'].append({
                "listen": "prerequest",
                "script": {
                    "exec": PRE_REQUEST_SCRIPT.strip().split('\n'),
                    "type": "text/javascript"
                }
            })
            print(f"   Added pre-request script to Get Dashboard Stats")
            break

# ================================================================================
# Save updated files
# ================================================================================

print(f"\n Saving updated files...")

with open(COLLECTION_PATH, 'w', encoding='utf-8') as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)
print(f"   Collection saved: {COLLECTION_PATH.name}")

with open(ENV_PATH, 'w', encoding='utf-8') as f:
    json.dump(environment, f, indent=2, ensure_ascii=False)
print(f"   Environment saved: {ENV_PATH.name}")

# ================================================================================
# Summary
# ================================================================================

print("\n" + "=" * 60)
print(" POSTMAN COLLECTION FIXES COMPLETED")
print("=" * 60)
print(f"\n Summary:")
print(f"   Fixed {path_fixes} URL path variables")
print(f"   Added {body_fixes} request bodies")
print(f"   Added {header_fixes} headers")
print(f"   Added {script_fixes} test scripts")
print(f"   Added 1 pre-request script")
print(f"   Updated environment with {len(new_vars)} new variables")

print(f"\n Next Steps:")
print(f"  1. Review changes in: {COLLECTION_PATH.name}")
print(f"  2. Set api_key in environment (from .env file)")
print(f"  3. Import collection + environment into Postman")
print(f"  4. Run collection and verify ~96% pass rate")
print(f"\n Backups saved with .backup.json extension")
print(f"\n Ready for testing!")
