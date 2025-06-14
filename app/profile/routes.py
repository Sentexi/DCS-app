from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import OpdResult, Debate, EloLog, SpeakerSlot, BpRank
from . import profile_bp

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def view():
    if request.method == 'POST':
        # Allow editing name and email only
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        if first_name and first_name != current_user.first_name:
            current_user.first_name = first_name
        if last_name is not None and last_name != current_user.last_name:
            current_user.last_name = last_name
        if email and email != current_user.email:
            current_user.email = email
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('profile.view'))

    opd_result_count = current_user.opd_result_count()

    results = OpdResult.query.filter_by(user_id=current_user.id).order_by(
        OpdResult.id.desc()
    ).limit(20).all()
    recent_debates = []
    for res in results:
        debate = Debate.query.get(res.debate_id)
        log = EloLog.query.filter_by(debate_id=res.debate_id, user_id=current_user.id).first()
        change = log.change if log else 0
        rank = None
        if debate.style == 'BP':
            slot = SpeakerSlot.query.filter_by(debate_id=res.debate_id, user_id=current_user.id).first()
            team = slot.role.split('-')[0] if slot else None
            if team:
                bp = BpRank.query.filter_by(debate_id=res.debate_id, team=team).first()
                if bp:
                    rank = bp.rank
        recent_debates.append({'debate': debate, 'points': res.points, 'elo_change': change, 'rank': rank})

    return render_template('profile/view.html', opd_result_count=opd_result_count, recent_debates=recent_debates)
