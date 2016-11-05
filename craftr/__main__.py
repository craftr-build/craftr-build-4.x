# The Craftr build system
# Copyright (C) 2016  Niklas Rosenstein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import craftr.core.build as build
import craftr.utils.shell as shell
import sys

def main():
  graph = build.Graph()
  target = build.Target('compile_doe_shit', [['gcc', '$in', '-o', '$out'], ['echo', 'foo']], ['main.c', 'tool.c'], ['main.exe'])
  graph.add_target(target)
  platform = build.WindowsPlatformHelper()
  context = build.ExportContext(ninja_version='1.7.2')
  writer = build.NinjaWriter(sys.stdout)
  graph.export(writer, context, platform)

if __name__ == '__main__':
  main()
