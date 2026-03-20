"""
SSOT ID Generator

SSOT ID 生成器 - 提供 ID 生成、Slug 生成功能。

ID 生成规则 (v1.5):
- 独立顺序型: SRC, ADR - 全局序号
- SRC 作用域独立型: EPIC, FEAT
- Release 型: REL-<semver>
- 单父唯一型: TECH, TESTSET, DEVPLAN, TESTPLAN
- 单父多实例型: UI, TASK
- 时态/运行型: REPORT - 带 kind/序号或日期
- 范围归属型: TC, BUG, EVI - ID 体现 FEAT 范围
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .types import SSOTType, ObjectCategory
from .placement import resolve_ssot_relative_dir, resolve_src_root_id


class SSOTIDGenerator:
    """
    SSOT ID 生成器

    提供 ID 生成、Slug 生成功能，支持 12 种对象类型。
    """

    # 序号文件名前缀
    SEQUENCE_FILE_PREFIX = ".ssot_seq_"

    def __init__(self, root_path: Optional[Path] = None):
        """
        初始化生成器

        Args:
            root_path: .artifacts/ 根目录
        """
        self.root_path = root_path or (Path.cwd() / ".artifacts")

        # 内存缓存：type -> 当前最大序号
        self._sequences: Dict[str, int] = {}

        # 加载已有序号
        self._load_sequences()

    def _get_sequence_file(self, ssot_type: SSOTType) -> Path:
        """获取类型对应的序号文件"""
        return self.root_path / f"{self.SEQUENCE_FILE_PREFIX}{ssot_type.value}"

    def _resolve_project_root(self) -> Path:
        """Resolve the project root used for filesystem scans."""
        if self.root_path.name == ".artifacts":
            return self.root_path.parent
        return self.root_path

    def _load_sequences(self) -> None:
        """从文件加载序号"""
        for ssot_type in SSOTType:
            existing_seq = self._scan_existing_sequence(ssot_type)
            seq_file = self._get_sequence_file(ssot_type)
            if seq_file.exists():
                try:
                    seq = int(seq_file.read_text().strip())
                    self._sequences[ssot_type.value] = max(seq, existing_seq)
                except (ValueError, IOError):
                    self._sequences[ssot_type.value] = existing_seq
            else:
                self._sequences[ssot_type.value] = existing_seq

    def _scan_existing_sequence(self, ssot_type: SSOTType) -> int:
        """扫描正式 SSOT 文件，推断当前已占用的最大独立序号。"""
        if ssot_type not in (SSOTType.SRC, SSOTType.ADR) or ssot_type == SSOTType.RELEASE:
            return 0

        project_root = self._resolve_project_root()
        target_dir = project_root / resolve_ssot_relative_dir(ssot_type)
        if not target_dir.exists():
            return 0

        prefix = f"{ssot_type.value.upper()}-"
        max_seq = 0
        for path in target_dir.rglob(f"{prefix}*__*.md"):
            object_id = path.name.split("__", 1)[0]
            match = re.fullmatch(rf"{prefix}(\d+)", object_id)
            if match:
                max_seq = max(max_seq, int(match.group(1)))
        return max_seq

    def _scan_scoped_sequence(self, ssot_type: SSOTType, src_root_id: str) -> int:
        """扫描指定 SRC 作用域内的正式序号。"""
        project_root = self._resolve_project_root()
        target_dir = project_root / resolve_ssot_relative_dir(ssot_type, source_refs=[src_root_id], properties={"src_root_id": src_root_id})
        if not target_dir.exists():
            return 0

        prefix = f"{ssot_type.value.upper()}-{src_root_id}-"
        max_seq = 0
        for path in target_dir.rglob(f"{ssot_type.value.upper()}-*__*.md"):
            object_id = path.name.split("__", 1)[0]
            match = re.fullmatch(rf"{ssot_type.value.upper()}-{re.escape(src_root_id)}-(\d+)", object_id)
            if match:
                max_seq = max(max_seq, int(match.group(1)))
        return max_seq

    def _save_sequence(self, ssot_type: SSOTType) -> None:
        """保存序号到文件"""
        seq_file = self._get_sequence_file(ssot_type)
        seq_file.parent.mkdir(parents=True, exist_ok=True)
        seq_file.write_text(str(self._sequences.get(ssot_type.value, 0)))

    def get_next_sequence(self, ssot_type: SSOTType, parent_scope: Optional[str] = None) -> int:
        """
        获取下一个序号

        对于独立顺序型，返回全局序号。
        对于其他类型，返回基于 parent_scope 的序号。

        Args:
            ssot_type: 对象类型
            parent_scope: 父对象范围 (如 FEAT-001)

        Returns:
            下一个序号
        """
        # 构建缓存 key
        if parent_scope:
            cache_key = f"{ssot_type.value}_{parent_scope}"
        else:
            cache_key = ssot_type.value

        if parent_scope and cache_key not in self._sequences:
            seq_file = self.root_path / "sequences" / parent_scope / f"{ssot_type.value}.seq"
            if seq_file.exists():
                try:
                    self._sequences[cache_key] = int(seq_file.read_text().strip())
                except (ValueError, IOError):
                    self._sequences[cache_key] = 0

        # 获取当前序号
        current = self._sequences.get(cache_key, 0)
        current += 1

        # 更新缓存
        self._sequences[cache_key] = current

        # 保存到文件
        if parent_scope:
            # 对于有 parent 的类型，序号文件放在 parent 目录下
            parent_dir = self.root_path / "sequences" / parent_scope
            parent_dir.mkdir(parents=True, exist_ok=True)
            seq_file = parent_dir / f"{ssot_type.value}.seq"
            seq_file.write_text(str(current))
        else:
            self._save_sequence(ssot_type)

        return current

    def _get_next_scoped_sequence(self, ssot_type: SSOTType, scope: str) -> int:
        cache_key = f"{ssot_type.value}_{scope}"
        if cache_key not in self._sequences:
            self._sequences[cache_key] = self._scan_scoped_sequence(ssot_type, scope)

        current = self._sequences.get(cache_key, 0) + 1
        self._sequences[cache_key] = current

        parent_dir = self.root_path / "sequences" / scope
        parent_dir.mkdir(parents=True, exist_ok=True)
        seq_file = parent_dir / f"{ssot_type.value}.seq"
        seq_file.write_text(str(current))
        return current

    def generate_id(
        self,
        ssot_type: SSOTType,
        parent_id: Optional[str] = None,
        suffix: Optional[str] = None,
        src_root_id: Optional[str] = None,
    ) -> str:
        """
        生成 SSOT ID

        Args:
            ssot_type: 对象类型
            parent_id: 父对象 ID (可选)
            suffix: 后缀 (可选，如 FE, 01 等)

        Returns:
            生成的 ID，如 FEAT-001, TC-FEAT-001-001
        """
        category = ObjectCategory.for_type(ssot_type)

        if ssot_type == SSOTType.RELEASE:
            if not suffix:
                raise ValueError("类型 release 需要 suffix 作为 semver，例如 1.4.0")
            return f"REL-{suffix}"

        if category == ObjectCategory.INDEPENDENT:
            if ssot_type in (SSOTType.SRC, SSOTType.ADR):
                seq = self.get_next_sequence(ssot_type)
                return f"{ssot_type.value.upper()}-{seq:03d}"

            src_scope = src_root_id or resolve_src_root_id(parent_id=parent_id)
            if src_scope:
                seq = self._get_next_scoped_sequence(ssot_type, src_scope)
                return f"{ssot_type.value.upper()}-{src_scope}-{seq:03d}"

            # 回退到旧版独立序号格式（不带 SRC 作用域）
            seq = self.get_next_sequence(ssot_type)
            return f"{ssot_type.value.upper()}-{seq:03d}"

        elif category == ObjectCategory.DIRECT_PARENT:
            # 直接父对象一致型
            if not parent_id:
                raise ValueError(f"类型 {ssot_type.value} 需要 parent_id")

            if ssot_type == SSOTType.TASK and parent_id.startswith(("DEVPLAN-", "TESTPLAN-")):
                task_scope = parent_id
                if suffix:
                    return f"TASK-{task_scope}-{suffix}"
                seq = self.get_next_sequence(ssot_type, task_scope)
                return f"TASK-{task_scope}-{seq:03d}"

            if ssot_type == SSOTType.REPORT and parent_id.startswith("REL-"):
                report_kind = (suffix or "GEN").upper()
                seq = self.get_next_sequence(ssot_type, f"{parent_id}_{report_kind}")
                return f"REPORT-{parent_id}-{report_kind}-{seq:03d}"

            parent_scope = self._extract_scope(parent_id)
            if not parent_scope:
                raise ValueError(f"无法从 parent_id {parent_id} 提取范围")

            if ssot_type in (SSOTType.DEVPLAN, SSOTType.TESTPLAN):
                return f"{ssot_type.value.upper()}-{parent_scope}"

            if ssot_type in (SSOTType.TECH, SSOTType.TESTSET):
                if suffix:
                    return f"{ssot_type.value.upper()}-{parent_scope}-{suffix}"
                return f"{ssot_type.value.upper()}-{parent_scope}"

            if ssot_type == SSOTType.REPORT:
                return self.generate_report_id(parent_scope)

            if suffix:
                return f"{ssot_type.value.upper()}-{parent_scope}-{suffix}"

            seq = self.get_next_sequence(ssot_type)
            return f"{ssot_type.value.upper()}-{parent_scope}-{seq:03d}"

        elif category == ObjectCategory.SCOPE_BOUNDED:
            # 范围归属型
            if not parent_id:
                raise ValueError(f"类型 {ssot_type.value} 需要 parent_id")

            # 解析 parent_id 获取范围
            parent_scope = self._extract_scope(parent_id)
            if not parent_scope:
                raise ValueError(f"无法从 parent_id {parent_id} 提取范围")

            seq = self.get_next_sequence(ssot_type, parent_scope)

            # 范围归属型使用 3 位序号
            return f"{ssot_type.value.upper()}-{parent_scope}-{seq:03d}"

        else:
            raise ValueError(f"未知类型分类: {ssot_type}")

    def _extract_scope(self, parent_id: str) -> Optional[str]:
        """
        从 parent_id 提取范围 (FEAT-XXX 或 REL-x.y.z)

        Args:
            parent_id: 父对象 ID

        Returns:
            范围，如 FEAT-001 或 REL-1.4.0
        """
        parts = parent_id.split("-")

        if len(parts) < 2:
            return None

        # 如果 parent_id 已经是 FEAT-XXX 或 REL-x.y.z 格式
        if parts[0].upper() == "FEAT":
            if len(parts) >= 4 and parts[1].upper() == "SRC":
                return "-".join(parts[:4])
            if len(parts) >= 2:
                return parent_id
        if parts[0].upper() == "REL":
            return parent_id

        if parts[0].upper() in ("DEVPLAN", "TESTPLAN") and len(parts) >= 5 and parts[1].upper() == "REL":
            return "-".join(parts[1:5])

        if (
            parts[0].upper() == "TASK"
            and len(parts) >= 6
            and parts[1].upper() in ("DEVPLAN", "TESTPLAN")
            and parts[2].upper() == "REL"
        ):
            return "-".join(parts[1:5])

        if parts[0].upper() == "REPORT" and len(parts) >= 5 and parts[1].upper() == "REL":
            return "-".join(parts[1:5])

        # 如果 parent_id 是其他类型，尝试提取 FEAT 范围
        if parts[0].upper() in ("TECH", "TESTSET", "UI", "TASK", "REPORT", "TC", "BUG", "EVI"):
            try:
                feat_idx = parts.index("FEAT")
                if feat_idx + 3 < len(parts) and parts[feat_idx + 1].upper() == "SRC":
                    return "-".join(parts[feat_idx:feat_idx + 4])
                if feat_idx + 1 < len(parts) and parts[feat_idx + 1].isdigit():
                    return "-".join(parts[feat_idx:feat_idx + 2])
            except ValueError:
                pass

        return None

    def generate_report_id(
        self,
        parent_id: str,
        date: Optional[datetime] = None,
        kind: Optional[str] = None,
    ) -> str:
        """
        生成 REPORT ID (带日期)

        Args:
            parent_id: 父对象 ID (FEAT 或 REL)
            date: 日期，默认为今天
            kind: release 级 report 的 kind

        Returns:
            生成的 ID，如 REPORT-FEAT-001-20260306
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y%m%d")

        parent_scope = self._extract_scope(parent_id)
        if not parent_scope:
            raise ValueError(f"无法从 parent_id {parent_id} 提取范围")

        if parent_scope.startswith("REL-"):
            report_kind = (kind or "GEN").upper()
            seq = self.get_next_sequence(SSOTType.REPORT, f"{parent_scope}_{report_kind}_{date_str}")
            return f"REPORT-{parent_scope}-{report_kind}-{seq:03d}"

        return f"REPORT-{parent_scope}-{date_str}"

    def generate_slug(
        self,
        title: str,
        explicit_slug: Optional[str] = None
    ) -> str:
        """
        生成 slug

        算法 (固定 7 步):
        1. 若显式提供 slug，使用该 slug；否则从 title 生成
        2. 全量转小写（中文保持不变）
        3. 空白折叠为 -
        4. 非 Unicode 词字符/连字符 替换为 -
        5. 合并连续 - 为单个 -
        6. 去除首尾分隔符
        7. 截断至 50 字符；若为空则回退为 "untitled"

        Args:
            title: 标题
            explicit_slug: 显式 slug (可选)

        Returns:
            生成的 slug
        """
        # 步骤 1
        slug = explicit_slug if explicit_slug else title

        # 步骤 2: 转小写（中文等非大小写字符保持不变）
        slug = slug.lower()

        # 步骤 3: 空白折叠为 -
        slug = re.sub(r"\s+", "-", slug, flags=re.UNICODE)

        # 步骤 4: 保留 Unicode 词字符和连字符，其他替换为 -
        slug = re.sub(r"[^\w-]", "-", slug, flags=re.UNICODE)

        # 步骤 5: 合并连续 -
        slug = re.sub(r"-+", "-", slug)

        # 步骤 6: 去除首尾分隔符
        slug = slug.strip(" .-_")

        # 步骤 7: 截断至 50 字符
        if len(slug) > 50:
            slug = slug[:50]
            slug = slug.rstrip(" .-_")

        # 回退
        if not slug:
            slug = "untitled"

        return slug

    def generate_filename(
        self,
        ssot_type: SSOTType,
        title: str,
        parent_id: Optional[str] = None,
        suffix: Optional[str] = None,
        src_root_id: Optional[str] = None,
        ext: str = "md"
    ) -> str:
        """
        生成完整文件名

        格式: [ID]__[slug].[ext]

        Args:
            ssot_type: 对象类型
            title: 标题
            parent_id: 父对象 ID
            suffix: 后缀
            ext: 文件扩展名

        Returns:
            文件名，如 FEAT-001__generate-plan.md
        """
        # 生成 ID
        artifact_id = self.generate_id(ssot_type, parent_id, suffix, src_root_id=src_root_id)

        # 生成 slug
        slug = self.generate_slug(title)

        return f"{artifact_id}__{slug}.{ext}"


# 全局生成器实例
_default_generator: Optional[SSOTIDGenerator] = None


def get_generator(root_path: Optional[Path] = None) -> SSOTIDGenerator:
    """
    获取全局 ID 生成器实例

    Args:
        root_path: .artifacts/ 根目录

    Returns:
        SSOTIDGenerator 实例
    """
    global _default_generator
    if _default_generator is None:
        _default_generator = SSOTIDGenerator(root_path)
    return _default_generator
