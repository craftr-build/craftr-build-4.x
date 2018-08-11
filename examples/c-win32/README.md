### Example: `c-win32`

This example demonstrates how to use the Win32 API and the MSVC resource
compiler.

```
$ craftr -cf examples/c-win32/ -b main:cxx.run
Selected compiler: Microsoft Visual C++ (msvc) 19.12.25835 for x64
note: writing "build\debug\build.ninja"
note: Ninja v1.7.2 (C:\Users\niklas\Nextcloud\share\prefs\bin\ninja.EXE)
[3/4] "C:\program files\python36\python.exe" c:\users\niklas\repo...\ninja\buildslave.py exmaples.c-win32@main:cxx.run^88c78320460f 0 Hello, World!
```
