from statistics import median
from flask import render_template
from flask_login import login_required

from app.extensions import db
from app.models import OpdResult, SpeakerSlot, Score, User

from . import analytics_bp


@analytics_bp.route('/analytics')
@login_required
def analytics_dashboard():
    # Collect all OPD scores
    scores = [r.points for r in OpdResult.query.all() if r.points is not None]

    # Gather points per debate and room
    query = (
        db.session.query(OpdResult.debate_id, SpeakerSlot.room, OpdResult.points)
        .join(
            SpeakerSlot,
            (OpdResult.debate_id == SpeakerSlot.debate_id)
            & (OpdResult.user_id == SpeakerSlot.user_id),
        )
    )
    data = {}
    for debate_id, room, points in query.all():
        data.setdefault(room, {}).setdefault(debate_id, []).append(points)

    # Calculate median for each debate/room
    room_medians = {}
    for room, debates in data.items():
        room_medians[room] = {deb_id: median(vals) for deb_id, vals in debates.items()}

    # Prepare labels and datasets for Chart.js
    labels = sorted({deb_id for debates in data.values() for deb_id in debates.keys()})
    datasets = []
    for room in sorted(room_medians.keys()):
        datasets.append(
            {
                'label': f'Room {room}',
                'data': [room_medians[room].get(debate_id) for debate_id in labels],
            }
        )

    # Calculate average score per judge
    judge_stats = (
        db.session.query(User.first_name, User.last_name, db.func.avg(Score.value))
        .join(Score, Score.judge_id == User.id)
        .group_by(User.id)
        .all()
    )
    judge_labels = [f"{fn} {ln}".strip() for fn, ln, _ in judge_stats]
    judge_averages = [avg for _, _, avg in judge_stats]

    return render_template(
        'analytics/analytics.html',
        hist_data=scores,
        labels=labels,
        datasets=datasets,
        judge_labels=judge_labels,
        judge_averages=judge_averages,
    )
