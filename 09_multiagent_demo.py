"""複数エージェント ― 巡回を安価なワーカーに並列で任せ、まとめだけ上位モデルが書く。

ロスターは Agent の multiagent フィールド（tools ではない）。委譲は 1 段のみ。
クライアントは今まで通り 1 セッション・1 ストリームを読むだけでよい。
"""
import os

import anthropic

from ma import console_url, drain, load_ids, require_id, save_id

client = anthropic.Anthropic()
ids = load_ids()

if "worker_agent_id" not in ids:
    worker = client.beta.agents.create(
        name="Page Reader",
        description="1 つの URL を渡すと取得して要点と変化を箇条書きで返す、安価で速い読み取り係",
        model="claude-haiku-4-5",
        system="渡された URL だけを web_fetch で取得し、要点を日本語で 5 行以内に箇条書きで報告します。推測はしません。",
        tools=[{"type": "agent_toolset_20260401", "default_config": {"enabled": False},
                "configs": [{"name": "web_fetch", "enabled": True}]}],
    )
    save_id("worker_agent_id", worker.id)

if "lead_agent_id" not in ids:
    lead = client.beta.agents.create(
        name="Report Lead",
        description="巡回を Page Reader に並列で委譲し、日報を統合して書く",
        model={"id": os.environ.get("MA_MODEL", "claude-opus-5"), "effort": "medium"},
        system=(
            "URL が複数渡されたら、1 URL ずつ Page Reader に同時に委譲してください（自分では取得しない）。"
            "報告が揃ったら統合し、/mnt/session/outputs/report.md に日本語の Markdown 日報を書きます。"
        ),
        tools=[{"type": "agent_toolset_20260401"}],
        multiagent={"type": "coordinator", "agents": [require_id("worker_agent_id"), {"type": "self"}]},
    )
    save_id("lead_agent_id", lead.id)

session = client.beta.sessions.create(
    agent=require_id("lead_agent_id"),
    environment_id=require_id("environment_id"),
    title="multiagent demo",
)
print("console:", console_url(session.id))
urls = ["https://www.anthropic.com/news", "https://docs.anthropic.com/", "https://github.com/anthropics/anthropic-sdk-python/releases"]
drain(client, session.id, first_events=[{"type": "user.message", "content": [{"type": "text",
      "text": "次の URL を巡回して日報を書いてください:\n" + "\n".join(f"- {u}" for u in urls)}]}])

for th in client.beta.sessions.threads.list(session_id=session.id):
    print("thread:", th.id, th.status, getattr(th.agent, "name", None), th.parent_thread_id)
