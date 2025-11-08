"""Utility functions for the chat application"""
from datetime import datetime, timezone

def utc_now() -> datetime:
    """
    Get current UTC time with timezone info.
    Replaces deprecated datetime.utcnow()
    """
    return datetime.now(timezone.utc)
