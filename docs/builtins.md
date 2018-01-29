
### Built-in variables

| Name | Type | Description |
| - | - | - |
| `OSNAME` | str | The name of the operating system, eg. `windows`, `macos` or `linux`. |
| `OSID` | str | An ID for the operating system, eg. `win32`, `darwin` or `linux`. |
| `OSARCH` | str | The architecture that the operating system is running, eg. `x86_64` or `x86`. |
| `MODE` | str | The build mode, either `"debug"` or `"release"`. |
| `DEBUG` | bool | True when the build mode is `"debug"`. |
| `RELEASE` | bool | True when the build mode is `"release"`. |
| `glob(patterns, excludes=[], parent=None)` | function | Match glob patterns relative to `parent`. If `parent` is omitted, defaults to the parent directory of the build script. |
| `error(message)` | function | Raise a build error with the specified message. |
