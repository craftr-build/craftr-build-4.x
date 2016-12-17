# Craftr Changelog

__v2.0.0.dev6__:

API Changes

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
- renamed `load_module()` to `load()`, using the old name displays a warning
- add `BaseLogger.flush()` method
- add `craftr.utils.path.getmtime()` and `.getimtime()`

Library Changes

- add `craftr.lib.sdl2` (tested on Windows only)
- add `craftr.lib.zlib` (tested on Windows only)
- add `uic()` and `moc()` target generators to `craftr.lib.qt5` (tested on Windows only)
- `craftr.lib.cURLpp` always requires RTTI enabled

Behaviour Changes

- Build-directory is now removed again if nothing was exported (eg. when
  using `craftr build` without formerly exporting the build files)
- Output before Ninja is executed is now flushed to make sure all data is
  flushed to the terminal before Ninja outputs to the pipe
