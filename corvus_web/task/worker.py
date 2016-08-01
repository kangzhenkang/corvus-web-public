# -*- coding: utf-8 -*-

from __future__ import absolute_import

import os
import functools
import hashlib
import logging
import os.path
import socket
import subprocess
import time
import traceback
import operator

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import requests
import json

from ruskit.cluster import ClusterNode, Cluster as RedisCluster
from ruskit.cmds.create import Manager

import corvus_web.agent.remote as remote
from ..exc import TaskException, AgentError, InvalidOperation
from ..models import Node, Task, RemoteTask, Cluster, Proxy
from ..agent import download_corvus, render_corvus_config, run, \
    render_corvus_ini, parse_corvus_conf, parse_proxy_ini, get_proxy_ini, \
    program_running, render_redis_ini, render_redis_conf, \
    render_redis_rsyslog, download_redis_package, check_ports, all_running, \
    makedirs_with_owner, redis_sys_init, redis_installed

logger = logging.getLogger(__name__)

tasks = {}


REDIS_PATH = '/opt/redis/redis_bin'
CORVUS_CONF = '/etc/corvus/corvus-{}.conf'
SUPERVISOR_DIR = '/etc/supervisord.d'


def handle_exc(func):
    @functools.wraps(func)
    def wrapper(app, task_id, **kwargs):
        try:
            if hasattr(func, '__pass_app__'):
                res = func(app, task_id, **kwargs)
            else:
                res = func(task_id, **kwargs)
            Task.set_status(task_id, Task.DONE)
            return res
        except Exception as e:
            logger.exception(e)
            Task.set_status(task_id, Task.FAILED,
                            reason=traceback.format_exc())
    return wrapper


def register_task(func):
    tasks[func.__name__] = handle_exc(func)
    return func


def pass_app(func):
    func.__pass_app__ = True
    return func


# TODO task执行失败之后需要还原数据
@register_task
def create_cluster(task_id, name, nodes, slaves=0, description=''):
    logger.info('start to create cluster %s' % name)
    nodes_addr = ['{}:{}'.format(n['host'], n['port']) for n in nodes]
    manager = Manager(slaves, nodes_addr)
    if not manager.check():
        raise TaskException('Cluster can not be created.')

    manager.init_slots()
    manager.set_slots()
    manager.assign_config_epoch()
    manager.join_cluster()

    manager.cluster.wait()
    manager.set_slave()
    manager.cluster.wait()

    c = Cluster.add(name=name, description=description)
    for node in manager.cluster.nodes:
        Node.upsert(node.host, node.port, cluster_id=c['id'])
    logger.info("cluster %s created successfully" % name)


@register_task
def destroy_cluster(task_id, cluster_id, host, port):
    logger.info('start to destroy cluster %d', cluster_id)
    cluster = RedisCluster.from_node(ClusterNode(host, port))
    for n in cluster.masters:
        n.flushall()

    for n in cluster.nodes:
        n.reset(hard=True)

    Cluster.update(cluster_id, deleted=True)
    Node.reset_cluster(cluster_id)
    Proxy.reset_cluster(cluster_id)
    logger.info('cluster %d destroyed', cluster_id)


@register_task
def cluster_migrate(task_id, plan, **ignore):
    logger.info('start to migratting slots')
    if not plan:
        return

    cluster = None
    for p in plan:
        src = ClusterNode(p['src']['host'], p['src']['port'])
        src.ping()
        if not cluster:
            cluster = RedisCluster.from_node(src)

        dst = ClusterNode(p['dst']['host'], p['dst']['port'])
        dst.ping()
        if p['count'] <= 0:
            continue

        cluster.migrate(src, dst, p['count'], verbose=False)
        cluster.wait()

    logger.info('migratting success')


@register_task
def cluster_reshard(task_id, host, port, **ignore):
    logger.info('start resharding cluster')
    cluster = RedisCluster.from_node(ClusterNode(host, port))
    cluster.reshard()
    cluster.wait()
    logger.info('resharding cluster done')


@register_task
def node_quit(task_id, nodes, **ignore):
    logger.info('start to quit cluster nodes')

    # forbid deleting all nodes
    cluster_id = Task.get(task_id)['cluster_id']
    if len(Node.get_cluster_nodes(cluster_id)) == len(nodes):
        raise TaskException('deleting all nodes is not allowed')

    for node in nodes:
        redis_node = ClusterNode(node['host'], node['port'])
        cluster = RedisCluster.from_node(redis_node)
        if len(cluster.nodes) > 1:
            cluster.delete_node(redis_node)
            cluster.wait()
        Node.update(node['nodeId'], cluster_id=-1)

    logger.info('nodes quit successfully')


@register_task
def node_add(task_id, current, nodes, clusterId, **ignore):
    logger.info('start adding nodes')
    redis_node = ClusterNode(current['host'], current['port'])
    cluster = RedisCluster.from_node(redis_node)
    for n in cluster.nodes:
        n.ping()
    for n in nodes:
        cluster.add_node(n)
        cluster.wait()
        host, port = n['addr'].split(':')
        node = ClusterNode(host, int(port))
        Node.upsert(node.host, node.port, cluster_id=clusterId)

    logger.info('nodes added')


@register_task
def delete_cluster(task_id, name=None, nodes=None, **kwargs):
    logger.info('start to delete cluster %s' % name)
    cluster_node = nodes[0]
    cluster_node_uri = ':'.join([cluster_node['host'],
                                 str(cluster_node['port'])])
    redis_node = ClusterNode.from_uri(cluster_node_uri)
    cluster = RedisCluster.from_node(redis_node)
    for node in cluster.masters:
        node.flushall()
    for node in cluster.nodes:
        node.reset(hard=True)
    logger.info('cluster %s delete successfully' % name)


def _update_proxy(bind, version, conf):
    etc = CORVUS_CONF.format(bind)
    render_corvus_config(conf, etc)
    sha1 = hashlib.sha1(open(etc).read()).hexdigest()[:7]
    conf['sha'] = sha1

    program = 'corvus-{}-{}-{}'.format(bind, version, sha1)
    new_ini = os.path.join('/etc/supervisord.d', '{}.ini'.format(program))
    render_corvus_ini(conf, new_ini)

    run('supervisorctl update {}'.format(program))

    for _ in range(30):
        if program_running(program):
            break
        time.sleep(1)
    else:
        raise TaskException('Proxy {} updated but not running'.format(bind))

    return new_ini


@register_task
@pass_app
def create_proxy(app, task_id, **config):
    logger.info('start creating proxy {}'.format(config['bind']))
    if 'node' not in config or 'cluster' not in config or \
            'version' not in config:
        raise TaskException('Missing config.')

    ip = socket.gethostbyname(socket.gethostname())

    logger.info('check if corvus running')
    try:
        run('pgrep -f corvus-{}.conf'.format(config['bind']))
        raise TaskException('Corvus already running on {}:{}'.format(
            ip, config['bind']))
    except subprocess.CalledProcessError:
        pass

    try:
        logger.info('check port usable')
        s = socket.create_connection((ip, config['bind']), 3)
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        raise TaskException('Port {} in use.'.format(config['bind']))
    except socket.error:
        pass

    corvus = '/opt/corvus/corvus-{}/src/corvus'.format(config['version'])
    if not os.path.exists(corvus):
        logger.info('downloading corvus')
        download_corvus(config['version'], app.config['ARCHIVE_ADDRESS'])

    _update_proxy(config['bind'], config['version'], config)

    web_address = config['web_address']
    proxy_ids = add_proxy_to_web(web_address, config['cluster_id'],
        [{'host': config['host'], 'port': config['bind']}])
    config['port'] = config['bind']
    config['id'] = proxy_ids[0]
    #register_proxy(web_address, config)  # Don't register to service registry, it shall be done manually.

    logger.info('proxy {} created'.format(config['bind']))


def add_proxy_to_web(web_address, cluster_id, proxies):
    data = {
        'clusterId': cluster_id,
        'proxies': proxies,
    }
    res = requests.post(
        'http://{}/api/proxy/add'.format(web_address), json=data)
    json = res.json()
    if json['status'] != 0:
        raise TaskException('adding proxy fail {}'.format(json))
    return json['proxy_ids']


def register_proxy(web_address, data):
    res = requests.post(
        'http://{}/api/proxy/register'.format(web_address), json=data)
    json = res.json()
    if json['status'] != 0:
        raise TaskException('register proxy fail {}'.format(json))


@register_task
@pass_app
def update_proxy(app, task_id, **config):
    bind = config['bind']

    etc = CORVUS_CONF.format(bind)
    if not os.path.exists(etc):
        raise TaskException('config file `{}` not exists'.format(etc))

    ini_files = get_proxy_ini(bind)
    if not ini_files:
        raise TaskException('proxy {} not running'.format(bind))

    version = config.get('version')
    if version:
        corvus = '/opt/corvus/corvus-{}/src/corvus'.format(version)
        if not os.path.exists(corvus):
            download_corvus(version, app.config['ARCHIVE_ADDRESS'])
    else:
        version, _ = parse_proxy_ini(ini_files[0])
        config['version'] = version

    conf = parse_corvus_conf(open(etc).read())
    conf.update(config)

    new_ini = _update_proxy(bind, version, conf)

    for ini in set(ini_files).difference([new_ini]):
        _, program = parse_proxy_ini(ini)
        os.remove(ini)
        run('supervisorctl stop {}'.format(program))
        run('supervisorctl update {}'.format(program))

    logger.info('update proxy %d done', bind)


@register_task
def delete_proxy(task_id, **config):
    logger.info('starting delete proxy')
    ports = config['ports']
    programs = []
    for p in ports:
        conf_file = CORVUS_CONF.format(p)
        if os.path.exists(conf_file):
            os.remove(conf_file)
        for f in os.listdir(SUPERVISOR_DIR):
            if f.startswith('corvus-{}-'.format(p)) and f.endswith('.ini'):
                programs.append(f[:-4])
                os.remove(os.path.join(SUPERVISOR_DIR, f))
        logger.info('{} deleted'.format(programs[-1]))
    run('supervisorctl reread')
    run('supervisorctl update {}'.format(' '.join(programs)))
    logger.info('waiting proxy to be stopped')
    retry = 5 * len(programs)
    for _ in range(retry):
        if all(map(operator.not_, map(program_running, programs))):
            break;
        os.sleep(2)
    else:
        raise TaskException('proxies are still running')
    delete_proxy_in_dashboard(config)
    logger.info('successfully delete proxy')


def delete_proxy_in_dashboard(config):
    res = requests.post(
        'http://{}/api/proxy/delete'.format(config['web_address']),
        json=config)
    json = res.json()
    if json['status'] != 0:
        raise TaskException('proxy delete failed {}'.format(json))


def create_daemon(task_id, version):
    pid = os.fork()
    if pid == 0:
        os.setsid()
        sub_pid = os.fork()
        if sub_pid == 0:
            try:
                run('supervisorctl restart corvus-agent:')
                for _ in range(30):
                    if program_running('corvus-agent:corvus-agent-api') and \
                            program_running('corvus-agent:corvus-agent-task'):
                        break
                    time.sleep(1)
                else:
                    raise TaskException('Agent updated but not running')
                Task.set_status(task_id, Task.DONE)
            except Exception:
                Task.set_status(task_id, Task.FAILED,
                                reason=traceback.format_exc())
            exit(0)
        else:
            os._exit(0)
    else:
        os._exit(0)


@register_task
@pass_app
def update_agent(app, task_id, version):
    logger.info('starting update agent to %s', version)
    r = urlparse.urlparse(app.config['INDEX_URL'])
    run('{}/bin/pip install corvus-web=={} '
        '--extra-index-url {} --trusted-host {}'.
        format(app.config['VENV'], version, app.config['INDEX_URL'], r.netloc))
    create_daemon(task_id, version)


@register_task
@pass_app
def deploy_redis(app, task_id, **config):
    '''run in agent'''
    logger.info('starting deploy redis')
    node = config['node']
    ports = node['ports']
    maxmemorys = node['maxmemorys']
    persistences = node['persistences']
    archives = node['archives']
    host = node['host']

    web_address = config['web_address']

    path = app.config.get('REDIS_PATH') or REDIS_PATH
    for archive in set(archives):
        if not redis_installed(path, archive):
            logger.info(
                '{} not installed, starting to download'.format(archive))
            url = 'http://{}/api/redis_package/{}'.format(
                web_address, archive)
            download_redis_package(url, archive, path)
            logger.info('finished installing redis')

    check_ports(ports)
    for port, maxmemory, persistence, archive in zip(
            ports, maxmemorys, persistences, archives):
        redis_server = os.path.join(path, archive, 'bin', 'redis-server')
        render_redis_ini(redis_server, port)
        render_redis_conf(port, maxmemory, persistence)
        working_dir = os.path.join('/data/redis/cluster/', str(port))
        makedirs_with_owner(working_dir, 'redis', 'redis')

    programs = ['redis-cluster-{}'.format(port) for port in ports]
    run('supervisorctl update {}'.format(' '.join(programs)))

    retry = 10 * len(ports)
    for _ in range(retry):
        if all_running(programs):
            break
        time.sleep(1)
    else:
        raise TaskException('deploying finished but not all redis running')

    logger.info('starting to register node {} on {}'.format(
        ports, web_address))
    register_node(web_address, host, ports)
    logger.info('finished register')

    logger.info('finished deploying redis')


def register_node(web_address, host, ports):
    data = {
        'nodes': [{'host': host, 'port': port} for port in ports]
    }
    res = requests.post(
        'http://{}/api/node/register'.format(web_address), json=data)
    json = res.json()
    if json['status'] != 0:
        raise TaskException('node register fail {}'.format(json))


def all_versions_installed(app):
    package_path = app.config['REDIS_PACKAGE_PATH']
    out_path = os.path.join(package_path, 'packages')
    versions = app.config['REDIS_VERSIONS']
    for v in versions:
        archive = 'redis-{}.tar.gz'.format(v)
        dest = os.path.join(out_path, archive)
        if not os.path.exists(dest):
            return False
    return True


@register_task
@pass_app
def gen_all_redis_package(app, task_id, **config):
    # can't completely avoid race condition, but reduce posibility
    tasks = Task.get_unfinished('gen_all_redis_package')
    if len(tasks) > 1:
        raise TaskException('multiple tasks found {}'.format(tasks))

    logger.info('starting generate redis package')

    package_path = app.config['REDIS_PACKAGE_PATH']
    out_path = os.path.join(package_path, 'packages')
    install_path = os.path.join(package_path, 'install')
    for p in (out_path, install_path):
        if not os.path.exists(p):
            os.makedirs(p)

    versions = app.config['REDIS_VERSIONS']
    for v in versions:
        archive = 'redis-{}.tar.gz'.format(v)
        dest = os.path.join(out_path, archive)
        if os.path.exists(dest):
            continue

        logger.info('starting install {}'.format(archive))
        os.chdir(install_path)
        DOWNLOAD_ADDRESS = 'http://download.redis.io/releases/{}'.format(archive)
        run('wget -N {}'.format(DOWNLOAD_ADDRESS))
        run('tar zxf {}'.format(archive))
        dir_name = archive[:-7]  # remove '.tar.gz'
        dir_path = os.path.join(install_path, dir_name)
        os.chdir(dir_path)
        run('make')
        run('make PREFIX={} install'.format(dir_path))
        run('tar czf {} {}'.format(dest, 'bin'))
        logger.info('packing finished')

    logger.info('all redis package installed')


def gen_deploy_tasks(nodes, app):
    for node in nodes:
        host = node['host']
        port = node['agent_port']
        try:
            web_address = app.config['WEB_ADDRESS']
            data = {'node': node, 'web_address': web_address}
            res = remote.deploy_redis(host, port, data)
        except Exception as e:
            logger.exception('remote call failed')
            res = {'status': -1, 'message': e.message}
        if res.get('status') != 0:
            Task.create_fail(
                'deploy_redis',
                json.dumps(node),
                'unexpected error in agent {}:{} {}'.format(
                    host, port, res.get('message') or ''),
                res.get('task_id') or -1)
        else:
            task = RemoteTask.add('deploy_redis', json.dumps(node),
                res.get('task_id'), remote_host=host, remote_port=port)
