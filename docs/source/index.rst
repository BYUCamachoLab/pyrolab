.. PyroLab documentation master file, created by
   sphinx-quickstart on Fri Aug 14 18:48:27 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

PyroLab
=======

.. image: ./_static/images/pyrolab_icon.svg
   :width: 80%

A framework for using remote lab instruments as local resources, built on Pyro5.

**Key Features:**

- Free and open-source software provided under the GPLv3+ License
- Compatible with Python 3.6+.
- Cross-platform: runs on Windows, MacOS, and Linux.
- Included device drivers for several scopes and ThorLabs motion controllers.


Getting Started
---------------

The source repository is hosted on `GitHub`_. Prepackaged wheels of stable 
versions are in `Releases`_, along with the release history. An additional 
`Changelog`_ is included in the repository.

.. _GitHub: https://github.com/sequoiap/pyrolab
.. _Releases: https://github.com/sequoiap/pyrolab/releases
.. _Changelog: https://github.com/sequoiap/pyrolab/tree/master/docs/changelog

* **Get familiar with PyroLab**:
  :doc:`start/intro`

* **Installation instructions**:
  :doc:`start/install`

.. toctree::
   :hidden:
   :caption: Getting Started

   self
   Introduction <start/intro>
   start/install


Using PyroLab
--------------

Learn the syntax and how to connect to remote instruments using simple tutorials.

* **Hosting a nameserver**:
  :doc:`usage/tutorials/nameserver`

* **Simple remote device servers**:
  :doc:`usage/tutorials/server`

* **Connect to services provided on a network**:
  :doc:`usage/tutorials/client`

* **Using the analysis library**:
  :doc:`usage/tutorials/analysis`

.. toctree::
   :hidden:
   :caption: Using PyroLab

   usage/index
   Drivers <usage/drivers>
   Analysis <usage/analysis>


Development
-----------

PyroLab was developed by `CamachoLab at Brigham Young University <https://camacholab.byu.edu/>`_ but also
strives to be an open-source project that welcomes the efforts of volunteers. 
If there is anything you feel can be improved, functionally or in our documentation,
we welcome your feedback -- let us know what the problem is or open a pull
request with a fix!

More information about the development of PyroLab can be found at our 
`project webpage <https://camacholab.byu.edu/research/computational-photonics>`__.

.. The documentation is hosted for free at https://simphonyphotonics.readthedocs.io/.

The source for this documentation can be found in the master branch of the source repository.

.. * **Documenting The PyroLab Project**:
  :doc:`dev/docs/howto_document` | 
  :doc:`dev/docs/howto_build_docs`

.. * **Contributing to PyroLab**:
  :doc:`dev/index`

.. * **Bugs and Feature Requests**:
  :doc:`dev/bugs`

.. toctree::
   :hidden:
   :caption: Development

   dev/index


Reference
---------

.. * **View the API**:
  :doc:`reference/api`

* **License agreement**:
  :doc:`reference/license`

.. * **How we name stuff**:
  :doc:`reference/glossary`

.. toctree::
   :hidden:
   :caption: Reference

   reference/api
   reference/license
