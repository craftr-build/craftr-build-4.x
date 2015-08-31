# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

default_outfile = 'build.json'


def export(fp, session, default_targets):
  session.error("JSON backend is not implemented.")


def build(target):
  raise RuntimeError("JSON backend can't build")
