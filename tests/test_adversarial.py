from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from hypothesis import given, seed, settings, strategies as st

from conftest import post, token, register
from test_inputs import add_subject, add_target, weekly
from test_adaptation import setup_plan, session_action
from test_evidence_priority import evidence_data
from studyflow import create_app, db
from studyflow.models import StudySession, PracticeTarget, EvidenceEntry, User, SessionEvent, WeeklyAvailability
from studyflow.services.scheduler import Target, Booking, ACTIVE, IMMUTABLE, allocate
from studyflow.services.repair import repair_plan
from scripts.benchmark import enumerate_legal, violations, evaluation

DAY = date(2030, 1, 7)


@seed(7072030)
@settings(max_examples=200, deadline=None)
@given(st.lists(st.tuples(st.integers(1, 6), st.integers(0, 100), st.integers(0, 7)), min_size=1, max_size=5),
       st.lists(st.integers(0, 120), min_size=7, max_size=7),
       st.lists(st.integers(0, 120), min_size=7, max_size=7),
       st.lists(st.integers(0, 4), min_size=1, max_size=20), st.booleans())
def test_random_repair_conservation_and_immutability(data, before_cap, after_cap, statuses, evidence_only):
    targets = [Target(i, blocks * 30, score, DAY + timedelta(days=deadline))
               for i, (blocks, score, deadline) in enumerate(data, 1)]
    original_cap = {DAY + timedelta(days=i): c for i, c in enumerate(before_cap)}
    changed_cap = {DAY + timedelta(days=i): c for i, c in enumerate(after_cap)}
    initial = allocate(DAY, targets, original_cap, [])
    bookings = []
    for i, a in enumerate(initial.assignments, 1):
        state = statuses[(i - 1) % len(statuses)]
        bookings.append(Booking(i, a.target_id, a.date,
            ['planned', 'planned', 'completed', 'in_progress', 'paused'][state], state == 1))
    changed_targets = [replace(t, priority=100 - t.priority,
                               deadline=t.deadline - timedelta(days=2),
                               budget=max(30, t.budget - 30)) for t in targets]
    result = repair_plan(DAY, changed_targets, changed_cap, bookings, evidence_only=evidence_only)
    cancelled = {i for i, _ in result.cancelled}
    protected = [b for b in bookings if b.state in IMMUTABLE or b.locked]
    assert not cancelled.intersection(b.id for b in protected)
    assert len(cancelled) <= sum(b.state == 'planned' and not b.locked for b in bookings)
    assert len(result.assignments) <= 336
    retained = [b for b in bookings if b.id not in cancelled]
    final = retained + [Booking(-i, a.target_id, a.date) for i, a in enumerate(result.assignments, 1)]
    for original in protected:
        assert original in final
    used, fixed_used = Counter(), Counter()
    completed, reserved, fixed_reserved = Counter(), Counter(), Counter()
    for b in final:
        if b.state in ACTIVE or b.state == 'completed':
            used[b.date] += b.minutes
        if b.state == 'completed':
            completed[b.target_id] += b.minutes
        if b.state in ACTIVE:
            reserved[b.target_id] += b.minutes
    for b in protected:
        fixed_used[b.date] += b.minutes
        if b.state in ACTIVE:
            fixed_reserved[b.target_id] += b.minutes
    for d, amount in used.items():
        if fixed_used[d] > changed_cap.get(d, 0):
            assert amount == fixed_used[d] and result.plan.conflicts
        else:
            assert amount <= changed_cap.get(d, 0)
    unmet = {u.target_id: u.minutes for u in result.plan.unallocated}
    by_id = {t.id: t for t in changed_targets}
    for t in changed_targets:
        outstanding = max(0, t.budget - completed[t.id])
        if fixed_reserved[t.id] > outstanding:
            assert reserved[t.id] == fixed_reserved[t.id] and result.plan.conflicts
        else:
            assert outstanding == reserved[t.id] + unmet.get(t.id, 0)
    for a in result.assignments:
        assert a.date >= DAY and a.date <= by_id[a.target_id].deadline
    for b in retained:
        if b not in protected:
            assert b.date <= by_id[b.target_id].deadline


@seed(7172030)
@settings(max_examples=25, deadline=None)
@given(st.lists(st.tuples(st.sampled_from(['override', 'outcome', 'advance', 'miss', 'lock']),
                         st.integers(0, 2)), min_size=1, max_size=6))
def test_random_database_repair_sequences(actions):
    with TemporaryDirectory(prefix='studyflow-property-') as directory:
        clock = [datetime(2030, 1, 7, 12, tzinfo=timezone.utc)]
        app = create_app({'TESTING': True, 'SECRET_KEY': 'property-only',
                         'SQLALCHEMY_DATABASE_URI': f'sqlite:///{Path(directory) / "test.sqlite"}',
                         'UPLOAD_FOLDER': str(Path(directory) / 'uploads'), 'CLOCK': lambda: clock[0]})
        with app.app_context():
            db.create_all()
        a, b = app.test_client(), app.test_client()
        register(a, 'property-a@example.test')
        add_subject(a, 'Synthetic A subject')
        for topic in ['Algebra', 'Graphs', 'Evaluation']:
            add_target(a, topic=topic)
        weekly(a, 30)
        post(a, '/plan/generate')
        register(b, 'property-b@example.test')
        add_subject(b, 'Synthetic private B subject')
        add_target(b, subject_id=2, topic='Private B goal')
        for name, value in actions:
            local_day = (clock[0] + timedelta(hours=8)).date()
            if name == 'override':
                assert post(a, '/settings', {'action': 'override', 'date': str(local_day), 'minutes': str(value * 30)}).status_code == 302
            elif name == 'outcome':
                with app.app_context():
                    version = db.session.get(PracticeTarget, 1).version
                assert post(a, '/target/1/evidence', evidence_data(version=version, date=str(local_day),
                           rating=['needs','developing','confident'][value])).status_code == 302
            elif name == 'advance':
                clock[0] += timedelta(days=1)
            else:
                a.get('/plan')
                with app.app_context():
                    query = db.select(StudySession).where(StudySession.user_id == 1, StudySession.state == 'planned')
                    if name == 'miss':
                        query = query.where(StudySession.date == local_day)
                    session = db.session.scalar(query.order_by(StudySession.id))
                    values = (session.id, session.version, session.locked) if session else None
                if values:
                    identifier, version, locked = values
                    assert session_action(a, identifier, 'miss' if name == 'miss' else 'unlock' if locked else 'lock', version)[0].status_code == 302
            a.get('/plan')
            with app.app_context():
                sessions = list(db.session.scalars(db.select(StudySession).where(StudySession.user_id == 1)))
                signature = [(s.id, s.target_id, s.date, s.state, s.locked) for s in sessions]
                for target in db.session.scalars(db.select(PracticeTarget).where(PracticeTarget.user_id == 1)):
                    completed = sum(s.planned_minutes for s in sessions if s.target_id == target.id and s.state == 'completed')
                    reserved = sum(s.planned_minutes for s in sessions if s.target_id == target.id and s.state in ACTIVE)
                    assert reserved <= max(0, target.requested_minutes - completed)
                assert db.session.get(PracticeTarget, 4).requested_minutes == 60
                assert db.session.get(PracticeTarget, 4).version == 1
                assert not list(db.session.scalars(db.select(StudySession).where(StudySession.user_id == 2)))
            assert 'Private B goal' not in a.get('/targets').text
            a.get('/plan')
            with app.app_context():
                assert [(s.id, s.target_id, s.date, s.state, s.locked) for s in db.session.scalars(
                    db.select(StudySession).where(StudySession.user_id == 1))] == signature
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


def test_concurrent_double_completion(user, app):
    setup_plan(user, budget='30')
    session_action(user, 1, 'start', 1)
    csrf = token(user)
    cookie = user.get_cookie('session').value
    data = {'csrf_token': csrf, 'action': 'complete', 'version': '2', 'request_id': str(uuid4()),
            'rating': 'needs'}
    def submit(_):
        client = app.test_client()
        client.set_cookie('session', cookie)
        return client.post('/session/1', data=data).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(submit, range(2))) == [302, 302]
    with app.app_context():
        assert db.session.query(EvidenceEntry).count() == 1
        assert db.session.query(StudySession).count() == 1
        assert db.session.get(StudySession, 1).state == 'completed'
        assert db.session.query(SessionEvent).filter_by(request_id=data['request_id']).count() == 1


def test_stale_settings_csrf_and_archive_retry(user, app):
    add_subject(user)
    old_token = token(user, '/settings')
    old = {'csrf_token': old_token, 'settings_version': '1', 'action': 'weekly',
           **{f'day_{i}': '60' for i in range(7)}}
    assert user.post('/settings', data=old).status_code == 302
    assert user.post('/settings', data={**old, 'day_0': '0'}).status_code == 409
    assert user.post('/settings', data={**old, 'csrf_token': 'forged', 'settings_version': '2'}).status_code == 400
    with app.app_context():
        assert db.session.scalar(db.select(WeeklyAvailability).where(WeeklyAvailability.weekday == 0)).minutes == 60
        assert db.session.get(User, 1).settings_version == 2
    post(user, '/archive/subject/1')
    post(user, '/archive/subject/1')
    with app.app_context():
        from studyflow.models import Subject
        assert db.session.get(Subject, 1).version == 2


def test_tiny_oracle_and_independent_checker():
    tomorrow = DAY + timedelta(days=1)
    targets = [Target(1, 30, 42, DAY), Target(2, 30, 70, None)]
    capacity = {DAY: 30, tomorrow: 30}
    legal = enumerate_legal(targets, capacity)
    assert max(len(p) for p in legal) == 2
    assert ((1, DAY), (2, tomorrow)) in legal
    for p in legal:
        assert violations(targets, capacity, p) == 0
    assert violations(targets, capacity, [(1, tomorrow)]) == 1
    assert violations(targets, capacity, [(1, DAY), (2, DAY)]) == 1
    assert violations(targets, {DAY: 90}, [(2, DAY), (2, DAY)]) == 1
    result = allocate(DAY, targets, capacity, [])
    placements = tuple((a.target_id, a.date) for a in result.assignments)
    assert placements in legal and len(placements) == 1
    rows = evaluation()
    assert rows[2]['fifo_initial']['remaining_minutes'] == 0
    assert rows[2]['adaptive_initial']['remaining_minutes'] == 30
    assert rows[2]['heuristic_allocation_gap_minutes'] == 30
    assert rows[3]['adaptive_after_change']['hard_violations'] == 0
    assert rows[3]['fifo_nonadaptive_after_change']['hard_violations'] > 0


def test_additional_tiny_oracle_fixtures():
    fixtures = [([Target(1, 30, 50, DAY)], {DAY: 29}, 0),
                ([Target(1, 60, 50, DAY)], {DAY: 60}, 2),
                ([Target(1, 30, 50, DAY), Target(2, 30, 50, DAY)], {DAY: 30}, 1)]
    for targets, capacity, expected in fixtures:
        legal = enumerate_legal(targets, capacity)
        assert max(len(p) for p in legal) == expected
        assert all(violations(targets, capacity, p) == 0 for p in legal)


def test_csrf_all_mutations_leave_records_unchanged(user, app):
    setup_plan(user)
    paths = ['/edit/subject', '/edit/feedback', '/edit/exam', '/edit/target', '/archive/target/1',
             '/settings', '/target/1/evidence', '/session/1', '/target/1/add-practice',
             '/plan/generate', '/logout']
    with app.app_context():
        before = [(s.id, s.state, s.version) for s in db.session.scalars(db.select(StudySession))]
    for path in paths:
        assert user.post(path, data={'csrf_token': 'invalid', 'action': 'complete'}).status_code == 400
    with app.app_context():
        assert [(s.id, s.state, s.version) for s in db.session.scalars(db.select(StudySession))] == before
        assert db.session.query(PracticeTarget).count() == 1
        assert db.session.query(EvidenceEntry).count() == 0
        assert db.session.get(User, 1).settings_version == 2
    assert user.get('/').status_code == 200


def test_add_practice_foreign_id_isolation(two_users):
    a, b = two_users
    add_subject(b)
    add_target(b)
    assert post(a, '/target/1/add-practice', {'version': '1'}).status_code == 404
