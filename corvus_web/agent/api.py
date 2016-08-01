# -*- coding: utf-8 -*-

from __future__ import absolute_import

import os
import json
import logging

from psutil import virtual_memory
from flask import Blueprint, request, jsonify, abort
from ..models import Task
from .helpers import parse_corvus_conf, get_proxy_ini, parse_proxy_ini, \
    program_running

logger = logging.getLogger(__name__)


agent = Blueprint('agent', __name__)


@agent.route('/proxy/create', methods=['POST'])
def create_proxy():
    payload = request.get_json()
    if 'node' not in payload or 'cluster' not in payload:
        abort(406, 'node and cluster must be configured')

    task = Task.add('create_proxy', json.dumps(payload))
    return jsonify(status=0, task_id=task['id'])


@agent.route('/proxy/delete', methods=['POST'])
def delete_proxy():
    payload = request.get_json()
    task = Task.add('delete_proxy', json.dumps(payload))
    return jsonify(status=0, task_id=task['id'])


@agent.route('/proxy/update', methods=['POST'])
def update_proxy():
    payload = request.get_json()
    if 'bind' not in payload:
        abort(406, '`bind` must be set')

    cluster_id = payload['cluster_id']

    task = Task.add('update_proxy', json.dumps(payload), sync=True,
                    cluster_id=cluster_id)
    return jsonify(status=0, task_id=task['id'])


@agent.route('/proxy/info/<int:port>', methods=['GET'])
def proxy_info(port):
    etc = '/etc/corvus/corvus-{}.conf'.format(port)
    if not os.path.exists(etc):
        abort(404, 'No proxy')

    conf = parse_corvus_conf(open(etc).read())
    ini_files = get_proxy_ini(port)
    if not ini_files:
        abort(404, 'No proxy')

    for ini in ini_files:
        version, program = parse_proxy_ini(ini)
        if program_running(program):
            break
    conf['version'] = version
    conf['bind'] = int(conf['bind'])
    if 'thread' in conf:
        conf['thread'] = int(conf['thread'])
    if 'server_timeout' in conf:
        conf['server_timeout'] = int(conf['server_timeout'])
    if 'client_timeout' in conf:
        conf['client_timeout'] = int(conf['client_timeout'])
    if 'bufsize' in conf:
        conf['bufsize'] = int(conf['bufsize'])
    return jsonify(conf=conf, status=0)


@agent.route('/task/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = Task.get(task_id)
    if not task:
        abort(404)

    return jsonify(task=task, status=0)


@agent.route('/ping', methods=['GET'])
def ping():
    import corvus_web
    return jsonify(status=0, version=corvus_web.__version__)


@agent.route('/update', methods=['POST'])
def agent_update():
    import corvus_web
    payload = request.get_json()
    version = payload['version']
    if version == corvus_web.__version__:
        return jsonify(status=0)

    task = Task.add('update_agent', json.dumps(payload))
    return jsonify(status=0, task_id=task['id'])


@agent.route('/redis/deploy', methods=['POST'])
def add_redis_deploy_task():
    payload = request.get_json()
    task = Task.add('deploy_redis', json.dumps(payload))
    return jsonify(status=0, task_id=task['id'])


@agent.route('/total_mem', methods=['GET'])
def get_total_mem():
    total_mem = virtual_memory().total
    return jsonify(status=0, total_mem=total_mem)
