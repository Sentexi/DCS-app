from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Debate, Topic
from app.extensions import db

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
    return render_template('admin/dashboard.html', debates=debates)

# Create debate
@admin_bp.route('/admin/create_debate', methods=['GET', 'POST'])
@login_required
@admin_required
def create_debate():
    if request.method == 'POST':
        title = request.form['title']
        style = request.form['style']
        if not title or style not in ['OPD', 'BP']:
            flash('Please fill all fields correctly.', 'danger')
            return redirect(url_for('admin.create_debate'))
        debate = Debate(title=title, style=style)
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
        if not text:
            flash('Please enter a topic.', 'danger')
            return redirect(url_for('admin.add_topic', debate_id=debate_id))
        topic = Topic(text=text, debate_id=debate_id)
        db.session.add(topic)
        db.session.commit()
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
    status = "opened" if debate.voting_open else "closed"
    flash(f'Voting {status} for {debate.title}.', 'info')
    return redirect(url_for('admin.admin_dashboard'))

# Edit debate
@admin_bp.route('/admin/<int:debate_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_debate(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    if request.method == 'POST':
        title = request.form['title']
        style = request.form['style']
        if title and style in ['OPD', 'BP']:
            debate.title = title
            debate.style = style
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
        if text:
            topic.text = text
            db.session.commit()
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
    flash('Topic deleted.', 'info')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    from app.models import User
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/admin/users/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_user_admin(user_id):
    from app.models import User
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f"User '{user.username}' admin status changed.", "info")
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/admin/assign_speakers/<int:debate_id>')
@login_required
@admin_required
def assign_speakers(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    flash("Speaker assignment coming soon!", "info")
    return redirect(url_for('admin.admin_dashboard'))
