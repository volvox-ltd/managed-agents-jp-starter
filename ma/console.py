import os


def console_url(session_id: str) -> str:
    """Console のセッション画面。開発中はこれを開いて眺めるのが一番早い。

    {workspace} は API キーが属するワークスペース。Default ワークスペース以外のキーなら
    ANTHROPIC_WORKSPACE にワークスペース ID を入れる（セッション応答にはワークスペース情報が
    含まれないので、自分で持つしかない）。
    """
    ws = os.environ.get("ANTHROPIC_WORKSPACE", "default")
    return f"https://platform.claude.com/workspaces/{ws}/sessions/{session_id}"
