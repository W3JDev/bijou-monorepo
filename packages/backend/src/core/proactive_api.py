#!/usr/bin/env python3
"""
Proactive Messaging API Endpoints
===================================

REST API for managing proactive messaging campaigns, schedules, and rules.

Author: W3J Bijou AI
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.core.dashboard_api_simple import verify_session

router = APIRouter(prefix="/api/proactive", tags=["proactive-messaging"])


# ==================== DEPENDENCY ====================

def get_proactive_system(request: Request):
    """Dependency to get the proactive messaging system from app state"""
    import logging
    logger = logging.getLogger(__name__)
    
    bijou = getattr(request.app.state, 'bijou', None)
    
    logger.info(f"🔍 get_proactive_system: bijou={bijou is not None}")
    if bijou:
        logger.info(f"🔍 get_proactive_system: proactive_messaging={bijou.proactive_messaging is not None}")
    
    if not bijou or not bijou.proactive_messaging:
        raise HTTPException(status_code=503, detail="Proactive messaging not available")
    
    return bijou.proactive_messaging


# ==================== REQUEST/RESPONSE MODELS ====================

class ScheduleMessageRequest(BaseModel):
    """Request to schedule a message"""
    recipient: str
    message_type: str  # lead_followup, silence_reengagement, campaign, reminder, custom
    content: str
    delay_minutes: int = 0
    metadata: Optional[dict] = None


class CreateCampaignRequest(BaseModel):
    """Request to create a campaign"""
    name: str
    message_template: str
    target_segment: str  # all, active, inactive, custom
    scheduled_time: datetime
    recipients: Optional[List[str]] = None


class SetSilenceRuleRequest(BaseModel):
    """Request to set a silence detection rule"""
    silence_days: int
    message_template: str


class MessageResponse(BaseModel):
    """Response for scheduled message"""
    id: str
    tenant_id: str
    recipient: str
    message_type: str
    content: str
    scheduled_time: datetime
    status: str


class CampaignResponse(BaseModel):
    """Response for campaign"""
    id: str
    tenant_id: str
    name: str
    message_template: str
    target_segment: str
    scheduled_time: datetime
    status: str
    recipient_count: int
    sent_count: int
    failed_count: int


# ==================== API ENDPOINTS ====================

@router.get("/status")
async def get_status():
    """Get proactive messaging system status"""
    from src.core.bijou import bijou_instance
    
    return {
        "bijou_instance_exists": bijou_instance is not None,
        "proactive_messaging_exists": bijou_instance.proactive_messaging is not None if bijou_instance else False,
        "system_active": bijou_instance.proactive_messaging._running if (bijou_instance and bijou_instance.proactive_messaging) else False
    }


@router.post("/schedule", response_model=MessageResponse)
async def schedule_message(
    req: ScheduleMessageRequest,
    tenant_id: str = Depends(verify_session),
    system = Depends(get_proactive_system)
):
    """
    Schedule a message to be sent later.
    
    Example:
    ```json
    {
      "recipient": "60123456789@s.whatsapp.net",
      "message_type": "lead_followup",
      "content": "Hi! Just following up on your inquiry...",
      "delay_minutes": 1440
    }
    ```
    """
    try:
        from src.core.proactive_messaging import MessageType
        
        msg_type = MessageType(req.message_type)
        
        msg = await system.schedule_message(
            tenant_id=tenant_id,
            recipient=req.recipient,
            message_type=msg_type,
            content=req.content,
            delay_minutes=req.delay_minutes,
            metadata=req.metadata
        )
        
        return MessageResponse(
            id=msg.id,
            tenant_id=msg.tenant_id,
            recipient=msg.recipient,
            message_type=msg.message_type.value,
            content=msg.content,
            scheduled_time=msg.scheduled_time,
            status=msg.status.value
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaign", response_model=CampaignResponse)
async def create_campaign(
    req: CreateCampaignRequest,
    tenant_id: str = Depends(verify_session),
    system = Depends(get_proactive_system)
):
    """
    Create a new marketing campaign.
    
    Example:
    ```json
    {
      "name": "New Year Promo",
      "message_template": "Happy New Year! Get 20% off...",
      "target_segment": "all",
      "scheduled_time": "2026-01-01T00:00:00Z"
    }
    ```
    """
    try:
        campaign = await system.create_campaign(
            tenant_id=tenant_id,
            name=req.name,
            message_template=req.message_template,
            target_segment=req.target_segment,
            scheduled_time=req.scheduled_time,
            recipients=req.recipients
        )
        
        return CampaignResponse(
            id=campaign.id,
            tenant_id=campaign.tenant_id,
            name=campaign.name,
            message_template=campaign.message_template,
            target_segment=campaign.target_segment,
            scheduled_time=campaign.scheduled_time,
            status=campaign.status.value,
            recipient_count=len(campaign.recipients),
            sent_count=campaign.sent_count,
            failed_count=campaign.failed_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/silence-rule")
async def set_silence_rule(
    req: SetSilenceRuleRequest,
    tenant_id: str = Depends(verify_session),
    system = Depends(get_proactive_system)
):
    """
    Set up silence detection and auto-reengagement.
    
    Example:
    ```json
    {
      "silence_days": 7,
      "message_template": "We haven't heard from you in a while! How can we help?"
    }
    ```
    """
    try:
        await system.set_silence_rule(
            tenant_id=tenant_id,
            silence_days=req.silence_days,
            message_template=req.message_template
        )
        
        return {
            "status": "success",
            "message": f"Silence rule set for tenant {tenant_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns")
async def list_campaigns(
    tenant_id: str = Depends(verify_session),
    system = Depends(get_proactive_system)
):
    """List all campaigns for the authenticated tenant"""
    campaigns = [
        c for c in system.campaigns.values()
        if c.tenant_id == tenant_id
    ]
    
    return {
        "campaigns": [
            CampaignResponse(
                id=c.id,
                tenant_id=c.tenant_id,
                name=c.name,
                message_template=c.message_template,
                target_segment=c.target_segment,
                scheduled_time=c.scheduled_time,
                status=c.status.value,
                recipient_count=len(c.recipients),
                sent_count=c.sent_count,
                failed_count=c.failed_count
            )
            for c in campaigns
        ]
    }


@router.get("/scheduled")
async def list_scheduled_messages(
    tenant_id: str = Depends(verify_session),
    system = Depends(get_proactive_system)
):
    """List all scheduled messages for the authenticated tenant"""
    messages = [
        m for m in system.scheduled_messages.values()
        if m.tenant_id == tenant_id
    ]
    
    return {
        "messages": [
            MessageResponse(
                id=m.id,
                tenant_id=m.tenant_id,
                recipient=m.recipient,
                message_type=m.message_type.value,
                content=m.content,
                scheduled_time=m.scheduled_time,
                status=m.status.value
            )
            for m in messages
        ]
    }


@router.delete("/scheduled/{message_id}")
async def cancel_scheduled_message(
    message_id: str,
    tenant_id: str = Depends(verify_session),
    system = Depends(get_proactive_system)
):
    """Cancel a scheduled message (only if owned by authenticated tenant)"""
    from src.core.proactive_messaging import MessageStatus
    
    msg = system.scheduled_messages.get(message_id)
    if not msg or msg.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Message not found")
    
    msg.status = MessageStatus.CANCELLED
    
    return {
        "status": "success",
        "message": f"Message {message_id} cancelled"
    }
