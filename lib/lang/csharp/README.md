# C# language module

Compile C# projects.

## Features

* Automatically download packages with NuGet (automatically installs NuGet if not available)
* Combine assemblies using ILMerge (automatically installed with NuGet if not available)

## Options

* `csharp.impl` (str) &ndash; The .NET implementation to use (`net` or `mono`).
  Automatically selected depending on the current platform (`net` on Windows,
  `mono` on any other).
* `csharp.csc` (str) &ndash; Name of the C# compiler. Defaults to `csc` when
  the selected implementation is `net`, otherwise `mcs`.
* `csharp.mono_arch` (str) &ndash; Used to determine the installation path of
  of Mono on Windows. Must be either `x64` or `x86`.
* `csharp.merge_tool` (str) &ndash; The name of the tool to merge assemblies.
  This should be either `ILMerge:<version>` or `ILRepack:<version>`. If not
  specified, will be selected based on `csharp.impl` (ILMerge for `net` and
  ILRepack for `mono`).

## Functions

### `csharp.build()`

__Parameters__

* `srcs` (list of str)
* `type` (str) &ndash; The target type. Must be one of `appcontainerexe`,
  `exe`, `library`, `module`, `winexe` or `winmdobj`
* `dll_dir` (str)
* `dll_name` (str)
* `main` (str)
* `csc` (CScInfo)
* `extra_arguments` (list of str)
* `merge_assemblies` (bool) &ndash; If `True`, assemblies will be merged 
  using the `ILMerge` tool. Note that `ILMerge` does not seem to work properly
  with Mono on Windows.

### `csharp.prebuilt()`

__Parameters__

* `dll_filename` (str)
* `package` (str) &ndash; The NuGet package name and version. Must be of the
  format `<name>:<version>`, eg. `Newtonsoft.Json:10.0.3`. While NuGet does
  not care about the proper letter case, your filesystem might!
* `csc` (CscInfo)

### `csharp.run()`

__Parameters__

* `binary` (str or Target)
* `*argv` (str)
* `csc` (CscInfo)
