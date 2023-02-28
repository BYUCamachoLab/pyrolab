import os
import sys
import platform
import pathlib

from flask import Flask


# Check if Python version is supported
pyversion = sys.version_info
if pyversion < (3, 7, 0):
    raise Exception(
        "PyroLab requires Python 3.7+ (version "
        + platform.python_version()
        + " detected)."
    )


# Metadata
__name__ = "pyromonitor"
__author__ = "BYU CamachoLab"
__copyright__ = "Copyright 2023, The PyroLab Project"
__version__ = "0.2.1"
__license__ = "GPLv3+"
__maintainer__ = "Sequoia Ploeg"
__maintainer_email__ = "sequoiac@byu.edu"
__status__ = "Development" # "Production"
__project_url__ = "https://github.com/sequoiap/pyrolab"
__forum_url__ = "https://github.com/sequoiap/pyrolab/issues"
__website_url__ = "https://camacholab.byu.edu/"


# Configuration directories
# Old api deprecated in 3.11, new api added in 3.9
if sys.version_info < (3, 9, 0):
    base_path = pathlib.Path(__file__).resolve().parent
else:
    from importlib.resources import files
    base_path = files("pyromonitor")
base_path = base_path / "localdata"

# Data directories
DATA_DIR = pathlib.Path(base_path)
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "config.yaml"


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    from . import lister
    app.register_blueprint(lister.bp)

    return app
