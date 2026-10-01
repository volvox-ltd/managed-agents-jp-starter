"""ファイルの出し入れ ― 入力は Files API で upload して mount、出力は /mnt/session/outputs/ から回収。"""
import pathlib
import time

import anthropic

from ma import console_url, drain, require_id

client = anthropic.Anthropic()

src = pathlib.Path("sample_sites.txt")
src.write_text("https://www.anthropic.com/news\nhttps://docs.anthropic.com/\n")

with src.open("rb") as f:
    uploaded = client.beta.files.upload(file=f)
print("uploaded:", uploaded.id)

session = client.beta.sessions.create(
    agent=require_id("agent_id"),
    environment_id=require_id("environment_id"),
    title="files demo",
    resources=[{"type": "file", "file_id": uploaded.id, "mount_path": "/workspace/sites.txt"}],  # 絶対パス必須・読み取り専用
)
print("console:", console_url(session.id))
# セッション側にはコピーが作られ、file_id は元と異なる
print("mounted file_id:", session.resources[0].file_id if session.resources else None)

drain(
    client,
    session.id,
    first_events=[{"type": "user.message", "content": [{"type": "text", "text": "/workspace/sites.txt に書かれた URL を巡回して日報を書いてください。"}]}],
)

for _ in range(3):
    files = client.beta.files.list(scope_id=session.id, betas=["managed-agents-2026-04-01"])
    if files.data:
        break
    time.sleep(2)
for f in files.data:
    client.beta.files.download(f.id).write_to_file(f.filename)
    print("downloaded:", f.filename)

client.beta.files.delete(uploaded.id)  # 元ファイルは消してよい。セッション側コピーはセッションと共に消える
