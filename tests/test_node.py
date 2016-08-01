import logging
import json
import sqlite3
from .base import Base

logger = logging.getLogger(__name__)


class TestNodeAPI(Base):
    def make_data(self):
        self.conn = sqlite3.connect('/tmp/coruvs-web.db')
        self.conn.execute("INSERT INTO node (host, port) VALUES ('127.0.0.1',8001)")
        self.conn.execute("INSERT INTO node (host, port) VALUES ('127.0.0.1',8002)")
        self.conn.commit()
        self.conn.close()

    def test_post_node(self):
        # test create a new node
        rv = self.client.post('/api/node', data=json.dumps({'host': '127.0.0.1', 'port': 8003}),
                           headers={'content-type': 'application/json'})
        self.assertEqual(201, rv.status_code)
        rv = self.client.get('/api/node/1')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(8003, json.loads(rv.data).get('port'))

        # test create node with duplicate address
        rv = self.client.post('/api/node', data=json.dumps({'host': '127.0.0.1', 'port': 8003}),
                           headers={'content-type': 'application/json'})
        self.assertEqual(400, rv.status_code)

        # test create node with empty address
        rv = self.client.post('/api/node', data=json.dumps([]),
                           headers={'content-type': 'application/json'})
        self.assertEqual(400, rv.status_code)

    def test_get_node(self):
        self.make_data()
        # test query an exists node
        rv = self.client.get('/api/node/1')
        self.assertEqual(200, rv.status_code)

        # test query an not exists node
        rv = self.client.get('/api/node/100')
        self.assertEqual(404, rv.status_code)

        # test query with a legal node id
        rv = self.client.get('/api/node/fsdfs')
        self.assertEqual(404, rv.status_code)

    def test_put_node(self):
        self.make_data()
        # test update successfully
        rv = self.client.put('/api/node/1', data=json.dumps({'host': '127.0.0.1', 'port': 8003}),
                          headers={'content-type': 'application/json'})
        self.assertEqual(200, rv.status_code)
        rv = self.client.get('/api/node/1')
        self.assertEqual(8003, json.loads(rv.data).get('port'))

        # update a not exist node
        rv = self.client.put('/api/node/100', data=json.dumps({'host': '127.0.0.1', 'port': 8001}),
                          headers={'content-type': 'application/json'})
        self.assertEqual(404, rv.status_code)

        # update to a exist node
        rv = self.client.put('/api/node/1', data=json.dumps({'host': '127.0.0.1', 'port': 8002}),
                          headers={'content-type': 'application/json'})
        self.assertEqual(400, rv.status_code)

    def test_delete_node(self):
        self.make_data()
        # test delete node successfully
        rv = self.client.delete('/api/node/1')
        self.assertEqual(204, rv.status_code)
        rv = self.client.get('/api/node/1')
        self.assertEqual(404, rv.status_code)

        # delete a not exist node
        rv = self.client.delete('/api/node/1')
        self.assertEqual(404, rv.status_code)

        # delete a legal node
        rv = self.client.delete('/api/node/sss')
        self.assertEqual(404, rv.status_code)
