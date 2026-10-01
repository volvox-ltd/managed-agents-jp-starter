"""RUNTIME ― 毎回実行する側。保存済みの ID でセッションを作り、ストリームを読み切る。

使い方:
    python 02_run_session.py https://www.anthropic.com/news https://docs.anthropic.com/
"""
import sys

import anthropic

from ma import console_url, drain, require_id

urls = sys.argv[1:] or ["https://www.anthropic.com/news"]
client = anthropic.Anthropic()

session = client.beta.sessions.create(
    agent=require_id("agent_id"),  # 文字列 = 最新バージョン。固定したいなら {"type":"agent","id":...,"version":N}
    environment_id=require_id("environment_id"),
    title="daily report (manual)",
    budget={"type": "limit", "max_list_cost": {"amount": "100", "currency": "USD"}},  # 上限 $1.00（単位はセント）
)
print("session:", session.id, session.status)
print("console:", console_url(session.id))

task = "次のページを巡回して日報を書いてください:\n" + "\n".join(f"- {u}" for u in urls)
stop = drain(
    client,
    session.id,
    first_events=[{"type": "user.message", "content": [{"type": "text", "text": task}]}],
)
print("\nstop:", stop)

# 成果物（/mnt/session/outputs/ 配下）を取り出す。idle 直後は索引に 1〜3 秒の遅れがある
import time

for attempt in range(3):
    files = client.beta.files.list(scope_id=session.id, betas=["managed-agents-2026-04-01"])
    if files.data:
        break
    time.sleep(2)
for f in files.data:
    print("output:", f.filename, f.size_bytes, "bytes")
    client.beta.files.download(f.id).write_to_file(f"outputs_{session.id}_{f.filename}")

final = client.beta.sessions.retrieve(session_id=session.id)
print("list_cost:", final.usage.list_cost if final.usage else None)
