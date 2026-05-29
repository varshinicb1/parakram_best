"""
Stripe Webhook Handler — Process payment events for subscriptions.

Handles:
  - checkout.session.completed → Activate subscription
  - customer.subscription.updated → Update plan
  - customer.subscription.deleted → Downgrade to free
  - invoice.payment_failed → Notify user
"""

import json
import hmac
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

SUBS_DIR = Path("./storage/subscriptions")
SUBS_DIR.mkdir(parents=True, exist_ok=True)

WEBHOOK_LOG = Path("./storage/webhook_log.json")


class StripeWebhookHandler:
    """Handle Stripe webhook events."""

    def __init__(self, webhook_secret: str = ""):
        self.webhook_secret = webhook_secret
        self.log: list[dict] = []

    def verify_signature(self, payload: bytes, sig_header: str) -> bool:
        """Verify Stripe webhook signature."""
        if not self.webhook_secret:
            return True  # Skip verification in dev mode
        try:
            elements = dict(item.split("=", 1) for item in sig_header.split(","))
            timestamp = elements.get("t", "")
            signature = elements.get("v1", "")
            signed_payload = f"{timestamp}.{payload.decode()}".encode()
            expected = hmac.new(
                self.webhook_secret.encode(), signed_payload, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception:
            return False

    async def handle_event(self, event_type: str, data: dict) -> dict:
        """Route webhook event to handler."""
        handlers = {
            "checkout.session.completed": self._handle_checkout,
            "customer.subscription.created": self._handle_sub_created,
            "customer.subscription.updated": self._handle_sub_updated,
            "customer.subscription.deleted": self._handle_sub_deleted,
            "invoice.payment_succeeded": self._handle_payment_success,
            "invoice.payment_failed": self._handle_payment_failed,
            "customer.created": self._handle_customer_created,
        }

        handler = handlers.get(event_type, self._handle_unknown)
        result = await handler(data)

        # Log event
        log_entry = {
            "event": event_type,
            "timestamp": datetime.now().isoformat(),
            "result": result,
        }
        self.log.append(log_entry)
        self._save_log()

        return result

    async def _handle_checkout(self, data: dict) -> dict:
        """Checkout completed — activate subscription."""
        session = data.get("object", {})
        customer_id = session.get("customer", "")
        email = session.get("customer_email", "")

        # Map price to plan
        line_items = session.get("line_items", {}).get("data", [])
        plan = "pro"  # Default
        for item in line_items:
            price_id = item.get("price", {}).get("id", "")
            if "team" in price_id.lower():
                plan = "team"
            elif "enterprise" in price_id.lower():
                plan = "enterprise"

        sub_data = {
            "customer_id": customer_id,
            "email": email,
            "plan": plan,
            "status": "active",
            "activated_at": datetime.now().isoformat(),
        }

        # Save subscription
        sub_file = SUBS_DIR / f"{customer_id}.json"
        sub_file.write_text(json.dumps(sub_data, indent=2))

        return {"action": "activated", "plan": plan, "customer": customer_id}

    async def _handle_sub_created(self, data: dict) -> dict:
        sub = data.get("object", {})
        return {"action": "subscription_created", "id": sub.get("id")}

    async def _handle_sub_updated(self, data: dict) -> dict:
        """Subscription updated — change plan."""
        sub = data.get("object", {})
        customer_id = sub.get("customer", "")
        status = sub.get("status", "")

        sub_file = SUBS_DIR / f"{customer_id}.json"
        if sub_file.exists():
            existing = json.loads(sub_file.read_text())
            existing["status"] = status
            existing["updated_at"] = datetime.now().isoformat()
            sub_file.write_text(json.dumps(existing, indent=2))

        return {"action": "updated", "customer": customer_id, "status": status}

    async def _handle_sub_deleted(self, data: dict) -> dict:
        """Subscription cancelled — downgrade to free."""
        sub = data.get("object", {})
        customer_id = sub.get("customer", "")

        sub_file = SUBS_DIR / f"{customer_id}.json"
        if sub_file.exists():
            existing = json.loads(sub_file.read_text())
            existing["plan"] = "free"
            existing["status"] = "cancelled"
            existing["cancelled_at"] = datetime.now().isoformat()
            sub_file.write_text(json.dumps(existing, indent=2))

        return {"action": "downgraded", "customer": customer_id, "plan": "free"}

    async def _handle_payment_success(self, data: dict) -> dict:
        invoice = data.get("object", {})
        return {
            "action": "payment_success",
            "amount": invoice.get("amount_paid", 0) / 100,
            "customer": invoice.get("customer", ""),
        }

    async def _handle_payment_failed(self, data: dict) -> dict:
        """Payment failed — notify user."""
        invoice = data.get("object", {})
        customer_id = invoice.get("customer", "")

        sub_file = SUBS_DIR / f"{customer_id}.json"
        if sub_file.exists():
            existing = json.loads(sub_file.read_text())
            existing["payment_status"] = "failed"
            existing["last_failed_at"] = datetime.now().isoformat()
            sub_file.write_text(json.dumps(existing, indent=2))

        return {"action": "payment_failed", "customer": customer_id}

    async def _handle_customer_created(self, data: dict) -> dict:
        customer = data.get("object", {})
        return {"action": "customer_created", "id": customer.get("id")}

    async def _handle_unknown(self, data: dict) -> dict:
        return {"action": "unhandled"}

    def _save_log(self):
        """Persist webhook log."""
        try:
            WEBHOOK_LOG.write_text(json.dumps(self.log[-100:], indent=2))  # Keep last 100
        except Exception:
            pass


_handler: Optional[StripeWebhookHandler] = None

def get_webhook_handler() -> StripeWebhookHandler:
    global _handler
    if _handler is None:
        _handler = StripeWebhookHandler()
    return _handler
