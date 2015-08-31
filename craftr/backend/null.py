# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

default_outfile = None


def export(fp, session, default_targets):
  session.error("no backend selected, can't export")


def build(target):
  raise RuntimeError("no backend selected, can't build")
