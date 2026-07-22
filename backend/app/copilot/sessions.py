from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Iterable

from app.copilot.contracts import (
    CopilotEntityV1,
    CopilotEntityType,
    CopilotIntentType,
    CopilotIntentV1,
    CopilotReasoningV1,
    CopilotSessionContextV1,
)


class CopilotSessionStore:
    """Bounded, process-local storage for compact conversational continuity.

    The store retains resolved identifiers and the prior stance, never raw
    prompts, full answers, prices, credentials, or user-supplied market data.
    """

    def __init__(self, *, maximum_sessions: int = 500, ttl_seconds: int = 21_600) -> None:
        self.maximum_sessions = max(1, maximum_sessions)
        self.ttl = timedelta(seconds=max(60, ttl_seconds))
        self._items: OrderedDict[str, CopilotSessionContextV1] = OrderedDict()
        self._lock = RLock()

    def get(self, thread_id: str | None) -> CopilotSessionContextV1 | None:
        key = self._key(thread_id)
        if not key:
            return None
        with self._lock:
            self._prune()
            item = self._items.get(key)
            if item is None:
                return None
            self._items.move_to_end(key)
            return item.model_copy(deep=True)

    def resolve(
        self,
        thread_id: str | None,
        explicit_context: CopilotSessionContextV1 | None = None,
    ) -> CopilotSessionContextV1 | None:
        """Merge client continuity hints with the authoritative server state.

        A client can legitimately restore compact context after a server
        restart, but it must not replace a newer server-side base intent with
        ``FOLLOW_UP``.  The returned ``updated_at`` is always the server
        revision when one exists so :meth:`save` can reject late completions.
        """

        key = self._key(thread_id or (explicit_context.thread_id if explicit_context else None))
        if not key:
            return None
        with self._lock:
            self._prune()
            stored = self._items.get(key)
            if stored is not None:
                self._items.move_to_end(key)
            resolved = _merge_contexts(stored, explicit_context, thread_id=key)
            return resolved.model_copy(deep=True) if resolved else None

    def save(
        self,
        *,
        thread_id: str,
        intent: CopilotIntentV1,
        reasoning: CopilotReasoningV1,
        evidence_ids: Iterable[str],
        current_screen: str | None = None,
        current_route: str | None = None,
        latest_report_id: str | None = None,
        previous_context: CopilotSessionContextV1 | None = None,
        reject_stale: bool = False,
    ) -> CopilotSessionContextV1:
        key = self._key(thread_id)
        if not key:
            raise ValueError("thread_id is required")
        with self._lock:
            self._prune()
            stored_context = self._items.get(key)
            if reject_stale and not _matches_expected_context(stored_context, previous_context):
                # A cancelled request can finish after its retry.  Its answer
                # may still be delivered to that caller, but it must not roll
                # the shared thread context back to the revision it started
                # from.
                if stored_context is not None:
                    self._items.move_to_end(key)
                    return stored_context.model_copy(deep=True)

            prior = _merge_contexts(stored_context, previous_context, thread_id=key)
            entities = list(intent.entities[:8]) or list(prior.active_entities[:8] if prior else [])
            stocks = [item.symbol for item in entities if item.entity_type == "stock" and item.symbol]
            groups = [item.entity_id for item in entities if item.entity_type in {"sector", "theme"}]
            active_intent = intent.intent
            if intent.intent == CopilotIntentType.FOLLOW_UP and prior and prior.active_intent:
                # FOLLOW_UP describes the current utterance, not the analytical
                # subject carried by the compact session.  Retain that subject so
                # a sequence such as "Why?" -> "What confirms it?" continues to
                # route to the stock/risk engines instead of falling back to Report.
                if prior.active_intent != CopilotIntentType.FOLLOW_UP:
                    active_intent = prior.active_intent
            context = CopilotSessionContextV1(
                thread_id=key,
                active_entities=entities,
                active_intent=active_intent,
                latest_referenced_stock=stocks[-1] if stocks else (prior.latest_referenced_stock if prior else None),
                latest_referenced_sector_or_theme=groups[-1] if groups else (prior.latest_referenced_sector_or_theme if prior else None),
                latest_report_id=latest_report_id or (prior.latest_report_id if prior else None),
                latest_thesis=reasoning.thesis[:500] if reasoning.thesis else None,
                unresolved_question=intent.clarification_question,
                previous_answer_stance=reasoning.stance,
                relevant_evidence_ids=list(dict.fromkeys(evidence_ids))[:24],
                current_screen=(current_screen or (prior.current_screen if prior else "") or "")[:80] or None,
                current_route=(current_route or (prior.current_route if prior else "") or "")[:160] or None,
                # Never derive a server revision from an untrusted client
                # timestamp.  Only the currently stored revision participates
                # in the monotonicity check.
                updated_at=_next_updated_at(stored_context),
            )
            self._items[key] = context
            self._items.move_to_end(key)
            while len(self._items) > self.maximum_sessions:
                self._items.popitem(last=False)
            return context.model_copy(deep=True)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _prune(self) -> None:
        cutoff = datetime.now(timezone.utc) - self.ttl
        expired: list[str] = []
        for key, value in self._items.items():
            try:
                updated = datetime.fromisoformat(value.updated_at.replace("Z", "+00:00"))
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
            except ValueError:
                expired.append(key)
                continue
            if updated < cutoff:
                expired.append(key)
        for key in expired:
            self._items.pop(key, None)

    @staticmethod
    def _key(thread_id: str | None) -> str:
        return "".join(character for character in str(thread_id or "") if character.isalnum() or character in "-_:.")[:128]


_SESSION_STORE = CopilotSessionStore()


def get_copilot_session_store() -> CopilotSessionStore:
    return _SESSION_STORE


def _merge_contexts(
    stored: CopilotSessionContextV1 | None,
    explicit: CopilotSessionContextV1 | None,
    *,
    thread_id: str,
) -> CopilotSessionContextV1 | None:
    if stored is None and explicit is None:
        return None
    if stored is None:
        return explicit.model_copy(update={"thread_id": thread_id}, deep=True) if explicit else None
    if explicit is None:
        return stored.model_copy(update={"thread_id": thread_id}, deep=True)

    entities: list[CopilotEntityV1] = []
    seen: set[tuple[str, str]] = set()
    # Server state is authoritative; explicit context can restore missing hints
    # but cannot reorder an older entity ahead of the active server entity.
    for item in [*stored.active_entities, *explicit.active_entities]:
        identity = (str(item.entity_type), item.entity_id.casefold())
        if identity in seen:
            continue
        seen.add(identity)
        entities.append(item)
        if len(entities) >= 8:
            break

    active_intent = stored.active_intent
    if not active_intent or active_intent == CopilotIntentType.FOLLOW_UP:
        if explicit.active_intent and explicit.active_intent != CopilotIntentType.FOLLOW_UP:
            active_intent = explicit.active_intent
    return stored.model_copy(
        update={
            "thread_id": thread_id,
            "active_entities": entities,
            "active_intent": active_intent,
            "latest_referenced_stock": stored.latest_referenced_stock or explicit.latest_referenced_stock,
            "latest_referenced_sector_or_theme": (
                stored.latest_referenced_sector_or_theme or explicit.latest_referenced_sector_or_theme
            ),
            "latest_report_id": stored.latest_report_id or explicit.latest_report_id,
            "latest_thesis": stored.latest_thesis or explicit.latest_thesis,
            "unresolved_question": stored.unresolved_question or explicit.unresolved_question,
            "previous_answer_stance": stored.previous_answer_stance or explicit.previous_answer_stance,
            "relevant_evidence_ids": list(
                dict.fromkeys([*stored.relevant_evidence_ids, *explicit.relevant_evidence_ids])
            )[:24],
            "current_screen": stored.current_screen or explicit.current_screen,
            "current_route": stored.current_route or explicit.current_route,
            # This is the optimistic-concurrency token used by save().
            "updated_at": stored.updated_at,
        },
        deep=True,
    )


def _matches_expected_context(
    stored: CopilotSessionContextV1 | None,
    expected: CopilotSessionContextV1 | None,
) -> bool:
    if stored is None:
        return True
    if expected is None:
        return False
    return stored.updated_at == expected.updated_at


def _next_updated_at(prior: CopilotSessionContextV1 | None) -> str:
    now = datetime.now(timezone.utc)
    if prior:
        try:
            previous = datetime.fromisoformat(prior.updated_at.replace("Z", "+00:00"))
            if previous.tzinfo is None:
                previous = previous.replace(tzinfo=timezone.utc)
            if now <= previous:
                now = previous + timedelta(microseconds=1)
        except ValueError:
            pass
    return now.isoformat()


def coerce_session_context(
    value: CopilotSessionContextV1 | dict[str, Any] | None,
    *,
    thread_id: str | None = None,
) -> CopilotSessionContextV1 | None:
    """Accept the public compact session shape without trusting arbitrary fields."""

    if isinstance(value, CopilotSessionContextV1):
        return value.model_copy(deep=True)
    if not isinstance(value, dict):
        return None
    entities: list[CopilotEntityV1] = []
    raw_entities = value.get("activeEntities") or value.get("active_entities") or []
    for item in raw_entities[:8] if isinstance(raw_entities, list) else []:
        if not isinstance(item, dict):
            continue
        entity_id = item.get("entityId") or item.get("entity_id") or item.get("id")
        entity_type = item.get("entityType") or item.get("entity_type") or item.get("type")
        if not entity_id or not entity_type:
            continue
        try:
            kind = CopilotEntityType(entity_type)
        except ValueError:
            continue
        symbol = item.get("symbol")
        if kind == CopilotEntityType.STOCK and not symbol:
            symbol = str(entity_id).upper()
        entities.append(
            CopilotEntityV1(
                entity_id=str(entity_id),
                entity_type=kind,
                display_name=str(item.get("displayName") or item.get("display_name") or entity_id),
                symbol=str(symbol).upper() if symbol else None,
                confidence=min(1, max(0, float(item.get("confidence") or 1))),
                resolution_source="session",
            )
        )
    payload = {
        "thread_id": str(value.get("threadId") or value.get("thread_id") or thread_id or "")[:128],
        "active_entities": entities,
        "active_intent": value.get("activeIntent") or value.get("active_intent"),
        "latest_referenced_stock": value.get("latestReferencedStock") or value.get("latest_referenced_stock"),
        "latest_referenced_sector_or_theme": value.get("latestReferencedSectorOrTheme") or value.get("latest_referenced_sector_or_theme"),
        "latest_report_id": value.get("latestReportId") or value.get("latest_report_id"),
        "latest_thesis": value.get("latestThesis") or value.get("latest_thesis"),
        "unresolved_question": value.get("unresolvedQuestion") or value.get("unresolved_question"),
        "previous_answer_stance": value.get("previousAnswerStance") or value.get("previous_answer_stance"),
        "relevant_evidence_ids": [str(item) for item in (value.get("relevantEvidenceIds") or value.get("relevant_evidence_ids") or [])[:24]],
        "current_screen": value.get("currentScreen") or value.get("current_screen"),
        "current_route": value.get("currentRoute") or value.get("current_route"),
        "updated_at": value.get("updatedAt") or value.get("updated_at") or datetime.now(timezone.utc).isoformat(),
    }
    if not payload["thread_id"]:
        return None
    try:
        return CopilotSessionContextV1.model_validate(payload)
    except Exception:
        return None
