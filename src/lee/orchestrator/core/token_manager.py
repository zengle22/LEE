"""
Token Manager - Step Token 令牌管理

核心功能：
1. 为每个步骤签发短期有效令牌
2. 验证令牌有效性
3. 控制工具调用权限
4. 令牌与产物绑定
"""

import json
import hashlib
import hmac
import secrets
import base64
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from .path_policy import WORKFLOW_SUBDIRS


@dataclass
class StepToken:
    """步骤令牌"""
    token_id: str
    run_id: str
    step_id: str
    agent_id: str
    issued_at: str
    expires_at: str
    permissions: List[str]  # 允许的工具/操作
    requires_approval: Optional[str] = None  # 依赖的审批 ID
    inputs_hash: Optional[str] = None
    signature: Optional[str] = None
    revoked: bool = False
    revoked_at: Optional[str] = None
    revoke_reason: Optional[str] = None


class TokenManager:
    """令牌管理器"""

    TOKENS_DIR = WORKFLOW_SUBDIRS["tokens"]
    SECRET_FILE = WORKFLOW_SUBDIRS["tokens"] + "/.secret"
    DEFAULT_VALIDITY_HOURS = 4

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.tokens_dir = self.project_dir / self.TOKENS_DIR
        self.secret_file = self.project_dir / self.SECRET_FILE
        self._secret: Optional[bytes] = None

    def _get_secret(self) -> bytes:
        """获取或生成密钥"""
        if self._secret is None:
            self.secret_file.parent.mkdir(parents=True, exist_ok=True)
            if self.secret_file.exists():
                self._secret = self.secret_file.read_bytes()
            else:
                self._secret = secrets.token_bytes(32)
                self.secret_file.write_bytes(self._secret)
                # 设置文件权限 (仅 owner 可读写)
                # self.secret_file.chmod(0o600)  # Windows 不支持
        return self._secret

    def _generate_token_id(self) -> str:
        """生成令牌 ID"""
        return f"TKN-{secrets.token_hex(8).upper()}"

    def _sign_token(self, token: StepToken) -> str:
        """签名令牌"""
        data = f"{token.token_id}:{token.run_id}:{token.step_id}:{token.expires_at}"
        signature = hmac.new(
            self._get_secret(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _verify_signature(self, token: StepToken) -> bool:
        """验证签名"""
        expected = self._sign_token(token)
        return hmac.compare_digest(token.signature or "", expected)

    def issue_token(self,
                    run_id: str,
                    step_id: str,
                    agent_id: str,
                    permissions: List[str] = None,
                    requires_approval: str = None,
                    inputs_hash: str = None,
                    validity_hours: int = None) -> StepToken:
        """签发步骤令牌"""
        self.tokens_dir.mkdir(parents=True, exist_ok=True)

        if validity_hours is None:
            validity_hours = self.DEFAULT_VALIDITY_HOURS

        if permissions is None:
            permissions = ["read", "write", "execute"]

        now = datetime.now()
        expires = now + timedelta(hours=validity_hours)

        token = StepToken(
            token_id=self._generate_token_id(),
            run_id=run_id,
            step_id=step_id,
            agent_id=agent_id,
            issued_at=now.isoformat(),
            expires_at=expires.isoformat(),
            permissions=permissions,
            requires_approval=requires_approval,
            inputs_hash=inputs_hash
        )

        # 签名
        token.signature = self._sign_token(token)

        # 保存
        token_path = self.tokens_dir / f"{token.token_id}.json"
        with open(token_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(token), f, indent=2)

        return token

    def load_token(self, token_id: str) -> Optional[StepToken]:
        """加载令牌"""
        token_path = self.tokens_dir / f"{token_id}.json"
        if not token_path.exists():
            return None

        with open(token_path, encoding='utf-8') as f:
            data = json.load(f)

        return StepToken(**data)

    def validate_token(self,
                       token_id: str,
                       step_id: str = None,
                       required_permission: str = None,
                       approval_path: str = None) -> Tuple[bool, Optional[str]]:
        """
        验证令牌

        返回: (是否有效, 失败原因)
        """
        token = self.load_token(token_id)

        if token is None:
            return False, "Token not found"

        # 检查是否已撤销
        if token.revoked:
            return False, "Token has been revoked"

        # 验证签名
        if not self._verify_signature(token):
            return False, "Invalid token signature"

        # 检查过期
        expires = datetime.fromisoformat(token.expires_at)
        if datetime.now() > expires:
            return False, "Token has expired"

        # 检查步骤匹配
        if step_id and token.step_id != step_id:
            return False, f"Token is for step {token.step_id}, not {step_id}"

        # 检查权限
        if required_permission and required_permission not in token.permissions:
            return False, f"Token does not have permission: {required_permission}"

        # 检查审批依赖
        if token.requires_approval:
            if not approval_path:
                approval_path = self.project_dir / ".workflow" / "approvals" / f"{token.requires_approval}.json"
            else:
                approval_path = Path(approval_path)

            if not approval_path.exists():
                return False, f"Required approval not found: {token.requires_approval}"

        return True, None

    def revoke_token(self, token_id: str, reason: str = None) -> bool:
        """撤销令牌"""
        token = self.load_token(token_id)
        if token is None:
            return False

        token.revoked = True

        token_path = self.tokens_dir / f"{token_id}.json"
        with open(token_path, 'w', encoding='utf-8') as f:
            data = asdict(token)
            data["revoked_at"] = datetime.now().isoformat()
            data["revoke_reason"] = reason
            json.dump(data, f, indent=2)

        return True

    def get_active_tokens(self, step_id: str = None) -> List[StepToken]:
        """获取活跃的令牌"""
        if not self.tokens_dir.exists():
            return []

        active = []
        now = datetime.now()

        for token_path in self.tokens_dir.glob("TKN-*.json"):
            with open(token_path, encoding='utf-8') as f:
                data = json.load(f)

            token = StepToken(**data)

            # 过滤已撤销和已过期的
            if token.revoked:
                continue
            if datetime.fromisoformat(token.expires_at) < now:
                continue

            # 按步骤过滤
            if step_id and token.step_id != step_id:
                continue

            active.append(token)

        return active

    def cleanup_expired(self) -> int:
        """清理过期令牌"""
        if not self.tokens_dir.exists():
            return 0

        count = 0
        now = datetime.now()
        archive_dir = self.tokens_dir / "expired"
        archive_dir.mkdir(exist_ok=True)

        for token_path in self.tokens_dir.glob("TKN-*.json"):
            with open(token_path, encoding='utf-8') as f:
                data = json.load(f)

            expires = datetime.fromisoformat(data["expires_at"])
            if expires < now:
                # 移动到归档目录
                token_path.rename(archive_dir / token_path.name)
                count += 1

        return count

    def encode_token_for_context(self, token: StepToken) -> str:
        """
        将令牌编码为可以注入到 LLM 上下文的格式

        这个字符串可以被 LLM 提取并在工具调用时携带
        """
        data = {
            "t": token.token_id,
            "s": token.step_id,
            "e": token.expires_at,
            "p": token.permissions
        }
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        return f"WORKFLOW_TOKEN:{encoded}"

    def decode_token_from_context(self, encoded: str) -> Optional[str]:
        """从上下文中解码令牌 ID"""
        if not encoded.startswith("WORKFLOW_TOKEN:"):
            return None

        try:
            b64 = encoded.replace("WORKFLOW_TOKEN:", "")
            data = json.loads(base64.b64decode(b64).decode())
            return data.get("t")
        except:
            return None


class ToolGuard:
    """
    工具调用守卫

    用于在工具调用前验证令牌权限
    """

    # 工具权限映射
    TOOL_PERMISSIONS = {
        # 读取类
        "read": ["Read", "Glob", "Grep", "WebFetch", "WebSearch"],
        # 写入类
        "write": ["Write", "Edit", "NotebookEdit"],
        # 执行类
        "execute": ["Bash", "Task"],
        # 危险操作
        "deploy": ["Bash:deploy", "Bash:kubectl", "Bash:docker"],
        "commit": ["Bash:git commit", "Bash:git push"],
    }

    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager

    def check_tool_access(self,
                          token_id: str,
                          tool_name: str,
                          step_id: str = None) -> Tuple[bool, Optional[str]]:
        """
        检查工具访问权限

        返回: (是否允许, 拒绝原因)
        """
        # 确定需要的权限
        required_permission = None
        for perm, tools in self.TOOL_PERMISSIONS.items():
            if tool_name in tools:
                required_permission = perm
                break

        if required_permission is None:
            required_permission = "read"  # 默认只需要读权限

        # 验证令牌
        valid, reason = self.token_manager.validate_token(
            token_id,
            step_id=step_id,
            required_permission=required_permission
        )

        return valid, reason

    def get_allowed_tools(self, token_id: str) -> List[str]:
        """获取令牌允许的工具列表"""
        token = self.token_manager.load_token(token_id)
        if token is None:
            return []

        allowed = []
        for perm in token.permissions:
            if perm in self.TOOL_PERMISSIONS:
                allowed.extend(self.TOOL_PERMISSIONS[perm])

        return list(set(allowed))
