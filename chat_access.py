"""Third Umpire message allowances, shared by the page and message API."""
from datetime import datetime, timedelta

from models import SupportChat

FREE_WEEKLY_LIMIT = 50


def chat_allowance(user, now=None):
    """Pro has no message-count cap; Free usage follows the account across chats."""
    if user.has_pro:
        return {
            "unlimited": True, "remaining": None, "weekly_limit": None,
            "renews_at": None,
        }
    now = now or datetime.utcnow()
    messages = SupportChat.query.filter(
        SupportChat.user_id == user.id,
        SupportChat.role == "user",
        SupportChat.created_at >= now - timedelta(days=7),
    )
    used = messages.count()
    oldest = messages.order_by(SupportChat.created_at.asc()).first() if used else None
    return {
        "unlimited": False,
        "remaining": max(0, FREE_WEEKLY_LIMIT - used),
        "weekly_limit": FREE_WEEKLY_LIMIT,
        "renews_at": (oldest.created_at + timedelta(days=7)).isoformat() + "Z"
        if oldest else None,
    }
