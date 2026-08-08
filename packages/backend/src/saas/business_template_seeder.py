#!/usr/bin/env python3
"""
Business-Specific Template Seeder
===============================

Automatically seeds appropriate message templates based on business type:
- Dental clinics: Appointment reminders, post-treatment care, checkup follow-ups
- Real estate: Property viewing reminders, callback scheduling, market updates  
- Consulting: Session reminders, agent confirmations, feedback collection
- Healthcare: Appointment reminders, medication reminders, health checkups
- Education: Class reminders, assignment deadlines, progress updates
- Retail: Order confirmations, delivery updates, loyalty programs

Author: W3J Bijou Enterprise
"""

import logging
from typing import Dict, List, Optional, Any
from src.core.advanced_reminder_system import BusinessType, ReminderType
import json

logger = logging.getLogger(__name__)


class BusinessTemplateSeeder:
    """Seeds business-specific templates based on detected business type"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.business_templates = self._load_all_business_templates()
    
    def _load_all_business_templates(self) -> Dict[str, List[Dict]]:
        """Load all business-specific templates organized by business type"""
        return {
            BusinessType.DENTAL_CLINIC.value: [
                {
                    "template_name": "Dental Appointment Reminder (24h)",
                    "category": "appointment_reminder",
                    "trigger_mode": "scheduled",
                    "trigger_keywords": ["appointment", "dental", "checkup", "cleaning", "tomorrow"],
                    "template_content": """
🦷 *Dental Appointment Reminder*

Hello {customer_name}! 👋

Just a friendly reminder that you have a dental appointment scheduled:

📅 **Tomorrow at {appointment_time}**
📍 {clinic_address}
👨‍⚕️ Dr. {doctor_name}

*What to bring:*
• IC/Passport for verification
• Previous dental records (if any)
• Insurance card (if applicable)

⏰ Please arrive 15 minutes early for check-in.

If you need to reschedule, please call us at {clinic_phone} or reply to this message.

Looking forward to seeing you! 😊

_Regards,_  
*{clinic_name}*
                    """.strip(),
                    "source": "bijou_business_templates",
                },
                {
                    "template_name": "Post-Treatment Care Instructions",
                    "category": "post_treatment",
                    "trigger_mode": "keyword_auto",
                    "trigger_keywords": ["treatment", "completed", "care", "instructions", "aftercare"],
                    "template_content": """
🦷 *Post-Treatment Care Instructions*

Hi {customer_name}!

Thank you for visiting {clinic_name} today. Here are your important care instructions:

💡 **For the next 24 hours:**
• Avoid hard or sticky foods
• Don't rinse vigorously or use straws
• Take prescribed medication as directed
• Apply ice pack for 15 minutes if swelling occurs

🚨 **Contact us immediately if you experience:**
• Severe pain that doesn't improve
• Excessive bleeding
• Signs of infection (fever, pus)
• Unusual swelling

📞 Emergency contact: {clinic_phone}
📅 Next appointment: {next_appointment}

We're here to support your dental health! 🦷✨

*{clinic_name} Team*
                    """.strip(),
                    "source": "bijou_business_templates",
                },
                {
                    "template_name": "6-Month Checkup Reminder",
                    "category": "follow_up",
                    "trigger_mode": "scheduled",
                    "trigger_keywords": ["checkup", "6 month", "routine", "cleaning", "examination"],
                    "template_content": """
🦷 *Time for Your 6-Month Checkup!*

Hello {customer_name}!

It's been 6 months since your last dental visit. Time flies when you're maintaining that beautiful smile! 😊

🗓️ **Why regular checkups matter:**
• Early detection of potential issues
• Professional cleaning for optimal oral health
• Personalized advice for your dental care

📅 **Book your appointment today:**
• Call us: {clinic_phone}
• WhatsApp: Reply "BOOK APPOINTMENT"
• Online: {booking_link}

🎁 **Special offer:** Mention this message for 10% off your cleaning!

We look forward to seeing you soon!

*Dr. {doctor_name} & Team*  
{clinic_name}
                    """.strip(),
                    "source": "bijou_business_templates",
                }
            ],
            
            BusinessType.REAL_ESTATE.value: [
                {
                    "template_name": "Property Viewing Reminder",
                    "category": "appointment_reminder", 
                    "trigger_mode": "scheduled",
                    "trigger_keywords": ["viewing", "property", "house", "condo", "tomorrow"],
                    "template_content": """
🏠 *Property Viewing Reminder*

Hello {customer_name}!

Hope you're excited about tomorrow's property viewing! 🗝️

📅 **Tomorrow at {viewing_time}**
📍 {property_address}
🏡 {property_type} - {bedrooms} bed, {bathrooms} bath
💰 Price: RM {property_price}

👨‍💼 Your agent: {agent_name} ({agent_phone})

📍 **Meeting Point:** Main entrance/lobby
🚗 Parking available on-site

**What to expect:**
• Full property walkthrough (~30 minutes)
• Neighborhood highlights tour
• Discussion about financing options

Any questions? Just reply to this message!

*{agency_name}*
                    """.strip(),
                    "source": "bijou_business_templates",
                },
                {
                    "template_name": "Property Interest Follow-up",
                    "category": "follow_up",
                    "trigger_mode": "keyword_auto", 
                    "trigger_keywords": ["interested", "like", "love", "want", "buy", "purchase"],
                    "template_content": """
🏡 *Following Up on Your Property Interest*

Hi {customer_name}!

Thank you for your interest in {property_address}! I'm here to help make your dream home a reality.

💭 **Common questions I can help with:**
• Loan eligibility and financing options
• Legal process and timeline
• Neighborhood insights and amenities
• Market analysis and price comparison

📞 **Let's schedule a call:**
• Today: {available_today}
• Tomorrow: {available_tomorrow}

🎯 **Next steps:**
• Complete property evaluation
• Financing pre-approval assistance
• Negotiation and closing support

Reply with your preferred time or any questions!

*{agent_name}*  
{agency_name}  
📱 {agent_phone}
                    """.strip(),
                    "source": "bijou_business_templates",
                },
                {
                    "template_name": "Market Update Newsletter",
                    "category": "newsletter",
                    "trigger_mode": "scheduled",
                    "trigger_keywords": ["market", "update", "newsletter", "trends", "prices"],
                    "template_content": """
📊 *Monthly Market Update - {month} {year}*

Hi {customer_name}!

Here's your personalized market update for {area}:

📈 **Market Highlights:**
• Average price: RM {average_price} ({price_trend})
• Properties sold: {properties_sold} units
• Average days on market: {days_on_market}

🏘️ **Your Area Focus - {customer_area}:**
• New listings: {new_listings}
• Price range: RM {price_range}
• Hot properties: {hot_properties}

💡 **Market Insight:**
{market_analysis}

🔔 **New Matching Properties:**
I found {matching_count} new properties that match your criteria!

Want to see them? Reply "SHOW PROPERTIES" 

*{agent_name}*  
{agency_name}
                    """.strip(),
                    "source": "bijou_business_templates",
                }
            ],
            
            BusinessType.CONSULTING.value: [
                {
                    "template_name": "Consultation Session Reminder",
                    "category": "appointment_reminder",
                    "trigger_mode": "scheduled", 
                    "trigger_keywords": ["consultation", "session", "meeting", "appointment", "tomorrow"],
                    "template_content": """
📋 *Consultation Reminder*

Hello {customer_name}!

Your consultation session is coming up tomorrow:

⏰ **Tomorrow at {consultation_time}**
💼 Session: {consultation_type}
👨‍💼 Consultant: {consultant_name}
🕒 Duration: {session_duration} minutes

📍 **Meeting Details:**
{meeting_location}
💻 Zoom link: {meeting_link}

📋 **To prepare:**
• Review materials we discussed
• Prepare your questions/objectives list
• Have your current situation summary ready

📞 **Need to reschedule?** Call {consultant_phone} or reply here.

Looking forward to our productive session!

*{consultant_name}*  
{company_name}
                    """.strip(),
                    "source": "bijou_business_templates",
                },
                {
                    "template_name": "Post-Session Action Plan",
                    "category": "follow_up",
                    "trigger_mode": "keyword_auto",
                    "trigger_keywords": ["session", "completed", "action", "plan", "next steps"],
                    "template_content": """
✅ *Your Action Plan - Session Follow-up*

Hi {customer_name}!

Great session today! Here's your personalized action plan:

📋 **Key Takeaways:**
{session_summary}

🎯 **Your Next Steps:**
1. {action_item_1}
2. {action_item_2}  
3. {action_item_3}

⏰ **Timeline:**
• Week 1: {week_1_goals}
• Week 2-4: {month_goals}

📅 **Follow-up Schedule:**
• Check-in call: {followup_date}
• Progress review: {review_date}

📎 **Resources shared:**
{shared_resources}

Questions? I'm here to help! 💪

*{consultant_name}*  
{company_name}
                    """.strip(),
                    "source": "bijou_business_templates",
                }
            ],
            
            BusinessType.HEALTHCARE.value: [
                {
                    "template_name": "Medical Appointment Reminder",
                    "category": "appointment_reminder",
                    "trigger_mode": "scheduled",
                    "trigger_keywords": ["appointment", "medical", "doctor", "checkup", "tomorrow"],
                    "template_content": """
🏥 *Medical Appointment Reminder*

Dear {patient_name},

You have a medical appointment scheduled:

📅 **Tomorrow at {appointment_time}**
👩‍⚕️ Dr. {doctor_name} - {specialty}
📍 {clinic_address}
🏥 {clinic_name}

📋 **Please bring:**
• IC and insurance card
• List of current medications
• Previous medical reports (if any)
• Referral letter (if applicable)

⏰ Arrive 15 minutes early for registration.

🚗 **Parking:** {parking_info}

Need to reschedule? Call {clinic_phone}

Take care!  
*{clinic_name} Team*
                    """.strip(),
                    "source": "bijou_business_templates",
                },
                {
                    "template_name": "Medication Reminder",
                    "category": "medication",
                    "trigger_mode": "scheduled",
                    "trigger_keywords": ["medication", "medicine", "pills", "prescription", "refill"],
                    "template_content": """
💊 *Medication Reminder*

Hello {patient_name}!

Time for your medication reminder:

💊 **{medication_name}**
⏰ Take: {dosage} at {medication_time}
🍽️ {food_instruction}

📋 **Important notes:**
{medication_instructions}

📅 **Prescription status:**
• Pills remaining: ~{pills_left}
• Refill needed by: {refill_date}

🏥 Need a refill? Reply "REFILL" or call {clinic_phone}

Stay healthy! 💪  
*{clinic_name}*
                    """.strip(),
                    "source": "bijou_business_templates",
                }
            ],
            
            BusinessType.EDUCATION.value: [
                {
                    "template_name": "Class Reminder",
                    "category": "class_reminder",
                    "trigger_mode": "scheduled", 
                    "trigger_keywords": ["class", "lesson", "course", "tomorrow", "session"],
                    "template_content": """
📚 *Class Reminder*

Hi {student_name}!

Your class is coming up tomorrow:

📅 **Tomorrow at {class_time}**
📖 Subject: {subject_name}
👨‍🏫 Instructor: {instructor_name}
📍 {classroom_location}

📋 **For tomorrow's class:**
• Topic: {class_topic}
• Materials needed: {materials_list}
• Homework due: {homework_due}

💡 **Preparation tip:**
{preparation_note}

📚 Don't forget to bring your {required_items}!

See you in class! 🎓  
*{school_name}*
                    """.strip(),
                    "source": "bijou_business_templates",
                },
                {
                    "template_name": "Assignment Due Reminder", 
                    "category": "assignment",
                    "trigger_mode": "scheduled",
                    "trigger_keywords": ["assignment", "homework", "due", "deadline", "submit"],
                    "template_content": """
📝 *Assignment Due Reminder*

Hi {student_name}!

Friendly reminder about your upcoming assignment:

📋 **Assignment:** {assignment_title}
📅 **Due date:** {due_date} at {due_time}
📍 **Submit to:** {submission_method}

✅ **Requirements checklist:**
• {requirement_1}
• {requirement_2}
• {requirement_3}

💡 **Need help?**
• Office hours: {office_hours}
• Email: {instructor_email}
• Study group: {study_group_info}

You've got this! 💪📚  
*{instructor_name}*
                    """.strip(),
                    "source": "bijou_business_templates",
                }
            ],
            
            BusinessType.RETAIL.value: [
                {
                    "template_name": "Order Confirmation",
                    "category": "order_status",
                    "trigger_mode": "keyword_auto",
                    "trigger_keywords": ["order", "purchase", "buy", "checkout", "confirm"],
                    "template_content": """
🛍️ *Order Confirmed!*

Hi {customer_name}!

Thank you for your order! Here are the details:

🛒 **Order #{order_number}**
📅 Order date: {order_date}
💰 Total: RM {order_total}

📦 **Items ordered:**
{order_items}

🚚 **Delivery information:**
• Address: {delivery_address}
• Estimated delivery: {delivery_date}
• Tracking: {tracking_number}

💳 **Payment:** {payment_method} - ✅ Confirmed

📲 Track your order: {tracking_link}

Questions? Reply here or call {store_phone}

Thank you for choosing {store_name}! 🙏  
*{store_name} Team*
                    """.strip(),
                    "source": "bijou_business_templates",
                },
                {
                    "template_name": "Delivery Update",
                    "category": "delivery",
                    "trigger_mode": "scheduled",
                    "trigger_keywords": ["delivery", "shipped", "tracking", "package", "courier"],
                    "template_content": """
🚚 *Delivery Update*

Hi {customer_name}!

Great news! Your order is on the way:

📦 **Order #{order_number}**
🚚 **Status:** {delivery_status}
📅 **Estimated delivery:** {delivery_date}
⏰ **Time window:** {delivery_time_window}

📍 **Delivery address:**
{delivery_address}

📱 **Courier contact:** {courier_phone}
🔍 **Real-time tracking:** {tracking_link}

💡 **Delivery tips:**
• Please be available during the time window
• Have your IC ready for verification
• Someone 18+ must be present to receive

Excited for you to receive your items! 🎉  
*{store_name}*
                    """.strip(),
                    "source": "bijou_business_templates",
                }
            ]
        }
    
    async def seed_business_templates(
        self, 
        tenant_id: str, 
        business_type: BusinessType,
        force_reseed: bool = False
    ) -> Dict[str, Any]:
        """
        Seed templates specific to the business type
        
        Args:
            tenant_id: Tenant to seed templates for
            business_type: Type of business to determine templates
            force_reseed: Whether to overwrite existing templates
            
        Returns:
            Summary of seeding operation
        """
        try:
            logger.info(f"🌱 Seeding {business_type.value} templates for tenant {tenant_id}")
            
            templates_to_seed = self.business_templates.get(business_type.value, [])
            if not templates_to_seed:
                logger.warning(f"⚠️ No templates defined for business type: {business_type.value}")
                return {"seeded": 0, "skipped": 0, "warnings": ["No templates available for business type"]}
            
            seeded_count = 0
            skipped_count = 0
            warnings = []
            
            # Check existing templates if not force reseeding
            existing_templates = []
            if not force_reseed:
                try:
                    result = self.supabase.table("message_templates").select("template_name").eq("tenant_id", tenant_id).execute()
                    existing_templates = [t["template_name"] for t in (result.data or [])]
                except Exception as e:
                    logger.warning(f"⚠️ Could not check existing templates: {e}")
            
            # Seed each template
            for template in templates_to_seed:
                template_name = template["template_name"]
                
                # Skip if already exists and not force reseeding
                if not force_reseed and template_name in existing_templates:
                    logger.debug(f"⏭️ Skipping '{template_name}' - already exists")
                    skipped_count += 1
                    continue
                
                # Prepare template data
                template_data = {
                    "tenant_id": tenant_id,
                    "template_name": template_name,
                    "category": template["category"],
                    "template_content": template["template_content"],
                    "trigger_mode": template["trigger_mode"],
                    "trigger_keywords": template.get("trigger_keywords", []),
                    "source": template["source"],
                    "is_active": True,
                    "business_type": business_type.value,
                    "created_at": "now()"
                }
                
                try:
                    # Insert or update template
                    if force_reseed and template_name in existing_templates:
                        # Update existing template
                        result = self.supabase.table("message_templates").update(template_data).eq("tenant_id", tenant_id).eq("template_name", template_name).execute()
                    else:
                        # Insert new template  
                        result = self.supabase.table("message_templates").insert(template_data).execute()
                    
                    logger.info(f"✅ Seeded template '{template_name}'")
                    seeded_count += 1
                    
                except Exception as e:
                    error_msg = f"Failed to seed template '{template_name}': {e}"
                    logger.error(f"❌ {error_msg}")
                    warnings.append(error_msg)
            
            # Create summary
            summary = {
                "business_type": business_type.value,
                "seeded": seeded_count,
                "skipped": skipped_count, 
                "warnings": warnings,
                "total_available": len(templates_to_seed)
            }
            
            logger.info(f"📊 Template seeding complete: {seeded_count} seeded, {skipped_count} skipped")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error seeding business templates: {e}")
            return {"seeded": 0, "skipped": 0, "warnings": [str(e)]}
    
    async def detect_and_seed_business_type(
        self, 
        tenant_id: str, 
        business_indicators: Dict[str, Any]
    ) -> Optional[BusinessType]:
        """
        Automatically detect business type from indicators and seed appropriate templates
        
        Args:
            tenant_id: Tenant ID to seed for
            business_indicators: Dict with keys like 'name', 'description', 'keywords', 'industry'
            
        Returns:
            Detected business type or None if unclear
        """
        try:
            # Extract text for analysis
            text_to_analyze = " ".join([
                str(business_indicators.get("name", "")),
                str(business_indicators.get("description", "")), 
                str(business_indicators.get("industry", "")),
                " ".join(business_indicators.get("keywords", []))
            ]).lower()
            
            # Business type detection logic
            business_type = None
            
            if any(keyword in text_to_analyze for keyword in [
                "dental", "dentist", "teeth", "oral", "clinic dental", "gigi", "orthodontic"
            ]):
                business_type = BusinessType.DENTAL_CLINIC
                
            elif any(keyword in text_to_analyze for keyword in [
                "property", "real estate", "house", "condo", "apartment", "development", "broker", "agent"
            ]):
                business_type = BusinessType.REAL_ESTATE
                
            elif any(keyword in text_to_analyze for keyword in [
                "consulting", "consultant", "advisory", "business coach", "strategy", "coaching"
            ]):
                business_type = BusinessType.CONSULTING
                
            elif any(keyword in text_to_analyze for keyword in [
                "medical", "doctor", "hospital", "clinic", "healthcare", "physician", "health"
            ]):
                business_type = BusinessType.HEALTHCARE
                
            elif any(keyword in text_to_analyze for keyword in [
                "school", "education", "tuition", "class", "course", "teacher", "learning"
            ]):
                business_type = BusinessType.EDUCATION
                
            elif any(keyword in text_to_analyze for keyword in [
                "shop", "store", "retail", "ecommerce", "sell", "product", "inventory"
            ]):
                business_type = BusinessType.RETAIL
            
            if business_type:
                logger.info(f"🔍 Detected business type: {business_type.value} for tenant {tenant_id}")
                
                # Automatically seed templates
                await self.seed_business_templates(tenant_id, business_type)
                
                # Update tenant record with business type
                try:
                    self.supabase.table("tenants").update({
                        "business_type": business_type.value,
                        "auto_templates_seeded": True,
                        "templates_seeded_at": "now()"
                    }).eq("id", tenant_id).execute()
                except Exception as e:
                    logger.warning(f"⚠️ Could not update tenant business type: {e}")
                
                return business_type
            else:
                logger.info(f"🤔 Could not detect business type for tenant {tenant_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error detecting business type: {e}")
            return None