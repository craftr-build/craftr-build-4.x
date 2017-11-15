# C/C++ language module

## Options

* `cxx.compiler` (str) &ndash; An identifier that specifies which compiler
  to use. If not specified, a legal value will be derived from the current
  platform. Additional information can be passed to the compiler by adding
  any additional data after a double-colon, eg. to select a specific MSVC
  version, use `msvc:140`.
* `cxx.link_style` (str) &ndash; Default value for the same-named
  `cxx.library()` parameter. Defaults to `static`.
* `cxx.unity_build` (bool) &ndash; Default value for the same-named
  `cxx.library(`) parameter. Defaults to `False`.
* `cxx.preferred_linkage` (str) &ndash; Default value for the same-named
  `cxx.library()` and `cxx.prebuilt()` parameter when there are no dependents
  that override the `link_style.`

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
* `target` (str) &ndash; The target build type. Must be either `library` or
  `binary`.
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
* `libname` (str) &ndash; The name of the library if it is produced by this
  target. The macro `$(ext)` will be replaced with a platform-appropriate
  extension. The macro `$(lib)` will be replaced by `lib` on a unix-style
  platform. A version number may be specified like `$(lib)foo.$(ext 2.3)` which
  will result in `libfoo.2.3.dylib` on Mac and `libfoo.so.2.3` on Linux and
  `foo.2.3.dll` on Windows.
* `unity_build` (bool) &ndash; Build all input sources as one unit. This can
  lead to higher performance due to the compiler being able to more agressively
  optimize and also lead to short build times. However, rebuilding the target
  will lead to all sources to be recompiled. Default is based on the
  `cxx.unity_build` option.

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