"""Property and unit tests for owlclaw.db Base model behavior."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from owlclaw.db import Base


class _DbBasePropertyModel(Base):
    """Test model for validating Base tenant_id inheritance."""

    __tablename__ = "db_base_property_model"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    content: Mapped[str] = mapped_column(String(128), nullable=False)


@given(st.text(min_size=1, max_size=64))
def test_base_tenant_id_property_roundtrip(value: str) -> None:
    """Property: tenant_id can be assigned as string values within model constraints."""
    row = _DbBasePropertyModel(id="1", content="x", tenant_id=value)
    assert row.tenant_id == value
    tenant_col = _DbBasePropertyModel.__table__.c.tenant_id
    assert tenant_col.nullable is False
    assert getattr(tenant_col.type, "length", None) == 64


@given(st.sampled_from(["db_base_property_model"]))
def test_base_metadata_includes_all_loaded_models(table_name: str) -> None:
    """Property: metadata tracks loaded Base subclasses with tenant_id column."""
    assert table_name in Base.metadata.tables
    table = Base.metadata.tables[table_name]
    assert "tenant_id" in table.c
    assert table.c.tenant_id.nullable is False


def test_base_is_declarative_and_metadata_accessible() -> None:
    """Unit: Base is DeclarativeBase and exposes usable metadata."""
    assert issubclass(Base, DeclarativeBase)
    assert Base.metadata is not None
    assert _DbBasePropertyModel.__table__.name in Base.metadata.tables
    assert hasattr(_DbBasePropertyModel, "tenant_id")
