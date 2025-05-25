import random
from app.models import SpeakerSlot, User, Debate
from app.extensions import db

def assign_speakers(debate, users):
    """
    Main entry point: assigns users to speaker slots for a debate.
    Returns (ok: bool, msg: str)
    """
    if len(users) < 6:
        return False, "Not enough participants for a debate!"

    if debate.style == 'OPD':
        return assign_opd(debate, users)
    elif debate.style == 'BP':
        return assign_bp(debate, users)
    else:
        return False, f"Unknown debate style: {debate.style}"

def assign_opd(debate, users):
    """
    Implements your OPD assignment rules.
    """
    random.shuffle(users)  # Always randomize!

    # SPLIT INTO ROOMS IF 15+
    if len(users) >= 15:
        mid = len(users) // 2
        users1, users2 = users[:mid], users[mid:]
        ok1, msg1 = assign_opd_single_room(debate, users1, room=1)
        ok2, msg2 = assign_opd_single_room(debate, users2, room=2)
        if ok1 and ok2:
            return True, "Two rooms assigned successfully."
        else:
            return False, f"Room 1: {msg1} | Room 2: {msg2}"
    else:
        return assign_opd_single_room(debate, users, room=1)

def assign_opd_single_room(debate, users, room=1):
    """
    OPD single-room assignment:
      1. Chair judge
      2. Six main speakers
      3. One Wing judge
      4. Up to three free speakers
      5. Remaining participants become extra Wings
    """
    import random
    from app.models import SpeakerSlot
    from app.extensions import db

    pool = list(users)
    random.shuffle(pool)                           # randomness

    if len(pool) < 6:
        return False, "Need at least 6 participants."

    # ---------- helper lambdas ---------------------------------------------
    is_chair = lambda u: getattr(u, "judge_skill", "") == "Chair"
    is_wing  = lambda u: getattr(u, "judge_skill", "") == "Wing"
    is_first = lambda u: getattr(u, "debate_skill", "") == "First Timer"

    # ---------- 1. CHAIR ----------------------------------------------------
    chair_user = next((u for u in pool if is_chair(u)), None)
    if not chair_user:
        chair_user = next((u for u in pool if is_wing(u) and not is_first(u)), None)
    if not chair_user:
        chair_user = next((u for u in pool if not is_first(u)), None)
    if not chair_user:
        return False, "No eligible Chair judge."

    assignments = [
        SpeakerSlot(debate_id=debate.id, user_id=chair_user.id,
                    role="Judge-Chair", room=room)
    ]
    pool.remove(chair_user)

    # ---------- 2. SIX MAIN SPEAKERS ---------------------------------------
    if len(pool) < 6:
        return False, "Not enough remaining for 6 main speakers."

    roles = ["Gov"] * 3 + ["Opp"] * 3
    main_speakers = pool[:6]
    for u, side in zip(main_speakers, roles):
        assignments.append(
            SpeakerSlot(debate_id=debate.id, user_id=u.id,
                        role=side, room=room)
        )
    pool = pool[6:]                                # remove main speakers

    # ---------- 3. FIRST WING ----------------------------------------------
    wing_user = next((u for u in pool if is_wing(u)), None)
    if not wing_user:
        wing_user = next((u for u in pool if not is_first(u)), None)

    if wing_user:
        assignments.append(
            SpeakerSlot(debate_id=debate.id, user_id=wing_user.id,
                        role="Judge-Wing", room=room)
        )
        pool.remove(wing_user)

    # ---------- 4. FREE SPEAKERS (max 3) -----------------------------------
    free_speakers = pool[:3]
    for idx, u in enumerate(free_speakers, start=1):
        assignments.append(
            SpeakerSlot(debate_id=debate.id, user_id=u.id,
                        role=f"Free-{idx}", room=room)
        )
    pool = pool[3:]

    # ---------- 5. EXTRA WINGS ---------------------------------------------
    for u in pool:
        assignments.append(
            SpeakerSlot(debate_id=debate.id, user_id=u.id,
                        role="Judge-Wing", room=room)
        )

    # ---------- COMMIT ------------------------------------------------------
    db.session.bulk_save_objects(assignments)
    db.session.commit()
    return True, f"Room {room}: OPD assignment complete."






def assign_bp(debate, users):
    """
    Assigns speakers for BP format.
    """
    random.shuffle(users)
    # Main speakers (8), teams of 2
    if len(users) < 8:
        return False, "Not enough participants for BP (need at least 8)."
    speakers = users[:8]
    remaining = users[8:]
    slots = []
    for i, user in enumerate(speakers):
        team_num = i // 2 + 1
        side = "Gov" if i % 4 < 2 else "Opp"
        team = f"{side}-{team_num}"
        slots.append(SpeakerSlot(debate_id=debate.id, user_id=user.id, role=f"{team}", room=1))
    # Up to 3 judges
    judges = [u for u in remaining if u.judge_skill in ('Wing','Chair')]
    for idx, user in enumerate(judges[:3]):
        role = "Judge-Chair" if user.judge_skill == "Chair" and idx == 0 else "Judge-Wing"
        slots.append(SpeakerSlot(debate_id=debate.id, user_id=user.id, role=role, room=1))
    for slot in slots:
        exists = SpeakerSlot.query.filter_by(debate_id=debate.id, user_id=slot.user_id, room=1).first()
        if not exists:
            db.session.add(slot)
    db.session.commit()
    return True, "BP speaker assignment complete."
