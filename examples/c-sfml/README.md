## examples/c-sfml

The code for this example is copied from the [SFML OpenGL example][0] with
the minor adjustment of replacing `sf::Keyboard::Enter` with
`sf::Keyboard::Return`.

  [0]: https://github.com/SFML/SFML/tree/master/examples/opengl

### Build & Run

```
$ craftr -cf examples/c-sfml/ -b main:cxx.run
Selected compiler: Microsoft Visual C++ (msvc) 19.12.25835 for x64
Downloading https://www.sfml-dev.org/files/SFML-2.4.2-windows-vc14-64-bit.zip ...
Extracting to build\debug\.source-downloads\SFML-2.4.2-windows-vc14-64-bit ...
note: writing "build\debug\build.ninja"
note: Ninja v1.7.2 (C:\Users\niklas\Nextcloud\share\prefs\bin\ninja.EXE)
[2/3] "C:\program files\python36\python.exe" c:\users\niklas\repo...s\ninja\buildslave.py examples.c-sfml@main:cxx.run^736c1424368a 0
```

![](https://i.imgur.com/uqbI1St.png)
