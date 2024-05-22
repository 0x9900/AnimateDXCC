#!/usr/bin/env python3

import argparse
import logging
import os
import re
import sys

from datetime import datetime, timedelta, timezone

DEFAULT_KEEP = 7 * 24           # Keep images for 7 days.
DEFAULT_PATH = '/var/tmp/dxcc'

def remove_file(filename):
  try:
    os.unlink(filename)
  except IOError as err:
    logging.error(err)


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
  parser.add_argument('-p', '--path', default=DEFAULT_PATH,
                      help="Root path for dxcc images [default: %(default)s]")
  parser.add_argument('-H', '--hours', default=DEFAULT_KEEP, type=int,
                      help='Number of hours to keep [default: %(default)d hours]')
  opts = parser.parse_args()

  logging.info('Scanning %s', opts.path)
  end_date = datetime.now(timezone.utc) - timedelta(hours=opts.hours)
  filematch = re.compile(r'dxcc-\w{2}.*-(\d+).png').match

  for topdir, _, files in os.walk(opts.path):
    for name in files:
      if not name.startswith('dxcc-'):
        continue
      mdate = filematch(name)
      if not mdate:
        logging.error('File "%s" matching error', name)
        continue
      sdate = mdate.group(1)
      ddate = datetime.strptime(sdate, '%Y%m%d%H%M')
      ddate = ddate.replace(tzinfo=timezone.utc)
      if ddate >= end_date:
        continue

      fullpath = os.path.join(topdir, name)
      if opts.dry_run:
        logging.info('To delete: "%s"', fullpath)
        continue

      logging.info('Delete: "%s"', fullpath)
      remove_file(fullpath)


if __name__ == "__main__":
  main()
