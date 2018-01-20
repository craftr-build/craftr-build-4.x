# Sample Craftr build script for C# projects.

import craftr from 'craftr'
import csharp from '@craftr/csharp'

csharp.prebuilt(
  name = 'Json.NET',
  packages = [
    'Newtonsoft.Json:10.0.3'  # Automatically installed with NuGet
  ]
)

csharp.build(
  name = 'lib',
  srcs = craftr.glob('src/lib/*.cs'),
  type = 'library'
)

csharp.build(
  name = 'main',
  deps = [':Json.NET', ':lib'],
  srcs = craftr.glob('src/*.cs'),
  type = 'exe',
  merge_assemblies = True  # Will combine assemblies using ILMerge/ILRepack
)

csharp.run(':main')
