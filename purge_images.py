#!/usr/bin/env python3

import argparse
import logging
import os
import re

from datetime import datetime, timedelta

DEFAULT_PATH = '/var/tmp/dxcc'

if os.uname().nodename.endswith('local'):
  DEFAULT_PATH = '/Volumes/WDPassport/tmp/dxcc'
else:
  DEFAULT_PATH = '/var/www/html/DXCC'

logging.basicConfig(format='%(asctime)s %(name)s:%(lineno)d %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S', level=logging.INFO)

def remove_file(filename):
  try:
    os.unlink(filename)
  except IOError as err:
    logging.error(err)


def main():
  parser = argparse.ArgumentParser(description="Purge old dxcc images")
  parser.add_argument('-n', '--dry-run', action="store_true", default=False,
                      help="Do not delete any file (dry run)")
  parser.add_argument('-p', '--path', default=DEFAULT_PATH,
                      help="Root path for dxcc images")
  parser.add_argument('-H', '--hours', default=96, type=int,
                      help='Number of hours to keep')
  opts = parser.parse_args()

  logging.info('Scanning %s', opts.path)
  end_date = datetime.utcnow() - timedelta(hours=opts.hours)
  filematch = re.compile(r'dxcc-\w{2}.*-(\d+).png').match

  for topdir, dirname, files in os.walk(opts.path):
    for name in files:
      if not name.startswith('dxcc-'):
        continue
      mdate = filematch(name)
      if not mdate:
        logging.error('File "%s" matching error', name)
        continue
      sdate = mdate.group(1)
      ddate = datetime.strptime(sdate, '%Y%m%d%H%M')
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
