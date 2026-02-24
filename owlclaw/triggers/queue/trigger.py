"""Queue trigger runtime: lifecycle management and consumption loop."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from owlclaw.triggers.queue.config import QueueTriggerConfig, validate_config
from owlclaw.triggers.queue.idempotency import IdempotencyStore
from owlclaw.triggers.queue.models import MessageEnvelope, RawMessage
from owlclaw.triggers.queue.parsers import BinaryParser, JSONParser, MessageParser, ParseError, TextParser
from owlclaw.triggers.queue.protocols import QueueAdapter

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProcessResult:
    """Outcome of processing one queue message."""

    message_id: str
    status: str
    trace_id: str
    detail: str | None = None


class QueueTrigger:
    """Core queue-trigger runtime for message consumption and Agent dispatch."""

    def __init__(
        self,
        *,
        config: QueueTriggerConfig,
        adapter: QueueAdapter,
        agent_runtime: Any | None = None,
        governance: Any | None = None,
        ledger: Any | None = None,
        idempotency_store: IdempotencyStore | None = None,
    ) -> None:
        config_errors = validate_config(config)
        if config_errors:
            joined = "; ".join(config_errors)
            raise ValueError(f"Invalid QueueTriggerConfig: {joined}")

        self.config = config
        self.adapter = adapter
        self.agent_runtime = agent_runtime
        self.governance = governance
        self.ledger = ledger
        self.idempotency_store = idempotency_store

        self._running = False
        self._paused = False
        self._tasks: list[asyncio.Task[Any]] = []
        self._processed_count = 0
        self._failed_count = 0
        self._dedup_hits = 0
        self._parser = self._create_parser(config.parser_type)

    @staticmethod
    def _create_parser(parser_type: str) -> MessageParser:
        parser_type = parser_type.lower().strip()
        if parser_type == "text":
            return TextParser()
        if parser_type == "binary":
            return BinaryParser()
        return JSONParser()

    async def start(self) -> None:
        """Start queue consumption workers."""
        if self._running:
            raise RuntimeError("QueueTrigger already running")
        self._running = True
        self._paused = False
        await self.adapter.connect()
        self._tasks = [
            asyncio.create_task(self._consume_loop(worker_id=i), name=f"queue-trigger-worker-{i}")
            for i in range(self.config.concurrency)
        ]

    async def stop(self) -> None:
        """Stop workers gracefully and close adapter connection."""
        self._running = False
        self._paused = False
        await self.adapter.close()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks = []

    async def pause(self) -> None:
        """Pause message processing without disconnecting adapter."""
        self._paused = True

    async def resume(self) -> None:
        """Resume message processing."""
        self._paused = False

    async def health_check(self) -> dict[str, Any]:
        """Return runtime health and basic counters."""
        adapter_healthy = await self.adapter.health_check()
        active_workers = len([task for task in self._tasks if not task.done()])
        return {
            "status": "healthy" if self._running and adapter_healthy else "unhealthy",
            "running": self._running,
            "paused": self._paused,
            "adapter_healthy": adapter_healthy,
            "active_workers": active_workers,
            "processed_count": self._processed_count,
            "failed_count": self._failed_count,
            "dedup_hits": self._dedup_hits,
        }

    async def _consume_loop(self, worker_id: int) -> None:
        """Consume queue messages until stopped."""
        logger.debug("Queue worker %s started", worker_id)
        try:
            async for raw_message in self.adapter.consume():
                if not self._running:
                    break
                while self._paused and self._running:
                    await asyncio.sleep(0.01)
                if not self._running:
                    break
                try:
                    await self._process_message(raw_message)
                except Exception:
                    self._failed_count += 1
                    logger.exception("Queue worker %s failed to process message", worker_id)
                # Yield to event loop to avoid starvation when handlers are immediate.
                await asyncio.sleep(0)
        except Exception:
            self._failed_count += 1
            logger.exception("Queue worker %s consume loop crashed", worker_id)
        finally:
            logger.debug("Queue worker %s stopped", worker_id)

    async def _process_message(self, raw_message: RawMessage) -> ProcessResult:
        """Parse and process one message; parse errors are routed to DLQ."""
        trace_id = f"queue-{raw_message.message_id}"
        try:
            envelope = MessageEnvelope.from_raw_message(
                raw_message,
                source=self.config.queue_name,
                parser=self._parser,
            )
        except ParseError as exc:
            self._failed_count += 1
            await self.adapter.send_to_dlq(raw_message, reason=str(exc))
            return ProcessResult(
                message_id=raw_message.message_id,
                status="parse_error",
                trace_id=trace_id,
                detail=str(exc),
            )

        await self._process_envelope(raw_message, envelope, trace_id)
        self._processed_count += 1
        return ProcessResult(
            message_id=raw_message.message_id,
            status="processed",
            trace_id=trace_id,
        )

    async def _process_envelope(
        self,
        raw_message: RawMessage,
        envelope: MessageEnvelope,
        trace_id: str,
    ) -> None:
        """Process a parsed envelope and apply basic ack policy behavior."""
        if self.config.enable_dedup and self.idempotency_store is not None:
            dedup_key = envelope.dedup_key or envelope.message_id
            try:
                exists = await self.idempotency_store.exists(dedup_key)
            except Exception:
                exists = False
                logger.exception("Idempotency check failed for key %s", dedup_key)
            if exists:
                self._dedup_hits += 1
                await self.adapter.ack(raw_message)
                return

        try:
            await self._trigger_agent(envelope, trace_id)
        except Exception as exc:
            self._failed_count += 1
            await self._handle_processing_error(raw_message, exc)
            return

        if self.config.enable_dedup and self.idempotency_store is not None:
            dedup_key = envelope.dedup_key or envelope.message_id
            try:
                await self.idempotency_store.set(
                    dedup_key,
                    {"trace_id": trace_id, "status": "processed"},
                    ttl=self.config.idempotency_window,
                )
            except Exception:
                logger.exception("Idempotency write failed for key %s", dedup_key)

        await self.adapter.ack(raw_message)

    async def _trigger_agent(self, envelope: MessageEnvelope, trace_id: str) -> None:
        """Trigger AgentRuntime if configured; otherwise no-op."""
        if self.agent_runtime is None:
            return
        trigger_event = getattr(self.agent_runtime, "trigger_event", None)
        if not callable(trigger_event):
            return
        payload = {
            "message": envelope.payload,
            "headers": envelope.headers,
            "source": envelope.source,
            "message_id": envelope.message_id,
            "received_at": envelope.received_at.isoformat(),
            "trace_id": trace_id,
        }
        await trigger_event(
            event_name=envelope.event_name or "queue_message",
            payload=payload,
            focus=self.config.focus,
            tenant_id=envelope.tenant_id or "default",
        )

    async def _handle_processing_error(self, raw_message: RawMessage, error: Exception) -> None:
        """Handle runtime processing failures by configured ack policy."""
        logger.warning("Queue message %s failed: %s", raw_message.message_id, error)
        policy = self.config.ack_policy
        if policy == "ack":
            await self.adapter.ack(raw_message)
            return
        if policy == "nack":
            await self.adapter.nack(raw_message, requeue=False)
            return
        if policy == "requeue":
            await self.adapter.nack(raw_message, requeue=True)
            return
        await self.adapter.send_to_dlq(raw_message, reason=str(error))
