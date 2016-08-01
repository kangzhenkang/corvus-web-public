# -*- coding: utf-8 -*-

from __future__ import absolute_import

import re
import redis
import socket
from itertools import groupby


def get_proxy_info(host, port):
    try:
        proxy = redis.StrictRedis(host, port, socket_timeout=1)
        return proxy.info()
    except Exception:
        pass


def ip(host):
    try:
        return socket.gethostbyname(host)
    except socket.error:
        return host


MEMORY_SIZE_PATTERN = re.compile('^\d+[kmg]b?$')


def validate_memory(mem):
    return bool(MEMORY_SIZE_PATTERN.match(mem.lower()))


def sort_groupby(iterables, key, reverse=False):
    return map(
            lambda (x, v): (x, list(v)),
            groupby(sorted(iterables, reverse=reverse, key=key), key)
            )


def split_addr(addr):
    return addr.split(':')
