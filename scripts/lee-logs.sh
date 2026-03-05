#!/bin/bash
# LEE 工作流日志查看工具

WORKFLOW_ID=${1:-"latest"}

echo "======================================"
echo "LEE 工作流日志查看器"
echo "======================================"
echo ""

if [ "$WORKFLOW_ID" = "latest" ]; then
    # 获取最新的工作流 ID
    WORKFLOW_ID=$(sqlite3 .workflow/orchestrator.db "SELECT id FROM workflow_instances ORDER BY created_at DESC LIMIT 1;" 2>/dev/null)
fi

echo "工作流 ID: $WORKFLOW_ID"
echo ""

echo "1️⃣  任务执行状态"
echo "--------------------------------------"
sqlite3 .workflow/orchestrator.db \
  "SELECT step_name, status,
    datetime(started_at) as started,
    datetime(completed_at) as completed,
    round((julianday(completed_at) - julianday(started_at)) * 86400) as seconds
   FROM task_executions
   WHERE workflow_id = '$WORKFLOW_ID'
   ORDER BY started_at;" \
  2>/dev/null | column -t -s '|'

echo ""
echo "2️⃣  当前工作流状态"
echo "--------------------------------------"
STATUS=$(sqlite3 .workflow/orchestrator.db \
  "SELECT status FROM workflow_instances WHERE id = '$WORKFLOW_ID';" 2>/dev/null)
echo "状态: $STATUS"

echo ""
echo "3️⃣  最近的事件日志"
echo "--------------------------------------"
grep "$WORKFLOW_ID" .workflow/events.jsonl 2>/dev/null | tail -5 | jq -r '[.timestamp, .event_type, .step_id]' 2>/dev/null

echo ""
echo "4️⃣  Claude Code 执行日志"
echo "--------------------------------------"
# 找到最新的执行目录
LATEST_DIR=$(ls -td .workflow/claude-code/* 2>/dev/null | head -1)
if [ -n "$LATEST_DIR" ]; then
    echo "最新执行目录: $LATEST_DIR"
    echo ""
    if [ -f "$LATEST_DIR/conversation.log" ]; then
        echo "对话日志（最后 20 行）:"
        tail -20 "$LATEST_DIR/conversation.log"
    elif [ -f "$LATEST_DIR/claude-debug.log" ]; then
        echo "调试日志（最后 10 行）:"
        tail -10 "$LATEST_DIR/claude-debug.log" | grep -E "ERROR|WARN|Stream|Permission"
    fi
else
    echo "没有找到执行日志"
fi

echo ""
echo "======================================"
echo "其他查看命令："
echo "--------------------------------------"
echo "实时监控事件："
echo "  tail -f .workflow/events.jsonl | jq"
echo ""
echo "查看特定工作流："
echo "  lee status $WORKFLOW_ID"
echo ""
echo "查看数据库："
echo "  sqlite3 .workflow/orchestrator.db"
echo ""
