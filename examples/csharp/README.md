### Example: `csharp`

This example demonstrates how to compile a C# application with dependencies
and bundling them into a single executable.

```
$ craftr -cb --project examples/csharp main:csharp.runBundle
CSC v2.8.3.63029 (e9a3a6c0)

======= BUILD

[examples.csharp@main/csharp.compile#1] SKIP
[examples.csharp@main/csharp.bundle#1]
  $ 'C:\Users\niklas\Desktop\craftr4\build\debug\craftr/lang/csharp\csharp\nuget\ILMerge.2.14.1208\tools\ILMerge.exe' '/out:C:\Users\niklas\Desktop\craftr4\build\debug\examples.csharp\main\main-1.0-0-bundle.exe' 'C:\Users\niklas\Desktop\craftr4\build\debug\examples.csharp\main\main-1.0-0.exe' 'C:\Users\niklas\Desktop\craftr4\build\debug\craftr/lang/csharp\csharp\nuget\Newtonsoft.Json.10.0.3\lib\net45\Newtonsoft.Json.dll'
[examples.csharp@main/csharp.runBundle#1] C:\Users\niklas\Desktop\craftr4\build\debug\examples.csharp\main\main-1.0-0-bundle.exe
  $ 'C:\Users\niklas\Desktop\craftr4\build\debug\examples.csharp\main\main-1.0-0-bundle.exe'
Hello, world!
{
  "MyArray": [
    "Manual text",
    "2000-05-23T00:00:00"
  ]
}
```
