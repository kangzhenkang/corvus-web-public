# -*- coding: utf-8 -*-

import requests

# connect timeout, read timeout
REQUEST_TIMEOUT = 3, 3


def create_proxy(host, port, config):
    url = 'http://{}:{}/agent/proxy/create'.format(host, port)
    res = requests.post(url, json=config, timeout=REQUEST_TIMEOUT)
    return res.json()


def delete_proxy(host, port, config):
    url = 'http://{}:{}/agent/proxy/delete'.format(host, port)
    res = requests.post(url, json=config, timeout=REQUEST_TIMEOUT)
    return res.json()


def update_proxy(host, port, config):
    url = 'http://{}:{}/agent/proxy/update'.format(host, port)
    res = requests.post(url, json=config, timeout=REQUEST_TIMEOUT)
    return res.json()


def ping(host, port):
    url = 'http://{}:{}/agent/ping'.format(host, port)
    res = requests.get(url, timeout=REQUEST_TIMEOUT)
    return res.json()


def get_task(host, port, remote_task_id):
    url = 'http://{}:{}/agent/task/{}'.format(host, port, remote_task_id)
    res = requests.get(url, timeout=REQUEST_TIMEOUT)
    return res.json()


def proxy_info(host, port, proxy_port):
    url = 'http://{}:{}/agent/proxy/info/{}'.format(host, port, proxy_port)
    res = requests.get(url, timeout=REQUEST_TIMEOUT)
    return res.json()


def agent_update(host, port, version):
    url = 'http://{}:{}/agent/update'.format(host, port)
    data = {'version': version}
    res = requests.post(url, json=data, timeout=REQUEST_TIMEOUT)
    return res.json()


def deploy_redis(host, port, data):
    url = 'http://{}:{}/agent/redis/deploy'.format(host, port)
    res = requests.post(url, json=data)
    return res.json()


def agent_total_mem(host, port):
    url = 'http://{}:{}/agent/total_mem'.format(host, port)
    res = requests.get(url)
    return res.json()
