#! /usr/bin/env python
# vim:fenc=utf-8
#
# Copyright © 2024 fred <github-fred@hidzz.com>
#
# Distributed under terms of the BSD 3-Clause license.

"""
Rename all the DXCC image with the new date format
"""

import pathlib
import re
import sys
from datetime import datetime, timezone

R_DATE = re.compile(r'(dxcc.*-)(\d+)(.png)').match


def parse_date(name):
  if match := R_DATE(name):
    date = datetime.strptime(match.group(2), '%Y%m%d%H%M')
    date = date.replace(tzinfo=timezone.utc)
    return (match.group(1), date, match.group(3))
  return None, None, None


def rename_files(path):
  for filename in pathlib.Path(path).glob('*.png'):
    name, date, ext = parse_date(filename.name)
    if not name:
      continue
    date = date.strftime('%Y%m%dT%H%M%S')
    target = filename.parent.joinpath(f"{name}{date}{ext}")
    if target.exists():
      continue
    filename.rename(target)
    print(f'{filename} -> {target} ')


def main():
  path = sys.argv[1]
  rename_files(path)


if __name__ == "__main__":
  main()
