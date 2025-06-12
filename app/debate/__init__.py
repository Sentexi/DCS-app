from flask import Blueprint

debate_bp = Blueprint('debate', __name__)

from . import routes  # noqa: E402
