# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

from multiprocessing.process import current_process
import click

from pyrolab.manager import DaemonManager
from pyrolab.nameserver import start_ns_loop
from pyrolab.configure import (
    update_config,
    reset_config,
    load_nameserver_configs, 
    load_daemon_configs, 
    load_service_configs,
    get_servers_used_by_services,
    get_services_for_server,
)
# from pyrolab.configure import GlobalConfiguration
from pyrolab.utils import bcolors


# GLOBAL_CONFIG = GlobalConfiguration.instance()
# GLOBAL_CONFIG.default_load()


def abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()


@click.group()
def cli():
    pass


@cli.group()
def launch(**kwargs):
    """
    Launch nameservers or a daemons.
    """
    pass


@launch.command()
@click.argument('nameserver', nargs=-1)
def nameserver(**kwargs):
    """
    Launch a nameserver. If none specified, all are launched.
    """
    if len(kwargs['nameserver']) == 0:
        print(f"Launching nameserver 'default'...")
        nscfg = load_nameserver_configs()['default']
    else:
        print(f"Launching nameserver '{kwargs['nameserver'][0]}'...")
        nscfg = load_nameserver_configs()[kwargs['nameserver'][0]]
    nscfg.update_pyro_config()
    start_ns_loop(nscfg)


@launch.command()
@click.argument('daemons', nargs=-1)
def daemon(**kwargs):
    """
    Launch daemons and associated services. If none specified, all are launched.
    """
    print(f"Collecting daemons...")
    if len(kwargs['daemons']) == 0 or kwargs['daemons'][0] == 'all':
        which = load_daemon_configs().keys()
    else:
        which = [*kwargs['daemons']]

    if __name__ == "__main__":
        if current_process().name == 'MainProcess':
            dm = DaemonManager.instance()
            for daemon in which:
                print(f"Launching daemon '{daemon}'...")
                dm.launch(daemon)
            dm.wait_for_interrupt()


@cli.group()
def config(**kwargs):
    """
    Update or reset configuration.
    """
    pass


@config.command(no_args_is_help=True)
@click.argument('filename', type=click.Path(exists=True, dir_okay=False, resolve_path=True))
def update(**kwargs):
    """
    Use a configuration file to update PyroLab's configuration.
    """
    print('Updating pyrolab config file from {}...'.format(kwargs['filename']), end='')
    update_config(kwargs['filename'])
    print(bcolors.OKGREEN + 'done' + bcolors.ENDC)


@config.command()
@click.option('--yes', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Are you sure you want to reset the configuration?')
def reset(**kwargs):
    """
    Reset the pyrolab environment.
    """
    print('Resetting pyrolab config file (deleting custom configurations)...', end='')
    reset_config()
    print(bcolors.OKGREEN + 'done' + bcolors.ENDC)


@cli.group()
@click.option('-v', '--verbose', is_flag=True, help='Show verbose details.')
@click.pass_context
def ls(ctx, verbose):
    """
    List nameservers, daemons, services or servers.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose


@ls.command()
@click.pass_context
def nameservers(ctx, **kwargs):
    """
    List nameservers.
    """
    if not ctx.obj['verbose']:
        print('Nameserver:')
        for nscfg in load_nameserver_configs().keys():
            print(f'  {nscfg}')
    else:
        print(f"Nameserver configuration (verbose):")
        cfgs = load_nameserver_configs()
            # cfgs = {kwargs['details']: load_nameserver_configs()[kwargs['details']]}
        for nscfg in cfgs.keys():
            print(f'  {nscfg}:')
            for k, v in cfgs[nscfg].to_dict().items():
                print(f'    {k}: {v}')

            
@ls.command()
@click.pass_context
def daemons(ctx, **kwargs):
    """
    List daemons.
    """
    if not ctx.obj['verbose']:
        print('Daemons:')
        for daemon in load_daemon_configs().keys():
            print(f'  {daemon}')
    else:
        print(f"Daemon configuration (verbose):")
        cfgs = load_daemon_configs()
        for daemon in cfgs.keys():
            print(f'  {daemon}:')
            for k, v in cfgs[daemon].to_dict().items():
                print(f'    {k}: {v}')


@ls.command()
@click.pass_context
@click.option('-d', '--daemon', help='List services specific to a daemon.')
def services(ctx, **kwargs):
    """
    List services.
    """
    if not kwargs['daemon']:
        services = load_service_configs()
    else:
        services = get_services_for_server(kwargs['daemon'])

    if not ctx.obj['verbose']:
        print('Services:')
        for service in services.keys():
            print(f'  {service}')
    else:
        print(f"Service configuration (verbose):")
        for service in services.keys():
            print(f'  {service}:')
            for k, v in services[service].to_dict().items():
                print(f'    {k}: {v}')


if __name__ == "__main__":
    cli()
