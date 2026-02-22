"""
LEE Orchestrator — Patch Output Collector

负责收集和标准化 Git Patch 三件套：
1. changes.patch: 具体的代码变更 diff
2. diff.stat: 变更统计 (files changed, insertions, deletions)
3. git_status.txt: git status --porcelain 输出

这些产物用于：
- Gate 审查 (e.g. 变更行数限制)
- Receipt 签名 (patch_hash)
- 用户审查 (diff 预览)
"""

import hashlib
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

from lee.runtime.worktree_manager import WorktreeManager


@dataclass
class PatchBundle:
    """Patch 三件套产物包"""
    run_id: str
    step_id: str
    repo_id: str
    
    # 文件路径 (绝对路径)
    patch_path: str       # changes.patch
    stat_path: str        # diff.stat
    status_path: str      # git_status.txt
    
    # 元数据
    patch_hash: str       # SHA256 of patch content
    files_changed: int
    insertions: int
    deletions: int
    is_empty: bool        # 是否无变更


class PatchCollector:
    """Patch 收集器"""

    def __init__(self, worktree_manager: WorktreeManager):
        self.mgr = worktree_manager

    def collect(self, run_id: str, step_id: str, repo_id: str) -> PatchBundle:
        """
        收集 Patch 三件套
        
        1. 调用 git diff 生成 patch 和 stat
        2. 调用 git status 生成 status
        3. 写入 artifacts 目录
        4. 计算 hash 和统计信息
        
        Args:
            run_id: 运行 ID
            step_id: 步骤 ID
            repo_id: 仓库 ID
            
        Returns:
            PatchBundle
        """
        # 1. 获取 worktree info
        try:
            # 这里的 get_workdir 会抛出 ValueError 如果未分配，但在 collect 时应该已经分配了
            # 为了获取 artifact_dir，我们需要重新构造 path 或者扩展 WorktreeManager 接口
            # 简单起见，我们重新allocate(幂等)来获取完整 info，或者假设 artifact 目录结构
            # 更好的做法是 WorktreeManager 提供 get_info()
            # 这里先假设 worktree_manager.get_workdir 是可用的，artifact dir 我们自己拼
            workdir = self.mgr.get_workdir(run_id, repo_id)
            # artifacts_dir 约定在 workdir 同级的 artifacts 目录
            # .lee/runs/<run_id>/worktrees/<repo_id>/artifacts
            artifacts_dir = os.path.join(os.path.dirname(workdir), "artifacts")
            if not os.path.exists(artifacts_dir):
                os.makedirs(artifacts_dir, exist_ok=True)
        except ValueError:
            raise RuntimeError(f"No worktree found for run={run_id} repo={repo_id}")

        # 2. 生成文件名
        prefix = f"{step_id}"
        patch_file = os.path.join(artifacts_dir, f"{prefix}.patch")
        stat_file = os.path.join(artifacts_dir, f"{prefix}.stat")
        status_file = os.path.join(artifacts_dir, f"{prefix}.status.txt")

        # 3. 收集内容
        patch_content = self.mgr.export_patch(run_id, repo_id) or ""
        stat_content = self.mgr.get_diff_stat(run_id, repo_id) or ""
        status_content = self.mgr.get_git_status(run_id, repo_id) or ""

        # 4. 写入文件
        with open(patch_file, "w", encoding="utf-8") as f:
            f.write(patch_content)
        with open(stat_file, "w", encoding="utf-8") as f:
            f.write(stat_content)
        with open(status_file, "w", encoding="utf-8") as f:
            f.write(status_content)

        # 5. 计算 Hash 和 Meta
        patch_hash = hashlib.sha256(patch_content.encode("utf-8")).hexdigest()
        files, insertions, deletions = self._parse_diff_stat(stat_content)
        is_empty = (len(patch_content.strip()) == 0)

        return PatchBundle(
            run_id=run_id,
            step_id=step_id,
            repo_id=repo_id,
            patch_path=patch_file,
            stat_path=stat_file,
            status_path=status_file,
            patch_hash=patch_hash,
            files_changed=files,
            insertions=insertions,
            deletions=deletions,
            is_empty=is_empty
        )

    def verify_bundle(self, bundle: PatchBundle) -> bool:
        """
        验证 PatchBundle 的完整性
        
        检查：
        1. 文件是否存在
        2. patch_hash 是否匹配文件内容
        """
        if not os.path.exists(bundle.patch_path):
            return False
            
        try:
            with open(bundle.patch_path, "r", encoding="utf-8") as f:
                content = f.read()
            calculated_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            return calculated_hash == bundle.patch_hash
        except Exception as e:
            logger.debug(
                f"Failed to verify patch hash for {bundle.patch_path}: {e}"
            )
            return False

    def _parse_diff_stat(self, stat_content: str) -> Tuple[int, int, int]:
        """
        解析 diff --stat 输出
        Example: " 2 files changed, 10 insertions(+), 5 deletions(-)"
        """
        if not stat_content:
            return 0, 0, 0
            
        # 取最后一行 summary
        lines = stat_content.strip().split('\n')
        summary = lines[-1].strip()
        
        files = 0
        insertions = 0
        deletions = 0
        
        # Regex parsing
        # 1 file changed, 1 insertion(+)
        # 2 files changed, 3 deletions(-)
        # 3 files changed, 1 insertion(+), 1 deletion(-)
        
        m_files = re.search(r'(\d+)\s+files? changed', summary)
        if m_files:
            files = int(m_files.group(1))
            
        m_insert = re.search(r'(\d+)\s+insertion', summary)
        if m_insert:
            insertions = int(m_insert.group(1))
            
        m_delete = re.search(r'(\d+)\s+deletion', summary)
        if m_delete:
            deletions = int(m_delete.group(1))
            
        return files, insertions, deletions
