"""定期実行 ― Deployment を作る（SETUP 側）。毎朝 8:00 JST に日報セッションを自動で起こす。

セッション側の起動コードは不要。初回イベント (initial_events) を Deployment が持つ。
テストは手動実行 (deployments.run) で行う。手動実行は一時停止中でも可能。
"""
import anthropic

from ma import load_ids, require_id, save_id

client = anthropic.Anthropic()
ids = load_ids()

SITES = ["https://www.anthropic.com/news", "https://docs.anthropic.com/"]
task = "次のページを巡回して日報を書いてください:\n" + "\n".join(f"- {u}" for u in SITES)

if "deployment_id" not in ids:
    dep = client.beta.deployments.create(
        name="daily site report",
        agent=require_id("agent_id"),
        environment_id=require_id("environment_id"),
        initial_events=[{"type": "user.message", "content": [{"type": "text", "text": task}]}],
        schedule={"type": "cron", "expression": "0 8 * * 1-5", "timezone": "Asia/Tokyo"},  # 平日 8:00
        budget={"type": "limit", "max_list_cost": {"amount": "200", "currency": "USD"}},  # 1回あたり上限 $2.00
    )
    save_id("deployment_id", dep.id)
    print("deployment:", dep.id, dep.status)
    print("upcoming:", dep.schedule.upcoming_runs_at if dep.schedule else None)
dep_id = require_id("deployment_id")

# 今すぐ1回動かして確かめる（trigger_context.type = manual）
run = client.beta.deployments.run(dep_id)
print("manual run:", run.id, "session:", run.session_id, "error:", run.error)
