"""
User challenge API endpoints - list user's challenges & issue new ones
"""
import datetime

import flask
import sqlalchemy

from .. import model, util

from . import util as api_util
from .blueprint import web_api


def make_challenge_record(challenge, participants):
    result = {
        "challenge_id": challenge["id"],
        "created": challenge["created"],
        "finished": challenge["finished"],
        "num_games": challenge["num_games"],
        "issuer": challenge["issuer"],
        "winner": challenge["winner"],
        "players": {},
    }

    for participant in participants:
        result["players"][participant["user_id"]] = {
            "username": participant["username"],
            "points": participant["version_number"],
            "is_issuer": participant["user_id"] == result["issuer"],
        }

    return result


@web_api.route("/user/<int:intended_user>/challenge", methods=["GET"])
@util.cross_origin(methods=["GET", "POST"])
def get_user_challenges(intended_user):
    offset, limit = api_util.get_offset_limit()
    where_clause, order_clause, manual_sort = api_util.get_sort_filter({
        "issuer": model.challenges.c.issuer,
        "created": model.challenges.c.created,
        "finished": model.challenges.c.finished,
        "num_games": model.challenges.c.num_games,
    }, ["finished"])

    participant_clause = model.challenge_participants.c.user_id == intended_user
    for (field, _, _) in manual_sort:
        if field == "finished":
            where_clause &= model.challenges.c.status == "finished"

    with model.engine.connect() as conn:
        query = sqlalchemy.sql.select([
            model.challenges.c.id,
            model.challenges.c.created,
            model.challenges.c.finished,
            model.challenges.c.num_games,
            model.challenges.c.issuer,
            model.challenges.c.winner,
        ]).select_from(model.games.join(
            model.challenge_participants,
            (model.challenges.c.id == model.challenge_participants.c.game_id)
        )).where(
            where_clause &
            sqlalchemy.sql.exists(
                model.challenge_participants.select(
                    participant_clause &
                    (model.challenge_participants.c.game_id == model.challenges.c.id)
                )
            )
        ).order_by(
            *order_clause
        ).offset(offset).limit(limit).reduce_columns()

        challenges = conn.execute(query)
        result = []
        for challenge in challenges.fetchall():
            participants = conn.execute(
                model.challenge_participants.join(
                    model.users,
                    model.challenge_participants.c.user_id == model.users.c.id
                ).select(
                    model.challenge_participants.c.challenge_id == challenge["id"]
                )
            )

            result.append(make_challenge_record(challenge, participants))

        return flask.jsonify(result)


@web_api.route("/user/<int:intended_user>/challenge", methods=["POST"])
@util.cross_origin(methods=["GET", "POST"])
@api_util.requires_login(accept_key=False)
@api_util.requires_competition_open
def create_challenge(intended_user, *, user_id):
    if user_id != intended_user:
        raise api_util.user_mismatch_error()

    challenge_body = flask.request.get_json()
    if "opponents" not in challenge_body:
        raise util.APIError(400, message="Must provide array of opponent IDs.")

    opponents = challenge_body["opponents"]
    if len(opponents) not in (1, 3):
        raise util.APIError(400, message="Must provide 1 or 3 opponents.")

    with model.engine.connect() as conn:
        sqlfunc = sqlalchemy.sql.func

        opponents_exist = [row["id"] for row in conn.execute(
            sqlalchemy.sql.select([
                model.users.c.id,
            ]).select_from(
                model.users
            ).where(
                model.users.c.id.in_(opponents)
            )
        ).fetchall()]

        if len(opponents_exist) != len(opponents):
            raise util.APIError(400, message="Opponents {} do not exist.".format(
                ", ".join(set(opponents) - set(opponents_exist))
            ))

        num_challenges = conn.execute(
            sqlalchemy.sql.select([
                sqlfunc.count(),
            ]).select_from(
                model.challenges
            ).where(
                (model.challenge.c.issuer == user_id) &
                (model.challenge.c.created >= sqlfunc.date_add(
                    sqlfunc.now(), datetime.timedelta(days=-1)))
            )
        ).first()[0]

        if num_challenges >= 3:
            raise util.APIError(
                400,
                message="Can't issue more than 3 challenges in a 24 hour period."
            )

        with conn.begin() as transaction:
            challenge_id = conn.execute(model.challenges.insert().values(
                issuer=user_id,
            )).inserted_primary_key[0]

            opponents.append(user_id)
            for participant in opponents:
                conn.execute(model.challenge_participants.insert().values(
                    challenge_id=challenge_id,
                    user_id=participant,
                ))

        return util.response_success({
            "challenge_id": challenge_id,
        }, status_code=201)
