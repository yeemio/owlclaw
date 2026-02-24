"""Queue trigger core models, parsers, and adapter contracts."""

from owlclaw.triggers.queue.config import QueueTriggerConfig, validate_config
from owlclaw.triggers.queue.models import MessageEnvelope, RawMessage
from owlclaw.triggers.queue.parsers import BinaryParser, JSONParser, MessageParser, ParseError, TextParser
from owlclaw.triggers.queue.protocols import QueueAdapter

__all__ = [
    "BinaryParser",
    "JSONParser",
    "MessageEnvelope",
    "MessageParser",
    "ParseError",
    "QueueAdapter",
    "QueueTriggerConfig",
    "RawMessage",
    "TextParser",
    "validate_config",
]
