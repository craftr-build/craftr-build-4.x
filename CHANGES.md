# Craftr Changelog

__v2.0.0.dev6__:

- `Target` objects can now be passed to the `frameworks = [...]` argument
  of target generators that use the `TargetBuilder` class. These input targets
  will automatically added to the implicit dependencies and their frameworks
  be added
- `Tool` objects can now be passed into the `commands = [[...]]` argument
  of targets generators
- MSVC now adds the static input library generated for DLLs to the outputs
- Experimental change not raising an exception in `craftr/core/build.py` inside
  `replace_argument_inout_vars()` when multiple outputs are specified to support
  the previously mentioned change
- add `pkg_config(static = False)` parameter
- `craftr/defaults.py` now makes `pkg_config()`, `external_file()` and
  `external_archive()` available to the built-ins
- add `glob(ignore_false_excludes=False)` parameter
- add `Manifest.filename` attribute
- `Manifest.parse()` no longer accepts a file-like object
- update verbose logging behaviour when the same module was detected twice
- `path.norm()` now makes sure that path is lowercased on Windows
