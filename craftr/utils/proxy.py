# Copyright (C) 2015 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

def resolve_proxy(proxy):
  ''' Given a `Proxy` instance, resolves the proxy and returns the
  internal object. If no proxy object is specified, the object is
  returned unchanged. '''

  if isinstance(proxy, Proxy):
    return proxy._Proxy__target()
  else:
    return proxy


class Proxy(object):
  ''' An instance of this class represents another Python object as
  a proxy and attempts to behave exactly the same as the proxy source
  object. The source object is retrieved by a function. '''

  __slots__ = ('_Proxy__target',)

  def __init__(self, target):
    if not callable(target):
      raise TypeError('target must be callable')
    super(Proxy, self).__init__()
    self.__target = target

  @property
  def __dict__(self):
    try:
      return self.__target().__dict__
    except RuntimeError:
      raise AttributeError('__dict__')

  def __nonzero__(self):
    try:
      obj = self.__target()
    except RuntimeError:
      return False
    return bool(obj)

  def __repr__(self):
    try:
      obj = self.__target()
    except RuntimeError:
      return '<%s unbound>' % self.__class__.__name__
    return repr(obj)

  def __str__(self):
    return str(self.__target())

  def __unicode__(self):
    return unicode(self.__target())

  def __bool__(self):
    try:
      return bool(self.__target())
    except RuntimeError:
      return False

  def __dir__(self):
    try:
      return dir(self.__target())
    except RuntimeError:
      return []

  def __getattr__(self, name):
    if name in type(self).__slots__:
      return super().__getattribute__(name)
    return getattr(self.__target(), name)

  def __setattr__(self, name, value):
    if name in type(self).__slots__:
      super().__setattr__(name, value)
    else:
      setattr(self.__target(), name, value)

  def __delattr__(self, name):
    delattr(self.__target(), name)

  def __getitem__(self, name):
    return self.__target()[name]

  def __setitem__(self, name, value):
    self.__target()[name] = value

  def __delitem__(self, name):
    del self.__target()[name]

  def __getslice__(self, i, j):
    return self.__target()[i:j]

  def __setslice__(self, i, j, seq):
    self.__target()[i:j] = seq

  def __delslice__(self, i, j):
    del self.__target()[i:j]

  __lt__ = lambda x, o: x.__target() < o
  __le__ = lambda x, o: x.__target() <= o
  __eq__ = lambda x, o: x.__target() == o
  __ne__ = lambda x, o: x.__target() != o
  __gt__ = lambda x, o: x.__target() > o
  __ge__ = lambda x, o: x.__target() >= o
  __cmp__ = lambda x, o: cmp(x.__target(), o)
  __hash__ = lambda x: hash(x.__target())
  __call__ = lambda x, *a, **kw: x.__target()(*a, **kw)
  __len__ = lambda x: len(x.__target())
  __iter__ = lambda x: iter(x.__target())
  __contains__ = lambda x, i: i in x.__target()
  __add__ = lambda x, o: x.__target() + o
  __sub__ = lambda x, o: x.__target() - o
  __mul__ = lambda x, o: x.__target() * o
  __floordiv__ = lambda x, o: x.__target() // o
  __mod__ = lambda x, o: x.__target() % o
  __divmod__ = lambda x, o: x.__target().__divmod__(o)
  __pow__ = lambda x, o: x.__target() ** o
  __lshift__ = lambda x, o: x.__target() << o
  __rshift__ = lambda x, o: x.__target() >> o
  __and__ = lambda x, o: x.__target() & o
  __xor__ = lambda x, o: x.__target() ^ o
  __or__ = lambda x, o: x.__target() | o
  __div__ = lambda x, o: x.__target().__div__(o)
  __truediv__ = lambda x, o: x.__target().__truediv__(o)
  __neg__ = lambda x: -(x.__target())
  __pos__ = lambda x: +(x.__target())
  __abs__ = lambda x: abs(x.__target())
  __invert__ = lambda x: ~(x.__target())
  __complex__ = lambda x: complex(x.__target())
  __int__ = lambda x: int(x.__target())
  __long__ = lambda x: long(x.__target())
  __float__ = lambda x: float(x.__target())
  __oct__ = lambda x: oct(x.__target())
  __hex__ = lambda x: hex(x.__target())
  __index__ = lambda x: x.__target().__index__()
  __coerce__ = lambda x, o: x.__target().__coerce__(x, o)
  __enter__ = lambda x: x.__target().__enter__()
  __exit__ = lambda x, *a, **kw: x.__target().__exit__(*a, **kw)
  __radd__ = lambda x, o: o + x.__target()
  __rsub__ = lambda x, o: o - x.__target()
  __rmul__ = lambda x, o: o * x.__target()
  __rdiv__ = lambda x, o: o / x.__target()
  __rtruediv__ = lambda x, o: x.__target().__rtruediv__(o)
  __rfloordiv__ = lambda x, o: o // x.__target()
  __rmod__ = lambda x, o: o % x.__target()
  __rdivmod__ = lambda x, o: x.__target().__rdivmod__(o)
