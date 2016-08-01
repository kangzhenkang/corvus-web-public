# -*- coding: utf-8 -*-

from __future__ import absolute_import

from werkzeug.routing import BaseConverter
from flask import Flask, jsonify

from .models import init_db
from .huskar import huskar_client, sash_client


class NotConverter(BaseConverter):
    regex = '(?!static|api).*'


def create_app():
    app = Flask(__name__)
    app.config['BUNDLE_ERRORS'] = True
    app.config.from_object('corvus_web.config')
    app.config.from_envvar('CORVUS_WEB_CONFIG', silent=True)
    init_db(app)
    huskar_client.init_app(app)
    sash_client.init_app(app)

    def _msg(e):
        return e.description if hasattr(e, 'description') else str(e)

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify(message=_msg(e), status=-1), 500

    @app.errorhandler(400)
    def invalid_input(e):
        return jsonify(message=_msg(e), status=-1), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(message=_msg(e), status=-1), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify(message=_msg(e), status=-1), 405

    @app.errorhandler(406)
    def not_acceptable(e):
        return jsonify(message=_msg(e), status=-1), 406

    @app.errorhandler(409)
    def conflict(e):
        return jsonify(message=_msg(e), status=-1), 409
    return app


def create_api_app():
    from .api.action import init_api
    from .api.restapi import init_restapi
    from .api.db import init_db_api

    app = create_app()
    init_db_api(app)
    init_restapi(app)
    init_api(app)
    return app


def create_web_app():
    app = create_api_app()
    app.url_map.converters['not'] = NotConverter

    @app.route('/<not:anything>')
    def index(anything):
        return app.send_static_file('template/index.html')
    return app
