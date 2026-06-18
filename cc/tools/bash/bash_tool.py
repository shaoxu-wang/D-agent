"""BashTool implementation.

Corresponds to TS: tools/BashTool/BashTool.tsx.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shutil
from pathlib import PureWindowsPath
from typing import Any

from cc.tools.base import Tool, ToolResult, ToolSchema

logger = logging.getLogger(__name__)

BASH_TOOL_NAME = "Bash"
# 限制子进程输出大小为 200KB，防止超大输出撑爆内存或上下文窗口
MAX_OUTPUT_BYTES = 200_000  # 200KB output cap
# 默认超时 2 分钟，与 TS 原版行为一致
DEFAULT_TIMEOUT_MS = 120_000  # 2 minutes

# 只读单词命令白名单——这些命令不会修改文件系统状态，
# 因此可以安全地与其他工具并发执行，不会产生竞态条件
_READ_ONLY_SINGLE = frozenset([
    "ls", "cat", "head", "tail", "wc", "du", "df", "file", "stat",
    "which", "whereis", "type", "echo", "printf", "date", "uname",
    "whoami", "id", "env", "printenv", "pwd", "hostname",
])

# 只读双词命令白名单——git 的查询子命令同样不会修改仓库状态，
# 允许并发执行以提升多工具场景下的响应速度
_READ_ONLY_TWO_WORD = frozenset([
    "git status", "git log", "git diff", "git show", "git branch",
    "git remote", "git tag", "git rev-parse", "git describe",
])


def _find_bash_executable() -> str | None:
    """Return a real Bash executable when available on Windows."""
    if os.name != "nt":
        return None

    for candidate in (
        "C:/Program Files/Git/bin/bash.exe",
        "C:/Program Files/Git/usr/bin/bash.exe",
        "D:/Git/bin/bash.exe",
        "D:/Git/usr/bin/bash.exe",
    ):
        if os.path.exists(candidate):
            return candidate

    bash_path = shutil.which("bash")
    if bash_path and "WindowsApps" not in bash_path:
        return bash_path
    return None


def _msys_to_windows_path(path: str) -> str | None:
    """Convert a simple MSYS absolute path to a Windows path."""
    if len(path) >= 3 and path[0] == "/" and path[2] == "/":
        drive = path[1]
        if drive.isalpha():
            return f"{drive.upper()}:\\" + path[3:].replace("/", "\\")
    return None


class BashTool(Tool):
    """Execute shell commands.

    Corresponds to TS: tools/BashTool/BashTool.tsx.
    """

    def __init__(self, cwd: str | None = None) -> None:
        # 工作目录可由调用方指定，用于控制子进程的执行上下文
        self._cwd = cwd

    def get_name(self) -> str:
        return BASH_TOOL_NAME

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=BASH_TOOL_NAME,
            description="Executes a given bash command and returns its output.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute",
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Optional timeout in milliseconds (max 600000)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Clear description of what the command does",
                    },
                },
                "required": ["command"],
            },
        )

    def is_concurrency_safe(self, tool_input: dict[str, Any]) -> bool:
        """Read-only commands are concurrency safe.

        FIX (check.md #2): Check both single-word and two-word command prefixes.

        安全策略：通过解析命令的前一到两个单词，判断是否属于只读命令。
        只有命中白名单的命令才返回 True，允许并发执行。
        写操作命令（如 rm, mv, git commit 等）不在白名单中，
        会返回 False，迫使引擎串行执行以避免竞态。
        """
        command = tool_input.get("command", "").strip()
        words = command.split()
        if not words:
            # 空命令无法判定安全性，保守返回 False
            return False
        # 先检查单词命令（如 ls, cat 等）
        if words[0] in _READ_ONLY_SINGLE:
            return True
        # 再检查双词命令（如 git status, git log 等）
        return len(words) >= 2 and f"{words[0]} {words[1]}" in _READ_ONLY_TWO_WORD

    async def execute(self, tool_input: dict[str, Any]) -> ToolResult:
        command: str = tool_input.get("command", "")
        # 用户可指定超时，但上限硬编码为 600 秒（10 分钟），防止进程长时间挂起
        timeout_ms: int = min(tool_input.get("timeout", DEFAULT_TIMEOUT_MS), 600_000)
        timeout_s = timeout_ms / 1000.0

        if not command.strip():
            return ToolResult(content="Error: empty command", is_error=True)

        try:
            # 使用 shell 模式启动子进程，以便支持管道、重定向等 shell 特性
            bash_path = _find_bash_executable()
            cwd = self._cwd
            if bash_path:
                proc = await asyncio.create_subprocess_exec(
                    bash_path,
                    "-lc",
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                )
            else:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout_s
                )
            except TimeoutError:
                # 超时处理采用两阶段策略：先 SIGTERM 优雅终止，再 SIGKILL 强杀，
                # 因为某些进程需要时间做清理工作（如释放锁文件）
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.communicate(), timeout=2.0)
                except (TimeoutError, ProcessLookupError):
                    # 如果 2 秒内仍未退出，强制杀死进程
                    with contextlib.suppress(ProcessLookupError):
                        proc.kill()
                return ToolResult(
                    content=f"Command timed out after {timeout_ms}ms",
                    is_error=True,
                )

            # 使用 errors="replace" 解码，确保二进制输出不会导致 UnicodeDecodeError
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            if bash_path and os.name == "nt":
                if self._cwd and command.strip() == "pwd":
                    stdout = f"{PureWindowsPath(self._cwd)}\n"
                else:
                    converted_lines = []
                    for line in stdout.splitlines(keepends=True):
                        line_body = line.rstrip("\r\n")
                        suffix = line[len(line_body):]
                        converted = _msys_to_windows_path(line_body)
                        converted_lines.append((converted or line_body) + suffix)
                    stdout = "".join(converted_lines)

            # 合并 stdout 和 stderr；如果 stdout 为空则只显示 stderr
            output = stdout
            if stderr:
                output = f"{stdout}\n{stderr}" if stdout else stderr

            # 输出截断：按字节数限制，用 1/4 估算字符数（因为 UTF-8 字符最多 4 字节）
            if len(output.encode("utf-8")) > MAX_OUTPUT_BYTES:
                truncated = output[:MAX_OUTPUT_BYTES // 4]  # rough char estimate
                output = f"{truncated}\n\n... (output truncated, exceeded {MAX_OUTPUT_BYTES} bytes)"

            # 非零退出码视为错误，附加退出码信息便于模型理解失败原因
            exit_code = proc.returncode or 0
            if exit_code != 0:
                output = f"{output}\n\nExit code: {exit_code}" if output else f"Exit code: {exit_code}"

            return ToolResult(content=output or "(no output)", is_error=exit_code != 0)

        except Exception as e:
            return ToolResult(content=f"Error executing command: {e}", is_error=True)
