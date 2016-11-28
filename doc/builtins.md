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

### `loader`

The `craftr.core.manifest.BaseLoader` object that succeeded. This is always set
if the manifest specifies at least one loader (because Craftr will not proceed
if none of the loaders succeed). If no loaders are defined in the manifest, this
variable is `None`.

## Variables

### `logger`

A `craftr.core.logging.BaseLogger` instance. Use its `.debug()`, `.info()`,
`.warn()` and `.error()` members to print information during the execution of
the build script.

See also: `error()` built-in function

### session

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

### `load_module()`

### `load_file()`

### `gentool()`

### `gentarget()`

### `write_response_file()`

### `error()`

### `append_PATH()`


## Classes

### `Namespace`

### `TargetBuilder`

### `Framework`


## Exceptions

### `ModuleError`

### `ModuleNotFound`

### `ToolDetectionError`


## Modules

### `path`

### `shell`

### `platform`

### `require`
