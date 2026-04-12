from __future__ import annotations

import pytest

from openharness.engine.stream_events import AssistantTextDelta
from openharness.services.web_runtime import run_single_prompt


@pytest.mark.asyncio
async def test_run_single_prompt_collects_internal_runtime_output(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = object()
    captured: dict[str, object] = {}

    async def fake_build_runtime(**kwargs):
        captured.update(kwargs)
        return bundle

    async def fake_start_runtime(runtime_bundle: object) -> None:
        assert runtime_bundle is bundle

    async def fake_handle_line(runtime_bundle: object, line: str, **kwargs) -> bool:
        assert runtime_bundle is bundle
        assert line == "Summarize this"
        await kwargs["render_event"](AssistantTextDelta(text="hello "))
        await kwargs["render_event"](AssistantTextDelta(text="world"))
        return True

    async def fake_close_runtime(runtime_bundle: object) -> None:
        assert runtime_bundle is bundle

    monkeypatch.setattr("openharness.services.web_runtime.build_runtime", fake_build_runtime)
    monkeypatch.setattr("openharness.services.web_runtime.start_runtime", fake_start_runtime)
    monkeypatch.setattr("openharness.services.web_runtime.handle_line", fake_handle_line)
    monkeypatch.setattr("openharness.services.web_runtime.close_runtime", fake_close_runtime)

    result = await run_single_prompt(
        profile_name="gemini-compatible",
        message="Summarize this",
        cwd="/tmp/project",
    )

    assert result == {
        "profile": "gemini-compatible",
        "answer": "hello world",
    }
    assert captured["active_profile"] == "gemini-compatible"
    assert captured["cwd"] == "/tmp/project"


@pytest.mark.asyncio
async def test_run_single_prompt_raises_on_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = object()

    async def fake_build_runtime(**kwargs):
        return bundle

    async def fake_start_runtime(runtime_bundle: object) -> None:
        assert runtime_bundle is bundle

    async def fake_handle_line(runtime_bundle: object, line: str, **kwargs) -> bool:
        await kwargs["print_system"]("profile failed")
        return True

    async def fake_close_runtime(runtime_bundle: object) -> None:
        assert runtime_bundle is bundle

    monkeypatch.setattr("openharness.services.web_runtime.build_runtime", fake_build_runtime)
    monkeypatch.setattr("openharness.services.web_runtime.start_runtime", fake_start_runtime)
    monkeypatch.setattr("openharness.services.web_runtime.handle_line", fake_handle_line)
    monkeypatch.setattr("openharness.services.web_runtime.close_runtime", fake_close_runtime)

    with pytest.raises(RuntimeError, match="profile failed"):
        await run_single_prompt(
            profile_name="openai-compatible",
            message="Summarize this",
            cwd="/tmp/project",
        )
