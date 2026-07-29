"""助手会话状态 — 进程内字典，演示够用。"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class AssistantSession:
    session_id: str
    last_day: str | None = None
    last_result: dict | None = None
    created_at: float = field(default_factory=time.time)


_sessions: dict[str, AssistantSession] = {}


def get_or_create(session_id: str | None) -> AssistantSession:
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    sid = session_id or f"sess-{uuid.uuid4().hex[:12]}"
    sess = AssistantSession(session_id=sid)
    _sessions[sid] = sess
    return sess
