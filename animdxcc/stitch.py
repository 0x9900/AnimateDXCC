#!/usr/bin/env python
# This is just an experiment.

import argparse
import atexit
import logging
import os
import re
import shutil
from datetime import date, datetime, timedelta
from importlib.resources import files
from itertools import product
from pathlib import Path
from typing import Optional, Type

from PIL import Image, ImageDraw, ImageFont

OFFSET = 40
FOOTER = 40
COLUMNS = 4
ROWS = 6
OUTPUT_SIZE = (360, 240)

RESAMPLING = Image.Resampling.LANCZOS

COLORS = {
  'dark': {'background': '#0c0c0c', 'foreground': '#eeeeee', },
  'light': {'background': '#ffffff', 'foreground': '#000000', },
}


class Workdir:
  def __init__(self, source: Path) -> None:
    self.workdir = source.joinpath('_workdir')

  def __enter__(self) -> Path:
    try:
      self.workdir.mkdir()
      return self.workdir
    except IOError as err:
      raise err

  def __exit__(self, exc_type: Optional[Type[BaseException]],
               exc_value: Optional[BaseException],
               traceback: Optional[Type[BaseException]]) -> None:
    shutil.rmtree(self.workdir)


def mk_overlay(image, day, style):
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
  textbox.text(((width - wpos)/2, 10), title, fill=COLORS[style]['foreground'], font=font_t)
  textbox.text((10,  (height - FOOTER/1.5)), author, fill=COLORS[style]['foreground'], font=font_f)
  return overlay


def stitch_thumbnails(thumbnails, cols, rows, output_size, day, style):
  total_width = cols * output_size[0]
  total_height = rows * output_size[1] + OFFSET + FOOTER

  canvas = Image.new('RGBA', (total_width, total_height), color=COLORS[style]['background'])

  for i, j in product(range(rows), range(cols)):
    index = i * cols + j
    if index >= len(thumbnails):
      break
    thumbnail = Image.open(thumbnails[index])
    thumbnail = thumbnail.resize(output_size, RESAMPLING)
    canvas.paste(thumbnail, (j * output_size[0], i * output_size[1] + OFFSET))

  canvas = Image.alpha_composite(canvas, mk_overlay(canvas, day, style))
  canvas = canvas.convert("RGB")
  return canvas


def create_link(filename, target):
  if os.path.exists(target):
    os.unlink(target)
  os.link(filename, target)
  logging.info('Link to "%s" created', target)


def add_margin(image, left=40, top=50, color='#ffffff'):
  width, height = image.size
  new_width = width + (left * 2)
  new_height = height + (top * 2)
  result = Image.new(image.mode, (new_width, new_height), color)
  result.paste(image, (left, top))
  return result


def mk_thumbnails(path, workdir, size, day, style):
  # We only use the top of the hour files
  if not day:
    day = (date.today() - timedelta(days=1)).strftime('%Y%m%d')
  else:
    day = day.strftime('%Y%m%d')

  _re = re.compile(rf'dxcc-.*-({day}+T\d+0000)-{style}.png')
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
  logging.basicConfig(
    format='%(asctime)s %(name)s:%(lineno)3d %(levelname)s - %(message)s', datefmt='%x %X',
    level=logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO')),
  )
  logging.getLogger('PIL').setLevel(logging.INFO)

  default_size = 'x'.join(str(x) for x in OUTPUT_SIZE)
  parser = argparse.ArgumentParser(description='Stitch propagation graphs into a canvas')
  parser.add_argument('-o', '--output-name', default='canvas',
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
  parser.add_argument('-s', '--style', required=True, choices=('dark', 'light'),
                      help='Output style')
  opts = parser.parse_args()

  if not opts.path.exists():
    logging.error('%s Not Found', opts.path)
    raise SystemExit('Path ERROR')

  workdir = mk_workdir(opts.path)
  atexit.register(cleanup, workdir)
  thumbnails = mk_thumbnails(opts.path, workdir, opts.thumbnails_size, opts.day, opts.style)
  canvas = stitch_thumbnails(thumbnails, opts.columns, opts.rows, opts.thumbnails_size, opts.day,
                             opts.style)
  try:
    canvas_name = opts.path.joinpath(f'{opts.output_name}-{opts.style}.png')
    canvas.save(canvas_name, quality=100)
    logging.info('%s saved', canvas_name)
    if opts.style == 'light':
      old_name = opts.path.joinpath(f'{opts.output_name}.png')
      create_link(canvas_name, old_name)
      logging.info('%s saved', old_name)

  except ValueError as err:
    logging.error(err)


if __name__ == '__main__':
  main()
