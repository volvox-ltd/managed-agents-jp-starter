"""Deployment の直近の実行を確認し、成果物を取り出す。cron や CI から呼ぶ想定。"""
import time

import anthropic

from ma import console_url, require_id

client = anthropic.Anthropic()
dep_id = require_id("deployment_id")

runs = list(client.beta.deployment_runs.list(deployment_id=dep_id, limit=5))
if not runs:
    raise SystemExit("実行記録がありません")
for r in runs:
    print(r.created_at, r.trigger_context.type, r.session_id or f"ERROR {r.error.type}: {r.error.message}")

latest = runs[0]
if not latest.session_id:
    raise SystemExit("直近の実行はセッションを作れていません。error を確認してください")
print("console:", console_url(latest.session_id))

# 終わるまで待つ（本番では webhooks を使う。章 12）
while True:
    s = client.beta.sessions.retrieve(session_id=latest.session_id)
    print("status:", s.status)
    if s.status in ("idle", "terminated"):
        break
    time.sleep(10)

for _ in range(3):
    files = client.beta.files.list(scope_id=latest.session_id, betas=["managed-agents-2026-04-01"])
    if files.data:
        break
    time.sleep(2)
for f in files.data:
    client.beta.files.download(f.id).write_to_file(f"report_{latest.created_at:%Y%m%d}_{f.filename}")
    print("saved:", f.filename)
print("list_cost:", s.usage.list_cost if s.usage else None)
