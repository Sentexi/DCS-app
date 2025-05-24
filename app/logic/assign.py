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
    Assigns OPD slots for one room.
    """
    # 1. Separate judges (Wing/Chair) and eligible for chair
    judges = [u for u in users if (u.judge_skill in ('Wing','Chair'))]
    chairs = [u for u in judges if u.judge_skill == 'Chair']
    wings  = [u for u in judges if u.judge_skill == 'Wing']
    non_judges = [u for u in users if u not in judges]
    # 2. Always at least one chair; if not present, promote random wing (if available)
    if not chairs:
        if wings:
            promoted = random.choice(wings)
            promoted.judge_skill = 'Chair'
            chairs.append(promoted)
            wings.remove(promoted)
        else:
            return False, "No eligible chair judge in participants."
    # 3. Assign main speakers (6)
    # At least two teams, each with at least one Intermediate or better
    # (Add this skill-balancing logic if you like; for now, random)
    first_timers = [u for u in non_judges if u.debate_skill == "First Timer"]
    free_speakers_pool = [u for u in non_judges if u.debate_skill != "First Timer"]
    team_speakers = non_judges.copy()
    if len(users) >= 6:
        main_speakers = team_speakers[:6]
        remaining = team_speakers[6:]
    else:
        return False, "Not enough speakers for 6 team slots."
    # 4. Fill out judges and free speakers as needed
    num_judges = min(3, len(judges))
    num_free = max(1, len(users) - (6 + num_judges))
    slots = []
    # Assign main speakers to roles (3 gov, 3 opp)
    for idx, user in enumerate(main_speakers):
        team = "Gov" if idx < 3 else "Opp"
        pos  = idx % 3 + 1
        slots.append(SpeakerSlot(debate_id=debate.id, user_id=user.id, role=f"{team}-{pos}", room=room))
    # Assign judges: chair first, then wings
    if chairs:
        slots.append(SpeakerSlot(debate_id=debate.id, user_id=chairs[0].id, role="Judge-Chair", room=room))
    for w in wings[:num_judges-1]:
        slots.append(SpeakerSlot(debate_id=debate.id, user_id=w.id, role="Judge-Wing", room=room))
    # Assign free speakers (remaining non-judges who aren't First Timers)
    for idx, user in enumerate(remaining[:num_free]):
        slots.append(SpeakerSlot(debate_id=debate.id, user_id=user.id, role=f"Free-{idx+1}", room=room))
    # Save assignments (prevent duplicates)
    for slot in slots:
        exists = SpeakerSlot.query.filter_by(debate_id=debate.id, user_id=slot.user_id, room=room).first()
        if not exists:
            db.session.add(slot)
    db.session.commit()
    return True, f"Room {room}: Speaker assignment complete."

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
