#!/usr/bin/env python3
#
# BSD 3-Clause License
#
# Copyright (c) 2022-2023 Fred W6BSD
# All rights reserved.
#
#
#
import argparse
import atexit
import logging
import os
import re
import shutil
import sys

from subprocess import Popen, PIPE
from datetime import datetime, timedelta, timezone

logging.basicConfig(format='%(asctime)s %(name)s:%(lineno)d %(levelname)s - %(message)s',
                    datefmt='%x %X', level=logging.INFO)

if os.uname().nodename.endswith('local'):
  SOURCE_DIR = '/Volumes/WDPassport/tmp/DXCC'
  VIDEO_DIR = '/tmp'
else:
  SOURCE_DIR = '/var/www/html/DXCC'
  VIDEO_DIR = '/var/www/html'

FFMPEG = shutil.which('ffmpeg')

RE_DATE = re.compile(r'^dxcc.*-\w+-(\d+)\..*').match

def parse_date(name):
  match = RE_DATE(name)
  if not match:
    return None
  return datetime.strptime(match.group(1), '%Y%m%d%H%M')

def select_files(source_dir, start_date=False):
  file_list = []
  for name in os.listdir(source_dir):
    if not name.startswith('dxcc-'):
      continue
    if parse_date(name) > start_date:
      file_list.append(name)
  file_list.sort()
  logging.info('%d files selected for animation', len(file_list))
  return file_list

def create_links(source_dir, target_dir, file_list):
  logging.info('Creating workspace %s', target_dir)
  if not file_list:
    return
  for idx, name in enumerate(file_list):
    target = os.path.join(target_dir, f"tmpdxcc-{idx:05d}.png")
    source = os.path.join(source_dir, name)
    os.link(source, target)
    logging.debug('Target file: %s', target)

def cleanup(directory):
  for name in os.listdir(directory):
    os.unlink(os.path.join(directory, name))
  os.rmdir(directory)
  logging.info('Working directory "%s" removed', directory)

def mk_video(src, video_file):
  logfile = '/tmp/newanim.log'
  tmp_file = f"{video_file}-{os.getpid()}.mp4"
  input_files = os.path.join(src, 'tmpdxcc-%05d.png')
  in_args = f'-y -framerate 10 -i {input_files}'.split()
  ou_args = '-c:v libx264 -pix_fmt yuv420p -vf scale=800:600'.split()
  cmd = [FFMPEG, *in_args, *ou_args, tmp_file]
  logging.info('Writing ffmpeg output in %s', logfile)
  logging.info("Saving %s video file", tmp_file)
  with open(logfile, "a", encoding='ascii') as err:
    err.write(' '.join(cmd))
    err.write('\n\n')
    err.flush()
    with Popen(cmd, shell=False, stdout=PIPE, stderr=err) as proc:
      proc.wait()
    if proc.returncode != 0:
      logging.error('Error generating the video file')
      return
    logging.info('mv %s %s', tmp_file, video_file)
    os.rename(tmp_file, video_file)


def animate(start_date, source_dir, video_file):
  pid = os.getpid()
  try:
    work_dir = os.path.join(source_dir, f"workdir-{pid}")
    os.mkdir(work_dir)
    atexit.register(cleanup, work_dir)

    files = select_files(source_dir, start_date)
    create_links(source_dir, work_dir, files)
    mk_video(work_dir, video_file)
  except KeyboardInterrupt:
    logging.warning("^C pressed")
    sys.exit(os.EX_SOFTWARE)
  finally:
    atexit.unregister(cleanup)
    cleanup(work_dir)


def main():
  parser = argparse.ArgumentParser(description='DXCC trafic animation')
  parser.add_argument('-c', '--continent', nargs="+",
                      choices=('AF', 'AS', 'EU', 'NA', 'OC', 'SA'))
  parser.add_argument('-C', '--cqzone', type=int, nargs="+",
                      help="CQ Zone numbers")
  parser.add_argument('-I', '--ituzone', type=int, nargs="+",
                      help="ITU Zone numbers")
  parser.add_argument('-H', '--hours', default=120, type=int,
                      help='Number of hours to animate [Default: %(default)s]')
  parser.add_argument('-v', '--video-dir', help='Directory to store the videos')
  opts = parser.parse_args()

  video_dir = VIDEO_DIR if not opts.video_dir else opts.video_dir
  if not os.path.isdir(video_dir):
    logging.error('the video directory "%s" does not exist', video_dir)
    sys.exit(os.EX_IOERR)

  start_date = datetime.now(timezone.utc) - timedelta(hours=opts.hours)

  for zone_type in ("continent", "cqzone", "ituzone"):
    zones = getattr(opts, zone_type)
    if not zones:
      continue
    for zone_name in zones:
      zone_name = str(zone_name)
      logging.info("Processing: %s %s, %d hours", zone_type, zone_name, opts.hours)
      source_dir = os.path.join(SOURCE_DIR, zone_type, zone_name)
      video_file = os.path.join(video_dir, f'dxcc-{zone_name}.mp4')
      animate(start_date, source_dir, video_file)


if __name__ == "__main__":
  sys.exit(main())
