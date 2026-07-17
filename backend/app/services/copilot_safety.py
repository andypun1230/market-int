from typing import Any


SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "bearer",
    "cookie",
    "password",
    "secret",
    "token",
}

FINANCIAL_DISCLAIMER = "Educational market decision support only, not financial advice."


def asks_for_personalized_advice(message: str) -> bool:
    lowered = message.lower()
    phrases = [
        "should i buy",
        "should i sell",
        "how much should i invest",
        "what should i buy",
        "what should i sell",
        "buy now",
        "sell now",
        "is it a buy",
        "is it a sell",
        "use options",
    ]
    return any(phrase in lowered for phrase in phrases)


def remove_sensitive_values(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(secret in normalized for secret in SENSITIVE_KEYS):
                continue
            cleaned[str(key)] = remove_sensitive_values(item)
        return cleaned
    if isinstance(value, list):
        return [remove_sensitive_values(item) for item in value]
    return value
