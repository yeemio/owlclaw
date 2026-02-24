"""Unit tests for owlclaw.integrations.langfuse (integrations-langfuse Tasks 1-4)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.integrations.langfuse import (
    LangfuseClient,
    LangfuseConfig,
    LLMSpanData,
    PrivacyMasker,
    TokenCalculator,
    ToolSpanData,
    TraceContext,
    TraceMetadata,
    load_langfuse_config,
    validate_config,
)


@dataclass
class _FakeObservation:
    id: str


class _FakeLangfuseSDK:
    def __init__(self) -> None:
        self.created_traces: list[dict[str, Any]] = []
        self.ended_traces: list[dict[str, Any]] = []
        self.generations: list[dict[str, Any]] = []
        self.spans: list[dict[str, Any]] = []
        self.flush_count = 0

    def trace(self, **kwargs: Any) -> _FakeObservation | None:
        if "id" in kwargs:
            self.ended_traces.append(kwargs)
            return None
        self.created_traces.append(kwargs)
        return _FakeObservation(id=f"trace-{len(self.created_traces)}")

    def generation(self, **kwargs: Any) -> _FakeObservation:
        self.generations.append(kwargs)
        return _FakeObservation(id=f"gen-{len(self.generations)}")

    def span(self, **kwargs: Any) -> _FakeObservation:
        self.spans.append(kwargs)
        return _FakeObservation(id=f"span-{len(self.spans)}")

    def flush(self) -> None:
        self.flush_count += 1


class TestLangfuseClient:
    def test_init_with_injected_client(self) -> None:
        sdk = _FakeLangfuseSDK()
        client = LangfuseClient(LangfuseConfig(enabled=True, client=sdk))
        assert client.enabled is True

    def test_init_missing_credentials_disables_client(self) -> None:
        client = LangfuseClient(LangfuseConfig(enabled=True, public_key="", secret_key=""))
        assert client.enabled is False

    def test_create_and_end_trace(self) -> None:
        sdk = _FakeLangfuseSDK()
        client = LangfuseClient(LangfuseConfig(enabled=True, client=sdk, sampling_rate=1.0))
        trace_id = client.create_trace(
            name="agent_run",
            metadata=TraceMetadata(agent_id="a1", run_id="r1", trigger_type="cron"),
            tags=["prod"],
        )
        assert trace_id == "trace-1"
        assert sdk.created_traces[0]["name"] == "agent_run"
        client.end_trace(trace_id, output={"ok": True}, metadata={"cost": 1.2})
        assert sdk.ended_traces[0]["id"] == "trace-1"

    @settings(max_examples=100, deadline=None)
    @given(
        sampling_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        rand_value=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_sampling_rate_obeyed(self, sampling_rate: float, rand_value: float) -> None:
        sdk = _FakeLangfuseSDK()
        original_random = random.random
        random.random = lambda: rand_value
        client = LangfuseClient(LangfuseConfig(enabled=True, client=sdk, sampling_rate=sampling_rate))
        try:
            assert client._should_sample() is (rand_value < sampling_rate)
        finally:
            random.random = original_random

    @settings(max_examples=100, deadline=None)
    @given(
        agent_id=st.from_regex(r"[a-z][a-z0-9_-]{0,12}", fullmatch=True),
        run_id=st.from_regex(r"[a-z][a-z0-9_-]{0,12}", fullmatch=True),
        trigger=st.sampled_from(["cron", "webhook", "signal"]),
        focus=st.none() | st.from_regex(r"[a-z][a-z0-9_-]{0,12}", fullmatch=True),
    )
    def test_property_trace_create_content_integrity(
        self,
        agent_id: str,
        run_id: str,
        trigger: str,
        focus: str | None,
    ) -> None:
        sdk = _FakeLangfuseSDK()
        client = LangfuseClient(LangfuseConfig(enabled=True, client=sdk, sampling_rate=1.0))
        trace_id = client.create_trace(
            name="agent_run",
            metadata=TraceMetadata(
                agent_id=agent_id,
                run_id=run_id,
                trigger_type=trigger,
                focus=focus,
            ),
        )
        assert trace_id
        payload = sdk.created_traces[-1]
        assert payload["metadata"]["agent_id"] == agent_id
        assert payload["metadata"]["run_id"] == run_id
        assert payload["metadata"]["trigger_type"] == trigger
        assert payload["metadata"]["focus"] == focus

    def test_create_llm_and_tool_spans(self) -> None:
        sdk = _FakeLangfuseSDK()
        client = LangfuseClient(LangfuseConfig(enabled=True, client=sdk, sampling_rate=1.0))
        llm_span_id = client.create_llm_span(
            trace_id="trace-1",
            span_name="llm_call",
            data=LLMSpanData(
                model="gpt-4o-mini",
                prompt=[{"role": "user", "content": "hello"}],
                response="world",
                prompt_tokens=10,
                completion_tokens=8,
                total_tokens=18,
                cost_usd=0.0001,
                latency_ms=120.0,
                status="success",
            ),
        )
        tool_span_id = client.create_tool_span(
            trace_id="trace-1",
            span_name="tool_call",
            data=ToolSpanData(
                tool_name="query_state",
                arguments={"name": "x"},
                result={"value": 1},
                duration_ms=20.0,
                status="success",
            ),
        )
        assert llm_span_id == "gen-1"
        assert tool_span_id == "span-1"
        assert sdk.generations[0]["usage"]["total_tokens"] == 18
        assert sdk.spans[0]["input"]["tool_name"] == "query_state"


class TestConfigAndHelpers:
    @settings(max_examples=100, deadline=None)
    @given(
        sampling=st.floats(min_value=-2, max_value=2, allow_nan=False, allow_infinity=False),
        batch=st.integers(min_value=-5, max_value=20),
        flush=st.integers(min_value=-5, max_value=20),
    )
    def test_property_config_validation(self, sampling: float, batch: int, flush: int) -> None:
        cfg = LangfuseConfig(
            enabled=True,
            public_key="pk",
            secret_key="sk",
            sampling_rate=sampling,
            batch_size=batch,
            flush_interval_seconds=flush,
        )
        errors = validate_config(cfg)
        assert ("sampling_rate must be between 0 and 1" in errors) is not (0 <= sampling <= 1)
        assert ("batch_size must be positive" in errors) is not (batch > 0)
        assert ("flush_interval_seconds must be positive" in errors) is not (flush > 0)

    def test_load_config_with_env_substitution(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LANGFUSE_PK", "pk-x")
        monkeypatch.setenv("LANGFUSE_SK", "sk-x")
        config_file = tmp_path / "langfuse.yaml"
        config_file.write_text(
            "langfuse:\n  enabled: true\n  public_key: ${LANGFUSE_PK}\n  secret_key: ${LANGFUSE_SK}\n",
            encoding="utf-8",
        )
        cfg = load_langfuse_config(config_file)
        assert cfg.enabled is True
        assert cfg.public_key == "pk-x"
        assert cfg.secret_key == "sk-x"

    @settings(max_examples=100, deadline=None)
    @given(
        prompt=st.integers(min_value=0, max_value=100000),
        completion=st.integers(min_value=0, max_value=100000),
        model=st.sampled_from(["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "claude-3-opus"]),
    )
    def test_property_cost_calculation(self, prompt: int, completion: int, model: str) -> None:
        cost = TokenCalculator.calculate_cost(model, prompt, completion)
        assert cost >= 0.0
        assert isinstance(cost, float)

    @settings(max_examples=100, deadline=None)
    @given(
        prompt=st.integers(min_value=0, max_value=100000),
        completion=st.integers(min_value=0, max_value=100000),
    )
    def test_property_token_extract(self, prompt: int, completion: int) -> None:
        total = prompt + completion
        response = {"usage": {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": total}}
        parsed = TokenCalculator.extract_tokens_from_response(response)
        assert parsed == (prompt, completion, total)

    @settings(max_examples=100, deadline=None)
    @given(
        email=st.from_regex(r"[A-Za-z0-9][A-Za-z0-9._%+-]{0,20}@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", fullmatch=True),
        phone=st.from_regex(r"\d{3}-\d{3}-\d{4}", fullmatch=True),
    )
    def test_property_privacy_masking(self, email: str, phone: str) -> None:
        text = f"contact {email} or {phone}"
        cfg = LangfuseConfig(mask_inputs=True)
        masked = PrivacyMasker.mask(text, cfg)
        assert email not in masked
        assert phone not in masked

    def test_trace_context_roundtrip(self) -> None:
        ctx = TraceContext(trace_id="trace-1", parent_span_id="span-1", metadata={"x": 1})
        TraceContext.set_current(ctx)
        current = TraceContext.get_current()
        assert current is not None
        assert current.trace_id == "trace-1"
        child = current.with_parent_span("span-2")
        assert child.parent_span_id == "span-2"
