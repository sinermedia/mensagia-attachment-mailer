from datetime import date, datetime, time, timedelta
import pytest
from src.domain.scheduling import (
    MAX_SCHEDULE_AHEAD, MIN_START_LEAD, SECONDS_BETWEEN_EMAILS, DayPreview, SendSchedule, StartMode,
    StartTooFarError, StartTooSoonError, calculate_start_dates, default_start_time, next_ten_minute_mark,
    preview_days, send_date_skip_reason, validate_fixed_start,
)


class TestNextTenMinuteMark:
    """Tests for the next_ten_minute_mark() scheduling helper.

    Verifies that the function always returns a datetime that is:
    - strictly after the input (never equal),
    - on a 10-minute boundary (:00, :10, :20, ...),
    - correct when crossing hour or day boundaries.
    """

    def test_mid_block_rounds_up(self):
        """A time in the middle of a 10-minute block rounds up to the next mark."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 30, 0)

    def test_start_of_block_goes_to_next(self):
        """A time exactly on a 10-minute mark moves to the following mark."""
        now = datetime(2024, 1, 15, 14, 20, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 30, 0)

    def test_on_exact_mark_with_seconds_rounds_up(self):
        """A time on a mark but with non-zero seconds is treated as past that mark."""
        now = datetime(2024, 1, 15, 14, 20, 5)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 30, 0)

    def test_crosses_hour_boundary(self):
        """A time near the end of an hour correctly crosses into the next hour."""
        now = datetime(2024, 1, 15, 14, 55, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 15, 0, 0)

    def test_at_end_of_hour_crosses_next_hour(self):
        """A time at :50 with extra seconds crosses into the next hour."""
        now = datetime(2024, 1, 15, 14, 50, 30)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 15, 0, 0)

    def test_exactly_midnight(self):
        """A time near midnight correctly crosses into the next day."""
        now = datetime(2024, 1, 15, 23, 55, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 16, 0, 0, 0)

    def test_one_minute_before_end(self):
        """A time one minute before the end of a 10-minute block rounds up correctly."""
        now = datetime(2024, 1, 15, 14, 9, 59)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 10, 0)


class TestCalculateStartDates:
    """Tests for the calculate_start_dates() bulk scheduling function.

    Verifies that dates are staggered correctly, that the first slot is
    placed at least one full 10-minute block in the future, and that the
    number and order of returned dates match expectations.
    """

    def test_zero_emails_returns_empty(self):
        """Requesting 0 dates returns an empty list."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(0, now)
        assert result == []

    def test_first_email_at_second_ten_minute_mark(self):
        """The first email is scheduled at the second 10-minute mark after now."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(1, now)
        assert result[0] == datetime(2024, 1, 15, 14, 40, 0)

    def test_first_email_skips_imminent_mark(self):
        """A mark only 20 seconds away is skipped; the first email goes to the next safe mark."""
        # At 14:09:40 the next mark is 14:10 (only 20s away) — should skip to 14:20
        now = datetime(2024, 1, 15, 14, 9, 40)
        result = calculate_start_dates(1, now)
        assert result[0] == datetime(2024, 1, 15, 14, 20, 0)

    def test_second_email_is_12_seconds_after_first(self):
        """Consecutive emails are separated by exactly SECONDS_BETWEEN_EMAILS."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(2, now)
        assert result[1] == result[0] + timedelta(seconds=SECONDS_BETWEEN_EMAILS)

    def test_five_emails_per_minute_rate(self):
        """Five emails span exactly 4 × SECONDS_BETWEEN_EMAILS total."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(5, now)
        total_seconds = (result[-1] - result[0]).total_seconds()
        assert total_seconds == SECONDS_BETWEEN_EMAILS * 4

    def test_count_matches_output_length(self):
        """The returned list always has exactly as many items as requested."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        for count in [1, 5, 10, 100]:
            result = calculate_start_dates(count, now)
            assert len(result) == count

    def test_dates_are_strictly_increasing(self):
        """Every date in the list is strictly later than the previous one."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(10, now)
        for i in range(1, len(result)):
            assert result[i] > result[i - 1]


class TestCalculateStartDatesWhenResuming:
    """Tests for calculate_start_dates() when continuing an interrupted campaign.

    When the last email of a previous run is still far enough in the future,
    the new run continues right after it so the sending rhythm is preserved
    and the two runs never overlap. Otherwise the usual 10-20 minute initial
    gap is applied, exactly as for a brand-new campaign.
    """

    NOW = datetime(2024, 1, 15, 15, 5, 0)

    def test_continues_right_after_last_scheduled_when_far_in_future(self):
        """A previous last slot well in the future is followed by the next 12-second slot."""
        last = datetime(2024, 1, 15, 15, 40, 0)
        result = calculate_start_dates(2, self.NOW, last_scheduled=last)
        assert result == [
            datetime(2024, 1, 15, 15, 40, 12),
            datetime(2024, 1, 15, 15, 40, 24),
        ]

    def test_continues_when_next_slot_is_exactly_ten_minutes_ahead(self):
        """A next slot exactly 10 minutes from now is still close enough to continue."""
        last = self.NOW + timedelta(minutes=10) - timedelta(seconds=SECONDS_BETWEEN_EMAILS)
        result = calculate_start_dates(1, self.NOW, last_scheduled=last)
        assert result[0] == self.NOW + timedelta(minutes=10)

    def test_applies_initial_gap_when_next_slot_is_less_than_ten_minutes_ahead(self):
        """A next slot under 10 minutes away falls back to the second 10-minute mark."""
        last = datetime(2024, 1, 15, 15, 14, 0)
        result = calculate_start_dates(1, self.NOW, last_scheduled=last)
        assert result[0] == datetime(2024, 1, 15, 15, 20, 0)

    def test_applies_initial_gap_when_last_scheduled_is_in_the_past(self):
        """A previous last slot already in the past falls back to the second 10-minute mark."""
        last = datetime(2024, 1, 15, 14, 0, 0)
        result = calculate_start_dates(1, self.NOW, last_scheduled=last)
        assert result[0] == datetime(2024, 1, 15, 15, 20, 0)

    def test_none_last_scheduled_behaves_like_a_new_campaign(self):
        """Passing last_scheduled=None gives the same dates as not passing it at all."""
        assert calculate_start_dates(3, self.NOW, last_scheduled=None) == calculate_start_dates(3, self.NOW)

    def test_resumed_dates_never_overlap_previous_run(self):
        """Whatever the previous last slot, the first new slot is always after it."""
        for minutes in range(-30, 60):
            last = self.NOW + timedelta(minutes=minutes)
            result = calculate_start_dates(1, self.NOW, last_scheduled=last)
            assert result[0] > last


class TestDefaultStartTime:
    """Tests for default_start_time(), the first slot of the "now" start mode."""

    def test_is_the_second_ten_minute_mark(self):
        """The default start is the second 10-minute mark after now."""
        assert default_start_time(datetime(2024, 1, 15, 14, 23, 0)) == datetime(2024, 1, 15, 14, 40, 0)

    def test_matches_the_first_slot_of_a_new_campaign(self):
        """The default start is the slot calculate_start_dates() gives a new campaign."""
        now = datetime(2024, 1, 15, 14, 9, 40)
        assert default_start_time(now) == calculate_start_dates(1, now)[0]


class TestCalculateStartDatesWithFixedStart:
    """Tests for calculate_start_dates() when the user chose a fixed start date and time.

    The first email goes out at the chosen time when it still leaves the
    minimum lead; otherwise it is postponed to the "now" schedule, so an
    email is never scheduled earlier than the user asked for.
    """

    NOW = datetime(2026, 10, 8, 10, 7, 0)

    def test_starts_at_the_chosen_time(self):
        """The first email is scheduled exactly at the chosen time and the next ones 12 seconds apart."""
        start = datetime(2026, 10, 15, 9, 0, 0)
        result = calculate_start_dates(3, self.NOW, start_at=start)
        assert result == [
            datetime(2026, 10, 15, 9, 0, 0),
            datetime(2026, 10, 15, 9, 0, 12),
            datetime(2026, 10, 15, 9, 0, 24),
        ]

    def test_starts_at_the_chosen_time_exactly_ten_minutes_ahead(self):
        """A chosen time exactly 10 minutes ahead still leaves enough lead to be kept."""
        start = self.NOW + MIN_START_LEAD
        assert calculate_start_dates(1, self.NOW, start_at=start)[0] == start

    def test_postpones_a_chosen_time_less_than_ten_minutes_ahead(self):
        """A chosen time under 10 minutes away is postponed to the "now" schedule."""
        start = datetime(2026, 10, 8, 10, 15, 0)
        assert calculate_start_dates(1, self.NOW, start_at=start)[0] == datetime(2026, 10, 8, 10, 20, 0)

    def test_postpones_a_chosen_time_already_past(self):
        """A chosen time already in the past is postponed to the "now" schedule."""
        start = datetime(2026, 10, 8, 10, 0, 0)
        assert calculate_start_dates(1, self.NOW, start_at=start)[0] == datetime(2026, 10, 8, 10, 20, 0)

    def test_may_run_past_midnight(self):
        """Emails starting just before midnight continue on the next day."""
        start = datetime(2026, 10, 15, 23, 59, 48)
        result = calculate_start_dates(2, self.NOW, start_at=start)
        assert result[1] == datetime(2026, 10, 16, 0, 0, 0)

    def test_resuming_continues_after_the_previous_run(self):
        """A resumed campaign continues after its last slot rather than at the chosen time."""
        start = datetime(2026, 10, 15, 9, 0, 0)
        last = datetime(2026, 10, 15, 9, 0, 48)
        assert calculate_start_dates(1, self.NOW, last_scheduled=last, start_at=start)[0] == datetime(2026, 10, 15, 9, 1, 0)

    def test_resuming_too_late_uses_a_chosen_time_still_ahead(self):
        """When the previous run's slots are too close, a chosen time with enough lead is used."""
        start = datetime(2026, 10, 20, 9, 0, 0)
        last = datetime(2026, 10, 8, 10, 8, 0)
        assert calculate_start_dates(1, self.NOW, last_scheduled=last, start_at=start)[0] == start


class TestValidateFixedStart:
    """Tests for validate_fixed_start(), the check made when the user picks a fixed start."""

    NOW = datetime(2026, 10, 8, 10, 7, 0)

    def test_accepts_a_time_with_enough_lead(self):
        """A start more than 10 minutes ahead and within the limit is accepted."""
        validate_fixed_start(datetime(2026, 10, 15, 9, 0, 0), self.NOW)

    def test_accepts_a_time_exactly_ten_minutes_ahead(self):
        """A start exactly 10 minutes ahead is accepted."""
        validate_fixed_start(self.NOW + MIN_START_LEAD, self.NOW)

    def test_rejects_a_time_less_than_ten_minutes_ahead(self):
        """A start under 10 minutes away is rejected as too soon."""
        with pytest.raises(StartTooSoonError):
            validate_fixed_start(datetime(2026, 10, 8, 10, 16, 0), self.NOW)

    def test_rejects_a_time_in_the_past(self):
        """A start already in the past is rejected as too soon."""
        with pytest.raises(StartTooSoonError):
            validate_fixed_start(datetime(2026, 10, 7, 9, 0, 0), self.NOW)

    def test_accepts_a_time_exactly_at_the_maximum_lead(self):
        """A start exactly MAX_SCHEDULE_AHEAD away is accepted."""
        validate_fixed_start(self.NOW + MAX_SCHEDULE_AHEAD, self.NOW)

    def test_rejects_a_time_beyond_the_maximum_lead(self):
        """A start beyond MAX_SCHEDULE_AHEAD is rejected as too far."""
        with pytest.raises(StartTooFarError):
            validate_fixed_start(self.NOW + MAX_SCHEDULE_AHEAD + timedelta(minutes=1), self.NOW)

    def test_maximum_lead_is_six_weeks(self):
        """The maximum lead is six weeks."""
        assert MAX_SCHEDULE_AHEAD == timedelta(weeks=6)


class TestSendScheduleByContactDate:
    """Tests for SendSchedule with the contact date start mode.

    Each contact is sent on its own day at the chosen time, 12 seconds
    after the previous email of the same day. The rules are applied when
    each email is scheduled, with the current time of that moment.
    """

    # Thursday 8 October 2026, 10:07; the chosen time is 10:00
    NOW = datetime(2026, 10, 8, 10, 7, 0)
    TODAY = date(2026, 10, 8)
    TOMORROW = date(2026, 10, 9)
    TEN = time(10, 0)

    def schedule(self, last_by_day=None) -> SendSchedule:
        """Build a contact date schedule at 10:00, optionally resuming."""
        return SendSchedule(StartMode.CONTACT_DATE, start_time=self.TEN, last_scheduled=last_by_day)

    def test_future_day_starts_at_the_chosen_time(self):
        """The first email of a future day goes out at the chosen time of that day."""
        assert self.schedule().next_slot(self.TOMORROW, self.NOW) == datetime(2026, 10, 9, 10, 0, 0)

    def test_each_day_counts_its_own_emails(self):
        """The 12-second gap is counted per day, starting again at the chosen time each day."""
        schedule = self.schedule()
        slots = [schedule.next_slot(day, self.NOW) for day in (self.TOMORROW, date(2026, 10, 10), self.TOMORROW)]
        assert slots == [datetime(2026, 10, 9, 10, 0, 0), datetime(2026, 10, 10, 10, 0, 0), datetime(2026, 10, 9, 10, 0, 12)]

    def test_today_after_the_chosen_time_uses_the_now_schedule(self):
        """At 10:07 with 10:00 chosen, the emails of today go out at 10:20:00, 10:20:12..."""
        schedule = self.schedule()
        assert [schedule.next_slot(self.TODAY, self.NOW) for _ in range(2)] == [
            datetime(2026, 10, 8, 10, 20, 0), datetime(2026, 10, 8, 10, 20, 12),
        ]

    def test_today_with_enough_lead_uses_the_chosen_time(self):
        """The emails of today go out at the chosen time when it is at least 10 minutes ahead."""
        assert self.schedule().next_slot(self.TODAY, datetime(2026, 10, 8, 9, 50)) == datetime(2026, 10, 8, 10, 0)

    def test_today_with_less_lead_uses_the_now_schedule(self):
        """A chosen time less than 10 minutes ahead is postponed like the "now" mode."""
        assert self.schedule().next_slot(self.TODAY, datetime(2026, 10, 8, 9, 55)) == datetime(2026, 10, 8, 10, 10)

    def test_rules_use_the_time_of_each_call(self):
        """A slot that has lost its lead by the time it is scheduled is postponed then."""
        schedule = self.schedule()
        assert schedule.next_slot(self.TODAY, datetime(2026, 10, 8, 9, 49)) == datetime(2026, 10, 8, 10, 0, 0)
        assert schedule.next_slot(self.TODAY, datetime(2026, 10, 8, 9, 55)) == datetime(2026, 10, 8, 10, 10, 0)

    def test_may_run_past_midnight(self):
        """The emails of a day may continue after midnight without moving the next day."""
        schedule = SendSchedule(StartMode.CONTACT_DATE, start_time=time(23, 59, 48))
        slots = [schedule.next_slot(self.TOMORROW, self.NOW) for _ in range(2)]
        assert slots == [datetime(2026, 10, 9, 23, 59, 48), datetime(2026, 10, 10, 0, 0, 0)]
        assert schedule.next_slot(date(2026, 10, 10), self.NOW) == datetime(2026, 10, 10, 23, 59, 48)

    def test_resuming_continues_after_the_last_slot_of_each_day(self):
        """A resumed send continues each day after its last slot, and starts new days at the chosen time."""
        schedule = self.schedule({self.TOMORROW: datetime(2026, 10, 9, 10, 0, 24)})
        assert schedule.next_slot(self.TOMORROW, self.NOW) == datetime(2026, 10, 9, 10, 0, 36)
        assert schedule.next_slot(date(2026, 10, 10), self.NOW) == datetime(2026, 10, 10, 10, 0, 0)

    def test_resuming_today_without_lead_uses_the_now_schedule(self):
        """Resumed emails of today use the "now" schedule when the next slot is less than 10 minutes ahead."""
        schedule = self.schedule({self.TODAY: datetime(2026, 10, 8, 10, 0, 24)})
        assert schedule.next_slot(self.TODAY, self.NOW) == datetime(2026, 10, 8, 10, 20, 0)


class TestSendScheduleSingleStart:
    """Tests for SendSchedule with the "now" and fixed start modes, where every email shares one sequence."""

    NOW = datetime(2024, 1, 15, 14, 23, 0)

    def test_now_mode_matches_calculate_start_dates(self):
        """The "now" mode hands out the same slots as calculate_start_dates()."""
        schedule = SendSchedule(StartMode.NOW)
        assert [schedule.next_slot(None, self.NOW) for _ in range(3)] == calculate_start_dates(3, self.NOW)

    def test_fixed_mode_starts_at_the_chosen_start(self):
        """The fixed mode starts at the chosen date and time."""
        start = datetime(2024, 1, 16, 9, 0)
        schedule = SendSchedule(StartMode.FIXED, start_at=start)
        assert [schedule.next_slot(None, self.NOW) for _ in range(2)] == [start, start + timedelta(seconds=12)]

    def test_a_retry_continues_after_the_last_slot(self):
        """A later call, such as an end-of-run retry, continues after the last slot handed out."""
        schedule = SendSchedule(StartMode.NOW)
        first = schedule.next_slot(None, self.NOW)
        assert schedule.next_slot(None, self.NOW + timedelta(minutes=1)) == first + timedelta(seconds=12)

    def test_a_late_retry_uses_the_now_schedule(self):
        """A retry made when the next slot has less than 10 minutes of lead is postponed."""
        schedule = SendSchedule(StartMode.NOW)
        schedule.next_slot(None, self.NOW)
        later = datetime(2024, 1, 15, 14, 38, 0)
        assert schedule.next_slot(None, later) == default_start_time(later)


class TestSendDateSkipReason:
    """Tests for the checks of the send date of a contact against the current time."""

    NOW = datetime(2026, 10, 8, 10, 7, 0)

    def test_today_and_future_days_are_accepted(self):
        """Today and later days within the limit can be scheduled."""
        assert send_date_skip_reason(date(2026, 10, 8), time(10, 0), self.NOW) is None
        assert send_date_skip_reason(date(2026, 10, 9), time(10, 0), self.NOW) is None

    def test_past_day_is_skipped(self):
        """A day before today is skipped as past_send_date."""
        assert send_date_skip_reason(date(2026, 10, 7), time(23, 0), self.NOW) == "past_send_date"

    def test_day_beyond_the_limit_is_skipped(self):
        """A day whose chosen time is more than 6 weeks ahead is skipped as send_date_too_far."""
        last_allowed = (self.NOW + MAX_SCHEDULE_AHEAD).date()
        assert send_date_skip_reason(last_allowed, time(10, 7), self.NOW) is None
        assert send_date_skip_reason(last_allowed, time(10, 8), self.NOW) == "send_date_too_far"
        assert send_date_skip_reason(last_allowed + timedelta(days=1), time(0, 0), self.NOW) == "send_date_too_far"


class TestPreviewDays:
    """Tests for the per-day preview of a contact date send shown in the summary."""

    NOW = datetime(2026, 10, 8, 10, 7, 0)

    def test_counts_each_day_with_its_first_and_last_slot(self):
        """Each day appears once, in date order, with its number of emails and first and last slot."""
        days = [date(2026, 10, 10), date(2026, 10, 9), date(2026, 10, 10), date(2026, 10, 10)]
        assert preview_days(days, time(9, 0), self.NOW) == [
            DayPreview(date(2026, 10, 9), 1, datetime(2026, 10, 9, 9, 0, 0), datetime(2026, 10, 9, 9, 0, 0)),
            DayPreview(date(2026, 10, 10), 3, datetime(2026, 10, 10, 9, 0, 0), datetime(2026, 10, 10, 9, 0, 24)),
        ]

    def test_resumed_days_continue_after_their_last_slot(self):
        """A resumed day starts after the last slot recorded for it."""
        last = {date(2026, 10, 9): datetime(2026, 10, 9, 9, 1)}
        assert preview_days([date(2026, 10, 9)], time(9, 0), self.NOW, last)[0].first == datetime(2026, 10, 9, 9, 1, 12)

    def test_no_dates_no_days(self):
        """Without emails there is nothing to preview."""
        assert preview_days([], time(9, 0), self.NOW) == []
