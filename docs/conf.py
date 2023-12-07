"""Sphinx configuration."""

import importlib.metadata

picobox_meta = importlib.metadata.metadata("picobox")

# -- Project settings
project = "Picobox"
author = "Ihor Kalnytskyi"
copyright = f"2017, {author}"
release = picobox_meta["Version"]
version = ".".join(release.split(".")[:2])
needs_sphinx = "2.0"

# -- General settings
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_issues",
    "sphinx_tabs.tabs",
]
exclude_patterns = ["_build", "_themes"]
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
autodoc_member_order = "bysource"
autodoc_mock_imports = ["flask"]
autodoc_typehints = "description"

# -- HTML output
html_logo = "_static/picobox.svg"
html_copy_source = False
html_show_sphinx = False
html_theme_options = {
    "description": picobox_meta["Summary"],
    "donate_url": "https://ko-fi.com/ikalnytskyi",
    "fixed_sidebar": True,
    "github_repo": "picobox",
    "github_type": "star",
    "github_user": "ikalnytskyi",
    "page_width": "1024px",
    "show_powered_by": html_show_sphinx,
}
