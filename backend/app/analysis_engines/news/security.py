from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from app.copilot.policy import contains_prompt_injection, contains_secret
from app.intelligence.news.contracts import NewsContractModel


NEWS_SECURITY_VERSION = "news-untrusted-content-v1"
MAX_RAW_TEXT_LENGTH = 20_000
MAX_SAFE_TEXT_LENGTH = 2_000

SCRIPT_PATTERN = re.compile(r"<(?:script|iframe|object|embed)\b", re.IGNORECASE)
DANGEROUS_URL_PATTERN = re.compile(r"(?:javascript|data|file|vbscript)\s*:", re.IGNORECASE)
MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]*\)")
MARKDOWN_CONTROL_PATTERN = re.compile(r"(?:```+|`|^\s{0,3}#{1,6}\s+|^\s*>\s?)", re.MULTILINE)


class SanitizedNewsText(NewsContractModel):
    safe_text: str
    quarantined: bool
    reasons: tuple[str, ...] = ()
    truncated: bool = False
    engine_version: str = NEWS_SECURITY_VERSION


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked_depth = 0
        self.saw_markup = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.saw_markup = True
        if tag.casefold() in {"script", "style", "iframe", "object", "embed"}:
            self.blocked_depth += 1

    def handle_endtag(self, tag: str) -> None:
        self.saw_markup = True
        if tag.casefold() in {"script", "style", "iframe", "object", "embed"} and self.blocked_depth:
            self.blocked_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.blocked_depth:
            self.parts.append(data)


class NewsContentSecurityEngine:
    """Quarantine adversarial external strings before evidence or persistence."""

    version = NEWS_SECURITY_VERSION

    def sanitize(self, value: str, *, max_output: int = MAX_SAFE_TEXT_LENGTH) -> SanitizedNewsText:
        raw = str(value or "")
        reasons: list[str] = []
        if len(raw) > MAX_RAW_TEXT_LENGTH:
            reasons.append("oversized_untrusted_text")
        if contains_prompt_injection(raw):
            reasons.append("prompt_injection_detected")
        if contains_secret(raw):
            reasons.append("secret_detected")
        if SCRIPT_PATTERN.search(raw):
            reasons.append("executable_markup_detected")
        if DANGEROUS_URL_PATTERN.search(raw):
            reasons.append("dangerous_url_scheme_detected")

        parser = _PlainTextParser()
        try:
            parser.feed(raw[:MAX_RAW_TEXT_LENGTH])
            parser.close()
            plain = " ".join(parser.parts) if parser.saw_markup else raw[:MAX_RAW_TEXT_LENGTH]
        except Exception:
            plain = ""
            reasons.append("malformed_markup")
        plain = html.unescape(plain)
        plain = MARKDOWN_IMAGE_PATTERN.sub("", plain)
        plain = MARKDOWN_LINK_PATTERN.sub(r"\1", plain)
        plain = MARKDOWN_CONTROL_PATTERN.sub("", plain)
        plain = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        truncated = len(plain) > max_output
        safe = plain[:max_output].rstrip()
        quarantined = bool(reasons)
        if quarantined:
            safe = ""
        return SanitizedNewsText(
            safe_text=safe,
            quarantined=quarantined,
            reasons=tuple(dict.fromkeys(reasons)),
            truncated=truncated,
        )
