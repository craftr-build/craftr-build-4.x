# craftr

Craftr is a meta build system that produces [Ninja] build manifests. It
uses [Python 3] for build scripts, which allows for an ease to use description
language but also gives you all the power if you need it.

  [Ninja]: https://github.com/ninja-build/ninja
  [Python 3]: https://www.python.org/

## How It Works

Craftr is built from versioned modules. As such, every Craftr module must
provide a `manifest.json` that contains all metadata such as the module
name, version, dependencies, options, etc. We cann the manifest, build script
and optionally other files together a *package*.

To start a new package, use the `craftr startpackage` command.

```json
$ craftr startpackage cxx.mylib
$ cat cxx.mylib/craftr/manifest.json
{
  "name": "cxx.mylib",
  "version": "1.0.0",
  "author": "",
  "url": "",
  "dependencies": {},
  "options": {},
  "loaders": []
}
```

The actual build script is located at `cxx.mylib/craftr/Craftrfile`. This
file is executed in the Craftr runtime and has some additional and alternative
built-in functions. For more information, see the `craftr.defaults` module.

```python
# cxx.mylib
utils = require('./utils.py')
logger.info(utils.say_hello())

include_defs('./DEFINITIONS')
logger.info('from ./DEFINITIONS:', VAR_FROM_DEFINITIONS_FILE)

# note that we HAVE to add this to the 'dependencies' section in the
# manifest in order load it in the build script.
another_lib = load_module('cxx.anotherlib')

# TODO: Show some sample C++ compilation targets.
```

### Dependencies

Dependencies are added to the `manifest.json` by specifying the dependency
name and map it to a version criteria. When using the `load_module()` function,
Craftr will automatically load the newest Craftr module that is available
matching the criteria.

```json
{
  "dependencies": {
    "cxx.anotherlib": "*",  // any version
    "cxx.curl": "> 1.2.8"
  }
}
```

> __IMPORTANT__: The version you specify is the version of the Craftr module
> that is specified in its manifest, NOT NECESSARILY the version of the
> library.

### Loaders

Craftr has a feature called "loaders" that we use to load external data into
a Craftr module before or during the build process. This is useful for
libraries that don not natively build with Craftr. Instead of the Craftr
package to contain the source files, they will be downloaded and extracted to
a temporary directory by a *loader*.

Currently there is only the `"url"` loader support, but in the future there
will also be a `"pkg_config"` loader.

```json
{
  "loaders": [
    {
      "name": "source",
      "type": "url",
      "urls": [
        "file://$source_dir",
        "https://curl.haxx.se/download/curl-$load_version.tar.gz"
      ]
    }
  ]
}
```

## Requirements

- [colorama](https://pypi.python.org/pypi/colorama) (optional, Windows)
- [glob2](https://pypi.python.org/pypi/glob2)
- [jsonschema](https://pypi.python.org/pypi/jsonschema)
- [ninja_syntax](https://pypi.python.org/pypi/ninja_syntax)
- [nr](https://pypi.python.org/pypi/nr)
- [py-require](https://pypi.python.org/pypi/py-require)\*
- [termcolor](https://pypi.python.org/pypi/termcolor) (optional)
- [werkzeug](https://pypi.python.org/pypi/werkzeug)

> \* While the `require` module is not directly used by Craftr, it is a
> common mechanism to load an additional file into a Craftr build script.
>
> ```python
> import require
> utils = require('./utils')
> ```

## License

    The Craftr build system
    Copyright (C) 2016  Niklas Rosenstein

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

For more information, see the `LICENSE.txt` file.