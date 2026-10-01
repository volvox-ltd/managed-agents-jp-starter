"""Claude Managed Agents 実践ガイド ― 付属ヘルパー。

全スクリプトが共有する小さな部品だけを置く。
- ids: 作成した Agent / Environment などの ID を .ma_ids.json に保存・読込
- console_url: Console のセッション画面 URL
- drain: イベントストリームを「正しい停止条件」で読み切るループ
"""
from .ids import load_ids, save_id, require_id
from .console import console_url
from .drain import drain, print_event

__all__ = ["load_ids", "save_id", "require_id", "console_url", "drain", "print_event"]
