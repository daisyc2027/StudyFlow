from datetime import date, datetime, timedelta, timezone

from hypothesis import given, seed, settings, strategies as st

from studyflow.services.review import RatedPractice, replay


def sample(i, rating='confident', day=7, hour=12, superseded=False):
    return RatedPractice(i, i, datetime(2030, 1, day, hour, tzinfo=timezone.utc), rating, superseded)


def test_initial_transitions_and_hand_calculated_dates():
    assert replay([], 'Asia/Hong_Kong').step == -1
    assert replay([sample(1, None)], 'UTC').due_date is None
    result = replay([sample(1), sample(2, day=8), sample(3, day=11)], 'UTC')
    assert [(h.interval, h.due_date) for h in result.history] == [
        (1, date(2030, 1, 8)), (3, date(2030, 1, 11)), (7, date(2030, 1, 18))]
    helped = replay([sample(1), sample(2, day=8), sample(3, day=11), sample(4, 'developing', 18)], 'UTC')
    assert helped.step == 1 and helped.due_date == date(2030, 1, 21)
    reset = replay([sample(1), sample(2, day=8), sample(3, day=11), sample(4, 'needs', 18)], 'UTC')
    assert reset.step == 0 and reset.due_date == date(2030, 1, 19)
    for rating in ['needs', 'developing', 'confident']:
        assert replay([sample(1, rating)], 'UTC').interval == 1


def test_daily_winner_correction_replay_and_timezone():
    values = [sample(1), sample(2, 'needs', hour=13), sample(3, day=8)]
    result = replay(values, 'UTC')
    assert [h.evidence_id for h in result.history] == [2, 3]
    assert result.interval == 3
    corrected = [sample(1), sample(2, 'needs', hour=13, superseded=True), sample(3, day=8),
                 RatedPractice(4, 2, sample(2, hour=13).completed_at, 'confident')]
    assert replay(corrected, 'UTC').interval == 3
    assert replay(reversed(corrected), 'UTC') == replay(corrected, 'UTC')
    boundary = [sample(1, hour=16), sample(2, day=8, hour=1)]
    assert len(replay(boundary, 'Asia/Hong_Kong').history) == 1
    assert len(replay(boundary, 'UTC').history) == 2
    assert replay(boundary, 'Asia/Hong_Kong').due_date == date(2030, 1, 9)
    ties = [RatedPractice(9, 1, sample(1).completed_at, 'needs'), sample(2)]
    assert replay(ties, 'UTC').source_id == 2  # stable session ID before evidence ID


@seed(7102030)
@settings(max_examples=150, deadline=None)
@given(st.lists(st.sampled_from(['needs', 'developing', 'confident', None]), max_size=60))
def test_replay_bounds_daily_limit_and_determinism(ratings):
    base = datetime(2030, 1, 1, tzinfo=timezone.utc)
    values = [RatedPractice(i, i, base + timedelta(hours=12*i), r) for i, r in enumerate(ratings)]
    result = replay(values, 'Asia/Hong_Kong')
    assert -1 <= result.step <= 4
    assert len({h.practice_date for h in result.history}) == len(result.history)
    assert all(h.interval in [1, 3, 7, 14, 30] and h.due_date > h.practice_date for h in result.history)
    assert replay(reversed(values), 'Asia/Hong_Kong') == result
    capped = replay([RatedPractice(i, i, base + timedelta(days=i), 'confident') for i in range(20)], 'UTC')
    assert capped.step == 4 and capped.interval == 30
