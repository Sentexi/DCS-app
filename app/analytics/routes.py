from statistics import median
from flask import render_template
from flask_login import login_required

from app.extensions import db
from app.models import OpdResult, SpeakerSlot

from . import analytics_bp


@analytics_bp.route("/analytics")
@login_required
def analytics_dashboard():
    # Collect all OPD scores
    scores = [r.points for r in OpdResult.query.all() if r.points is not None]

    # Gather points per debate and room
    query = db.session.query(
        OpdResult.debate_id, SpeakerSlot.room, OpdResult.points
    ).join(
        SpeakerSlot,
        (OpdResult.debate_id == SpeakerSlot.debate_id)
        & (OpdResult.user_id == SpeakerSlot.user_id),
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
                "label": f"Room {room}",
                "data": [room_medians[room].get(deb_id) for deb_id in labels],
            }
        )

    return render_template(
        "analytics/analytics.html",
        hist_data=scores,
        labels=labels,
        datasets=datasets,
    )
