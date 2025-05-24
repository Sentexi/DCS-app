from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Debate, Topic, Vote
from app.extensions import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def dashboard():
    # Show all debates (future: filter to only "active" debates)
    debates = Debate.query.all()
    return render_template('main/dashboard.html', debates=debates)

@main_bp.route('/debate/<int:debate_id>', methods=['GET', 'POST'])
@login_required
def debate_view(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    topics = debate.topics
    # Find all this user's votes (by topic)
    user_votes = {v.topic_id for v in Vote.query.filter_by(user_id=current_user.id).all()}
    # Count total votes by user
    votes_left = 2 - Vote.query.join(Topic).filter(
        Vote.user_id == current_user.id,
        Topic.debate_id == debate_id
    ).count()

    # Handle voting
    if request.method == 'POST':
        if not debate.voting_open:
            flash('Voting is closed for this debate.')
            return redirect(url_for('main.debate_view', debate_id=debate_id))
        if votes_left <= 0:
            flash('You have used all your votes for this debate.')
            return redirect(url_for('main.debate_view', debate_id=debate_id))
        topic_id = int(request.form['topic_id'])
        if topic_id in user_votes:
            flash('You have already voted for this topic.')
            return redirect(url_for('main.debate_view', debate_id=debate_id))
        # Register vote
        vote = Vote(user_id=current_user.id, topic_id=topic_id)
        db.session.add(vote)
        db.session.commit()
        flash('Vote recorded.')
        return redirect(url_for('main.debate_view', debate_id=debate_id))

    # For result: Count votes for each topic
    vote_counts = {t.id: len(t.votes) for t in topics}
    # Find winner if voting closed
    winner = None
    if not debate.voting_open and topics:
        winner = max(topics, key=lambda t: len(t.votes))

    return render_template(
        'main/debate.html',
        debate=debate,
        topics=topics,
        user_votes=user_votes,
        votes_left=votes_left,
        voting_open=debate.voting_open,
        vote_counts=vote_counts,
        winner=winner
    )
