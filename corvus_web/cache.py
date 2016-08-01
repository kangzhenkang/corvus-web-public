# -*- coding: utf-8 -*-

import gevent.pool
import logging
import pickle
import redis
import time

from ruskit.cluster import ClusterNode

from .app import create_app
from .models import Node
from .utils import sort_groupby
from .consts import REDIS_CLUSTER_SLOTS_NUM


logger = logging.getLogger(__name__)

CACHE_KEY_PATTERN = 'corvus-web:node-info:{host}:{port}'
CLUSTER_KEY_PATTERN = 'corvus-web:cluster-info:{cluster_id}'


class NodeCache(object):
    def __init__(self, pool_size=150):
        self.app = create_app()
        self.pool_size = pool_size

        dsn = self.app.config['CACHE_REDIS_DSN']
        self.period = self.app.config.get('CACHE_UPDATE_INTERVAL', 10)
        self.cache_client = redis.StrictRedis.from_url(dsn, socket_timeout=0.1)

    @staticmethod
    def key(host, port):
        return CACHE_KEY_PATTERN.format(host=host, port=port)

    @staticmethod
    def cluster_key(cluster_id):
        return CLUSTER_KEY_PATTERN.format(cluster_id=cluster_id)

    @staticmethod
    def get_info(app, host, port):
        r = redis.StrictRedis(host, port, socket_timeout=0.1)
        cmd = '{} get maxmemory'.format(app.config['REDIS_CONFIG_CMD'])
        p = r.pipeline()
        p.info()
        p.execute_command(cmd)
        result = p.execute()
        info = result[0]

        if 'db0' in info:
            expires = info['db0']['expires']
            keys = info['db0']['keys']
        else:
            expires = 0
            keys = 0
        return {
            'memory': info['used_memory'],
            'maxmemory': int(result[1][1]),
            'connected_clients': info['connected_clients'],
            'total_commands_processed': info['total_commands_processed'],
            'total_keys': keys,
            'expires_keys': expires,
            'keyspace_misses': info['keyspace_misses'],
            'keyspace_hits': info['keyspace_hits'],
        }

    def store(self, nodes):
        for n in nodes:
            try:
                data = self.get_info(self.app, n['host'], n['port'])
                self.cache_client.setex(self.key(n['host'], n['port']),
                                        self.period * 2,
                                        pickle.dumps(data))
            except Exception as e:
                logger.warning(e)

    def update_all(self, pool):
        all_nodes = sort_groupby(Node.get_used_nodes(),
            lambda n: n['cluster_id'])
        cluster_ids = [n[0] for n in all_nodes]
        nodes = [n[1] for n in all_nodes]
        pool.imap(self.update_cluster_info, cluster_ids, nodes)

    def update_cluster_info(self, cluster_id, nodes):
        try:
            cluster_info = self.gen_cluster_info(cluster_id, nodes)
            self.cache_client.setex(self.cluster_key(cluster_id),
                                    self.period * 2,
                                    pickle.dumps(cluster_info))
        except Exception as e:
            logger.exception(e)

    def gen_cluster_info(self, cluster_id, nodes):
        nodes_info = None
        for n in nodes:
            node = ClusterNode(n['host'], n['port'], retry=-1)
            try:
                nodes_info = node.nodes()
                break
            except:
                pass
        if nodes_info is None:
            return {
                'cluster_id': cluster_id,
                'fail_nodes': list(n['addr'] for n in nodes),
                'migrating': [],
                'missing_slots': 0,
            }

        slots = set()
        fail_nodes = []
        migrating_nodes = []
        for n in nodes_info:
            if 'disconnected' in n['link_status']:
                fail_nodes.append(n['addr'])
            else:
                slots.update(n['slots'])
            if len(n['migrating']) > 0:
                migrating_nodes.append(n['addr'])

        if fail_nodes:
            pass  ## todo: add task

        if len(slots) < REDIS_CLUSTER_SLOTS_NUM:
            pass  ## todo: add task

        return {
            'cluster_id': cluster_id,
            'fail_nodes': fail_nodes,
            'migrating': migrating_nodes,
            'missing_slots': REDIS_CLUSTER_SLOTS_NUM - len(slots),
        }

    def get_cluster_info(self, cluster_id):
        data = self.cache_client.get(self.cluster_key(cluster_id))
        cluster_info = {}
        try:
            cluster_info = pickle.loads(data)
        except Exception as e:
            logger.exception(e)

        cluster_info.update(self.get_cluster_memory(cluster_id) or {})
        return cluster_info

    def run(self):
        pool = gevent.pool.Pool(self.pool_size)

        while True:
            start = time.time()
            self.update_all(pool)
            nodes = list(Node.all())
            chunks = [nodes[i:i + 1] for i in range(len(nodes))]
            pool.map(self.store, chunks)
            logger.info('Cache updated in %f seconds', time.time() - start)
            gevent.sleep(self.period)

    def get_cluster_memory(self, cluster_id):
        ZERO = {
            'maxmemory': 0,
            'memory': 0,
            'connected_clients': 0,
            'total_commands_processed': 0,
            'expires_keys': 0,
            'total_keys': 0,
            'keyspace_misses': 0,
            'keyspace_hits': 0,
        }

        nodes = Node.get_cluster_nodes(cluster_id)
        for n in nodes:
            data = self.cache_client.get(self.key(n['host'], n['port']))
            n.update(ZERO)
            try:
                n.update(pickle.loads(data))
            except Exception:
                pass

        if not nodes:
            return

        result = {k: sum(n[k] for n in nodes) for k in ZERO.keys()}

        if result['maxmemory'] == 0:
            return

        def cmp(n):
            if n['maxmemory'] == 0:
                return 0
            return float(n['memory']) / n['maxmemory']

        hottest_node = max(nodes, key=cmp)
        result.update({
            'hottest_node_mem_used': hottest_node['memory'],
            'hottest_node_max_mem': hottest_node['maxmemory'],
        })
        return result


node_cache = NodeCache()
