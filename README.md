# managed-agents-jp-starter

Zenn 本『Claude Managed Agents 実践ガイド』の付属コードです。
Claude Managed Agents（Anthropic がエージェントループとサンドボックスを運用する、サーバー不要のエージェント基盤）を Python で動かす最小構成を、章ごとのスクリプトにしてあります。

| ファイル | 章 | 内容 |
|---|---|---|
| `01_setup.py` | 3 | Environment と Agent を **一度だけ** 作り、ID を `.ma_ids.json` に保存 |
| `02_run_session.py` | 3–4 | セッションを作り、ストリームを正しい停止条件で読み切り、成果物を回収 |
| `smoke_test.py` | 3 | 上限 $0.50 の疎通テスト |
| `03_permissions_demo.py` | 5 | `bash` だけ人間の承認を必須にする |
| `04_files_demo.py` | 6 | Files API で入力をマウントし、`/mnt/session/outputs/` から出力を取る |
| `05_vault_env_demo.py` | 7 | Vault の環境変数資格情報で Slack に投稿（秘密はサンドボックスに入らない） |
| `06_mcp_demo.py` | 8 | GitHub MCP サーバー接続（認証は Vault） |
| `07_deploy_daily_report.py` / `07b_fetch_latest_run.py` | 9 | cron で毎朝動く Deployment と、結果の回収 |
| `08_memory_demo.py` | 10 | Memory Store で前回との差分を書く |
| `09_multiagent_demo.py` | 11 | 安価なワーカーに並列委譲するコーディネータ |
| `10_webhook_server.py` | 12 | Webhook で完了通知を受ける |
| `11_outcome_demo.py` | 12 | ルーブリック採点で合格まで回す Outcome |
| `agents/*.yaml` | 3, 12 | `ant` CLI で同じ Agent / Environment を作る定義 |
| `ma/` | 共通 | ID 保存・Console URL・イベント読み切りループ `drain()` |

## 使い方

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # anthropic>=1.0.0
cp .env.example .env                     # ANTHROPIC_API_KEY を設定
set -a; source .env; set +a

python tests/test_params.py              # ネットワーク不要。パラメータの形を SDK の型で検査
python 01_setup.py                       # 一度だけ
python smoke_test.py                     # 疎通（$0.50 上限）
python 02_run_session.py https://www.anthropic.com/news
```

## 注意

- Managed Agents は **ベータ** です（`managed-agents-2026-04-01`）。仕様変更があり得ます。公式ドキュメント: https://platform.claude.com/docs/en/managed-agents/overview
- Agent / Environment / Memory Store の **archive は取り消せません**。サンプルはセッション以外を archive しません。
- 費用: モデルトークン（定価）＋ web 検索 $10/1,000 回＋セッション稼働時間 $0.08/時。各サンプルは `budget` で上限を付けています。

## ライセンス

MIT
