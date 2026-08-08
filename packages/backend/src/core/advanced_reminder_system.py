#!/usr/bin/env python3
"""
Advanced Reminder System - Comprehensive WhatsApp Reminders
=========================================================

Business-specific reminder and follow-up system for:
- Dental appointments and follow-ups
- Property viewings and callbacks
- General consultation scheduling
- Agent confirmation workflows
- Calendar event integration

Author: W3J Bijou Enterprise
Architecture: docs/SAAS_ARCHITECTURE.md
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)


class ReminderType(Enum):
    """Types of reminders supported"""
    DENTAL_CHECKUP = "dental_checkup"
    DENTAL_FOLLOW_UP = "dental_follow_up" 
    PROPERTY_VIEWING = "property_viewing"
    PROPERTY_CALLBACK = "property_callback"
    CONSULTATION_REMINDER = "consultation_reminder"
    AGENT_CONFIRMATION = "agent_confirmation"
    CALENDAR_EVENT = "calendar_event"
    POST_APPOINTMENT = "post_appointment"


class BusinessType(Enum):
    """Business types for tailored messaging"""
    DENTAL_CLINIC = "dental_clinic"
    REAL_ESTATE = "real_estate"
    CONSULTING = "consulting"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    RETAIL = "retail"


class AdvancedReminderSystem:
    """
    Comprehensive reminder system with business-specific templates
    and intelligent scheduling based on customer behavior.
    """
    
    def __init__(self, bijou_instance):
        self.bijou = bijou_instance
        self.reminder_templates = self._load_business_templates()
        self.scheduling_rules = self._load_scheduling_rules()
    
    def _load_business_templates(self) -> Dict[str, Dict]:
        """Load business-specific reminder templates"""
        return {
            # ==================== DENTAL CLINIC TEMPLATES ====================
            "dental_checkup_24h": {
                "business_type": BusinessType.DENTAL_CLINIC,
                "reminder_type": ReminderType.DENTAL_CHECKUP,
                "timing": "24_hours_before",
                "template": """
🦷 *Dental Appointment Reminder*

Hello {customer_name}! 👋

Just a friendly reminder that you have a dental appointment scheduled:

📅 **Tomorrow at {appointment_time}**
📍 {clinic_address}
👨‍⚕️ Dr. {doctor_name}

*What to bring:*
• IC/Passport
• Previous dental records (if any)
• Insurance card (if applicable)

⏰ Please arrive 15 minutes early for check-in.

If you need to reschedule, please call us at {clinic_phone} or reply to this message.

Looking forward to seeing you! 😊

_Regards,_  
*{clinic_name}*
                """.strip(),
                "triggers": ["appointment", "dental", "checkup", "cleaning"],
                "follow_up_hours": [1, 24],  # 1 hour before, and 24 hours after if no-show
            },
            
            "dental_follow_up_post": {
                "business_type": BusinessType.DENTAL_CLINIC,
                "reminder_type": ReminderType.DENTAL_FOLLOW_UP,
                "timing": "2_hours_after",
                "template": """
🦷 *Thank You for Your Visit!*

Hi {customer_name}! 

Thank you for visiting {clinic_name} today. We hope you had a comfortable experience with Dr. {doctor_name}.

📋 *Post-Treatment Care:*
{treatment_instructions}

💡 *Important Reminders:*
• Avoid hard foods for 24 hours
• Take prescribed medication as directed
• Rinse gently with warm salt water

📞 If you experience any discomfort or have questions, don't hesitate to call us at {clinic_phone}.

🗓️ *Next Appointment:* {next_appointment_date}

We appreciate your trust in our care! ⭐

_Your dental health team,_  
*{clinic_name}*
                """.strip(),
                "triggers": ["treatment", "completed", "visit"],
                "follow_up_hours": [24, 168],  # 1 day and 1 week follow-up
            },

            # ==================== REAL ESTATE TEMPLATES ====================
            "property_viewing_24h": {
                "business_type": BusinessType.REAL_ESTATE,
                "reminder_type": ReminderType.PROPERTY_VIEWING,
                "timing": "24_hours_before",
                "template": """
🏠 *Property Viewing Reminder*

Hello {customer_name}! 

Hope you're excited about tomorrow's property viewing! 🗝️

📅 **Tomorrow at {viewing_time}**
📍 {property_address}
🏡 {property_type} - {bedrooms} bedrooms, {bathrooms} bathrooms
💰 Price: RM {property_price}

👨‍💼 Your agent: {agent_name} ({agent_phone})

*What to expect:*
• Full property walkthrough (~30 minutes)
• Neighborhood tour
• Q&A session about pricing & terms

📍 **Meeting Point:** Main entrance/lobby
🚗 Parking available on-site

Have any questions before the viewing? Just reply to this message!

Best regards,  
*{agency_name}*
                """.strip(),
                "triggers": ["viewing", "property", "house", "condo"],
                "follow_up_hours": [2, 24, 72],  # 2h before, 1 day after, 3 days after
            },

            "property_callback_follow_up": {
                "business_type": BusinessType.REAL_ESTATE,
                "reminder_type": ReminderType.PROPERTY_CALLBACK,
                "timing": "24_hours_after",
                "template": """
🏠 *Following Up on Your Property Interest*

Hi {customer_name}!

Thank you for your interest in {property_address}. I wanted to follow up and see if you have any questions about the property we discussed.

🏡 **Property Highlights:**
• {property_features}
• Prime location near {nearby_amenities}  
• {financing_options}

💭 *Common questions I can help with:*
• Financing and loan options
• Legal processes and timeline  
• Neighborhood insights
• Market comparison

📞 Would you like to schedule a call to discuss further? I'm available:
• Today: {available_times_today}
• Tomorrow: {available_times_tomorrow}

Or simply reply with any questions you might have!

Looking forward to helping you find your dream home! 🏡✨

*{agent_name}*  
{agency_name}  
📱 {agent_phone}
                """.strip(),
                "triggers": ["interest", "callback", "follow-up"],
                "follow_up_hours": [48, 168],  # 2 days, 1 week
            },

            # ==================== CONSULTATION TEMPLATES ====================
            "consultation_reminder_2h": {
                "business_type": BusinessType.CONSULTING,
                "reminder_type": ReminderType.CONSULTATION_REMINDER,
                "timing": "2_hours_before",
                "template": """
📋 *Consultation Reminder*

Hello {customer_name}!

Your consultation session is coming up in 2 hours:

⏰ **Today at {consultation_time}**
💼 Session: {consultation_type}
👨‍💼 Consultant: {consultant_name}
🕒 Duration: {session_duration} minutes

📍 **Meeting Details:**
{meeting_details}

📋 **To prepare for our session:**
• Review the documents we discussed
• Prepare your questions/concerns list
• Have your goals clearly in mind

💡 **Zoom/Teams link:** {meeting_link}
📞 **Backup phone:** {consultant_phone}

Looking forward to our productive session!

Best regards,  
*{consultant_name}*  
{company_name}
                """.strip(),
                "triggers": ["consultation", "meeting", "session"],
                "follow_up_hours": [24],  # Follow up 1 day after
            },

            # ==================== AGENT CONFIRMATION TEMPLATES ====================
            "agent_confirmation_request": {
                "business_type": BusinessType.CONSULTING,
                "reminder_type": ReminderType.AGENT_CONFIRMATION,
                "timing": "immediate",
                "template": """
🤝 *Agent Confirmation Required*

Hi {agent_name}!

A new {appointment_type} has been scheduled and requires your confirmation:

📋 **Appointment Details:**
• Customer: {customer_name} ({customer_phone})
• Date & Time: {scheduled_datetime}
• Type: {service_type}
• Duration: {duration} minutes
• Notes: {customer_notes}

📍 **Action Required:**
Please confirm your availability by replying:
• ✅ **CONFIRM** - to accept the appointment
• 🔄 **RESCHEDULE** - to propose new time
• ❌ **DECLINE** - if unavailable

⚠️ Please respond within 2 hours to ensure good customer experience.

*Appointment ID: {appointment_id}*

Dashboard: {dashboard_link}

Thank you!  
*Bijou AI Scheduling System*
                """.strip(),
                "triggers": ["confirmation", "agent", "approval"],
                "follow_up_hours": [2, 4],  # Remind agent if no response
            },

            # ==================== CALENDAR EVENT TEMPLATES ====================
            "calendar_event_reminder": {
                "business_type": BusinessType.CONSULTING,
                "reminder_type": ReminderType.CALENDAR_EVENT,
                "timing": "1_hour_before",
                "template": """
📅 *Event Reminder*

Hi {participant_name}!

Your scheduled event is starting in 1 hour:

🗓️ **{event_title}**
⏰ Time: {event_start_time} - {event_end_time}
📍 Location: {event_location}
👥 Attendees: {attendee_count} people

🔗 **Join Link:** {event_link}
📋 **Agenda:** {event_agenda}

*Need to reschedule?* Reply with "RESCHEDULE" and your preferred times.

See you soon! 👋

*{organizer_name}*
                """.strip(),
                "triggers": ["event", "calendar", "meeting"],
                "follow_up_hours": [],  # No automatic follow-up for calendar events
            },

            # ==================== POST-APPOINTMENT TEMPLATES ====================
            "post_appointment_feedback": {
                "business_type": BusinessType.CONSULTING,
                "reminder_type": ReminderType.POST_APPOINTMENT,
                "timing": "4_hours_after",
                "template": """
⭐ *How was your experience?*

Hi {customer_name}!

Thank you for choosing {business_name} today. We hope you had a great experience!

📝 **Quick feedback (takes 30 seconds):**
Rate your experience: 
⭐⭐⭐⭐⭐ (Reply with 1-5 stars)

💬 **Tell us:**
• What went well?
• Any suggestions for improvement?
• Would you recommend us to friends?

🎁 **Special offer:** As a thank you, here's a 10% discount for your next visit: {discount_code}

📞 Any concerns? Call us directly: {business_phone}

We appreciate your business! 🙏

*{business_name} Team*
                """.strip(),
                "triggers": ["feedback", "review", "post-visit"],
                "follow_up_hours": [72, 168],  # 3 days, 1 week for retention
            },
        }
    
    def _load_scheduling_rules(self) -> Dict[str, Any]:
        """Load intelligent scheduling rules based on business type and customer behavior"""
        return {
            "dental_clinic": {
                "optimal_reminder_times": [24, 2],  # 24 hours and 2 hours before
                "no_show_follow_up": 2,  # Hours after missed appointment
                "satisfaction_follow_up": 4,  # Hours after appointment
                "next_checkup_reminder": 4320,  # 3 months (in hours)
            },
            "real_estate": {
                "viewing_reminder_times": [24, 2],
                "interest_follow_up": [24, 72, 168],  # 1 day, 3 days, 1 week
                "hot_lead_response": 1,  # 1 hour for hot leads
                "callback_schedule": [48, 120, 336],  # 2 days, 5 days, 2 weeks
            },
            "consulting": {
                "session_reminders": [24, 2, 0.25],  # 24h, 2h, 15min before
                "confirmation_timeout": 2,  # Agent must confirm within 2 hours
                "follow_up_sequence": [24, 72, 168],  # 1 day, 3 days, 1 week
                "satisfaction_survey": 4,  # 4 hours after session
            }
        }
    
    async def schedule_appointment_reminders(
        self, 
        customer_jid: str,
        tenant_id: str,
        appointment_details: Dict[str, Any],
        business_type: BusinessType
    ) -> List[str]:
        """
        Schedule comprehensive appointment reminders based on business type
        
        Returns:
            List of scheduled reminder IDs
        """
        try:
            reminder_ids = []
            appointment_time = datetime.fromisoformat(appointment_details["scheduled_time"])
            
            # Get business-specific rules
            rules = self.scheduling_rules.get(business_type.value, {})
            reminder_times = rules.get("optimal_reminder_times", [24, 2])
            
            # Schedule pre-appointment reminders
            for hours_before in reminder_times:
                remind_time = appointment_time - timedelta(hours=hours_before)
                
                # Only schedule if remind time is in the future
                if remind_time > datetime.now():
                    reminder_id = await self._schedule_reminder(
                        customer_jid=customer_jid,
                        tenant_id=tenant_id,
                        reminder_type=ReminderType.CONSULTATION_REMINDER,
                        scheduled_time=remind_time,
                        template_data=appointment_details,
                        business_type=business_type
                    )
                    reminder_ids.append(reminder_id)
            
            # Schedule post-appointment follow-ups
            follow_up_hours = rules.get("follow_up_sequence", [24, 72])
            for hours_after in follow_up_hours:
                follow_up_time = appointment_time + timedelta(hours=hours_after)
                
                reminder_id = await self._schedule_reminder(
                    customer_jid=customer_jid,
                    tenant_id=tenant_id,
                    reminder_type=ReminderType.POST_APPOINTMENT,
                    scheduled_time=follow_up_time,
                    template_data=appointment_details,
                    business_type=business_type
                )
                reminder_ids.append(reminder_id)
            
            logger.info(f"✅ Scheduled {len(reminder_ids)} reminders for appointment {appointment_details.get('id', 'unknown')}")
            return reminder_ids
            
        except Exception as e:
            logger.error(f"❌ Error scheduling appointment reminders: {e}")
            return []
    
    async def schedule_agent_confirmation(
        self,
        agent_jid: str,
        tenant_id: str,
        appointment_details: Dict[str, Any],
        timeout_hours: int = 2
    ) -> str:
        """
        Schedule agent confirmation request with automatic escalation
        
        Returns:
            Confirmation request ID
        """
        try:
            # Send immediate confirmation request
            confirmation_id = str(uuid.uuid4())
            
            template_data = {
                **appointment_details,
                "agent_name": appointment_details.get("agent_name", "Agent"),
                "appointment_id": confirmation_id,
                "dashboard_link": f"https://{self.bijou.get_domain()}/dashboard"
            }
            
            # Send confirmation request
            await self._send_template_message(
                recipient=agent_jid,
                template_key="agent_confirmation_request",
                template_data=template_data,
                business_type=BusinessType.CONSULTING
            )
            
            # Schedule escalation if no response
            escalation_time = datetime.now() + timedelta(hours=timeout_hours)
            await self._schedule_reminder(
                customer_jid=agent_jid,
                tenant_id=tenant_id,
                reminder_type=ReminderType.AGENT_CONFIRMATION,
                scheduled_time=escalation_time,
                template_data=template_data,
                business_type=BusinessType.CONSULTING,
                is_escalation=True
            )
            
            logger.info(f"📋 Sent agent confirmation request {confirmation_id} to {agent_jid}")
            return confirmation_id
            
        except Exception as e:
            logger.error(f"❌ Error scheduling agent confirmation: {e}")
            return ""
    
    async def schedule_business_specific_follow_up(
        self,
        customer_jid: str,
        tenant_id: str,
        interaction_type: str,
        customer_data: Dict[str, Any],
        business_type: BusinessType
    ) -> List[str]:
        """
        Schedule intelligent follow-ups based on business type and customer interaction
        
        Args:
            interaction_type: "property_inquiry", "dental_visit", "consultation_request", etc.
            
        Returns:
            List of scheduled follow-up IDs
        """
        try:
            follow_up_ids = []
            
            # Determine follow-up sequence based on business type and interaction
            if business_type == BusinessType.REAL_ESTATE and interaction_type == "property_inquiry":
                # Real estate follow-up sequence
                follow_up_times = [24, 72, 168]  # 1 day, 3 days, 1 week
                template_keys = ["property_callback_follow_up", "property_callback_follow_up", "property_callback_follow_up"]
                
            elif business_type == BusinessType.DENTAL_CLINIC and interaction_type == "appointment_completed":
                # Dental follow-up sequence
                follow_up_times = [2, 24, 4320]  # 2 hours, 1 day, 3 months
                template_keys = ["dental_follow_up_post", "dental_follow_up_post", "dental_checkup_24h"]
                
            elif business_type == BusinessType.CONSULTING and interaction_type == "consultation_inquiry":
                # Consulting follow-up sequence
                follow_up_times = [24, 72, 168]  # 1 day, 3 days, 1 week
                template_keys = ["consultation_reminder_2h", "consultation_reminder_2h", "post_appointment_feedback"]
                
            else:
                # Default follow-up
                follow_up_times = [24, 168]  # 1 day, 1 week
                template_keys = ["post_appointment_feedback", "post_appointment_feedback"]
            
            # Schedule each follow-up
            for i, hours_later in enumerate(follow_up_times):
                follow_up_time = datetime.now() + timedelta(hours=hours_later)
                template_key = template_keys[i] if i < len(template_keys) else template_keys[-1]
                
                reminder_id = await self._schedule_reminder(
                    customer_jid=customer_jid,
                    tenant_id=tenant_id,
                    reminder_type=ReminderType.PROPERTY_CALLBACK if "property" in interaction_type else ReminderType.POST_APPOINTMENT,
                    scheduled_time=follow_up_time,
                    template_data=customer_data,
                    business_type=business_type,
                    custom_template_key=template_key
                )
                follow_up_ids.append(reminder_id)
            
            logger.info(f"📅 Scheduled {len(follow_up_ids)} business follow-ups for {interaction_type}")
            return follow_up_ids
            
        except Exception as e:
            logger.error(f"❌ Error scheduling business follow-ups: {e}")
            return []
    
    async def _schedule_reminder(
        self,
        customer_jid: str,
        tenant_id: str,
        reminder_type: ReminderType,
        scheduled_time: datetime,
        template_data: Dict[str, Any],
        business_type: BusinessType,
        is_escalation: bool = False,
        custom_template_key: Optional[str] = None
    ) -> str:
        """Schedule a single reminder in the database"""
        try:
            reminder_id = str(uuid.uuid4())
            
            # Prepare reminder data
            reminder_data = {
                "id": reminder_id,
                "tenant_id": tenant_id,
                "recipient": customer_jid,
                "message_type": "business_reminder",
                "content": json.dumps({
                    "reminder_type": reminder_type.value,
                    "business_type": business_type.value,
                    "template_data": template_data,
                    "is_escalation": is_escalation,
                    "custom_template_key": custom_template_key
                }),
                "scheduled_time": scheduled_time.isoformat(),
                "status": "pending",
                "metadata": json.dumps({
                    "business_type": business_type.value,
                    "reminder_type": reminder_type.value,
                    "created_at": datetime.now().isoformat()
                })
            }
            
            # Insert into database
            if self.bijou.db_type == "supabase":
                try:
                    result = self.bijou.db_conn.table("scheduled_messages").insert(reminder_data).execute()
                except Exception as db_error:
                    if "could not find" in str(db_error).lower():
                        logger.warning(f"⚠️ Skipping reminder insert due to schema issue: {db_error}")
                        return reminder_id  # Return ID but skip insert until schema is fixed
                    else:
                        raise db_error
            else:
                # SQLite
                cursor = self.bijou.db_conn.cursor()
                cursor.execute("""
                    INSERT INTO scheduled_messages 
                    (id, tenant_id, recipient, message_type, content, scheduled_time, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    reminder_data["id"],
                    reminder_data["tenant_id"],
                    reminder_data["recipient"],
                    reminder_data["message_type"],
                    reminder_data["content"],
                    reminder_data["scheduled_time"],
                    reminder_data["status"],
                    reminder_data["metadata"]
                ))
                self.bijou.db_conn.commit()
            
            return reminder_id
            
        except Exception as e:
            logger.error(f"❌ Error scheduling reminder: {e}")
            return ""
    
    async def _send_template_message(
        self,
        recipient: str,
        template_key: str,
        template_data: Dict[str, Any],
        business_type: BusinessType
    ) -> bool:
        """Send a templated message immediately"""
        try:
            template = self.reminder_templates.get(template_key)
            if not template:
                logger.error(f"❌ Template {template_key} not found")
                return False
            
            # Format template with data
            message = template["template"].format(**template_data)
            
            # Send via WhatsApp bridge
            bridge_adapter = self.bijou.get_bridge_adapter()
            if bridge_adapter:
                success = bridge_adapter.send_text(recipient, message)
                if success:
                    logger.info(f"📤 Sent template message {template_key} to {recipient}")
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error sending template message: {e}")
            return False
    
    async def process_scheduled_reminders(self) -> int:
        """
        Process all pending reminders that are due to be sent
        Called by the main polling loop every minute
        
        Returns:
            Number of reminders processed
        """
        try:
            now = datetime.now()
            processed_count = 0
            
            # Get pending reminders that are due
            if self.bijou.db_type == "supabase":
                try:
                    result = self.bijou.db_conn.table("scheduled_messages").select("*").eq("status", "pending").lte("scheduled_time", now.isoformat()).execute()  # noaudit - system scheduler: intentionally loads all tenants' due reminders; each processed per-tenant via reminder['tenant_id']
                    pending_reminders = result.data or []
                except Exception as db_error:
                    if "could not find" in str(db_error).lower() or "status" in str(db_error).lower():
                        logger.warning(f"⚠️ scheduled_messages table schema incomplete: {db_error}")
                        return 0  # Skip processing until schema is fixed
                    else:
                        raise db_error
            else:
                cursor = self.bijou.db_conn.cursor()
                cursor.execute("""
                    SELECT * FROM scheduled_messages 
                    WHERE status = 'pending' AND scheduled_time <= ?
                """, (now.isoformat(),))
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                pending_reminders = [dict(zip(columns, row)) for row in rows]
            
            # Process each reminder
            for reminder in pending_reminders:
                success = await self._process_single_reminder(reminder)
                if success:
                    processed_count += 1
            
            if processed_count > 0:
                logger.info(f"📬 Processed {processed_count} scheduled reminders")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"❌ Error processing scheduled reminders: {e}")
            return 0
    
    async def _process_single_reminder(self, reminder: Dict[str, Any]) -> bool:
        """Process a single reminder"""
        try:
            content = json.loads(reminder["content"])
            template_data = content.get("template_data", {})
            reminder_type = content.get("reminder_type", "")
            business_type = content.get("business_type", "")
            custom_template_key = content.get("custom_template_key")
            
            # Determine template key
            template_key = custom_template_key
            if not template_key:
                # Map reminder type to template key
                if reminder_type == "dental_checkup":
                    template_key = "dental_checkup_24h"
                elif reminder_type == "property_viewing":
                    template_key = "property_viewing_24h"
                elif reminder_type == "consultation_reminder":
                    template_key = "consultation_reminder_2h"
                elif reminder_type == "agent_confirmation":
                    template_key = "agent_confirmation_request"
                elif reminder_type == "post_appointment":
                    template_key = "post_appointment_feedback"
                else:
                    template_key = "consultation_reminder_2h"  # Default
            
            # Send the reminder
            success = await self._send_template_message(
                recipient=reminder["recipient"],
                template_key=template_key,
                template_data=template_data,
                business_type=BusinessType(business_type) if business_type else BusinessType.CONSULTING
            )
            
            # Update reminder status
            new_status = "sent" if success else "failed"
            if self.bijou.db_type == "supabase":
                self.bijou.db_conn.table("scheduled_messages").update({
                    "status": new_status,
                    "sent_at": datetime.now().isoformat() if success else None
                }).eq("tenant_id", reminder["tenant_id"]).eq("id", reminder["id"]).execute()
            else:
                cursor = self.bijou.db_conn.cursor()
                cursor.execute("""
                    UPDATE scheduled_messages 
                    SET status = ?, sent_at = ?
                    WHERE id = ?
                """, (new_status, datetime.now().isoformat() if success else None, reminder["id"]))
                self.bijou.db_conn.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error processing reminder {reminder.get('id', 'unknown')}: {e}")
            return False