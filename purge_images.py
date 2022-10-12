#!/usr/bin/env python3

import argparse
import logging
import os
import re

from datetime import datetime, timedelta

DEFAULT_PATH = '/var/tmp/dxcc'

def select_files(path, end_date):
  match = re.compile(r'dxcc-\w{2}.*-(\d+).png')
  selected = []
  files = sorted(os.listdir(path))
  for file in files:
    mdate = match.match(file)
    if not mdate:
      logging.error('File "%s" matching error', file)
      continue
    sdate = mdate.group(1)
    ddate = datetime.strptime(sdate, '%Y%m%d%H%M')
    if ddate < end_date:
      selected.append(os.path.join(path, file))

  return selected

def main():
  continents = ("AF", "AS", "EU", "NA", "OC", "SA")
  parser = argparse.ArgumentParser(description="Purge old dxcc images")
  parser.add_argument('-n', '--dry-run', action="store_true", default=False,
                      help="Do not delete any file (dry run)")
  parser.add_argument('-p', '--path', default=DEFAULT_PATH,
                      help="Root path for dxcc images")
  parser.add_argument('-H', '--hours', default=96, type=int,
                      help='Number of hours to keep')
  parser.add_argument('args', choices=continents, nargs="+",
                      help='Purge files for the specified continent')
  opts = parser.parse_args()

  for continent in opts.args:
    path = os.path.join(opts.path, continent)
    if not os.path.exists(path):
      logging.warning("Path %s not found", path)
      continue

    logging.info('Scanning %s', path)
    end_date = datetime.utcnow() - timedelta(hours=opts.hours)
    to_delete = select_files(path, end_date)
    for file in to_delete:
      if not opts.dry_run:
        logger.info('Delete: "%s"', file)
        os.unlink(file)
      else:
        logging.info('"%s" should be deleted', file)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger(__name__)
  main()
