"""
LEE Orchestrator v3.0 - 统一存储层（SQLite）

本模块提供 SQLite 存储层实现，是所有状态的唯一权威。

核心原则：
- SQLite 是唯一状态权威
- 所有状态变更必须通过 Orchestrator
- 提供事务支持和数据一致性
"""

import aiosqlite
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from lee.orchestrator.storage.models import (
    WorkflowInstance,
    WorkflowLevel,
    WorkflowStatus,
    TaskExecution,
    TaskExecutionStatus,
    Template,
    GateApproval,
    GateStatus,
)


class SQLiteStore:
    """
    SQLite 存储层 - 唯一状态存储权威

    设计原则：
    1. 所有状态存储在 SQLite
    2. 支持事务
    3. 提供完整的 CRUD 接口
    """

    def __init__(self, db_path: str = ":memory:"):
        """
        初始化 SQLite 存储

        Args:
            db_path: 数据库文件路径，默认为内存数据库
        """
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self._transaction_depth: int = 0

    async def connect(self):
        """建立数据库连接并创建表结构"""
        self._conn = await aiosqlite.connect(self.db_path)
        await self._init_tables()

    async def close(self):
        """关闭数据库连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None

    # ========================================================================
    # 事务支持 (v1.1)
    # ========================================================================

    def transaction(self, isolation_level: str = "REPEATABLE_READ"):
        """
        事务上下文管理器

        Args:
            isolation_level: 隔离级别
                - "REPEATABLE_READ": 可重复读（默认，使用 BEGIN IMMEDIATE）
                - "DEFERRED": 延迟事务（使用 BEGIN DEFERRED）
                - "IMMEDIATE": 立即事务（使用 BEGIN IMMEDIATE）
                - "EXCLUSIVE": 排他事务（使用 BEGIN EXCLUSIVE）

        Yields:
            aiosqlite.Cursor: 事务内的游标对象

        Example:
            async with store.transaction() as cursor:
                await cursor.execute("INSERT INTO ...")
                await cursor.execute("UPDATE ...")
            # 自动提交或回滚
        """
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _transaction_context():
            if self._conn is None:
                raise RuntimeError("Database not connected. Call connect() first.")
            if self._transaction_depth > 0:
                raise RuntimeError("Nested transactions are not supported.")

            cursor = await self._conn.cursor()
            self._transaction_depth += 1
            try:
                # 根据隔离级别选择 BEGIN 语句
                if isolation_level == "REPEATABLE_READ":
                    # SQLite 的 REPEATABLE READ 通过 BEGIN IMMEDIATE 实现
                    await self.execute("BEGIN IMMEDIATE")
                elif isolation_level == "DEFERRED":
                    await self.execute("BEGIN DEFERRED")
                elif isolation_level == "IMMEDIATE":
                    await self.execute("BEGIN IMMEDIATE")
                elif isolation_level == "EXCLUSIVE":
                    await self.execute("BEGIN EXCLUSIVE")
                else:
                    raise ValueError(f"Unknown isolation level: {isolation_level}")

                yield cursor

                await self.execute("COMMIT")

            except Exception as e:
                # 发生异常时回滚
                try:
                    await self.execute("ROLLBACK")
                except Exception as rollback_error:
                    # 回滚失败，记录错误但不掩盖原始异常
                    print(f"Warning: ROLLBACK failed: {rollback_error}")
                raise e
            finally:
                if self._transaction_depth > 0:
                    self._transaction_depth -= 1
                await cursor.close()

        return _transaction_context()

    async def execute(self, sql: str, parameters: tuple = ()):
        """
        执行 SQL 语句（便捷方法）

        Args:
            sql: SQL 语句
            parameters: 参数元组

        Returns:
            aiosqlite.Cursor
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return await self._conn.execute(sql, parameters)

    async def executemany(self, sql: str, parameters_list: list):
        """
        批量执行 SQL 语句（便捷方法）

        Args:
            sql: SQL 语句
            parameters_list: 参数列表

        Returns:
            aiosqlite.Cursor
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return await self._conn.executemany(sql, parameters_list)

    # ========================================================================
    # 内部方法
    # ========================================================================

    async def _init_tables(self):
        """初始化数据库表结构"""
        # 工作流实例表（统一 L1/L2/L3）
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_instances (
                id TEXT PRIMARY KEY,
                level TEXT NOT NULL,
                parent_id TEXT,
                template_id TEXT,
                status TEXT NOT NULL,
                current_step TEXT,
                data TEXT,
                created_at TEXT,
                updated_at TEXT,
                completed_at TEXT,

                FOREIGN KEY (parent_id) REFERENCES workflow_instances(id)
            )
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_parent
            ON workflow_instances(parent_id)
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_status
            ON workflow_instances(status)
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_level
            ON workflow_instances(level)
        """)

        # 任务执行记录表
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS task_executions (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                executor_type TEXT,
                input_data TEXT,
                output_data TEXT,
                status TEXT,
                error_message TEXT,
                started_at TEXT,
                completed_at TEXT,
                invalidated_at TEXT,

                FOREIGN KEY (workflow_id) REFERENCES workflow_instances(id)
            )
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_workflow
            ON task_executions(workflow_id)
        """)

        # 模板定义表
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                level TEXT NOT NULL,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                version TEXT,
                created_at TEXT
            )
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_template_level
            ON templates(level)
        """)

        # 门禁审批表
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS gate_approvals (
                workflow_id TEXT NOT NULL,
                gate_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                status TEXT NOT NULL,
                approver TEXT,
                comments TEXT,
                created_at TEXT,
                decided_at TEXT,
                approval_criteria TEXT,
                reviewers TEXT,
                version INTEGER DEFAULT 1,
                default_reject_action TEXT,
                default_reject_target TEXT,
                default_revise_action TEXT,
                default_revise_target TEXT,
                decision_action TEXT,
                target_step TEXT,
                structured_feedback TEXT,
                issues TEXT,
                invalidated_at TEXT,

                PRIMARY KEY (workflow_id, gate_id),
                FOREIGN KEY (workflow_id) REFERENCES workflow_instances(id)
            )
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_gate_status
            ON gate_approvals(status)
        """)

        await self._conn.commit()

    # ========================================================================
    # WorkflowInstance 操作
    # ========================================================================

    async def create_workflow(
        self,
        instance: WorkflowInstance
    ) -> WorkflowInstance:
        """创建工作流实例"""
        await self._conn.execute("""
            INSERT INTO workflow_instances
            (id, level, parent_id, template_id, status, current_step, data, created_at, updated_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            instance.id,
            instance.level.value,
            instance.parent_id,
            instance.template_id,
            instance.status.value,
            instance.current_step,
            json.dumps(instance.data),
            instance.created_at.isoformat(),
            instance.updated_at.isoformat(),
            instance.completed_at.isoformat() if instance.completed_at else None,
        ))
        await self._conn.commit()
        return instance

    async def get_workflow(
        self,
        workflow_id: str
    ) -> Optional[WorkflowInstance]:
        """获取工作流实例"""
        cursor = await self._conn.execute("""
            SELECT * FROM workflow_instances WHERE id = ?
        """, (workflow_id,))
        row = await cursor.fetchone()
        return self._row_to_workflow(row) if row else None

    async def update_workflow_status(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        current_step: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        clear_current_step: bool = False
    ):
        """更新工作流状态"""
        updated_at = datetime.now()

        # 构建 SET 子句
        set_clauses = ["status = ?", "updated_at = ?"]
        params = [status.value, updated_at.isoformat()]

        # 更新 current_step（如果提供或明确清除）
        if clear_current_step:
            set_clauses.append("current_step = NULL")
        elif current_step is not None:
            set_clauses.append("current_step = ?")
            params.append(current_step)

        if completed_at is not None:
            set_clauses.append("completed_at = ?")
            params.append(completed_at.isoformat())

        params.append(workflow_id)

        await self._conn.execute(f"""
            UPDATE workflow_instances
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """, params)
        await self._conn.commit()

    async def update_workflow_data(
        self,
        workflow_id: str,
        data: Dict[str, Any]
    ):
        """更新工作流数据"""
        updated_at = datetime.now()
        await self._conn.execute("""
            UPDATE workflow_instances
            SET data = ?, updated_at = ?
            WHERE id = ?
        """, (
            json.dumps(data),
            updated_at.isoformat(),
            workflow_id,
        ))
        await self._conn.commit()

    async def update_workflow_data_and_clear_current_step(
        self,
        workflow_id: str,
        data: Dict[str, Any],
        status: WorkflowStatus
    ):
        """
        原子性更新工作流数据并清除 current_step（BUG-2026-0040）

        在单个事务中完成：
        1. 更新 workflow_instances.data
        2. 清除 current_step（设置为 NULL）
        3. 更新 updated_at

        这确保了 completed_steps 更新和 current_step 清除的原子性。
        """
        updated_at = datetime.now()
        await self._conn.execute("""
            UPDATE workflow_instances
            SET data = ?,
                current_step = NULL,
                status = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            json.dumps(data),
            status.value,
            updated_at.isoformat(),
            workflow_id,
        ))
        await self._conn.commit()

    async def get_children(
        self,
        parent_id: str
    ) -> List[WorkflowInstance]:
        """获取子工作流实例"""
        cursor = await self._conn.execute("""
            SELECT * FROM workflow_instances
            WHERE parent_id = ?
            ORDER BY created_at ASC
        """, (parent_id,))
        rows = await cursor.fetchall()
        return [self._row_to_workflow(row) for row in rows]

    async def get_all_instances(
        self,
        level: Optional[WorkflowLevel] = None
    ) -> List[WorkflowInstance]:
        """获取所有工作流实例（可选按层级过滤）"""
        if level:
            cursor = await self._conn.execute("""
                SELECT * FROM workflow_instances
                WHERE level = ?
                ORDER BY created_at DESC
            """, (level.value,))
        else:
            cursor = await self._conn.execute("""
                SELECT * FROM workflow_instances
                ORDER BY created_at DESC
            """)
        rows = await cursor.fetchall()
        return [self._row_to_workflow(row) for row in rows]

    async def list_workflows(
        self,
        limit: int = 100,
        status: Optional[WorkflowStatus] = None,
        level: Optional[WorkflowLevel] = None,
        parent_id: Optional[str] = None
    ) -> List[WorkflowInstance]:
        """
        List workflows with optional filters.

        Args:
            limit: Maximum number of workflows to return
            status: Optional status filter
            level: Optional level filter
            parent_id: Optional parent_id filter

        Returns:
            List of workflows, ordered by created_at DESC
        """
        sql = "SELECT * FROM workflow_instances WHERE 1=1"
        params = []

        if status:
            sql += " AND status = ?"
            params.append(status.value)

        if level:
            sql += " AND level = ?"
            params.append(level.value)

        if parent_id:
            sql += " AND parent_id = ?"
            params.append(parent_id)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = await self._conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [self._row_to_workflow(row) for row in rows]

    # ========================================================================
    # TaskExecution 操作
    # ========================================================================

    async def create_task_execution(
        self,
        execution: TaskExecution
    ) -> TaskExecution:
        """创建任务执行记录"""
        await self._conn.execute("""
            INSERT INTO task_executions
            (id, workflow_id, step_name, executor_type, input_data, output_data,
             status, error_message, started_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution.id,
            execution.workflow_id,
            execution.step_name,
            execution.executor_type,
            json.dumps(execution.input_data),
            json.dumps(execution.output_data) if execution.output_data else None,
            execution.status.value,
            execution.error_message,
            execution.started_at.isoformat() if execution.started_at else None,
            execution.completed_at.isoformat() if execution.completed_at else None,
        ))
        await self._conn.commit()
        return execution

    async def get_task_executions(
        self,
        workflow_id: str
    ) -> List[TaskExecution]:
        """获取工作流的所有任务执行记录"""
        cursor = await self._conn.execute("""
            SELECT * FROM task_executions
            WHERE workflow_id = ?
            ORDER BY started_at ASC
        """, (workflow_id,))
        rows = await cursor.fetchall()
        return [self._row_to_task_execution(row) for row in rows]

    async def update_task_execution(
        self,
        execution_id: str,
        status: TaskExecutionStatus,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None
    ) -> Optional[TaskExecution]:
        """更新任务执行记录"""
        # 构建更新语句
        set_clauses = ["status = ?"]
        params = [status.value]

        if output_data is not None:
            set_clauses.append("output_data = ?")
            params.append(json.dumps(output_data))

        if error_message is not None:
            set_clauses.append("error_message = ?")
            params.append(error_message)

        if completed_at is not None:
            set_clauses.append("completed_at = ?")
            params.append(completed_at.isoformat())

        params.append(execution_id)

        await self._conn.execute(f"""
            UPDATE task_executions
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """, params)
        await self._conn.commit()

        # 返回更新后的记录（需要查询获取）
        cursor = await self._conn.execute("""
            SELECT * FROM task_executions WHERE id = ?
        """, (execution_id,))
        row = await cursor.fetchone()
        return self._row_to_task_execution(row) if row else None

    async def fail_running_task_executions(
        self,
        workflow_id: str,
        error_message: str = "Workflow interrupted; running step marked as failed",
        completed_at: Optional[datetime] = None,
    ) -> int:
        """
        将工作流下所有 RUNNING 的 task_executions 收敛为 FAILED。

        返回受影响的记录条数。
        """
        done_at = (completed_at or datetime.now()).isoformat()
        cursor = await self._conn.execute("""
            UPDATE task_executions
            SET status = ?,
                error_message = COALESCE(?, error_message),
                completed_at = COALESCE(?, completed_at)
            WHERE workflow_id = ?
              AND status = 'running'
            """,
            (
                TaskExecutionStatus.FAILED.value,
                error_message,
                done_at,
                workflow_id,
            ),
        )
        await self._conn.commit()
        return cursor.rowcount or 0

    async def find_stale_task_executions(
        self,
        threshold_minutes: int = 30,
    ) -> List[TaskExecution]:
        """
        查找长时间处于 RUNNING 状态的 task_executions（BUG-2026-0038 监控）

        Args:
            threshold_minutes: 阈值（分钟），超过此时间的 RUNNING 记录被视为 stale

        Returns:
            所有 stale 的 task_execution 列表
        """
        from datetime import timedelta

        threshold_time = datetime.now() - timedelta(minutes=threshold_minutes)

        cursor = await self._conn.execute("""
            SELECT * FROM task_executions
            WHERE status = 'running'
              AND started_at < ?
            ORDER BY started_at ASC
        """, (threshold_time.isoformat(),))

        rows = await cursor.fetchall()
        return [self._row_to_task_execution(row) for row in rows]

    async def get_stale_task_executions_summary(
        self,
        threshold_minutes: int = 30,
    ) -> Dict[str, Any]:
        """
        获取 stale task_executions 的摘要信息

        Args:
            threshold_minutes: 阈值（分钟）

        Returns:
            摘要字典，包含：
            - count: stale 记录数量
            - oldest_started_at: 最早的启动时间
            - workflows: 受影响的工作流 ID 列表
        """
        from datetime import timedelta

        threshold_time = datetime.now() - timedelta(minutes=threshold_minutes)

        # 获取数量
        cursor = await self._conn.execute("""
            SELECT COUNT(*) FROM task_executions
            WHERE status = 'running' AND started_at < ?
        """, (threshold_time.isoformat(),))
        count_row = await cursor.fetchone()
        count = count_row[0] if count_row else 0

        if count == 0:
            return {
                "count": 0,
                "oldest_started_at": None,
                "workflows": [],
            }

        # 获取最早的启动时间
        cursor = await self._conn.execute("""
            SELECT MIN(started_at) FROM task_executions
            WHERE status = 'running' AND started_at < ?
        """, (threshold_time.isoformat(),))
        oldest_row = await cursor.fetchone()
        oldest_started_at = oldest_row[0] if oldest_row else None

        # 获取受影响的工作流 ID 列表
        cursor = await self._conn.execute("""
            SELECT DISTINCT workflow_id FROM task_executions
            WHERE status = 'running' AND started_at < ?
        """, (threshold_time.isoformat(),))
        workflow_rows = await cursor.fetchall()
        workflows = [row[0] for row in workflow_rows]

        return {
            "count": count,
            "oldest_started_at": oldest_started_at,
            "workflows": workflows,
        }

    async def fail_running_task_executions(
        self,
        workflow_id: str,
        error_message: str = "Workflow interrupted; running step marked as failed",
        completed_at: Optional[datetime] = None,
    ) -> int:
        """
        将工作流下所有 RUNNING 的 task_executions 收敛为 FAILED。

        返回受影响的记录条数。
        """
        done_at = (completed_at or datetime.now()).isoformat()
        cursor = await self._conn.execute("""
            UPDATE task_executions
            SET status = ?,
                error_message = COALESCE(error_message, ?),
                completed_at = COALESCE(completed_at, ?)
            WHERE workflow_id = ?
              AND status = ?
            """,
            (
                TaskExecutionStatus.FAILED.value,
                error_message,
                done_at,
                workflow_id,
                TaskExecutionStatus.RUNNING.value,
            ),
        )
        await self._conn.commit()
        return cursor.rowcount or 0

    async def list_task_executions(
        self,
        workflow_id: str,
        limit: int = 100,
        status: Optional[TaskExecutionStatus] = None
    ) -> List[TaskExecution]:
        """
        List task executions for a workflow.

        Args:
            workflow_id: Workflow ID
            limit: Maximum number of executions to return
            status: Optional status filter

        Returns:
            List of task executions, ordered by started_at DESC
        """
        sql = """
            SELECT * FROM task_executions
            WHERE workflow_id = ?
        """
        params = [workflow_id]

        if status:
            sql += " AND status = ?"
            params.append(status.value)

        sql += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        cursor = await self._conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [self._row_to_task_execution(row) for row in rows]

    # ========================================================================
    # Template 操作
    # ========================================================================

    async def create_template(
        self,
        template: Template
    ) -> Template:
        """创建模板"""
        await self._conn.execute("""
            INSERT INTO templates
            (id, level, name, content, version, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            template.id,
            template.level.value,
            template.name,
            template.content,
            template.version,
            template.created_at.isoformat(),
        ))
        await self._conn.commit()
        return template

    async def get_template(
        self,
        template_id: str
    ) -> Optional[Template]:
        """获取模板"""
        cursor = await self._conn.execute("""
            SELECT * FROM templates WHERE id = ?
        """, (template_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return Template(
            id=row[0],
            level=WorkflowLevel(row[1]),
            name=row[2],
            content=row[3],
            version=row[4],
            created_at=datetime.fromisoformat(row[5]),
        )

    # ========================================================================
    # 辅助方法
    # ========================================================================

    @staticmethod
    def _row_to_workflow(row) -> WorkflowInstance:
        """将数据库行转换为 WorkflowInstance"""
        return WorkflowInstance(
            id=row[0],
            level=WorkflowLevel(row[1]),
            parent_id=row[2],
            template_id=row[3],
            status=WorkflowStatus(row[4]),
            current_step=row[5],
            data=json.loads(row[6]) if row[6] else {},
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]),
            completed_at=datetime.fromisoformat(row[9]) if row[9] else None,
        )

    @staticmethod
    def _row_to_task_execution(row) -> TaskExecution:
        """将数据库行转换为 TaskExecution"""
        return TaskExecution(
            id=row[0],
            workflow_id=row[1],
            step_name=row[2],
            executor_type=row[3],
            input_data=json.loads(row[4]) if row[4] else {},
            output_data=json.loads(row[5]) if row[5] else None,
            status=TaskExecutionStatus(row[6]),
            error_message=row[7],
            started_at=datetime.fromisoformat(row[8]) if row[8] else None,
            completed_at=datetime.fromisoformat(row[9]) if row[9] else None,
        )

    # ========================================================================
    # GateApproval 操作
    # ========================================================================

    async def create_gate_approval(
        self,
        gate: GateApproval
    ) -> GateApproval:
        """
        创建门禁审批记录

        v1.1: 支持新增字段（version, default_action, decision_action 等）
        """
        # 检查 gate_approvals 表是否有新列
        # 如果没有（旧版本），则不插入新字段
        try:
            await self._conn.execute("""
                INSERT INTO gate_approvals
                (workflow_id, gate_id, step_id, status, approver, comments,
                 created_at, decided_at, approval_criteria, reviewers,
                 version, default_reject_action, default_reject_target,
                 default_revise_action, default_revise_target,
                 decision_action, target_step)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                gate.workflow_id,
                gate.gate_id,
                gate.step_id,
                gate.status.value,
                gate.approver,
                gate.comments,
                gate.created_at.isoformat(),
                gate.decided_at.isoformat() if gate.decided_at else None,
                json.dumps(gate.approval_criteria),
                json.dumps(gate.reviewers),
                gate.version,
                gate.default_reject_action,
                gate.default_reject_target,
                gate.default_revise_action,
                gate.default_revise_target,
                gate.decision_action,
                gate.target_step,
            ))
        except aiosqlite.OperationalError as e:
            # 如果新列不存在，回退到旧版本插入
            if "column" in str(e).lower():
                await self._conn.execute("""
                    INSERT INTO gate_approvals
                    (workflow_id, gate_id, step_id, status, approver, comments,
                     created_at, decided_at, approval_criteria, reviewers)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    gate.workflow_id,
                    gate.gate_id,
                    gate.step_id,
                    gate.status.value,
                    gate.approver,
                    gate.comments,
                    gate.created_at.isoformat(),
                    gate.decided_at.isoformat() if gate.decided_at else None,
                    json.dumps(gate.approval_criteria),
                    json.dumps(gate.reviewers),
                ))
            else:
                raise

        await self._conn.commit()
        return gate

    async def get_gate_approval(
        self,
        workflow_id: str,
        gate_id: str
    ) -> Optional[GateApproval]:
        """获取门禁审批记录"""
        cursor = await self._conn.execute("""
            SELECT * FROM gate_approvals
            WHERE workflow_id = ? AND gate_id = ?
        """, (workflow_id, gate_id))
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_gate_approval(row)

    async def update_gate_approval(
        self,
        workflow_id: str,
        gate_id: str,
        status: GateStatus,
        approver: Optional[str] = None,
        comments: Optional[str] = None
    ) -> GateApproval:
        """更新门禁审批状态"""
        decided_at = datetime.now()
        await self._conn.execute("""
            UPDATE gate_approvals
            SET status = ?, approver = ?, comments = ?, decided_at = ?
            WHERE workflow_id = ? AND gate_id = ?
        """, (
            status.value,
            approver,
            comments,
            decided_at.isoformat(),
            workflow_id,
            gate_id,
        ))
        await self._conn.commit()

        # 返回更新后的记录
        return await self.get_gate_approval(workflow_id, gate_id)

    async def get_pending_gates(
        self,
        workflow_id: str
    ) -> List[GateApproval]:
        """获取工作流的待审批门禁列表"""
        cursor = await self._conn.execute("""
            SELECT * FROM gate_approvals
            WHERE workflow_id = ? AND status = 'pending'
            ORDER BY created_at ASC
        """, (workflow_id,))
        rows = await cursor.fetchall()
        return [self._row_to_gate_approval(row) for row in rows]

    async def get_gate_approvals(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[GateApproval]:
        """
        获取门禁审批记录（可按 workflow_id/status 过滤）
        """
        sql = "SELECT * FROM gate_approvals"
        where_clauses: List[str] = []
        params: List[Any] = []

        if workflow_id:
            where_clauses.append("workflow_id = ?")
            params.append(workflow_id)

        if status:
            where_clauses.append("status = ?")
            params.append(status)

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY created_at ASC"

        cursor = await self._conn.execute(sql, tuple(params))
        rows = await cursor.fetchall()
        return [self._row_to_gate_approval(row) for row in rows]

    async def update_gate_approval_with_version(
        self,
        workflow_id: str,
        gate_id: str,
        status: GateStatus,
        approver: Optional[str] = None,
        comments: Optional[str] = None,
        expected_version: Optional[int] = None,
        decision_action: Optional[str] = None,
        target_step: Optional[str] = None,
        structured_feedback: Optional[Dict[str, Any]] = None,
        issues: Optional[List[str]] = None,
    ) -> Optional[GateApproval]:
        """
        更新门禁审批状态（带版本检查）

        v1.1: 支持乐观锁，防止并发决策冲突

        Args:
            workflow_id: 工作流 ID
            gate_id: 门禁 ID
            status: 新状态
            approver: 审批人
            comments: 审批意见
            expected_version: 期望的版本号（用于乐观锁）
            decision_action: 决策动作
            target_step: 目标步骤
            structured_feedback: 结构化反馈
            issues: 问题列表

        Returns:
            更新后的 GateApproval，如果版本不匹配返回 None（并发冲突）

        Raises:
            ValueError: 如果 gate 不存在
        """
        # 检查 gate 是否存在
        current = await self.get_gate_approval(workflow_id, gate_id)
        if current is None:
            raise ValueError(f"Gate not found: {workflow_id}/{gate_id}")

        # 如果没有指定期望版本，使用当前版本
        if expected_version is None:
            expected_version = current.version

        decided_at = datetime.now()

        # 尝试更新（带版本检查）
        try:
            # 检查表是否有 version 列
            cursor = await self._conn.execute("""
                UPDATE gate_approvals
                SET status = ?,
                    approver = ?,
                    comments = ?,
                    decided_at = ?,
                    version = version + 1
                WHERE workflow_id = ? AND gate_id = ? AND version = ?
            """, (
                status.value,
                approver,
                comments,
                decided_at.isoformat(),
                workflow_id,
                gate_id,
                expected_version,
            ))

            # 检查是否更新成功
            if cursor.rowcount == 0:
                # 版本不匹配，并发冲突
                return None

            # 如果有其他新字段，也尝试更新
            try:
                if decision_action is not None:
                    await self._conn.execute("""
                        UPDATE gate_approvals
                        SET decision_action = ?
                        WHERE workflow_id = ? AND gate_id = ?
                    """, (decision_action, workflow_id, gate_id))

                if target_step is not None:
                    await self._conn.execute("""
                        UPDATE gate_approvals
                        SET target_step = ?
                        WHERE workflow_id = ? AND gate_id = ?
                    """, (target_step, workflow_id, gate_id))

                if structured_feedback is not None:
                    await self._conn.execute("""
                        UPDATE gate_approvals
                        SET structured_feedback = ?
                        WHERE workflow_id = ? AND gate_id = ?
                    """, (json.dumps(structured_feedback), workflow_id, gate_id))

                if issues is not None:
                    await self._conn.execute("""
                        UPDATE gate_approvals
                        SET issues = ?
                        WHERE workflow_id = ? AND gate_id = ?
                    """, (json.dumps(issues), workflow_id, gate_id))

            except aiosqlite.OperationalError:
                # 新列可能不存在，忽略
                pass

            await self._conn.commit()

            # 返回更新后的记录
            return await self.get_gate_approval(workflow_id, gate_id)

        except aiosqlite.OperationalError as e:
            # 如果 version 列不存在，使用旧版本更新逻辑
            if "version" in str(e).lower():
                return await self.update_gate_approval(
                    workflow_id, gate_id, status, approver, comments
                )
            raise

    @staticmethod
    def _row_to_gate_approval(row) -> GateApproval:
        """
        将数据库行转换为 GateApproval

        v1.1: 支持新字段的解析
        """
        # 基本字段（索引 0-9）
        workflow_id = row[0]
        gate_id = row[1]
        step_id = row[2]
        status = GateStatus(row[3])
        approver = row[4]
        comments = row[5]
        created_at = datetime.fromisoformat(row[6])
        decided_at = datetime.fromisoformat(row[7]) if row[7] else None
        approval_criteria = json.loads(row[8]) if row[8] else []
        reviewers = json.loads(row[9]) if row[9] else []

        # v1.1 新字段（索引 10+）
        # 注意：旧版本数据库可能没有这些列
        version = 1
        default_reject_action = None
        default_reject_target = None
        default_revise_action = None
        default_revise_target = None
        decision_action = None
        target_step = None
        structured_feedback = None
        issues = None
        invalidated_at = None

        # 尝试解析新字段
        try:
            if len(row) > 10:
                version = row[10] if row[10] is not None else 1
            if len(row) > 11:
                default_reject_action = row[11]
            if len(row) > 12:
                default_reject_target = row[12]
            if len(row) > 13:
                default_revise_action = row[13]
            if len(row) > 14:
                default_revise_target = row[14]
            if len(row) > 15:
                decision_action = row[15]
            if len(row) > 16:
                target_step = row[16]
            if len(row) > 17 and row[17]:
                structured_feedback = json.loads(row[17])
            if len(row) > 18 and row[18]:
                issues = json.loads(row[18])
            if len(row) > 19 and row[19]:
                invalidated_at = datetime.fromisoformat(row[19])
        except (IndexError, json.JSONDecodeError, ValueError):
            # 新字段不存在或解析失败，使用默认值
            pass

        return GateApproval(
            workflow_id=workflow_id,
            gate_id=gate_id,
            step_id=step_id,
            status=status,
            approver=approver,
            comments=comments,
            created_at=created_at,
            decided_at=decided_at,
            approval_criteria=approval_criteria,
            reviewers=reviewers,
            version=version,
            default_reject_action=default_reject_action,
            default_reject_target=default_reject_target,
            default_revise_action=default_revise_action,
            default_revise_target=default_revise_target,
            decision_action=decision_action,
            target_step=target_step,
            structured_feedback=structured_feedback,
            issues=issues,
            invalidated_at=invalidated_at,
        )
