"""
Simple parser and evaluator for macros.
"""

import nr.parse.strex as strex


class SafeLexer(strex.Lexer):
  """
  Returns a token where the type is #None rather than raising a
  #strex.TokenizationError and progresses the scanner.
  """

  def next(self, *args, **kwargs):
    try:
      return super().next(*args, **kwargs)
    except strex.TokenizationError as exc:
      self.scanner.seek(len(exc.token.value), 'cur')
      return exc.token


class _Node:

  def eval(self, ctx):
    raise NotImplementedError


class _Macro(_Node):

  def __init__(self, name, args):
    self.name = name
    self.args = args

  def __repr__(self):
    return '_Macro(name={!r}, args={!r})'.format(self.name, self.args)

  def eval(self, ctx):
    func = ctx.get_function(self.name)
    args = [x.eval(ctx) for x in self.args]
    return func(args)


class _String(_Node):

  def __init__(self, s):
    assert isinstance(s, str)
    self.s = s

  def __repr__(self):
    return '_String(s={!r})'.format(self.s)

  def eval(self, ctx):
    return self.s


class _Concatenation(_Node):

  def __init__(self, children):
    self.children = children

  def __repr__(self):
    return '_Concatenation(children={!r})'.format(self.children)

  def unpack(self):
    if len(self.children) == 0:
      return _String('')
    elif len(self.children) == 1:
      child = self.children[0]
      if isinstance(child, _Concatenation):
        child = child.unpack()
      return child
    return self

  def eval(self, ctx):
    return ''.join(x.eval(ctx) for x in self.children)


class Parser:

  _rules = [
    strex.Keyword('$$', '$$'),
    strex.Keyword('$(', '$('),
    strex.Keyword(')', ')'),
    strex.Keyword(',', ','),
    strex.Keyword('\\', '\\'),
    strex.Regex('name', '\w+'),
    strex.Regex('text', '[^()$,\\\\]+')
  ]

  def parse(self, s):
    lexer = SafeLexer(strex.Scanner(s), self._rules)
    return self._parse_string(lexer).unpack()

  def _parse_string(self, lexer, inside_expr=False):
    result = _Concatenation([])
    for token in lexer:
      if token.type == '\\':
        token = lexer.next()
        result.children.append(_String(token.string_repr or token.value))
      elif token.type == '$$':
        result.children.append(_String('$'))
      elif token.type == '$(':
        result.children.append(self._parse_macro(lexer))
      elif token.type in (',', ')'):
        if inside_expr:
          break
        else:
          result.children.append(_String(','))
      elif token.type in ('name', 'text'):
        result.children.append(_String(token.string_repr))
      elif token.type is None:  # could not tokenize character
        result.children.append(_String(token.value))
      else:
        raise RuntimeError('unexpected token', token)
    return result

  def _parse_macro(self, lexer):
    assert lexer.token.type == '$('
    name = lexer.next('name').string_repr
    args = []
    lexer.next()
    while lexer.token.type not in (strex.eof, ')'):
      args.append(self._parse_string(lexer, inside_expr=True))
    return _Macro(name, args)


class Context:

  def __init__(self, safe=True):
    self.functions = {}
    self.safe = safe

  def get_function(self, name):
    try:
      return self.functions[name]
    except KeyError:
      if self.safe:
        return lambda *x: ''
      else:
        raise

  def define(self, name, value):
    if isinstance(value, str):
      _value = value
      def value(args):
        return _value
    elif not callable(value):
      raise ValueError('expected string or callable')
    self.functions[name] = value


def parse(s):
  return Parser().parse(s)
