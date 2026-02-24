"""Signal trigger package."""

from owlclaw.triggers.signal.config import SignalTriggerConfig
from owlclaw.triggers.signal.handlers import (
    BaseSignalHandler,
    InstructHandler,
    PauseHandler,
    ResumeHandler,
    TriggerHandler,
    default_handlers,
)
from owlclaw.triggers.signal.models import PendingInstruction, Signal, SignalResult, SignalSource, SignalType
from owlclaw.triggers.signal.persistence import AgentControlStateORM, PendingInstructionORM
from owlclaw.triggers.signal.router import SignalRouter
from owlclaw.triggers.signal.state import AgentState, AgentStateManager

__all__ = [
    "AgentState",
    "AgentStateManager",
    "AgentControlStateORM",
    "BaseSignalHandler",
    "InstructHandler",
    "PauseHandler",
    "PendingInstruction",
    "PendingInstructionORM",
    "ResumeHandler",
    "Signal",
    "SignalResult",
    "SignalRouter",
    "SignalSource",
    "SignalTriggerConfig",
    "SignalType",
    "TriggerHandler",
    "default_handlers",
]
