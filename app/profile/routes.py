from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import OpdResult, Debate, EloLog, SpeakerSlot, BpRank, User
from app.debate.routes import infer_room_style
from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload
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


@profile_bp.route('/profile/debate/<int:debate_id>/results')
@login_required
def debate_results(debate_id):
    debate = Debate.query.options(
        joinedload(Debate.speakerslots)
    ).get_or_404(debate_id)

    slots_by_room = {}
    for slot in debate.speakerslots:
        slots_by_room.setdefault(slot.room, []).append(slot)

    room_styles = {}
    for room, slots in slots_by_room.items():
        room_styles[room] = infer_room_style(debate.style, slots)

    user_ids = [s.user_id for s in debate.speakerslots]
    user_map = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}

    opd_points = {
        r.user_id: r.points for r in OpdResult.query.filter_by(debate_id=debate_id).all()
    }

    gov_total = {}
    opp_total = {}
    for room, slots in slots_by_room.items():
        if room_styles[room] != 'OPD':
            continue
        gov_total[room] = sum(opd_points.get(s.user_id, 0) for s in slots if s.role.startswith('Gov'))
        opp_total[room] = sum(opd_points.get(s.user_id, 0) for s in slots if s.role.startswith('Opp'))

    bp_ranks = {r.team: r.rank for r in BpRank.query.filter_by(debate_id=debate_id).all()}

    return render_template(
        'profile/debate_results.html',
        debate=debate,
        slots_by_room=slots_by_room,
        room_styles=room_styles,
        user_map=user_map,
        opd_points=opd_points,
        gov_total=gov_total,
        opp_total=opp_total,
        bp_ranks=bp_ranks,
    )
