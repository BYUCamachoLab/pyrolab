#!/usr/bin/env python3

# Copyright © 2023 PyroLab Project Contributors and others (see AUTHORS.txt).
# The resources, libraries, and some source files under other terms (see NOTICE.txt).
#
# This file is part of PyroLab.
#
# PyroLab is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyroLab is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyroLab. If not, see <https://www.gnu.org/licenses/>.

# This file is a development server only, not fit for production use! To learn
# about running flask apps in production, see
# https://flask.palletsprojects.com/en/2.2.x/deploying/


from pyromonitor import create_app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, use_debugger=False, use_reloader=True, passthrough_errors=True)
