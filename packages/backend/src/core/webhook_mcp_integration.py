"""
Bijou AI - MCP Webhook Integration
==================================

Replaces Make.com with local MCP-based webhook processing.
Handles lead capture, quality scoring, and webhook delivery automatically.

Author: W3J Bijou AI
Version: 1.0.0 (MCP Integration)
"""

import asyncio
import logging
import os
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
import json

logger = logging.getLogger(__name__)


class MCPWebhookProcessor:
    """MCP-based webhook processor for lead capture and automation"""
    
    def __init__(self):
        self.webhook_endpoints = {
            'lead_capture': os.getenv('LEAD_CAPTURE_WEBHOOK_URL', ''),
            'zapier': os.getenv('ZAPIER_WEBHOOK_URL', ''),
            'make': os.getenv('MAKE_WEBHOOK_URL', ''),
        }
    
    async def process_lead_capture(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process lead capture with MCP automation
        
        Features:
        1. Quality scoring using AI
        2. Lead classification
        3. Multi-webhook delivery
        4. Error handling & retries
        """
        logger.info(f"🔄 Processing lead with MCP: {lead_data.get('name', 'Unknown')}")
        
        try:
            # Step 1: Enhance lead data with quality scoring
            enhanced_lead = await self.calculate_quality_score(lead_data)
            
            # Step 2: Add timestamp and metadata
            enhanced_lead.update({
                'processed_at': datetime.now().isoformat(),
                'processor': 'MCP_Webhook_Integration',
                'source': 'Bijou_AI_Dashboard'
            })
            
            # Step 3: Deliver to configured webhooks
            delivery_results = await self.deliver_webhooks(enhanced_lead)
            
            logger.info(f"✅ Lead processing complete: {enhanced_lead['quality_label']}")
            
            return {
                'status': 'success',
                'lead_data': enhanced_lead,
                'delivery_results': delivery_results,
                'quality_score': enhanced_lead.get('quality_score', 0)
            }
            
        except Exception as e:
            logger.error(f"❌ MCP lead processing failed: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'lead_data': lead_data
            }
    
    async def calculate_quality_score(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate lead quality score using business rules
        
        Scoring criteria:
        - Phone number present: +20 points
        - Email present: +15 points
        - Message content quality: +30 points
        - Business type match: +20 points
        - Urgency indicators: +15 points
        """
        score = 0
        factors = []
        
        # Phone validation
        phone = lead_data.get('phone', '').strip()
        if phone and len(phone) >= 10:
            score += 20
            factors.append('phone_present')
        
        # Email validation
        email = lead_data.get('email', '').strip()
        if email and '@' in email:
            score += 15
            factors.append('email_present')
        
        # Message quality analysis
        message = lead_data.get('message', '').strip()
        if message:
            # High-value keywords
            high_value_keywords = [
                'urgent', 'emergency', 'asap', 'booking', 'appointment',
                'consultation', 'quote', 'price', 'cost', 'budget',
                'interested', 'need', 'require', 'help', 'service'
            ]
            
            message_lower = message.lower()
            keyword_matches = sum(1 for keyword in high_value_keywords if keyword in message_lower)
            
            if keyword_matches >= 3:
                score += 30
                factors.append('high_quality_message')
            elif keyword_matches >= 1:
                score += 20
                factors.append('moderate_message')
            elif len(message) > 20:
                score += 10
                factors.append('detailed_message')
        
        # Business type relevance
        business_type = lead_data.get('business_type', '').lower()
        high_value_types = ['dental', 'property', 'restaurant', 'healthcare']
        if any(btype in business_type for btype in high_value_types):
            score += 20
            factors.append('high_value_vertical')
        
        # Urgency indicators
        if message and any(word in message.lower() for word in ['urgent', 'asap', 'emergency', 'today']):
            score += 15
            factors.append('urgency_detected')
        
        # Determine quality label
        if score >= 80:
            quality_label = 'High Quality'
        elif score >= 60:
            quality_label = 'Medium Quality'
        elif score >= 40:
            quality_label = 'Low Quality'
        else:
            quality_label = 'Very Low Quality'
        
        # Add scoring data to lead
        lead_data.update({
            'quality_score': score,
            'quality_label': quality_label,
            'scoring_factors': factors,
            'scored_at': datetime.now().isoformat()
        })
        
        logger.info(f"🎯 Quality score calculated: {score}/100 ({quality_label})")
        
        return lead_data
    
    async def deliver_webhooks(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deliver lead data to configured webhook endpoints
        
        Supports multiple webhook providers:
        - Zapier
        - Make.com
        - Custom endpoints
        """
        results = {}
        
        for webhook_name, webhook_url in self.webhook_endpoints.items():
            if not webhook_url:
                continue
            
            try:
                logger.info(f"📤 Delivering to {webhook_name}: {webhook_url}")
                
                # Prepare payload
                payload = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'Bijou_AI_MCP',
                    'webhook_type': webhook_name,
                    'lead': lead_data
                }
                
                # Send webhook with async httpx
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        webhook_url,
                        json=payload,
                        headers={
                            'Content-Type': 'application/json',
                            'User-Agent': 'Bijou-AI-MCP/1.0'
                        },
                    )
                
                results[webhook_name] = {
                    'status': 'success' if response.status_code < 400 else 'error',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'url': webhook_url
                }
                
                if response.status_code >= 400:
                    logger.warning(f"⚠️ {webhook_name} returned {response.status_code}")
                else:
                    logger.info(f"✅ {webhook_name} delivered successfully")
                
            except Exception as e:
                logger.error(f"❌ {webhook_name} delivery failed: {e}")
                results[webhook_name] = {
                    'status': 'error',
                    'error': str(e),
                    'url': webhook_url
                }
        
        return results
    
    def configure_webhook(self, webhook_name: str, webhook_url: str) -> bool:
        """Add or update webhook configuration"""
        try:
            self.webhook_endpoints[webhook_name] = webhook_url
            logger.info(f"✅ Webhook configured: {webhook_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to configure webhook: {e}")
            return False
    
    async def test_webhook_connectivity(self) -> Dict[str, Any]:
        """Test all configured webhooks"""
        results = {}
        
        for webhook_name, webhook_url in self.webhook_endpoints.items():
            if not webhook_url:
                continue
            
            try:
                test_payload = {
                    'test': True,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'Bijou_AI_MCP_Test'
                }
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        webhook_url,
                        json=test_payload,
                    )
                
                results[webhook_name] = {
                    'status': 'success' if response.status_code < 400 else 'error',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
                
            except Exception as e:
                results[webhook_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results


# Global MCP processor instance
mcp_processor = MCPWebhookProcessor()


async def process_lead_via_mcp(lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for MCP lead processing
    
    Usage:
        result = await process_lead_via_mcp({
            'name': 'John Doe',
            'phone': '+60123456789',
            'message': 'Need urgent dental consultation',
            'business_type': 'dental'
        })
    """
    return await mcp_processor.process_lead_capture(lead_data)


if __name__ == "__main__":
    # Test the MCP processor
    async def test_mcp():
        test_lead = {
            'name': 'Test Customer',
            'phone': '+60123456789',
            'email': 'test@example.com',
            'message': 'I need urgent dental consultation for teeth cleaning. Can I book this week?',
            'business_type': 'dental'
        }
        
        result = await process_lead_via_mcp(test_lead)
        print(json.dumps(result, indent=2))
    
    asyncio.run(test_mcp())