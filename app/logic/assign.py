import math, random
from app.models import SpeakerSlot, User, Debate
from app.extensions import db
from collections import Counter


def _compute_room_counts(total, settings):
    """Compute participant counts per room based on min/max settings.

    settings is a list of tuples (min_count, max_count).
    Returns a list of counts or None if total cannot fit within bounds.
    """
    mins = [m for m, _ in settings]
    maxs = [M for _, M in settings]

    numbers = mins[:]
    remaining = total - sum(numbers)
    if remaining < 0:
        return None
    capacity = sum(M - m for m, M in settings)
    if remaining > capacity:
        return None

    for i in range(len(settings)):
        if remaining <= 0:
            break
        add = min(maxs[i] - numbers[i], remaining)
        numbers[i] += add
        remaining -= add

    if remaining != 0:
        return None
    return numbers

def assign_speakers(debate, users, max_rooms=2, scenario=None):
    """
    Dispatch to OPD or BP, splitting into at most max_rooms rooms,
    and always using the fewest rooms needed.
    """

    users = list(users)
    random.shuffle(users)

    # Determine thresholds
    if debate.style == "OPD":
        split_threshold = 15
        helper = assign_opd_single_room
    elif debate.style == "BP":
        split_threshold = 18
        helper = assign_bp_single_room
    elif debate.style == "Dynamic":
        return assign_dynamic(debate, users, scenario=scenario)
    else:
        return False, f"Unknown debate style: {debate.style}"

    # Decide number of rooms
    if len(users) < split_threshold or max_rooms < 2:
        num_rooms = 1
    else:
        # Once you hit the threshold, always split into exactly 2 rooms
        num_rooms = 2
        
    assignments_ok = []
    messages = []

    # If only one room needed:
    if num_rooms == 1:
        ok, msg = helper(debate, users, room=1)
        assignments_ok.append(ok)
        messages.append(msg)
    else:
        # Otherwise split into num_rooms (here always 2), as evenly as possible
        per_room = math.ceil(len(users) / num_rooms)
        for room in range(1, num_rooms + 1):
            start = (room - 1) * per_room
            end   = start + per_room
            subset = users[start:end]
            ok, msg = helper(debate, subset, room=room)
            assignments_ok.append(ok)
            messages.append(f"Room{room}: {msg}")    

    if all(assignments_ok):
        debate.assignment_complete = True
        db.session.commit() 
        return True, " | ".join(messages)
    else:
        return False, " | ".join(messages)



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


def assign_dynamic(debate, users, scenario=None):
    """Assign speakers for the Dynamic style using a selected scenario."""
    if not scenario:
        # Fallback to old heuristic if no scenario provided
        if len(users) <= 7:
            return assign_opd_single_room(debate, users, room=1)
        elif len(users) <= 9:
            return assign_bp_single_room(debate, users, room=1)
        else:
            mid = len(users) // 2
            ok1, msg1 = assign_opd_single_room(debate, users[:mid], room=1)
            ok2, msg2 = assign_bp_single_room(debate, users[mid:], room=2)
            return ok1 and ok2, f"Dynamic: {msg1}; {msg2}"

    room_types = {'O': ('OPD', 7, 12), 'B': ('BP', 9, 11)}
    letters = scenario.split('-')
    try:
        settings = [room_types[c.upper()] for c in letters]
    except KeyError:
        return False, "Unknown scenario"

    counts = _compute_room_counts(len(users), [(s[1], s[2]) for s in settings])
    if counts is None:
        return False, "Participant count doesn't fit the selected scenario"

    def eligible_chair(u):
        if getattr(u, 'judge_skill', '') == 'Chair':
            return True
        if getattr(u, 'judge_skill', '') == 'Wing' and getattr(u, 'debate_skill', '') != 'First Timer':
            return True
        return getattr(u, 'debate_skill', '') != 'First Timer'

    pool = list(users)
    random.shuffle(pool)
    rooms = []
    unsafe = False
    for _ in settings:
        chair_user = next((u for u in pool if getattr(u, 'judge_skill', '') == 'Chair'), None)
        if not chair_user:
            chair_user = next((u for u in pool if getattr(u, 'judge_skill', '') == 'Wing' and getattr(u, 'debate_skill', '') != 'First Timer'), None)
            if not chair_user:
                chair_user = next((u for u in pool if getattr(u, 'debate_skill', '') != 'First Timer'), None)
                if not chair_user:
                    return False, "No eligible Chair judge for one of the rooms"
                unsafe = True
            else:
                unsafe = True
        rooms.append([chair_user])
        pool.remove(chair_user)

    remaining = pool

    for idx, count in enumerate(counts):
        need = count - 1  # one chair already placed
        rooms[idx].extend(remaining[:need])
        remaining = remaining[need:]

    messages = []
    success = True
    for i, (room_users, spec) in enumerate(zip(rooms, settings), start=1):
        if spec[0] == 'OPD':
            ok, msg = assign_opd_single_room(debate, room_users, room=i)
        else:
            ok, msg = assign_bp_single_room(debate, room_users, room=i)
        success = success and ok
        messages.append(msg)

    if remaining:
        success = False
        messages.append('Unassigned participants remain')

    if unsafe:
        messages.append('Fallback Chairs were used')

    if success:
        debate.assignment_complete = True
        db.session.commit()
    return success, ' | '.join(messages)

