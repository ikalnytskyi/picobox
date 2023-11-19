"""Sphinx configuration."""

import importlib.metadata

# -- Project settings
project = "Picobox"
author = "Ihor Kalnytskyi"
copyright = "2017, Ihor Kalnytskyi"
release = importlib.metadata.version("picobox")
version = ".".join(release.split(".")[:2])

# -- General settings
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
]
source_suffix = ".rst"
master_doc = "index"
exclude_patterns = ["_build", "_themes"]
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
autodoc_member_order = "bysource"
autodoc_mock_imports = ["flask"]
autodoc_typehints = "description"

# -- HTML output
html_use_index = False
html_show_sourcelink = False
html_logo = "_static/picobox.svg"
html_theme = "furo"
html_theme_options = {
    "navigation_with_keys": True,
}
