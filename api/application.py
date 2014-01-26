from flask import render_template
from flask import jsonify
from flask import request
from api import api_app
from flask import make_response, Response
import game
import json


@api_app.route("/initial_board", methods=["GET"])
def initial_board():
#     key = request.form["key"]
#     if not key:
#         raise Exception
    game_engine = game.make_game_engine(game.player_down)
    json_dict = game_engine.board.json_dict()
    return Response(json.dumps(str(json_dict)),  mimetype='application/json')