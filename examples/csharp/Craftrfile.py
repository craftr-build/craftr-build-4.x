
import craftr from 'craftr'
import csharp from 'craftr/lang/csharp'

# Download Json.NET using NuGet (requires the 'nuget' command)/
csharp.prebuilt(name = 'Json.NET', package = 'Newtonsoft.Json:10.0.3')

# Build a DLL assembly from source.
csharp.build(
  name = 'lib',
  srcs = craftr.glob('src/lib/*.cs'),
  type = 'library'
)

# Build an executable assembly from source and merge them into a single
# assembly using ILMerge.
csharp.build(
  name = 'main',
  deps = [':Json.NET', ':lib'],
  srcs = craftr.glob('src/*.cs'),
  type = 'exe',
  merge_assemblies = True
)

csharp.run(':main')
