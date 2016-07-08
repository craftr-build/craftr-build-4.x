# Creates .rst files for every Craftr module in the standard library
# path and updates the list in stl.rst .

import os
import sys
import craftr
import functools
import builtins

Module = craftr.utils.recordclass('Module', 'name parent children pure')


def write_module_rst(module, dirname):
  filename = os.path.join(dirname, module.name + '.rst')
  with open(filename, 'w') as fp:
    print = functools.partial(builtins.print, file=fp)
    header = ':mod:`{0}`'.format(module.name)
    print(header)
    print('=' * len(header))
    print('\n.. automodule:: {0}'.format(module.name))
    if module.children:
      print()
      print('Submodules')
      print('----------')
      print()
      print('.. toctree::')
      print('  :maxdepth: 1')
      print()
      for child in sorted(module.children, key=lambda c: c.name):
        print('  ' + child.name)


def inject_stl_toctree(input, output, dirname, modules):
  modules = [m.name for m in modules.values() if m.parent and not m.parent.pure]
  modules.sort()
  toctree_contents = '\n  '.join(dirname + '/' + m for m in modules)
  with open(input, 'r') as fp:
    data = fp.read()
    data = data.replace('{{stl_toctree}}', toctree_contents)
  with open(output, 'w') as fp:
    fp.write(data)


def main():
  if not os.path.isfile('conf.py'):
    sys.exit('error: must be used from inside the docs directory')
  if not os.path.exists('stl'):
    os.makedirs('stl')

  # Find all extension modules in the craftr LIBDIR.
  modules = {}
  for file in os.listdir(craftr.LIBDIR):
    if not file.startswith('craftr.ext.') or not file.endswith('.py') :
      continue

    module_name = file[:-3]
    module = modules.get(module_name) or Module(module_name, None, [], True)
    module.pure = True
    modules[module_name] = module

    parent_name = module.name.rpartition('.')[0]
    if parent_name:
      parent = modules.get(parent_name) or Module(parent_name, None, [], False)
      modules[parent_name] = parent
      module.parent = parent
      parent.children.append(module)

  # Write them into .rst files.
  for module in modules.values():
    write_module_rst(module, 'stl')

  inject_stl_toctree('stl.rst.template', 'stl.rst', 'stl', modules)


if __name__ == '__main__':
  main()
