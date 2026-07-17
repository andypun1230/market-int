import json
import logging
import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - keeps local status checks working before pip install
    load_dotenv = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional until dependencies are installed
    OpenAI = None

DEFAULT_MODEL = "gpt-5.5-mini"
BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_ROOT / ".env"
logger = logging.getLogger(__name__)


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or "=" not in cleaned:
            continue

        key, value = cleaned.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


if load_dotenv is not None:
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_env_file(ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)


def get_openai_model() -> str:
    return OPENAI_MODEL


def is_openai_enabled() -> bool:
    return bool(OPENAI_API_KEY)


def get_openai_status() -> dict[str, object]:
    return {
        "openai_enabled": bool(OPENAI_API_KEY),
        "model": OPENAI_MODEL,
        "env_path": str(ENV_PATH),
        "env_file_exists": ENV_PATH.exists(),
        "api_key_present": bool(OPENAI_API_KEY),
    }


def generate_structured_summary(
    system_prompt: str,
    user_payload: dict[str, Any],
) -> dict[str, Any] | None:
    return generate_structured_response(
        system_prompt=system_prompt,
        user_payload=user_payload,
        schema_name="market_intelligence_ai_summary",
        response_schema=AI_SUMMARY_SCHEMA,
        validate=validate_summary_payload,
    )


def generate_structured_chat_response(
    system_prompt: str,
    user_payload: dict[str, Any],
) -> dict[str, Any] | None:
    return generate_structured_response(
        system_prompt=system_prompt,
        user_payload=user_payload,
        schema_name="market_intelligence_ai_chat",
        response_schema=AI_CHAT_SCHEMA,
        validate=validate_chat_payload,
    )


def generate_structured_response(
    system_prompt: str,
    user_payload: dict[str, Any],
    schema_name: str,
    response_schema: dict[str, Any],
    validate: Any,
) -> dict[str, Any] | None:
    if not is_openai_enabled():
        return None

    if OpenAI is None:
        logger.warning("OpenAI request skipped: OpenAI SDK is not available")
        return None

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.responses.create(
            model=get_openai_model(),
            input=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, default=str),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": response_schema,
                }
            },
        )
        parsed_response = parse_response_json(response)

        if parsed_response is None:
            logger.warning("OpenAI response rejected: JSON parsing returned no usable content")
            return None

        if not validate(parsed_response):
            return None

        return parsed_response
    except Exception as e:
        logger.error("OpenAI request failed: %s: %s", type(e).__name__, e)
        return None


def parse_response_json(response: Any) -> dict[str, Any] | None:
    output_text = getattr(response, "output_text", None)

    if isinstance(output_text, str) and output_text.strip():
        return parse_json_text(output_text)

    output = getattr(response, "output", None)
    if not output:
        return None

    for item in output:
        content_items = getattr(item, "content", None)
        if content_items is None and isinstance(item, dict):
            content_items = item.get("content", [])

        for content_item in content_items:
            text = getattr(content_item, "text", None)
            if text is None and isinstance(content_item, dict):
                text = content_item.get("text")

            if isinstance(text, str) and text.strip():
                return parse_json_text(text)

    return None


def parse_json_text(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("OpenAI response rejected: invalid JSON: %s", exc)
        return None

    if not isinstance(parsed, dict):
        logger.warning(
            "OpenAI response rejected: expected JSON object, got %s",
            type(parsed).__name__,
        )
        return None

    return parsed


def validate_summary_payload(payload: dict[str, Any]) -> bool:
    required_fields = [
        "headline",
        "summary",
        "risks",
        "what_to_watch",
        "confidence",
        "generated_by",
        "next_update",
        "disclaimer",
    ]
    missing_fields = [field for field in required_fields if field not in payload]

    if missing_fields:
        logger.warning("OpenAI response rejected: missing fields=%s", missing_fields)
        return False

    if payload.get("generated_by") != "openai":
        logger.warning("OpenAI response rejected: generated_by is not openai")
        return False

    if not isinstance(payload.get("confidence"), (int, float)):
        logger.warning("OpenAI response rejected: confidence is not numeric")
        return False

    return True


def validate_chat_payload(payload: dict[str, Any]) -> bool:
    required_fields = [
        "type",
        "answer",
        "key_points",
        "risks",
        "what_to_watch",
        "related_symbols",
        "confidence",
        "generated_by",
        "disclaimer",
    ]
    missing_fields = [field for field in required_fields if field not in payload]

    if missing_fields:
        logger.warning("OpenAI chat response rejected: missing fields=%s", missing_fields)
        return False

    if payload.get("type") != "ai_chat_response":
        logger.warning("OpenAI chat response rejected: type is not ai_chat_response")
        return False

    if payload.get("generated_by") != "openai":
        logger.warning("OpenAI chat response rejected: generated_by is not openai")
        return False

    if not isinstance(payload.get("confidence"), (int, float)):
        logger.warning("OpenAI chat response rejected: confidence is not numeric")
        return False

    return True


AI_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "key_points": {
            "type": "array",
            "items": {"type": "string"},
        },
        "why_it_matters": {
            "type": "array",
            "items": {"type": "string"},
        },
        "opportunities": {
            "type": "array",
            "items": {"type": "string"},
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
        },
        "what_to_watch": {
            "type": "array",
            "items": {"type": "string"},
        },
        "confidence": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        },
        "generated_by": {
            "type": "string",
            "enum": ["openai"],
        },
        "next_update": {"type": "string"},
        "disclaimer": {"type": "string"},
    },
    "required": [
        "headline",
        "summary",
        "key_points",
        "why_it_matters",
        "opportunities",
        "strengths",
        "risks",
        "what_to_watch",
        "confidence",
        "generated_by",
        "next_update",
        "disclaimer",
    ],
}


AI_CHAT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "type": {
            "type": "string",
            "enum": ["ai_chat_response"],
        },
        "answer": {"type": "string"},
        "key_points": {
            "type": "array",
            "items": {"type": "string"},
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
        },
        "what_to_watch": {
            "type": "array",
            "items": {"type": "string"},
        },
        "related_symbols": {
            "type": "array",
            "items": {"type": "string"},
        },
        "confidence": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        },
        "generated_by": {
            "type": "string",
            "enum": ["openai"],
        },
        "disclaimer": {"type": "string"},
    },
    "required": [
        "type",
        "answer",
        "key_points",
        "risks",
        "what_to_watch",
        "related_symbols",
        "confidence",
        "generated_by",
        "disclaimer",
    ],
}
