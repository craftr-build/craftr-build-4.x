
import typing as t
import sys


class NamingScheme:

  WIN: 'NamingScheme'
  OSX: 'NamingScheme'
  LINUX: 'NamingScheme'
  CURRENT: 'NamingScheme'

  def __init__(self, data: t.Union[str, t.Dict[str, str]]) -> None:
    if isinstance(data, str):
      data = {k.lower(): v for k, v in (x.partition('=')[::2] for x in data.split(','))}
    self.data = data

  def __str__(self) -> str:
    return 'NamingScheme({!r})'.format(self.to_str())

  def __getitem__(self, key: str) -> str:
    return self.data[key]

  def to_str(self) -> str:
    return ','.join('{}={}'.format(k, v) for k, v in self.data.items())

  def with_defaults(self, scheme: t.Union['NamingScheme', t.Dict[str, str]]) -> 'NamingScheme':
    if not isinstance(scheme, NamingScheme):
      scheme = NamingScheme(scheme)
    return NamingScheme({**scheme.data, **self.data})

  def get(self, key: str, default: t.Optional[str] = None) -> t.Optional[str]:
    return self.data.get(key, default)


NamingScheme.WIN = NamingScheme('e=.exe,lp=,ls=.lib,ld=.dll,o=.obj')
NamingScheme.OSX = NamingScheme('e=,lp=lib,ls=.a,ld=.dylib,o=.o')
NamingScheme.LINUX = NamingScheme('e=,lp=lib,ls=.a,ld=.so,o=.o')
NamingScheme.CURRENT = {'win32': NamingScheme.WIN, 'darwin': NamingScheme.OSX}.get(
    sys.platform, NamingScheme.LINUX)
