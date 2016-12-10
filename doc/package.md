A Craftr *package* consists of at least two files: A manifest and build script.
We also call the build script *module*. These files can be placed in your
project root directory or in a sub-directory with the name `craftr/`. The nested
structure is usually used for larger projects that have a complex file tree to
keep the root directory cleaner.

Also, there can be a `.craftrconfig` depending on where the `manifest.json`
is located which will be loaded before anything else. For more information on
configuration, see the [Config documentation](config.md).

      Standard                   Nested

    |  project/               |  project/
    |    .craftrconfig        |    craftr/
    |    manifest.json        |      .craftrconfig
    |    Craftrfile           |      manifest.json
    |    source/              |      Craftrfile
    |                         |    source/

Note that in the nested format, you want to make sure to set the
`project_dir` field in the manifest to `".."`.

## Package manifest

Below you can find a list of all the available fields in a `manifest.json` file.
Note that you can use the `craftr startpackage` command to quickly generate a
manifest for your project.

Example manifest:

```json
{
  "name": "craftr.lib.curlpp",
  "version": "1.0.0",
  "dependencies": {
    "craftr.lang.cxx": "*",
    "craftr.lib.curl": "*"
  },
  "options": {
    "version": {
      "type": "string",
      "default": "v0.7.3"
    },
    "static": {
      "type": "bool",
      "help": "Whether to build a static or dynamic library. Must match the linkage of cURL.",
      "default": true
    },
    "rtti": {
      "type": "bool",
      "default": true
    }
  }
}
```

### name

*Required*. The name of the Craftr package. This name must only consist of
letters, digits, dots and underscores. The name of a package must be unique
in the Craftr ecosystem, however if you are sure that you will never submit
the package to [Craftr.net], you can choose whatever you like.

### version

*Required*. A semantic versioning number for the package. This version number
is used to find and load the correct package version when resoloving dependencies.
Note that Craftr can load the same package multiple times, given they have
different version numbers.

### description

*Optional*. A short description of what the package does and what it is used
for.

### author

*Optional*. The name of the author of the package and optionally his/her email
address. If given, the email address should be enclosed in angle brackets, like
`"John Peter <john.peter@fakemail.com>"`.

### url

*Optional*. URL to the project website. Most likely a link to the GitHub page.

### options

*Optional*. An object that describes available options for the package. The
fields for this object are the option names. These fields again map to objects
that describe the option parameter *or* simply the option type name. Example:

```json
  "options": {
    "directory": "path",
    "build_examples": {
      "type": "bool",
      "help": "Whether to build example files"
    }
  }
```

Available fields:

#### type

*Require*. The type of the option. Available option types are `"bool"`,
`"triplet"` and `"string"`.

#### default

*Optional*. The default value of the option if no explicit value is defined.
The default value of this field depends on the option `type`.

#### help

*Optional*. A short description of what the option is used for.

#### inherit

*Optional*. Defaults to `true`. If this field is `true` and the value of the
option is not defined explicitly, the global option with the same name will be
inherited. For example if your package is called `some.cool.package` and the
option name is `build_examples`, then the full qualified option name would be
`some.cool.package.build_examples`. Now if this option is not set but a global
option `build_examples` is set, this value will be used for the option.

### dependencies

*Optional*. An object that describes the dependencies of the package. The
fields of this object are the names of the required Craftr packages. The
value of each field is a *version criteria*, that is a string which specifies
one exact version number or a range of accepted version numbers. The format is
similar to `npm` version selectors. Examples:

    "craftr.lib.curl": "*"          // any version, but the newest we can get
    "craftr.lib.curl": "=1.2.9"     // exactly version 1.2.9
    "craftr.lib.curl": "1.3 - 1.8"  // any version between 1.3.0 and 1.8.0
    "craftr.lib.curl": "2.x.2"      // major and patch version 2, but any minor version

Note that Craftr will refuse to load modules with `load_module()` that are not
listed in the manifest `dependencies`!

> __Important__: Keep in mind that the version number defined in the
> `dependencies` are the version numbers of Craftr packages, not necessarily
> the version of the actual library that can be used with it.

### main

*Optional*. The name of the build script. Usually you don't need/want to set
this field. The default value is `"Craftrfile"`.

### project_dir

*Optional*. A relative path the alters the `project_dir` variable in the Craftr
build script. This influences the way the `local()` built-in function behaves.
For more information on built-in functions, see the [Builtins documentation](builtins.md).

Note that you usually want this field to be set to `".."` if you are using the
nested project structure. The `craftr startpackage` command has a `-n/--nested`
option which creates a nested project structure and also sets this `project_dir`
field.
