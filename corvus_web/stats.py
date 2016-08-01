# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging
import pystatsd
import redis
import time

from .models import Node, Cluster

logger = logging.getLogger(__name__)


# corvus-web.napos_order.node.127-0-0-1.connected_clients
class Stats(object):
    METRICS = (
        'connected_clients',
        'used_memory',
        'used_memory_rss',
        'total_commands_processed',
        'instantaneous_ops_per_sec',
        'total_net_input_bytes',
        'total_net_output_bytes',
        'expired_keys',
        'evicted_keys',
        'keyspace_hits',
        'keyspace_misses',
        'used_cpu_sys',
        'used_cpu_user',
    )

    def __init__(self, host, port, interval=10):
        self.statsd = pystatsd.Client(host, port)
        self.interval = interval
        self.chunk_size = 128

    def val(self, value):
        return '{}|g'.format(value)

    def gen_metrics(self, prefix, info):
        return {'.'.join([prefix, m]): self.val(info[m]) for m in self.METRICS}

    def gen_node_stats(self, cluster):
        res = {}
        nodes = Node.get_cluster_nodes(cluster['id'])
        for node in nodes:
            host = node['host'].replace('.', '-')
            prefix = "corvus-web.{}.node.{}-{}".format(
                cluster['name'], host, node['port'])
            r = redis.StrictRedis(node['host'], node['port'])
            res.update(self.gen_metrics(prefix, r.info()))
        return res

    def gen_stats(self):
        data = {}
        for cluster in Cluster.all():
            logger.info("processing cluster %s", cluster['name'])
            try:
                data.update(self.gen_node_stats(cluster))
            except Exception as e:
                logger.exception(e)
        return data

    def start(self):
        while True:
            start = time.time()
            stats = self.gen_stats().items()
            chunks = (stats[i:i + self.chunk_size]
                      for i in range(0, len(stats), self.chunk_size))
            for chunk in chunks:
                self.statsd.send(dict(chunk))
            elapsed = time.time() - start

            interval = self.interval - elapsed
            if interval < 0:
                interval = 0
            time.sleep(interval)
