"""秘密情報 ― Vault の environment_variable 資格情報で Slack に投稿する。

秘密はサンドボックスに入らない。コンテナ内の bash が見るのは置き換え用のプレースホルダで、
本物の値は Anthropic 側の出口で「許可したホスト宛て」のリクエストにだけ差し込まれる。
ここでは Slack の chat.postMessage（Authorization ヘッダにトークン）を使う。
Incoming Webhook の URL は「URL パスに秘密が入る」形なので Vault では扱えない点に注意。
"""
import os

import anthropic

from ma import console_url, drain, load_ids, require_id, save_id

client = anthropic.Anthropic()
ids = load_ids()

if "vault_id" not in ids:
    vault = client.beta.vaults.create(display_name="ma-guide vault")
    save_id("vault_id", vault.id)
    client.beta.vaults.credentials.create(
        vault.id,
        display_name="Slack bot token",
        auth={
            "type": "environment_variable",
            "secret_name": "SLACK_BOT_TOKEN",
            "secret_value": os.environ["SLACK_BOT_TOKEN"],
            "networking": {"type": "limited", "allowed_hosts": ["slack.com"]},
            "injection_location": {"header": True},  # ヘッダにだけ差し込む（本文には差し込まない）
        },
    )
    print("vault:", vault.id)
vault_id = require_id("vault_id")

channel = os.environ["SLACK_CHANNEL"]
session = client.beta.sessions.create(
    agent=require_id("agent_id"),
    environment_id=require_id("environment_id"),
    title="vault demo",
    vault_ids=[vault_id],  # vault_ids はセッション作成時のみ指定できる（update では拒否される）
)
print("console:", console_url(session.id))

task = f"""https://www.anthropic.com/news を巡回して日報を書いたあと、要点3行を Slack に投稿してください。
投稿は bash から次のように行います（$SLACK_BOT_TOKEN は環境変数として存在します。値を表示・保存しないでください）:
curl -sS https://slack.com/api/chat.postMessage -H "Authorization: Bearer $SLACK_BOT_TOKEN" \\
  -H "Content-Type: application/json; charset=utf-8" \\
  -d '{{"channel": "{channel}", "text": "<要点>"}}'
レスポンスの ok が true であることを確認して報告してください。"""
drain(client, session.id, first_events=[{"type": "user.message", "content": [{"type": "text", "text": task}]}])
