# development

Bugfixes

- An empty value for an option of type `path` will no longer end up have the
  value of the project directory but instead be an empty string
- Fix `msvc_runtime_library` parameter in compile procedure of the
  `craftr.lang.cxx.msvc` module (invert behaviour of `'static'` and `'dynamic'`)

API Changes

- change `load()` now accepts a `mode` parameter instead of `get_namespace`,
  can be one of `'exports'` (defualt), `'namespace'` and `'mmodule'`.

Standard Library

- add `craftr.utils.archive` module

# v2.0.0.dev7

Bugfixes

- Fix function `cxx_extend_framework()` that is kept for backwards compatibility,
  which was missing to call the new `cxx.extend_framework()`.
- Fix `NameError` in `'craftr build'` command
- fix `errno.ENOTTY` raised on Linux CI runners (eg. GitLab)

Changes

- If terminal size can not be determined, assume 120 characters wide
  instead of 80

# v2.0.0.dev6

General Changes

- Default manifest configuration format is now CSON (`manifest.cson`),
  JSON being kept for backwards compatibility (see #168)
- Fix crash on Travis CI with `tty.terminal_size()` (see #169)
- Add `craftr lock` command which generates `.dependency-lock` file in the
  same directory as the project's Manifest (see #155)

API Changes

- add `pkg_config(static = False)` parameter
- add `pkg_config()`, `external_file()` and `external_archive()` to `craftr/defaults.py`
- add `glob(ignore_false_excludes=False)` parameter
- add `BaseLogger.flush()` method
- add `craftr.utils.path.getmtime()` and `.getimtime()`
- add `write_response_file(suffix='')` parameter
- add `Default` singleton to built-in namespace
- add `gentask()` and `task()` built-in functions (see #163)
- add `Target.runprefix` parameter and attribute
- add `Session.main_module` member
- add `Module.dependencies` member
- change `Target` objects can now be passed to the `frameworks = [...]` argument
  of target generators that use the `TargetBuilder` class. These input targets
  will automatically added to the implicit dependencies and their frameworks
  be added
- change `Tool` objects can now be passed into the `commands = [[...]]` argument
  of targets generators
- change `runtarget()` to take `Target.runprefix` into account
- change `path.norm()` now makes sure that path is lowercased on Windows
- change `load_file()` now adds the loaded file to `Module.dependent_files`
- change `glob(patterns)` now accepts a string additionally to a list of strings
- rename `load_module()` to `load()`, using the old name displays a warning

Library Changes

- add `craftr.lib.sdl2` (tested on Windows only)
- add `craftr.lib.zlib` (tested on Windows only)
- add `uic()` and `moc()` target generators to `craftr.lib.qt5` (tested on Windows only)
- add support for `source_directory` argument in `cxx.c_compile()` and `cxx.cpp_compile()`
  (actually implemented in `craftr.lang.cxx.common` and `craftr.lang.cxx.msvc`), see #154
- add `craftr.lang.csharp:compile()` to be used for unstarred import, and add docstrings
- add `exflags` option to `craftr.lang.cxx.common` module (see #152)
- add `ccprefix` option to `craftr.lang.cxx.common` module (related to #149)
- add to `craftr.lang.cxx` functions `static_library()` and `shared_library()`
- change `craftr.lang.cxx` member names, old names are still available with a
  deprecation notice. `binary() -> executable()`, `c_compile() -> compile_c()`,
  `cpp_compile() -> compile_cpp()`
- change `craftr.lib.cURLpp` always requires RTTI enabled
- change `craftr.lang.cxx.msvc` now adds the static input library generated for DLLs to the outputs
- change MSVC `compile()` now supports response-files for long list of includes
- update default download version of `craftr.lib.zlib` to `1.2.10`

Behaviour Changes

- Experimental change not raising an exception in `craftr/core/build.py` inside
  `replace_argument_inout_vars()` when multiple outputs are specified to support
  the previously mentioned change
- Update verbose logging behaviour when the same module was detected twice
- Build-directory is now removed again if nothing was exported (eg. when
  using `craftr build` without formerly exporting the build files)
- Output before Ninja is executed is now flushed to make sure all data is
  flushed to the terminal before Ninja outputs to the pipe
- When using `craftr build`, Craftr now checks if any of the files that generated
  the build data (ie. manifests and Craftrfiles) have changed since the build
  files was generated and notifies the user in that case (see #162)
- `craftr.core.logging.DefaultLogger` now logs the module and line number from
  which the log occurred, padded to the right side of the terminal
- Craftr now exports a variable `Craftr_run_command` into the Ninja manifest
- Fix invalid Ninja manifests generated with foreach Targets with no inputs (see #151)

Internal API Changes

- add `craftr.core.session.Module.current_line` property
- add `Module.scriptfile` property
- add `Module.dependent_files` attribute
- add `Manifest.filename` attribute
- add `craftr.core.build.Graph.add_task()` and `.tasks` members
- add `craftr.core.build.Task` class
- add `tty.terminal_size(default)` parameter
- change `Manifest.parse()` no longer accepts a file-like object

Command-line Changes

- add `-P/--project-dir` parameters to `craftr`
- add `craftr options [-m MODULE] [-r] [-d]` command (see #166)
- add `craftr deptree [-m MODULE]` command (see #166)
- add `craftr help [name]` command (see #167)
- fix `craftr run` command
- add `[task] [task_args...]` arguments to `craftr run` (for internal use mostly)
