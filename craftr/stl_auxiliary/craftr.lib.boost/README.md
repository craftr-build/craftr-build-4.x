# Prebuilt Boost

This package is incomplete.

It provides support for using prebuilt boost libraries.

## Todolist

- [ ] Test on platforms other than Windows

## Example

You need to specify the path to the boost installation and also the
architecture that the prebuilt binaries were compiled for. Instead of
passing these options via the command-line each and every time, it is
convenient to create a Craftr configuration file.

```
# .craftrconfig
[craftr.lib.boost]
  path = D:\lib\boost_1_58_0
  arch = lib64-msvc-12.0
```
