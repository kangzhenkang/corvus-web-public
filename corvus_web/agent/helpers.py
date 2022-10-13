# -*- coding: utf-8 -*-

from __future__ import absolute_import

import ConfigParser
import logging
import os
import subprocess
import glob
import tarfile
import urllib
import pwd
import grp

import jinja2
import psutil

from pkg_resources import resource_string

from ..exc import TaskException

SUPERVISOR = '/etc/supervisord.d'
REDIS_CONF = '/etc/redis/redis-cluster-{}.conf'
REDIS_INI = '/etc/supervisord.d/redis-cluster-{}.ini'
REDIS_RSYSLOG_PATH = '/etc/rsyslog.d/30-redis.conf'
REDIS_LOGROTATE_PATH = '/etc/logrotate.d/redis'

logger = logging.getLogger(__name__)


class CalledProcessErrorWrapper(subprocess.CalledProcessError):
    def __init__(self, e):
        super(CalledProcessErrorWrapper, self).__init__(
            e.returncode, e.cmd, e.output)

    def __str__(self):
        err = super(CalledProcessErrorWrapper, self).__str__()
        return '{}: {}'.format(err, self.output)


def run(cmd, shell=False):
    try:
        output = subprocess.check_output(
            cmd.split(), shell=shell, stderr=subprocess.STDOUT)
        logger.info('%s\n%s', cmd, output.strip())
        return output
    except subprocess.CalledProcessError as e:
        raise CalledProcessErrorWrapper(e)


def makedirs_with_owner(path, user, group):
    if not os.path.exists(path):
        os.makedirs(path)
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid
    os.chown(path, uid, gid)


def user_exist(user):
    return user in map(lambda a: a.pw_name, pwd.getpwall())


def download_corvus(version, archive_url):
    corvus_dir = '/opt/corvus'
    if not os.path.exists(corvus_dir):
        os.mkdir(corvus_dir)
    os.chdir(corvus_dir)

    corvus_url = '{}/corvus-{}.tar.bz2'.format(archive_url, version)

    run('wget -N {}'.format(corvus_url))
    run('tar xf corvus-{}.tar.bz2'.format(version))
    os.chdir('corvus-{}'.format(version))
    run('make')


def render_corvus_config(config, path):
    if not os.path.exists('/etc/corvus'):
        os.mkdir('/etc/corvus')

    node = [n.strip() for n in config['node'].split(',') if n.strip()]
    if not node:
        raise TaskException('No nodes')

    conf_tpl = resource_string('corvus_web', 'static/corvus.conf.jinja')
    template = jinja2.Template(conf_tpl)
    args = dict(
        bind=config['bind'],
        node=','.join(node),
        thread=config.get('thread', 4),
        client_timeout=config.get('client_timeout', 600),
        server_timeout=config.get('server_timeout', 0),
        cluster=config['cluster'],
        statsd=config.get('statsd', '')
    )
    bufsize = config.get('bufsize')
    if bufsize:
        args['bufsize'] = bufsize
    conf = template.render(args)

    with open(path, 'w') as f:
        f.write(conf)

    logger.info('render {} done'.format(path))


def render_corvus_ini(config, path):
    ini_tpl = resource_string('corvus_web', 'static/corvus.ini.jinja')
    template = jinja2.Template(ini_tpl)
    ini = template.render(bind=config['bind'], version=config['version'],
                          sha=config['sha'])
    with open(path, 'w') as f:
        f.write(ini)

    logger.info('render {} done'.format(path))


def render_corvus_rsyslog(config):
    rsyslog = resource_string('corvus_web', 'static/corvus_rsyslog.conf')
    logratate = resource_string('corvus_web', 'static/logrotate_corvus')

    with open(config['RSYSLOG_PATH'], 'wb') as f:
        f.write(rsyslog)

    with open(config['LOGROTATE_PATH'], 'wb') as f:
        f.write(logratate)

    run('service rsyslog restart')


def parse_corvus_conf(conf):
    res = {}
    for line in conf.split('\n'):
        line = line.strip()

        if line.startswith('#'):
            continue

        components = line.split()
        length = len(components)
        if length < 1:
            continue
        res[components[0]] = '' if length == 1 else ' '.join(components[1:])
    return res


def parse_proxy_ini(path):
    config = ConfigParser.ConfigParser()
    config.read([path])
    section = config.sections()[0]
    command = config.get(section, 'command')
    corvus = command.split()[0]
    _, version = corvus.split(os.path.sep)[3].split('-')

    _, program = section.split(':')
    return version, program


def write_ini(section, config):
    new_config = ConfigParser.ConfigParser()
    new_config.add_section(section)
    for key, value in config.items(section):
        new_config.set(section, key, value)

    bind = section.split('-')[1]
    path = os.path.join(SUPERVISOR, 'corvus-{}.ini'.format(bind))
    with open(path, 'wb') as f:
        new_config.write(f)


def process_old_ini():
    ini = os.path.join(SUPERVISOR, 'corvus.ini')
    if not os.path.exists(ini):
        return

    config = ConfigParser.ConfigParser()
    config.read([ini])

    for section in config.sections():
        write_ini(section, config)

    with open(ini, 'r+') as f:
        lines = []
        for line in f.readlines():
            line = line.lstrip()
            if not line:
                lines.append('\n')
            elif not line.startswith('#'):
                lines.append('# {}'.format(line))
            else:
                lines.append(line)

        if lines:
            f.seek(0)
            f.truncate()
            f.writelines(lines)


def get_proxy_ini(bind):
    d = '/etc/supervisord.d'
    _ini = lambda: glob.glob(os.path.join(d, 'corvus-{}*'.format(bind)))
    ini_files = _ini()
    if not ini_files:
        try:
            process_old_ini()
            ini_files = _ini()
        except Exception as e:
            logger.exception(e)

    ini_files.sort()
    return ini_files


def program_running(program):
    out = run('supervisorctl status {}'.format(program))
    try:
        if out.split()[1] == 'RUNNING':
            return True
    except Exception:
        pass
    return False


def all_running(programs):
    out = run('supervisorctl status {}'.format(' '.join(programs)))
    try:
        results = filter(lambda l: l.strip(), out.split('\n'))
        if all(map(lambda r: r.split()[1] == 'RUNNING', results)):
            return True
    except Exception as e:
        logger.info(e.message)
    return False


def extract_redis_package(tgz_file, path):
    with tarfile.open(tgz_file, 'r') as f:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(f, path, members=filter_sentinel(f))


def filter_sentinel(members):
    for tarinfo in members:
        if tarinfo.name != 'redis-sentinel':
            yield tarinfo


def render_redis_ini(redis_server, port):
    path = REDIS_INI.format(port)
    d = os.path.dirname(path)
    if not os.path.exists(d):
        os.makedirs(d)

    ini_tpl = resource_string('corvus_web', 'static/redis-cluster.ini.jinja')
    template = jinja2.Template(ini_tpl)
    args = {'port': port, 'redis_server': redis_server}
    ini = template.render(args)

    with open(path, 'w') as f:
        f.write(ini)

    logger.info('render {} done'.format(path))


def render_redis_conf(port, maxmemory, persistence):
    path = REDIS_CONF.format(port)
    d = os.path.dirname(path)
    if not os.path.exists(d):
        os.makedirs(d)

    conf_tpl = resource_string('corvus_web', 'static/redis.conf.jinja')
    template = jinja2.Template(conf_tpl)
    args = {'port': port, 'maxmemory': maxmemory, 'persistence': persistence}
    conf = template.render(args)

    with open(path, 'w') as f:
        f.write(conf)

    logger.info('render {} done'.format(path))


def render_redis_rsyslog(config):
    rsyslog = resource_string('corvus_web', 'static/redis-rsyslog.conf')
    logratate = resource_string('corvus_web', 'static/logrotate_redis')

    rsys_path = config.get('REDIS_RSYSLOG_PATH') or REDIS_RSYSLOG_PATH
    with open(rsys_path, 'wb') as f:
        f.write(rsyslog)

    logrotate_path = config.get('REDIS_LOGROTATE_PATH') or REDIS_LOGROTATE_PATH
    with open(logrotate_path, 'wb') as f:
        f.write(logratate)

    run('service rsyslog restart')


def redis_installed(path, archive):
    redis_bin = os.path.join(path, archive, 'bin', 'redis-server')
    return os.path.exists(redis_bin)


def download_redis_package(url, archive, path):
    path = os.path.join(path, archive)
    tgz_file = os.path.join(path, archive)
    if not os.path.exists(path):
        makedirs_with_owner(path, 'redis', 'redis')
    try:
        urllib.urlretrieve(url, tgz_file)
    except Exception as e:
        msg = 'download redis failed'
        logger.exception(msg)
        raise TaskException('{}: {}'.format(msg, e.message))

    extract_redis_package(tgz_file, path)


def check_ports(ports):
    connections = psutil.net_connections()
    all_ports = set(
        c.laddr[1] for c in connections if isinstance(c.laddr, tuple))
    ports_inuse = set(ports) & all_ports
    if ports_inuse:
        raise TaskException(
            'ports {} are in use'.format(', '.join(map(str, ports_inuse))))


def redis_sys_init():
    redis = 'redis'
    if not user_exist(redis):
        run('useradd -U -r -d /data/redis -s /bin/false {}'.format(redis))
    run('groupadd -f adm')

    dirs = [
        ('/data/redis', 'redis', 'redis'),
        ('/etc/redis', 'root', 'root'),
        ('/var/log/redis', 'syslog', 'adm'),
    ]
    for d, u, g in dirs:
        makedirs_with_owner(d, u, g)

    run('sysctl -w vm.overcommit_memory=1')
