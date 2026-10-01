"""ONE-TIME SETUP ― 一度だけ実行して ID を保存する。

Environment と Agent は使い回す資源。毎回作らない。
agents/*.yaml と同じ内容を SDK で作成する（CLI `ant` を使うなら YAML を直接 create すればよい）。
"""
import os

import anthropic

from ma import load_ids, save_id

client = anthropic.Anthropic()
ids = load_ids()
MODEL = os.environ.get("MA_MODEL", "claude-opus-5")

if "environment_id" not in ids:
    env = client.beta.environments.create(
        name="ma-guide-env",
        description="本書のサンプル共通",
        config={"type": "cloud", "networking": {"type": "unrestricted"}},
    )
    save_id("environment_id", env.id)
    print("environment:", env.id)
else:
    print("environment (既存):", ids["environment_id"])

if "agent_id" not in ids:
    agent = client.beta.agents.create(
        name="Daily Site Reporter",
        description="指定された Web ページ群を巡回し、前回からの変化と要点を Markdown 日報にまとめる",
        model={"id": MODEL, "effort": "medium"},
        system=(
            "あなたは Web サイト巡回担当です。指示されたページを web_fetch で取得し、"
            "日本語の Markdown 日報を /mnt/session/outputs/report.md に書きます。\n"
            "日報の構成: 1) 今日の要点（3行以内） 2) ページごとの変化・新着 3) 要確認事項。\n"
            "取得できなかったページは、その旨と理由を記録して先に進みます。推測で内容を補わないでください。"
        ),
        tools=[
            {
                "type": "agent_toolset_20260401",
                "default_config": {"enabled": True},
                "configs": [
                    {"name": "web_search", "enabled": False},
                    {"name": "web_fetch", "max_content_tokens": 20000},
                ],
            }
        ],
    )
    save_id("agent_id", agent.id)
    save_id("agent_version", str(agent.version))
    print("agent:", agent.id, "version", agent.version)
else:
    print("agent (既存):", ids["agent_id"])
