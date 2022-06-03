# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import datetime
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

autoclass_content = "both"

# -- Project information -----------------------------------------------------

project = "Piccolo API"
year = datetime.datetime.now().strftime("%Y")
author = "Daniel Townsend"
copyright = f"{year}, {author}"


import piccolo_api  # noqa

version = ".".join(piccolo_api.__VERSION__.split(".")[:2])
release = piccolo_api.__VERSION__

# -- General configuration ---------------------------------------------------

master_doc = "index"

extensions = []

# -- Autodoc -----------------------------------------------------------------

extensions += ["sphinx.ext.autodoc"]
autodoc_typehints = "signature"
autodoc_typehints_format = "short"
autoclass_content = "both"
autodoc_type_aliases = {
    "ASGIApp": "ASGIApp",
    "PreLoginHook": "PreLoginHook",
    "LoginSuccessHook": "LoginSuccessHook",
    "LoginFailureHook": "LoginFailureHook",
}

# -- Intersphinx -------------------------------------------------------------

extensions += ["sphinx.ext.intersphinx"]
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "piccolo": ("https://piccolo-orm.readthedocs.io/en/latest/", None),
}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "piccolo_theme"
html_short_title = "Piccolo API"
