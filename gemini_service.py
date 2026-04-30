import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MEDICAL_DISCLAIMER = (
    "Medical disclaimer: This AI-generated response is for general informational purposes only "
    "and is not a diagnosis, treatment plan, or substitute for professional medical advice. "
    "Always consult a licensed healthcare professional for personal medical concerns. "
    "Seek urgent care immediately for severe or worsening symptoms."
)


class GeminiServiceError(Exception):
    pass


def is_gemini_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _extract_text(response_json: dict[str, Any]) -> str:
    candidates = response_json.get("candidates") or []
    if not candidates:
        raise GeminiServiceError("Gemini returned no candidates.")

    parts = candidates[0].get("content", {}).get("parts", [])
    text_fragments = [part.get("text", "") for part in parts if part.get("text")]
    text = "\n".join(fragment.strip() for fragment in text_fragments if fragment.strip()).strip()

    if not text:
        raise GeminiServiceError("Gemini returned an empty response.")

    return text


def call_gemini(
    prompt: str,
    *,
    system_instruction: str | None = None,
    generation_config: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiServiceError("GEMINI_API_KEY is not configured.")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
    }

    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if generation_config:
        payload["generationConfig"] = generation_config
    if tools:
        payload["tools"] = tools

    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise GeminiServiceError(f"Gemini API HTTP error {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise GeminiServiceError(f"Gemini API connection error: {exc.reason}") from exc


def fetch_medicine_details(query: str) -> dict[str, Any]:
    prompt = f"""
You are a cautious medical information assistant.
Return structured medicine information for the medicine name below.

Medicine query: {query}

Rules:
- Focus on general adult information unless the medicine is clearly pediatric-only.
- Keep dosage high-level and brief.
- List common side effects only.
- List major contraindications or reasons to avoid use.
- If the medicine is ambiguous, use the most common interpretation and note that in summary.
- Do not claim certainty.
""".strip()

    schema = {
        "type": "object",
        "properties": {
            "medicine": {"type": "string"},
            "dosage": {"type": "string"},
            "side_effects": {
                "type": "array",
                "items": {"type": "string"},
            },
            "contraindications": {
                "type": "array",
                "items": {"type": "string"},
            },
            "summary": {"type": "string"},
        },
        "required": ["medicine", "dosage", "side_effects", "contraindications", "summary"],
    }

    response_json = call_gemini(
        prompt,
        system_instruction=(
            "Provide careful, non-diagnostic medication information. "
            "Never replace professional medical advice."
        ),
        generation_config={
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
        },
    )

    data = json.loads(_extract_text(response_json))

    return {
        "medicine": str(data.get("medicine") or query).strip(),
        "dosage": str(data.get("dosage") or "Consult a licensed clinician or pharmacist.").strip(),
        "side_effects": [str(item).strip() for item in data.get("side_effects", []) if str(item).strip()],
        "contraindications": [
            str(item).strip() for item in data.get("contraindications", []) if str(item).strip()
        ],
        "summary": str(data.get("summary") or "").strip(),
        "disclaimer": MEDICAL_DISCLAIMER,
        "source": "gemini",
    }


def generate_chat_reply(message: str) -> dict[str, Any]:
    prompt = f"""
User medical question or symptom description:
{message}

Write a concise response with:
1. A short general interpretation of the user's question or symptoms.
2. Safe next-step guidance.
3. Red-flag symptoms that need urgent medical attention, if relevant.

Do not diagnose with certainty.
Do not prescribe medication doses unless the user asked general educational questions.
Keep the tone calm and practical.
End with the exact medical disclaimer provided in the system instruction.
""".strip()

    system_instruction = (
        "You are a medical information assistant for a consumer web application. "
        "Give general educational information only, avoid definitive diagnosis, and encourage professional care. "
        f"End every answer with this exact text:\n{MEDICAL_DISCLAIMER}"
    )

    response_json = call_gemini(
        prompt,
        system_instruction=system_instruction,
        generation_config={
            "temperature": 0.4,
        },
        tools=[{"googleSearch": {}}],
    )

    reply = _extract_text(response_json)
    if MEDICAL_DISCLAIMER not in reply:
        reply = f"{reply}\n\n{MEDICAL_DISCLAIMER}"

    return {
        "reply": reply,
        "disclaimer": MEDICAL_DISCLAIMER,
        "source": "gemini",
    }
