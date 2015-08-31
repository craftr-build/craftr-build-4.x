# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.
''' Werkzeug-like proxies. '''


class ProxyBase(object):
    ''' Forwards most of all catchable operations to a proxy object
    which is retreived via `_get_current`. '''

    __slots__ = ()

    def _get_current(self):
        r""" Return the wrapped proxy object. Raise a RuntimeError if
        the Proxy is unbound. """

        raise RuntimeError('proxy is unbound')

    @property
    def __dict__(self):
        try:
            return self._get_current().__dict__
        except RuntimeError:
            raise AttributeError('__dict__')

    def __nonzero__(self):
        try:
            obj = self._get_current()
        except RuntimeError:
            return False
        return bool(obj)

    def __repr__(self):
        try:
            obj = self._get_current()
        except RuntimeError:
            return '<%s unbound>' % self.__class__.__name__
        return repr(obj)

    def __str__(self):
        return str(self._get_current())

    def __unicode__(self):
        return unicode(self._get_current())

    def __bool__(self):
        try:
            return bool(self._get_current())
        except RuntimeError:
            return False

    def __dir__(self):
        try:
            return dir(self._get_current())
        except RuntimeError:
            return []

    def __getattr__(self, name):
        if name == '__members__':
            return dir(self._get_current())
        elif name in type(self).__slots__:
            return super().__getattribute__(name)
        return getattr(self._get_current(), name)

    def __setattr__(self, name, value):
        if name in type(self).__slots__:
            super().__setattr__(name, value)
        else:
            setattr(self._get_current(), name, value)

    def __delattr__(self, name):
        delattr(self._get_current(), name)

    def __getitem__(self, name):
        return self._get_current()[name]

    def __setitem__(self, name, value):
        self._get_current()[name] = value

    def __delitem__(self, name):
        del self._get_current()[name]

    def __getslice__(self, i, j):
        return self._get_current()[i:j]

    def __setslice__(self, i, j, seq):
        self._get_current()[i:j] = seq

    def __delslice__(self, i, j):
        del self._get_current()[i:j]

    __lt__ = lambda x, o: x._get_current() < o
    __le__ = lambda x, o: x._get_current() <= o
    __eq__ = lambda x, o: x._get_current() == o
    __ne__ = lambda x, o: x._get_current() != o
    __gt__ = lambda x, o: x._get_current() > o
    __ge__ = lambda x, o: x._get_current() >= o
    __cmp__ = lambda x, o: cmp(x._get_current(), o)
    __hash__ = lambda x: hash(x._get_current())
    __call__ = lambda x, *a, **kw: x._get_current()(*a, **kw)
    __len__ = lambda x: len(x._get_current())
    __iter__ = lambda x: iter(x._get_current())
    __contains__ = lambda x, i: i in x._get_current()
    __add__ = lambda x, o: x._get_current() + o
    __sub__ = lambda x, o: x._get_current() - o
    __mul__ = lambda x, o: x._get_current() * o
    __floordiv__ = lambda x, o: x._get_current() // o
    __mod__ = lambda x, o: x._get_current() % o
    __divmod__ = lambda x, o: x._get_current().__divmod__(o)
    __pow__ = lambda x, o: x._get_current() ** o
    __lshift__ = lambda x, o: x._get_current() << o
    __rshift__ = lambda x, o: x._get_current() >> o
    __and__ = lambda x, o: x._get_current() & o
    __xor__ = lambda x, o: x._get_current() ^ o
    __or__ = lambda x, o: x._get_current() | o
    __div__ = lambda x, o: x._get_current().__div__(o)
    __truediv__ = lambda x, o: x._get_current().__truediv__(o)
    __neg__ = lambda x: -(x._get_current())
    __pos__ = lambda x: +(x._get_current())
    __abs__ = lambda x: abs(x._get_current())
    __invert__ = lambda x: ~(x._get_current())
    __complex__ = lambda x: complex(x._get_current())
    __int__ = lambda x: int(x._get_current())
    __long__ = lambda x: long(x._get_current())
    __float__ = lambda x: float(x._get_current())
    __oct__ = lambda x: oct(x._get_current())
    __hex__ = lambda x: hex(x._get_current())
    __index__ = lambda x: x._get_current().__index__()
    __coerce__ = lambda x, o: x._get_current().__coerce__(x, o)
    __enter__ = lambda x: x._get_current().__enter__()
    __exit__ = lambda x, *a, **kw: x._get_current().__exit__(*a, **kw)
    __radd__ = lambda x, o: o + x._get_current()
    __rsub__ = lambda x, o: o - x._get_current()
    __rmul__ = lambda x, o: o * x._get_current()
    __rdiv__ = lambda x, o: o / x._get_current()
    __rtruediv__ = lambda x, o: x._get_current().__rtruediv__(o)
    __rfloordiv__ = lambda x, o: o // x._get_current()
    __rmod__ = lambda x, o: o % x._get_current()
    __rdivmod__ = lambda x, o: x._get_current().__rdivmod__(o)


class LocalProxy(ProxyBase):
    ''' Accepts a callable object for getting the current object. '''

    __slots__ = ('__func',)

    def __init__(self, func):
        super(LocalProxy, self).__init__()
        object.__setattr__(self, '_LocalProxy__func', func)

    def _get_current(self):
        return self.__func()


class DelayedBinding(ProxyBase):
    ''' The wrapped object can be bound directly to this object. '''

    __slots__ = ('__obj',)

    def __init__(self):
        super(DelayedBinding, self).__init__()

    def _get_current(self):
        try:
            return self.__obj
        except AttributeError:
            raise RuntimeError('DelayedBinding is yet not bound')

    def _bind(self, obj):
        object.__setattr__(self, '_DelayedBinding__obj', obj)
