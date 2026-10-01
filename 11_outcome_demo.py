"""Outcome ― 「完成の定義」をルーブリックで渡し、合格するまで採点→修正を回させる。"""
import anthropic

from ma import console_url, drain, require_id

client = anthropic.Anthropic()

RUBRIC = """\
# 日報の合格基準
1. /mnt/session/outputs/report.md が存在する
2. 先頭に「今日の要点」見出しがあり、箇条書きが 3 行以内である
3. 指定した各 URL について見出しが 1 つずつあり、取得失敗時は理由が書かれている
4. 「要確認事項」見出しがある（無ければ「なし」と明記）
5. 本文に推測を示す語（「おそらく」「と思われる」）が含まれない
"""

session = client.beta.sessions.create(
    agent=require_id("agent_id"),
    environment_id=require_id("environment_id"),
    title="outcome demo",
    initial_events=[{  # 作成と同時に開始できる（user.define_outcome は 1 つだけ・rubric 必須）
        "type": "user.define_outcome",
        "description": "https://www.anthropic.com/news と https://docs.anthropic.com/ を巡回した日報を書く",
        "rubric": {"type": "text", "content": RUBRIC},
        "max_iterations": 3,
    }],
)
print("console:", console_url(session.id), "status:", session.status)  # initial_events ありは最初から running


def show(ev):
    if ev.type == "span.outcome_evaluation_end":
        print(f"  [grader] iteration={ev.iteration} result={ev.result}\n  {ev.explanation[:300]}")
    else:
        from ma import print_event
        print_event(ev)


drain(client, session.id, on_event=show)
s = client.beta.sessions.retrieve(session_id=session.id)
for o in s.outcome_evaluations or []:
    print("outcome:", o.outcome_id, o.result)
