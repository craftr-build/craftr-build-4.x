## examples/haskell

This example demonstrates how to compile a simple Haskell program with Craftr.

### Build & Run

```
$ craftr -cf examples/haskell/ -b main:haskell.run
note: writing "build\debug\build.ninja"
note: Ninja v1.7.2 (build\debug\ninja.exe)
[1/2] "C:\program files\python36\python.exe" c:\users\niklas\repo...uildslave.py examples.haskell@main:haskell.compile^8d0347dcd780 0
[1 of 1] Compiling Main             ( C:\Users\niklas\Repositories\craftr-build\craftr\examples\haskell\src\Main.hs, C:\Users\niklas\Repositories\craftr-build\craftr\examples\haskell\src\Main.o )
Linking C:\Users\niklas\Repositories\craftr-build\craftr\build\debug\examples.haskell\main1.0.0.exe ...
[1/2] "C:\program files\python36\python.exe" c:\users\niklas\repo...ja\buildslave.py examples.haskell@main:haskell.run^705041bcbd4c 0
Hello, world!
```
