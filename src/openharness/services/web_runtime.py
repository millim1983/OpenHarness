"""Helpers for one-shot web requests that reuse the internal OpenHarness runtime."""

from __future__ import annotations

import asyncio

from openharness.engine.stream_events import AssistantTextDelta, AssistantTurnComplete, ErrorEvent, StreamEvent
from openharness.ui.runtime import build_runtime, close_runtime, handle_line, start_runtime


async def run_single_prompt(
    *,
    profile_name: str,
    message: str,
    cwd: str,
    system_prompt: str = "",
) -> dict[str, str]:
    """Execute one prompt through the internal runtime without spawning the CLI."""

    async def _noop_permission(tool_name: str, reason: str) -> bool:
        return True

    async def _noop_ask(question: str) -> str:
        return ""

    bundle = await build_runtime(
        prompt=message,
        cwd=cwd,
        active_profile=profile_name,
        system_prompt=system_prompt or None,
        permission_prompt=_noop_permission,
        ask_user_prompt=_noop_ask,
        enforce_max_turns=True,
    )

    collected_text = ""
    error_message: str | None = None

    async def _print_system(message: str) -> None:
        nonlocal error_message
        if message and error_message is None:
            error_message = message

    async def _render_event(event: StreamEvent) -> None:
        nonlocal collected_text, error_message
        if isinstance(event, AssistantTextDelta):
            collected_text += event.text
            return
        if isinstance(event, AssistantTurnComplete) and not collected_text.strip():
            collected_text = event.message.text.strip()
            return
        if isinstance(event, ErrorEvent):
            error_message = event.message

    async def _clear_output() -> None:
        return None

    await start_runtime(bundle)
    try:
        await handle_line(
            bundle,
            message,
            print_system=_print_system,
            render_event=_render_event,
            clear_output=_clear_output,
        )
    finally:
        await close_runtime(bundle)

    if error_message:
        raise RuntimeError(error_message)

    answer = collected_text.strip()
    if not answer:
        raise RuntimeError("OpenHarness returned no output.")

    return {
        "profile": profile_name,
        "answer": answer,
    }


def run_single_prompt_sync(
    *, profile_name: str, message: str, cwd: str, system_prompt: str = ""
) -> dict[str, str]:
    """Synchronous wrapper for the threaded web MVP server."""

    return asyncio.run(
        run_single_prompt(
            profile_name=profile_name,
            message=message,
            cwd=cwd,
            system_prompt=system_prompt,
        )
    )
