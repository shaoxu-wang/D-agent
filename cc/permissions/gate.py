"""Permission gate — minimal tool permission checking.

P2a: Mode-based permission checking with non-interactive semantics.
Corresponds to TS: types/permissions.ts + hooks/toolPermission/.

Key design:
- PermissionMode controls strictness (bypass/acceptEdits/default)
- PermissionContext wraps mode + interactivity for each session
- New/unknown tools default to ASK (whitelist approach)
- Non-interactive contexts (--print, background, teammate) fail-fast on ASK

权限系统的核心设计理念是"白名单"模式：
只有明确列入白名单的工具才能自动执行，其余一律需要用户确认。
这样即使未来新增工具，也不会因为遗漏权限配置而导致意外执行。
"""

from __future__ import annotations

import hashlib
import inspect
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cc.permissions.rules import PermissionRules

logger = logging.getLogger(__name__)

# 只读工具白名单 —— 这些工具不会修改文件系统，在所有模式下都自动允许
READ_ONLY_TOOLS = frozenset({
    "Read", "Glob", "Grep", "TaskGet", "TaskList", "ToolSearch", "Brief",
    "TaskCreate", "TaskUpdate",
})
# 编辑工具集 —— 会修改文件但不执行命令，在 ACCEPT_EDITS 模式下自动允许
EDIT_TOOLS = frozenset({
    "Edit", "Write", "NotebookEdit", "TodoWrite",
})


class PermissionMode(Enum):
    """Tool execution permission modes.

    三级权限模式，严格程度递增：
    - BYPASS: 完全跳过权限检查，所有工具自动允许（危险，仅限受信环境）
    - ACCEPT_EDITS: 读取和编辑操作自动允许，命令执行等需确认（推荐的交互模式）
    - DEFAULT: 仅读取操作自动允许，其余均需确认（最安全的默认模式）
    """
    BYPASS = "bypassPermissions"   # All tools auto-allowed
    ACCEPT_EDITS = "acceptEdits"   # Read + Edit auto-allowed, rest ASK
    DEFAULT = "default"            # Only read auto-allowed, rest ASK


class PermissionDecision(Enum):
    """Result of a permission check.

    ALLOW: 直接执行，无需用户确认
    ASK: 需要询问用户是否允许（交互模式下弹出提示，非交互模式下拒绝）
    DENY: 直接拒绝，不询问用户
    """
    ALLOW = "allow"
    ASK = "ask"
    STRONG_ASK = "strong_ask"
    DENY = "deny"


@dataclass(frozen=True)
class PermissionDecisionRecord:
    """Auditable permission decision for a single tool call."""

    tool_call_id: str
    tool_name: str
    decision: str
    source: str
    allowed: bool
    input_hash: str
    input_summary: str
    prompt_shown: bool = False
    always_allowed: bool = False
    created_at: str = ""


PromptCallback = Callable[[str, dict[str, object]], Awaitable[str] | str]


def check_permission(
    mode: PermissionMode,
    tool_name: str,
    tool_input: dict[str, object] | None = None,
) -> PermissionDecision:
    """Check if a tool should be allowed, denied, or needs user approval.

    Whitelist approach: only explicitly listed tools get ALLOW.
    Everything else defaults to ASK (safe for new/unknown tools).

    判定流程（按优先级）：
    1. BYPASS 模式 → 一律 ALLOW
    2. 只读工具 → ALLOW（所有模式下都安全）
    3. 编辑工具 + ACCEPT_EDITS 模式 → ALLOW
    4. 其余情况（Bash、Agent 等高危工具，或未知新工具）→ ASK
    """
    # BYPASS 模式跳过所有权限检查
    if mode == PermissionMode.BYPASS:
        return PermissionDecision.ALLOW

    # 只读工具在任何模式下都安全执行
    if tool_name in READ_ONLY_TOOLS:
        return PermissionDecision.ALLOW

    # 编辑工具在 ACCEPT_EDITS 模式下自动允许
    if tool_name in EDIT_TOOLS and mode == PermissionMode.ACCEPT_EDITS:
        return PermissionDecision.ALLOW

    # 所有未列入白名单的工具（Bash、Agent、WebFetch 等）→ 需要用户确认
    # 这包括未来可能新增的工具，确保安全默认行为
    return PermissionDecision.ASK


class PermissionContext:
    """Session-scoped permission context.

    Wraps mode + interactivity. Non-interactive contexts (--print,
    background agent, teammate) cannot prompt the user.

    PermissionContext 是每个会话的权限状态容器，封装了：
    - mode: 权限模式（决定自动允许哪些工具）
    - is_interactive: 是否可以向用户提问（非交互模式下 ASK → 拒绝）
    - rules: 自定义规则（优先于模式检查，允许精细控制）
    - _always_allow: 运行时累积的"始终允许"决定（用户选择 "a" 后记住）
    """

    def __init__(
        self,
        mode: PermissionMode = PermissionMode.ACCEPT_EDITS,
        is_interactive: bool = True,
        rules: PermissionRules | None = None,
        prompt_callback: PromptCallback | None = None,
    ) -> None:
        self.mode = mode
        self.is_interactive = is_interactive
        self.rules = rules
        self.prompt_callback = prompt_callback
        # 存储用户选择"always allow"的工具名，避免每次都弹窗确认
        self._always_allow: set[str] = set()

    async def check(
        self,
        tool_name: str,
        tool_input: dict[str, object],
    ) -> bool:
        """Check permission and potentially prompt user.

        Returns True if allowed, False if denied.

        完整判定流程：
        1. 检查 _always_allow 缓存（用户曾选 "a" 的工具直接放行）
        2. 检查自定义规则（rules，P2b 扩展点）
        3. 执行模式检查（check_permission）
        4. 如果结果是 ASK：
           - 非交互模式 → 直接拒绝（fail-fast）
           - 交互模式 → 弹窗询问用户
        """
        record = await self.check_with_record(tool_name, tool_input)
        return record.allowed

    async def check_with_record(
        self,
        tool_name: str,
        tool_input: dict[str, object],
        *,
        tool_call_id: str = "",
    ) -> PermissionDecisionRecord:
        """Check permission and return an auditable decision record."""
        input_hash = _hash_tool_input(tool_input)
        input_summary = _summarize_tool_input(tool_input)
        dsim_risk = _classify_dsim_risk(tool_name, tool_input)

        # P2b: 自定义规则优先于模式检查，deny 规则仍保持最高优先级。
        rules_decision: PermissionDecision | None = None
        if self.rules is not None:
            from cc.permissions.rules import apply_rules

            rules_decision = apply_rules(self.rules, tool_name, tool_input)
            if rules_decision == PermissionDecision.DENY:
                return _decision_record(
                    tool_call_id,
                    tool_name,
                    "deny",
                    "config_deny",
                    False,
                    input_hash,
                    input_summary,
                )

        if dsim_risk == PermissionDecision.STRONG_ASK:
            return await self._prompt_and_record(
                tool_call_id,
                tool_name,
                tool_input,
                PermissionDecision.STRONG_ASK,
                "dsim_risk",
                input_hash,
                input_summary,
                allow_always=False,
            )

        # 已被用户标记为"始终允许"的工具，跳过普通 ASK，但不会绕过 strong_ask。
        if tool_name in self._always_allow:
            return _decision_record(
                tool_call_id,
                tool_name,
                "allow",
                "always_allow",
                True,
                input_hash,
                input_summary,
                always_allowed=True,
            )

        if rules_decision == PermissionDecision.ALLOW:
            return _decision_record(
                tool_call_id,
                tool_name,
                "allow",
                "config_allow",
                True,
                input_hash,
                input_summary,
            )

        if dsim_risk == PermissionDecision.ALLOW:
            return _decision_record(
                tool_call_id,
                tool_name,
                "allow",
                "dsim_risk",
                True,
                input_hash,
                input_summary,
            )

        if dsim_risk == PermissionDecision.ASK:
            return await self._prompt_and_record(
                tool_call_id,
                tool_name,
                tool_input,
                PermissionDecision.ASK,
                "dsim_risk",
                input_hash,
                input_summary,
                allow_always=True,
            )

        # 模式检查：根据 PermissionMode 和工具白名单判定
        decision = check_permission(self.mode, tool_name, tool_input)

        if decision == PermissionDecision.ALLOW:
            return _decision_record(
                tool_call_id,
                tool_name,
                "allow",
                "permission_mode",
                True,
                input_hash,
                input_summary,
            )

        if decision == PermissionDecision.ASK:
            return await self._prompt_and_record(
                tool_call_id,
                tool_name,
                tool_input,
                PermissionDecision.ASK,
                "permission_mode",
                input_hash,
                input_summary,
                allow_always=True,
            )

        # DENY 决定：直接拒绝
        return _decision_record(
            tool_call_id,
            tool_name,
            "deny",
            "permission_mode",
            False,
            input_hash,
            input_summary,
        )

    async def _prompt_and_record(
        self,
        tool_call_id: str,
        tool_name: str,
        tool_input: dict[str, object],
        decision: PermissionDecision,
        source: str,
        input_hash: str,
        input_summary: str,
        *,
        allow_always: bool,
    ) -> PermissionDecisionRecord:
        if not self.is_interactive:
            logger.info("Permission denied (non-interactive): %s", tool_name)
            return _decision_record(
                tool_call_id,
                tool_name,
                decision.value,
                source,
                False,
                input_hash,
                input_summary,
            )

        allowed, always_allowed = await self._prompt_user_decision(
            tool_name,
            tool_input,
            allow_always=allow_always,
        )
        return _decision_record(
            tool_call_id,
            tool_name,
            decision.value,
            source,
            allowed,
            input_hash,
            input_summary,
            prompt_shown=True,
            always_allowed=always_allowed,
        )

    async def _prompt_user(
        self,
        tool_name: str,
        tool_input: dict[str, object],
    ) -> bool:
        """Prompt the user for approval in interactive mode.

        向用户展示工具名和输入摘要，提供三种选择：
        - y/yes: 本次允许
        - n/no: 本次拒绝
        - a/always: 本次允许，且记住该工具后续自动允许（存入 _always_allow）
        """
        allowed, _always_allowed = await self._prompt_user_decision(tool_name, tool_input)
        return allowed

    async def _prompt_user_decision(
        self,
        tool_name: str,
        tool_input: dict[str, object],
        *,
        allow_always: bool = True,
    ) -> tuple[bool, bool]:
        """Prompt the user and return (allowed, stored_as_always_allowed)."""
        if self.prompt_callback is not None:
            response = self.prompt_callback(tool_name, tool_input)
            if inspect.isawaitable(response):
                response = await response
            response_text = str(response).strip().lower()
        else:
            # 截断过长的输入预览，避免刷屏
            from cc.ui.renderer import _shorten_paths, console

            input_preview = _shorten_paths(str(tool_input))
            if len(input_preview) > 200:
                input_preview = input_preview[:200] + "..."

            console.print(f"\n[yellow]Permission required: {tool_name}[/]")
            console.print(f"[dim]{input_preview}[/]")

            try:
                response_text = console.input("[bold]Allow? (y/n/a=always): [/]").strip().lower()
            except (EOFError, KeyboardInterrupt):
                # 用户中断输入时视为拒绝
                return False, False

        if response_text in ("a", "always"):
            # 记住选择，后续同类工具调用不再弹窗
            if allow_always:
                self._always_allow.add(tool_name)
                return True, True
            return True, False
        return response_text in ("y", "yes"), False


def _classify_dsim_risk(
    tool_name: str,
    tool_input: dict[str, object],
) -> PermissionDecision | None:
    from cc.dsim.permissions import DsimRiskClassifier

    classifier = DsimRiskClassifier()
    if not classifier.is_dsim_tool(tool_name):
        return None

    risk = classifier.classify(tool_name, tool_input)
    if risk == "strong_ask":
        return PermissionDecision.STRONG_ASK
    if risk == "ask":
        return PermissionDecision.ASK
    return PermissionDecision.ALLOW


def _hash_tool_input(tool_input: dict[str, object]) -> str:
    try:
        payload = json.dumps(tool_input, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        payload = str(tool_input)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _summarize_tool_input(tool_input: dict[str, object]) -> str:
    summary = ", ".join(f"{key}={value!r}" for key, value in sorted(tool_input.items()))
    if len(summary) > 200:
        return summary[:200] + "..."
    return summary


def _decision_record(
    tool_call_id: str,
    tool_name: str,
    decision: str,
    source: str,
    allowed: bool,
    input_hash: str,
    input_summary: str,
    *,
    prompt_shown: bool = False,
    always_allowed: bool = False,
) -> PermissionDecisionRecord:
    return PermissionDecisionRecord(
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        decision=decision,
        source=source,
        allowed=allowed,
        input_hash=input_hash,
        input_summary=input_summary,
        prompt_shown=prompt_shown,
        always_allowed=always_allowed,
        created_at=datetime.now(UTC).isoformat(),
    )
