from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app.models import Debate, Topic, Vote
from app.models import Debate, SpeakerSlot, User
from app.extensions import db
from app import socketio
from datetime import datetime, timedelta
from app.utils import compute_winning_topic


from . import main_bp


@main_bp.route("/privacy")
def privacy():
    """Public privacy policy page."""
    return render_template("main/privacy.html")


@main_bp.route("/")
@login_required
def dashboard():
    # Redirect to survey if user hasn't filled it out
    if not current_user.date_joined_choice:
        return redirect(url_for("auth.survey"))

    # Get all debates, newest first
    debates = Debate.query.order_by(Debate.id.desc()).all()
    open_debates = [d for d in debates if d.active]
    current_debate = open_debates[0] if len(open_debates) == 1 else None

    # Initialize vote statistics and user role
    vote_percent = votes_cast = votes_total = user_role = None
    has_slot = False
    is_judge_chair = False
    is_first_timer = False
    if getattr(current_user, "debate_skill", "") == "First Timer":
        is_first_timer = True

    winning_topic = None
    if current_debate:
        if current_debate.second_voting_open:
            topic_ids = current_debate.second_topic_ids()
            round_num = 2
        else:
            topic_ids = [t.id for t in current_debate.topics]
            round_num = 1
        votes = Vote.query.filter(
            Vote.topic_id.in_(topic_ids), Vote.round == round_num
        ).all()
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
        slot = SpeakerSlot.query.filter_by(
            debate_id=current_debate.id, user_id=current_user.id
        ).first()
        has_slot = slot is not None
        if slot:
            user_role = f"{slot.role} in Room {slot.room}" if slot.room else slot.role
            if slot.role == "Judge-Chair":
                is_judge_chair = True

        winning_topic = compute_winning_topic(current_debate)

    # Categorize debates for UI tabs or display
    active_debates = [
        d
        for d in debates
        if d.active and (not current_debate or d.id != current_debate.id)
    ]
    past_debates = [d for d in debates if not d.active and d.assignment_complete]
    upcoming_debates = [
        d for d in debates if not d.active and not d.assignment_complete
    ]

    return render_template(
        "main/dashboard.html",
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
        has_slot=has_slot,
        is_first_timer=is_first_timer,
        is_judge_chair=is_judge_chair,
        second_voting_open=(
            current_debate.second_voting_open if current_debate else False
        ),
        winning_topic=winning_topic,
        prefers_free=current_user.prefer_free,
        prefers_judging=current_user.prefer_judging,
    )


@main_bp.route("/dashboard/debates_json")
@login_required
def dashboard_debates_json():
    debates = Debate.query.order_by(Debate.id.desc()).all()
    open_debates = [d for d in debates if d.active]
    current_debate = open_debates[0] if len(open_debates) == 1 else None

    active_debates = [
        d
        for d in debates
        if d.active and (not current_debate or d.id != current_debate.id)
    ]
    past_debates = [d for d in debates if not d.active and d.assignment_complete]
    upcoming_debates = [
        d for d in debates if not d.active and not d.assignment_complete
    ]

    def serialize(d):
        return (
            {
                "id": d.id,
                "title": d.title,
                "style": d.style,
                "active": d.active,
                "second_voting_open": d.second_voting_open,
            }
            if d
            else None
        )

    def serialize_current(d):
        if not d:
            return None
        if d.second_voting_open:
            topic_ids = d.second_topic_ids()
            round_num = 2
        else:
            topic_ids = [t.id for t in d.topics]
            round_num = 1
        votes = Vote.query.filter(
            Vote.topic_id.in_(topic_ids), Vote.round == round_num
        ).all()
        voter_ids = set(v.user_id for v in votes)
        votes_cast = len(voter_ids)

        now = datetime.utcnow()
        ten_minutes_ago = now - timedelta(minutes=10)
        active_user_ids = set(
            u.id for u in User.query.filter(User.last_seen >= ten_minutes_ago).all()
        )
        eligible_user_ids = active_user_ids.union(voter_ids)
        votes_total = len(eligible_user_ids)
        vote_percent = int((votes_cast / votes_total) * 100) if votes_total else 0

        slot = SpeakerSlot.query.filter_by(
            debate_id=d.id, user_id=current_user.id
        ).first()
        user_role = (
            (f"{slot.role} in Room {slot.room}" if slot and slot.room else slot.role)
            if slot
            else None
        )

        is_judge_chair = slot.role == "Judge-Chair" if slot else False
        winner = compute_winning_topic(d)

        return {
            "id": d.id,
            "title": d.title,
            "style": d.style,
            "active": d.active,
            "voting_open": d.voting_open,
            "second_voting_open": d.second_voting_open,
            "assignment_complete": d.assignment_complete,
            "user_role": user_role,
            "is_first_timer": is_first_timer,
            "is_judge_chair": is_judge_chair,
            "vote_percent": vote_percent,
            "votes_cast": votes_cast,
            "votes_total": votes_total,
            "winner_topic": (
                {
                    "id": winner.id,
                    "text": winner.text,
                    "factsheet": winner.factsheet,
                }
                if winner
                else None
            ),
        }

    return jsonify(
        {
            "current_debate": serialize_current(current_debate),
            "active_debates": [serialize(d) for d in active_debates],
            "past_debates": [serialize(d) for d in past_debates],
            "upcoming_debates": [serialize(d) for d in upcoming_debates],
        }
    )


@main_bp.route("/debate/<int:debate_id>", methods=["GET", "POST"])
@login_required
def debate_view(debate_id):
    if not current_user.date_joined_choice:
        return redirect(url_for("auth.survey"))

    debate = Debate.query.options(joinedload(Debate.speakerslots)).get_or_404(debate_id)
    topics = debate.second_topics() if debate.second_voting_open else debate.topics

    # voting logic
    if request.method == "POST" and debate.voting_open:
        topic_id = int(request.form.get("topic_id"))
        round_num = 2 if debate.second_voting_open else 1
        existing_vote = Vote.query.filter_by(
            user_id=current_user.id, topic_id=topic_id, round=round_num
        ).first()
        user_votes_in_debate = (
            Vote.query.join(Topic)
            .filter(
                Vote.user_id == current_user.id,
                Topic.debate_id == debate_id,
                Vote.round == round_num,
            )
            .count()
        )
        max_votes = 1 if debate.second_voting_open else 2
        if existing_vote:
            flash("You have already voted for this topic.", "warning")
        elif user_votes_in_debate >= max_votes:
            if debate.second_voting_open:
                flash("You can only vote for one topic in this round.", "danger")
            else:
                flash("You can only vote for up to 2 topics per debate.", "danger")
        else:
            # Bump debate_count if this is their first vote in this debate

            if user_votes_in_debate == 0 and round_num == 1:
                if current_user.debate_count is None:
                    current_user.debate_count = 0
                current_user.debate_count += 1
                prev_skill = getattr(current_user, "debate_skill", "")
                # if this is the user's third debate overall, they graduate to Newbie status and are more eligible for wing judge selection
                prev_judge_skill = getattr(current_user, "judge_skill", "")
                if prev_judge_skill == "Cant judge" and current_user.debate_count == 3:
                    current_user.judge_skill = "Newbie"
                # experience level of user is upgraded to Beginner with the fifth debate
                if prev_skill == "First Timer" and current_user.debate_count >= 5:
                    current_user.debate_skill = "Beginner"
                # TODO count debates where the user judged? maybe with a 0.5 factor?
                # generally requires a debates_judged variable which should be initialized through the difference of debate_count and existing scores for this user ignoring BP debates
                # probably best as an admin functionality that is executed once for all users in order to avoid re-evaluating this with every new debate
                elif prev_skill == "Beginner" and current_user.debate_count >= 15:
                    current_user.debate_skill = "Intermediate"
                # step to advanced would make more sense to implement with a dependency on actual scores
            vote = Vote(user_id=current_user.id, topic_id=topic_id, round=round_num)
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
                .filter(Topic.debate_id == debate_id, Vote.round == round_num)
                .distinct()
                .all()
            )
            eligible_user_ids = active_user_ids.union(voted_user_ids)
            total_users = len(eligible_user_ids)
            voted_users = len(voted_user_ids)

            socketio.emit(
                "vote_update",
                {
                    "debate_id": debate_id,
                    "vote_data": {
                        "total_users": total_users,
                        "voted_users": voted_users,
                    },
                },
            )
            # -- live vote update end --

            flash("Your vote has been cast!", "success")
        return redirect(url_for("main.debate_view", debate_id=debate_id))

    # Prepare user vote info for template
    round_num = 2 if debate.second_voting_open else 1
    topic_ids = (
        debate.second_topic_ids()
        if debate.second_voting_open
        else [t.id for t in debate.topics]
    )
    user_votes = [
        v.topic_id
        for v in Vote.query.filter(
            Vote.user_id == current_user.id,
            Vote.round == round_num,
            Vote.topic_id.in_(topic_ids),
        ).all()
    ]
    limit = 1 if debate.second_voting_open else 2
    votes_left = limit - len(user_votes)

    return render_template(
        "main/debate.html",
        debate=debate,
        topics=topics,
        user_votes=user_votes,
        votes_left=votes_left,
    )


@main_bp.route("/debate/<int:debate_id>/assignments")
@login_required
def debate_assignments(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    slots = SpeakerSlot.query.filter_by(debate_id=debate_id).all()
    # Optionally group by room for split debates
    slots_by_room = {}
    for slot in slots:
        slots_by_room.setdefault(slot.room, []).append(slot)
    # Get users by id for lookup
    user_map = {
        u.id: u
        for u in User.query.filter(User.id.in_([s.user_id for s in slots])).all()
    }
    return render_template(
        "main/debate_assignments.html",
        debate=debate,
        slots_by_room=slots_by_room,
        user_map=user_map,
    )


@main_bp.route("/debate/<int:debate_id>/topics_json")
@login_required
def debate_topics_json(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    topic_list = debate.second_topics() if debate.second_voting_open else debate.topics
    topics = [
        {"id": t.id, "text": t.text, "factsheet": t.factsheet} for t in topic_list
    ]
    return jsonify({"topics": topics})


@main_bp.route("/debate/<int:debate_id>/assignments_json")
@login_required
def debate_assignments_json(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    slots = SpeakerSlot.query.filter_by(debate_id=debate_id).all()
    assignments = [
        {
            "role": s.role,
            "room": s.room,
            "user_id": s.user_id,
            "name": f"{s.user.first_name} {s.user.last_name}",
            "prefer_free": s.user.prefer_free,
            "prefer_judging": s.user.prefer_judging,
        }
        for s in slots
    ]

    slots_by_room = {}
    for s in slots:
        slots_by_room.setdefault(s.room, []).append(s)

    room_styles = {}
    for room, room_slots in slots_by_room.items():
        roles = {sl.role for sl in room_slots}
        if roles.intersection({"OG", "OO", "CG", "CO"}):
            room_styles[room] = "BP"
        elif roles.intersection({"Gov", "Opp"}):
            room_styles[room] = "OPD"
        else:
            room_styles[room] = debate.style

    return jsonify({"assignments": assignments, "room_styles": room_styles})


@main_bp.route("/debate/<int:debate_id>/join", methods=["POST"])
@login_required
def debate_join(debate_id):
    debate = Debate.query.get_or_404(debate_id)

    # Ensure the user is not already assigned a slot in this debate
    existing = SpeakerSlot.query.filter_by(
        debate_id=debate_id, user_id=current_user.id
    ).first()
    if existing:
        return (
            jsonify({"success": False, "message": "Already assigned to this debate."}),
            400,
        )

    rooms = sorted({s.room for s in debate.speakerslots}) or [1]

    def judge_room_counts():
        counts = []
        for room in rooms:
            count = SpeakerSlot.query.filter(
                SpeakerSlot.debate_id == debate_id,
                SpeakerSlot.room == room,
                SpeakerSlot.role.like("Judge%"),
            ).count()
            counts.append((count, room))
        counts.sort()
        return counts

    def assign_judge():
        for count, room in judge_room_counts():
            if count < 3:
                slot = SpeakerSlot(
                    debate_id=debate_id,
                    user_id=current_user.id,
                    role="Judge-Wing",
                    room=room,
                )
                db.session.add(slot)
                db.session.commit()
                socketio.emit("assignments_ready", {"debate_id": debate_id})
                return jsonify({"success": True, "role": "Judge-Wing", "room": room})
        return None

    def assign_speaker():
        for room in rooms:
            roles = {s.role for s in debate.speakerslots if s.room == room}
            # Detect OPD rooms by the presence of Gov/Opp or any Free slot
            is_opd_room = any(
                r.startswith("Free") or r in {"Gov", "Opp"} for r in roles
            )
            if not is_opd_room:
                continue
            for idx in range(1, 4):
                role = f"Free-{idx}"
                if role not in roles:
                    slot = SpeakerSlot(
                        debate_id=debate_id,
                        user_id=current_user.id,
                        role=role,
                        room=room,
                    )
                    db.session.add(slot)
                    db.session.commit()
                    socketio.emit("assignments_ready", {"debate_id": debate_id})
                    return jsonify({"success": True, "role": role, "room": room})
        return None

    # Step 1: Ensure each room has at least two judges
    if current_user.judge_skill in ("Wing", "Chair"):
        counts = judge_room_counts()
        if counts and counts[0][0] < 2:
            result = assign_judge()
            if result:
                return result

    # Step 2 and 3: Respect judging preference or fill speakers first
    if current_user.prefer_judging and current_user.judge_skill in ("Wing", "Chair"):
        result = assign_judge()
        if result:
            return result
        result = assign_speaker()
        if result:
            return result
    else:
        result = assign_speaker()
        if result:
            return result
        if current_user.judge_skill in ("Wing", "Chair"):
            result = assign_judge()
            if result:
                return result

    return (
        jsonify(
            {"success": False, "message": "No available slot or judging permission."}
        ),
        400,
    )


@main_bp.route("/debate/<int:debate_id>/vote_status_json")
@login_required
def debate_vote_status_json(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    if debate.second_voting_open:
        round_num = 2
        topic_ids = debate.second_topic_ids()
        limit = 1
    else:
        round_num = 1
        topic_ids = [t.id for t in debate.topics]
        limit = 2
    user_votes = [
        v.topic_id
        for v in Vote.query.filter(
            Vote.user_id == current_user.id,
            Vote.round == round_num,
            Vote.topic_id.in_(topic_ids),
        ).all()
    ]
    votes_left = limit - len(user_votes)
    return jsonify({"user_votes": user_votes, "votes_left": votes_left})


@main_bp.route("/debate/<int:debate_id>/graphic")
@login_required
def debate_graphic(debate_id):
    from sqlalchemy.orm import joinedload

    debate = Debate.query.options(
        joinedload(Debate.speakerslots), joinedload(Debate.topics)
    ).get_or_404(debate_id)

    if not debate.assignment_complete:
        flash("Speaker assignments are not complete for this debate.", "warning")
        return redirect(url_for("main.debate_view", debate_id=debate_id))

    # Find current user's slot (may be None if not assigned)
    my_slot = SpeakerSlot.query.filter_by(
        debate_id=debate_id, user_id=current_user.id
    ).first()

    # Group slots by room (for multi-room support)
    slots_by_room = {}
    for slot in debate.speakerslots:
        slots_by_room.setdefault(slot.room, []).append(slot)

    # Determine style for each room based on assigned roles
    room_styles = {}
    for room, slots in slots_by_room.items():
        roles = {s.role for s in slots}
        if roles.intersection({"OG", "OO", "CG", "CO"}):
            room_styles[room] = "BP"
        elif roles.intersection({"Gov", "Opp"}):
            room_styles[room] = "OPD"
        else:
            room_styles[room] = debate.style

    active_room = request.args.get("room", type=int)
    if not active_room:
        active_room = my_slot.room if my_slot else sorted(slots_by_room)[0]

    return render_template(
        "main/graphic.html",
        debate=debate,
        slots_by_room=slots_by_room,
        room_styles=room_styles,
        active_room=active_room,
        my_slot=my_slot,
        user=current_user,
    )
