# -*- coding: utf-8 -*-
import json
import sqlite3
import logging
from .base import Base

logger = logging.getLogger(__name__)


class TestClusterAPI(Base):
    def make_data(self):
        self.conn = sqlite3.connect('/tmp/coruvs-web.db')
        self.conn.execute("INSERT INTO cluster (name, description) VALUES ('eos-cluster','cluster for eos')")
        self.conn.execute("INSERT INTO cluster (name, description) VALUES ('ers-cluster','cluster for ers')")
        self.conn.commit()
        self.conn.close()

    def test_get_cluster(self):
        self.make_data()
        rv = self.client.get('/api/cluster/1')
        self.assertEqual(200, rv.status_code)

        rv = self.client.get('/api/cluster/100')
        self.assertEqual(404, rv.status_code)

        rv = self.client.get('/api/cluster/sds')
        self.assertEqual(404, rv.status_code)

    def test_post_cluster(self):
        rv = self.client.post('/api/cluster', data=json.dumps({'name': 'ems-cluster', 'description': 'cluster for ems'}),
                              headers={'content-type': 'application/json'})
        self.assertEqual(201, rv.status_code)

    def test_put_cluster(self):
        self.make_data()
        rv = self.client.put('/api/cluster/1', data=json.dumps({'name': 'ems-cluster', 'description': 'cluster for ems'}),
                             headers={'content-type': 'application/json'})
        self.assertEqual(200, rv.status_code)
        rv = self.client.get('/api/cluster/1')
        self.assertEqual('ems-cluster', json.loads(rv.data).get('name'))

    def test_delete_cluster(self):
        self.make_data()
        rv = self.client.delete('/api/cluster/1')
        self.assertEqual(204, rv.status_code)
        rv = self.client.get('api/cluster/1')
        self.assertEqual(404, rv.status_code)
