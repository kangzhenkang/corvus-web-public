# -*- coding: utf-8 -*-

from __future__ import absolute_import

import json
import random

try:
    import httplib as http
    import urllib as urllib
except ImportError:
    import http.client as http
    import urllib.parse as urllib


class HuskarException(Exception):
    pass


class SashException(Exception):
    pass


class HuskarClient(object):
    def __init__(self, timeout=30):
        self.timeout = timeout
        self.token = ''

    def init_app(self, app):
        self.token = app.config.get('HUSKAR_TOKEN')
        self.team = app.config.get('HUSKAR_TEAM')
        host = app.config.get('HUSKAR_API_HOST')
        port = app.config.get('HUSKAR_API_PORT')

        if not all([self.token, host, port, self.team]):
            raise HuskarException('Missing huskar connection infomation')

        self.client = http.HTTPConnection(host, port, timeout=self.timeout)

    def request(self, method, url, params=None, headers=None):
        params = urllib.urlencode(params) if params else ''
        hs = {
            'Content-type': 'application/x-www-form-urlencoded',
            'Authorization': self.token
        }
        if headers:
            hs.update(headers)

        try:
            self.client.request(method, url, params, hs)
            response = self.client.getresponse()
            data = response.read().decode('utf-8')
        finally:
            self.client.close()

        try:
            data = json.loads(data)
        except ValueError:
            pass

        if response.status != 200 or data['status'] != 'SUCCESS':
            raise HuskarException('{}'.format(data))

        return data

    def get_token(self, username, password):
        args = {
            'username': username,
            'password': password
        }
        data = self.request('POST', '/api/auth/token', args)
        if data['status'] == 'SUCCESS':
            self.token = data['data']['token']
        return self.token

    def create_app(self, app):
        args = {
            'application': app,
            'team': self.team
        }
        return self.request('POST', '/api/application', args)

    def add_service(self, app_name, cluster, ip, port):
        args = {
            'key': "{}_{}".format(ip, port),
            'value': json.dumps({'ip': ip, 'port': {'main': port}}),
            'runtime': json.dumps({'status': 'up'})
        }
        return self.request(
            'POST', '/api/service/{}/{}'.format(app_name, cluster), args)

    def get_app(self, app_name):
        r = self.request('GET', '/api/application')
        return next(iter(filter(
            lambda a: a['name'] == app_name, r['data'])), None)

    def get_service(self, app_name, cluster, key):
        try:
            r = self.request('GET',
                             '/api/service/{}/{}'.format(app_name, cluster),
                             {'key': key})
        except HuskarException as e:
            if 'DataNotExistsError' not in str(e):
                raise
            return
        v = json.loads(r['data']['value'])
        return {'host': v['ip'], 'port': v['port']['main']}

    def delete_service(self, app_name, cluster, host, port):
        try:
            return self.request('DELETE',
                                '/api/service/{}/{}?key={}_{}'.format(
                                    app_name, cluster, host, port))
        except HuskarException as e:
            if 'DataNotExistsError' not in str(e):
                raise


class SashClient(object):
    def __init__(self, timeout=30):
        self.timeout = timeout

    def init_app(self, app):
        host = app.config.get('SASH_HOST')
        port = app.config.get('SASH_PORT')
        if not all([host, port]):
            raise SashException('Missing sash connection infomation')
        self.client = http.HTTPConnection(host, port, timeout=self.timeout)

    def request(self, method, url, params=None, headers=None):
        try:
            self.client.request(method, url, params)
            response = self.client.getresponse()
            data = response.read().decode('utf-8')
        finally:
            self.client.close()

        try:
            data = json.loads(data)
        except ValueError:
            pass

        if response.status != 200:
            raise SashException('{}'.format(data))

        return data

    def is_application_registered(self, application):
        frontends = self.request('GET', '/api/configs/frontends/')
        return application in [f['name'] for f in frontends]

    def register_frontend(self, application):
        try:
            frontends = self.request('GET', '/api/configs/frontends/')
            existing_frontends = set([f['port'] for f in frontends])
            available_ports = set(range(8000, 9000)) - existing_frontends
            if not available_ports:
                raise SashException("No available ports")
            port = random.choice(list(available_ports))
            self.request('POST',
                         '/api/configs/frontends/{}/{}'.format(
                             application, port))

        except SashException:
            pass


huskar_client = HuskarClient()
sash_client = SashClient()


def register_proxy(application, cluster, host, port):
    apps = huskar_client.get_app(application)
    if not apps:
        huskar_client.create_app(application)

    service = huskar_client.get_service(
        application, cluster, '{}_{}'.format(host, port))
    if not service:
        huskar_client.add_service(application, cluster, host, port)

    if not sash_client.is_application_registered(application):
        sash_client.register_frontend(application)


def deregister_proxy(application, cluster, host, port):
    huskar_client.delete_service(application, cluster, host, port)


def proxy_registered(application, cluster, host, port):
    service = huskar_client.get_service(
        application, cluster, '{}_{}'.format(host, port))
    return bool(service)
