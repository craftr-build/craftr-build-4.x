# SDL2 (`craftr.lib.sdl2`)

-- SDL2 support for C/C++.

__Note__:

This package is automatically compiled from source on Windows.

__Example__:

```python
cxx = load('craftr.lang.cxx')
sdl2 = load('craftr.lib.sdl2')

main = cxx.executable(
  output = 'main',
  inputs = cxx.compile_c(
    sources = glob(['*.c']),
    frameworks = [sdl2.SDL2main]
  )
)

run = runtarget(main, cwd = project_dir)
```

__Useful links__:

- https://wiki.libsdl.org/FAQUsingSDL
