# -*- coding: utf-8 -*-

from __future__ import absolute_import

import datetime
import logging

from flask import current_app
from flask_restless import APIManager
from ruskit.cluster import ClusterNode

import corvus_web.agent.remote as remote

from ..models import db, Node, Cluster, Proxy, Task, Agent, RemoteTask
from ..utils import get_proxy_info, ip
from ..cache import node_cache

logger = logging.getLogger(__name__)


def init_restapi(app):
    manager = APIManager(app, flask_sqlalchemy_db=db)

    manager.create_api(
        Task,
        methods=['GET'],
        postprocessors={
            'GET_SINGLE': [post_get_task],
            'GET_MANY': [post_get_tasks]
        }
    )

    manager.create_api(
        Cluster,
        methods=['GET', 'PUT'],
        postprocessors={
            'GET_MANY': [post_get_clusters],
            'GET_SINGLE': [post_get_cluster]
        },
    )

    manager.create_api(
        Node,
        max_results_per_page=16384,
        methods=['GET', 'DELETE'],
        postprocessors={
            'GET_SINGLE': [post_get_node],
            'GET_MANY': [post_get_nodes]
        }
    )

    manager.create_api(
        Proxy,
        methods=['GET'],
        postprocessors={
            'GET_MANY': [post_get_proxies]
        }
    )

    manager.create_api(Agent, methods=['GET', 'PUT', 'POST', 'DELETE'])


def fmt(date):
    try:
        return datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        # for sqlite
        return datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')


def set_node_info(result, info):
    result.update({
        'id': info['id'],
        'version': info['redis_version'],
        'usedMemory': info['used_memory'],
        'maxMemory': info['maxmemory'],
        'slots': info['slots'],
        'userCpu': info['used_cpu_user'],
        'sysCpu': info['used_cpu_sys'],
        'totalRunTime': info['uptime_in_seconds'],
        'rss': info['used_memory_rss'],
        'keyspaceHits': info['keyspace_hits'],
        'keyspaceMisses': info['keyspace_misses'],
        'expiredKeys': info['expired_keys'],
        'evictedKeys': info['evicted_keys'],
        'idle': True,
        'role': info['role'],
        'connectedClients': info['connected_clients'],
        'totalCommandsProcessed': info['total_commands_processed'],
    })
    if 'db0' in info:
        result.update({
            'totalKeys': info['db0']['keys'],
            'expiresKeys': info['db0']['expires'],
        })
    else:
        result.update({
            'totalKeys': 0,
            'expiresKeys': 0,
        })


def node_info(node):
    info = node.info()
    conf = node.node_info  # will trigger CLUSTER NODES
    info['id'] = conf['name']
    info['slots'] = len(conf['slots'])
    try:
        info['maxmemory'] = int(node.execute_command('{} get maxmemory'.format(
            current_app.config['REDIS_CONFIG_CMD']))[1])
    except:
        info['maxmemory'] = 0
    return info


def get_node_info(data):
    data['nodeId'] = data['id']
    data['alive'] = True
    data['clusterId'] = data['cluster_id']

    try:
        node = ClusterNode(data['host'], data['port'])
        info = node_info(node)
        set_node_info(data, info)

        if data['cluster_id'] == -1:
            return data

        c = Cluster.get(data['cluster_id'])
        if not c:
            return data

        data['clusterName'] = c['name']
        data['idle'] = False
    except Exception as e:
        logger.warning(e)
        data['alive'] = False

    return data


def post_get_clusters(result=None, **kwargs):
    for obj in result['objects']:
        post_get_cluster(result=obj)


def post_get_cluster(result=None, **kwargs):
    result['node_count'] = Node.get_count(result['id'])
    result['proxy_count'] = Proxy.get_count(result['id'])

    try:
        cluster_info = node_cache.get_cluster_info(result['id'])
        result.update(cluster_info)
    except Exception as e:
        logger.exception(e)


def post_get_node(result=None, **kwargs):
    get_node_info(result)


def post_get_nodes(result=None, **kwargs):
    for node in result['objects']:
        post_get_node(node)


def post_get_proxies(result=None, **kwargs):
    setted = False

    for proxy in result['objects']:
        info = get_proxy_info(proxy['host'], proxy['port'])
        proxy.update({'alive': False, 'version': 'unknown'})
        if info:
            proxy['alive'] = True
            proxy['version'] = info.get('version', 'unknown')
            proxy['threadsNum'] = info.get('threads', 'unknown')
            proxy['completedCommands'] = info.get('completed_commands',
                'unknown')
            proxy['connectedClients'] = info.get('connected_clients',
                'unknown')

        if not setted and info and 'cluster' in info and \
                proxy['cluster_id'] != -1:
            Cluster.update(proxy['cluster_id'], name=info['cluster'])
            setted = True

        proxy['canUpdate'] = False
        if Agent.get_port(ip(proxy['host'])):
            proxy['canUpdate'] = True


def post_get_task(result=None, **kwargs):
    remote_id = result['remote_id']
    if remote_id == -1:
        return

    remote_task = RemoteTask.get(remote_id)
    extra = {}

    if not remote_task:
        status = Task.FAILED
        reason = 'No remote task'
    else:
        try:
            r = remote.get_task(remote_task['remote_host'],
                                remote_task['remote_port'],
                                remote_task["remote_id"])
        except Exception as e:
            logger.exception(e)
            return
        if r['status'] != 0:
            status = Task.FAILED
            reason = r['message']
        else:
            task = r['task']
            status = task['status']
            reason = task['reason']
            extra = {'created_at': fmt(task['created_at']),
                     'updated_at': fmt(task['updated_at'])}

    Task.update(result['id'], status=status, reason=reason, **extra)
    Task.set_status(result['id'], status, reason=reason)
    result['status'] = status
    result['reason'] = reason


def post_get_tasks(result=None, **kwargs):
    for task in result['objects']:
        post_get_task(task)
