"""
User challenge API endpoints - list user's challenges & issue new ones
"""

import flask
import sqlalchemy

from .. import model, util

from . import util as api_util
from .blueprint import web_api


@web_api.route("/user/<int:intended_user>/challenge", methods=["GET"])
@util.cross_origin(methods=["GET", "POST"])
def get_user_challenges(intended_user):
    pass

@web_api.route("/user/<int:intended_user>/challenge", methods=["POST"])
@util.cross_origin(methods=["GET", "POST"])
@api_util.requires_login(accept_key=False)
@api_util.requires_competition_open
def create_challenge(intended_user, *, user_id):
    if user_id != intended_user:
        raise api_util.user_mismatch_error()

    with model.engine.connect() as conn:
        num_challenges = conn.execute(
            sqlalchemy.sql.select([
                sqlalchemy.sql.func.count(),
            ]).select_from(
            ).where(
            )
        ).first()[0]
