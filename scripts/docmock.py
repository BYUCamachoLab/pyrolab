autodoc_mock_imports = [
    'numpy',
    'scipy',
    'Pyro5',
    'pydantic',
    'yaml',
    'appdirs',
    'deprecation',
    'appnope',
    'typer',
    'colorama',
    'tabulate', 
    'serial',
    'thorlabs_kinesis',
    'pyfirmata',
    'sacher_tec',
    'firmata',
]

import sys
from unittest.mock import Mock

for item in autodoc_mock_imports:
    sys.modules[item] = Mock()
