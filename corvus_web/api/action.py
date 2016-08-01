# -*- coding: utf-8 -*-

from __future__ import absolute_import

import os
import json
import logging
import redis
import requests
import random
import sqlalchemy
import uuid
from itertools import groupby

import corvus_web.agent.remote as remote

from flask import Blueprint, request, jsonify, abort, current_app, \
    send_from_directory
from ruskit.cluster import ClusterNode, Cluster as RedisCluster

from ..models import Task, Node, Cluster, Proxy, RemoteTask, Agent, PAGE_SIZE
from ..utils import get_proxy_info, ip, validate_memory, sort_groupby, split_addr
from ..huskar import register_proxy, deregister_proxy
from ..cache import NodeCache
from ..task.worker import gen_deploy_tasks, all_versions_installed

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__)


def gen_name():
    return uuid.uuid4().get_hex()[0:7]


def init_api(app, url_prefix='/api'):
    app.register_blueprint(api, url_prefix=url_prefix)


def create_proxy_update_task(payload, agent_host, agent_port, config):
    data = remote.update_proxy(agent_host, agent_port, config)
    remote_id = data.get('task_id', -1)
    if remote_id == -1:
        return

    task = RemoteTask.add('remote_update_proxy', json.dumps(payload),
                          remote_id=remote_id, remote_host=agent_host,
                          remote_port=agent_port)

    version = config.get('version')
    if version:
        Proxy.add_many(payload['clusterId'], [{
            'host': agent_host,
            'port': config['bind'],
            'version': version
        }])

    return task


def create_agent_update_task(item):
    """
    item: host, port, newVersion
    """
    host = ip(item['host'])
    data = remote.agent_update(host, item['port'], item['newVersion'])
    remote_id = data.get('task_id', -1)
    if remote_id == -1:
        return
    task = RemoteTask.add('remote_agent_update', json.dumps(item),
                          remote_id=remote_id, remote_host=host,
                          remote_port=item['port'])
    return task


@api.route('/cluster/create', methods=['POST'])
def create_cluster():
    payload = request.get_json()
    if not payload['nodes']:
        abort(406, message='没有节点')

    payload['slaves'] = int(payload['slaves'])

    max_slaves = int(len(payload['nodes']) / 3 - 1)
    max_slaves = 0 if max_slaves < 0 else max_slaves

    if payload['slaves'] > max_slaves:
        abort(406, '最大从节点数为 {}'.format(max_slaves))

    if len(payload['nodes']) > 300:
        abort(400, u'集群节点数不可超过300')

    if Cluster.get_by_name(payload['name']):
        abort(406, '集群名称 {} 已被占用'.format(payload['name']))

    task = Task.add('create_cluster', json.dumps(payload), sync=False)
    return jsonify(status=0, task_id=task['id'])


@api.route('/cluster/<host>/<int:port>', methods=['GET', 'POST'])
def get_cluster_by_host(host, port):
    cluster = None
    try:
        cluster = RedisCluster.from_node(ClusterNode(host, port))
        for n in cluster.nodes:
            n.ping()
    except Exception:
        cluster = None

    if request.method == 'GET':
        if not cluster:
            return jsonify(nodes=[])

        nodes = []
        try:
            for node in cluster.nodes:
                nodes.append({
                    'id': node.name,
                    'host': node.host,
                    'port': node.port,
                    'role': 'master' if node.is_master() else 'slave'
                })
        except Exception:
            pass

        return jsonify(nodes=nodes)
    if request.method == 'POST':
        payload = request.get_json()
        nodes = cluster.nodes
        new_nodes, update_nodes = [], []
        cluster_id = None
        for n in nodes:
            node = Node.get_by_address(n.host, n.port)
            if not node:
                new_nodes.append({'host': n.host, 'port': n.port})
            elif node['cluster_id'] <= 0:
                update_nodes.append(node)
            else:
                cluster_id = node['cluster_id']

        if not cluster_id or not Cluster.get(cluster_id):
            cluster_name = payload.get('name', '').strip()
            cluster_name = cluster_name or uuid.uuid4().get_hex()[0:7]

            c = Cluster.add(description=payload.get('description', ''),
                            name=cluster_name)
            cluster_id = c['id']
        for n in new_nodes:
            n['cluster_id'] = cluster_id
            Node.add(**n)

        for n in update_nodes:
            Node.update(n['id'], cluster_id=cluster_id)
        return jsonify(status=0)


@api.route('/cluster/migrate', methods=['POST'])
def migrate():
    payload = request.get_json()
    task = Task.add('cluster_migrate', json.dumps(payload),
                    sync=True, cluster_id=payload['clusterId'])
    return jsonify(task_id=task['id'])


@api.route('/cluster/reshard', methods=['POST'])
def reshard():
    payload = request.get_json()
    task = Task.add('cluster_reshard', json.dumps(payload),
                    sync=True, cluster_id=payload['clusterId'])
    return jsonify(task_id=task['id'])


@api.route('/cluster/delete/<int:cluster_id>', methods=['POST'])
def cluster_delete(cluster_id):
    c = Cluster.get(cluster_id)
    if not c or c['deleted']:
        return jsonify(status=0)

    if Proxy.get_cluster_proxy(c['id']):
        abort(406, u'proxy 未删除, 不能解散集群')

    node = Node.get_cluster_node(c['id'])
    if not node:
        return jsonify(status=0)

    task = Task.add('destroy_cluster', json.dumps({
        'cluster_id': c['id'],
        'host': node['host'],
        'port': node['port']
    }), sync=True, cluster_id=cluster_id)
    return jsonify(task_id=task['id'])


@api.route('/cluster/info/<int:cluster_id>', methods=['GET'])
def cluster_info(cluster_id):
    node = Node.get_cluster_node(cluster_id)
    if not node:
        return jsonify(nodes=[])

    def _address(a):
        host, port = split_addr(a)
        return {'host': host, 'port': int(port)}

    nodes = []
    cluster = RedisCluster.from_node(ClusterNode(node['host'], node['port']))
    for m in cluster.masters:
        item = {'master': {'host': m.host, 'port': m.port}}
        item['slaves'] = [_address(s['addr']) for s in m.slaves(m.name)]
        nodes.append(item)
    nodes.sort(key=lambda x: (x['master']['host'], x['master']['port']))
    return jsonify(nodes=nodes)


@api.route('/node/update/<int:cluster_id>', methods=['PUT'])
def node_update(cluster_id):
    items = request.get_json()
    nodes = []
    for item in items:
        nodes.append(item['master'])
        nodes.extend(item['slaves'])

    for node in nodes:
        Node.upsert(node['host'], node['port'], cluster_id=cluster_id)
    return jsonify(status=0)


@api.route('/node/quit', methods=['POST'])
def node_quit():
    payload = request.get_json()
    cluster_id = payload['clusterId']
    if len(Node.get_cluster_nodes(cluster_id)) == len(payload['nodes']):
        abort(400, u'禁止删除所有节点,请使用删除集群')

    task = Task.add('node_quit', json.dumps(payload),
                    sync=True, cluster_id=payload['clusterId'])
    return jsonify(task_id=task['id'])


@api.route('/node/add', methods=['POST'])
def node_add():
    payload = request.get_json()
    nodes = payload['nodes']
    current_node = ClusterNode(payload['current']['host'],
                               payload['current']['port'])
    cluster = RedisCluster.from_node(current_node)
    master_ids = [m.name for m in cluster.masters]

    if len(nodes) > 1000:
        abort(400, u'禁止添加超过1000个节点')

    for n in nodes:
        role = n.get('role')
        if 'addr' not in n or not role or \
                role not in ('slave', 'master') or \
                role == 'slave' and n['master'] not in master_ids:
            abort(406, '格式错误')

    task = Task.add('node_add', json.dumps(payload),
                    sync=True, cluster_id=payload['clusterId'])
    return jsonify(task_id=task['id'], status=0)


@api.route('/node/register', methods=['POST'])
def node_register():
    payload = request.get_json()
    for node in payload.get('nodes', []):
        host = ip(node['host'])
        try:
            port = int(node['port'])
        except Exception:
            continue

        if Node.get_by_address(host, port):
            continue

        Node.add(host=host, port=port)
    return jsonify(status=0)


@api.route('/node/count/<int:cluster_id>', methods=['GET'])
def get_node_count(cluster_id):
    nodes = Node.get_cluster_nodes(cluster_id)
    if not nodes:
        return jsonify(masters=0, slaves=0)

    NO_RETRY = -1
    for n in nodes:
        try:
            cluster = RedisCluster.from_node(ClusterNode(n['host'], n['port'],
                retry=NO_RETRY))
            masters = len(cluster.masters)
            return jsonify(
                masters=masters, slaves=len(cluster.nodes) - masters)
        except:
            pass
    return jsonify(masters=0, slaves=0)


@api.route('/node/masters/<int:cluster_id>', methods=['GET'])
def get_master_nodes(cluster_id):
    node = Node.get_cluster_node(cluster_id)
    if not node:
        return jsonify(nodes=[])
    cluster = RedisCluster.from_node(ClusterNode(node['host'], node['port']))
    nodes = [{'id': m.name, 'host': m.host, 'port': m.port}
             for m in cluster.masters]
    nodes.sort(key=lambda x: (x['host'], x['port']))
    return jsonify(nodes=nodes)


@api.route('/node/masters/<int:cluster_id>/sample', methods=['GET'])
def get_master_nodes_for_corvus(cluster_id):
    try:
        limit = int(request.args.get('limit', 3))
    except Exception:
        abort(400, u'limit 输入参数不正确')

    node = Node.get_cluster_node(cluster_id)
    if not node:
        return jsonify(nodes=[])
    cluster = RedisCluster.from_node(ClusterNode(node['host'], node['port']))
    nodes = sort_groupby(cluster.masters, lambda m: m.host)
    nodes = random.sample(nodes, min((len(nodes), limit)))
    for _, n in nodes:
        n[0].ping()
    nodes = [{'id': ns[0].name, 'host': ns[0].host, 'port': ns[0].port}
             for host, ns in nodes]
    return jsonify(nodes=nodes)


# flask_restless can't post many
@api.route('/proxy/add', methods=['POST'])
def proxy_add():
    payload = request.get_json()

    valid = []
    for proxy in payload['proxies']:
        info = get_proxy_info(proxy['host'], proxy['port'])
        if not info or not info.get('remotes'):
            valid.append(proxy)
            continue
        remotes = info['remotes'].split(',')
        try:
            host, port = split_addr(remotes[0])
        except ValueError:
            valid.append(proxy)
            continue
        node = Node.get_by_address(host, port)
        if not node:
            valid.append(proxy)
            continue
        if node['cluster_id'] == payload['clusterId']:
            valid.append(proxy)
    if not valid:
        abort(406, '没有有效的代理')

    proxy_ids = Proxy.add_many(payload['clusterId'], valid)
    return jsonify(status=0, proxy_ids=proxy_ids)


@api.route('/remote/proxy/delete', methods=['POST'])
def remote_proxy_delete():
    payload = request.get_json()
    all_proxies = Proxy.get_many(payload['proxies'])
    if len(all_proxies) != len(payload['proxies']):
        abort(406, u'proxy 不存在')
    for p in all_proxies:
        host = p['host']
        if Agent.get_port(host) is None:
            abort(406, u"agent {} 不存在".format(host))

    for host, proxies in sort_groupby(all_proxies, lambda p: p['host']):
        agent_port = Agent.get_port(host)
        data = {
            'proxies': [p['id'] for p in proxies],
            'ports': [p['port'] for p in proxies],
            'web_address': current_app.config['WEB_ADDRESS'],
        }
        try:
            res = remote.delete_proxy(host, agent_port, data)
        except Exception as e:
            logger.exception('remote delete proxy failed')
            res = {'status': -1, 'message': e.message}
        if res.get('status') != 0:
            Task.create_fail(
                'delete_proxy',
                json.dumps(data),
                'unexpected error in agent {}:{} {}'.format(
                    host, port, res.get('message') or ''),
                res.get('task_id') or -1)
        else:
            RemoteTask.add('delete_proxy', json.dumps(payload),
                           remote_id=res.get('task_id'), remote_host=host,
                           remote_port=agent_port)
    return jsonify(status=0)


@api.route('/proxy/delete', methods=['POST'])
def proxy_delete():
    payload = request.get_json()
    Proxy.delete_many(payload['proxies'])
    return jsonify(status=0)


@api.route('/proxy/list')
def proxy_list():
    version = request.args.get('version')
    cluster = request.args.get('cluster')
    registered = request.args.get('registered')
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    if registered:
        registered = True if registered == 'true' else False

    res = Proxy.search((page - 1) * PAGE_SIZE, version=version,
                       cluster=cluster, registered=registered)

    for proxy in res['items']:
        info = get_proxy_info(proxy['host'], proxy['port'])
        proxy.update({'alive': False})
        if info:
            version = info.get('version', proxy['version'])
            if version != proxy['version']:
                Proxy.update(proxy['id'], version=version)
                proxy['version'] = version
            proxy.update({'alive': True})
    return jsonify(pages=res['pages'], page=page, count=res['count'],
                   items=res['items'])


@api.route('/proxy/updateAll', methods=['POST'])
def proxy_update_all():
    payload = request.get_json()
    version = payload.get('version')
    cluster = payload.get('cluster')
    new_version = payload['newVersion']
    page = 0

    registered = payload.get('registered')
    if registered:
        registered = True if registered == 'true' else False

    def _r(p):
        return Proxy.search(p * PAGE_SIZE, version=version, cluster=cluster,
                            registered=registered)

    res = _r(page)

    while True:
        for item in res['items']:
            host = ip(item['host'])
            port = Agent.get_port(host)
            if not port or new_version == item['version']:
                continue
            item.update({
                'clusterId': item['cluster_id'],
                'newVersion': new_version,
                'clusterCond': cluster,
                'versionCond': version
            })
            config = {
                'bind': item['port'],
                'version': new_version,
                'cluster_id': item['cluster_id']
            }
            try:
                create_proxy_update_task(item, host, port, config)
            except Exception as e:
                logger.exception(e)
                continue
        if len(res['items']) < PAGE_SIZE:
            break
        page += 1
        res = _r(page)
    return jsonify(status=0)


@api.route('/proxy/registerAll', methods=['POST'])
def proxy_register_all():
    payload = request.get_json()
    version = payload.get('version')
    cluster = payload.get('cluster')

    registered = payload.get('registered')
    if registered:
        registered = True if registered == 'true' else False

    def _r(p):
        return Proxy.search(p * PAGE_SIZE, version=version,
                            cluster=cluster, registered=registered)

    page = 0
    res = _r(page)

    while True:
        for item in res['items']:
            host = ip(item['host'])
            c = Cluster.get(item['cluster_id'])
            if not c:
                continue
            register_proxy(c['register_app'], c['register_cluster'],
                host, item['port'])
            Proxy.update(item['id'], registered=True)
        if len(res['items']) < PAGE_SIZE:
            break
        page += 1
        res = _r(page)
    return jsonify(status=0)


@api.route('/proxy/register', methods=['POST'])
def proxy_register():
    payload = request.get_json()
    host = ip(payload['host'])

    if 'register_app' not in payload or 'register_cluster' not in payload:
        c = Cluster.get(payload['cluster_id'])
        if not c:
            abort(406, '没有找到集群 {}'.format(payload['cluster_id']))
        payload['register_app'] = c['register_app']
        payload['register_cluster'] = c['register_cluster']
    register_proxy(payload['register_app'], payload['register_cluster'],
        host, payload['port'])
    Proxy.update(payload['id'], registered=True)
    return jsonify(status=0)


@api.route('/proxy/deregister', methods=['POST'])
def proxy_deregister():
    payload = request.get_json()
    host = ip(payload['host'])

    if 'register_app' not in payload or 'register_cluster' not in payload:
        c = Cluster.get(payload['cluster_id'])
        if not c:
            abort(406, '没有找到集群 {}'.format(payload['cluster_id']))
        payload['register_app'] = c['register_app']
        payload['register_cluster'] = c['register_cluster']
    deregister_proxy(payload['register_app'], payload['register_cluster'],
        host, payload['port'])
    Proxy.update(payload['id'], registered=False)
    return jsonify(status=0)


@api.route('/command/<host>/<int:port>/<command>', methods=['GET'])
def execute_command(host, port, command):
    r = redis.StrictRedis(host, port, socket_timeout=1)
    try:
        result = r.execute_command(command)
    except redis.RedisError as e:
        result = "Err: {}".format(e)
    return jsonify(result=result, status=0)


@api.route('/agent/add', methods=['POST'])
def agent_add():
    payload = request.get_json()
    for agent in payload['agents']:
        host = ip(agent['host'])
        port = agent['port']
        try:
            res = remote.ping(host, port)
            if res['status'] != 0:
                abort(406, '{}:{} 远端 agent 异常'.format(host, port))
        except requests.ConnectionError:
            abort(500, '{}:{} Connection error'.format(host, port))
        try:
            Agent.add(host, port)
        except sqlalchemy.exc.SQLAlchemyError:
            abort(500, '{}:{} 已被注册'.format(host, port))
    return jsonify(status=0)


@api.route('/agent/list')
def agent_list():
    host = request.args.get('host')
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    res = Agent.search((page - 1) * PAGE_SIZE, host=host)
    for item in res['items']:
        item.update({'alive': False, 'version': 'unknown'})
        try:
            r = remote.ping(item['host'], item['port'])
            if r['status'] != 0:
                continue
            item.update({'alive': True,
                         'version': r.get('version', 'unknown')})
        except requests.ConnectionError:
            continue
    return jsonify(pages=res['pages'], page=page, count=res['count'],
                   items=res['items'])


@api.route('/agent/updateAll', methods=['POST'])
def agent_update_all():
    payload = request.get_json()
    host = payload.get('host')
    if host:
        host = ip(host)
    version = payload['newVersion']
    page = 0

    def _r(p):
        return Agent.search(p * PAGE_SIZE, host=host)

    res = _r(page)
    while True:
        for item in res['items']:
            item['host'] = ip(item['host'])
            try:
                r = remote.ping(item['host'], item['port'])
                if r['status'] != 0 or 'version' not in r:
                    continue
                item['version'] = r['version']
            except requests.ConnectionError:
                continue
            if version == item['version']:
                continue
            item['newVersion'] = version
            try:
                create_agent_update_task(item)
            except Exception as e:
                logger.exception(e)
                continue
        if len(res['items']) < PAGE_SIZE:
            break
        page += 1
        res = _r(page)
    return jsonify(status=0)


def __check_proxy_node(nodes, cluster):
    for node_dsn in nodes:
        node_host, node_port = split_addr(node_dsn)
        n = Node.get_by_address(node_host, node_port)
        if n is None:
            abort(406, '节点不存在')
        if n['cluster_id'] != cluster['id']:
            abort(406, u'%s 节点不属于此集群' % node_dsn)


@api.route('/remote/proxy/create', methods=['POST'])
def proxy_create_view():
    payload = request.get_json()

    host = ip(payload['host'])
    port = Agent.get_port(host)
    if not port:
        abort(406, 'Agent 未注册')

    c = Cluster.get(payload['clusterId'])
    if not c or not c['name']:
        abort(406, '无此集群 {!r}'.format(payload['clusterId']))

    __check_proxy_node(payload['config']['node'].split(","), c)

    payload['config']['cluster'] = c['name']
    payload['config']['cluster_id'] = payload['clusterId']
    payload['config']['host'] = payload['host']
    payload['config']['web_address'] = current_app.config['WEB_ADDRESS']
    data = remote.create_proxy(payload['host'], port, payload['config'])
    remote_id = data.get('task_id', -1)
    if remote_id == -1:
        abort(500, '任务创建失败')

    task = RemoteTask.add('remote_create_proxy', json.dumps(payload),
                          remote_id=remote_id, remote_host=payload['host'],
                          remote_port=port)

    return jsonify(task_id=task['id'])


@api.route('/remote/proxy/update', methods=['POST'])
def proxy_update_view():
    payload = request.get_json()

    host = ip(payload['host'])
    port = Agent.get_port(host)
    if not port:
        abort(406, 'Agent 未注册')

    c = Cluster.get(payload['clusterId'])
    if not c or not c['name']:
        abort(406, '无此集群 {!r}'.format(payload['clusterId']))

    if 'node' in payload['config']:
        __check_proxy_node(payload['config']['node'].split(","), c)

    payload['config']['cluster_id'] = payload['clusterId']
    task = create_proxy_update_task(payload, host, port, payload['config'])
    if not task:
        abort(500, '任务创建失败')
    return jsonify(task_id=task['id'])


@api.route('/remote/proxy/info/<host>/<int:bind>', methods=['GET'])
def proxy_info_view(host, bind):
    port = Agent.get_port(ip(host))
    if not port:
        abort(406, 'Agent 未注册')

    data = remote.proxy_info(host, port, bind)
    return jsonify(**data)


@api.route('/remote/agent/update', methods=['POST'])
def agent_update_view():
    payload = request.get_json()
    task = create_agent_update_task(payload)
    if not task:
        abort(500, '任务创建失败')
    return jsonify(task_id=task['id'])


@api.route('/redis_package/<string:archive>', methods=['GET'])
def download_redis_archive(archive):
    path = current_app.config['REDIS_PACKAGE_PATH']
    path = os.path.join(path, 'packages')
    if not os.path.exists(os.path.join(path, archive)):
        abort(404, u'redis包不存在')
    return send_from_directory(path, archive)


@api.route('/redis/archive/names', methods=['GET'])
def get_redis_archives():
    versions = current_app.config['REDIS_VERSIONS']
    archives = ['redis-{}.tar.gz'.format(v) for v in versions]
    return jsonify(status=0, archives=archives)


@api.route('/redis_package/installed', methods=['GET'])
def is_redis_installed():
    return jsonify(status=0, installed=all_versions_installed(current_app))


@api.route('/redis_package', methods=['POST'])
def install_redis():
    if all_versions_installed(current_app):
        abort(409, u'redis已打包')
    task = Task.upsert_unfinished('gen_all_redis_package', json.dumps({}))
    return jsonify(status=0, task_id=task['id'])


@api.route('/remote/agent/redis/deploy', methods=['POST'])
def agent_deploy_redis():
    '''input: a list of {
        'host':xxx,
        'port': xxx,
        'maxmemory': xxx,
        'persistence': True/False,
        'archive': xxx,
    }
    '''
    if not all_versions_installed(current_app):
        abort(400, u'未打包redis')

    payload = request.get_json()

    nodes = []
    try:
        for d in payload:
            if not validate_memory(d['maxmemory']):
                abort(400, u'最大内存格式错误')
            d['host'] = ip(d['host'])
        for host, instances in groupby(payload, lambda d: d['host']):
            instances = list(instances)
            if len(instances) > 1000:
                abort(400, u'同一台机器不能部署超过1000个节点')
            nodes.append({
                'host': host,
                'ports': [n['port'] for n in instances],
                'maxmemorys': [n['maxmemory'] for n in instances],
                'persistences': [n['persistence'] for n in instances],
                'archives': [n['archive'] for n in instances],
                'agent_port': Agent.get_port(host),
            })
    except KeyError as e:
        abort(400, e.message)

    missing_agents = map(lambda n: n['host'],
        filter(lambda n: not n['agent_port'], nodes))
    if missing_agents:
        abort(400, u'{} 没有agent'.format(', '.join(missing_agents)))

    gen_deploy_tasks(nodes, current_app)

    return jsonify(status=0)


@api.route('/node/instances', methods=['GET'])
def get_node_memory():
    host = request.args.get('host')
    if not host:
        abort(400, 'missing host')

    def get_mem_or_zero(node):
        try:
            return NodeCache.get_info(current_app, node['host'], node['port'])
        except:
            return {'memory': 0, 'maxmemory': 0}

    try:
        port = Agent.get_port(host)
        res = remote.agent_total_mem(host, port)
        total_mem = res['total_mem']
    except:
        logger.exception("can't get agent total memory")
        total_mem = 0

    try:
        nodes = Node.get_nodes_by_host(host)
        memorys = map(get_mem_or_zero, nodes)
        mem_used_sum = sum(map(lambda m: m['memory'], memorys))
        maxmemory_sum = sum(map(lambda m: m['maxmemory'], memorys))
    except Exception as e:
        logger.exception('get memory failed')
        abort(404, e.message)

    return jsonify(
        status=0,
        instances_num=len(filter(lambda m: m['maxmemory'], memorys)),
        mem_used_sum=mem_used_sum,
        max_mem_sum=maxmemory_sum,
        total_mem=total_mem,
        )


@api.route('/archive/<string:archive>', methods=['GET'])
def download_archive(archive):
    return send_from_directory(current_app.config['ARCHIVE_DIRECTORY'],
                               archive, as_attachment=True)
