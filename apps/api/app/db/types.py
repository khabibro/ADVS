"""Column types that behave the same on PostgreSQL and SQLite."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CHAR
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UUID(TypeDecorator[uuid.UUID]):
    """A UUID: the native type on PostgreSQL, a 32-character hex TEXT column elsewhere.

    The generic `UUID` type was declared as "UUID" on SQLite, which gives the column NUMERIC affinity: a hex id made of
    digits and a single "e" (for example 12e45678...) was silently converted to a float (even to infinity) and the row
    could no longer be read. CHAR(32) has TEXT affinity and keeps the hex string as it is."""

    impl = CHAR(32)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        parsed = value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return parsed if dialect.name == "postgresql" else parsed.hex

    def process_result_value(self, value: Any, dialect: Dialect) -> uuid.UUID | None:
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
