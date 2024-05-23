#!/usr/bin/env python3

import argparse
import logging
import os
import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone

DEFAULT_KEEP = 7 * 24           # Keep images for 7 days.
DEFAULT_PATH = '/var/tmp/dxcc'


def purge_files(src_path, hours, dry_run=False):
  start_date = datetime.now(timezone.utc) - timedelta(hours=hours)
  filematch = re.compile(r'dxcc-\w{2}.*-(\d+).png').match
  for path, _, files in src_path.walk():
    for name in files:
      if not (fmatch := filematch(name)):
        continue
      date = datetime.strptime(fmatch.group(1), '%Y%m%d%H%M')
      date = date.replace(tzinfo=timezone.utc)
      if date >= start_date:
        logging.debug('Keep file: %s', path)
        continue
      fullname = path.joinpath(name)
      if dry_run:
        logging.info('File "%s" will be purged', fullname)
        continue
      logging.info('Purge file "%s"',  fullname)
      fullname.unlink()


def type_path(arg):
  path = pathlib.Path(arg)
  if not path.is_dir():
    raise argparse.ArgumentTypeError(f'Error reading the directory "{arg}"')
  return path


def main():
  log_file = None if os.isatty(sys.stdout.fileno()) else '/tmp/purge_images.log'
  logging.basicConfig(
    format='%(asctime)s %(name)s:%(lineno)3d %(levelname)s - %(message)s', datefmt='%x %X',
    level=logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO')),
    filename=log_file
  )
  parser = argparse.ArgumentParser(description="Purge old dxcc images")
  parser.add_argument('-n', '--dry-run', action="store_true", default=False,
                      help="Do not delete any file (dry run)")
  parser.add_argument('-s', '--source', default=DEFAULT_PATH, type=type_path,
                      help="Root path for dxcc images [default: %(default)s]")
  parser.add_argument('-H', '--hours', default=DEFAULT_KEEP, type=int,
                      help='Number of hours to keep [default: %(default)d hours]')
  opts = parser.parse_args()

  logging.info('Scanning %s', opts.source)
  purge_files(opts.source, opts.hours, opts.dry_run)


if __name__ == "__main__":
  main()
