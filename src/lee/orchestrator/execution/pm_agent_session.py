"""
PM Agent Session Management

Handles persistence of PM Agent conversation sessions, allowing users to
resume interactions after disconnecting.
"""

import json
import os
import time
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

@dataclass
class SessionState:
    session_id: str
    run_id: Optional[str]
    last_active_timestamp: float
    history_summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class PMAgentSession:
    """
    Manages session persistence in .lee/pm_agent_sessions/
    """
    
    def __init__(self, project_root: str):
        self.sessions_dir = os.path.join(project_root, ".lee", "pm_agent_sessions")
        os.makedirs(self.sessions_dir, exist_ok=True)

    def save(self, session_id: str, state: SessionState) -> None:
        """Save session state to disk"""
        file_path = self._get_session_path(session_id)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(asdict(state), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")

    def restore(self, session_id: str) -> Optional[SessionState]:
        """Restore session state from disk"""
        file_path = self._get_session_path(session_id)
        if not os.path.exists(file_path):
            return None
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return SessionState(**data)
        except Exception as e:
            logger.error(f"Failed to restore session {session_id}: {e}")
            return None

    def list_active(self, max_age_seconds: int = 86400) -> List[SessionState]:
        """List active sessions (not older than max_age_seconds)"""
        active_sessions = []
        now = time.time()
        
        for filename in os.listdir(self.sessions_dir):
            if not filename.endswith(".json"):
                continue
                
            session_id = filename[:-5]
            state = self.restore(session_id)
            
            if state and (now - state.last_active_timestamp) < max_age_seconds:
                active_sessions.append(state)
                
        # Sort by most recent
        active_sessions.sort(key=lambda s: s.last_active_timestamp, reverse=True)
        return active_sessions

    def _get_session_path(self, session_id: str) -> str:
        # Sanitize session_id to prevent path traversal
        safe_id = "".join(c for c in session_id if c.isalnum() or c in ('-', '_'))
        return os.path.join(self.sessions_dir, f"{safe_id}.json")
