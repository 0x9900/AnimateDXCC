#!/usr/bin/env python3
#

import argparse
import logging
import os
import re
import sys

from subprocess import Popen, PIPE

from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)

if os.uname().nodename.endswith('local'):
  SOURCE_DIR = '/Volumes/WDPassport/tmp/dxcc'
  VIDEO_DIR = '/tmp'
  FFMPEG = '/opt/local/bin/ffmpeg'
else:
  SOURCE_DIR = '/var/tmp/dxcc'
  VIDEO_DIR = '/var/www/html'
  FFMPEG = '/usr/bin/ffmpeg'

RE_DATE = re.compile(r'^dxcc.*-\w{2}-(\d+)\..*').match

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
    target = os.path.join(target_dir, f"dxcc-{idx:05d}.png")
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
  input_files = os.path.join(src, 'dxcc-%05d.png')
  in_args = f'-y -framerate 14 -i {input_files}'.split()
  ou_args = '-c:v libx264 -pix_fmt yuv420p -vf scale=800:600'.split()
  cmd = [FFMPEG, *in_args, *ou_args, video_file]
  logging.info("Saving %s video file", video_file)
  logging.info('Writing ffmpeg output in %s', logfile)
  with open(logfile, "w", encoding='ascii') as err:
    err.write(' '.join(cmd))
    err.write('\n\n')
    err.flush()
    with Popen(cmd, shell=False, stdout=PIPE, stderr=err) as proc:
      proc.wait()
      if proc.returncode != 0:
        logging.error('Error generating the video file')

def main():
  parser = argparse.ArgumentParser(description='DXCC trafic animation')
  parser.add_argument('-c', '--continent', required=True, nargs="+",
                      choices=('AF', 'AS', 'EU', 'NA', 'OC', 'SA'))
  parser.add_argument('-H', '--hours', default=120, type=int,
                      help='Number of hours to animate [Default: %(default)s]')
  parser.add_argument('-v', '--video-dir', help='Directory to store the videos')
  opts = parser.parse_args()

  start_date = datetime.utcnow() - timedelta(hours=opts.hours)

  for continent in opts.continent:
    logging.info("Processing: %s, %d hours", continent, opts.hours)
    video_dir = VIDEO_DIR if not opts.video_dir else opts.video_dir
    source_dir = os.path.join(SOURCE_DIR, continent)
    video_file = os.path.join(video_dir, f'dxcc-{continent}.mp4')
    if not os.path.isdir(video_dir):
      logging.error('the video directory "%s" does not exist', video_dir)
      sys.exit(os.EX_IOERR)

    pid = os.getpid()
    try:
      work_dir = os.path.join(source_dir, f"workdir-{pid}")
      os.mkdir(work_dir)

      files = select_files(source_dir, start_date)
      create_links(source_dir, work_dir, files)
      mk_video(work_dir, video_file)
    except KeyboardInterrupt:
      logging.warning("^C pressed")
      sys.exit(os.EX_SOFTWARE)
    finally:
      cleanup(work_dir)

if __name__ == "__main__":
  sys.exit(main())
