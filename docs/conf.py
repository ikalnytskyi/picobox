from __future__ import unicode_literals

import os
import pkg_resources


# -- Project settings
project = 'Picobox'
copyright = '2017, Ihor Kalnytskyi'
release = pkg_resources.get_distribution('picobox').version
version = '.'.join(release.split('.')[:2])

# -- General settings
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']
source_suffix = '.rst'
master_doc = 'index'
exclude_patterns = ['_build', '_themes']
pygments_style = 'sphinx'
intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}
autodoc_member_order = 'bysource'
autodoc_mock_imports = ['contextvars']

# -- HTML output
html_use_index = False
html_show_sourcelink = False
html_logo = '_static/picobox.svg'

if not os.environ.get('READTHEDOCS') == 'True':
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Sphinx does not support "code" directive preserving default (docutils)
# behaviour. This means code won't be highlighted which is not good. In
# order to fix that we want to register custom (Sphinx) translator for
# code directive.
#
# See https://github.com/sphinx-doc/sphinx/issues/2155 for details.
from docutils.parsers.rst import directives
from sphinx.directives.code import CodeBlock
directives.register_directive('code', CodeBlock)

# flake8: noqa
