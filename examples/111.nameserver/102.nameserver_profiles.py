
from pyrolab.nameserver import NameserverConfiguration, ns_profile
from pyrolab.api import start_ns_loop

# View installed profiles on your machine
print(ns_profile.list())

# Create a few different profiles
name = 'local'
cfg = NameserverConfiguration(
    ns_host="0.0.0.0",
    ns_port=9090,
    ns_autoclean=15.0,
    storage_type="memory"
)
try:
    ns_profile.add(name, cfg)
except Exception as e:
    print(e)

name = 'production'
cfg = NameserverConfiguration(
    ns_host="camacholab.ee.byu.edu",
    ns_port=9090,
    ns_autoclean=15.0,
    storage_type="sql"
)
try:
    ns_profile.add(name, cfg)
except Exception as e:
    print(e)

# View again the installed profiles on your machine
print(ns_profile.list())

# We can see the configuration values for the loaded profile.
print(ns_profile.configuration)

# We can remove profiles by name.
ns_profile.delete('production')

# We could export (or install) profiles from other machines.
# path = pathlib.Path.home()
# ns_profile.export('local', path)
# ns_profile.install('production', some_profile_path)

# If you make changes to the loaded profile, you can save it to persist it.
ns_profile.NS_PORT = 9091
ns_profile.save()

print(ns_profile.configuration)

# We'll clean up everything we did with this file
ns_profile.delete('local')
