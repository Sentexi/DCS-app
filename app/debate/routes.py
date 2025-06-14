from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Debate, SpeakerSlot, Score, BpRank

from . import debate_bp


def get_chair_slot(user, debate_id):
    """Return chair slot for a user in a debate or None."""
    return SpeakerSlot.query.filter_by(
        debate_id=debate_id,
        user_id=user.id,
        role='Judge-Chair'
    ).first()


@debate_bp.route('/debate/<int:debate_id>/judging', methods=['GET', 'POST'])
@login_required
def judging(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    if not debate.active:
        flash('This debate is inactive.', 'warning')
        return redirect(url_for('main.debate_view', debate_id=debate_id))
    chair_slot = get_chair_slot(current_user, debate_id)
    if not chair_slot:
        flash('Only the chair judge can access this page.', 'danger')
        return redirect(url_for('main.debate_view', debate_id=debate_id))

    room = chair_slot.room

    judges = SpeakerSlot.query.filter(
        SpeakerSlot.debate_id == debate_id,
        SpeakerSlot.room == room,
        SpeakerSlot.role.startswith('Judge')
    ).all()

    if debate.style == 'BP':
        if request.method == 'POST':
            BpRank.query.filter_by(debate_id=debate_id).delete()
            for team in ['OG', 'OO', 'CG', 'CO']:
                val = request.form.get(f'rank_{team}')
                if val:
                    db.session.add(BpRank(debate_id=debate_id, team=team, rank=int(val)))
            db.session.commit()
            flash('Rankings saved.', 'success')
            return redirect(url_for('debate.judging', debate_id=debate_id))
        existing = {r.team: r.rank for r in BpRank.query.filter_by(debate_id=debate_id).all()}
        return render_template('debate/judging_bp.html', debate=debate, existing=existing)

    speakers = SpeakerSlot.query.filter(
        SpeakerSlot.debate_id == debate_id,
        SpeakerSlot.room == room,
        ~SpeakerSlot.role.startswith('Judge')
    ).all()
    speaker_ids = [sp.user_id for sp in speakers]
    judge_ids = [j.user_id for j in judges]

    if request.method == 'POST':
        Score.query.filter(
            Score.debate_id == debate_id,
            Score.speaker_id.in_(speaker_ids),
            Score.judge_id.in_(judge_ids)
        ).delete(synchronize_session=False)
        for sp in speakers:
            for j in judges:
                key = f'score_{sp.id}_{j.id}'
                val = request.form.get(key)
                if val:
                    db.session.add(Score(
                        debate_id=debate_id,
                        speaker_id=sp.user_id,
                        judge_id=j.user_id,
                        value=int(val)
                    ))
        db.session.commit()
        flash('Scores saved.', 'success')
        return redirect(url_for('debate.judging', debate_id=debate_id))
    scores = {
        (s.speaker_id, s.judge_id): s.value
        for s in Score.query.filter(
            Score.debate_id == debate_id,
            Score.speaker_id.in_(speaker_ids),
            Score.judge_id.in_(judge_ids)
        ).all()
    }
    return render_template('debate/judging_opd.html', debate=debate, judges=judges, speakers=speakers, scores=scores)
