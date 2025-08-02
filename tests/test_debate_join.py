import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import create_app, db
from app.models import User, Debate, SpeakerSlot


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SERVER_NAME='example.com',
        WTF_CSRF_ENABLED=False,
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def create_user(idx, judge_skill='Cant judge', prefer_judging=False):
    user = User(
        first_name=f'User{idx}',
        last_name='Test',
        email=f'user{idx}@example.com',
        password='pw',
        judge_skill=judge_skill,
        prefer_judging=prefer_judging,
    )
    db.session.add(user)
    db.session.commit()
    return user


def test_join_assigns_free_slot_after_judges_filled(client):
    gov = create_user(1)
    opp = create_user(2)
    free1_user = create_user(3)
    judge1 = create_user(4, judge_skill='Chair')
    judge2 = create_user(5, judge_skill='Wing')
    joiner = create_user(6, judge_skill='Wing')

    debate = Debate(title='Debate', style='OPD', active=True)
    db.session.add(debate)
    db.session.commit()

    db.session.add_all([
        SpeakerSlot(debate_id=debate.id, user_id=gov.id, role='Gov', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=opp.id, role='Opp', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=free1_user.id, role='Free-1', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=judge1.id, role='Judge-Chair', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=judge2.id, role='Judge-Wing', room=1),
    ])
    db.session.commit()

    login(client, joiner)
    resp = client.post(f'/debate/{debate.id}/join')
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['role'] == 'Free-2'
    assert data['room'] == 1

    slot = SpeakerSlot.query.filter_by(debate_id=debate.id, user_id=joiner.id).first()
    assert slot.role == 'Free-2'
    assert slot.room == 1


def test_join_assigns_judge_when_needed(client):
    gov = create_user(1)
    opp = create_user(2)
    free1 = create_user(3)
    free2 = create_user(4)
    free3 = create_user(5)
    chair = create_user(6, judge_skill='Chair')
    joiner = create_user(7, judge_skill='Wing')

    debate = Debate(title='Debate', style='OPD', active=True)
    db.session.add(debate)
    db.session.commit()

    db.session.add_all([
        SpeakerSlot(debate_id=debate.id, user_id=gov.id, role='Gov', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=opp.id, role='Opp', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=free1.id, role='Free-1', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=free2.id, role='Free-2', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=free3.id, role='Free-3', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=chair.id, role='Judge-Chair', room=1),
    ])
    db.session.commit()

    login(client, joiner)
    resp = client.post(f'/debate/{debate.id}/join')
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['role'] == 'Judge-Wing'
    assert data['room'] == 1

    slot = SpeakerSlot.query.filter_by(debate_id=debate.id, user_id=joiner.id).first()
    assert slot.role == 'Judge-Wing'
    assert slot.room == 1


def test_join_prefers_judge_when_flagged(client):
    gov = create_user(1)
    opp = create_user(2)
    free1 = create_user(3)
    chair = create_user(4, judge_skill='Chair')
    joiner = create_user(5, judge_skill='Wing', prefer_judging=True)

    debate = Debate(title='Debate', style='OPD', active=True)
    db.session.add(debate)
    db.session.commit()

    db.session.add_all([
        SpeakerSlot(debate_id=debate.id, user_id=gov.id, role='Gov', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=opp.id, role='Opp', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=free1.id, role='Free-1', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=chair.id, role='Judge-Chair', room=1),
    ])
    db.session.commit()

    login(client, joiner)
    resp = client.post(f'/debate/{debate.id}/join')
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['role'] == 'Judge-Wing'
    assert data['room'] == 1

    slot = SpeakerSlot.query.filter_by(debate_id=debate.id, user_id=joiner.id).first()
    assert slot.role == 'Judge-Wing'
    assert slot.room == 1


def test_join_balances_judges_before_speakers(client):
    gov = create_user(1)
    opp = create_user(2)
    free1 = create_user(3)
    chair = create_user(4, judge_skill='Chair')
    joiner = create_user(5, judge_skill='Wing')

    debate = Debate(title='Debate', style='OPD', active=True)
    db.session.add(debate)
    db.session.commit()

    db.session.add_all([
        SpeakerSlot(debate_id=debate.id, user_id=gov.id, role='Gov', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=opp.id, role='Opp', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=free1.id, role='Free-1', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=chair.id, role='Judge-Chair', room=1),
    ])
    db.session.commit()

    login(client, joiner)
    resp = client.post(f'/debate/{debate.id}/join')
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['role'] == 'Judge-Wing'
    assert data['room'] == 1

    slot = SpeakerSlot.query.filter_by(debate_id=debate.id, user_id=joiner.id).first()
    assert slot.role == 'Judge-Wing'
    assert slot.room == 1


def test_join_prefer_judge_even_with_two_judges(client):
    gov = create_user(1)
    opp = create_user(2)
    free1 = create_user(3)
    chair = create_user(4, judge_skill='Chair')
    wing1 = create_user(5, judge_skill='Wing')
    joiner = create_user(6, judge_skill='Wing', prefer_judging=True)

    debate = Debate(title='Debate', style='OPD', active=True)
    db.session.add(debate)
    db.session.commit()

    db.session.add_all([
        SpeakerSlot(debate_id=debate.id, user_id=gov.id, role='Gov', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=opp.id, role='Opp', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=free1.id, role='Free-1', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=chair.id, role='Judge-Chair', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=wing1.id, role='Judge-Wing', room=1),
    ])
    db.session.commit()

    login(client, joiner)
    resp = client.post(f'/debate/{debate.id}/join')
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['role'] == 'Judge-Wing'
    assert data['room'] == 1

    slot = SpeakerSlot.query.filter_by(debate_id=debate.id, user_id=joiner.id).first()
    assert slot.role == 'Judge-Wing'
    assert slot.room == 1
