from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import distinct
import itertools
from app.models import Debate, Topic, Vote, User
from app.extensions import db
from app.logic.assign import assign_speakers, _compute_room_counts
from datetime import datetime, timedelta
from app import socketio

from . import admin_bp

# Decorator for admin-only views
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Admin dashboard: list debates, option to add
@admin_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    debates = Debate.query.all()
    # Build voter count per debate
    voter_counts = {}
    for debate in debates:
        topic_ids = [t.id for t in debate.topics]
        if topic_ids:
            # Query for unique user_ids who voted for any topic in this debate
            count = (db.session.query(Vote.user_id)
                     .filter(Vote.topic_id.in_(topic_ids))
                     .distinct()
                     .count())
        else:
            count = 0
        voter_counts[debate.id] = count
    print(voter_counts)
    return render_template("admin/dashboard.html", debates=debates, voter_counts=voter_counts)


# Create debate
@admin_bp.route('/admin/create_debate', methods=['GET', 'POST'])
@login_required
@admin_required
def create_debate():
    if request.method == 'POST':
        title = request.form['title']
        style = request.form['style']
        assignment_mode = request.form.get('assignment_mode', 'Random')
        if not title or style not in ['OPD', 'BP', 'Dynamic']:
            flash('Please fill all fields correctly.', 'danger')
            return redirect(url_for('admin.create_debate'))
        debate = Debate(title=title, style=style,
                        assignment_mode=assignment_mode, active=False)
        db.session.add(debate)
        db.session.commit()
        flash('Debate created!', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('admin/create_debate.html')

# Add topic to debate
@admin_bp.route('/admin/<int:debate_id>/add_topic', methods=['GET', 'POST'])
@login_required
@admin_required
def add_topic(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    if request.method == 'POST':
        text = request.form['text']
        factsheet = request.form.get('factsheet')
        if not text:
            flash('Please enter a topic.', 'danger')
            return redirect(url_for('admin.add_topic', debate_id=debate_id))
        topic = Topic(text=text, factsheet=factsheet, debate_id=debate_id)
        db.session.add(topic)
        db.session.commit()
        socketio.emit('topic_list_update', {'debate_id': debate_id})
        flash('Topic added.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('admin/add_topic.html', debate=debate)

# Toggle voting
@admin_bp.route('/admin/<int:debate_id>/toggle_voting')
@login_required
@admin_required
def toggle_voting(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    debate.voting_open = not debate.voting_open
    db.session.commit()
    socketio.emit('debate_status', {
        'debate_id': debate_id,
        'voting_open': debate.voting_open
    })
    socketio.emit('debate_list_update', {
        'debate_id': debate_id,
        'voting_open': debate.voting_open
    })
    status = "opened" if debate.voting_open else "closed"
    flash(f'Voting {status} for {debate.title}.', 'info')
    return redirect(url_for('admin.admin_dashboard'))

# Toggle active status
@admin_bp.route('/admin/<int:debate_id>/toggle_active')
@login_required
@admin_required
def toggle_active(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    debate.active = not debate.active
    db.session.commit()
    socketio.emit('debate_list_update', {
        'debate_id': debate_id,
        'active': debate.active
    })
    status = "activated" if debate.active else "deactivated"
    flash(f'Debate {status}.', 'info')
    return redirect(url_for('admin.admin_dashboard'))
    
@admin_bp.route('/admin/debate/<int:debate_id>/vote_stats')
@login_required
@admin_required
def vote_stats(debate_id):
    now = datetime.utcnow()
    ten_minutes_ago = now - timedelta(minutes=10)

    # Get IDs of recently active users
    active_user_ids = set(
        u.id for u in User.query.filter(User.last_seen >= ten_minutes_ago).all()
    )

    # Get IDs of users who have voted in this debate
    voted_user_ids = set(
        row[0]
        for row in db.session.query(Vote.user_id)
        .join(Topic)
        .filter(Topic.debate_id == debate_id)
        .distinct()
        .all()
    )

    # Union: all users who are either active or have voted
    eligible_user_ids = active_user_ids.union(voted_user_ids)

    total_users = len(eligible_user_ids)
    voted_users = len(voted_user_ids)

    return jsonify({
        'total_users': total_users,
        'voted_users': voted_users
    })

# Edit debate
@admin_bp.route('/admin/<int:debate_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_debate(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    if request.method == 'POST':
        title = request.form['title']
        style = request.form['style']
        assignment_mode = request.form.get('assignment_mode', debate.assignment_mode)
        if title and style in ['OPD', 'BP', 'Dynamic']:
            debate.title = title
            debate.style = style
            debate.assignment_mode = assignment_mode
            db.session.commit()
            flash('Debate updated.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        flash('Invalid input.', 'danger')
    return render_template('admin/edit_debate.html', debate=debate)

# Delete debate
@admin_bp.route('/admin/<int:debate_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_debate(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    db.session.delete(debate)
    db.session.commit()
    flash('Debate deleted.', 'info')
    return redirect(url_for('admin.admin_dashboard'))

# Edit topic
@admin_bp.route('/admin/topic/<int:topic_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if request.method == 'POST':
        text = request.form['text']
        factsheet = request.form.get('factsheet')
        if text:
            topic.text = text
            topic.factsheet = factsheet
            db.session.commit()
            socketio.emit('topic_list_update', {'debate_id': topic.debate_id})
            flash('Topic updated.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        flash('Invalid input.', 'danger')
    return render_template('admin/edit_topic.html', topic=topic)

# Delete topic
@admin_bp.route('/admin/topic/<int:topic_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    db.session.delete(topic)
    db.session.commit()
    socketio.emit('topic_list_update', {'debate_id': topic.debate_id})
    flash('Topic deleted.', 'info')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    from app.models import User
    users = User.query.all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/admin/pending_users')
@login_required
@admin_required
def manage_pending_users():
    from app.models import PendingUser
    pending = PendingUser.query.all()
    return render_template('admin/pending_users.html', pending_users=pending)


@admin_bp.route('/admin/pending_users/<int:pending_id>/confirm', methods=['POST'])
@login_required
@admin_required
def confirm_pending_user(pending_id):
    from app.models import PendingUser, User
    p = PendingUser.query.get_or_404(pending_id)
    user = User(first_name=p.first_name, last_name=p.last_name, email=p.email, password=p.password)
    db.session.add(user)
    db.session.delete(p)
    db.session.commit()
    flash('User confirmed.', 'success')
    return redirect(url_for('admin.manage_pending_users'))


@admin_bp.route('/admin/pending_users/<int:pending_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_pending_user(pending_id):
    from app.models import PendingUser
    p = PendingUser.query.get_or_404(pending_id)
    db.session.delete(p)
    db.session.commit()
    flash('Pending user deleted.', 'info')
    return redirect(url_for('admin.manage_pending_users'))

@admin_bp.route('/admin/users/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_user_admin(user_id):
    from app.models import User
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f"User '{user.first_name} {user.last_name}' admin status changed.", "info")
    return redirect(url_for('admin.manage_users'))
    
@admin_bp.route('/admin/<int:debate_id>/assign', methods=['POST'])
@login_required
def run_assign(debate_id):
    if not current_user.is_admin:
        flash("Admin rights required.", "danger")
        return redirect(url_for('main.dashboard'))

    from app.models import Debate, User
    debate = Debate.query.get_or_404(debate_id)
    # Option: Only assign users who registered or are eligible
    # Subquery: all topic IDs for this debate
    topic_ids_subq = db.session.query(Topic.id).filter(Topic.debate_id == debate.id).subquery()

    # Main query: all users who have a vote on one of these topics
    users = User.query.join(Vote, User.id == Vote.user_id) \
                      .filter(Vote.topic_id.in_(topic_ids_subq)) \
                      .distinct().all()

    # Clean up previous assignments for this debate if re-running
    from app.models import SpeakerSlot
    SpeakerSlot.query.filter_by(debate_id=debate.id).delete()
    db.session.commit()

    scenario = request.form.get('scenario')
    mode = request.form.get('assignment_mode')
    if mode:
        debate.assignment_mode = mode
        db.session.commit()
    ok, msg = assign_speakers(debate, users, scenario=scenario)
    flash(msg, "success" if ok else "danger")
    if ok:
        socketio.emit('assignments_ready', {'debate_id': debate_id})
    return redirect(url_for('admin.admin_dashboard'))


# Display dynamic planning for a Dynamic debate
@admin_bp.route('/admin/<int:debate_id>/dynamic_plan')
@login_required
@admin_required
def dynamic_plan(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    if debate.voting_open:
        flash('Voting must be closed before planning rooms.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    topic_ids_subq = db.session.query(Topic.id).filter(Topic.debate_id == debate.id).subquery()
    users = User.query.join(Vote, User.id == Vote.user_id) \
                      .filter(Vote.topic_id.in_(topic_ids_subq)) \
                      .distinct().all()

    groups = {}
    for u in users:
        skill = u.debate_skill or 'Unknown'
        groups.setdefault(skill, []).append(u)

    total = len(users)
    chair_count = sum(1 for u in users if u.judge_skill == 'Chair')
    def eligible_chair(u):
        if getattr(u, 'judge_skill', '') == 'Chair':
            return True
        if getattr(u, 'judge_skill', '') == 'Wing' and getattr(u, 'debate_skill', '') != 'First Timer':
            return True
        return getattr(u, 'debate_skill', '') != 'First Timer'
    fallback_chair_count = sum(1 for u in users if eligible_chair(u))

    scenarios = []
    room_types = {'O': ('OPD', 7, 12), 'B': ('BP', 9, 11)}

    max_rooms = min(5, total // 7) if total else 1

    def opd_breakdown(n):
        extra = max(n - 7, 0)
        wing = 1 if extra > 0 else 0
        free = min(max(n - 8, 0), 3)
        speakers = 6 + free
        judges = n - speakers
        return f'{speakers} speakers, {judges} judges'

    def bp_breakdown(n):
        wings = min(max(n - 9, 0), 3)
        speakers = 8
        judges = 1 + wings
        return f'{speakers} speakers, {judges} judges'

    for num_rooms in range(1, max_rooms + 1):
        for combo in itertools.product('OB', repeat=num_rooms):
            spec = [room_types[c] for c in combo]
            counts = _compute_room_counts(total, [(s[1], s[2]) for s in spec])
            if not counts:
                continue
            safe = chair_count >= num_rooms
            if not safe and fallback_chair_count < num_rooms:
                continue
            desc = ' + '.join(room_types[c][0] for c in combo)
            if not safe:
                desc += ' (unsafe - using fallback Chairs)'
            breakdown = []
            for c, count in zip(combo, counts):
                if c == 'O':
                    breakdown.append(opd_breakdown(count))
                else:
                    breakdown.append(bp_breakdown(count))
            scenarios.append({
                'id': '-'.join(c for c in combo),
                'desc': desc,
                'safe': safe,
                'breakdown': breakdown
            })

    return render_template('admin/dynamic_plan.html',
                           debate=debate,
                           groups=groups,
                           scenarios=scenarios)


