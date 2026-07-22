from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.analysis_engines.session.contracts import (
    BarInterval,
    MarketCalendarConfig,
    SessionBounds,
    SessionPhase,
)


class SessionCalendarError(ValueError):
    pass


class MarketSessionCalendar:
    """Deterministic US-equity session boundaries with injected closures.

    The calendar deliberately ships with no silently changing holiday dataset.
    Production callers must inject the holiday and early-close dates covering
    their requested period; tests can therefore remain hermetic.
    """

    def __init__(self, config: MarketCalendarConfig | None = None) -> None:
        self.config = config or MarketCalendarConfig()
        self._holidays = frozenset(self.config.holidays)
        self._early_closes = dict(self.config.early_closes)
        try:
            self.timezone = ZoneInfo(self.config.timezone_name)
        except ZoneInfoNotFoundError as exc:  # pragma: no cover - host configuration
            raise SessionCalendarError("America/New_York timezone data is unavailable") from exc

    def bounds(self, session_date: date) -> SessionBounds:
        if session_date.weekday() >= 5 or session_date in self._holidays:
            return SessionBounds(
                session_date=session_date,
                is_open=False,
                timezone_name=self.config.timezone_name,
            )

        close_time = self._early_closes.get(session_date, self.config.regular_close)
        regular_open = datetime.combine(
            session_date, self.config.regular_open, tzinfo=self.timezone
        )
        regular_close = datetime.combine(session_date, close_time, tzinfo=self.timezone)
        final_hour_start = max(
            regular_open,
            regular_close - timedelta(minutes=self.config.final_hour_minutes),
        )
        close_phase_start = max(
            final_hour_start,
            regular_close - timedelta(minutes=self.config.close_phase_minutes),
        )
        return SessionBounds(
            session_date=session_date,
            is_open=True,
            is_early_close=session_date in self._early_closes,
            timezone_name=self.config.timezone_name,
            premarket_open=datetime.combine(
                session_date, self.config.premarket_open, tzinfo=self.timezone
            ),
            regular_open=regular_open,
            opening_phase_end=min(
                regular_open + timedelta(minutes=self.config.opening_phase_minutes),
                final_hour_start,
            ),
            morning_end=min(
                datetime.combine(session_date, self.config.morning_end, tzinfo=self.timezone),
                final_hour_start,
            ),
            midday_end=min(
                datetime.combine(session_date, self.config.midday_end, tzinfo=self.timezone),
                final_hour_start,
            ),
            final_hour_start=final_hour_start,
            close_phase_start=close_phase_start,
            regular_close=regular_close,
            after_hours_close=datetime.combine(
                session_date, self.config.after_hours_close, tzinfo=self.timezone
            ),
        )

    def phase_at(self, timestamp: datetime, *, session_date: date | None = None) -> SessionPhase:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise SessionCalendarError("phase timestamps must be timezone-aware")
        local = timestamp.astimezone(self.timezone)
        target_date = session_date or local.date()
        if local.date() != target_date:
            return SessionPhase.CLOSED
        bounds = self.bounds(target_date)
        if not bounds.is_open:
            return SessionPhase.CLOSED

        premarket_open = self._required(bounds.premarket_open)
        regular_open = self._required(bounds.regular_open)
        regular_close = self._required(bounds.regular_close)
        after_hours_close = self._required(bounds.after_hours_close)
        opening_phase_end = self._required(bounds.opening_phase_end)
        morning_end = self._required(bounds.morning_end)
        midday_end = self._required(bounds.midday_end)
        final_hour_start = self._required(bounds.final_hour_start)
        close_phase_start = self._required(bounds.close_phase_start)

        if premarket_open <= local < regular_open:
            return SessionPhase.PREMARKET
        if close_phase_start <= local < regular_close:
            return SessionPhase.CLOSE
        if final_hour_start <= local < close_phase_start:
            return SessionPhase.FINAL_HOUR
        if regular_open <= local < opening_phase_end:
            return SessionPhase.OPENING_PHASE
        if opening_phase_end <= local < morning_end:
            return SessionPhase.MORNING
        if morning_end <= local < midday_end:
            return SessionPhase.MIDDAY
        if midday_end <= local < final_hour_start:
            return SessionPhase.AFTERNOON
        if regular_close <= local < after_hours_close:
            return SessionPhase.AFTER_HOURS
        return SessionPhase.CLOSED

    def regular_bar_starts(
        self,
        session_date: date,
        interval: BarInterval,
        *,
        completed_through: datetime | None = None,
    ) -> tuple[datetime, ...]:
        bounds = self.bounds(session_date)
        if not bounds.is_open:
            return ()
        start = self._required(bounds.regular_open)
        close = self._required(bounds.regular_close)
        cutoff = close
        if completed_through is not None:
            if completed_through.tzinfo is None or completed_through.utcoffset() is None:
                raise SessionCalendarError("completed_through must be timezone-aware")
            cutoff = min(close, completed_through.astimezone(self.timezone))
        duration = timedelta(minutes=interval.minutes)
        values: list[datetime] = []
        cursor = start
        while cursor + duration <= cutoff:
            values.append(cursor)
            cursor += duration
        return tuple(values)

    def regular_minutes_elapsed(self, session_date: date, through: datetime) -> int:
        bounds = self.bounds(session_date)
        if not bounds.is_open:
            return 0
        if through.tzinfo is None or through.utcoffset() is None:
            raise SessionCalendarError("elapsed-time boundary must be timezone-aware")
        regular_open = self._required(bounds.regular_open)
        regular_close = self._required(bounds.regular_close)
        local = through.astimezone(self.timezone)
        cutoff = min(max(local, regular_open), regular_close)
        return max(0, int((cutoff - regular_open).total_seconds() // 60))

    @staticmethod
    def _required(value: datetime | None) -> datetime:
        if value is None:  # pragma: no cover - guarded by is_open
            raise SessionCalendarError("open session is missing a required boundary")
        return value
