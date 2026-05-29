"""Shared exception types for external API clients.

Replaces the original http_base.py. Each client imports from here rather
than coupling through a shared httpx client instance.
"""

from __future__ import annotations


class UpstreamError(Exception):
    """Raised when an external API call fails (network, 4xx, 5xx, parse error)."""


class NotFoundError(UpstreamError):
    """Raised when an upstream returns 404."""
