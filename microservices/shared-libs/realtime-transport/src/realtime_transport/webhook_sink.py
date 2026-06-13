"""Webhook sink: forward a consumed Kafka message to a Svix webhook engine.

The webhook ROLE of realtime-transport is a processor-shaped app whose per-message
action is "POST the message to Svix as an event" instead of "produce to Kafka".
This module owns that action — the bridge between the realtime substrate (Kafka)
and the outbound-webhook engine (Svix), which then fans out HMAC-signed deliveries
to externally-registered endpoints.

Design mirrors the rest of the wheel:
  * lazy ``httpx`` import (only the webhook role needs it),
  * non-fatal on transient Svix errors (log + drop, with a single retry),
  * a pure factory ``make_webhook_sink`` that returns an async ``(topic, message)``
    callable — easy to unit-test with a mocked httpx client.
"""

import logging
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# The async signature the webhook app calls per consumed message.
WebhookSink = Callable[[str, Dict[str, Any]], Awaitable[None]]


def _default_event_type(topic: str) -> str:
    """Default topic->event-type mapping: dotted topic name (sensor_agg -> sensor.agg)."""
    return topic.replace("_", ".")


def make_webhook_sink(
    engine_api: str,
    admin_token: str,
    app_id: str,
    topic_to_event_type: Optional[Dict[str, str]] = None,
    *,
    timeout_s: float = 5.0,
) -> WebhookSink:
    """Build an async webhook sink.

    The returned coroutine ``(topic, message)`` POSTs to
    ``{engine_api}/app/{app_id}/msg`` with body
    ``{"eventType": <mapped>, "payload": message}`` and
    ``Authorization: Bearer {admin_token}``.

    ``engine_api`` is the Svix REST base. We accept it WITH or WITHOUT the
    trailing ``/api/v1`` (the <name>-conn secret's WEBHOOK_ENGINE_API includes
    ``/api/v1``; a bare engine URL is normalized) so the bridge works regardless
    of which form the binding env supplies.

    ``topic_to_event_type`` maps a consumed topic to its Svix event type. A topic
    that is absent falls back to the dotted topic name.

    Non-fatal: transient Svix/network errors are logged and dropped after a single
    retry, so a webhook blip never crashes the consumer (mirrors the processor's
    non-fatal produce). The aggregate is still in Kafka and replayable.
    """
    base = engine_api.rstrip("/")
    if not base.endswith("/api/v1"):
        base = base + "/api/v1"
    mapping = dict(topic_to_event_type or {})
    url = f"{base}/app/{app_id}/msg"

    async def sink(topic: str, message: Dict[str, Any]) -> None:
        event_type = mapping.get(topic) or _default_event_type(topic)
        body = {"eventType": event_type, "payload": message}
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json",
        }

        # Lazy import: only the webhook role pulls httpx into the image.
        try:
            import httpx
        except Exception as e:  # pragma: no cover - import guard
            logger.error(f"webhook sink unavailable (httpx import failed: {e})")
            return

        last_err: Optional[Exception] = None
        # One initial attempt + one retry (Svix is at-least-once; a duplicate
        # delivery is acceptable, a dropped one is not — but we cap retries so a
        # hard-down engine doesn't block the consumer indefinitely).
        for attempt in (1, 2):
            try:
                async with httpx.AsyncClient(timeout=timeout_s) as client:
                    resp = await client.post(url, json=body, headers=headers)
                if resp.status_code < 300:
                    return
                # 4xx (bad token / unknown event-type) won't fix on retry — log+drop.
                if 400 <= resp.status_code < 500:
                    logger.error(
                        f"webhook sink: Svix rejected {event_type} "
                        f"({resp.status_code}) — dropping: {resp.text[:200]}"
                    )
                    return
                last_err = RuntimeError(f"Svix {resp.status_code}: {resp.text[:200]}")
            except Exception as e:  # network / timeout
                last_err = e
            if attempt == 1:
                logger.warning(
                    f"webhook sink transient error for {event_type} "
                    f"(attempt 1, retrying): {last_err}"
                )
        logger.error(
            f"webhook sink: failed to deliver {event_type} to Svix after retry "
            f"(dropping): {last_err}"
        )

    return sink
