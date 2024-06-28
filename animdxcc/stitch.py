#!/usr/bin/env python
# This is just an experiment.

import argparse
import atexit
import logging
import os
import re
import sys
from datetime import date, datetime, timedelta
from importlib.resources import files
from itertools import product
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OFFSET = 40
FOOTER = 40
COLUMNS = 4
ROWS = 6
OUTPUT_SIZE = (360, 240)

RESAMPLING = Image.Resampling.LANCZOS


def mk_overlay(image, day):
  fontpath = files('animdxcc')
  font_t_path = fontpath.joinpath('JetBrainsMono-Bold.ttf')
  font_f_path = fontpath.joinpath('JetBrainsMono-MediumItalic.ttf')

  font_t = ImageFont.truetype(font_t_path.open('rb'), 18)
  font_f = ImageFont.truetype(font_f_path.open('rb'), 12)

  title = f'Hourly overview of HF propagation for {day}'
  author = f'(c){day.year} W6BSD https://bsdworld.org/'

  width, height = image.size
  overlay = Image.new('RGBA', (width, height))
  textbox = ImageDraw.Draw(overlay)
  wpos = textbox.textlength(title, font=font_t)
  textbox.text(((width - wpos)/2, 10), title, fill='#000044', font=font_t)
  textbox.text((10,  (height - FOOTER/1.5)), author, fill='#000000', font=font_f)
  return overlay


def stitch_thumbnails(thumbnails, cols, rows, output_size, day):
  total_width = cols * output_size[0]
  total_height = rows * output_size[1] + OFFSET + FOOTER

  canvas = Image.new('RGBA', (total_width, total_height), color='#ffffff')

  for i, j in product(range(rows), range(cols)):
    index = i * cols + j
    if index >= len(thumbnails):
      break
    thumbnail = Image.open(thumbnails[index])
    thumbnail = thumbnail.resize(output_size, RESAMPLING)
    canvas.paste(thumbnail, (j * output_size[0], i * output_size[1] + OFFSET))

  canvas = Image.alpha_composite(canvas, mk_overlay(canvas, day))
  canvas = canvas.convert("RGB")
  return canvas


def add_margin(image, left=40, top=50, color='#ffffff'):
  width, height = image.size
  new_width = width + (left * 2)
  new_height = height + (top * 2)
  result = Image.new(image.mode, (new_width, new_height), color)
  result.paste(image, (left, top))
  return result


def mk_thumbnails(path, workdir, size, day):
  # We only use the top of the hour files
  if not day:
    day = (date.today() - timedelta(days=1)).strftime('%Y%m%d')
  else:
    day = day.strftime('%Y%m%d')

  _re = re.compile(rf'dxcc-.*-({day}+T\d+0000).png')
  thumbnail_names = []
  for fname in path.iterdir():
    if not _re.match(fname.name):
      continue
    tn_name = workdir.joinpath(fname.name)
    logging.debug('New thumbnail: %s', tn_name)
    image = Image.open(fname)
    image.thumbnail(size)
    image.save(tn_name)
    thumbnail_names.append(tn_name)

  return sorted(thumbnail_names)


def cleanup(path):
  for fname in path.iterdir():
    fname.unlink()
  path.rmdir()
  logging.info('Working directory "%s" removed', path)


def mk_workdir(path):
  workdir = path.joinpath('-workdir')
  workdir.mkdir()
  logging.info('Work directory %s created', workdir)
  return workdir


def type_tns(parg):
  size = []
  _size = parg.lower().split('x')
  for val in _size:
    if not val.isdigit():
      raise argparse.ArgumentTypeError
    size.append(int(val))
  return tuple(size)


def type_day(parg):
  if parg.lower() == 'today':
    day = date.today()
  elif parg.lower() == 'yesterday':
    day = date.today() - timedelta(days=1)
  else:
    day = datetime.strptime(parg, '%Y%m%d')
  return day


def main():
  log_file = None if os.isatty(sys.stdout.fileno()) else '/tmp/purge_images.log'
  logging.basicConfig(
    format='%(asctime)s %(name)s:%(lineno)3d %(levelname)s - %(message)s', datefmt='%x %X',
    level=logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO')),
    filename=log_file
  )
  logging.getLogger('PIL').setLevel(logging.INFO)

  default_size = 'x'.join(str(x) for x in OUTPUT_SIZE)
  parser = argparse.ArgumentParser(description='Stitch propagation graphs into a canvas')
  parser.add_argument('-o', '--output-name', nargs='*', default=['canvas.png'], type=Path,
                      help='Output image name (without the extension) [default: %(default)s]')
  parser.add_argument('-c', '--columns', type=int, default=COLUMNS,
                      help='Number of columns [default: %(default)d]')
  parser.add_argument('-r', '--rows', type=int, default=ROWS,
                      help='Numer of rows [default %(default)d]')
  parser.add_argument('-S', '--thumbnails-size', type=type_tns, default=default_size,
                      help='Thumbnails size width x height [default %(default)r]')
  parser.add_argument('-p', '--path', required=True, type=Path,
                      help='Directory containing the propagation graphs images')
  parser.add_argument('-d', '--day', default='yesterday', type=type_day,
                      help='Date format is "YYYYMMDD" as well as "today" or "yesterday"')
  opts = parser.parse_args()

  if not opts.path.exists():
    logging.error('%s Not Found', opts.path)
    raise SystemExit('Path ERROR')

  workdir = mk_workdir(opts.path)
  atexit.register(cleanup, workdir)
  thumbnails = mk_thumbnails(opts.path, workdir, opts.thumbnails_size, opts.day)
  thumbnails.sort()
  canvas = stitch_thumbnails(thumbnails, opts.columns, opts.rows, opts.thumbnails_size, opts.day)
  for canvas_name in (opts.path.joinpath(f) for f in opts.output_name):
    try:
      canvas.save(canvas_name, quality=100)
      logging.info(canvas_name)
    except ValueError as err:
      logging.error(err)


if __name__ == '__main__':
  main()
