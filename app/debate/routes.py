from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (
    Debate,
    SpeakerSlot,
    Score,
    BpRank,
    OpdResult,
    EloLog,
    User,
)
from app.logic.elo import compute_bp_elo

from . import debate_bp


def infer_room_style(debate_style, speaker_slots):
    """Infer the debating style for a set of slots within a dynamic debate."""
    style = debate_style
    if debate_style == "Dynamic":
        roles = {sp.role.split("-")[0] for sp in speaker_slots}
        opd_markers = {"Gov", "Opp"}
        if roles & opd_markers or any(r.startswith("Free") for r in roles):
            style = "OPD"
        else:
            style = "BP"
    return style


def get_chair_slot(user, debate_id):
    """Return chair slot for a user in a debate or None."""
    return SpeakerSlot.query.filter_by(
        debate_id=debate_id, user_id=user.id, role="Judge-Chair"
    ).first()


@debate_bp.route("/debate/<int:debate_id>/judging", methods=["GET", "POST"])
@login_required
def judging(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    if not debate.active:
        flash("This debate is inactive.", "warning")
        return redirect(url_for("main.debate_view", debate_id=debate_id))
    chair_slot = get_chair_slot(current_user, debate_id)
    if not chair_slot:
        flash("Only the chair judge can access this page.", "danger")
        return redirect(url_for("main.debate_view", debate_id=debate_id))

    room = chair_slot.room

    speakers = SpeakerSlot.query.filter(
        SpeakerSlot.debate_id == debate_id,
        SpeakerSlot.room == room,
        ~SpeakerSlot.role.startswith("Judge"),
    ).all()

    judges = SpeakerSlot.query.filter(
        SpeakerSlot.debate_id == debate_id,
        SpeakerSlot.room == room,
        SpeakerSlot.role.startswith("Judge"),
    ).all()

    room_style = infer_room_style(debate.style, speakers)

    if room_style == "BP":
        if request.method == "POST":
            BpRank.query.filter_by(debate_id=debate_id).delete()
            for team in ["OG", "OO", "CG", "CO"]:
                val = request.form.get(f"rank_{team}")
                if val:
                    db.session.add(
                        BpRank(
                            debate_id=debate_id,
                            team=team,
                            rank=int(val),
                        )
                    )
            db.session.commit()
            flash("Rankings saved.", "success")
            return redirect(url_for("debate.judging", debate_id=debate_id))
        existing = {
            r.team: r.rank for r in BpRank.query.filter_by(debate_id=debate_id).all()
        }
        return render_template(
            "debate/judging_bp.html",
            debate=debate,
            existing=existing,
        )

    speaker_ids = [sp.user_id for sp in speakers]
    judge_ids = [j.user_id for j in judges]

    if request.method == "POST":
        Score.query.filter(
            Score.debate_id == debate_id,
            Score.speaker_id.in_(speaker_ids),
            Score.judge_id.in_(judge_ids),
        ).delete(synchronize_session=False)
        for sp in speakers:
            for j in judges:
                key = f"score_{sp.id}_{j.id}"
                val = request.form.get(key)
                if val:
                    db.session.add(
                        Score(
                            debate_id=debate_id,
                            speaker_id=sp.user_id,
                            judge_id=j.user_id,
                            value=int(val),
                        )
                    )
        db.session.commit()
        flash("Scores saved.", "success")
        feedback = {}
        for j in judges:
            key = f"feedback_{j.user_id}"
            values = request.form.getlist(key)
            feedback[j.user_id] = values[0] if values else None
        session["feedback"] = feedback

        return redirect(url_for("debate.judging", debate_id=debate_id))

    feedback = session.get("feedback", {})
    scores = {
        (s.speaker_id, s.judge_id): s.value
        for s in Score.query.filter(
            Score.debate_id == debate_id,
            Score.speaker_id.in_(speaker_ids),
            Score.judge_id.in_(judge_ids),
        ).all()
    }
    return render_template(
        "debate/judging_opd.html",
        debate=debate,
        judges=judges,
        speakers=speakers,
        scores=scores,
        feedback=feedback,
    )


@debate_bp.route("/debate/<int:debate_id>/finalize", methods=["POST"])
@login_required
def finalize(debate_id):
    """Finalize a debate and record results/Elo."""
    debate = Debate.query.get_or_404(debate_id)
    if not debate.active:
        flash("This debate is inactive.", "warning")
        return redirect(url_for("main.debate_view", debate_id=debate_id))
    chair_slot = get_chair_slot(current_user, debate_id)
    if not chair_slot:
        flash("Only the chair judge can finalize this debate.", "danger")
        return redirect(url_for("main.debate_view", debate_id=debate_id))

    all_slots = SpeakerSlot.query.filter_by(debate_id=debate_id).all()
    rooms = sorted({s.room for s in all_slots})

    slots_by_room = {r: [] for r in rooms}
    judges_by_room = {r: [] for r in rooms}
    
    finalized_judges = {}

    for slot in all_slots:
        if slot.role.startswith("Judge"):
            judges_by_room[slot.room].append(slot.user_id)
        else:
            slots_by_room[slot.room].append(slot)

    OpdResult.query.filter_by(debate_id=debate_id).delete()
    EloLog.query.filter_by(debate_id=debate_id).delete()
    processed_users = set()

    for room in rooms:
        speaker_slots = slots_by_room[room]
        judge_ids = judges_by_room[room]
        # this will be empty (sometimes it executes with the feedback for the wrong room which is fine because it does nothing in that case) or only contain ChairID: None in cases of no wing judges, which will not cause any changes in status
        feedback_values = session.get("feedback", {})

        for j in judge_ids:
            # does not need to consider neutral feedback, as that never changes the status
            # feedback_values might also contain a None value for the chair, which is also ignored
            judge_user = User.query.filter_by(id=str(j)).first()

            prev_skill = judge_user.judge_skill

            individual_feedback = feedback_values.get(str(j))
            # user is upgraded in status if the previous status was Newbie or Can't Judge (the second option should be rare, as the prioritization in picking wing judges is 1. Wing 2. Newbie 3. Can't Judge 3.5 Chair and 4. Suspended)
            if individual_feedback == "positive":
                if prev_skill == "Newbie":
                    User.query.filter_by(id=str(j)).update(
                        {User.judge_skill: "Wing"}, synchronize_session=False
                    )
                elif prev_skill == "Cant judge":
                    User.query.filter_by(id=str(j)).update(
                        {User.judge_skill: "Newbie"}, synchronize_session=False
                    )
            # user is downgraded in status if the previous status was Newbie or Wing (this serves as a feedback mechanism to existing Wings too)
            elif individual_feedback == "negative":
                if prev_skill == "Newbie":
                    User.query.filter_by(id=str(j)).update(
                        {User.judge_skill: "Suspended"}, synchronize_session=False
                    )
                elif prev_skill == "Wing":
                    User.query.filter_by(id=str(j)).update(
                        {User.judge_skill: "Newbie"}, synchronize_session=False
                    )

        room_style = infer_room_style(debate.style, speaker_slots)

        if room_style == "OPD":
            for sp in speaker_slots:
                avg = (
                    db.session.query(db.func.avg(Score.value))
                    .filter(
                        Score.debate_id == debate_id,
                        Score.speaker_id == sp.user_id,
                        Score.judge_id.in_(judge_ids),
                    )
                    .scalar()
                    or 0
                )
                db.session.add(
                    OpdResult(
                        debate_id=debate_id,
                        user_id=sp.user_id,
                        points=avg,
                    )
                )
                old = sp.user.elo_rating or 1000
                new = old + (avg - 43) / 10
                sp.user.elo_rating = new
                db.session.add(
                    EloLog(
                        debate_id=debate_id,
                        user_id=sp.user_id,
                        old_elo=old,
                        new_elo=new,
                        change=new - old,
                    )
                )
                processed_users.add(sp.user_id)
        else:  # BP
            ranks = {
                r.team: r.rank
                for r in BpRank.query.filter_by(debate_id=debate_id).all()
            }
            team_points = {1: 3, 2: 2, 3: 1, 4: 0}
            # Update elo ratings using the Plackett-Luce model
            elo_updates = compute_bp_elo(speaker_slots, ranks)
            for slot, old, new in elo_updates:
                team = slot.role.split("-")[0]
                rank = ranks.get(team)
                pts = team_points.get(rank, 0)
                db.session.add(
                    OpdResult(
                        debate_id=debate_id,
                        user_id=slot.user_id,
                        points=pts,
                    )
                )
                db.session.add(
                    EloLog(
                        debate_id=debate_id,
                        user_id=slot.user_id,
                        old_elo=old,
                        new_elo=new,
                        change=new - old,
                    )
                )
                processed_users.add(slot.user_id)

        print(type(room))
        finalized_judges[room] = True
        print(finalized_judges)
            
    debate.active = False
    db.session.commit()

    if debate.style in ("OPD", "Dynamic"):
        for uid in processed_users:
            user = User.query.get(uid)
            if user:
                user.update_opd_skill()
        db.session.commit()
    flash("Debate finalized.", "success")
    return redirect(url_for("main.debate_view", debate_id=debate_id))
