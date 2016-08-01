# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .api import agent
from .helpers import (
    download_corvus,
    get_proxy_ini,
    parse_corvus_conf,
    parse_proxy_ini,
    program_running,
    render_corvus_config,
    render_corvus_ini,
    render_corvus_rsyslog,
    run,
    download_redis_package,
    render_redis_ini,
    render_redis_conf,
    render_redis_rsyslog,
    check_ports,
    all_running,
    makedirs_with_owner,
    redis_sys_init,
    redis_installed,
)


def init_agent(app, url_prefix='/agent'):
    app.register_blueprint(agent, url_prefix=url_prefix)
    redis_sys_init()
    render_corvus_rsyslog(app.config)
    render_redis_rsyslog(app.config)
