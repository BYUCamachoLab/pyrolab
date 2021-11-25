import click
from yaml import load

from pyrolab.nameserver import load_ns_configs


@click.group()
def cli():
    pass


@cli.command()
@click.option('--list-profiles', is_flag=True, help='List all installed profiles.')
@click.option('-l', '--launch', default='default', help='Launch the specified nameserver profile ("default" started if none provided).')
def nameserver(**kwargs):
    """
    Start the PyroLab Nameserver.
    """
    if kwargs['list_profiles']:
        print('Profiles:')
        for profile in load_ns_configs().keys():
            print(f'  {profile}')
        return
    if 'profile' in kwargs:
        print(kwargs['profile'])
        return


if __name__ == "__main__":
    cli()
