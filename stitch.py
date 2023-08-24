#!/usr/bin/env python
# This is just an experiment.

import argparse
import atexit
import logging
import os
import re
import sys

from itertools import product
from datetime import date, timedelta

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

logging.basicConfig(format='%(asctime)s %(name)s:%(lineno)d %(levelname)s - %(message)s',
                    datefmt='%x %X', level=logging.INFO)

OFFSET = 40
FOOTER = 40

try:
  RESAMPLING = Image.Resampling.LANCZOS
except AttributeError:
  RESAMPLING = Image.LANCZOS    # pylint: disable=no-member

def mk_overlay(image):
  home = os.path.dirname(sys.argv[0])
  font_t = ImageFont.truetype(os.path.join(home, 'JetBrainsMono-Bold.ttf'), 18)
  font_f = ImageFont.truetype(os.path.join(home, 'JetBrainsMono-MediumItalic.ttf'), 12)

  yesterday = date.today() - timedelta(days=1)
  title = f'Hourly overview of HF propagation for {yesterday}'
  author = f'(c){yesterday.year} W6BSD https://bsdworld.org/'

  width, height = image.size
  overlay = Image.new('RGBA', (width, height))
  textbox = ImageDraw.Draw(overlay)
  wpos = textbox.textlength(title, font=font_t)
  textbox.text(((width - wpos)/2, 10), title, fill='#000044', font=font_t)
  textbox.text((10,  (height - FOOTER/1.5)), author, fill='#000000', font=font_f)
  return overlay


def stitch_thumbnails(thumbnails, cols, rows, output_size):
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

  canvas = Image.alpha_composite(canvas, mk_overlay(canvas))
  canvas = canvas.convert("RGB")
  return canvas


def add_margin(image, left=40, top=50, color='#ffffff'):
  width, height = image.size
  new_width = width + (left * 2)
  new_height = height + (top * 2)
  result = Image.new(image.mode, (new_width, new_height), color)
  result.paste(image, (left, top))
  return result


def mk_thumbnails(path, workdir, size=(240, 160)):
  # We only use the top of the hour files
  yesterday = (date.today() - timedelta(days=1)).strftime('%Y%m%d')
  _re = re.compile(r'dxcc-.*-' + yesterday + r'\d+00.png')
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


def main():
  parser = argparse.ArgumentParser(description='Stitch propagation graphs into a canvas')
  parser.add_argument('-p', '--path', required=True,
                      help='Directory containing the propagation graphs images')
  opts = parser.parse_args()

  if not os.path.exists(opts.path):
    logging.error('%s Not Found', opts.path)
    sys.exit(os.EX_IOERR)

  workdir = mk_workdir(opts.path)
  atexit.register(rm_workdir, opts.path)

  thumbnails = mk_thumbnails(opts.path, workdir)

  cols = 4
  rows = 6
  output_size = (240, 160)

  canvas = stitch_thumbnails(thumbnails, cols, rows, output_size)
  for ext in ('.png', '.webp'):
    canvas_name = os.path.join(opts.path, 'canvas' + ext)
    canvas.save(canvas_name, quality=100)
    logging.info(canvas_name)


if __name__ == '__main__':
  main()
