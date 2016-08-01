# -*- coding: utf-8 -*-

from __future__ import absolute_import

import json
import logging
import gevent
import gevent.pool
import gevent.queue
import traceback

from .worker import tasks
from ..models import Task

logger = logging.getLogger(__name__)


class TaskManager(object):
    def __init__(self, app, pool_size=30):
        self.task_queue = gevent.queue.Queue()
        self.pool_size = pool_size
        self.app = app

    def run(self):
        logger.info("starting task daemon...")

        pool = gevent.pool.Pool(self.pool_size)
        for i in range(self.pool_size):
            pool.apply_async(self.consumer)

        p = gevent.spawn(self.producer)
        p.join()

    def producer(self):
        while True:
            gevent.sleep(1)

            task = Task.get_unprocessed()
            if task is None:
                continue
            Task.set_status(task['id'], Task.EXECUTING)

            if task:
                self.task_queue.put(task)

    def consumer(self):
        while True:
            task = self.task_queue.get()

            func = tasks.get(task['operation'])
            if not func:
                op = task['operation']
                try:
                    op = op.encode('utf-8')
                except:
                    pass

                Task.set_status(
                    task['id'], Task.FAILED,
                    reason='Operation {!r} undefined'.format(op)
                )
                continue
            try:
                param = json.loads(task['param'])
                func(self.app, task['id'], **param)
            except Exception as e:
                logger.exception(e)
                Task.set_status(task['id'], Task.FAILED,
                                reason=traceback.format_exc())
