"""
Public build-script API of the Craftr build system.
"""

import {Configuration} from 'craftr/utils/cfgparser'

#: Set to True when this is a release build.
release = False

#: Set to the build directory.
build_directory = None

#: This is a persistent cache that is serialized into JSON. All objects in
#: this dictionary must be JSON serializable.
cache = {}

#: Craftr configuration, automatically loaded from the configuration file
#: by the CLI.
options = Configuration()
