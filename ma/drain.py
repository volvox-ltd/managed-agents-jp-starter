"""イベントストリームを読み切る。

ポイントは3つ。
1. ストリームを開いてから最初のイベントを送る（送ってから開くと取りこぼす）
2. `session.status_idle` で即 break しない。stop_reason が requires_action のときは
   こちらの応答（ツール承認・カスタムツール結果）待ちなので、応えて続ける
3. `session.status_terminated` か、requires_action 以外の idle で終わる
"""
from __future__ import annotations

import json
from typing import Any, Callable, Iterable

import anthropic

ToolHandler = Callable[[str, dict[str, Any]], str]
Confirmer = Callable[[Any], bool]


def _text_of(content: Iterable[Any]) -> str:
    parts = []
    for block in content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)


def print_event(ev: Any) -> None:
    """人間向けの簡易表示。本番ではロガーに置き換える。"""
    t = ev.type
    if t == "agent.message":
        print(_text_of(ev.content))
    elif t in ("agent.tool_use", "agent.mcp_tool_use"):
        arg = json.dumps(ev.input, ensure_ascii=False)
        print(f"  [tool] {ev.name}({arg[:120]}{'…' if len(arg) > 120 else ''})  permission={ev.evaluated_permission}")
    elif t in ("agent.tool_result", "agent.mcp_tool_result"):
        flag = " (error)" if getattr(ev, "is_error", False) else ""
        print(f"  [result]{flag}")
    elif t == "agent.custom_tool_use":
        print(f"  [custom tool] {ev.name} {json.dumps(ev.input, ensure_ascii=False)}")
    elif t == "session.error":
        print(f"  [error] {ev.error}")
    elif t == "span.model_request_end":
        u = ev.model_usage
        print(f"  [usage] in={u.input_tokens} out={u.output_tokens} cache_read={u.cache_read_input_tokens}")
    elif t == "session.status_idle":
        print(f"  [idle] stop_reason={ev.stop_reason.type}")
    elif t == "session.status_terminated":
        print("  [terminated]")
    elif t.startswith("session.thread_") or t.startswith("agent.thread_"):
        name = getattr(ev, "agent_name", None) or getattr(ev, "from_agent_name", None) or getattr(ev, "to_agent_name", None)
        print(f"  [{t}] {name or ''}")


def drain(
    client: anthropic.Anthropic,
    session_id: str,
    *,
    first_events: list[dict[str, Any]] | None = None,
    on_event: Callable[[Any], None] | None = print_event,
    custom_tools: dict[str, ToolHandler] | None = None,
    confirm: Confirmer | None = None,
) -> str:
    """セッションが止まるまでイベントを処理し、最後の stop_reason（または 'terminated'）を返す。

    first_events: ストリームを開いた直後に送るイベント（user.message など）。
    custom_tools: {ツール名: handler}。agent.custom_tool_use を受けたら handler(name, input) の
                  戻り値を user.custom_tool_result として返す。
    confirm:      permission が 'ask' のツール呼び出しに対して True/False を返す関数。
                  None の場合は 'ask' をすべて deny する（安全側）。
    """
    custom_tools = custom_tools or {}
    while True:
        pending_custom: list[Any] = []
        pending_ask: list[Any] = []
        with client.beta.sessions.events.stream(session_id=session_id) as stream:
            if first_events:
                client.beta.sessions.events.send(session_id=session_id, events=first_events)
                first_events = None
            for ev in stream:
                if on_event:
                    on_event(ev)
                if ev.type == "agent.custom_tool_use":
                    pending_custom.append(ev)
                elif ev.type in ("agent.tool_use", "agent.mcp_tool_use") and ev.evaluated_permission == "ask":
                    pending_ask.append(ev)
                elif ev.type == "session.status_terminated":
                    return "terminated"
                elif ev.type == "session.status_idle":
                    if ev.stop_reason.type == "requires_action":
                        break  # こちらの番。ストリームを抜けて応答を送る
                    return ev.stop_reason.type  # end_turn / retries_exhausted / budget_reached

        replies: list[dict[str, Any]] = []
        for ev in pending_ask:
            ok = bool(confirm(ev)) if confirm else False
            reply: dict[str, Any] = {
                "type": "user.tool_confirmation",
                "tool_use_id": ev.id,  # toolu_ ではなくイベント ID
                "result": "allow" if ok else "deny",
            }
            if not ok:
                reply["deny_message"] = "このツール呼び出しは運用者に拒否されました。別の方法を検討してください。"
            if getattr(ev, "session_thread_id", None):
                reply["session_thread_id"] = ev.session_thread_id
            replies.append(reply)
        for ev in pending_custom:
            handler = custom_tools.get(ev.name)
            if handler is None:
                result, is_error = f"unknown tool: {ev.name}", True
            else:
                try:
                    result, is_error = handler(ev.name, ev.input), False
                except Exception as e:  # ツール側の失敗はエージェントに伝える
                    result, is_error = f"{type(e).__name__}: {e}", True
            reply = {
                "type": "user.custom_tool_result",
                "custom_tool_use_id": ev.id,
                "content": [{"type": "text", "text": result}],
                "is_error": is_error,
            }
            if getattr(ev, "session_thread_id", None):
                reply["session_thread_id"] = ev.session_thread_id
            replies.append(reply)
        if not replies:
            # requires_action なのに応答すべきものが無い（通常は起きない）。無限ループを避けて抜ける
            return "requires_action"
        client.beta.sessions.events.send(session_id=session_id, events=replies)
