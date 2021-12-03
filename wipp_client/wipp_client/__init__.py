# -*- coding: utf-8 -*-

"""Top-level package for WIPP Python Client."""

__author__ = "Konstantin Taletskiy"
__email__ = "konstantin@taletskiy.com"
# Do not edit this string manually, always use bumpversion
# Details in CONTRIBUTING.md
__version__ = "0.2.0"


def get_module_version():
    return __version__


from .wipp import Wipp, WippEntity, WippPlugin
