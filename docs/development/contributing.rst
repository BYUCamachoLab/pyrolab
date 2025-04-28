.. _development_contributing:


============
Contributing
============

PyroLab was developed by `CamachoLab at Brigham Young University <https://camacholab.byu.edu/>`_ but also
strives to be an open-source project that welcomes the efforts of volunteers. 
If there is anything you feel can be improved, functionally or in our documentation,
we welcome your feedback -- let us know what the problem is or open a pull
request with a fix!

More information about the development of PyroLab can be found at our 
`project webpage <https://camacholab.byu.edu/research/computational-photonics>`__.

The documentation is hosted for free at https://pyrolab.readthedocs.io/.

The source for this documentation can be found in the master branch of the source repository.

Have an instrument driver you've written for Python code? Why not add it to 
PyroLab and expand our set of supported devices?

We're always looking to expand the number of devices included in the driver
library. We'd love to have yours, too!

To submit your driver, fork PyroLab on GitHub, add your driver (inheriting 
from the right parent classes, and creating a new driver category if it doesn't
fall under any existing categories), make sure it's well documented and 
following the numpydoc standard, test it to make sure it works over a network
(pay particular attention to the types of the arguments and the return values),
and then submit a pull request! One of the maintainers will then look at it
as soon as possible, work with you to make sure it's up to standards, and then
merge it in to the main repository and release a new version to PyPI.

You can also contribute by submitting issues, improvement suggestions, or bug
reports. We manage these through `GitHub Issues
<https://github.com/BYUCamachoLab/pyrolab/issues>`_.
