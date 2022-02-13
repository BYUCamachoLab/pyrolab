===================
Documenting PyroLab
===================

PyroLab strictly adheres to the `numpydoc`_ docstring style guide. Since we use
the numpydoc parser in building the docs, straying from that convention will 
cause the automated documentation build to fail.

.. _numpydoc: https://numpydoc.readthedocs.io/en/latest/

The documentation is also written using restructured text (reST), the language
of choice for parsing and building with `Sphinx`_.

.. _Sphinx: https://www.sphinx-doc.org/en/master/

For uniformity in documentation, the reST standard we use for headings is as
follows (docstrings that use headings that will be rendered by Sphinx should
also follow this convention):

* # with overline, for parts
* * with overline, for chapters
* =, for sections
* -, for subsections
* ^, for subsubsections
* “, for paragraphs

Therefore, most documentation pages (and the docstrings themselves) should use
the following headings:

.. code-block:: rst
   
   Heading 1
   =========

   Heading 2
   ---------

   Heading 3
   ^^^^^^^^^
