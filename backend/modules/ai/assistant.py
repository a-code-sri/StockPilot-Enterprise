"""
AI assistant and dashboard insights on top of a local Ollama model.

Chat flow (function calling):
  1. Send the conversation plus the tools the user may use.
  2. If the model requests tools, run them (read-only, permission-checked),
     append the results and ask again. At most MAX_TOOL_ROUNDS rounds.
  3. Return the final answer and which tools were used.

Fallback ("context mode") for models without tool support: pre-run the overview
tools the user may access and put their output in the system prompt.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.core.time import utctoday
from backend.modules.ai.client import OllamaClient, ToolsNotSupported
from backend.modules.ai.tools import INSIGHT_SOURCES, TOOLS_BY_NAME, Tool, tools_for

logger = logging.getLogger("ai.assistant")

MAX_TOOL_ROUNDS = 4
MAX_HISTORY_MESSAGES = 12
MAX_TOOL_RESULT_CHARS = 6000
CONTEXT_MODE_TOOLS = (
    "inventory_alerts", "accounts_summary", "delivery_overview", "projects_overview", "organization_overview",
    "business_profile",
)

SYSTEM_PROMPT = """You are StockPilot Assistant, a concise business analyst for a manufacturing company.
Today is {today}. You are helping {username}.
Rules:
- Answer ONLY from tool results or data provided to you. Never invent numbers, names or dates.
- If the data needed is not available to you, say so plainly.
- Prefer short answers: a sentence or two, or a few bullet points. Use markdown.
- Money amounts are in the business's currency; do not add a currency symbol unless shown.
- You can only read data; you cannot create, change or delete anything. If asked to, explain which page to use.
"""


def _to_json(data: Any) -> str:
    text = json.dumps(data, default=str, separators=(",", ":"))
    if len(text) > MAX_TOOL_RESULT_CHARS:
        text = text[:MAX_TOOL_RESULT_CHARS] + '..."(truncated)"'
    return text


def _run_tool(db: Session, tool: Tool, args: Any) -> str:
    if isinstance(args, str):
        try:
            args = json.loads(args or "{}")
        except json.JSONDecodeError:
            args = {}
    if not isinstance(args, dict):
        args = {}
    try:
        return _to_json(tool.run(db, **args))
    except Exception as e:  # a tool failure should not end the conversation
        logger.exception("AI tool %s failed", tool.name)
        db.rollback()
        return _to_json({"error": f"{type(e).__name__}: {e}"})


def _clean_history(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    cleaned = [
        {"role": m["role"], "content": str(m.get("content", ""))[:4000]}
        for m in messages
        if m.get("role") in ("user", "assistant") and str(m.get("content", "")).strip()
    ]
    return cleaned[-MAX_HISTORY_MESSAGES:]


class Assistant:
    def __init__(self, db: Session, user, permissions: set[str], client: OllamaClient | None = None):
        self.db = db
        self.user = user
        self.tools = tools_for(permissions)
        self.client = client or OllamaClient()

    def _system(self, extra: str = "") -> dict[str, str]:
        content = SYSTEM_PROMPT.format(today=utctoday().isoformat(), username=self.user.username)
        if extra:
            content += "\n" + extra
        return {"role": "system", "content": content}

    def chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        history = _clean_history(messages)
        if not history or history[-1]["role"] != "user":
            return {"reply": "Ask me a question about your business data.", "tools_used": [], "mode": "none"}
        try:
            return self._chat_with_tools(history)
        except ToolsNotSupported:
            logger.info("Model lacks tool support; using context mode")
            return self._chat_with_context(history)

    def _chat_with_tools(self, history: list[dict[str, str]]) -> dict[str, Any]:
        allowed = {t.name: t for t in self.tools}
        convo: list[dict[str, Any]] = [self._system()] + history
        used: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            msg = self.client.chat(convo, tools=[t.schema() for t in self.tools])
            calls = msg.get("tool_calls") or []
            if not calls:
                return {"reply": (msg.get("content") or "").strip(), "tools_used": used, "mode": "tools"}

            convo.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
            for call in calls:
                fn = call.get("function") or {}
                name = fn.get("name", "")
                tool = allowed.get(name)
                if tool is None:
                    reason = "not permitted for this user" if name in TOOLS_BY_NAME else "unknown tool"
                    result = _to_json({"error": f"Tool '{name}' is {reason}."})
                else:
                    result = _run_tool(self.db, tool, fn.get("arguments"))
                    used.append(name)
                convo.append({"role": "tool", "content": result, "tool_name": name})

        # Out of rounds: ask for a final answer without tools.
        convo.append({"role": "user", "content": "Answer now using the data above."})
        msg = self.client.chat(convo)
        return {"reply": (msg.get("content") or "").strip(), "tools_used": used, "mode": "tools"}

    def _chat_with_context(self, history: list[dict[str, str]]) -> dict[str, Any]:
        allowed = {t.name: t for t in self.tools}
        used = [n for n in CONTEXT_MODE_TOOLS if n in allowed]
        context = "\n".join(f"### {n}\n{_run_tool(self.db, allowed[n], {})}" for n in used)
        msg = self.client.chat([self._system("Business data (JSON):\n" + context)] + history)
        return {"reply": (msg.get("content") or "").strip(), "tools_used": used, "mode": "context"}

    def insights(self, module: str) -> dict[str, Any]:
        sources = INSIGHT_SOURCES[module]
        allowed = {t.name: t for t in self.tools}
        data = {name: json.loads(_run_tool(self.db, allowed[name], {})) for name in sources if name in allowed}
        prompt = (
            f"Here is current {module} data as JSON:\n{_to_json(data)}\n\n"
            "Write a short briefing in markdown:\n"
            "- 3 to 5 bullet points with the most important observations (cite the numbers),\n"
            "- then a line starting with **Recommended actions:** followed by 1-2 concrete actions.\n"
            "Mention anomalies if any are present. Do not invent data."
        )
        msg = self.client.chat([self._system(), {"role": "user", "content": prompt}], temperature=0.3)
        return {"module": module, "summary": (msg.get("content") or "").strip(), "sources": list(data)}
