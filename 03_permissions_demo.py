"""ツールの権限ポリシー ― bash だけ人間の承認を必須にする（always_ask）。

承認待ちになると session.status_idle(stop_reason=requires_action) で止まる。
drain() の confirm コールバックで allow/deny を返す。
"""
import anthropic

from ma import console_url, drain, require_id

client = anthropic.Anthropic()

# この回だけツール設定を差し替える（Agent 本体は変更しない = バージョンも増えない）
session = client.beta.sessions.create(
    agent={
        "type": "agent_with_overrides",
        "id": require_id("agent_id"),
        "tools": [
            {
                "type": "agent_toolset_20260401",
                "default_config": {"enabled": True, "permission_policy": {"type": "always_allow"}},
                "configs": [
                    {"name": "bash", "permission_policy": {"type": "always_ask"}},
                ],
            }
        ],
    },
    environment_id=require_id("environment_id"),
    title="permissions demo",
)
print("console:", console_url(session.id))


def ask_human(ev) -> bool:
    print(f"\n承認しますか? {ev.name} {ev.input}")
    return input("[y/N] ").strip().lower() == "y"


drain(
    client,
    session.id,
    first_events=[{"type": "user.message", "content": [{"type": "text", "text": "/workspace の内容を bash の ls -la で確認して報告してください。"}]}],
    confirm=ask_human,
)
