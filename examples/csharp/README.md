## examples/csharp

This example demonstrates how to compile a C# application with dependencies
and bundling them into a single executable.

### Build & Run

```
$ craftr -cf examples/csharp/ -b main:csharp.runBundle
CSC v2.6.0.62329 (5429b35d)
Feeds used:
  C:\Users\niklas\.nuget\packages\
  https://api.nuget.org/v3/index.json



Attempting to gather dependency information for package 'Newtonsoft.Json.10.0.3' with respect to project 'C:\Users\niklas\Repositories\craftr-build\craftr\build\debug\csharp\nuget', targeting 'Any,Version=v0.0'
Gathering dependency information took 487,71 ms
Attempting to resolve dependencies for package 'Newtonsoft.Json.10.0.3' with DependencyBehavior 'Lowest'
Resolving dependency information took 0 ms
Resolving actions to install package 'Newtonsoft.Json.10.0.3'
Resolved actions to install package 'Newtonsoft.Json.10.0.3'
Retrieving package 'Newtonsoft.Json 10.0.3' from 'C:\Users\niklas\.nuget\packages\'.
Adding package 'Newtonsoft.Json.10.0.3' to folder 'C:\Users\niklas\Repositories\craftr-build\craftr\build\debug\csharp\nuget'
Added package 'Newtonsoft.Json.10.0.3' to folder 'C:\Users\niklas\Repositories\craftr-build\craftr\build\debug\csharp\nuget'
Successfully installed 'Newtonsoft.Json 10.0.3' to C:\Users\niklas\Repositories\craftr-build\craftr\build\debug\csharp\nuget
Executing nuget actions took 205,12 ms
[Installing] ILMerge.2.14.1208
Feeds used:
  C:\Users\niklas\.nuget\packages\
  https://api.nuget.org/v3/index.json



Attempting to gather dependency information for package 'ILMerge.2.14.1208' with respect to project 'C:\Users\niklas\Repositories\craftr-build\craftr\build\debug\csharp\nuget', targeting 'Any,Version=v0.0'
Gathering dependency information took 875,42 ms
Attempting to resolve dependencies for package 'ILMerge.2.14.1208' with DependencyBehavior 'Lowest'
Resolving dependency information took 0 ms
Resolving actions to install package 'ILMerge.2.14.1208'
Resolved actions to install package 'ILMerge.2.14.1208'
Retrieving package 'ILMerge 2.14.1208' from 'C:\Users\niklas\.nuget\packages\'.
Adding package 'ILMerge.2.14.1208' to folder 'C:\Users\niklas\Repositories\craftr-build\craftr\build\debug\csharp\nuget'
Added package 'ILMerge.2.14.1208' to folder 'C:\Users\niklas\Repositories\craftr-build\craftr\build\debug\csharp\nuget'
Successfully installed 'ILMerge 2.14.1208' to C:\Users\niklas\Repositories\craftr-build\craftr\build\debug\csharp\nuget
Executing nuget actions took 81,58 ms
note: writing "build\debug\build.ninja"
note: Ninja v1.7.2 (C:\Users\niklas\Nextcloud\share\prefs\bin\ninja.EXE)
[2/3] "C:\program files\python36\python.exe" c:\users\niklas\repo...uildslave.py examples.csharp@main:csharp.runBundle^3fe7961f5a2f 0 Hello, world!
{
  "MyArray": [
    "Manual text",
    "2000-05-23T00:00:00"
  ]
}
```
