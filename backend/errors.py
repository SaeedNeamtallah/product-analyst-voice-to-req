"""
Application-level error helpers.
"""
from __future__ import annotations

from typing import Iterator

from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError, OperationalError


def _iter_exception_chain(exc: BaseException) -> Iterator[BaseException]:
    current: BaseException | None = exc
    while current is not None:
        yield current
        current = current.__cause__ or current.__context__


def is_database_unavailable_error(exc: BaseException) -> bool:
    """Return True when an exception indicates DB connectivity is unavailable."""
    connectivity_markers = (
        "connection refused",
        "could not connect to server",
        "is the server running",
        "connection reset",
        "server closed the connection",
        "connection timed out",
        "timeout expired",
        "temporary failure in name resolution",
        "nodename nor servname provided",
        "no route to host",
    )

    for err in _iter_exception_chain(exc):
        if isinstance(err, (OperationalError, ConnectionRefusedError, TimeoutError, OSError)):
            return True
        if isinstance(err, DBAPIError) and getattr(err, "connection_invalidated", False):
            return True

        message = str(err).lower()
        if any(marker in message for marker in connectivity_markers):
            return True

    return False


def db_unavailable_http_exception() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Database service unavailable. Start PostgreSQL (or Docker services) and try again.",
    )
