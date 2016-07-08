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
'''
Various common utilities used by Craftr and its extension modules.

Transform Functions
-------------------

.. autofunction:: flatten
.. autofunction:: uniquify

Recordclass
-----------

.. autoclass:: recordclass_base
  :members:
  :undoc-members:
.. autofunction:: recordclass

Environment Variables
---------------------

.. autofunction:: append_path
.. autofunction:: prepend_path
.. autofunction:: override_environ

:mod:`craftr.utils.regex` Module
---------------------------------

.. automodule:: craftr.utils.regex
'''

from . import regex
from .env import append_path, prepend_path, override_environ
from .recordclass import recordclass_base, recordclass
from .transform import flatten, uniquify

# backwards compatibility < 1.11.
from ..shell import find_program, test_program
from ..path import tempfile
from .regex import search_get_groups as gre_search
unique = uniquify
slotobject = recordclass
