# C# language module

Compile C# projects.

## Features

* Automatically download packages with NuGet (automatically installs NuGet if not available)
* Combine assemblies using ILMerge (automatically installed with NuGet if not available)

## Options

* `csharp.impl` (str) &ndash; The .NET implementation to use (`net` or `mono`).
  Automatically selected depending on the current platform (`net` on Windows,
  `mono` on any other).
* `csharp.csc` (str) &ndash; Name of the C# compiler. Defaults to `csc` but
  can be set to `mcs` if you want to use the Mono C# compiler instead.
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
* `dll_filenames` (list of str)
* `package` (str) &ndash; The NuGet package name and version. Must be of the
  format `<name>:<version>#<NETV>`, eg. `Newtonsoft.Json:10.0.3`. While NuGet
  does not care about the proper letter case, your filesystem might! Note that
  the `#<NETV>` part is optional and can be used to opt into another .NET
  framework directory that contains the package's DLL (eg. `ZedGraph:5.1.6#net35-Client`).
* `packages` (list of str`)
* `csc` (CscInfo)

### `csharp.run()`

__Parameters__

* `binary` (str or Target)
* `*argv` (str)
* `csc` (CscInfo)
