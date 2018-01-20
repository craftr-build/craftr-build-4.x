## @craftr/msvc

Determines MSVC installations on the system. Can be used as a Craftr tool
(using the `craftr --tool` option) to list available installations or to
run a command using the proper MSVC environment.

### Options

The following options specify the default MSVC installation that will be
returned from `MsvcToolkit.from_config()`:

* `msvc.install_dir` (default: `null`) &ndash; Explicitly specify the Visual Studio installation directory to use.
* `msvc.version` (default: `null`) &ndash; Must be one of `90`, `110`, `120`, `140`, `141`, etc.
* `msvc.arch` (default: `x86_amd64` on x64-bit Windows, else `x86`)
* `msvc.platform_type`
* `msvc.sdk_version`
* `msvc.cache` (default: `true` in configure step) &ndash; Whether to cache the information detected about the MSVC instalation
  (speeds up subsequent configure steps).
