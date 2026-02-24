"""Database change trigger module."""

from owlclaw.triggers.db_change.adapter import DBChangeAdapter, DBChangeEvent, PostgresNotifyAdapter
from owlclaw.triggers.db_change.aggregator import AggregationMode, EventAggregator
from owlclaw.triggers.db_change.config import DBChangeTriggerConfig
from owlclaw.triggers.db_change.manager import DBChangeTriggerManager

__all__ = [
    "AggregationMode",
    "DBChangeAdapter",
    "DBChangeEvent",
    "DBChangeTriggerConfig",
    "DBChangeTriggerManager",
    "EventAggregator",
    "PostgresNotifyAdapter",
]
