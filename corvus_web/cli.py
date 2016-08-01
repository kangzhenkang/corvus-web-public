# -*- coding: utf-8 -*-

from __future__ import absolute_import

from ruskit import cli


@cli.command
@cli.argument('-p', '--port', type=int)
def dev_serve(args):
    from .app import create_web_app
    app = create_web_app()
    app.run(debug=True, host='0.0.0.0', port=args.port)


@cli.command
@cli.argument('-p', '--pool-size', type=int, default=30)
def task_daemon(args):
    import gevent.monkey
    gevent.monkey.patch_all()

    from .app import create_app
    app = create_app()

    from .task.manager import TaskManager
    manager = TaskManager(app, args.pool_size)
    try:
        manager.run()
    except KeyboardInterrupt:
        pass


@cli.command
@cli.argument('-p', '--pool-size', type=int, default=150)
def cache_daemon(args):
    import gevent.monkey
    gevent.monkey.patch_all()

    from .cache import node_cache
    node_cache.pool_size = args.pool_size
    try:
        node_cache.run()
    except KeyboardInterrupt:
        pass


@cli.command
@cli.argument('-p', '--port', type=int)
def agent(args):
    from .app import create_app
    from .agent import init_agent

    app = create_app()
    init_agent(app)
    app.run(host='0.0.0.0', port=args.port)


@cli.command
@cli.argument('-a', '--address')
@cli.argument('-i', '--interval')
@cli.pass_ctx
def stats(ctx, args):
    from .app import create_app
    from .stats import Stats

    app = create_app()

    if not args.address:
        args.address = app.config.get('STATSD_ADDR')

    if not args.address:
        ctx.abort('Statsd address not configured')

    if not args.interval:
        args.interval = app.config.get('STATSD_INTERVAL', 10)

    host, port = args.address.split(':')
    stats = Stats(host, port, args.interval)
    try:
        stats.start()
    except KeyboardInterrupt:
        pass


@cli.command
def sync_version(args):
    from .app import create_app
    from .models import Proxy
    from .utils import get_proxy_info
    create_app()

    updates = []
    for proxy in Proxy.all():
        info = get_proxy_info(proxy['host'], proxy['port'])
        if not info:
            continue
        version = info.get('version', 'unknown')
        if proxy['version'] != version:
            updates.append((proxy['id'], {'version': version}))
    Proxy.update_many(updates)


def main():
    parser = cli.CommandParser()
    parser.add_command(dev_serve)
    parser.add_command(task_daemon)
    parser.add_command(cache_daemon)
    parser.add_command(agent)
    parser.add_command(stats)
    parser.add_command(sync_version)
    parser.run()
