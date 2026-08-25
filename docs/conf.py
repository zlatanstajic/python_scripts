# Configuration file for the Sphinx documentation builder.
import os
import sys

# Add the parent directory to sys.path so we can import the package
sys.path.insert(0, os.path.abspath(".."))

# -- Project information --
project = "Python Scripts"
copyright = "2026, Contributors"
author = "Contributors"
release = "1.0.0"
version = "1.0"

# -- General configuration --
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output --
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

html_theme_options = {
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "vcs_pageview_mode": "",
}

# -- Options for autodoc --
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "undoc-members": True,
    "show-inheritance": True,
}

# -- Options for autosummary --
autosummary_generate = True
