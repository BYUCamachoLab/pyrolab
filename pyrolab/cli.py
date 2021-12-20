# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
pyrolab commands to be implemented


pyrolab ps
pyrolab config update FILENAME
pyrolab config reset
pyrolab config export FILENAME
pyrolab reload
pyrolab start NAME
pyrolab stop NAME
pyrolab info NAME
pyrolab logs NAME
pyrolab rename NAME
pyrolab restart NAME
pyrolab rm NAME
pyrolab add nameserver NAME
pyrolab add daemon NAME
pyrolab add service NAME
pyrolab remotens list NAME
pyrolab version


Autoreload when watching a directory? 
* watchdog
* watchgod
"""

import typer


app = typer.Typer()


@app.command()
def hello(name: str):
    message = typer.style(f"Hello {name}!", fg=typer.colors.GREEN, bold=True)
    typer.echo(message)

@app.command()
def goodbye(name: str, formal: bool=False):
    if formal:
        typer.echo("Goodbye, Mr. " + name + ".")
    else:
        typer.echo(f"Bye, {name}!")


if __name__ == "__main__":
    app()
    



# from multiprocessing.process import current_process
# import click

# from pyrolab.manager import ProcessManager
# from pyrolab.configure import GlobalConfiguration, update_config, reset_config
# from pyrolab.utils import bcolors


# GLOBAL_CONFIG = GlobalConfiguration.instance()
# GLOBAL_CONFIG.default_load()


# def abort_if_false(ctx, param, value):
#     if not value:
#         ctx.abort()


# @click.group()
# def cli():
#     pass


# @cli.group()
# def launch(**kwargs):
#     """
#     Launch nameservers or a daemons.
#     """
#     pass


# @launch.command()
# @click.argument('nameserver', nargs=-1)
# def nameserver(**kwargs):
#     """
#     Launch a nameserver. If none specified, all are launched.
#     """
#     print(f"Collecting nameservers...")
#     if len(kwargs['nameserver']) == 0 or kwargs['nameserver'][0] == 'all':
#         which = GLOBAL_CONFIG.list_nameservers()
#     else:
#         which = [*kwargs['nameserver']]

#     if current_process().name == 'MainProcess':
#         manager = ProcessManager.instance()
#         for nameserver in which:
#             print(f"Launching nameserver '{nameserver}'...")
#             manager.launch_nameserver(nameserver)
#         manager.wait_for_interrupt()


# @launch.command()
# @click.argument('daemons', nargs=-1)
# def daemon(**kwargs):
#     """
#     Launch daemons and associated services. If none specified, all are launched.
#     """
#     print(f"Collecting daemons...")
#     if len(kwargs['daemons']) == 0 or kwargs['daemons'][0] == 'all':
#         which = GLOBAL_CONFIG.list_daemons()
#     else:
#         which = [*kwargs['daemons']]

#     if current_process().name == 'MainProcess':
#         dm = ProcessManager.instance()
#         for daemon in which:
#             print(f"Launching daemon '{daemon}'...")
#             dm.launch_daemon(daemon)
#         dm.wait_for_interrupt()


# @cli.group()
# def config(**kwargs):
#     """
#     Update or reset configuration.
#     """
#     pass


# @config.command(no_args_is_help=True)
# @click.argument('filename', type=click.Path(exists=True, dir_okay=False, resolve_path=True))
# def update(**kwargs):
#     """
#     Use a configuration file to update PyroLab's configuration.
#     """
#     print('Updating pyrolab config file from {}...'.format(kwargs['filename']), end='')
#     update_config(kwargs['filename'])
#     print(bcolors.OKGREEN + 'done' + bcolors.ENDC)


# @config.command()
# @click.option('--yes', is_flag=True, callback=abort_if_false,
#               expose_value=False,
#               prompt='Are you sure you want to reset the configuration?')
# def reset(**kwargs):
#     """
#     Reset the pyrolab environment.
#     """
#     print('Resetting pyrolab config file (deleting custom configurations)...', end='')
#     reset_config()
#     print(bcolors.OKGREEN + 'done' + bcolors.ENDC)


# @cli.group()
# @click.option('-v', '--verbose', is_flag=True, help='Show verbose details.')
# @click.pass_context
# def ls(ctx, verbose):
#     """
#     List nameservers, daemons, services or servers.
#     """
#     ctx.ensure_object(dict)
#     ctx.obj['verbose'] = verbose


# @ls.command()
# @click.pass_context
# def nameservers(ctx, **kwargs):
#     """
#     List nameservers.
#     """
#     if not ctx.obj['verbose']:
#         print('Nameserver:')
#         for nscfg in GLOBAL_CONFIG.list_nameservers():
#             print(f'  {nscfg}')
#     else:
#         print(f"Nameserver configuration (verbose):")
#         for nscfg in GLOBAL_CONFIG.list_nameservers():
#             print(f'  {nscfg}:')
#             for k, v in GLOBAL_CONFIG.get_nameserver_config(nscfg).to_dict().items():
#                 print(f'    {k}: {v}')

            
# @ls.command()
# @click.pass_context
# def daemons(ctx, **kwargs):
#     """
#     List daemons.
#     """
#     if not ctx.obj['verbose']:
#         print('Daemons:')
#         for daemon in GLOBAL_CONFIG.list_daemons():
#             print(f'  {daemon}')
#     else:
#         print(f"Daemon configuration (verbose):")
#         for daemon in GLOBAL_CONFIG.list_daemons():
#             print(f'  {daemon}:')
#             for k, v in GLOBAL_CONFIG.get_daemon_config(daemon).to_dict().items():
#                 print(f'    {k}: {v}')


# @ls.command()
# @click.pass_context
# @click.option('-d', '--daemon', help='List services specific to a daemon.')
# def services(ctx, **kwargs):
#     """
#     List services.
#     """
#     if not kwargs['daemon']:
#         services = GLOBAL_CONFIG.list_services()
#     else:
#         services = GLOBAL_CONFIG.list_services_for_daemon(kwargs['daemon'])

#     if not ctx.obj['verbose']:
#         print('Services:')
#         for service in services:
#             print(f'  {service}')
#     else:
#         print(f"Service configuration (verbose):")
#         for service in services:
#             print(f'  {service}:')
#             for k, v in GLOBAL_CONFIG.get_service_config(service).to_dict().items():
#                 print(f'    {k}: {v}')


# if __name__ == "__main__":
#     cli()
