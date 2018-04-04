+++
title = "pkg-config"
+++

`craftr/tools/pkg-config`

This Craftr module allows you to use pkg-config in your build scripts.

Example (excerpt from `craftr/libs/sfml`):

```python
public target "sfml" if OS.id != 'win32':
  eval:
    import {pkg_config} from 'craftr/tools/pkg-config'
    pkg_config(target, 'sfml-all', static=options.static)
  eval if OS.id == 'linux':
    target.exported_props['cxx.systemLibraries'] += ['GL']
```

### API

#### `pkg_config(target, pkg_name, static=False)`

Uses `pkg-config` to retrieve information about *pkg_name* and appends the
information to the `cxx.*` properties of the specified *target*. Can be
used multiple times with the same target.
