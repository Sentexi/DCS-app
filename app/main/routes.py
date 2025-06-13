from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app.models import Debate, Topic, Vote
from app.models import Debate, SpeakerSlot, User
from app.extensions import db
from app import socketio
from datetime import datetime, timedelta


from . import main_bp

@main_bp.route('/')
@login_required
def dashboard():
    # Redirect to survey if user hasn't filled it out
    if not current_user.date_joined_choice:
        return redirect(url_for('auth.survey'))

    # Get all debates, newest first
    debates = Debate.query.order_by(Debate.id.desc()).all()
    open_debates = [d for d in debates if d.voting_open]
    current_debate = open_debates[0] if len(open_debates) == 1 else None

    # Initialize vote statistics and user role
    vote_percent = votes_cast = votes_total = user_role = None

    if current_debate:
        # Get topic IDs for this debate
        topic_ids = [t.id for t in current_debate.topics]
        # Get all votes for these topics
        votes = Vote.query.filter(Vote.topic_id.in_(topic_ids)).all()
        voter_ids = set(v.user_id for v in votes)
        votes_cast = len(voter_ids)

        now = datetime.utcnow()
        ten_minutes_ago = now - timedelta(minutes=10)

        # Count only users who are recently active or have voted
        active_user_ids = set(
            u.id for u in User.query.filter(User.last_seen >= ten_minutes_ago).all()
        )
        eligible_user_ids = active_user_ids.union(voter_ids)
        votes_total = len(eligible_user_ids)
        vote_percent = int((votes_cast / votes_total) * 100) if votes_total else 0

        # Find this user's speaker role (if assigned)
        slot = SpeakerSlot.query.filter_by(debate_id=current_debate.id, user_id=current_user.id).first()
        if slot:
            user_role = f"{slot.role} in Room {slot.room}" if slot.room else slot.role

    # Categorize debates for UI tabs or display
    active_debates = [d for d in debates if d.voting_open and (not current_debate or d.id != current_debate.id)]
    past_debates = [d for d in debates if not d.voting_open and d.assignment_complete]
    upcoming_debates = [d for d in debates if not d.voting_open and not d.assignment_complete]

    return render_template(
        'main/dashboard.html',
        current_debate=current_debate,
        vote_percent=vote_percent,
        votes_cast=votes_cast,
        votes_total=votes_total,
        user_role=user_role,
        active_debates=active_debates,
        past_debates=past_debates,
        upcoming_debates=upcoming_debates,
        debates=debates,
        single_open=current_debate,
    )


@main_bp.route('/debate/<int:debate_id>', methods=['GET', 'POST'])
@login_required
def debate_view(debate_id):
    if not current_user.date_joined_choice:
        return redirect(url_for('auth.survey'))

    debate = Debate.query.options(joinedload(Debate.speakerslots)).get_or_404(debate_id)
    topics = debate.topics  # adjust as needed

    # voting logic
    if request.method == 'POST' and debate.voting_open:
        topic_id = int(request.form.get('topic_id'))
        # Check if user already voted for this topic
        existing_vote = Vote.query.filter_by(user_id=current_user.id, topic_id=topic_id).first()
        # Count how many topics user already voted for in this debate
        user_votes_in_debate = Vote.query.join(Topic).filter(
            Vote.user_id == current_user.id,
            Topic.debate_id == debate_id
        ).count()
        if existing_vote:
            flash('You have already voted for this topic.', 'warning')
        elif user_votes_in_debate >= 2:
            flash('You can only vote for up to 2 topics per debate.', 'danger')
        else:
            # Bump debate_count if this is their first vote in this debate
            
            if user_votes_in_debate == 0:
                if current_user.debate_count is None:
                    current_user.debate_count = 0
                current_user.debate_count += 1
            vote = Vote(user_id=current_user.id, topic_id=topic_id)
            db.session.add(vote)
            db.session.commit()
            
            # -- live vote update start --
            now = datetime.utcnow()
            ten_minutes_ago = now - timedelta(minutes=10)

            active_user_ids = set(
                u.id for u in User.query.filter(User.last_seen >= ten_minutes_ago).all()
            )
            voted_user_ids = set(
                row[0]
                for row in db.session.query(Vote.user_id)
                .join(Topic)
                .filter(Topic.debate_id == debate_id)
                .distinct()
                .all()
            )
            eligible_user_ids = active_user_ids.union(voted_user_ids)
            total_users = len(eligible_user_ids)
            voted_users = len(voted_user_ids)

            socketio.emit('vote_update', {
                'debate_id': debate_id,
                'vote_data': {
                    'total_users': total_users,
                    'voted_users': voted_users
                }
            })
            # -- live vote update end --
            
            flash('Your vote has been cast!', 'success')
        return redirect(url_for('main.debate_view', debate_id=debate_id))

    # Prepare user vote info for template
    user_votes = [vote.topic_id for vote in Vote.query.filter_by(user_id=current_user.id).all()]
    votes_left = 2 - Vote.query.join(Topic).filter(
        Vote.user_id == current_user.id,
        Topic.debate_id == debate_id
    ).count()

    return render_template('main/debate.html',
                           debate=debate,
                           topics=topics,
                           user_votes=user_votes,
                           votes_left=votes_left)
                           
@main_bp.route('/debate/<int:debate_id>/assignments')
@login_required
def debate_assignments(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    slots = SpeakerSlot.query.filter_by(debate_id=debate_id).all()
    # Optionally group by room for split debates
    slots_by_room = {}
    for slot in slots:
        slots_by_room.setdefault(slot.room, []).append(slot)
    # Get users by id for lookup
    user_map = {u.id: u for u in User.query.filter(User.id.in_([s.user_id for s in slots])).all()}
    return render_template('main/debate_assignments.html',
                           debate=debate,
                           slots_by_room=slots_by_room,
                           user_map=user_map)

@main_bp.route('/debate/<int:debate_id>/topics_json')
@login_required
def debate_topics_json(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    topics = [{'id': t.id, 'text': t.text} for t in debate.topics]
    return jsonify({'topics': topics})

@main_bp.route('/debate/<int:debate_id>/assignments_json')
@login_required
def debate_assignments_json(debate_id):
    slots = SpeakerSlot.query.filter_by(debate_id=debate_id).all()
    assignments = [
        {
            'role': s.role,
            'room': s.room,
            'user_id': s.user_id,
            'username': s.user.username
        } for s in slots
    ]
    return jsonify({'assignments': assignments})

@main_bp.route('/debate/<int:debate_id>/graphic')
@login_required
def debate_graphic(debate_id):
    from sqlalchemy.orm import joinedload
    debate = Debate.query.options(
        joinedload(Debate.speakerslots),
        joinedload(Debate.topics)
    ).get_or_404(debate_id)

    if not debate.assignment_complete:
        flash('Speaker assignments are not complete for this debate.', 'warning')
        return redirect(url_for('main.debate_view', debate_id=debate_id))

    # Find current user's slot
    my_slot = SpeakerSlot.query.filter_by(debate_id=debate_id, user_id=current_user.id).first()

    # For admins, allow seeing all, otherwise restrict access
    if not my_slot and not current_user.is_admin:
        flash('You are not assigned to this debate.', 'danger')
        return redirect(url_for('main.debate_view', debate_id=debate_id))

    # Group slots by room (for multi-room support)
    slots_by_room = {}
    for slot in debate.speakerslots:
        slots_by_room.setdefault(slot.room, []).append(slot)

    return render_template(
        'main/graphic.html',
        debate=debate,
        slots_by_room=slots_by_room,
        my_slot=my_slot,
        user=current_user
    )
