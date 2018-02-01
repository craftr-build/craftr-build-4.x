
### Built-in variables

| Name | Type | Description |
| - | - | - |
| `OS` | `OsInfo` | An `OsInfo` object that contains the name, id, type and arch of the current operating system. Possible names are `windows`, `macos` and `linux`. Possible IDs are `win32`, `darwin` and `linux`. Possible types are `nt` and `posix`. Note that on Windows Cygwin, the type will also be `posix`.  Possible architectures are `x86_64` and `x86`. |
| `BUILD` | `BuildInfo` | A `BuildInfo` object that tells you whether this is a release or debug build. Members of this object are `mode`, `debug` and `release`. |
| `error(message)` | function | Raise an error (`craftr.dsl.ExplicitRunError`) with the specified message. |
| `fmt(format)` | function | Expects a Python `str.format()` string that will be substituted in the context of the current global and local variables. |
| `glob(patterns, excludes=[], parent=None)` | function | Match glob patterns relative to `parent`. If `parent` is omitted, defaults to directory of the build script or the target if explicitly set with `this.directory`. |
| `load(filename)` | function | Loads a Craftr module and returns its eval namespace, or loads a Python file by (relative) filename and returns its namespace. |
| `option_default(option, value)` | function | Set the default value for an option. Use this in an `eval` block before the `options` block. |
