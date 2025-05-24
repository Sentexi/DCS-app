from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Debate, Topic, Vote
from app.extensions import db


from . import main_bp 

@main_bp.route('/')
@login_required
def dashboard():
    if not current_user.date_joined_choice:
        return redirect(url_for('auth.survey'))

    debates = Debate.query.all()
    # Find open debates
    open_debates = [debate for debate in debates if debate.voting_open]
    single_open = open_debates[0] if len(open_debates) == 1 else None
    return render_template('main/dashboard.html', debates=debates, single_open=single_open)


@main_bp.route('/debate/<int:debate_id>', methods=['GET', 'POST'])
@login_required
def debate_view(debate_id):
    if not current_user.date_joined_choice:
        return redirect(url_for('auth.survey'))

    debate = Debate.query.get_or_404(debate_id)
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
                current_user.debate_count += 1
            vote = Vote(user_id=current_user.id, topic_id=topic_id)
            db.session.add(vote)
            db.session.commit()
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
