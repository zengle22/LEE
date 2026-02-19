"""
LEE Orchestrator — Execution Receipt

执行凭证（Receipt）是每一步骤执行的"收据"，用于保障完整性和可追溯性。
包含：
1. 上下文信息 (run_id, step_id, repo_id)
2. 环境快照 (commit_before, commit_after)
3. 输入输出指纹 (inputs_hash, patch_hash)
4. 执行结果 (exit_code)
5. 完整性校验和 (checksum)

Receipt 存储在 worktree/artifacts 或 run/receipts 目录，并可通过 verify 命令验证。
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ExecutionReceipt:
    """
    执行凭证
    
    关键字段：
    - checksum: 包含除 checksum 外所有字段的 SHA256，防止被篡改
    """
    run_id: str
    step_id: str
    repo_id: str
    
    # 环境状态
    commit_before: str
    commit_after: str
    
    # 指纹
    inputs_hash: str       # SHA256 of input_data
    patch_hash: str        # 来自 PatchBundle
    
    # 结果
    exit_code: int
    timestamp: str         # ISO 8601
    executor_type: str
    
    # 完整性
    checksum: str = ""

    def compute_checksum(self) -> str:
        """计算除 checksum 外所有字段的 SHA256"""
        # 1. 提取所有字段（排除 checksum）
        data = asdict(self)
        data.pop("checksum", None)
        
        # 2. 排序并序列化（保证唯一性）
        canonical_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        
        # 3. 计算 Hash
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def sign(self):
        """计算并填充 checksum"""
        self.checksum = self.compute_checksum()


class ReceiptVerifier:
    """Receipt 验证器"""

    def verify(self, receipt: ExecutionReceipt) -> bool:
        """验证 receipt 的完整性"""
        expected = receipt.compute_checksum()
        return expected == receipt.checksum

    def verify_from_dict(self, data: Dict[str, Any]) -> bool:
        """从 dict 验证"""
        try:
            receipt = ExecutionReceipt(**data)
            return self.verify(receipt)
        except Exception:
            return False


class ReceiptStore:
    """
    Receipt 存储
    
    存储位置：.lee/runs/<run_id>/receipts.jsonl
    """

    def __init__(self, runs_root: str):
        self.runs_root = runs_root

    def save(self, receipt: ExecutionReceipt) -> None:
        """保存 receipt"""
        # Ensure it's signed
        if not receipt.checksum:
            receipt.sign()
            
        run_dir = os.path.join(self.runs_root, receipt.run_id)
        receipt_file = os.path.join(run_dir, "receipts.jsonl")
        
        os.makedirs(run_dir, exist_ok=True)
        
        with open(receipt_file, "a", encoding="utf-8") as f:
            data = asdict(receipt)
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def load_by_run(self, run_id: str) -> List[ExecutionReceipt]:
        """加载 run 的所有 receipts"""
        receipt_file = os.path.join(self.runs_root, run_id, "receipts.jsonl")
        if not os.path.exists(receipt_file):
            return []
            
        receipts = []
        with open(receipt_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    receipts.append(ExecutionReceipt(**data))
                except Exception as e:
                    logger.warning(f"Failed to parse receipt line: {e}")
        return receipts
