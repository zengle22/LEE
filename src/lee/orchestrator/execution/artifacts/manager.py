"""
Artifact Manager

产出物管理器 - 提供创建、adopt、freeze 等核心操作。
"""

import hashlib
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
import re
import yaml

from .models import ArtifactMetadata, RunManifest
from .metadata_inheritance import MetadataInheritanceEngine
from .placement import resolve_ssot_relative_dir
from .registry import ArtifactRegistry
from .types import ArtifactType, ArtifactStatus, AdoptMode, GovernanceKind, ArtifactCategoryRegistry, SSOTType
from .id_generator import SSOTIDGenerator

# Windows 兼容性：fcntl 不可用
if sys.platform != "win32":
    import fcntl

# 最大文件大小限制 (100 MB)
MAX_ARTIFACT_SIZE_BYTES = 100 * 1024 * 1024


class ArtifactManager:
    """
    产出物管理器

    提供产出物的创建、adopt、freeze 等核心操作。
    所有产出物必须通过此类进入系统。
    """

    def __init__(self, root_path: Optional[Path] = None, project_root: Optional[Path] = None):
        """
        初始化管理器

        Args:
            root_path: .artifacts/ 根目录
            project_root: 项目根目录
        """
        inferred_root = Path(root_path).resolve() if root_path else None
        default_project_root = inferred_root.parent if inferred_root and inferred_root.name == ".artifacts" else Path.cwd()
        self.project_root = Path(project_root or default_project_root).resolve()
        self.root_path = Path(root_path or (self.project_root / ".artifacts")).resolve()
        self.sequence_file = self.root_path / ".sequence"
        self._artifacts_path_root = self._to_metadata_path_root(self.root_path)
        self.registry = ArtifactRegistry(self.root_path, self.project_root)

        # 确保目录存在
        self._ensure_directories()

        # 加载注册表
        if self.registry.registry_file.exists():
            self.registry.load()
        else:
            self.registry.rebuild()

    def _to_metadata_path_root(self, base_path: Path) -> str:
        """
        Convert a concrete base path into the serialized path_root form.
        """
        resolved = base_path.resolve()
        try:
            relative_to_cwd = resolved.relative_to(Path.cwd())
            return relative_to_cwd.as_posix()
        except ValueError:
            return str(resolved)

    def _resolve_path_root(self, path_root: str) -> Path:
        """Resolve a metadata path_root against the manager project root."""
        base_path = Path(path_root or ".artifacts")
        if not base_path.is_absolute():
            base_path = Path.cwd() / base_path
        return base_path.resolve()

    def _resolve_metadata_path(self, metadata: ArtifactMetadata) -> Path:
        """Resolve a metadata record to an absolute file path."""
        return self._resolve_path_root(metadata.path_root) / metadata.path

    def _is_artifacts_storage(self, metadata: ArtifactMetadata) -> bool:
        """Whether the artifact content is stored under the artifacts root."""
        return self._resolve_path_root(metadata.path_root) == self.root_path.resolve()

    def _ensure_directories(self) -> None:
        """确保目录结构存在"""
        for dir_name in ["active", "frozen", "archive", "logs", "cache"]:
            (self.root_path / dir_name).mkdir(parents=True, exist_ok=True)

    def _validate_path(self, path: Path) -> bool:
        """
        验证路径安全性，防止路径遍历攻击

        Args:
            path: 要验证的路径

        Returns:
            路径是否安全
        """
        # 转换为绝对路径
        try:
            abs_path = path.resolve()
            # 确保路径在 artifacts_root 之内
            abs_root = self.root_path.resolve()
            abs_path.is_relative_to(abs_root)
            try:
                abs_path.relative_to(abs_root)
                return True
            except ValueError:
                return False
        except (OSError, RuntimeError):
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除危险字符

        Args:
            filename: 原始文件名

        Returns:
            安全的文件名
        """
        # 移除路径遍历字符
        dangerous = {"..", "~", "\x00"}
        for part in dangerous:
            filename = filename.replace(part, "")
        # 只保留安全字符
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
        return "".join(c if c in safe_chars else "_" for c in filename)

    def _generate_id(self) -> str:
        """
        生成唯一的产出物 ID

        使用 sequence 文件 + file lock 保证并发安全。

        Returns:
            格式为 ART-xxxxx 的 ID
        """
        # 获取文件锁 (确保父目录存在)
        lock_file = self.sequence_file.with_suffix(".lock")
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = open(lock_file, "w")

        try:
            # Windows 不支持 fcntl 锁，跳过
            if sys.platform != "win32":
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)

            # 读取当前序号
            if self.sequence_file.exists():
                sequence = int(self.sequence_file.read_text().strip())
            else:
                sequence = 0

            # 递增
            sequence += 1

            # 写回
            self.sequence_file.write_text(str(sequence))

            return f"ART-{sequence:05d}"
        finally:
            # Windows 不支持 fcntl 锁，跳过
            if sys.platform != "win32":
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()

    def create(
        self,
        artifact_type: ArtifactType,
        category: str,
        content: Union[str, bytes, Path],
        run_id: str,
        title: str = "",
        description: str = "",
        department: Optional[str] = None,
        workflow_id: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
        derived_from: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: ArtifactStatus = ArtifactStatus.ACTIVE,
        properties: Optional[Dict] = None,
        # v1.0 新增参数
        governance_kind: Optional[GovernanceKind] = None,
        implements: Optional[List[str]] = None,
        verifies: Optional[List[str]] = None,
        supersedes: Optional[str] = None,
    ) -> ArtifactMetadata:
        """
        创建新的产出物

        Args:
            artifact_type: 产出物类型
            category: 产出物类别
            content: 产出物内容 (字符串、字节或文件路径)
            run_id: 所属 run ID
            title: 标题
            description: 描述
            department: 所属部门
            workflow_id: 所属 workflow ID
            depends_on: 依赖的产出物 ID 列表
            derived_from: 派生自哪个产出物
            tags: 标签列表
            status: 初始状态
            properties: 扩展属性
            governance_kind: 治理类别 (v1.0 新增)
            implements: 实现哪些契约 (v1.0 新增)
            verifies: 验证哪些契约 (v1.0 新增)
            supersedes: 替代哪个旧真理 (v1.0 新增)

        Returns:
            创建的 ArtifactMetadata 对象
        """
        # 验证类别
        if not ArtifactCategoryRegistry.is_valid_category(artifact_type.value, category):
            raise ValueError(
                f"Invalid category '{category}' for type '{artifact_type.value}'"
            )

        # 生成 ID
        artifact_id = self._generate_id()

        # 计算目标路径
        if department:
            # 清理 department 名称，防止路径遍历
            safe_department = self._sanitize_filename(department)
            artifact_dir = self.root_path / "active" / safe_department / run_id
        else:
            artifact_dir = self.root_path / "active" / run_id

        artifact_dir.mkdir(parents=True, exist_ok=True)

        # 验证目标路径安全性
        if not self._validate_path(artifact_dir):
            raise ValueError(f"Invalid artifact path: {artifact_dir}")

        # 确定文件扩展名
        ext = self._get_extension_for_category(category)
        artifact_path = artifact_dir / f"{artifact_id}{ext}"

        # 写入内容
        if isinstance(content, (str, bytes)):
            if isinstance(content, str):
                content_bytes = content.encode("utf-8")
            else:
                content_bytes = content
            # 检查大小限制
            if len(content_bytes) > MAX_ARTIFACT_SIZE_BYTES:
                raise ValueError(
                    f"Content size ({len(content_bytes)} bytes) exceeds "
                    f"maximum allowed size ({MAX_ARTIFACT_SIZE_BYTES} bytes)"
                )
            artifact_path.write_bytes(content_bytes)
        elif isinstance(content, Path):
            # 验证源路径并检查大小
            source_path = Path(content)
            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")
            source_size = source_path.stat().st_size
            if source_size > MAX_ARTIFACT_SIZE_BYTES:
                raise ValueError(
                    f"Source file size ({source_size} bytes) exceeds "
                    f"maximum allowed size ({MAX_ARTIFACT_SIZE_BYTES} bytes)"
                )
            shutil.copy2(content, artifact_path)
        else:
            raise TypeError(f"Unsupported content type: {type(content)}")

        # 计算哈希
        content_hash = self._compute_hash(artifact_path)

        # 构建相对路径
        relative_path = artifact_path.relative_to(self.root_path)

        # 创建元数据
        now = datetime.now()
        metadata = ArtifactMetadata(
            id=artifact_id,
            type=artifact_type,
            category=category,
            status=status,
            path=str(relative_path),
            path_root=self._artifacts_path_root,
            external_path=None,
            adopt_mode=None,
            run_id=run_id,
            workflow_id=workflow_id,
            department=department,
            depends_on=depends_on or [],
            derived_from=derived_from,
            implements=implements or [],
            verifies=verifies or [],
            supersedes=supersedes,
            governance_kind=governance_kind or GovernanceKind.TRANSFER,
            title=title,
            description=description,
            tags=tags or [],
            size_bytes=artifact_path.stat().st_size,
            content_hash=content_hash,
            created_at=now,
            updated_at=now,
            properties=properties or {},
        )

        # 注册到注册表
        self.registry.register(metadata)

        return metadata

    def adopt(
        self,
        external_path: Union[str, Path],
        run_id: str,
        artifact_type: ArtifactType,
        category: str,
        mode: Optional[AdoptMode] = None,
        title: str = "",
        description: str = "",
        department: Optional[str] = None,
        workflow_id: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
        derived_from: Optional[str] = None,
        tags: Optional[List[str]] = None,
        properties: Optional[Dict] = None,
        # v1.0 新增参数
        governance_kind: Optional[GovernanceKind] = None,
        implements: Optional[List[str]] = None,
        verifies: Optional[List[str]] = None,
        supersedes: Optional[str] = None,
    ) -> ArtifactMetadata:
        """
        Adopt 外部文件到产出物系统

        支持两种模式:
        - copy_mode: 复制文件内容到 .artifacts/
        - reference_mode: 仅保存 git 引用 (SHA + path)

        Args:
            external_path: 外部文件路径
            run_id: 所属 run ID
            artifact_type: 产出物类型
            category: 产出物类别
            mode: adopt 模式 (None 则自动推断)
            title: 标题
            description: 描述
            department: 所属部门
            workflow_id: 所属 workflow ID
            depends_on: 依赖的产出物 ID 列表
            derived_from: 派生自哪个产出物
            tags: 标签列表
            properties: 扩展属性
            governance_kind: 治理类别 (v1.0 新增)
            implements: 实现哪些契约 (v1.0 新增)
            verifies: 验证哪些契约 (v1.0 新增)
            supersedes: 替代哪个旧真理 (v1.0 新增)

        Returns:
            创建的 ArtifactMetadata 对象
        """
        external_path = Path(external_path)

        if not external_path.exists():
            raise FileNotFoundError(f"External file not found: {external_path}")

        # 自动推断模式
        if mode is None:
            mode = self._infer_adopt_mode(artifact_type, category)

        # 生成 ID
        artifact_id = self._generate_id()

        now = datetime.now()

        if mode == AdoptMode.COPY:
            # copy_mode: 复制文件
            return self._adopt_copy(
                artifact_id=artifact_id,
                external_path=external_path,
                run_id=run_id,
                artifact_type=artifact_type,
                category=category,
                title=title,
                description=description,
                department=department,
                workflow_id=workflow_id,
                depends_on=depends_on,
                derived_from=derived_from,
                tags=tags,
                properties=properties,
                governance_kind=governance_kind,
                implements=implements,
                verifies=verifies,
                supersedes=supersedes,
                now=now,
            )
        else:
            # reference_mode: git 引用
            return self._adopt_reference(
                artifact_id=artifact_id,
                external_path=external_path,
                run_id=run_id,
                artifact_type=artifact_type,
                category=category,
                title=title,
                description=description,
                department=department,
                workflow_id=workflow_id,
                depends_on=depends_on,
                derived_from=derived_from,
                tags=tags,
                properties=properties,
                governance_kind=governance_kind,
                implements=implements,
                verifies=verifies,
                supersedes=supersedes,
                now=now,
            )

    def _adopt_copy(
        self,
        artifact_id: str,
        external_path: Path,
        run_id: str,
        artifact_type: ArtifactType,
        category: str,
        title: str,
        description: str,
        department: Optional[str],
        workflow_id: Optional[str],
        depends_on: Optional[List[str]],
        derived_from: Optional[str],
        tags: Optional[List[str]],
        properties: Optional[Dict],
        now: datetime,
        governance_kind: Optional[GovernanceKind] = None,
        implements: Optional[List[str]] = None,
        verifies: Optional[List[str]] = None,
        supersedes: Optional[str] = None,
    ) -> ArtifactMetadata:
        """copy_mode adopt 实现"""

        # 计算目标路径
        if department:
            artifact_dir = self.root_path / "active" / department / run_id
        else:
            artifact_dir = self.root_path / "active" / run_id

        artifact_dir.mkdir(parents=True, exist_ok=True)

        ext = self._get_extension_for_category(category)
        artifact_path = artifact_dir / f"{artifact_id}{ext}"

        # 复制文件
        shutil.copy2(external_path, artifact_path)

        # 计算哈希
        content_hash = self._compute_hash(artifact_path)

        # 构建相对路径
        relative_path = artifact_path.relative_to(self.root_path)

        metadata = ArtifactMetadata(
            id=artifact_id,
            type=artifact_type,
            category=category,
            status=ArtifactStatus.ACTIVE,
            path=str(relative_path),
            path_root=self._artifacts_path_root,
            external_path=str(external_path),
            adopt_mode=AdoptMode.COPY,
            run_id=run_id,
            workflow_id=workflow_id,
            department=department,
            depends_on=depends_on or [],
            derived_from=derived_from,
            implements=implements or [],
            verifies=verifies or [],
            supersedes=supersedes,
            governance_kind=governance_kind or GovernanceKind.TRANSFER,
            title=title or external_path.stem,
            description=description,
            tags=tags or [],
            size_bytes=artifact_path.stat().st_size,
            content_hash=content_hash,
            created_at=now,
            updated_at=now,
            properties=properties or {},
        )

        self.registry.register(metadata)
        return metadata

    def _adopt_reference(
        self,
        artifact_id: str,
        external_path: Path,
        run_id: str,
        artifact_type: ArtifactType,
        category: str,
        title: str,
        description: str,
        department: Optional[str],
        workflow_id: Optional[str],
        depends_on: Optional[List[str]],
        derived_from: Optional[str],
        tags: Optional[List[str]],
        properties: Optional[Dict],
        now: datetime,
        governance_kind: Optional[GovernanceKind] = None,
        implements: Optional[List[str]] = None,
        verifies: Optional[List[str]] = None,
        supersedes: Optional[str] = None,
    ) -> ArtifactMetadata:
        """reference_mode adopt 实现"""

        # 获取 git SHA
        git_sha, git_repo_path = self._get_git_info(external_path)

        if git_sha is None:
            raise ValueError(
                f"Cannot get git SHA for {external_path}, "
                "reference_mode requires file to be in a git repository"
            )

        # 计算虚拟路径 (不实际复制文件)
        if department:
            virtual_dir = f"active/{department}/{run_id}"
        else:
            virtual_dir = f"active/{run_id}"

        ext = self._get_extension_for_category(category)
        virtual_path = f"{virtual_dir}/{artifact_id}{ext}"

        metadata = ArtifactMetadata(
            id=artifact_id,
            type=artifact_type,
            category=category,
            status=ArtifactStatus.ACTIVE,
            path=virtual_path,
            path_root=self._artifacts_path_root,
            external_path=str(external_path),
            adopt_mode=AdoptMode.REFERENCE,
            run_id=run_id,
            workflow_id=workflow_id,
            department=department,
            depends_on=depends_on or [],
            derived_from=derived_from,
            implements=implements or [],
            verifies=verifies or [],
            supersedes=supersedes,
            governance_kind=governance_kind or GovernanceKind.TRANSFER,
            title=title or external_path.stem,
            description=description,
            tags=tags or [],
            git_sha=git_sha,
            git_repo_path=git_repo_path,
            created_at=now,
            updated_at=now,
            properties=properties or {},
        )

        self.registry.register(metadata)
        return metadata

    def _infer_adopt_mode(self, artifact_type: ArtifactType, category: str) -> AdoptMode:
        """推断 adopt 模式"""
        # CODE_REF 和 PATCH 默认使用 reference_mode
        if artifact_type in (ArtifactType.CODE_REF, ArtifactType.PATCH):
            return AdoptMode.REFERENCE
        return AdoptMode.COPY

    def _get_extension_for_category(self, category: str) -> str:
        """根据类别获取文件扩展名"""
        extensions = {
            # CONTRACT
            "frozen_prd": ".md",
            "api_contract": ".json",
            "test_plan": ".md",
            "design_doc": ".md",
            # DOCUMENT
            "readme": ".md",
            "usage_guide": ".md",
            "investigation_report": ".md",
            "handover_doc": ".md",
            # CODE_REF
            "implementation": ".py",
            "config": ".yaml",
            "script": ".sh",
            # PATCH
            "feature_patch": ".patch",
            "bugfix_patch": ".patch",
            "refactor_patch": ".patch",
            # TEST
            "test_report": ".md",
            "test_case": ".py",
            "coverage_report": ".txt",
            # HANDOVER
            "to_qa": ".md",
            "to_backend": ".md",
            "to_frontend": ".md",
            "to_devops": ".md",
            # LOG
            "execution_log": ".log",
            "error_log": ".log",
            "debug_log": ".log",
            # INTERMEDIATE
            "draft": ".tmp",
            "temp": ".tmp",
            "scratch": ".tmp",
        }
        return extensions.get(category, ".bin")

    def _compute_hash(self, file_path: Path) -> str:
        """计算文件 SHA256 哈希"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _get_git_info(self, file_path: Path) -> tuple[Optional[str], Optional[str]]:
        """
        获取文件的 git SHA 和 repo 路径

        Returns:
            (git_sha, git_repo_relative_path)
        """
        try:
            # 找到 git 根目录
            git_root = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=file_path.parent,
                capture_output=True,
                text=True,
                timeout=30,  # 30 秒超时
            )

            if git_root.returncode != 0:
                return None, None

            repo_path = Path(git_root.stdout.strip())

            # 获取文件 SHA
            git_sha = subprocess.run(
                ["git", "ls-files", "-s", str(file_path)],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,  # 30 秒超时
            )

            if git_sha.returncode != 0:
                return None, None

            # 解析输出: 100644 <sha> 0   <path>
            parts = git_sha.stdout.strip().split()
            if len(parts) >= 2:
                sha = parts[1]
                # 计算相对路径
                try:
                    rel_path = Path.cwd().relative_to(repo_path)
                    return sha, str(rel_path) if rel_path != Path(".") else None
                except ValueError:
                    return sha, None

            return None, None
        except Exception:
            return None, None

    def get(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """获取产出物元数据"""
        return self.registry.get(artifact_id)

    def get_content(self, artifact_id: str) -> Optional[Union[str, bytes]]:
        """获取产出物内容"""
        metadata = self.get(artifact_id)
        if not metadata:
            return None

        if metadata.adopt_mode == AdoptMode.REFERENCE:
            # reference_mode: 从 git 获取
            return self._get_git_content(metadata)
        else:
            # copy_mode: 从文件读取
            path = self._resolve_metadata_path(metadata)
            if not path.exists():
                return None
            content = path.read_bytes()
            # 尝试解码为文本
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content

    def _get_git_content(self, metadata: ArtifactMetadata) -> Optional[str]:
        """从 git 获取内容 (reference_mode)"""
        if not metadata.git_sha:
            return None

        try:
            repo_path = Path.cwd() / (metadata.git_repo_path or ".")
            result = subprocess.run(
                ["git", "show", metadata.git_sha],
                cwd=repo_path,
                capture_output=True,
                timeout=60,  # 60 秒超时 (大文件可能需要更长时间)
            )

            if result.returncode == 0:
                return result.stdout.decode("utf-8")
        except Exception:
            pass

        return None

    def delete(self, artifact_id: str, force: bool = False) -> bool:
        """
        删除产出物

        Args:
            artifact_id: 产出物 ID
            force: 强制删除 (跳过引用保护)

        Returns:
            是否成功删除
        """
        metadata = self.get(artifact_id)
        if not metadata:
            return False

        # 引用保护检查
        if not force:
            references = self.registry.find_references_to(artifact_id)
            if references:
                raise RuntimeError(
                    f"Cannot delete {artifact_id}: still referenced by {len(references)} artifacts"
                )

        # 删除文件
        if metadata.adopt_mode != AdoptMode.REFERENCE:
            file_path = self._resolve_metadata_path(metadata)
            if file_path.exists():
                file_path.unlink()

        # 从注册表移除
        self.registry._remove_from_index(artifact_id)
        self.registry._save()

        return True

    def freeze(self, artifact_id: str) -> ArtifactMetadata:
        """
        冻结产出物

        将产出物移动到 frozen/ 目录，状态变为 FROZEN。
        """
        metadata = self.get(artifact_id)
        if not metadata:
            raise KeyError(f"Artifact {artifact_id} not found")

        if metadata.status == ArtifactStatus.FROZEN:
            return metadata

        if metadata.adopt_mode == AdoptMode.REFERENCE or not self._is_artifacts_storage(metadata):
            self._update_project_ssot_front_matter_status(metadata, ArtifactStatus.FROZEN)
            metadata.status = ArtifactStatus.FROZEN
            metadata.frozen_at = datetime.now()
            metadata.updated_at = datetime.now()
            self.registry.update(metadata)
            return metadata

        # copy_mode: 移动文件到 frozen/
        old_path = self._resolve_metadata_path(metadata)
        frozen_dir = self.root_path / "frozen"
        frozen_path = frozen_dir / Path(metadata.path).name

        # 移动文件
        frozen_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(frozen_path))

        # 更新元数据
        metadata.path = f"frozen/{frozen_path.name}"
        metadata.status = ArtifactStatus.FROZEN
        metadata.frozen_at = datetime.now()
        metadata.updated_at = datetime.now()

        self.registry.update(metadata)
        return metadata

    def _update_project_ssot_front_matter_status(
        self,
        metadata: ArtifactMetadata,
        status: ArtifactStatus,
    ) -> None:
        artifact_path = self._resolve_metadata_path(metadata)
        if not artifact_path.exists():
            return
        if artifact_path.suffix.lower() != ".md":
            return
        try:
            raw_text = artifact_path.read_text(encoding="utf-8")
        except OSError:
            return
        if not raw_text.startswith("---\n"):
            return
        match = re.match(r"^---\n(.*?)\n---\n?", raw_text, re.DOTALL)
        if not match:
            return
        try:
            front_matter = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return
        if not isinstance(front_matter, dict):
            return
        front_matter["status"] = status.value.lower()
        frozen_at = datetime.now().isoformat()
        front_matter["frozen_at"] = frozen_at
        body = raw_text[match.end():]
        front_matter_yaml = yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False).strip()
        artifact_path.write_text(f"---\n{front_matter_yaml}\n---\n{body}", encoding="utf-8")

    def create_ssot(
        self,
        ssot_type,
        title: str,
        content,
        run_id: str,
        formal_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        derived_from: Optional[List[Union[str, Dict]]] = None,
        source_refs: Optional[List[str]] = None,
        related_ids: Optional[List[str]] = None,
        verifies: Optional[List[str]] = None,
        implements: Optional[List[str]] = None,
        owner: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: ArtifactStatus = ArtifactStatus.ACTIVE,
        version: str = "v1",
        properties: Optional[Dict] = None,
    ) -> ArtifactMetadata:
        """
        创建 SSOT 对象 (v1.3 新增)

        使用新的 SSOT ID 格式和文件命名规则。

        Args:
            ssot_type: SSOT 对象类型
            title: 标题
            content: 内容
            run_id: 所属 run ID
            parent_id: 父对象 ID
            derived_from: 派生来源
            source_refs: 源文档锚点
            related_ids: 横向关联
            verifies: 验证哪些对象
            implements: 实现哪些对象
            owner: 负责人
            tags: 标签
            status: 状态
            version: 版本
            properties: 扩展属性

        Returns:
            创建的 ArtifactMetadata 对象
        """
        if not isinstance(ssot_type, SSOTType):
            ssot_type = SSOTType(ssot_type)

        inheritance = MetadataInheritanceEngine(self.get).normalize(
            ssot_type=ssot_type,
            formal_id=formal_id,
            parent_id=parent_id,
            source_refs=source_refs,
            derived_from_ids=derived_from,
            version=version,
        )
        parent_id = inheritance.parent_id
        source_refs = inheritance.source_refs
        derived_from = inheritance.derived_from_ids

        # 生成 ID
        generator = SSOTIDGenerator(self.root_path)

        # 生成 slug
        slug = generator.generate_slug(title)

        # 生成完整 ID
        generation_suffix = None
        if ssot_type == SSOTType.RELEASE:
            generation_suffix = (properties or {}).get("release_version")
            if not generation_suffix:
                raise ValueError("RELEASE create_ssot 需要 properties.release_version 作为 semver")
        elif ssot_type == SSOTType.REPORT and parent_id and str(parent_id).startswith("REL-"):
            generation_suffix = (properties or {}).get("report_kind")

        artifact_id = (formal_id or "").strip() or generator.generate_id(
            ssot_type,
            parent_id,
            generation_suffix,
        )

        # 生成文件名
        filename = f"{artifact_id}__{slug}.md"

        # 正式 SSOT 主文件落在项目内容目录，而不是 .artifacts/ssot/
        relative_dir = resolve_ssot_relative_dir(ssot_type, parent_id=parent_id)
        artifact_dir = self.project_root / relative_dir
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_dir / filename
        existing_metadata = self.registry.get(artifact_id) if self.registry.exists(artifact_id) else None
        self._cleanup_existing_ssot_paths(
            artifact_id=artifact_id,
            artifact_dir=artifact_dir,
            target_path=artifact_path,
            existing_metadata=existing_metadata,
        )

        derived_from_ids = derived_from or []
        front_matter = {
            "id": artifact_id,
            "ssot_type": ssot_type.value,
            "title": title,
            "status": status.value.lower(),
            "version": version,
            "workflow_instance_id": run_id,
            "parent_id": parent_id,
            "derived_from_ids": derived_from_ids,
            "source_refs": source_refs or [],
            "owner": owner,
            "tags": tags or [],
            "properties": properties or {},
        }

        # 写入内容
        if isinstance(content, Path):
            raw_body = content.read_text(encoding="utf-8")
        else:
            raw_body = content.decode("utf-8") if isinstance(content, bytes) else str(content)

        if raw_body.startswith("---"):
            match = re.match(r"^---\n(.*?)\n---\n?", raw_body, re.DOTALL)
            if match:
                try:
                    existing_front_matter = yaml.safe_load(match.group(1)) or {}
                except yaml.YAMLError:
                    existing_front_matter = {}
                if not isinstance(existing_front_matter, dict):
                    existing_front_matter = {}
                body = raw_body[match.end():].lstrip("\r\n")
                merged_front_matter = dict(existing_front_matter)
                merged_front_matter.update(front_matter)
                front_matter_yaml = yaml.safe_dump(
                    merged_front_matter,
                    allow_unicode=True,
                    sort_keys=False,
                ).strip()
                file_text = f"---\n{front_matter_yaml}\n---\n\n{body}"
            else:
                front_matter_yaml = yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False).strip()
                file_text = f"---\n{front_matter_yaml}\n---\n\n{raw_body}"
        else:
            front_matter_yaml = yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False).strip()
            file_text = f"---\n{front_matter_yaml}\n---\n\n{raw_body}"

        artifact_path.write_text(file_text, encoding="utf-8")
        content_hash = self._compute_hash(artifact_path)
        size_bytes = artifact_path.stat().st_size

        # 创建 metadata
        metadata = ArtifactMetadata(
            id=artifact_id,
            type=ArtifactType.DOCUMENT,  # 暂用 DOCUMENT 类型
            category="ssot_object",
            status=status,
            path=artifact_path.relative_to(self.project_root).as_posix(),
            path_root=self._to_metadata_path_root(self.project_root),
            run_id=run_id,
            title=title,
            derived_from=next(
                (
                    item.get("id")
                    for item in derived_from_ids
                    if isinstance(item, dict) and item.get("id")
                ),
                next((item for item in derived_from_ids if isinstance(item, str)), None),
            ),
            verifies=verifies or [],
            implements=implements or [],
            tags=tags or [],
            size_bytes=size_bytes,
            content_hash=content_hash,
            properties=properties or {},
        )

        # 添加 SSOT 扩展字段 (作为 properties 存储)
        metadata.properties["ssot_type"] = ssot_type.value
        metadata.properties["parent_id"] = parent_id
        metadata.properties["source_refs"] = source_refs or []
        metadata.properties["related_ids"] = related_ids or []
        metadata.properties["owner"] = owner
        metadata.properties["version"] = version
        metadata.properties["placement_dir"] = relative_dir.as_posix()
        metadata.properties["derived_from_ids"] = derived_from_ids
        metadata.properties["workflow_instance_id"] = run_id

        # 注册/更新
        if existing_metadata is not None:
            self.registry.update(metadata)
        else:
            self.registry.register(metadata)

        return metadata

    def _cleanup_existing_ssot_paths(
        self,
        artifact_id: str,
        artifact_dir: Path,
        target_path: Path,
        existing_metadata: Optional[ArtifactMetadata] = None,
    ) -> None:
        """
        Remove stale checked-in SSOT files for the same formal ID before writing.

        Reruns may regenerate the same SSOT with a different title/slug. The formal
        ID must remain a single checked-in file, so we delete sibling variants first.
        """
        existing_paths = set(artifact_dir.glob(f"{artifact_id}__*.md"))
        if existing_metadata is not None:
            existing_path = self._resolve_metadata_path(existing_metadata)
            if existing_path.exists():
                existing_paths.add(existing_path)

        for existing_path in existing_paths:
            if existing_path.resolve() == target_path.resolve():
                continue
            if existing_path.exists():
                existing_path.unlink()

    def get_ssot(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """
        获取 SSOT 对象

        Args:
            artifact_id: SSOT ID

        Returns:
            ArtifactMetadata 或 None
        """
        if not self.registry.is_ssot_id(artifact_id):
            return None
        return self.registry.get(artifact_id)

    def list_ssot_by_type(self, ssot_type: SSOTType) -> List[ArtifactMetadata]:
        """
        列出指定类型的所有 SSOT 对象

        Args:
            ssot_type: SSOT 对象类型

        Returns:
            ArtifactMetadata 列表
        """
        return [
            a for a in self.registry.get_ssot_artifacts()
            if a.properties.get("ssot_type") == ssot_type.value
        ]

    def list_ssot_by_parent(self, parent_id: str) -> List[ArtifactMetadata]:
        """
        列出指定父对象的所有子对象

        Args:
            parent_id: 父对象 ID

        Returns:
            ArtifactMetadata 列表
        """
        return self.registry.get_by_parent(parent_id)

    def rebuild_ssot_registry(self) -> int:
        """从正式 SSOT 文件全量重建 registry。"""
        self.registry.rebuild()
        return len(self.registry.list_all())

    def sync_ssot_registry(self) -> int:
        """增量同步入口，当前先复用全量重建。"""
        return self.rebuild_ssot_registry()
