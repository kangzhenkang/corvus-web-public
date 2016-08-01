# -*- coding: utf-8 -*-
import json
import sqlite3
import logging
from .base import Base

logger = logging.getLogger(__name__)


class TestProxyAPI(Base):
    def make_data(self):
        self.conn = sqlite3.connect('/tmp/coruvs-web.db')
        self.conn.execute("INSERT INTO cluster (name, description) VALUES ('eos-cluster','cluster for eos')")
        self.conn.execute("INSERT INTO proxy (host, port, cluster_id, url) VALUES "
                          "('127.0.0.1', 7001, 1, 'https://github.com/eleme/corvus-web/archive/master.zip')")
        self.conn.execute("INSERT INTO agent (host, port) VALUES ('127.0.0.1', 6001)")
        self.conn.commit()
        self.conn.close()

    def test_get_proxy(self):
        self.make_data()
        rv = self.client.get('/api/proxy/1')
        self.assertEqual(200, rv.status_code)

    def test_post_proxy(self):
        self.make_data()
        rv = self.client.post('/api/proxy', data=json.dumps(
            {'host': '127.0.0.1', 'port': 7003,
             'url': 'https://github.com/eleme/corvus-web/archive/master.zip'}),
                              headers={'content-type': 'application/json'})
        self.assertEqual(201, rv.status_code)
        rv = self.client.get('/api/proxy/1')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(7003, json.loads(rv.data).get('port'))

    def test_put_proxy(self):
        self.make_data()
        rv = self.client.put('/api/proxy/1', data=json.dumps({'host': '127.0.0.1', 'port': 7003}),
                          headers={'content-type': 'application/json'})
        self.assertEqual(200, rv.status_code)
        rv = self.client.get('/api/proxy/1')
        self.assertEqual(7003, json.loads(rv.data).get('port'))

    def test_delete_proxy(self):
        self.make_data()
        # test delete node successfully
        rv = self.client.delete('/api/proxy/1')
        self.assertEqual(204, rv.status_code)
        rv = self.client.get('/api/proxy/1')
        self.assertEqual(404, rv.status_code)
