This document describes the available built-in data members and functions in
a `Craftrfile` build script. Except for the package-specific variables, all
built-in functions and classes are defined in the `craftr.defaults` module.

## Package-specific variables

### `project_dir`

The project directory. This is usually the same as the directory of the
Craftr package manifest (`manifest.json`), but can be altered with the
`project_dir` field in the manifest.

This variable has direct influence on the behaviour of the `local()` function.

### `options`

An object that has as its members all options defined in the package manifest.

```python
if options.bad_weather:
  logger.warn('be careful, you are choosing a build environment with bad weather')
```


## Variables

### `logger`

A `craftr.core.logging.BaseLogger` instance. Use its `.debug()`, `.info()`,
`.warn()` and `.error()` members to print information during the execution of
the build script.

See also: `error()` built-in function

### `session`

The current `craftr.core.session.Session` object that manages the build process
and Craftr packages. Sometimes you will want to modify its `.options` member
or retrieve the currently executed Craftr module from its `.module` member.


## Functions

### `gtn()`

### `include_defs()`

### `glob()`

### `local()`

### `buildlocal()`

### `relocate_files()`

### `filter()`

### `map()`

### `zip()`

### `load()`

### `load_file()`

### `gentool()`

### `gentarget()`

### `genalias()`

### `runtarget()`

### `write_response_file()`

### `error()`

### `return_()`

### `append_PATH()`

### `external_file(*urls, filename = None, directory = None, copy_file_urls = False, name = None)`

### `external_archive(*urls, directory = None, name = None)`

### `pkg_config(pkg_name, static = False)`

Uses `pkg-config` to read the flags for the library specified with *pkg_name*
and returns a Framework object. If `pkg-config` is not available on the platform
or the library can not be found, `pkg_config.Error` is raised.

```python
from craftr.loaders import pkg_config
try:
  cURL = pkg_config('libcurl')
except pkg_config.Error:
  # compile from source or whatever
```


## Classes

### `Namespace`

### `TargetBuilder`

### `Framework`


## Exceptions

### `ModuleError`

### `ModuleReturn`

### `ModuleNotFound`

### `ToolDetectionError`


## Modules

### `path`

### `shell`

### `platform`
