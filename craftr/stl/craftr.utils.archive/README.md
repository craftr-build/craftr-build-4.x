# Archive Utilities (`craftr.utils.archive`)

Generate archives from Ninja tasks.

## Example

```python
myapp = # ...

Archive = load('craftr.utils.archive')
git = load('craftr.utils.git').Git(project_dir)

dist = (
  Archive(
    prefix = 'myapp-{}'.format(git.describe())
  )
  .add(['static', 'resources', 'LICENSE.txt', 'README.md'])
  .add(myapp.outputs)
  .astarget(explicit=False)
)
```
