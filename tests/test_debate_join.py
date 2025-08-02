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


def create_user(idx, judge_skill='Cant judge'):
    user = User(
        first_name=f'User{idx}',
        last_name='Test',
        email=f'user{idx}@example.com',
        password='pw',
        judge_skill=judge_skill,
    )
    db.session.add(user)
    db.session.commit()
    return user


def test_join_assigns_first_free_slot(client):
    gov = create_user(1)
    opp = create_user(2)
    free1_user = create_user(3)
    joiner = create_user(4, judge_skill='Wing')

    debate = Debate(title='Debate', style='OPD', active=True)
    db.session.add(debate)
    db.session.commit()

    db.session.add_all([
        SpeakerSlot(debate_id=debate.id, user_id=gov.id, role='Gov', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=opp.id, role='Opp', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=free1_user.id, role='Free-1', room=1),
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


def test_dynamic_debate_assigns_free_slot(client):
    og = create_user(1)
    oo = create_user(2)
    cg = create_user(3)
    co = create_user(4)
    gov = create_user(5)
    opp = create_user(6)
    joiner = create_user(7, judge_skill='Wing')

    debate = Debate(title='Dynamic Debate', style='Dynamic', active=True)
    db.session.add(debate)
    db.session.commit()

    db.session.add_all([
        SpeakerSlot(debate_id=debate.id, user_id=og.id, role='OG', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=oo.id, role='OO', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=cg.id, role='CG', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=co.id, role='CO', room=1),
        SpeakerSlot(debate_id=debate.id, user_id=gov.id, role='Gov', room=2),
        SpeakerSlot(debate_id=debate.id, user_id=opp.id, role='Opp', room=2),
    ])
    db.session.commit()

    login(client, joiner)
    resp = client.post(f'/debate/{debate.id}/join')
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['role'] == 'Free-1'
    assert data['room'] == 2

    slot = SpeakerSlot.query.filter_by(debate_id=debate.id, user_id=joiner.id).first()
    assert slot.role == 'Free-1'
    assert slot.room == 2
