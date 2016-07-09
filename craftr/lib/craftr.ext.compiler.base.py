# Copyright (C) 2016  Niklas Rosenstein
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
"""
Provides a convenient base class for Craftr compilers.

.. autoclass:: BaseCompiler
  :members:
  :undoc-members:
"""

__all__ = ['BaseCompiler']

from craftr import Framework, Target, TargetBuilder
import copy


class BaseCompiler(object):
  """
  This is a convenient base class for implementing compilers.

  :params kwargs: Arbitrary keyword arguments from which a
    :class:`Framework` will be created and assigned to the
    :attr:`settings` member

  .. code:: python

    from craftr.ext.compiler.base import BaseCompiler
    from craftr.ext.compiler import gen_output

    class SimpleGCC(BaseCompiler):
      def compile(self, sources, frameworks, **kwargs):
        builder = self.builder(sources, frameworks, kwargs)
        include = builder.merge('include')
        defines = builder.merge('defines')

        outputs = gen_output(builder.input, suffix='.obj')
        command = ['gcc', '-c', '$in', '-c', '-o', '$out']
        command += ['-I' + x for x in include]
        command += ['-D' + x for x in defines]
        return builder.create_target(command, outputs, foreach=True)

  In the above example, the :class:`TargetBuilder` returned by
  :meth:`builder` has the following framework option resolution
  order (first is first):

  1. The ``**kwargs`` passed to ``compile()``
  2. The :class:`Framework` objects in ``frameworks``
  3. The :attr:`settings` framework of ``SimpleGCC``
  4. If the ``sources`` list contained an :class:`Target` s,
     the :class:`Framework` s of these targets will be considered

  .. attribute:: settings

    A :class:`Framework` that will be included in the
    :class:`TargetBuilder` returned by the :meth:`builder`
    method.
  """

  def __init__(self, **kwargs):
    if not hasattr(self, 'name'):
      raise TypeError('{0}.name is not set'.format(type(self).__name__))
    super().__init__()
    self.settings = Framework(type(self).__name__, **kwargs)
    self.frameworks = [self.settings]
    self.hooks = {}

  def builder(self, inputs, frameworks, kwargs, **_add_kwargs):
    """
    Create a :class:`TargetBuilder` that includes the :attr:`settings`
    :class:`Framework` of this :class:`BaseCompiler`.
    """

    frameworks = list(frameworks) + self.frameworks
    builder = TargetBuilder(inputs, frameworks, kwargs, stacklevel=2, **_add_kwargs)
    if builder.caller in self.hooks:
      for handler in self.hooks[builder.caller]:
        handler(builder)
    return builder

  def fork(self, **kwargs):
    """
    Create a fork of the compiler that overrides/add parameters in
    the :attr:`settings` with the specified ``**kwargs``.
    """

    obj = copy.copy(self)
    # Create a new Settings framework for the compiler.
    obj.settings = Framework(type(self).__name__, **kwargs)
    # Copy the frameworks of the parent.
    obj.frameworks = copy.copy(self.frameworks)
    obj.frameworks.insert(0, obj.settings)
    obj.hooks = copy.copy(self.hooks)
    return obj

  def register_hook(self, call, handler):
    """
    Registers a handler for the method call that will be invoked
    when a :class:`TargetBuilder` was created. It will allow the
    "handler" to set up default and additional settings.
    """

    self.hooks.setdefault(call, []).append(handler)



