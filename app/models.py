# app/models.py

from .extensions import db
from flask_login import UserMixin

# User model: represents app users (debaters, admins, etc.)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)  # hashed password
    is_admin = db.Column(db.Boolean, default=False)

    # Relationship: which votes has this user cast?
    votes = db.relationship('Vote', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

# Debate model: stores debate event details
class Debate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    style = db.Column(db.Enum('OPD', 'BP', name='debate_style'), nullable=False)
    voting_open = db.Column(db.Boolean, default=True)

    # Relationship: which topics belong to this debate?
    topics = db.relationship('Topic', back_populates='debate', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Debate {self.title} ({self.style})>'

# Topic model: a possible motion for a debate
class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(240), nullable=False)
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

    # Relationships
    user = db.relationship('User', back_populates='votes')
    topic = db.relationship('Topic', back_populates='votes')

    # Enforce: a user can only vote for a given topic once
    __table_args__ = (db.UniqueConstraint('user_id', 'topic_id', name='_user_topic_uc'),)

    def __repr__(self):
        return f'<Vote user={self.user_id} topic={self.topic_id}>'
