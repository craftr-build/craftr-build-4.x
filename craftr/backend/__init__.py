# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import importlib


def load_backend(backend_name):
  ''' Loads the module that implements the backend for the specified
  *backend_name*. First, it will attempt to import a module called
  `craftr_<x>_backend` and then `craftr.backend.<x>` where `<x>` is
  to be replaced with the actual backend name. '''

  try:
    return importlib.import_module('craftr_%s_backend')
  except ImportError:
    pass
  try:
    return importlib.import_module('craftr.backend.' + backend_name)
  except ImportError:
    pass
  raise ValueError("no backend named '{0}'".format(backend_name))
