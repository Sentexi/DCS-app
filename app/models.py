# app/models.py

from .extensions import db
from flask_login import UserMixin
from enum import Enum
from datetime import datetime

class JoinTimeEnum(db.Enum):
    first = 'first'
    less2m = '<2m'
    less6m = '2m-6m'
    less1y = '6m-1y'
    less2y = '1y-2y'
    more2y = '>2y'

class JudgeChoiceEnum(db.Enum):
    no = 'no'
    wing = 'wing'
    chair = 'chair'

class DebateSkillEnum(db.Enum):
    first_timer = 'First Timer'
    beginner = 'Beginner'
    intermediate = 'Intermediate'
    advanced = 'Advanced'
    expert = 'Expert'

class JudgeSkillEnum(db.Enum):
    cant_judge = 'Cant judge'
    wing = 'Wing'
    chair = 'Chair'

# Assignment mode for distributing speakers
class AssignmentModeEnum(db.Enum):
    true_random = 'True random'
    random = 'Random'
    skill_based = 'Skill based'
    pro_am = 'ProAm'


class PendingUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# User model: represents app users (debaters, admins, etc.)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)  # hashed password
    is_admin = db.Column(db.Boolean, default=False)
    date_joined_choice = db.Column(db.String(16), nullable=True)   # stores survey radio answer
    judge_choice = db.Column(db.String(8), nullable=True)          # stores survey radio answer
    languages = db.Column(db.String(64), nullable=True)            # comma separated list of languages
    debate_skill = db.Column(db.String(24), nullable=True)
    judge_skill = db.Column(db.String(16), nullable=True)
    debate_count = db.Column(db.Integer, default=0)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    elo_rating = db.Column(db.Integer, default=1000)
    elo_sigma = db.Column(db.Float, default=1000/3)
    opd_skill = db.Column(db.Float, nullable=True)

    # Relationship: which votes has this user cast?
    votes = db.relationship('Vote', back_populates='user', cascade='all, delete-orphan')
    slots = db.relationship('SpeakerSlot', backref='user', lazy='dynamic')
    opd_results = db.relationship('OpdResult', backref='user', lazy='dynamic')
    elo_logs = db.relationship('EloLog', backref='user', lazy='dynamic')
    
    def get_slot_for_debate(self, debate_id):
        from app.models import SpeakerSlot
        return SpeakerSlot.query.filter_by(debate_id=debate_id, user_id=self.id).first()

    def recent_opd_results(self, n=5):
        return (
            OpdResult.query.join(Debate, OpdResult.debate_id == Debate.id)
            .filter(
                OpdResult.user_id == self.id,
                Debate.style == "OPD"
            )
            .order_by(OpdResult.id.desc())
            .limit(n)
            .all()
        )

    def opd_skill_level(self, n=5):
        results = self.recent_opd_results(n)
        if not results:
            return None
        return sum(r.points for r in results) / len(results)

    def update_opd_skill(self, n=5):
        results = (
            OpdResult.query.join(Debate, OpdResult.debate_id == Debate.id)
            .filter(
                OpdResult.user_id == self.id,
                Debate.style == "OPD"
            )
            .order_by(OpdResult.id.desc())
            .limit(n)
            .all()
        )
        if len(results) < n:
            self.opd_skill = None
        else:
            self.opd_skill = sum(r.points for r in results) / n
        return len(results)

    def opd_result_count(self):
        return (
            OpdResult.query.join(Debate, OpdResult.debate_id == Debate.id)
            .filter(
                OpdResult.user_id == self.id,
                Debate.style == "OPD"
            )
            .count()
        )

    def __repr__(self):
        return f'<User {self.first_name} {self.last_name}>'

# Debate model: stores debate event details
class Debate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    style = db.Column(
        db.Enum('OPD', 'BP', 'Dynamic', name='debate_style'),
        nullable=False
    )
    assignment_mode = db.Column(
        db.Enum(
            'True random',
            'Random',
            'Skill based',
            'ProAm',
            name='assignment_mode'
        ),
        default='Random'
    )
    voting_open = db.Column(db.Boolean, default=True)
    second_voting_open = db.Column(db.Boolean, default=False)
    second_voting_topics = db.Column(db.String, nullable=True)
    active = db.Column(db.Boolean, default=False)

    # Relationship: which topics belong to this debate?
    topics = db.relationship('Topic', back_populates='debate', cascade='all, delete-orphan')
    slots = db.relationship('SpeakerSlot', backref='debate', lazy='dynamic')
    speakerslots = db.relationship(
        'SpeakerSlot', backref='debate_ref', lazy=True, cascade="all, delete-orphan"
    )
    
    assignment_complete = db.Column(db.Boolean, default=False)

    def second_topic_ids(self):
        if not self.second_voting_topics:
            return []
        return [int(tid) for tid in self.second_voting_topics.split(',') if tid]

    def second_topics(self):
        ids = set(self.second_topic_ids())
        return [t for t in self.topics if t.id in ids]

    def __repr__(self):
        return f'<Debate {self.title} ({self.style})>'

# Topic model: a possible motion for a debate
class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(240), nullable=False)
    factsheet = db.Column(db.Text, nullable=True)
    debate_id = db.Column(db.Integer, db.ForeignKey('debate.id'), nullable=False)

    # Relationship: back to debate
    debate = db.relationship('Debate', back_populates='topics')

    # Relationship: votes for this topic
    votes = db.relationship('Vote', back_populates='topic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Topic {self.text[:30]}...>'

# Vote model: represents a user's vote for a topic
class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    round = db.Column(db.Integer, default=1)

    # Relationships
    user = db.relationship('User', back_populates='votes')
    topic = db.relationship('Topic', back_populates='votes')

    # Enforce: a user can only vote for a given topic once
    __table_args__ = (
        db.UniqueConstraint('user_id', 'topic_id', 'round', name='_user_topic_round_uc'),
    )

    def __repr__(self):
        return f'<Vote user={self.user_id} topic={self.topic_id}>'

JOIN_SKILL = {
    'first': 'First Timer',
    '<2m': 'Beginner',
    '2m-6m': 'Beginner',
    '6m-1y': 'Intermediate',
    '1y-2y': 'Advanced',
    '>2y': 'Expert'
}
JUDGE_SKILL = {
    'no': 'Cant judge',
    'wing': 'Wing',
    'chair': 'Chair'
}

def apply_skills(user):
    user.debate_skill = JOIN_SKILL.get(user.date_joined_choice, 'First Timer')
    user.judge_skill = JUDGE_SKILL.get(user.judge_choice, 'Cant judge')
    
class SpeakerSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    debate_id = db.Column(db.Integer, db.ForeignKey('debate.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(32), nullable=False)    # e.g. "Gov-1", "Judge-Chair"
    room = db.Column(db.Integer, default=1)            # For split debates (1 or 2)
    # Ensure each user is only assigned once per debate per room
    __table_args__ = (db.UniqueConstraint('debate_id', 'user_id', 'room', name='_debate_user_room_uc'),)


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    debate_id = db.Column(db.Integer, db.ForeignKey('debate.id'), nullable=False)
    speaker_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    judge_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    value = db.Column(db.Integer, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('debate_id', 'speaker_id', 'judge_id', name='score_unique'),
    )


class BpRank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    debate_id = db.Column(db.Integer, db.ForeignKey('debate.id'), nullable=False)
    team = db.Column(db.String(8), nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('debate_id', 'team', name='bp_rank_unique'),
    )


class OpdResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    debate_id = db.Column(db.Integer, db.ForeignKey('debate.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points = db.Column(db.Float)
    __table_args__ = (
        db.UniqueConstraint('debate_id', 'user_id', name='opd_result_unique'),
    )


class EloLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    debate_id = db.Column(db.Integer, db.ForeignKey('debate.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    old_elo = db.Column(db.Float, nullable=False)
    new_elo = db.Column(db.Float, nullable=False)
    change = db.Column(db.Float, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('debate_id', 'user_id', name='elo_log_unique'),
    )
