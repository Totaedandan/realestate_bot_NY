from __future__ import annotations
import json
from typing import Any, Dict, Optional
from app.config import settings

class LLMClient:
    def __init__(self) -> None:
        self.enabled = (settings.LLM_MODE.lower() == "on" and bool(settings.OPENAI_API_KEY))
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def extract(self, state: Dict[str, Any], user_text: str, listing_text: Optional[str]) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        schema = {
            "type": "object",
            "properties": {
                "reply": {"type": "string"},
                "updates": {
                    "type": "object",
                    "properties": {
                        "listing_ref": {"type": ["string", "null"]},
                        "people_count": {"type": ["integer", "null"]},
                        "employment": {"type": ["string", "null"]},
                        "lease_term": {"type": ["string", "null"]},
                        "budget_usd": {"type": ["integer", "null"]},
                        "pets": {"type": ["string", "null"]},
                        "children": {"type": ["string", "null"]},
                        "showing_time": {"type": ["string", "null"]},
                    },
                    "additionalProperties": False,
                },
                "handoff": {"type": "boolean"},
                "pause": {"type": "boolean"},
                "next_question": {"type": ["string", "null"]},
            },
            "required": ["reply", "updates", "handoff", "pause", "next_question"],
            "additionalProperties": False,
        }

        system = (
            "You are a Telegram assistant for US rentals (USD only). "
            "Handle first touch. Ask minimal qualifying questions. "
            "Answer listing questions ONLY from listing text. If not specified, say it's not specified and will be clarified. "
            "Be concise, friendly, in Russian."
        )

        context = {
            "state": state,
            "listing_text": (listing_text[:1500] if listing_text else None),
            "user_text": user_text[:1500],
            "constraints": {"usd_only": True},
        }

        client = self._get_client()
        try:
            resp = client.responses.create(
                model=settings.OPENAI_MODEL,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": "Return JSON strictly matching the provided JSON Schema."},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ],
                text={"format": {"type": "json_schema", "name": "leadbot", "schema": schema}},
            )
            return json.loads(resp.output_text)
        except Exception:
            return None

    def transcribe(self, audio_path: str) -> Optional[str]:
        if not bool(settings.OPENAI_API_KEY):
            return None
        client = self._get_client()
        try:
            with open(audio_path, "rb") as f:
                tr = client.audio.transcriptions.create(
                    model=settings.OPENAI_TRANSCRIBE_MODEL,
                    file=f,
                )
            return getattr(tr, "text", None) or None
        except Exception:
            return None

llm = LLMClient()
