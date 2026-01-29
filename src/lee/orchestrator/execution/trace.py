"""
Trace - Span-based Execution Tracing

基于 execution-trace contract (v1.0) 实现的追踪系统。

核心概念:
- Run: 一次工作流执行的顶层记录
- Span: 执行跨度 - 追踪的最小单元 (有开始和结束时间)
- Artifact: 产物记录

设计原则:
1. 日志是基础设施，不是智能行为
2. 事实由系统采集，Agent 只做可选语义补充
3. 所有外部动作通过工具层，工具层强制打点
4. 不可绕过、不可伪造、结构化可查询

参考: ai-spec/specs/common/contracts/execution-trace/v1/contract.yaml
"""

import json
import hashlib
import re
import secrets
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
import threading


# ============================================
# 常量定义
# ============================================

TRACES_DIR = ".workflow/traces"
TRACES_FILE = "traces.jsonl"
BLOBS_DIR = ".workflow/blobs"
MAX_INLINE_SIZE = 4096  # 超过此大小存对象存储


# ============================================
# 枚举类型
# ============================================

class SpanType(Enum):
    """跨度类型"""
    ORCHESTRATOR = "orchestrator"  # 编排器操作
    AGENT = "agent"                # Agent 调用
    TOOL = "tool"                  # 工具调用
    GATE = "gate"                  # 门禁检查
    VALIDATION = "validation"      # 验证操作
    IO = "io"                      # IO 操作


class SpanStatus(Enum):
    """跨度状态"""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class RunStatus(Enum):
    """运行状态"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ToolType(Enum):
    """工具类型"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    HTTP = "http"
    DB = "db"
    FS = "fs"
    SHELL = "shell"


class ArtifactType(Enum):
    """产物类型"""
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    REPORT = "report"
    TEST_RESULT = "test_result"
    COVERAGE = "coverage"
    DIFF = "diff"
    SCREENSHOT = "screenshot"
    LOG = "log"


# ============================================
# 脱敏规则
# ============================================

SANITIZATION_PATTERNS = [
    # Email
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]'),
    # Phone (Chinese)
    (r'1[3-9]\d{9}', '[PHONE]'),
    # API Key patterns
    (r'(sk-|api_key[=:]|token[=:])[a-zA-Z0-9_-]{20,}', '[API_KEY]'),
    # Password
    (r'(password|passwd|pwd)[=:][^\s]+', '[PASSWORD]', re.IGNORECASE),
    # ID Card (Chinese)
    (r'\d{17}[\dXx]', '[ID_CARD]'),
    # Bearer Token
    (r'Bearer [a-zA-Z0-9._-]+', 'Bearer [REDACTED]'),
    # Generic secrets
    (r'(secret|credential|key)[=:][^\s"\']*', r'\1=[REDACTED]', re.IGNORECASE),
]


def sanitize(text: str) -> str:
    """脱敏文本"""
    if not isinstance(text, str):
        return text

    for pattern in SANITIZATION_PATTERNS:
        if len(pattern) == 3:
            regex, replacement, flags = pattern
            text = re.sub(regex, replacement, text, flags=flags)
        else:
            regex, replacement = pattern
            text = re.sub(regex, replacement, text)

    return text


def compute_hash(data: Any) -> str:
    """计算数据 hash (SHA256 前16位)"""
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def generate_id(prefix: str) -> str:
    """生成唯一 ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(4)
    return f"{prefix}-{timestamp}-{random_part}"


# ============================================
# 数据结构
# ============================================

@dataclass
class ContentRef:
    """内容引用 (不直接存大内容)"""
    hash: str
    size_bytes: int
    content_ref: Optional[str] = None  # 对象存储引用
    summary: Optional[str] = None      # 内容摘要
    sanitized: bool = False

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ErrorInfo:
    """错误信息"""
    code: str
    message: str
    stack: Optional[str] = None

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class AgentInfo:
    """Agent 信息"""
    agent_id: str
    agent_name: Optional[str] = None
    agent_version: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ToolInfo:
    """工具信息"""
    tool_name: str
    tool_type: ToolType
    target: Optional[str] = None  # 操作目标

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['tool_type'] = self.tool_type.value
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class GateInfo:
    """门禁信息"""
    gate_id: str
    gate_type: str  # human | auto | quality
    approver: Optional[str] = None
    decision: Optional[str] = None  # approved | rejected | deferred
    evidence_refs: Optional[List[str]] = None

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Metrics:
    """度量指标"""
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_total: int = 0
    cost_usd: float = 0.0
    retries: int = 0
    api_calls: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Span:
    """执行跨度 - 追踪的最小单元"""
    span_id: str
    run_id: str
    span_type: SpanType
    name: str
    started_at: str
    status: SpanStatus = SpanStatus.RUNNING

    # 可选字段
    parent_span_id: Optional[str] = None
    trace_id: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None

    # 类型特有字段
    agent: Optional[AgentInfo] = None
    tool: Optional[ToolInfo] = None
    gate: Optional[GateInfo] = None

    # 输入输出
    input: Optional[ContentRef] = None
    output: Optional[ContentRef] = None

    # 度量
    metrics: Optional[Metrics] = None

    # 错误
    error: Optional[ErrorInfo] = None

    # 标签和属性
    tags: List[str] = field(default_factory=list)
    attributes: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        d = {
            'span_id': self.span_id,
            'run_id': self.run_id,
            'span_type': self.span_type.value,
            'name': self.name,
            'started_at': self.started_at,
            'status': self.status.value,
        }

        if self.parent_span_id:
            d['parent_span_id'] = self.parent_span_id
        if self.trace_id:
            d['trace_id'] = self.trace_id
        if self.completed_at:
            d['completed_at'] = self.completed_at
        if self.duration_ms is not None:
            d['duration_ms'] = self.duration_ms
        if self.agent:
            d['agent'] = self.agent.to_dict()
        if self.tool:
            d['tool'] = self.tool.to_dict()
        if self.gate:
            d['gate'] = self.gate.to_dict()
        if self.input:
            d['input'] = self.input.to_dict()
        if self.output:
            d['output'] = self.output.to_dict()
        if self.metrics:
            d['metrics'] = self.metrics.to_dict()
        if self.error:
            d['error'] = self.error.to_dict()
        if self.tags:
            d['tags'] = self.tags
        if self.attributes:
            d['attributes'] = self.attributes

        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'Span':
        d = d.copy()
        d['span_type'] = SpanType(d['span_type'])
        d['status'] = SpanStatus(d['status'])

        # 重建嵌套对象
        if 'agent' in d and d['agent']:
            d['agent'] = AgentInfo(**d['agent'])
        if 'tool' in d and d['tool']:
            tool_data = d['tool']
            tool_data['tool_type'] = ToolType(tool_data['tool_type'])
            d['tool'] = ToolInfo(**tool_data)
        if 'gate' in d and d['gate']:
            d['gate'] = GateInfo(**d['gate'])
        if 'input' in d and d['input']:
            d['input'] = ContentRef(**d['input'])
        if 'output' in d and d['output']:
            d['output'] = ContentRef(**d['output'])
        if 'metrics' in d and d['metrics']:
            d['metrics'] = Metrics(**d['metrics'])
        if 'error' in d and d['error']:
            d['error'] = ErrorInfo(**d['error'])

        return cls(**d)


@dataclass
class Artifact:
    """产物记录"""
    artifact_id: str
    run_id: str
    span_id: str
    artifact_type: ArtifactType
    path: str
    hash: str
    size_bytes: Optional[int] = None
    diff_ref: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['artifact_type'] = self.artifact_type.value
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class Run:
    """运行记录"""
    run_id: str
    workflow_id: str
    workflow_name: str
    started_at: str
    status: RunStatus = RunStatus.RUNNING

    workflow_version: Optional[str] = None
    completed_at: Optional[str] = None
    initiator: Dict = field(default_factory=dict)
    environment: Dict = field(default_factory=dict)
    config: Dict = field(default_factory=dict)
    summary: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['status'] = self.status.value
        return {k: v for k, v in d.items() if v is not None and v != {}}


# ============================================
# Context 管理 (线程本地存储)
# ============================================

class TraceContext:
    """追踪上下文"""
    _local = threading.local()

    @classmethod
    def get_current_run_id(cls) -> Optional[str]:
        return getattr(cls._local, 'run_id', None)

    @classmethod
    def set_current_run_id(cls, run_id: str):
        cls._local.run_id = run_id

    @classmethod
    def get_current_span_id(cls) -> Optional[str]:
        return getattr(cls._local, 'span_id', None)

    @classmethod
    def set_current_span_id(cls, span_id: str):
        cls._local.span_id = span_id

    @classmethod
    def get_context(cls) -> Dict:
        return {
            'run_id': cls.get_current_run_id(),
            'parent_span_id': cls.get_current_span_id(),
        }

    @classmethod
    def clear(cls):
        cls._local.run_id = None
        cls._local.span_id = None


# ============================================
# TraceLog - 追踪日志管理器
# ============================================

class TraceLog:
    """
    追踪日志管理器

    实现 execution-trace contract 定义的数据模型。
    负责 spans、artifacts 的记录和查询。
    """

    def __init__(self, project_dir: str, run_id: str = None):
        self.project_dir = Path(project_dir)
        self.traces_dir = self.project_dir / TRACES_DIR
        self.blobs_dir = self.project_dir / BLOBS_DIR
        self.traces_file = self.traces_dir / TRACES_FILE

        self.run_id = run_id or generate_id("RUN")
        self._active_spans: Dict[str, Span] = {}

        # 确保目录存在
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.blobs_dir.mkdir(parents=True, exist_ok=True)

        # 设置 context
        TraceContext.set_current_run_id(self.run_id)

    # ============================================
    # 基础写入
    # ============================================

    def _write_span(self, span: Span):
        """写入 span 到日志文件"""
        with open(self.traces_file, 'a', encoding='utf-8') as f:
            line = json.dumps(span.to_dict(), ensure_ascii=False) + '\n'
            f.write(line)

    def _store_blob(self, content: str) -> str:
        """存储大内容到对象存储"""
        content_hash = compute_hash(content)
        blob_path = self.blobs_dir / f"{content_hash}.blob"
        with open(blob_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"blob://{content_hash}"

    def _create_content_ref(self, data: Any, sanitize_content: bool = True) -> ContentRef:
        """创建内容引用"""
        if data is None:
            return None

        content_str = json.dumps(data, ensure_ascii=False, default=str)
        size_bytes = len(content_str.encode('utf-8'))
        content_hash = compute_hash(data)

        content_ref = None
        if size_bytes > MAX_INLINE_SIZE:
            content_ref = self._store_blob(content_str)

        return ContentRef(
            hash=content_hash,
            size_bytes=size_bytes,
            content_ref=content_ref,
            sanitized=sanitize_content
        )

    # ============================================
    # Span 生命周期
    # ============================================

    def start_span(self,
                   span_type: SpanType,
                   name: str,
                   parent_span_id: str = None,
                   agent: AgentInfo = None,
                   tool: ToolInfo = None,
                   gate: GateInfo = None,
                   input_data: Any = None,
                   tags: List[str] = None,
                   attributes: Dict = None) -> Span:
        """
        开始一个 span

        这是记录操作开始的核心方法。
        返回的 span_id 用于后续 complete/fail 调用。
        """
        span_id = generate_id("SPAN")

        # 如果没有指定 parent，使用 context 中的当前 span
        if parent_span_id is None:
            parent_span_id = TraceContext.get_current_span_id()

        span = Span(
            span_id=span_id,
            run_id=self.run_id,
            span_type=span_type,
            name=name,
            started_at=datetime.now().isoformat(),
            parent_span_id=parent_span_id,
            agent=agent,
            tool=tool,
            gate=gate,
            tags=tags or [],
            attributes=attributes or {},
        )

        # 创建输入引用
        if input_data is not None:
            span.input = self._create_content_ref(input_data)

        # 记录活跃 span
        self._active_spans[span_id] = span

        # 写入日志 (记录开始)
        self._write_span(span)

        # 更新 context
        TraceContext.set_current_span_id(span_id)

        return span

    def complete_span(self,
                      span_id: str,
                      output_data: Any = None,
                      metrics: Metrics = None,
                      tags: List[str] = None) -> Span:
        """
        完成一个 span

        标记操作成功完成，记录输出和度量。
        支持跨进程/跨会话完成之前启动的 span。
        """
        # 先检查内存中的活跃 spans
        if span_id in self._active_spans:
            span = self._active_spans[span_id]
        else:
            # 尝试从文件加载
            span = self.get_span(span_id)
            if span is None:
                raise ValueError(f"Span {span_id} not found")
            if span.status != SpanStatus.RUNNING:
                raise ValueError(f"Span {span_id} already completed (status: {span.status.value})")
        span.status = SpanStatus.SUCCESS
        span.completed_at = datetime.now().isoformat()

        # 计算耗时
        started = datetime.fromisoformat(span.started_at)
        completed = datetime.fromisoformat(span.completed_at)
        span.duration_ms = int((completed - started).total_seconds() * 1000)

        # 输出引用
        if output_data is not None:
            span.output = self._create_content_ref(output_data)

        # 度量
        if metrics:
            span.metrics = metrics

        # 追加标签
        if tags:
            span.tags.extend(tags)

        # 写入完成记录
        self._write_span(span)

        # 移除活跃 span (如果在内存中)
        if span_id in self._active_spans:
            del self._active_spans[span_id]

        # 恢复 context 到父 span
        TraceContext.set_current_span_id(span.parent_span_id)

        return span

    def fail_span(self,
                  span_id: str,
                  error_code: str,
                  error_message: str,
                  error_stack: str = None,
                  metrics: Metrics = None) -> Span:
        """
        标记 span 失败

        记录错误信息。
        支持跨进程/跨会话完成之前启动的 span。
        """
        # 先检查内存中的活跃 spans
        if span_id in self._active_spans:
            span = self._active_spans[span_id]
        else:
            # 尝试从文件加载
            span = self.get_span(span_id)
            if span is None:
                raise ValueError(f"Span {span_id} not found")
            if span.status != SpanStatus.RUNNING:
                raise ValueError(f"Span {span_id} already completed (status: {span.status.value})")
        span.status = SpanStatus.FAILED
        span.completed_at = datetime.now().isoformat()

        # 计算耗时
        started = datetime.fromisoformat(span.started_at)
        completed = datetime.fromisoformat(span.completed_at)
        span.duration_ms = int((completed - started).total_seconds() * 1000)

        # 错误信息 (脱敏)
        span.error = ErrorInfo(
            code=error_code,
            message=sanitize(error_message),
            stack=sanitize(error_stack) if error_stack else None
        )

        if metrics:
            span.metrics = metrics

        # 写入失败记录
        self._write_span(span)

        # 移除活跃 span (如果在内存中)
        if span_id in self._active_spans:
            del self._active_spans[span_id]

        # 恢复 context
        TraceContext.set_current_span_id(span.parent_span_id)

        return span

    # ============================================
    # 便捷方法
    # ============================================

    @contextmanager
    def span(self,
             span_type: SpanType,
             name: str,
             **kwargs):
        """
        Context manager 形式的 span

        Usage:
            with trace_log.span(SpanType.TOOL, "tool.file_write") as span:
                # do something
                span.output = ...
        """
        span = self.start_span(span_type, name, **kwargs)
        try:
            yield span
            self.complete_span(span.span_id)
        except Exception as e:
            self.fail_span(
                span.span_id,
                error_code=type(e).__name__,
                error_message=str(e)
            )
            raise

    def log_agent_call(self,
                       agent_id: str,
                       agent_name: str = None,
                       model: str = None,
                       input_data: Any = None,
                       parent_span_id: str = None) -> Span:
        """记录 Agent 调用开始"""
        return self.start_span(
            span_type=SpanType.AGENT,
            name=f"agent.{agent_id}",
            parent_span_id=parent_span_id,
            agent=AgentInfo(
                agent_id=agent_id,
                agent_name=agent_name,
                model=model
            ),
            input_data=input_data
        )

    def log_tool_call(self,
                      tool_name: str,
                      tool_type: ToolType,
                      target: str = None,
                      input_data: Any = None,
                      parent_span_id: str = None) -> Span:
        """记录工具调用开始"""
        return self.start_span(
            span_type=SpanType.TOOL,
            name=f"tool.{tool_name}",
            parent_span_id=parent_span_id,
            tool=ToolInfo(
                tool_name=tool_name,
                tool_type=tool_type,
                target=sanitize(target) if target else None
            ),
            input_data=input_data
        )

    def log_gate_trigger(self,
                         gate_id: str,
                         gate_type: str,
                         parent_span_id: str = None) -> Span:
        """记录门禁触发"""
        return self.start_span(
            span_type=SpanType.GATE,
            name=f"gate.{gate_id}",
            parent_span_id=parent_span_id,
            gate=GateInfo(
                gate_id=gate_id,
                gate_type=gate_type
            )
        )

    def log_artifact(self,
                     span_id: str,
                     artifact_type: ArtifactType,
                     path: str,
                     content_hash: str,
                     size_bytes: int = None,
                     metadata: Dict = None) -> Artifact:
        """记录产物"""
        artifact = Artifact(
            artifact_id=generate_id("ART"),
            run_id=self.run_id,
            span_id=span_id,
            artifact_type=artifact_type,
            path=path,
            hash=content_hash,
            size_bytes=size_bytes,
            metadata=metadata or {}
        )

        # 写入到产物文件
        artifacts_file = self.traces_dir / "artifacts.jsonl"
        with open(artifacts_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(artifact.to_dict(), ensure_ascii=False) + '\n')

        return artifact

    # ============================================
    # 查询方法
    # ============================================

    def get_spans(self,
                  span_type: SpanType = None,
                  status: SpanStatus = None,
                  parent_span_id: str = None,
                  limit: int = None) -> List[Span]:
        """查询 spans"""
        if not self.traces_file.exists():
            return []

        spans = []
        seen_ids = set()  # 用于去重 (span 会有 start 和 complete 两条记录)

        with open(self.traces_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)

                # 去重，保留最新状态
                span_id = d['span_id']
                if span_id in seen_ids:
                    # 更新已有 span
                    for i, s in enumerate(spans):
                        if s.span_id == span_id:
                            spans[i] = Span.from_dict(d)
                            break
                    continue
                seen_ids.add(span_id)

                span = Span.from_dict(d)

                # 过滤
                if span_type and span.span_type != span_type:
                    continue
                if status and span.status != status:
                    continue
                if parent_span_id and span.parent_span_id != parent_span_id:
                    continue

                spans.append(span)

                if limit and len(spans) >= limit:
                    break

        return spans

    def get_span(self, span_id: str) -> Optional[Span]:
        """获取单个 span (最新状态)"""
        spans = self.get_spans()
        for span in spans:
            if span.span_id == span_id:
                return span
        return None

    def get_span_children(self, span_id: str) -> List[Span]:
        """获取子 spans"""
        return self.get_spans(parent_span_id=span_id)

    def get_call_tree(self, root_span_id: str = None) -> Dict:
        """获取调用树"""
        spans = self.get_spans()

        # 构建树
        tree = {}
        children_map = {}

        for span in spans:
            tree[span.span_id] = {
                'span': span,
                'children': []
            }
            parent = span.parent_span_id
            if parent:
                if parent not in children_map:
                    children_map[parent] = []
                children_map[parent].append(span.span_id)

        # 链接子节点
        for span_id, child_ids in children_map.items():
            if span_id in tree:
                tree[span_id]['children'] = child_ids

        # 如果指定了根节点，只返回该子树
        if root_span_id and root_span_id in tree:
            return tree[root_span_id]

        # 返回所有根节点 (没有 parent 的)
        roots = {sid: node for sid, node in tree.items()
                 if node['span'].parent_span_id is None}
        return roots

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        spans = self.get_spans()

        stats = {
            'run_id': self.run_id,
            'total_spans': len(spans),
            'by_type': {},
            'by_status': {},
            'total_duration_ms': 0,
            'total_tokens': 0,
            'total_cost_usd': 0.0,
            'error_count': 0,
        }

        for span in spans:
            # 按类型统计
            t = span.span_type.value
            stats['by_type'][t] = stats['by_type'].get(t, 0) + 1

            # 按状态统计
            s = span.status.value
            stats['by_status'][s] = stats['by_status'].get(s, 0) + 1

            # 耗时
            if span.duration_ms:
                stats['total_duration_ms'] += span.duration_ms

            # 度量
            if span.metrics:
                stats['total_tokens'] += span.metrics.tokens_total
                stats['total_cost_usd'] += span.metrics.cost_usd

            # 错误
            if span.error:
                stats['error_count'] += 1

        return stats

    # ============================================
    # 导出
    # ============================================

    def export_yaml(self, output_path: str = None) -> str:
        """导出为 YAML 格式 (人类可读)"""
        import yaml

        spans = self.get_spans()
        stats = self.get_statistics()

        data = {
            'run_id': self.run_id,
            'generated_at': datetime.now().isoformat(),
            'statistics': stats,
            'spans': [s.to_dict() for s in spans]
        }

        if output_path is None:
            output_path = self.traces_dir / f"trace_{self.run_id}.yaml"

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        return str(output_path)

    def export_markdown_report(self, output_path: str = None) -> str:
        """导出 Markdown 报告 (Observer 使用)"""
        spans = self.get_spans()
        stats = self.get_statistics()

        report = f"""# Execution Trace Report

**Run ID**: {self.run_id}
**Generated At**: {datetime.now().isoformat()}

---

## Summary

| Metric | Value |
|--------|-------|
| Total Spans | {stats['total_spans']} |
| Total Duration | {stats['total_duration_ms']}ms |
| Total Tokens | {stats['total_tokens']} |
| Total Cost | ${stats['total_cost_usd']:.4f} |
| Errors | {stats['error_count']} |

### By Type

"""
        for t, count in stats['by_type'].items():
            report += f"- {t}: {count}\n"

        report += "\n### By Status\n\n"
        for s, count in stats['by_status'].items():
            report += f"- {s}: {count}\n"

        report += "\n---\n\n## Timeline\n\n"

        # 按时间排序
        sorted_spans = sorted(spans, key=lambda x: x.started_at)
        for span in sorted_spans:
            status_icon = "✅" if span.status == SpanStatus.SUCCESS else "❌" if span.status == SpanStatus.FAILED else "⏳"
            duration = f"{span.duration_ms}ms" if span.duration_ms else "-"
            report += f"- {status_icon} **{span.name}** ({span.span_type.value}) - {duration}\n"
            if span.error:
                report += f"  - Error: {span.error.message}\n"

        report += "\n---\n\n*Report generated by TraceLog*\n"

        if output_path is None:
            output_path = self.traces_dir / f"report_{self.run_id}.md"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        return str(output_path)
