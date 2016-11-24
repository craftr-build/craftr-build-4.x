Configuration values in Craftr are stored in the `Session.options` dictionary.
There are those options that are defined in Craftr packages and are automatically
validated, but they are not limited by these definitions.

Note that options that are not listed in Craftr package manifests do *not*
have the *inheriting* behaviour, thus the full qualified option name must
be defined.

## Options

### `craftr.ninja`

The path or name of the Ninja executable to invoke. Defaults to the `NINJA`
environment variable or simply `ninja`.

## Configuring

On the command-line, you can use the `-d/--option` argument to set options.
These options override every option read from configuration files. Alternatively,
you can specify one or more configuration files to load with the `-c/--config`
argument. If none are specified, the file `.craftrconfig` in the current working
directory is loaded if it exists.

If present, the file `.craftrconfig` in the users home directory will always
be loaded.

Configuration files are simple `.ini` files with two additions:

### Include configuration files

A configuration file can include another configuration file using the
`include` section directive. Note that the `if-exists` portion is optional
and can be used if you don't want it to be an error if the included file
does not exist.

```ini
[include "path/to/file.ini" if-exists]
```

### Setting global options

The `[__global__]` section can be used to define options without a prefix.

```ini
[__global__]
debug = true
```
