from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import OpdResult, Debate, EloLog, SpeakerSlot, BpRank
from app.debate.routes import infer_room_style
from sqlalchemy.sql import func
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

    results = (
        OpdResult.query.filter_by(user_id=current_user.id)
        .order_by(OpdResult.id.desc())
        .limit(20)
        .all()
    )

    recent_debates = []
    for res in results:
        debate = Debate.query.get(res.debate_id)
        log = EloLog.query.filter_by(
            debate_id=res.debate_id, user_id=current_user.id
        ).first()
        change = log.change if log else 0
        rank = None
        win = None

        slot = SpeakerSlot.query.filter_by(
            debate_id=res.debate_id, user_id=current_user.id
        ).first()
        role = slot.role.split('-')[0] if slot else None

        style = debate.style
        if slot:
            room_slots = SpeakerSlot.query.filter_by(
                debate_id=res.debate_id, room=slot.room
            ).all()
            style = infer_room_style(debate.style, room_slots)

        if style == "BP":
            team = role
            if team:
                bp = BpRank.query.filter_by(
                    debate_id=res.debate_id, team=team
                ).first()
                if bp:
                    rank = bp.rank
        elif style == "OPD" and role in ("Gov", "Opp"):
            gov_total = (
                db.session.query(func.sum(OpdResult.points))
                .join(
                    SpeakerSlot,
                    (OpdResult.debate_id == SpeakerSlot.debate_id)
                    & (OpdResult.user_id == SpeakerSlot.user_id),
                )
                .filter(
                    OpdResult.debate_id == res.debate_id,
                    SpeakerSlot.role.startswith("Gov"),
                )
                .scalar()
                or 0
            )
            opp_total = (
                db.session.query(func.sum(OpdResult.points))
                .join(
                    SpeakerSlot,
                    (OpdResult.debate_id == SpeakerSlot.debate_id)
                    & (OpdResult.user_id == SpeakerSlot.user_id),
                )
                .filter(
                    OpdResult.debate_id == res.debate_id,
                    SpeakerSlot.role.startswith("Opp"),
                )
                .scalar()
                or 0
            )
            if gov_total != opp_total:
                winning = "Gov" if gov_total > opp_total else "Opp"
                win = role == winning

        recent_debates.append(
            {
                "debate": debate,
                "points": res.points,
                "elo_change": change,
                "rank": rank,
                "win": win,
                "style": style,
            }
        )

    return render_template('profile/view.html', opd_result_count=opd_result_count, recent_debates=recent_debates)
