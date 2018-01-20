# C/C++ language module

## Options

* `cxx.compiler` (str) &ndash; An identifier that specifies which compiler
  to use. If not specified, a legal value will be derived from the current
  platform. Additional information can be passed to the compiler by adding
  any additional data after a double-colon, eg. to select a specific MSVC
  version, use `msvc:140`. A specific MinGW version can be selected by checking
  the output of `craftr -t mingw` and using the index of the MinGW toolset
  that has been found like `mingw:1`.
* `cxx.link_style` (str) &ndash; Default value for the same-named
  `cxx.library()` parameter. Defaults to `static`.
* `cxx.unity_build` (bool) &ndash; Default value for the same-named
  `cxx.library(`) parameter. Defaults to `False`.
* `cxx.preferred_linkage` (str) &ndash; Default value for the same-named
  `cxx.library()` and `cxx.prebuilt()` parameter when there are no dependents
  that override the `link_style.`

---

* `msvc.runtime_library`

## Functions

### `cxx.version()`

Returns the version string of the compiler.

### `cxx.name()`

Returns the name of the compiler, eg. `msvc`, `gcc` or `llvm`.

### `cxx.build()`

Builds a set of C and/or C++ source files into a library or executable binary.

__Todo__

* Figure out what to do if two dependents specify different link styles when
  the `preferred_linkage` is set to `any`. Should the target be compiled twice,
  or should it fall back to its preferred link style?

__Parameters__

* `srcs` (list of str) &ndash; A list of C and/or C++ source files to compile.
* `type` (str) &ndash; The build type. Must be either `library` or `binary`.
* `debug` (bool) &ndash; Build this target with debug symbols. If not specified,
  this option is inherit from the target's dependents.
* `warnings` (bool) &ndash; Enable all warnings. Defaults to `False`.
* `warnings_es_errors (bool)` &ndash; Promote warnings to errors. Defaults to
  `False`.
* `optimize` (str) &ndash; The optimization type. Will not be considered when
  building the target in debug mode.
* `static_defines` (list of str) &ndash; A list of preprocessor macros that
  will only be set when the target is built as a static library or executable.
* `exported_static_defines` (list of str)
* `shared_defines` (list of str) &ndash; A list of preprocessor macros that
  will only be set when the target is built as a shared library.
* `exported_shared_defines` (list of str)
* `includes` (list of str) &ndash; A list of header include directories that
  are available to the source files in this target.
* `exported_includes` (list of str) &ndash; A list of header include
  directories that are available not only to the source files in this
  target but also to targets that depend on this library.
* `defines` (list of str) &ndash; A list of preprocessor macros that are
  set for the compilation of the source files.
* `exported_defines` (list of str)
* `compiler_flags` (list of str) &ndash; A list of flags for the compiler.
* `exported_compiler_flags` (list of str)
* `linker_flags` (list of str) &ndash; A list of flags for the linker.
* `exported_linker_flags` (list of str)
* `link_style` (str) &ndash; Determines the `preferred_linkage` of this
  target's dependencies if they have specified `any`. Can be either `static`
  or `shared`.
* `preferred_linkage` (str) &ndash; Determines how the library prefers to be
  built and linked. Accepted values are: `any` &ndash; Link based on the
  link-style specified by the target's dependents (see the `link_style`
  parameter); `static` &ndash; Always link statically; `shared` &ndash;
  Always link dynamically (note that depending on two dynamic libraries which
  themselves link statically to the same other library will cause duplicate
  symbol errors);
* `outname` (str) &ndash; The name of the library or binary produced by the
  target. Defaults to `$(lib)$(name)$(ext)`.
* `unity_build` (bool) &ndash; Build all input sources as one unit. This can
  lead to higher performance due to the compiler being able to more agressively
  optimize and also lead to short build times. However, rebuilding the target
  will lead to all sources to be recompiled. Default is based on the
  `cxx.unity_build` option.
* `options` (dict of (str, any)) &ndash; Additional options for the current
  compiler. The options will be converted into the compiler's `option_class`
  where unknown options are allowed but will trigger a warning when the target
  is created.

### `cxx.prebuilt()`

Represents a set of native libraries and C/C++ header files and provides
various flags to control how they are linked and exported.

__Parameters__

* `includes` (list of str) &ndash; A list of header include directories.
* `defines` (list of str) &ndash; A list of preprocessor definitions.
* `static_libs` (list of str) &ndash; A list of paths to static libraries to
  use when performing static linking.
* `static_pic_libs` (list of str) &ndash; A list of paths to static libraries
  to use when performing static PIC linking.
* `shared_libs` (list of str) &ndash; A list of paths to shared libraries to
  use when performing shared linking.
* `compiler_flags` (list of str) &ndash; A list of flags to passed to the 
  compiler step for targets that depend on this library.
* `linker_flags` (list of str) &ndash; A list of flags to passed to the link
  step for targets that depend on this library.
* `preferred_linkage` (list of str) &ndash; Controls how the library should
  be linked. See `cxx.library()` for details on this parameter.
