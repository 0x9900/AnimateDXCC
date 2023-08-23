#!/usr/bin/env python
# This is just an experiment.

import argparse
import atexit
import logging
import os
import re

from itertools import product
from datetime import date, timedelta

from PIL import Image

logging.basicConfig(format='%(asctime)s %(name)s:%(lineno)d %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S', level=logging.INFO)


try:
  RESAMPLING = Image.Resampling.LANCZOS
except AttributeError:
  RESAMPLING = Image.LANCZOS


def stitch_thumbnails(thumbnails, cols, rows, output_size):
  total_width = cols * output_size[0]
  total_height = rows * output_size[1]

  canvas = Image.new('RGB', (total_width, total_height))

  for i, j in product(range(rows), range(cols)):
    index = i * cols + j
    if index >= len(thumbnails):
      break
    thumbnail = Image.open(thumbnails[index])
    thumbnail = thumbnail.resize(output_size, RESAMPLING)
    canvas.paste(thumbnail, (j * output_size[0], i * output_size[1]))

  return canvas


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
  parser = argparse.ArgumentParser(description='Stitch band activity into a canvas')
  parser.add_argument('-p', '--path', required=True, help='Directory containing activity images')
  opts = parser.parse_args()
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
