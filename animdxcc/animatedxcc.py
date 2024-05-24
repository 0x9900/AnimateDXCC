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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Iterator, Optional

RE_DATE = re.compile(r'^dxcc.*-\w+-(\d+)\..*').match


def counter(start: int = 1) -> Iterator[str]:
  cnt = start
  while True:
    yield f'{cnt:06}'
    cnt += 1


def parse_date(name: str) -> Optional[datetime]:
  match = RE_DATE(name)
  if not match:
    return None
  date = datetime.strptime(match.group(1), '%Y%m%d%H%M')
  return date.replace(tzinfo=timezone.utc)


def select_files(source_dir: Path, workdir: Path,  start_date: datetime):
  count = counter()
  for fullname in sorted(source_dir.glob('dxcc-*.png')):
    if not fullname.name.startswith('dxcc-'):
      continue
    file_date = parse_date(fullname.name)
    if file_date and file_date > start_date:
      target = workdir.joinpath(f'dxcc-{next(count)}.png')
      target.hardlink_to(fullname)
      logging.info('Selecting file %s', fullname.name)


def cleanup(workdir: Path) -> None:
  if not workdir.exists():
    return
  for name in workdir.glob('*'):
    name.unlink()
  workdir.rmdir()
  logging.info('Working directory "%s" removed', workdir)


def mk_workdir(source: Path) -> Path:
  workdir = source.joinpath('_workdir')
  atexit.register(cleanup, workdir)
  workdir.mkdir()
  return workdir


def mk_video(workdir: Path, video_file: Path) -> None:
  ffmpeg = shutil.which('ffmpeg')
  if not ffmpeg:
    raise FileNotFoundError('ffmpeg not found')

  logfile = Path('/tmp/newanim.log')
  tmp_file = workdir.joinpath(f'video-{os.getpid()}.mp4')
  pngfiles = workdir.joinpath('dxcc-*.png')

  in_args: list[str] = f'-y -framerate 10 -pattern_type glob -i {pngfiles}'.split()
  ou_args: list[str] = '-c:v libx264 -pix_fmt yuv420p -vf scale=800:600'.split()
  cmd = [ffmpeg, *in_args, *ou_args, str(tmp_file)]
  txt_cmd = ' '.join(cmd)

  logging.info('Writing ffmpeg output in %s', logfile)
  logging.info("Saving %s video file", tmp_file)
  with logfile.open("a", encoding='ascii') as err:
    err.write(txt_cmd)
    err.write('\n\n')
    err.flush()
    with Popen(cmd, shell=False, stdout=PIPE, stderr=err) as proc:
      proc.wait()
    if proc.returncode != 0:
      logging.error('Error generating the video file')
      return
    logging.info('mv %s %s', tmp_file, video_file)
    tmp_file.rename(video_file)


def type_path(arg: str) -> Path:
  path = Path(arg)
  if not path.is_dir():
    raise argparse.ArgumentTypeError(f'Error reading the directory {arg}')
  return path


def main():
  log_file = None if os.isatty(sys.stdout.fileno()) else '/tmp/animdxcc.log'
  logging.basicConfig(
    format='%(asctime)s %(name)s:%(lineno)3d %(levelname)s - %(message)s', datefmt='%x %X',
    level=logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO')),
    filename=log_file
  )

  parser = argparse.ArgumentParser(description='DXCC trafic animation')
  parser.add_argument('-c', '--continent', nargs="+",
                      choices=('AF', 'AS', 'EU', 'NA', 'OC', 'SA'))
  parser.add_argument('-C', '--cqzone', type=int, nargs="+",
                      help="CQ Zone numbers")
  parser.add_argument('-I', '--ituzone', type=int, nargs="+",
                      help="ITU Zone numbers")
  parser.add_argument('-H', '--hours', default=120, type=int,
                      help='Number of hours to animate [Default: %(default)s]')
  parser.add_argument('-s', '--source', default='/var/tmp/DXCC', type=type_path,
                      help='Directory where the images are located')
  parser.add_argument('-v', '--video-dir', default='/tmp', type=type_path,
                      help='Directory to store the videos')
  opts = parser.parse_args()

  if not opts.video_dir.is_dir():
    logging.error('the video directory "%s" does not exist', opts.video_dir)
    raise SystemExit(opts.video_dir)

  start_date = datetime.now(timezone.utc) - timedelta(hours=opts.hours)

  for zone_type in ("continent", "cqzone", "ituzone"):
    zones = getattr(opts, zone_type)
    if not zones:
      continue
    for zone_name in zones:
      zone_name = str(zone_name)
      logging.info("Processing: %s %s, %d hours", zone_type, zone_name, opts.hours)
      source_dir = opts.source.joinpath(zone_type, zone_name)
      video_file = opts.video_dir.joinpath(f'dxcc-{zone_name}.mp4')
      try:
        work_dir = mk_workdir(source_dir)
        select_files(source_dir, work_dir, start_date)
      except IOError as err:
        logging.error(err)
        raise SystemExit('Error') from None
      mk_video(work_dir, video_file)
      cleanup(work_dir)


if __name__ == "__main__":
  sys.exit(main())
