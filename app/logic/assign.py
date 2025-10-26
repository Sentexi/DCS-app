import math
import random
from typing import List, Tuple

from app.models import SpeakerSlot, User, Debate
from app.extensions import db
from collections import Counter

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

_EXP_MAP = {
    "First Timer": 0,
    "Beginner": 1,
    "Intermediate": 2,
    "Advanced": 3,
    "Expert": 4,
}


#helper lambdas to determine the judge_skill of a user 
is_chair = lambda u: getattr(u, "judge_skill", "") == "Chair"
is_trainee = lambda u: getattr(u, "judge_skill", "") == "Trainee"
is_wing = lambda u: getattr(u, "judge_skill", "") == "Wing"
is_newbie = lambda u: getattr(u, "judge_skill", "") == "Newbie"
is_first = lambda u: getattr(u, "judge_skill", "") == "Cant judge"
is_suspended = lambda u: getattr(u, "judge_skill", "") == "Suspended"

def _skill_for(user: User, style: str) -> float:
    """Return a numeric skill level for a user in the given style."""

    if style == "BP":
        sigma = getattr(user, "elo_sigma", None)
        if sigma is not None and sigma <= 320:
            return float(getattr(user, "elo_rating", 1000))
        exp = _EXP_MAP.get(getattr(user, "debate_skill", "First Timer"), 0)
        return 800 + exp * 50

    # OPD
    if getattr(user, "opd_skill", None) is not None:
        return float(user.opd_skill)
    exp = _EXP_MAP.get(getattr(user, "debate_skill", "First Timer"), 0)
    return 35 + exp * 5


def _overall_skill(user: User) -> float:
    """Generic skill value used when style is mixed."""

    bp = _skill_for(user, "BP")
    opd = _skill_for(user, "OPD")
    return (bp / 20.0) + opd  # simple combination keeping order stable


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

    # Distribute remaining participants in a round-robin fashion so that no
    # room ends up more than one participant larger than another (where
    # permitted by the max bounds).
    while remaining > 0:
        progressed = False
        for i in range(len(settings)):
            if remaining <= 0:
                break
            if numbers[i] < maxs[i]:
                numbers[i] += 1
                remaining -= 1
                progressed = True
        if not progressed:
            # No room could accept more participants even though ``remaining``
            # suggests otherwise. This should not happen due to the capacity
            # check above, but guard against misconfiguration.
            return None
    print("format of room counts")
    print(numbers)
    return numbers


def _balance_preferred(rooms: List[List[User]]):
    """Evenly distribute users who prefer judging across rooms.

    Swaps participants between rooms so that the number of users with
    ``prefer_judging`` set is balanced. While doing so, it keeps the size of
    each room constant and never removes the only Chair judge from a room.
    """

    is_pref = lambda u: getattr(u, "prefer_judging", False)
    chair_count = lambda room: sum(1 for u in room if is_chair(u))

    total_pref = sum(1 for room in rooms for u in room if is_pref(u))
    if not rooms or total_pref == 0:
        return rooms

    n_rooms = len(rooms)
    base = total_pref // n_rooms
    extra = total_pref % n_rooms
    targets = [base + (1 if i < extra else 0) for i in range(n_rooms)]
    pref_counts = [sum(1 for u in room if is_pref(u)) for room in rooms]

    while True:
        over = next((i for i, c in enumerate(pref_counts) if c > targets[i]), None)
        under = next((i for i, c in enumerate(pref_counts) if c < targets[i]), None)
        if over is None or under is None:
            break

        over_room = rooms[over]
        under_room = rooms[under]

        over_user = next(
            (
                u
                for u in over_room
                if is_pref(u) and (not is_chair(u) or chair_count(over_room) > 1)
            ),
            None,
        )
        swap_user = next(
            (
                u
                for u in under_room
                if not is_pref(u) and (not is_chair(u) or chair_count(under_room) > 1)
            ),
            None,
        )
        if not over_user or not swap_user:
            break

        over_room.remove(over_user)
        under_room.append(over_user)
        under_room.remove(swap_user)
        over_room.append(swap_user)

        pref_counts[over] -= 1
        pref_counts[under] += 1

    return rooms


def _allocate_by_mode(
    users: List[User],
    counts: List[int],
    settings: List[Tuple[str, int, int]],
    mode: str,
) -> Tuple[List[List[User]], bool, str]:
    """Return per-room user lists based on the assignment mode."""
    pool = list(users)
    unsafe = False

    rooms: List[List[User]] = [[] for _ in counts]

    if mode == "True random":
        random.shuffle(pool)
        for idx, cnt in enumerate(counts):
            rooms[idx] = pool[:cnt]
            pool = pool[cnt:]
        rooms = _balance_preferred(rooms)
        return rooms, unsafe, ""

    if mode == "Random":
        chairs = [u for u in pool if getattr(u, "judge_skill", "") == "Chair"]
        #might be a bit of a hybrid thing, where the other scenario can only happen in OPD mode
        if len(chairs) < len(counts):
            return [], True, "Not enough Chair judges"
        random.shuffle(chairs)
        for idx in range(len(counts)):
            chair = chairs.pop()
            rooms[idx].append(chair)
            pool.remove(chair)
        random.shuffle(pool)
        for idx, cnt in enumerate(counts):
            need = cnt - 1
            rooms[idx].extend(pool[:need])
            pool = pool[need:]
        rooms = _balance_preferred(rooms)
        return rooms, unsafe, ""

    # determine skill metric
    has_bp = any(spec[0] == "BP" for spec in settings)
    style = "BP" if has_bp else "OPD"

    if mode == "Skill based":
        ranked = sorted(pool, key=lambda u: _skill_for(u, style), reverse=True)
        start_idx = 0
        for idx, cnt in enumerate(counts):
            rooms[idx] = ranked[start_idx : start_idx + cnt]
            start_idx += cnt

        # ensure a Chair judge in every room
        for idx, room in enumerate(rooms):
            if not any(is_chair(u) for u in room):
                chair = next(
                    (
                        u
                        for u in pool
                        if is_chair(u) and u not in room
                    ),
                    None,
                )
                if chair:
                    room[0], _ = chair, room[0]
                    pool.remove(chair)
                else:
                    unsafe = True
        rooms = _balance_preferred(rooms)
        return rooms, unsafe, ""

    if mode == "ProAm":
        ranked = sorted(pool, key=lambda u: _skill_for(u, style), reverse=True)
        direction = 1
        index = 0
        for u in ranked:
            rooms[index].append(u)
            index += direction
            if index >= len(rooms):
                index = len(rooms) - 1
                direction = -1
            elif index < 0:
                index = 0
                direction = 1
        # ensure Chair judges present
        for idx, room in enumerate(rooms):
            if not any(is_chair(u) for u in room):
                chair = next(
                    (
                        u
                        for u in pool
                        if is_chair(u) and u not in room
                    ),
                    None,
                )
                if chair:
                    room[0], _ = chair, room[0]
                    pool.remove(chair)
                else:
                    unsafe = True
        rooms = _balance_preferred(rooms)
        return rooms, unsafe, ""

    random.shuffle(pool)
    for idx, cnt in enumerate(counts):
        rooms[idx] = pool[:cnt]
        pool = pool[cnt:]
    rooms = _balance_preferred(rooms)
    return rooms, unsafe, ""


def assign_speakers(debate, users, max_rooms=2, scenario=None):
    """
    Dispatch to OPD or BP, splitting into at most max_rooms rooms,
    and always using the fewest rooms needed.
    """

    users = list(users)
    random.shuffle(users)

    return assign_dynamic(debate, users, scenario=scenario)


#checks if there is an eligible trainee and activates training_mode if that is the case (impacts selection of the first wing judge, who then should be of chair status), otherwise chair selection as usually: preferred first, chair status second, wing status third, neither suspended nor first timer fourth, not suspended last

def select_chair(pool, style):
    preferred = [u for u in pool if getattr(u, "prefer_judging", False)]
    others = [u for u in pool if u not in preferred]
    trainees = [u for u in pool if is_trainee(u)]

    # this parameter simplifies the wing selection later on
    training_mode = False

    # trainee will get the role of chair until they graduate to actual chair status, no preferences are respected (could go through the preferred parameter but an intensive training phase is probably best anyway?)
    # 8 participants are required to guarantee a wing judge
    if style=="OPD" and trainees and len(pool) >= 8:
        chair_user = trainees.pop(0)
        training_mode = True

    else:
        chair_user = next((u for u in preferred if is_chair(u)), None)
        if not chair_user:
            chair_user = next((u for u in others if is_chair(u)), None)

        #wing preference is not considered when no chair is present, but that is already a rare scenario
        if not chair_user:
            combined = preferred + others
            chair_user = next(
                (u for u in combined if is_wing(u) and not is_first(u)), None
            )

        #very unlikely that there is neither a chair nor a wing in a room but if that were to happen, it's practically true random with some consideration of first timers and suspension
        if not chair_user:
            combined = preferred + others
            chair_user = next((u for u in combined if not is_first(u) and not is_suspended(u)), None)

        #practically impossible unless the rules for voluntary suspension are very liberal
        if not chair_user:
            chair_user = next((u for u in combined if not is_suspended(u)), None)

    return chair_user, training_mode


def select_first_wing(preferred, pref_free, others, training_mode):

    remaining_pool = preferred + pref_free + others
    chairs = [u for u in remaining_pool if is_chair(u)]

    # distinction depending on whether or not the Chair Judge is a trainee
    if training_mode:
        #the algorithm tries to respect preferences of chairs so there is an option of volunteering(-ish, no guarantees) for the role of expert wing
        wing_user = next((u for u in preferred if is_chair(u)), None)
        if not wing_user and chairs:
            wing_user = chairs.pop(0)
        #technically this is impossible when a safe scenario is selected because the algorithm tries to assign at least one chair to each room and that chair has not been assigned yet (otherwise training_mode would be false)
        if not wing_user:
            wing_user = next((u for u in others if is_wing(u) or is_newbie(u)), None)

    #wings and newbies are treated equally here for more equality and variety but there is a slight preference for selecting someone with some experience here as the first wing judge
    else:
        wing_user = next((u for u in preferred if is_wing(u) or is_newbie(u)), None)
        if not wing_user:
            wing_user = next((u for u in others if is_wing(u) or is_newbie(u)), None)
        # this should be quite unlikely to happen but will select either first timers or chairs
        if not wing_user:
            wing_user = next((u for u in others if not is_suspended(u)), None)

    return wing_user


# selects wing judges ahead of main speaker selection in order to try to enforce that participants are not first timers or suspended (or chairs to avoid judging fatigue) but anything else is fine in the spirit of diverse juries and ~knowledge sharing~
def select_wings(preferred, pool, style):
    wings = []
    # 9 because main speakers and free speakers have not been assigned yet
    if style=="OPD":
        required_wings = len(pool) - 9
    else:
        required_wings = len(pool) - 8

    if required_wings <= 0:
        return wings
    else:
        while len(wings) < required_wings:
            # first timers or chairs who set the judging preference can get selected here - volunteers are welcome! maybe some more distinction for chairs would be good but this probably doesn't have too much impact
            if preferred:
                wings.append(preferred.pop(0))
            else:
                wing_user = next((u for u in pool if not is_suspended(u) and not is_first(u) and not is_chair(u)), None)
                if not wing_user:
                    wing_user = next((u for u in pool if not is_suspended(u) and not is_chair(u)), None)
                if not wing_user:
                    wing_user = next((u for u in pool), None)
                if wing_user:
                    wings.append(wing_user)
    return wings


# avoids users being in multiple sets after already being assigned a role, relevant in case of users setting both preferences or the assigned chair having set a preference
def remove_user(user, preferred, pref_free, others, pool):
    if user in preferred:
        preferred.remove(user)
    if user in pref_free:
        pref_free.remove(user)
    if user in others:
        others.remove(user)
    if user in pool:
        pool.remove(user)
    return preferred, pref_free, others, pool


def integrity_check_opd(assignments):

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

    return True


def assign_opd_single_room_true_random(debate, users, room=1):
    pool = list(users)
    random.shuffle(pool)  # randomness

    if len(pool) < 7:
        return False, "Need at least 7 participants (including a chair)."

    # If True random mode, skip chair/wing preference logic and assign purely
    # based on shuffled order
    roles = ["Gov"] * 3 + ["Opp"] * 3
    assignments = []
    chair_user = pool.pop(0)
    assignments.append(
        SpeakerSlot(
            debate_id=debate.id,
            user_id=chair_user.id,
            role="Judge-Chair",
            room=room,
        )
    )

    main_speakers = pool[:6]
    for u, side in zip(main_speakers, roles):
        assignments.append(
            SpeakerSlot(debate_id=debate.id, user_id=u.id, role=side, room=room)
        )
    pool = pool[6:]

    if pool:
        wing_user = pool.pop(0)
        assignments.append(
            SpeakerSlot(
                debate_id=debate.id,
                user_id=wing_user.id,
                role="Judge-Wing",
                room=room,
            )
        )

    free_speakers = pool[:3]
    for idx, u in enumerate(free_speakers, start=1):
        assignments.append(
            SpeakerSlot(
                debate_id=debate.id, user_id=u.id, role=f"Free-{idx}", room=room
            )
        )
    pool = pool[3:]

    for u in pool:
        assignments.append(
            SpeakerSlot(debate_id=debate.id, user_id=u.id, role="Judge-Wing", room=room)
        )

    if integrity_check_opd(assignments):
        db.session.bulk_save_objects(assignments)
        db.session.commit()
        return True, f"Room {room}: OPD assignment complete."

    else:
        return False, "Integrity Error"


def assign_opd_single_room(debate, users, room=1, mode="Random"):
    """
    OPD single-room assignment:
      1. Chair judge
      2. Six main speakers
      3. One Wing judge
      4. Up to three free speakers
      5. Remaining participants become extra Wings
    """

    pool = list(users)
    random.shuffle(pool)  # randomness

    if len(pool) < 7:
        return False, "Need at least 7 participants (including a chair)."

    roles = ["Gov"] * 3 + ["Opp"] * 3

    # judging preference is only considered for users who are not suspended
    preferred = [u for u in pool if not is_suspended(u) and getattr(u, "prefer_judging", False)]
    # it is possible that users set both preferences, this will be considered in free speaker/wing selection
    pref_free = [u for u in pool if getattr(u, "prefer_free", False)]
    others = [u for u in pool if u not in preferred and u not in pref_free]

    chair_user, training_mode = select_chair(pool, "OPD")

    if not chair_user:
        return False, "No eligible Chair judge"

    # chair_user is removed from all sets at once
    preferred, pref_free, others, pool = remove_user(
        chair_user, preferred, pref_free, others, pool
    )

    assignments = [
        SpeakerSlot(
            debate_id=debate.id,
            user_id=chair_user.id,
            role="Judge-Chair",
            room=room,
        )
    ]

    # the first wing judge always exists for a pool of at least eight participants but the chair has already been removed, so 7 is the magic number here
    if len(pool) > 6:
        wing_user = select_first_wing(preferred, pref_free, others, training_mode)
        if wing_user:
            assignments.append(
                SpeakerSlot(
                    debate_id=debate.id,
                    user_id=wing_user.id,
                    role="Judge-Wing",
                    room=room,
                )
            )

        preferred, pref_free, others, pool = remove_user(
            wing_user, preferred, pref_free, others, pool
        )

    # ---------- 2. WING SELECTION ------------------------------------------

    # this method should automatically assign the correct number of wing judges (difference between pool and six main speakers + three free speakers)
    wing_judges = select_wings(preferred, pool, "OPD")
    for j in wing_judges:
        preferred, pref_free, others, pool = remove_user(
            j, preferred, pref_free, others, pool
        )
        assignments.append(
            SpeakerSlot(
                debate_id=debate.id,
                user_id=j.id,
                role="Judge-Wing",
                room=room,
            )
        )

    # ---------- 3. SIX MAIN SPEAKERS ---------------------------------------

    # wing selection is finished, therefore judging preference is obsolete
    others = list(set(others + preferred))

    while len(others) < 6 and pref_free:
        others.append(pref_free.pop(0))

    if mode == "ProAm":
        ranked = sorted(others, key=lambda u: _skill_for(u, "OPD"), reverse=True)
        main_speakers = []
        while len(main_speakers) < 6 and ranked:
            if ranked:
                main_speakers.append(ranked.pop(0))
            if ranked and len(main_speakers) < 6:
                main_speakers.append(ranked.pop())
    else:
        main_speakers = others[:6]
        for u, side in zip(main_speakers, roles):
            assignments.append(
                SpeakerSlot(debate_id=debate.id, user_id=u.id, role=side, room=room)
            )

        for u in main_speakers:
            preferred, pref_free, others, pool = remove_user(
                u, preferred, pref_free, others, pool
            )

    # ---------- 4. FREE SPEAKERS (max 3) -----------------------------------
    free_speakers = pref_free[:3]

    while len(free_speakers) < 3 and len(others) > 0:
        free_speakers.append(others.pop(0))

    # duplicate removal just in case of rare coincidences with someone setting both preferences and somehow getting selected twice above
    free_speakers = set(free_speakers)

    for idx, u in enumerate(free_speakers, start=1):
        assignments.append(
            SpeakerSlot(
                debate_id=debate.id, user_id=u.id, role=f"Free-{idx}", room=room
            )
        )
        preferred, pref_free, others, pool = remove_user(
            u, preferred, pref_free, others, pool
        )

    # ---------- COMMIT ------------------------------------------------------

    if integrity_check_opd(assignments):
        db.session.bulk_save_objects(assignments)
        db.session.commit()
        return True, f"Room {room}: OPD assignment complete."

    else:
        return False, "Integrity Error"


def assign_bp_single_room(debate, users, room=1, mode="Random"):
    """
    Assigns speakers for BP format with ProAm constraint.
    1. Chair judge first (prefer 'Chair', fallback to Wing/non-First-Timer)
    2. 8 speakers, paired so no team has two First Timers unless unavoidable
    3. 4 teams: OG, OO, CG, CO (two debaters each)
    4. Remaining: assign as Wings
    """

    pool = list(users)
    random.shuffle(pool)

    bp_roles = ["OG", "OG", "OO", "OO", "CG", "CG", "CO", "CO"]

    if mode == "True random":
        if len(pool) < 9:
            return False, "Not enough eligible debaters for BP."

        chair_user = pool.pop(0)
        slots = [
            SpeakerSlot(
                debate_id=debate.id,
                user_id=chair_user.id,
                role="Judge-Chair",
                room=room,
            )
        ]

        speakers = pool[:8]
        for user, role in zip(speakers, bp_roles):
            slots.append(
                SpeakerSlot(debate_id=debate.id, user_id=user.id, role=role, room=room)
            )
        pool = pool[8:]

        wings_assigned = 0
        for u in pool:
            if wings_assigned >= 3:
                break
            slots.append(
                SpeakerSlot(
                    debate_id=debate.id, user_id=u.id, role="Judge-Wing", room=room
                )
            )
            wings_assigned += 1

        for slot in slots:
            exists = SpeakerSlot.query.filter_by(
                debate_id=debate.id, user_id=slot.user_id, room=room
            ).first()
            if not exists:
                db.session.add(slot)
        db.session.commit()
        return True, "BP speaker assignment complete."

    # --- 1. Assign judges ---

    # Chair judge selection via helper method

    preferred = [u for u in pool if not is_suspended(u) and getattr(u, "prefer_judging", False)]
    others = [u for u in pool if u not in preferred]
    
    #training mode isn't really used in BP so that is ignored
    chair_user, training_mode = select_chair(pool, "BP")
    if not chair_user:
        return False, "No eligible Chair judge"
    
    #there is no pref_free set in BP which is why an empty list is passed
    remove_user(chair_user, preferred, [], others, pool)
    slots = [
        SpeakerSlot(
            debate_id=debate.id, user_id=chair_user.id, role="Judge-Chair", room=room
        )
    ]

    wings = select_wings(preferred, pool, "BP")
    for u in wings:
        remove_user(u, preferred, [], others, pool)
        slots.append( SpeakerSlot( debate_id=debate.id, user_id=u.id, role="Judge-Wing", room=room))

    # --- 2. Assign 8 speakers ---
    speakers = []
    if mode == "ProAm":
        ranked = sorted(others, key=lambda u: _skill_for(u, "BP"), reverse=True)
        while len(speakers) < 8 and ranked:
            if ranked:
                speakers.append(ranked.pop(0))
            if ranked and len(speakers) < 8:
                speakers.append(ranked.pop())
    else:
        first_timers = [u for u in pool if is_first(u)]
        non_firsts = [u for u in pool if not is_first(u)]
        while first_timers and non_firsts and len(speakers) < 8:
            speakers.extend([first_timers.pop(0), non_firsts.pop(0)])
        while len(speakers) < 8 and non_firsts:
            speakers.append(non_firsts.pop(0))
        while len(speakers) < 8 and first_timers:
            speakers.append(first_timers.pop(0))
    # Final check
    if len(speakers) < 8:
        return False, "Not enough eligible debaters for BP."

    # Now, group into 4 teams of 2, with ProAm enforced where possible
    for user, role in zip(speakers, bp_roles):
        slots.append(
            SpeakerSlot(debate_id=debate.id, user_id=user.id, role=role, room=room)
        )
    # Remove these users from pool
    for u in speakers:
        remove_user(u, preferred, [], others, pool)

    # --- Commit (guaranteeing no duplicate SpeakerSlot) ---
    for slot in slots:
        exists = SpeakerSlot.query.filter_by(
            debate_id=debate.id, user_id=slot.user_id, room=room
        ).first()
        if not exists:
            db.session.add(slot)
    db.session.commit()
    return True, "BP speaker assignment complete."


def fallback_heuristic(debate, users):
    if len(users) <= 7:
        if debate.assignment_mode == "True random":
            debate.style = "OPD"
            return assign_opd_single_room_true_random(debate, users, room=1)
        else:
            debate.style = "OPD"
            return assign_opd_single_room(
                debate, users, room=1, mode=debate.assignment_mode
            )
    elif len(users) <= 9:
        debate.style = "BP"
        return assign_bp_single_room(
            debate, users, room=1, mode=debate.assignment_mode
        )
    else:
        mid = len(users) // 2
        if debate.assignment_mode == "True random":
            ok1, msg1 = assign_opd_single_room_true_random(
                debate, users[:mid], room=1
            )
        else:
            ok1, msg1 = assign_opd_single_room(
                debate, users[:mid], room=1, mode=debate.assignment_mode
            )
        ok2, msg2 = assign_bp_single_room(
            debate, users[mid:], room=2, mode=debate.assignment_mode
        )
        return ok1 and ok2, f"Dynamic: {msg1}; {msg2}"


def infer_debate_style(letters):
    letters = list(set(letters))
    if len(letters) == 1:
        if letters[0] == 'O':
            return "OPD"
        else:
            return "BP"
    else:
        return "Dynamic"
        
def assign_dynamic(debate, users, scenario=None):
    """Assign speakers using a selected scenario."""
    
    # Fallback to old heuristic if no scenario is provided
    if not scenario:
        return fallback_heuristic(debate, users)

    room_types = {"O": ("OPD", 7, 12), "B": ("BP", 9, 11)}
    #special case of 13 participants, which is a larger than usual OPD room
    if len(users) == 13:
        room_types = {"O": ("OPD", 7, 13), "B": ("BP", 9, 11)}
    letters = scenario.split("-")
    #this will change the debate style if a scenario with only OPD or only BP rooms is selected
    debate.style = infer_debate_style(letters) 
    try:
        settings = [room_types[c.upper()] for c in letters]
    except KeyError:
        return False, "Unknown scenario"

    counts = _compute_room_counts(len(users), [(s[1], s[2]) for s in settings])
    if counts is None:
        return False, "Participant count doesn't fit the selected scenario"

    #try to ensure that there is a user of chair skill in each room
    rooms, unsafe, msg = _allocate_by_mode(
        users, counts, settings, debate.assignment_mode
    )
    if msg:
        return False, msg

    messages = []
    success = True
    for i, (room_users, spec) in enumerate(zip(rooms, settings), start=1):
        if spec[0] == "OPD":
            ok, msg = assign_opd_single_room(
                debate, room_users, room=i, mode=debate.assignment_mode
            )
        else:
            ok, msg = assign_bp_single_room(
                debate, room_users, room=i, mode=debate.assignment_mode
            )
        success = success and ok
        messages.append(msg)

    if unsafe:
        messages.append("Fallback Chairs were used")

    if success:
        debate.assignment_complete = True
        db.session.commit()
    return success, " | ".join(messages)
