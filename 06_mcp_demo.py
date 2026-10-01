"""MCP サーバー接続 ― Agent 側は URL だけを宣言し、認証トークンは Vault に置く。

例として GitHub の MCP サーバー (https://api.githubcopilot.com/mcp/) を使う。
MCP の認証は OAuth か static bearer。GitHub の fine-grained PAT は static_bearer として登録できる。
MCP ツールの既定ポリシーは always_ask。ここでは auto（サーバー側が判定）に緩める。
"""
import os

import anthropic

from ma import console_url, drain, load_ids, require_id, save_id

client = anthropic.Anthropic()
ids = load_ids()
MCP_URL = "https://api.githubcopilot.com/mcp/"

if "mcp_agent_id" not in ids:
    agent = client.beta.agents.create(
        name="GitHub Reader",
        description="GitHub の MCP サーバーでリポジトリ情報を読む",
        model={"id": os.environ.get("MA_MODEL", "claude-opus-5"), "effort": "medium"},
        system="GitHub の MCP ツールで質問に答えます。書き込み系の操作はしません。",
        mcp_servers=[{"type": "url", "name": "github", "url": MCP_URL}],
        tools=[
            {"type": "agent_toolset_20260401", "default_config": {"enabled": False},
             "configs": [{"name": "read", "enabled": True}]},
            {"type": "mcp_toolset", "mcp_server_name": "github",
             "default_config": {"permission_policy": {"type": "auto"}}},
        ],
    )
    save_id("mcp_agent_id", agent.id)

if "github_vault_id" not in ids:
    vault = client.beta.vaults.create(display_name="GitHub MCP")
    client.beta.vaults.credentials.create(
        vault.id,
        display_name="GitHub PAT (static bearer)",
        auth={"type": "static_bearer", "mcp_server_url": MCP_URL, "token": os.environ["GITHUB_TOKEN"]},
    )
    save_id("github_vault_id", vault.id)

session = client.beta.sessions.create(
    agent=require_id("mcp_agent_id"),
    environment_id=require_id("environment_id"),
    title="mcp demo",
    vault_ids=[require_id("github_vault_id")],  # URL が一致する資格情報が自動で使われる
)
print("console:", console_url(session.id))

repo = os.environ.get("GITHUB_REPO", "anthropics/anthropic-sdk-python")

# 外部サービス依存は作成時には失敗しない。最初の1ターンを「疎通確認」に使う
drain(client, session.id, first_events=[{"type": "user.message", "content": [{"type": "text",
      "text": f"疎通確認: {repo} の最新リリース1件のタグ名だけ答えてください。他の作業はしないでください。"}]}])
drain(client, session.id, first_events=[{"type": "user.message", "content": [{"type": "text",
      "text": f"{repo} の直近5件のリリースノートの要点を日本語でまとめてください。"}]}])
