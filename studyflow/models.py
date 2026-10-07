from . import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    settings_version = db.Column(db.Integer, nullable=False, default=1)
    plan_started = db.Column(db.Boolean, nullable=False, default=False)
    repair_fingerprint = db.Column(db.String(64))
    timezone = db.Column(db.String(80), nullable=False, default="Asia/Hong_Kong")


class OwnedRecord:
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    archived = db.Column(db.Boolean, default=False, nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)


class Subject(OwnedRecord, db.Model):
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(2))
    __table_args__ = (db.UniqueConstraint('id', 'user_id'),)


class FeedbackEntry(OwnedRecord, db.Model):
    subject_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(150), nullable=False)
    teacher_text = db.Column(db.Text, nullable=False)
    overall_grade = db.Column(db.String(80))
    attachment = db.Column(db.String(80))
    __table_args__ = (
        db.ForeignKeyConstraint(['subject_id', 'user_id'], ['subject.id', 'subject.user_id']),
        db.UniqueConstraint('id', 'user_id', 'subject_id'),
    )

    @property
    def subject(self):
        return db.session.get(Subject, self.subject_id)


class Exam(OwnedRecord, db.Model):
    subject_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False)
    __table_args__ = (
        db.ForeignKeyConstraint(['subject_id', 'user_id'], ['subject.id', 'subject.user_id']),
        db.UniqueConstraint('id', 'user_id', 'subject_id'),
    )

    @property
    def subject(self):
        return db.session.get(Subject, self.subject_id)


class PracticeTarget(OwnedRecord, db.Model):
    subject_id = db.Column(db.Integer, nullable=False)
    feedback_id = db.Column(db.Integer)
    exam_id = db.Column(db.Integer)
    topic = db.Column(db.String(100), nullable=False)
    skill = db.Column(db.String(100), nullable=False, default='')
    goal = db.Column(db.String(500), nullable=False)
    start_rating = db.Column(db.String(20))
    requested_minutes = db.Column(db.Integer, nullable=False, default=60)
    deadline = db.Column(db.Date)
    created_date = db.Column(db.Date, nullable=False)
    __table_args__ = (
        db.ForeignKeyConstraint(['subject_id', 'user_id'], ['subject.id', 'subject.user_id']),
        db.ForeignKeyConstraint(['feedback_id', 'user_id', 'subject_id'],
                                ['feedback_entry.id', 'feedback_entry.user_id', 'feedback_entry.subject_id']),
        db.ForeignKeyConstraint(['exam_id', 'user_id', 'subject_id'],
                                ['exam.id', 'exam.user_id', 'exam.subject_id']),
        db.UniqueConstraint('id', 'user_id'),
        db.CheckConstraint('requested_minutes > 0 AND requested_minutes <= 1440 AND requested_minutes % 30 = 0'),
    )

    @property
    def subject(self):
        return db.session.get(Subject, self.subject_id)

    @property
    def exam(self):
        return db.session.get(Exam, self.exam_id) if self.exam_id else None


class WeeklyAvailability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    weekday = db.Column(db.Integer, nullable=False)
    minutes = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'weekday'),
                      db.CheckConstraint('weekday BETWEEN 0 AND 6'),
                      db.CheckConstraint('minutes BETWEEN 0 AND 1440'))


class DateAvailabilityOverride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    minutes = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'date'),
                      db.CheckConstraint('minutes BETWEEN 0 AND 1440'))


class EvidenceEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    target_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    rating = db.Column(db.String(20))
    source = db.Column(db.String(30), nullable=False)
    note = db.Column(db.String(1000), nullable=False, default='')
    earned = db.Column(db.Float)
    possible = db.Column(db.Float)
    session_id = db.Column(db.Integer)
    superseded = db.Column(db.Boolean, nullable=False, default=False)
    supersedes_id = db.Column(db.Integer, db.ForeignKey('evidence_entry.id'), unique=True)
    request_id = db.Column(db.String(80), nullable=False)
    payload_hash = db.Column(db.String(64), nullable=False)
    __table_args__ = (
        db.ForeignKeyConstraint(['target_id', 'user_id'], ['practice_target.id', 'practice_target.user_id']),
        db.ForeignKeyConstraint(['session_id', 'user_id'], ['study_session.id', 'study_session.user_id'], name='fk_evidence_session_owner'),
        db.UniqueConstraint('user_id', 'request_id'),
        db.Index('uq_evidence_owner_target', 'id', 'user_id', 'target_id', unique=True),
        db.CheckConstraint('(earned IS NULL AND possible IS NULL) OR (possible > 0 AND earned >= 0 AND earned <= possible)', name='ck_evidence_marks'),
    )


class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    target_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    planned_minutes = db.Column(db.Integer, nullable=False, default=30)
    actual_seconds = db.Column(db.Float, nullable=False, default=0)
    active_since = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    state = db.Column(db.String(20), nullable=False, default='planned')
    locked = db.Column(db.Boolean, nullable=False, default=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    replacement_for_id = db.Column(db.Integer, db.ForeignKey('study_session.id'), unique=True)
    reason = db.Column(db.String(250), nullable=False)
    __table_args__ = (
        db.ForeignKeyConstraint(['target_id', 'user_id'], ['practice_target.id', 'practice_target.user_id']),
        db.UniqueConstraint('id', 'user_id'),
        db.Index('uq_session_owner_target', 'id', 'user_id', 'target_id', unique=True),
        db.CheckConstraint('planned_minutes = 30'),
        db.CheckConstraint('actual_seconds >= 0'),
        db.CheckConstraint("state IN ('planned','in_progress','paused','completed','missed','skipped','cancelled')"),
    )

    @property
    def review_task_id(self):
        link = db.session.get(SessionReview, self.id)
        return link.task_id if link else None

    @property
    def review_task(self):
        return db.session.get(ReviewTask, self.review_task_id) if self.review_task_id else None

    @property
    def kind(self):
        return 'review' if self.review_task_id else 'practice'

    @property
    def target(self):
        return db.session.get(PracticeTarget, self.target_id)


class SessionEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    session_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, nullable=False)
    request_id = db.Column(db.String(100), nullable=False)
    payload_hash = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=False)
    __table_args__ = (
        db.ForeignKeyConstraint(['session_id', 'user_id'], ['study_session.id', 'study_session.user_id']),
        db.UniqueConstraint('user_id', 'request_id'),
    )


class ReviewState(db.Model):
    target_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    step = db.Column(db.Integer, nullable=False, default=-1)
    interval = db.Column(db.Integer)
    last_rated_date = db.Column(db.Date)
    recommended_due_date = db.Column(db.Date)
    awaiting_outcome = db.Column(db.Boolean, nullable=False, default=False)
    policy_version = db.Column(db.String(30), nullable=False, default='review-v1')
    outcome_fingerprint = db.Column(db.String(64))
    __table_args__ = (
        db.ForeignKeyConstraint(['target_id', 'user_id'], ['practice_target.id', 'practice_target.user_id']),
        db.CheckConstraint('step BETWEEN -1 AND 4', name='ck_review_step'),
    )


class ReviewTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    planned_minutes = db.Column(db.Integer, nullable=False, default=30)
    state = db.Column(db.String(20), nullable=False, default='pending')
    source_evidence_id = db.Column(db.Integer)
    __table_args__ = (
        db.ForeignKeyConstraint(['target_id', 'user_id'], ['practice_target.id', 'practice_target.user_id']),
        db.ForeignKeyConstraint(['source_evidence_id', 'user_id', 'target_id'],
                               ['evidence_entry.id', 'evidence_entry.user_id', 'evidence_entry.target_id']),
        db.UniqueConstraint('id', 'user_id', 'target_id'),
        db.Index('uq_pending_review_target', 'target_id', unique=True, sqlite_where=db.text("state = 'pending'")),
        db.CheckConstraint("state IN ('pending','completed','cancelled')", name='ck_review_task_state'),
        db.CheckConstraint('planned_minutes = 30', name='ck_review_task_minutes'),
    )


class SessionReview(db.Model):
    session_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    task_id = db.Column(db.Integer, nullable=False)
    __table_args__ = (
        db.ForeignKeyConstraint(['session_id', 'user_id', 'target_id'],
                               ['study_session.id', 'study_session.user_id', 'study_session.target_id']),
        db.ForeignKeyConstraint(['task_id', 'user_id', 'target_id'],
                               ['review_task.id', 'review_task.user_id', 'review_task.target_id']),
    )
