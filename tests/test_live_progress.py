import json
import sqlite3
from pathlib import Path

from lee.cli.commands.live_progress import (
    format_execution_boundary_summary,
    WorkflowLiveOutputFollower,
    classify_live_execution_state,
    format_live_execution_state,
    get_execution_boundary_summaries,
    get_running_live_executions,
)


def _prepare_db(tmp_path: Path) -> Path:
    db_dir = tmp_path / ".workflow"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "orchestrator.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE task_executions (
            id TEXT PRIMARY KEY,
            workflow_id TEXT,
            step_name TEXT,
            executor_type TEXT,
            input_data TEXT,
            output_data TEXT,
            status TEXT,
            started_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    return db_path


def test_classify_live_execution_state_from_heartbeat() -> None:
    result = classify_live_execution_state(
        [
            "[2026-03-12T12:00:00][meta] pid=123",
            "[2026-03-12T12:00:10][meta] heartbeat elapsed=10s silent_for=4s stdout_lines=0 stderr_lines=0",
        ]
    )
    assert result["state"] == "streaming"
    assert result["elapsed_seconds"] == 10
    assert result["silent_for_seconds"] == 4

    stalled = classify_live_execution_state(
        [
            "[2026-03-12T12:00:30][meta] heartbeat elapsed=30s silent_for=30s stdout_lines=0 stderr_lines=0",
        ]
    )
    assert stalled["state"] == "stalled"


def test_get_running_live_executions_reads_evidence_base(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    evidence_dir = tmp_path / ".workflow" / "claude-code" / "RUN-1-step"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    live_log = evidence_dir / "conversation.live.log"
    live_log.write_text(
        "\n".join(
            [
                "[2026-03-12T12:00:00][meta] pid=123",
                "[2026-03-12T12:00:15][meta] heartbeat elapsed=15s silent_for=12s stdout_lines=0 stderr_lines=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO task_executions (id, workflow_id, step_name, executor_type, input_data, status, started_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "exec1",
            "wf_task_1",
            "task_planning",
            "claude_code",
            json.dumps({"evidence_base": str(evidence_dir)}),
            "running",
            "2026-03-12T12:00:00",
        ),
    )
    conn.commit()
    conn.close()

    states = get_running_live_executions(tmp_path, "wf_task_1")
    assert len(states) == 1
    state = states[0]
    assert state.step_name == "task_planning"
    assert state.state == "quiet"
    assert "silent_for=12s" in format_live_execution_state(state)


def test_workflow_live_output_follower_skips_old_lines_and_emits_new_lines(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    evidence_dir = tmp_path / ".workflow" / "claude-code" / "RUN-1-step"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    live_log = evidence_dir / "conversation.live.log"
    live_log.write_text("[2026-03-12T12:00:00][meta] pid=123\n", encoding="utf-8")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO task_executions (id, workflow_id, step_name, executor_type, input_data, status, started_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "exec1",
            "wf_task_1",
            "task_planning",
            "claude_code",
            json.dumps({"evidence_base": str(evidence_dir)}),
            "running",
            "2026-03-12T12:00:00",
        ),
    )
    conn.commit()
    conn.close()

    follower = WorkflowLiveOutputFollower(tmp_path, "wf_task_1")
    first_messages = follower.poll_messages()
    assert any("接入实时输出" in message for message in first_messages)
    assert not any("[stdout]" in message for message in first_messages)

    with open(live_log, "a", encoding="utf-8") as handle:
        handle.write("[2026-03-12T12:00:01][stdout] hello world\n")

    second_messages = follower.poll_messages()
    assert any("[task_planning][stdout] hello world" in message for message in second_messages)


def test_get_execution_boundary_summaries_reads_evidence_and_output_paths(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    evidence_dir = tmp_path / ".workflow" / "claude-code" / "RUN-1-step"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    live_log = evidence_dir / "conversation.live.log"
    live_log.write_text(
        "[2026-03-12T12:00:15][meta] heartbeat elapsed=15s silent_for=12s stdout_lines=0 stderr_lines=0\n",
        encoding="utf-8",
    )
    debug_log = evidence_dir / "claude-debug.log"
    debug_log.write_text("debug", encoding="utf-8")
    conversation_log = evidence_dir / "conversation.log"
    conversation_log.write_text("conversation", encoding="utf-8")
    prompt_system = evidence_dir / "prompt.system.txt"
    prompt_system.write_text("sys", encoding="utf-8")
    prompt_user = evidence_dir / "prompt.user.txt"
    prompt_user.write_text("user", encoding="utf-8")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO task_executions (id, workflow_id, step_name, executor_type, input_data, output_data, status, started_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "exec1",
            "wf_task_1",
            "task_planning",
            "claude_code",
            json.dumps({"evidence_base": str(evidence_dir)}),
            json.dumps(
                {
                    "conversation_log_path": str(conversation_log),
                    "debug_log_path": str(debug_log),
                    "prompt_system_path": str(prompt_system),
                    "prompt_user_path": str(prompt_user),
                }
            ),
            "running",
            "2026-03-12T12:00:00",
        ),
    )
    conn.commit()
    conn.close()

    summaries = get_execution_boundary_summaries(tmp_path, "wf_task_1")
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.evidence_dir == evidence_dir
    assert summary.debug_log_path == debug_log
    assert summary.conversation_log_path == conversation_log
    lines = format_execution_boundary_summary(summary, tmp_path)
    assert any("恢复入口:" in line for line in lines)
    assert any("日志边界:" in line for line in lines)
