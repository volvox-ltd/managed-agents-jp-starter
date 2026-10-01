"""Webhook 受信 ― ポーリングやストリーム常駐なしで「終わった」を知る。

Console → Manage → Webhooks で HTTPS の URL を登録し、署名鍵 (whsec_...) を
ANTHROPIC_WEBHOOK_SIGNING_KEY に入れる。SDK の unwrap() が署名と鮮度（約5分）を検証する。
ペイロードは ID だけの薄い形。中身は fetch して取る。同じ event.id が複数回届きうるので重複排除する。
標準ライブラリだけで書いた最小サーバー。本番は Flask/FastAPI 等に置き換える。
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

import anthropic

client = anthropic.Anthropic()  # ANTHROPIC_WEBHOOK_SIGNING_KEY を環境変数から読む
seen: set[str] = set()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode()
        try:
            event = client.beta.webhooks.unwrap(raw, headers={k.lower(): v for k, v in self.headers.items()})
        except Exception as e:
            self.send_response(400); self.end_headers(); self.wfile.write(str(e).encode()); return
        self.send_response(204); self.end_headers()  # まず 2xx を返す（3xx を返すと自動停止される）
        if event.id in seen:
            return
        seen.add(event.id)
        data = event.data
        print("webhook:", data.type, data.id)
        if data.type == "session.status_idled":
            # 薄いペイロードなので stop_reason はイベント一覧から取る
            events = client.beta.sessions.events.list(session_id=data.id, types=["session.status_idle"], order="desc", limit=1)
            last = next(iter(events), None)
            print("  stop_reason:", last.stop_reason.type if last else "?")
        elif data.type == "deployment_run.failed":
            run = client.beta.deployment_runs.retrieve(data.id)
            print("  run failed:", run.error.type if run.error else "?")
        elif data.type == "vault_credential.refresh_failed":
            print("  要対応: OAuth の更新に失敗", data.id)

    def log_message(self, *a):  # 標準のアクセスログを抑制
        pass


if __name__ == "__main__":
    print("listening on :8080 (HTTPS 終端はリバースプロキシや ngrok 等で)")
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
