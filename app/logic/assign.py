import random
from app.models import SpeakerSlot, User, Debate
from app.extensions import db
from collections import Counter

def assign_speakers(debate, users):
    """
    Dispatch to OPD or BP—and if there are enough participants,
    split into two rooms (each one full debate) rather than
    try to jam everyone into one room.
    """
    import random

    if debate.style == 'OPD':
        random.shuffle(users)
        # OPD: split when 15+ participants
        if len(users) >= 15:
            mid = len(users) // 2
            u1, u2 = users[:mid], users[mid:]
            ok1, m1 = assign_opd_single_room(debate, u1, room=1)
            ok2, m2 = assign_opd_single_room(debate, u2, room=2)
            if ok1 and ok2:
                return True, "Two OPD rooms assigned successfully."
            return False, f"Room1: {m1} | Room2: {m2}"
        else:
            return assign_opd_single_room(debate, users, room=1)

    elif debate.style == 'BP':
        random.shuffle(users)
        # BP: split when 16+ participants (8 per room)
        if len(users) >= 16:
            # take first 8+1 for room1, next 8+1 for room2 if you want 1 judge each
            # or simply split evenly and let assign_bp handle judge count
            mid = len(users) // 2
            u1, u2 = users[:mid], users[mid:]
            ok1, m1 = assign_bp_single_room(debate, u1, room=1)
            ok2, m2 = assign_bp_single_room(debate, u2, room=2)
            if ok1 and ok2:
                return True, "Two BP rooms assigned successfully."
            return False, f"Room1: {m1} | Room2: {m2}"
        else:
            return assign_bp_single_room(debate, users, room=1)

    else:
        return False, f"Unknown debate style: {debate.style}"


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
    
    # ---------- INTEGRITY CHECK ------------------------------------------------
    roles = [a.role for a in assignments]
    user_ids = [a.user_id for a in assignments]

    role_counts = Counter(roles)

    # 1. One Judge-Chair
    if role_counts.get("Judge-Chair", 0) != 1:
        return False, "Integrity Error: Must have exactly 1 Chair judge."

    # 2. Exactly 6 speakers (Gov/Opp)
    speaker_count = sum(1 for r in roles if r in ("Gov", "Opp"))
    if speaker_count != 6:
        return False, "Integrity Error: Must have exactly 6 Gov/Opp speakers."

    # 3. Only one Judge-Wing before free speakers
    # Already enforced by logic — you can just count total Judge-Wings

    # 4. Free speakers must be labeled correctly and max 3
    free_roles = [r for r in roles if r.startswith("Free")]
    if len(free_roles) > 3:
        return False, "Integrity Error: Too many free speakers."
    if sorted(free_roles) != [f"Free-{i+1}" for i in range(len(free_roles))]:
        return False, "Integrity Error: Free speaker labels are malformed."

    # 5. All other users should be assigned as Judge-Wing
    valid_roles = {"Gov", "Opp", "Judge-Chair", "Judge-Wing"} | set(free_roles)
    if any(r not in valid_roles for r in roles):
        return False, "Integrity Error: Invalid roles detected."

    # 6. No duplicate user assignments
    if len(set(user_ids)) != len(user_ids):
        return False, "Integrity Error: Duplicate user assignment detected."

    # ---------- COMMIT ------------------------------------------------------
    db.session.bulk_save_objects(assignments)
    db.session.commit()
    return True, f"Room {room}: OPD assignment complete."


def assign_bp_single_room(debate, users, room=1):
    """
    Assigns speakers for BP format with ProAm constraint.
    1. Chair judge first (prefer 'Chair', fallback to Wing/non-First-Timer)
    2. 8 speakers, paired so no team has two First Timers unless unavoidable
    3. 4 teams: OG, OO, CG, CO (two debaters each)
    4. Remaining: assign as Wings
    """
    import random
    from app.models import SpeakerSlot
    from app.extensions import db

    pool = list(users)
    random.shuffle(pool)

    is_chair = lambda u: getattr(u, "judge_skill", "") == "Chair"
    is_wing  = lambda u: getattr(u, "judge_skill", "") == "Wing"
    is_first = lambda u: getattr(u, "debate_skill", "") == "First Timer"

    # --- 1. Assign Chair ---
    chair_user = next((u for u in pool if is_chair(u)), None)
    if not chair_user:
        chair_user = next((u for u in pool if is_wing(u) and not is_first(u)), None)
    if not chair_user:
        chair_user = next((u for u in pool if not is_first(u)), None)
    if not chair_user:
        return False, "No eligible Chair judge for BP."

    slots = [
        SpeakerSlot(debate_id=debate.id, user_id=chair_user.id, role="Judge-Chair", room=room)
    ]
    pool.remove(chair_user)

    # --- 2. Assign 8 speakers with ProAm pairing ---
    # Split pool into First Timers and Non-First-Timers
    first_timers = [u for u in pool if is_first(u)]
    non_firsts   = [u for u in pool if not is_first(u)]

    teams = []
    speakers = []

    # Attempt to pair each First Timer with a Non-First-Timer
    while first_timers and non_firsts and len(speakers) < 8:
        ft = first_timers.pop(0)
        nf = non_firsts.pop(0)
        teams.append((ft, nf))
        speakers.extend([ft, nf])
    # If still more needed, fill with remaining non-First-Timers
    while len(speakers) < 8 and non_firsts:
        nf = non_firsts.pop(0)
        speakers.append(nf)
    # If still more needed, fill with remaining First Timers (may create a First-Timer pair)
    while len(speakers) < 8 and first_timers:
        ft = first_timers.pop(0)
        speakers.append(ft)
    # Final check
    if len(speakers) < 8:
        return False, "Not enough eligible debaters for BP."

    # Now, group into 4 teams of 2, with ProAm enforced where possible
    bp_roles = ["OG", "OG", "OO", "OO", "CG", "CG", "CO", "CO"]
    for user, role in zip(speakers, bp_roles):
        slots.append(SpeakerSlot(debate_id=debate.id, user_id=user.id, role=role, room=room))
    # Remove these users from pool
    for u in speakers:
        pool.remove(u)

    # --- 3. Assign Wings from remaining ---
    # Assign up to 3 judges: first Wing, then fallback to any non-First-Timer, then (if needed) anyone
    wings = [u for u in pool if is_wing(u)]
    non_firsts_judge = [u for u in pool if not is_first(u) and u not in wings]
    others = [u for u in pool if u not in wings + non_firsts_judge]

    wings_assigned = 0
    for u in wings:
        if wings_assigned == 0:
            slots.append(SpeakerSlot(debate_id=debate.id, user_id=u.id, role="Judge-Wing", room=room))
        else:
            slots.append(SpeakerSlot(debate_id=debate.id, user_id=u.id, role="Judge-Wing", room=room))
        wings_assigned += 1

    for u in non_firsts_judge:
        slots.append(SpeakerSlot(debate_id=debate.id, user_id=u.id, role="Judge-Wing", room=room))
        wings_assigned += 1
        if wings_assigned >= 3:
            break
    for u in others:
        if wings_assigned >= 3:
            break
        slots.append(SpeakerSlot(debate_id=debate.id, user_id=u.id, role="Judge-Wing", room=room))
        wings_assigned += 1

    # --- Commit (guaranteeing no duplicate SpeakerSlot) ---
    for slot in slots:
        exists = SpeakerSlot.query.filter_by(debate_id=debate.id, user_id=slot.user_id, room=room).first()
        if not exists:
            db.session.add(slot)
    db.session.commit()
    return True, "BP speaker assignment complete."

