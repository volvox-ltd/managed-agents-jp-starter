"""作成済みリソースの ID を保存する。

Agent や Environment は「一度作って使い回す」資源。スクリプトを実行するたびに
作り直すと孤児のリソースが溜まり、バージョン管理の意味もなくなる。
ここでは最も単純な方法として、カレントディレクトリの .ma_ids.json に保存する。
本番ではシークレットマネージャや設定ファイルに置き換える。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

IDS_FILE = Path(os.environ.get("MA_IDS_FILE", ".ma_ids.json"))


def load_ids() -> dict[str, str]:
    if IDS_FILE.exists():
        return json.loads(IDS_FILE.read_text())
    return {}


def save_id(key: str, value: str) -> None:
    ids = load_ids()
    ids[key] = value
    IDS_FILE.write_text(json.dumps(ids, indent=2, ensure_ascii=False) + "\n")


def require_id(key: str, hint: str = "先に 01_setup.py を実行してください") -> str:
    value = load_ids().get(key)
    if not value:
        sys.exit(f"{IDS_FILE} に {key} がありません。{hint}")
    return value
