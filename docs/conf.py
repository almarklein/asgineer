#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Asgineer documentation build configuration file, created by
# sphinx-quickstart on Wed Sep 26 15:13:51 2018.
#
# This file is execfile()d with the current directory set to its
# containing dir.

import os
import sys

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asgineer

# -- General configuration ------------------------------------------------

extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"

# General information about the project.
project = "Asgineer"
copyright = "2018-2024, Almar Klein"
author = "Almar Klein"

# The short X.Y version.
version = ".".join(asgineer.__version__.split(".")[:2])
# The full version, including alpha/beta/rc tags.
release = asgineer.__version__

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
pygments_style = "default"
todo_include_todos = False

# -- Options for HTML output ----------------------------------------------

if not (os.getenv("READTHEDOCS") or os.getenv("CI")):
    html_theme = "sphinx_rtd_theme"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []  # ['_static']

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# This is required for the alabaster theme
# refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
html_sidebars = {
    "**": [
        "relations.html",  # needs 'show_related': True theme option to display
        "searchbox.html",
    ]
}
