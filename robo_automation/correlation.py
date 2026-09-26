"""Per-test correlation identifiers for reusable automation execution.

A deterministic ``test_case_id`` identifies the pytest node across runs, while a
unique ``process_id`` identifies one concrete execution attempt.  ContextVars
make the identifiers available to logging, diagnostics, reporting, and evidence
code without threading IDs through every flow/component call.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any


_TEST_CASE_ID: ContextVar[str] = ContextVar("robo_test_case_id", default="")
_PROCESS_ID: ContextVar[str] = ContextVar("robo_process_id", default="")
_ATTEMPT_ID: ContextVar[str] = ContextVar("robo_attempt_id", default="")


@dataclass(frozen=True)
class CorrelationTokens:
    """ContextVar reset tokens for one bound testcase execution."""

    test_case_id: Token[str]
    process_id: Token[str]
    attempt_id: Token[str]


def _safe_token(value: object, limit: int = 48) -> str:
    """Return a compact identifier-safe token."""
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "")).strip("-._")
    return token[:limit]


def build_test_case_id(nodeid: str) -> str:
    """Return a deterministic testcase correlation ID for a pytest nodeid."""
    digest = hashlib.sha1(str(nodeid).encode("utf-8")).hexdigest()[:12].upper()
    return f"TC-{digest}"


def build_attempt_id(sequence: int) -> str:
    """Return an execution-attempt label, preserving the Jenkins retry round."""
    configured = _safe_token(os.getenv("ROBO_TEST_ATTEMPT", ""))
    local_attempt = f"A{max(1, int(sequence))}"
    return f"{configured}-{local_attempt}" if configured else local_attempt


def build_process_id(test_case_id: str, attempt_id: str) -> str:
    """Return a unique process/correlation ID for one testcase attempt."""
    unique = uuid.uuid4().hex[:8].upper()
    test_suffix = test_case_id.removeprefix("TC-")
    safe_attempt = _safe_token(attempt_id, 32) or "A1"
    return f"PR-{test_suffix}-{safe_attempt}-{unique}"


def bind_test_context(item: Any) -> CorrelationTokens:
    """Create/bind correlation IDs for one pytest protocol execution."""
    sequence = int(getattr(item, "_robo_process_sequence", 0) or 0) + 1
    item._robo_process_sequence = sequence

    test_case_id = str(
        getattr(item, "_robo_test_case_id", "") or build_test_case_id(item.nodeid)
    )
    attempt_id = build_attempt_id(sequence)
    process_id = build_process_id(test_case_id, attempt_id)

    item._robo_test_case_id = test_case_id
    item._robo_process_id = process_id
    item._robo_attempt_id = attempt_id

    return CorrelationTokens(
        test_case_id=_TEST_CASE_ID.set(test_case_id),
        process_id=_PROCESS_ID.set(process_id),
        attempt_id=_ATTEMPT_ID.set(attempt_id),
    )


def reset_test_context(tokens: CorrelationTokens) -> None:
    """Restore correlation ContextVars after a testcase protocol completes."""
    _ATTEMPT_ID.reset(tokens.attempt_id)
    _PROCESS_ID.reset(tokens.process_id)
    _TEST_CASE_ID.reset(tokens.test_case_id)


def current_correlation() -> dict[str, str]:
    """Return the current correlation identifiers."""
    return {
        "test_case_id": _TEST_CASE_ID.get(),
        "process_id": _PROCESS_ID.get(),
        "attempt_id": _ATTEMPT_ID.get(),
    }
