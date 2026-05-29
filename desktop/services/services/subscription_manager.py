"""
Subscription Manager — Freemium model with Stripe-ready payment hooks.

Parakram Pricing:
  - Free (Hobbyist): All features, 3 projects, community support
  - Pro ($9/mo): Unlimited projects, priority AI, datasheet parsing, OTA
  - Team ($29/mo): Multi-user, MISRA reports, enterprise extensions
  - Enterprise (Custom): Dedicated support, custom extensions, SLA

For launch: Free tier only. Stripe integration ready for activation.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum


class PlanTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


@dataclass
class PlanLimits:
    max_projects: int
    max_builds_per_day: int
    max_extensions: int
    datasheet_parsing: bool
    misra_reports: bool
    ota_management: bool
    priority_ai: bool
    voice_input: bool
    team_members: int
    custom_models: bool
    support_level: str  # community, email, priority, dedicated


PLANS = {
    PlanTier.FREE: PlanLimits(
        max_projects=3, max_builds_per_day=10, max_extensions=8,
        datasheet_parsing=True, misra_reports=True, ota_management=False,
        priority_ai=False, voice_input=True, team_members=1,
        custom_models=False, support_level="community",
    ),
    PlanTier.PRO: PlanLimits(
        max_projects=999, max_builds_per_day=100, max_extensions=999,
        datasheet_parsing=True, misra_reports=True, ota_management=True,
        priority_ai=True, voice_input=True, team_members=1,
        custom_models=True, support_level="email",
    ),
    PlanTier.TEAM: PlanLimits(
        max_projects=999, max_builds_per_day=500, max_extensions=999,
        datasheet_parsing=True, misra_reports=True, ota_management=True,
        priority_ai=True, voice_input=True, team_members=10,
        custom_models=True, support_level="priority",
    ),
    PlanTier.ENTERPRISE: PlanLimits(
        max_projects=999, max_builds_per_day=999, max_extensions=999,
        datasheet_parsing=True, misra_reports=True, ota_management=True,
        priority_ai=True, voice_input=True, team_members=999,
        custom_models=True, support_level="dedicated",
    ),
}

PLAN_PRICES = {
    PlanTier.FREE: 0,
    PlanTier.PRO: 9,
    PlanTier.TEAM: 29,
    PlanTier.ENTERPRISE: -1,  # Custom pricing
}


@dataclass
class Subscription:
    user_id: str
    plan: PlanTier = PlanTier.FREE
    started_at: str = ""
    expires_at: str = ""
    stripe_customer_id: str = ""
    stripe_subscription_id: str = ""
    is_active: bool = True


class SubscriptionManager:
    """Manage user subscriptions and plan limits."""

    STORAGE = Path("./storage/subscriptions")

    def __init__(self):
        self.STORAGE.mkdir(parents=True, exist_ok=True)

    def get_subscription(self, user_id: str) -> dict:
        """Get user's current subscription."""
        sub_file = self.STORAGE / f"{user_id}.json"
        if sub_file.exists():
            return json.loads(sub_file.read_text())
        # Default: free tier
        return {
            "user_id": user_id,
            "plan": "free",
            "is_active": True,
            "started_at": datetime.now().isoformat(),
        }

    def get_limits(self, user_id: str) -> dict:
        """Get plan limits for a user."""
        sub = self.get_subscription(user_id)
        plan_tier = PlanTier(sub.get("plan", "free"))
        limits = PLANS[plan_tier]
        return {
            "plan": plan_tier.value,
            "price": PLAN_PRICES[plan_tier],
            "limits": {
                "max_projects": limits.max_projects,
                "max_builds_per_day": limits.max_builds_per_day,
                "max_extensions": limits.max_extensions,
                "datasheet_parsing": limits.datasheet_parsing,
                "misra_reports": limits.misra_reports,
                "ota_management": limits.ota_management,
                "priority_ai": limits.priority_ai,
                "voice_input": limits.voice_input,
                "team_members": limits.team_members,
                "custom_models": limits.custom_models,
                "support_level": limits.support_level,
            },
        }

    def check_limit(self, user_id: str, resource: str, current_count: int = 0) -> dict:
        """Check if a user can perform an action based on their plan."""
        limits_data = self.get_limits(user_id)
        limits = limits_data["limits"]

        limit_map = {
            "projects": limits["max_projects"],
            "builds": limits["max_builds_per_day"],
            "extensions": limits["max_extensions"],
            "team_members": limits["team_members"],
        }

        max_allowed = limit_map.get(resource, 999)
        allowed = current_count < max_allowed

        return {
            "allowed": allowed,
            "resource": resource,
            "current": current_count,
            "max": max_allowed,
            "plan": limits_data["plan"],
            "upgrade_needed": not allowed,
        }

    def get_all_plans(self) -> list[dict]:
        """Return all available plans with features and pricing."""
        plans = []
        for tier in PlanTier:
            limits = PLANS[tier]
            plans.append({
                "id": tier.value,
                "name": tier.value.capitalize(),
                "price": PLAN_PRICES[tier],
                "features": {
                    "projects": limits.max_projects if limits.max_projects < 999 else "Unlimited",
                    "builds_per_day": limits.max_builds_per_day if limits.max_builds_per_day < 999 else "Unlimited",
                    "extensions": limits.max_extensions if limits.max_extensions < 999 else "Unlimited",
                    "datasheet_parsing": limits.datasheet_parsing,
                    "misra_reports": limits.misra_reports,
                    "ota_management": limits.ota_management,
                    "priority_ai": limits.priority_ai,
                    "voice_input": limits.voice_input,
                    "team_members": limits.team_members if limits.team_members < 999 else "Unlimited",
                    "custom_models": limits.custom_models,
                    "support": limits.support_level,
                },
            })
        return plans

    def upgrade(self, user_id: str, plan: str, stripe_customer_id: str = "", stripe_subscription_id: str = "") -> dict:
        """Upgrade a user's plan (Stripe webhook handler)."""
        sub = {
            "user_id": user_id,
            "plan": plan,
            "is_active": True,
            "started_at": datetime.now().isoformat(),
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
        }
        sub_file = self.STORAGE / f"{user_id}.json"
        sub_file.write_text(json.dumps(sub, indent=2))
        return {"upgraded": True, "plan": plan}


def get_subscription_manager() -> SubscriptionManager:
    return SubscriptionManager()
