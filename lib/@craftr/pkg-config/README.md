## @craftr/pkg-config

### Example

```python
import cxx from '@craftr/cxx'
import {pkg_config} from '@craftr/pkg-config'

try:
  pkg_config('glew')
except pkg_config.Error:
  # pkg-config may not be available or the library could not be found.
  # Fallback to something else, eg. download the source code and compile.
  pass

# The pkg_config() function declares a new target with the same name.
cxx.binary(
  name = 'main',
  deps = [':glew'],
  # ...
)
```
