"""ネットワーク無しで「SDK に渡す辞書の形」を検証する。

各スクリプトが組み立てるパラメータを、SDK の TypedDict / Pydantic 定義に対して検査する。
API 自体の挙動は保証しないが、キー名の打ち間違い・必須キーの欠落はここで止まる。
実行: python -m pytest tests  （pytest が無ければ python tests/test_params.py）
"""
from __future__ import annotations

import sys
import typing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import TypeAdapter  # anthropic が依存しているので同梱される
from anthropic.types.beta import agent_create_params, session_create_params, deployment_create_params
from anthropic.types.beta.sessions import event_send_params
from anthropic.types.beta.vaults import credential_create_params
from anthropic.types.beta import environment_create_params


def check(td, value):
    """TypedDict に対して値を検証する（余分なキー・欠落・型違いで例外）。"""
    TypeAdapter(td).validate_python(value, strict=False)


def test_environment():
    check(environment_create_params.EnvironmentCreateParams,
          {"name": "ma-guide-env", "config": {"type": "cloud", "networking": {"type": "unrestricted"}}})


def test_agent_daily_report():
    check(agent_create_params.AgentCreateParams, {
        "name": "Daily Site Reporter",
        "model": {"id": "claude-opus-5", "effort": "medium"},
        "system": "...",
        "tools": [{"type": "agent_toolset_20260401", "default_config": {"enabled": True},
                   "configs": [{"name": "web_search", "enabled": False},
                               {"name": "web_fetch", "max_content_tokens": 20000}]}],
    })


def test_agent_mcp_and_multiagent():
    check(agent_create_params.AgentCreateParams, {
        "name": "GitHub Reader", "model": "claude-opus-5",
        "mcp_servers": [{"type": "url", "name": "github", "url": "https://api.githubcopilot.com/mcp/"}],
        "tools": [{"type": "agent_toolset_20260401", "default_config": {"enabled": False},
                   "configs": [{"name": "read", "enabled": True}]},
                  {"type": "mcp_toolset", "mcp_server_name": "github",
                   "default_config": {"permission_policy": {"type": "auto"}}}],
    })
    check(agent_create_params.AgentCreateParams, {
        "name": "Report Lead", "model": "claude-opus-5", "tools": [{"type": "agent_toolset_20260401"}],
        "multiagent": {"type": "coordinator", "agents": ["agent_123", {"type": "self"}]},
    })


def test_session_shapes():
    base = {"agent": "agent_123", "environment_id": "env_123"}
    check(session_create_params.SessionCreateParams, {**base, "title": "x",
          "budget": {"type": "limit", "max_list_cost": {"amount": "100", "currency": "USD"}}})
    check(session_create_params.SessionCreateParams, {**base,
          "agent": {"type": "agent_with_overrides", "id": "agent_123",
                    "tools": [{"type": "agent_toolset_20260401",
                               "default_config": {"enabled": True, "permission_policy": {"type": "always_allow"}},
                               "configs": [{"name": "bash", "permission_policy": {"type": "always_ask"}}]}]}})
    check(session_create_params.SessionCreateParams, {**base,
          "resources": [{"type": "file", "file_id": "file_1", "mount_path": "/workspace/sites.txt"},
                        {"type": "memory_store", "memory_store_id": "memstore_1", "access": "read_write", "instructions": "..."}],
          "vault_ids": ["vlt_1"]})
    check(session_create_params.SessionCreateParams, {**base,
          "initial_events": [{"type": "user.define_outcome", "description": "...",
                              "rubric": {"type": "text", "content": "# rubric"}, "max_iterations": 3}]})


def test_events():
    check(event_send_params.EventSendParams, {"events": [
        {"type": "user.message", "content": [{"type": "text", "text": "hi"}]},
        {"type": "user.tool_confirmation", "tool_use_id": "sevt_1", "result": "deny", "deny_message": "no"},
        {"type": "user.custom_tool_result", "custom_tool_use_id": "sevt_2",
         "content": [{"type": "text", "text": "ok"}], "is_error": False},
        {"type": "user.interrupt"},
        {"type": "system.message", "content": [{"type": "text", "text": "tz=Asia/Tokyo"}]},
    ]})


def test_deployment():
    check(deployment_create_params.DeploymentCreateParams, {
        "name": "daily", "agent": "agent_123", "environment_id": "env_123",
        "initial_events": [{"type": "user.message", "content": [{"type": "text", "text": "go"}]}],
        "schedule": {"type": "cron", "expression": "0 8 * * 1-5", "timezone": "Asia/Tokyo"},
        "budget": {"type": "limit", "max_list_cost": {"amount": "200", "currency": "USD"}},
    })


def test_credentials():
    check(credential_create_params.CredentialCreateParams, {"display_name": "slack", "auth": {
        "type": "environment_variable", "secret_name": "SLACK_BOT_TOKEN", "secret_value": "xoxb",
        "networking": {"type": "limited", "allowed_hosts": ["slack.com"]},
        "injection_location": {"header": True}}})
    check(credential_create_params.CredentialCreateParams, {"auth": {
        "type": "static_bearer", "mcp_server_url": "https://api.githubcopilot.com/mcp/", "token": "ghp"}})


def test_drain_logic_offline():
    """drain() の停止条件を、偽のストリームで検証する。"""
    from types import SimpleNamespace as NS
    from ma import drain as drain_fn

    sent = []

    class FakeStream:
        def __init__(self, evs): self.evs = evs
        def __enter__(self): return iter(self.evs)
        def __exit__(self, *a): return False

    rounds = [
        [NS(type="agent.custom_tool_use", id="sevt_a", name="echo", input={"x": 1}, session_thread_id=None),
         NS(type="session.status_idle", stop_reason=NS(type="requires_action"))],
        [NS(type="agent.message", content=[NS(type="text", text="done")]),
         NS(type="session.status_idle", stop_reason=NS(type="end_turn"))],
    ]
    it = iter(rounds)
    events = NS(stream=lambda session_id: FakeStream(next(it)),
                send=lambda session_id, events: sent.append(events))
    client = NS(beta=NS(sessions=NS(events=events)))
    stop = drain_fn(client, "sesn_1", first_events=[{"type": "user.message", "content": []}],
                   on_event=None, custom_tools={"echo": lambda name, inp: f"{name}:{inp['x']}"})
    assert stop == "end_turn"
    assert sent[0][0]["type"] == "user.message"
    assert sent[1][0] == {"type": "user.custom_tool_result", "custom_tool_use_id": "sevt_a",
                          "content": [{"type": "text", "text": "echo:1"}], "is_error": False}


if __name__ == "__main__":
    import inspect
    for name, fn in list(globals().items()):
        if name.startswith("test_") and inspect.isfunction(fn):
            fn(); print("ok", name)
