# -*- coding: utf-8 -*-

from __future__ import absolute_import

import datetime
import functools
import logging
import sqlalchemy as sa
import math

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

PAGE_SIZE = 10

db = SQLAlchemy()
logger = logging.getLogger(__name__)


def init_db(app):
    db.init_app(app)
    db.app = app
    db.create_all()
    return db


def safe_session(func):
    @functools.wraps(func)
    def deco(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(e)
            raise
        finally:
            db.session.close()
    return deco


class Base(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow)


def default_register_app(context):
    name = context.current_parameters['name']
    return 'corvus.{}'.format(name)


def default_register_cluster(context):
    return context.current_parameters['name']


class Cluster(Base):
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), default='')
    register_app = db.Column(db.String(50), nullable=False,
        default=default_register_app)
    register_cluster = db.Column(db.String(50), nullable=False,
        default=default_register_cluster)
    deleted = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'deleted': self.deleted,
            'description': self.description,
            'register_app': self.register_app,
            'register_cluster': self.register_cluster,
        }

    @classmethod
    @safe_session
    def all(cls, limit=100):
        current_id = 0
        while True:
            clusters = db.session.query(cls).\
                filter(cls.deleted != True).\
                filter(cls.id > current_id).\
                order_by(cls.id).\
                limit(limit).\
                all()  # noqa
            if not clusters:
                break
            current_id = clusters[-1].id

            for cluster in clusters:
                yield cluster.to_dict()

    @classmethod
    @safe_session
    def update(cls, cluster_id, **updates):
        db.session.query(cls).filter(cls.id == cluster_id).update(updates)
        db.session.commit()

    @classmethod
    @safe_session
    def get(cls, cluster_id):
        c = db.session.query(cls).get(cluster_id)
        if c:
            return c.to_dict()

    @classmethod
    @safe_session
    def get_by_name(cls, name):
        c = db.session.query(cls).filter(cls.name == name,
            cls.deleted != True).first()
        if c:
            return c.to_dict()

    @classmethod
    @safe_session
    def add(cls, **kwargs):
        c = cls(**kwargs)
        db.session.add(c)
        db.session.commit()
        return c.to_dict()

    @classmethod
    @safe_session
    def get_name_map(cls, ids):
        if not ids:
            return {}

        r = db.session.query(cls.id, cls.name).\
            filter(cls.id.in_(ids))
        return dict(r)


class Node(Base):
    host = db.Column(db.String(100), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    cluster_id = db.Column(db.Integer, index=True, default=-1, nullable=False)

    __table_args__ = (db.Index('node-address', 'host', 'port', unique=True),)

    def to_dict(self):
        return {
            'id': self.id,
            'host': self.host,
            'port': self.port,
            'cluster_id': self.cluster_id
        }

    # for flask_restless
    @classmethod
    def query(cls):
        return db.session.query(cls).\
            order_by(cls.cluster_id, cls.host, cls.port)

    @classmethod
    @safe_session
    def update(cls, node_id, **updates):
        db.session.query(cls).filter(cls.id == node_id).update(updates)
        db.session.commit()

    @classmethod
    def upsert(cls, host, port, **updates):
        node = cls.get_by_address(host, port)
        if not node:
            cls.add(host=host, port=port, **updates)
        else:
            cls.update(node['id'], **updates)

    @classmethod
    @safe_session
    def add(cls, **kwargs):
        node = cls(**kwargs)
        db.session.add(node)
        db.session.commit()

    @classmethod
    @safe_session
    def get(cls, node_id):
        node = db.session.query(cls).get(node_id)
        if node:
            return node.to_dict()

    @classmethod
    @safe_session
    def get_by_address(cls, host, port):
        node = db.session.query(cls).\
            filter(cls.host == host).\
            filter(cls.port == port).\
            first()
        if node:
            return node.to_dict()

    @classmethod
    @safe_session
    def get_count(cls, cluster_id):
        return db.session.query(sa.func.count(cls.id)).\
            filter(cls.cluster_id == cluster_id).\
            scalar()

    @classmethod
    @safe_session
    def get_cluster_node(cls, cluster_id):
        c = db.session.query(cls).\
            filter(cls.cluster_id == cluster_id).\
            first()
        if c:
            return c.to_dict()

    @classmethod
    @safe_session
    def get_cluster_nodes(cls, cluster_id):
        nodes = db.session.query(cls).\
            filter(cls.cluster_id == cluster_id)
        return [node.to_dict() for node in nodes]

    @classmethod
    @safe_session
    def reset_cluster(cls, cluster_id):
        nodes = db.session.query(cls).\
            filter(cls.cluster_id == cluster_id)
        for node in nodes:
            node.cluster_id = -1
        db.session.commit()

    @classmethod
    @safe_session
    def all(cls, limit=100):
        current_id = 0
        while True:
            nodes = db.session.query(cls).\
                filter(cls.id > current_id).\
                order_by(cls.id).\
                limit(limit).\
                all()  # noqa
            if not nodes:
                break
            current_id = nodes[-1].id

            name_map = Cluster.get_name_map([n.cluster_id for n in nodes])
            for node in nodes:
                res = node.to_dict()
                res['cluster_name'] = name_map.get(node.cluster_id)
                yield res

    @classmethod
    @safe_session
    def get_nodes_by_host(cls, host):
        return map(cls.to_dict,
            db.session.query(cls).filter(cls.host == host).all())

    @classmethod
    @safe_session
    def get_used_nodes(cls):
        return map(cls.to_dict,
            db.session.query(cls).filter(cls.cluster_id != -1).all())


class Proxy(Base):
    host = db.Column(db.String(100), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    version = db.Column(db.String(50), nullable=False, default='unknown')
    registered = db.Column(db.Boolean, nullable=False, default=False)
    cluster_id = db.Column(db.Integer, default=-1, index=True)

    __table_args__ = (db.Index('proxy-address', 'host', 'port', unique=True),)

    def to_dict(self):
        return {
            'id': self.id,
            'host': self.host,
            'port': self.port,
            'version': self.version,
            'cluster_id': self.cluster_id,
            'registered': self.registered,
        }

    @classmethod
    def _get_by_host(cls, host, port):
        p = db.session.query(cls).\
            filter(cls.host == host).\
            filter(cls.port == port).\
            first()
        return p

    @classmethod
    @safe_session
    def add_many(cls, cluster_id, proxies):
        tmp = []
        for p in proxies:
            proxy = cls._get_by_host(p['host'], p['port'])
            if not proxy:
                proxy = cls(host=p['host'], port=p['port'])
            proxy.cluster_id = cluster_id
            if 'version' in p:
                proxy.version = p['version']
            db.session.add(proxy)
            tmp.append(proxy)
        db.session.commit()
        return [p.id for p in tmp]

    @classmethod
    @safe_session
    def get_many(cls, proxies):
        proxies = db.session.query(cls).filter(cls.id.in_(proxies)).all()
        return map(cls.to_dict, proxies)

    @classmethod
    @safe_session
    def all(cls, limit=100):
        current_id = 0
        while True:
            proxies = db.session.query(cls).\
                filter(cls.id > current_id).\
                order_by(cls.id).\
                limit(limit).\
                all()  # noqa
            if not proxies:
                break
            current_id = proxies[-1].id
            name_map = Cluster.get_name_map([n.cluster_id for n in proxies])

            for proxy in proxies:
                res = proxy.to_dict()
                res['cluster_name'] = name_map.get(proxy.cluster_id)
                yield res

    @classmethod
    @safe_session
    def search(cls, offset, version=None, cluster=None, registered=None):
        cluster_id = None
        if cluster:
            c = Cluster.get_by_name(cluster)
            if not c:
                return {'pages': 0, 'count': 0, 'items': []}
            cluster_id = c['id']

        def _q(arg):
            q = db.session.query(arg).\
                filter(cls.cluster_id != -1)
            if version:
                q = q.filter(cls.version == version)
            if cluster_id:
                q = q.filter(cls.cluster_id == cluster_id)
            if registered is not None:
                q = q.filter(cls.registered == registered)
            return q

        count = _q(sa.func.count(cls.id)).scalar()
        q = _q(cls).order_by(cls.id)
        items = [i.to_dict() for i in q[offset:offset + PAGE_SIZE]]
        cluster_ids = [i['cluster_id'] for i in items]
        name_map = Cluster.get_name_map(cluster_ids)
        for i in items:
            i['cluster'] = name_map[i['cluster_id']]
        return {'pages': int(math.ceil(count / float(PAGE_SIZE))),
                'count': count, 'items': items}

    @classmethod
    @safe_session
    def delete_many(cls, proxies):
        if not proxies:
            return
        db.session.query(cls).\
            filter(cls.id.in_(proxies)).\
            delete(synchronize_session=False)
        db.session.commit()

    @classmethod
    @safe_session
    def get_count(cls, cluster_id):
        return db.session.query(sa.func.count(cls.id)).\
            filter(cls.cluster_id == cluster_id).\
            scalar()

    @classmethod
    @safe_session
    def get_cluster_proxy(cls, cluster_id):
        p = db.session.query(cls).\
            filter(cls.cluster_id == cluster_id).\
            first()
        if p:
            return p.to_dict()

    @classmethod
    @safe_session
    def reset_cluster(cls, cluster_id):
        proxies = db.session.query(cls).\
            filter(cls.cluster_id == cluster_id)
        for proxy in proxies:
            proxy.cluster_id = -1
        db.session.commit()

    @classmethod
    @safe_session
    def update(cls, proxy_id, **updates):
        db.session.query(cls).filter(cls.id == proxy_id).update(updates)
        db.session.commit()

    @classmethod
    @safe_session
    def update_many(cls, updates):
        if not updates:
            return
        for proxy_id, args in updates:
            db.session.query(cls).filter(cls.id == proxy_id).update(args)
        db.session.commit()


class Task(Base):
    CREATED = 0
    EXECUTING = 1
    DONE = 2
    FAILED = 3

    operation = db.Column(db.String(50))
    param = db.Column(db.Text)
    status = db.Column(db.Integer)
    reason = db.Column(db.Text, default='')
    sync = db.Column(db.Boolean, default=False)
    cluster_id = db.Column(db.Integer, default=-1)
    remote_id = db.Column(db.Integer, default=-1)

    def to_dict(self):
        return {
            'id': self.id,
            'operation': self.operation,
            'param': self.param,
            'status': self.status,
            'reason': self.reason,
            'sync': self.sync,
            'cluster_id': self.cluster_id,
            'remote_id': self.remote_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at)
        }

    @classmethod
    @safe_session
    def add(cls, operation, param, sync=False, cluster_id=-1, remote_id=-1):
        task = cls(operation=operation, param=param, status=cls.CREATED,
                   sync=sync, cluster_id=cluster_id, remote_id=remote_id)
        db.session.add(task)
        db.session.commit()
        return task.to_dict()

    @classmethod
    @safe_session
    def get(cls, task_id):
        task = db.session.query(cls).get(task_id)
        if task:
            return task.to_dict()

    @classmethod
    @safe_session
    def update(cls, task_id, **updates):
        db.session.query(cls).filter(cls.id == task_id).update(updates)
        db.session.commit()

    @classmethod
    @safe_session
    def get_unprocessed(cls):
        tasks = db.session.query(cls).\
            filter(cls.status == cls.CREATED).\
            filter(cls.remote_id == -1).\
            order_by(cls.created_at).\
            all()
        tasks = [t for t in tasks if not t.locked()]
        if not tasks:
            return

        task = tasks[0]
        if task.sync:
            task.lock()

        return task.to_dict()

    @classmethod
    @safe_session
    def set_status(cls, task_id, status, reason=''):
        task = db.session.query(cls).get(task_id)
        if not task:
            return

        task.status = status
        task.reason = reason
        db.session.add(task)
        db.session.commit()

        if status in (cls.DONE, cls.FAILED) and task.sync:
            task.unlock()

    @safe_session
    def lock(self):
        if self.cluster_id <= -1:
            return

        attr = db.session.query(TaskAttribute).\
            filter(TaskAttribute.cluster_id == self.cluster_id).\
            first()
        if not attr:
            attr = TaskAttribute()

        attr.locked = True
        attr.cluster_id = self.cluster_id

        db.session.add(attr)
        db.session.commit()

    @safe_session
    def unlock(self):
        if self.cluster_id <= -1:
            return

        attr = db.session.query(TaskAttribute).\
            filter(TaskAttribute.cluster_id == self.cluster_id).\
            first()
        if not attr:
            return

        attr.locked = False
        db.session.add(attr)
        db.session.commit()

    @safe_session
    def locked(self):
        if self.cluster_id <= 0:
            return False
        return db.session.query(TaskAttribute.locked).\
            filter(TaskAttribute.cluster_id == self.cluster_id).\
            scalar()

    @classmethod
    @safe_session
    def create_fail(cls, operation, param, reason, remote_id, **kwargs):
        task = cls(
            operation=operation,
            param=param,
            status=cls.FAILED,
            reason=reason,
            remote_id=remote_id,
            **kwargs)
        db.session.add(task)
        db.session.commit()
        return task.to_dict()

    @classmethod
    @safe_session
    def upsert_unfinished(cls, operation, param):
        '''WARNING: potential race condition'''
        tasks = cls.get_unfinished(operation)
        if len(tasks) == 1:
            return tasks[0]
        elif not tasks:
            return Task.add(operation, param)
        else:
            raise Exception('multiple {} found'.format(operation))

    @classmethod
    @safe_session
    def get_unfinished(cls, operation):
        tasks = db.session.query(cls).\
            filter(cls.operation == operation).\
            filter(sa.or_(cls.status == Task.CREATED,
                cls.status == Task.EXECUTING)).all()
        return map(cls.to_dict, tasks)


class TaskAttribute(Base):
    cluster_id = db.Column(db.Integer)
    locked = db.Column(db.Boolean)


class RemoteTask(Base):
    remote_id = db.Column(db.Integer)
    remote_host = db.Column(db.String(100))
    remote_port = db.Column(db.Integer)

    def to_dict(self):
        return {
            'remote_id': self.remote_id,
            'remote_host': self.remote_host,
            'remote_port': self.remote_port
        }

    @classmethod
    @safe_session
    def add(cls, task_name, param, remote_id, **kwargs):
        r = cls(remote_id=remote_id, **kwargs)
        db.session.add(r)
        db.session.commit()
        task = Task.add(task_name, param, remote_id=r.id)
        return task

    @classmethod
    @safe_session
    def get(cls, remote_id):
        task = db.session.query(cls).get(remote_id)
        if task:
            return task.to_dict()


class Agent(Base):
    host = db.Column(db.String(100), index=True, unique=True, nullable=False)
    port = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'host': self.host,
            'port': self.port
        }

    @classmethod
    @safe_session
    def add(cls, host, port):
        db.session.add(cls(host=host, port=port))
        db.session.commit()

    @classmethod
    @safe_session
    def get_port(cls, host):
        return db.session.query(cls.port).\
            filter(cls.host == host).\
            scalar()

    @classmethod
    @safe_session
    def search(cls, offset, host=None):
        def _q(arg):
            q = db.session.query(arg)
            if host:
                q = q.filter(cls.host == host)
            return q

        count = _q(sa.func.count(cls.id)).scalar()
        q = _q(cls).order_by(cls.id)
        items = [i.to_dict() for i in q[offset:offset + PAGE_SIZE]]
        return {'pages': int(math.ceil(count / float(PAGE_SIZE))),
                'count': count, 'items': items}
