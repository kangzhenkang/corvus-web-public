# -*- coding: utf-8 -*-

from __future__ import absolute_import

from flask import Blueprint, jsonify

from ..models import Node, Proxy

api = Blueprint('db_api', __name__)


def init_db_api(app, url_prefix='/api/db'):
    app.register_blueprint(api, url_prefix=url_prefix)


@api.route('/node', methods=['GET'])
def query_nodes():
    res = list(Node.all())
    return jsonify(nodes=res)


@api.route('/proxy', methods=['GET'])
def query_proxies():
    res = list(Proxy.all())
    return jsonify(proxies=res)
