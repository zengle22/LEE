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
