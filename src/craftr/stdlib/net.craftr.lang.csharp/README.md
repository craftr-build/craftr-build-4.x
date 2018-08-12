### Module: `craftr/lang/csharp`

This Craftr module allows you to compile and bundle C# applications with
the MS Visual Compiler as well as Mono.

#### To do

* Determine default `netversion` in `CscInfo` class (currently defaults to `net45`)
* Add output files to `csharp.outModules` / `csharp.outReferences`
* Is there an option/envvar to make the .NET runtime search for assemblies
  in other directories (like the Java classpath)? That would be interesting
  for the `csharp.run` operator.
