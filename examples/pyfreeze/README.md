## examples/pyfreeze

This example demonstrates building a frozen Python application.

### Build & Run

```
$ cd examples/pyfreeze
$ craftr -t python.freeze -- -o frozen_src hello.py
[...]
$ craftr -cb main:cxx.run
Selected compiler: Microsoft Visual C++ (msvc) 19.12.25835 for x64
note: writing "build\debug\build.ninja"
note: Ninja v1.7.2 (C:\Users\niklas\Nextcloud\share\prefs\bin\ninja.EXE)
[9/166] "C:\program files\python36\python.exe" c:\users\niklas\re...\buildslave.py examples.pyfreeze@main:cxx.compileC^d37d5413797d 1
c:\program files\python36\include\pyconfig.h(279): warning C4005: 'MS_COREDLL': macro redefinition
c:\program files\python36\include\pyconfig.h(279): note: command-line arguments:  see previous definition of 'MS_COREDLL'
[10/166] "C:\program files\python36\python.exe" c:\users\niklas\r...\buildslave.py examples.pyfreeze@main:cxx.compileC^d37d5413797d 0
c:\program files\python36\include\pyconfig.h(279): warning C4005: 'MS_COREDLL': macro redefinition
c:\program files\python36\include\pyconfig.h(279): note: command-line arguments:  see previous definition of 'MS_COREDLL'
[161/166] "C:\program files\python36\python.exe" c:\users\niklas\...uildslave.py examples.pyfreeze@main:cxx.compileC^d37d5413797d 162
c:\program files\python36\include\pyconfig.h(279): warning C4005: 'MS_COREDLL': macro redefinition
c:\program files\python36\include\pyconfig.h(279): note: command-line arguments:  see previous definition of 'MS_COREDLL'
[165/166] "C:\program files\python36\python.exe" c:\users\niklas\...ninja\buildslave.py examples.pyfreeze@main:cxx.run^2c530df9de2a 0
Hello, world!
```
