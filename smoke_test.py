"""最小の疎通テスト ― 01_setup.py のあとに実行。1 セッション・上限 $0.50。

web_fetch を使わず、bash で日付を取って outputs にファイルを書くだけ。
これが通れば、認証・環境・エージェント・ストリーム・成果物回収の 5 点が確認できる。
"""
import time

import anthropic

from ma import console_url, drain, require_id

client = anthropic.Anthropic()
session = client.beta.sessions.create(
    agent=require_id("agent_id"),
    environment_id=require_id("environment_id"),
    title="smoke test",
    budget={"type": "limit", "max_list_cost": {"amount": "50", "currency": "USD"}},
)
print("console:", console_url(session.id))
stop = drain(client, session.id, first_events=[{"type": "user.message", "content": [{"type": "text",
    "text": "bash で `date -u` を実行し、その出力を /mnt/session/outputs/smoke.txt に書いてください。Web アクセスは不要です。"}]}])
assert stop == "end_turn", stop
for _ in range(5):
    files = client.beta.files.list(scope_id=session.id, betas=["managed-agents-2026-04-01"])
    if files.data:
        break
    time.sleep(2)
names = [f.filename for f in files.data]
assert "smoke.txt" in names, names
print("OK outputs:", names)
s = client.beta.sessions.retrieve(session_id=session.id)
print("list_cost:", s.usage.list_cost if s.usage else None)
client.beta.sessions.archive(session_id=session.id)  # セッションは使い捨て。Agent/Environment は archive しない
