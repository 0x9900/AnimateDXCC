#!/usr/bin/env python
# This is just an experiment.

import argparse
import atexit
import logging
import os
import re
import sys

from itertools import product
from datetime import date, datetime, timedelta

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

logging.basicConfig(format='%(asctime)s %(name)s:%(lineno)d %(levelname)s - %(message)s',
                    datefmt='%x %X', level=logging.INFO)

OFFSET = 40
FOOTER = 40
COLUMNS = 4
ROWS = 6
OUTPUT_SIZE = (360, 240)

try:
  RESAMPLING = Image.Resampling.LANCZOS
except AttributeError:
  RESAMPLING = Image.LANCZOS    # pylint: disable=no-member

def mk_overlay(image, day):
  home = os.path.dirname(sys.argv[0])
  font_t = ImageFont.truetype(os.path.join(home, 'JetBrainsMono-Bold.ttf'), 18)
  font_f = ImageFont.truetype(os.path.join(home, 'JetBrainsMono-MediumItalic.ttf'), 12)

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

  _re = re.compile(r'dxcc-.*-' + day + r'\d+00.png')
  thumbnail_names = []
  for name in os.listdir(path):
    if not _re.match(name):
      continue
    tn_name = os.path.join(workdir, name)
    logging.info('New thumbnail: %s', tn_name)
    image = Image.open(os.path.join(path, name))
    image.thumbnail(size)
    image.save(tn_name)
    thumbnail_names.append(tn_name)

  return thumbnail_names


def rm_workdir(path):
  workdir = os.path.join(path, f'workdir-{os.getpid()}')
  for name in os.listdir(workdir):
    os.unlink(os.path.join(workdir, name))
  os.rmdir(workdir)
  logging.info('Working directory "%s" removed', workdir)


def mk_workdir(path):
  workdir = os.path.join(path, f'workdir-{os.getpid()}')
  os.mkdir(workdir)
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
  yesterday = date.today() - timedelta(days=1)
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
  parser.add_argument('-p', '--path', required=True,
                      help='Directory containing the propagation graphs images')
  parser.add_argument('-d', '--day', default=yesterday, type=type_day,
                      help='Date format is "YYYYMMDD" as well as "today" or "yesterday"')
  opts = parser.parse_args()

  if not os.path.exists(opts.path):
    logging.error('%s Not Found', opts.path)
    sys.exit(os.EX_IOERR)

  workdir = mk_workdir(opts.path)
  atexit.register(rm_workdir, opts.path)
  thumbnails = mk_thumbnails(opts.path, workdir, opts.thumbnails_size, opts.day)
  thumbnails.sort()
  canvas = stitch_thumbnails(thumbnails, opts.columns, opts.rows, opts.thumbnails_size, opts.day)
  for ext in ('.png', '.webp'):
    canvas_name = os.path.join(opts.path, opts.output_name + ext)
    canvas.save(canvas_name, quality=100)
    logging.info(canvas_name)


if __name__ == '__main__':
  main()
