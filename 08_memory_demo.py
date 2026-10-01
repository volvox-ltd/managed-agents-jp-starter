"""記憶 ― Memory Store を付けて「前回の日報との差分」を書けるようにする。

ストアはコンテナに /mnt/memory/<store名>/ としてマウントされ、通常のファイルツールで読み書きされる。
書き込みは全て不変のバージョン (memver_...) として残り、監査・巻き戻し・秘匿化ができる。
秘密情報は絶対に書かせないこと（次回以降のコンテキストにそのまま流れる）。
"""
import anthropic

from ma import console_url, drain, load_ids, require_id, save_id

client = anthropic.Anthropic()
ids = load_ids()

if "memory_store_id" not in ids:
    store = client.beta.memory_stores.create(
        name="site-report-memory",
        description="巡回対象ページの前回取得時の要点。ページごとに1ファイル (/sites/<host>.md)。",  # モデルに読ませる説明
    )
    save_id("memory_store_id", store.id)
    client.beta.memory_stores.memories.create(
        store.id,
        path="/README.md",
        content="このストアには巡回ページごとの『前回の要点』を /sites/<host>.md に保存します。日報を書く前に必ず読み、書き終えたら更新してください。",
    )
store_id = require_id("memory_store_id")

session = client.beta.sessions.create(
    agent=require_id("agent_id"),
    environment_id=require_id("environment_id"),
    title="memory demo",
    resources=[{
        "type": "memory_store",
        "memory_store_id": store_id,
        "access": "read_write",
        "instructions": "日報作成の前に /sites/ を読み、前回からの差分を日報に書く。終わったら今回の要点で上書きする。",
    }],
)
print("console:", console_url(session.id))
drain(client, session.id, first_events=[{"type": "user.message", "content": [{"type": "text",
      "text": "https://www.anthropic.com/news を巡回して日報を書いてください。"}]}])

# ホスト側から記憶を点検する
for m in client.beta.memory_stores.memories.list(store_id, path_prefix="/", view="full"):
    if m.type == "memory":
        print(f"--- {m.path} ({m.content_size_bytes} bytes)\n{(m.content or '')[:300]}")
