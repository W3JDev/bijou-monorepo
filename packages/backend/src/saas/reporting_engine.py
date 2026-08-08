"""
Bijou AI - Reporting Engine
============================

Automated reporting system for daily, weekly, and monthly analytics.

Reports are generated automatically and sent via WhatsApp to the owner.
Includes:
- Message volume and trends
- Customer engagement metrics
- Sentiment analysis
- AI performance statistics
- Usage tracking
- Business insights

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportingEngine:
    """
    Generates automated reports for business owners.

    Reports are sent via WhatsApp at scheduled times.
    """

    def __init__(
        self,
        memory_system=None,
        supabase_client=None,
        pricing_engine=None,
        send_message_callback=None,
    ):
        """
        Initialize reporting engine.

        Args:
            memory_system: ConversationMemory instance
            supabase_client: Supabase client
            pricing_engine: PricingEngine instance
            send_message_callback: Function to send WhatsApp messages
        """
        self.memory = memory_system
        self.supabase = supabase_client
        self.pricing_engine = pricing_engine
        self.send_message = send_message_callback

        # Feature flag
        self.enabled = os.getenv("ENABLE_AUTO_REPORTS", "false").lower() == "true"

        # Report settings
        self.daily_enabled = os.getenv("ENABLE_DAILY_REPORTS", "true").lower() == "true"
        self.weekly_enabled = (
            os.getenv("ENABLE_WEEKLY_REPORTS", "true").lower() == "true"
        )
        self.monthly_enabled = (
            os.getenv("ENABLE_MONTHLY_REPORTS", "true").lower() == "true"
        )

        # Send time (default 9 AM local time)
        self.report_hour = int(os.getenv("REPORT_HOUR", "9"))

        logger.info(f"✅ ReportingEngine initialized (enabled={self.enabled})")

    def generate_daily_report(self, tenant_id: str) -> str:
        """
        Generate daily report.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Report text
        """
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        # Get metrics
        metrics = self._get_metrics(tenant_id, yesterday, today)

        report = [
            "📊 **Daily Report**",
            f"📅 {yesterday.strftime('%A, %B %d, %Y')}\n",
            "**Message Activity:**",
            f"📨 Total messages: {metrics['total_messages']}",
            f"👥 Active customers: {metrics['active_customers']}",
            f"🆕 New customers: {metrics['new_customers']}\n",
            "**Sentiment:**",
            f"😊 Positive: {metrics['sentiment_positive']}%",
            f"😐 Neutral: {metrics['sentiment_neutral']}%",
            f"😟 Negative: {metrics['sentiment_negative']}%\n",
            "**AI Performance:**",
            f"⚡ Avg response time: {metrics['avg_response_time']:.1f}s",
            f"✅ Success rate: {metrics['success_rate']:.1f}%\n",
        ]

        # Add escalations if any
        if metrics["escalations"] > 0:
            report.extend(
                [
                    "**🔥 Attention Required:**",
                    f"⚠️ {metrics['escalations']} escalation(s)",
                    f"🚨 {metrics['urgent_issues']} urgent issue(s)\n",
                ]
            )

        # Add usage if pricing enabled
        if self.pricing_engine:
            usage = self.pricing_engine.get_usage_percentage(tenant_id)
            report.extend(
                [
                    "**📈 Usage (Month):**",
                    f"💬 Messages: {usage['messages']:.0f}%",
                    f"🛠️ Tools: {usage['tool_calls']:.0f}%",
                ]
            )

        _dash = (os.getenv("DASHBOARD_URL") or os.getenv("APP_URL", "") + "/static/dashboard.html").rstrip("/")
        report.append(f"\n💡 Full analytics: {_dash}")

        return "\n".join(report)

    def generate_weekly_report(self, tenant_id: str) -> str:
        """
        Generate weekly report.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Report text
        """
        today = datetime.now()
        week_start = today - timedelta(days=7)

        metrics = self._get_metrics(tenant_id, week_start, today)

        report = [
            "📊 **Weekly Report**",
            f"📅 Week of {week_start.strftime('%B %d')} - {today.strftime('%B %d, %Y')}\n",
            "**📈 Growth:**",
            f"📨 Total messages: {metrics['total_messages']} ({metrics['message_growth']:+.0f}%)",
            f"👥 Total customers: {metrics['active_customers']} ({metrics['customer_growth']:+.0f}%)",
            f"🆕 New this week: {metrics['new_customers']}\n",
            "**😊 Customer Happiness:**",
            f"Average sentiment: {metrics['avg_sentiment']:.2f}/5.0",
            f"Positive interactions: {metrics['sentiment_positive']}%",
            f"Issues resolved: {metrics['issues_resolved']}/{metrics['total_issues']}\n",
            "**🎯 Top Topics:**",
        ]

        # Add top topics
        for i, topic in enumerate(metrics["top_topics"][:5], 1):
            report.append(f"{i}. {topic['name']} ({topic['count']} mentions)")

        report.extend(
            [
                "\n**⚡ Performance:**",
                f"Avg response time: {metrics['avg_response_time']:.1f}s",
                f"AI success rate: {metrics['success_rate']:.1f}%",
                f"Human handovers: {metrics['handovers']}",
            ]
        )

        # Business insights
        if metrics.get("sales_opportunities", 0) > 0:
            report.extend(
                [
                    "\n**💰 Business Insights:**",
                    f"🎯 {metrics['sales_opportunities']} sales opportunities detected",
                    f"💎 Estimated value: ${metrics['estimated_value']:.0f}",
                ]
            )

        _dash = (os.getenv("DASHBOARD_URL") or os.getenv("APP_URL", "") + "/static/dashboard.html").rstrip("/")
        report.append(f"\n📊 View detailed analytics: {_dash}")

        return "\n".join(report)

    def generate_monthly_report(self, tenant_id: str) -> str:
        """
        Generate monthly report.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Report text
        """
        today = datetime.now()
        month_start = today.replace(day=1)

        metrics = self._get_metrics(tenant_id, month_start, today)

        report = [
            "📊 **Monthly Report**",
            f"📅 {month_start.strftime('%B %Y')}\n",
            "**🎯 Key Metrics:**",
            f"📨 Messages processed: {metrics['total_messages']:,}",
            f"👥 Active customers: {metrics['active_customers']}",
            f"🆕 New customers: {metrics['new_customers']}",
            f"🔄 Retention rate: {metrics['retention_rate']:.1f}%\n",
            "**😊 Customer Experience:**",
            f"Average CSAT: {metrics['avg_csat']:.1f}/5.0",
            f"Positive sentiment: {metrics['sentiment_positive']}%",
            f"Resolution rate: {metrics['resolution_rate']:.1f}%",
            f"Avg resolution time: {metrics['avg_resolution_time']:.0f}min\n",
            "**🤖 AI Performance:**",
            f"Success rate: {metrics['success_rate']:.1f}%",
            f"Avg response time: {metrics['avg_response_time']:.1f}s",
            f"Tool usage: {metrics['tool_calls']:,} calls",
            f"Human handovers: {metrics['handovers']} ({metrics['handover_rate']:.1f}%)\n",
        ]

        # Cost tracking
        if metrics.get("total_cost"):
            report.extend(
                [
                    "**💰 Cost Analysis:**",
                    f"Total cost: ${metrics['total_cost']:.2f}",
                    f"Cost per message: ${metrics['cost_per_message']:.3f}",
                    f"Cost per customer: ${metrics['cost_per_customer']:.2f}",
                ]
            )

        # Business insights
        report.extend(
            [
                "\n**📈 Business Insights:**",
                f"🎯 Sales opportunities: {metrics.get('sales_opportunities', 0)}",
                f"💎 Estimated pipeline: ${metrics.get('estimated_value', 0):.0f}",
                f"🔥 Top converting topic: {metrics.get('top_topic', 'N/A')}",
            ]
        )

        # Recommendations
        report.extend(
            [
                "\n**💡 Recommendations:**",
                self._get_recommendation(metrics),
            ]
        )

        _dash = (os.getenv("DASHBOARD_URL") or os.getenv("APP_URL", "") + "/static/dashboard.html").rstrip("/")
        report.append(f"\n📊 Full analytics dashboard: {_dash}?tenant={tenant_id}")

        return "\n".join(report)

    def _get_metrics(
        self, tenant_id: str, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get metrics for date range.

        Args:
            tenant_id: Tenant identifier
            start_date: Start date
            end_date: End date

        Returns:
            Metrics dictionary
        """
        metrics = {
            "total_messages": 0,
            "active_customers": 0,
            "new_customers": 0,
            "sentiment_positive": 0,
            "sentiment_neutral": 0,
            "sentiment_negative": 0,
            "avg_sentiment": 0.0,
            "avg_response_time": 0.0,
            "success_rate": 0.0,
            "escalations": 0,
            "urgent_issues": 0,
            "handovers": 0,
            "handover_rate": 0.0,
            "tool_calls": 0,
            "top_topics": [],
            "message_growth": 0,
            "customer_growth": 0,
            "issues_resolved": 0,
            "total_issues": 0,
            "sales_opportunities": 0,
            "estimated_value": 0,
            "retention_rate": 0.0,
            "avg_csat": 0.0,
            "resolution_rate": 0.0,
            "avg_resolution_time": 0,
            "total_cost": 0.0,
            "cost_per_message": 0.0,
            "cost_per_customer": 0.0,
            "top_topic": "N/A",
        }

        if not self.supabase:
            return metrics

        try:
            # Query conversations for date range
            response = (
                self.supabase.table("conversations")
                .select("*")
                .eq("tenant_id", tenant_id)
                .gte("timestamp", start_date.isoformat())
                .lte("timestamp", end_date.isoformat())
                .execute()
            )

            if response.data:
                conversations = response.data
                metrics["total_messages"] = len(conversations)

                # Count unique customers
                customers = set(c["chat_jid"] for c in conversations)
                metrics["active_customers"] = len(customers)

                # Sentiment analysis
                sentiments = [
                    c.get("detected_emotion", "neutral") for c in conversations
                ]
                positive = sum(
                    1 for s in sentiments if s in ["joy", "surprise", "neutral"]
                )
                negative = sum(
                    1
                    for s in sentiments
                    if s in ["anger", "sadness", "fear", "disgust"]
                )
                neutral = len(sentiments) - positive - negative

                total = len(sentiments) or 1
                metrics["sentiment_positive"] = int((positive / total) * 100)
                metrics["sentiment_neutral"] = int((neutral / total) * 100)
                metrics["sentiment_negative"] = int((negative / total) * 100)

                # Average sentiment score
                sentiment_scores = []
                for conv in conversations:
                    emotion = conv.get("detected_emotion")
                    if emotion == "joy":
                        sentiment_scores.append(5.0)
                    elif emotion in ["surprise", "neutral"]:
                        sentiment_scores.append(3.0)
                    elif emotion in ["anger", "sadness", "fear"]:
                        sentiment_scores.append(1.0)

                if sentiment_scores:
                    metrics["avg_sentiment"] = sum(sentiment_scores) / len(
                        sentiment_scores
                    )

            # Get escalations
            escalation_response = (
                self.supabase.table("escalations")
                .select("*")
                .eq("tenant_id", tenant_id)
                .gte("created_at", start_date.isoformat())
                .lte("created_at", end_date.isoformat())
                .execute()
            )

            if escalation_response.data:
                metrics["escalations"] = len(escalation_response.data)
                metrics["handovers"] = len(escalation_response.data)
                metrics["urgent_issues"] = sum(
                    1 for e in escalation_response.data if e.get("priority") == "high"
                )

        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")

        return metrics

    def _get_recommendation(self, metrics: Dict[str, Any]) -> str:
        """
        Get AI-powered recommendation based on metrics.

        Args:
            metrics: Metrics dictionary

        Returns:
            Recommendation text
        """
        # High negative sentiment
        if metrics["sentiment_negative"] > 30:
            return (
                "⚠️ High negative sentiment detected. Consider:\n"
                "  - Review common pain points\n"
                "  - Improve response templates\n"
                "  - Enable faster human escalation"
            )

        # High success rate
        elif metrics["success_rate"] > 95:
            return (
                "🎉 Excellent AI performance! Consider:\n"
                "  - Increase automation level\n"
                "  - Add more self-service options\n"
                "  - Share success stories with team"
            )

        # Growth opportunity
        elif metrics["customer_growth"] > 20:
            return (
                "📈 Strong growth! Consider:\n"
                "  - Upgrade to handle more volume\n"
                "  - Add team members for handover\n"
                "  - Enable advanced analytics"
            )

        # Default
        return (
            "✅ Performance is stable. Keep monitoring:\n"
            "  - Customer satisfaction trends\n"
            "  - Response time consistency\n"
            "  - Seasonal patterns"
        )

    async def send_report(
        self, tenant_id: str, report_type: str, owner_jid: str
    ) -> bool:
        """
        Generate and send report to owner.

        Args:
            tenant_id: Tenant identifier
            report_type: Type of report (daily, weekly, monthly)
            owner_jid: Owner's WhatsApp JID

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.debug("Reports disabled via feature flag")
            return False

        if not self.send_message:
            logger.error("Cannot send report: send_message callback not configured")
            return False

        try:
            # Generate report
            if report_type == "daily":
                report_text = self.generate_daily_report(tenant_id)
            elif report_type == "weekly":
                report_text = self.generate_weekly_report(tenant_id)
            elif report_type == "monthly":
                report_text = self.generate_monthly_report(tenant_id)
            else:
                logger.error(f"Unknown report type: {report_type}")
                return False

            # Send via WhatsApp
            self.send_message(owner_jid, report_text)

            logger.info(f"✅ Sent {report_type} report to {owner_jid}")
            return True

        except Exception as e:
            logger.error(f"Error sending report: {e}")
            return False

    def should_send_daily(self) -> bool:
        """Check if should send daily report now"""
        if not self.daily_enabled:
            return False

        now = datetime.now()
        return now.hour == self.report_hour and now.minute < 5

    def should_send_weekly(self) -> bool:
        """Check if should send weekly report now (Mondays)"""
        if not self.weekly_enabled:
            return False

        now = datetime.now()
        return (
            now.weekday() == 0  # Monday
            and now.hour == self.report_hour
            and now.minute < 5
        )

    def should_send_monthly(self) -> bool:
        """Check if should send monthly report now (1st of month)"""
        if not self.monthly_enabled:
            return False

        now = datetime.now()
        return now.day == 1 and now.hour == self.report_hour and now.minute < 5

    def get_stats(self) -> Dict[str, Any]:
        """Get reporting engine statistics"""
        return {
            "enabled": self.enabled,
            "daily_enabled": self.daily_enabled,
            "weekly_enabled": self.weekly_enabled,
            "monthly_enabled": self.monthly_enabled,
            "report_hour": self.report_hour,
        }
