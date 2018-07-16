#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, 51 Franklin Street, Fifth Floor, Boston, MA 02110-1335, USA.
#
# Authors:
#     Santiago Dueñas <sduenas@bitergia.com>
#     Jesus M. Gonzalez-Barahona <jgb@gsyc.es>
#

import codecs
import os
import re

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
readme_md = os.path.join(here, 'README.md')
version_py = os.path.join(here, 'manuscripts', '_version.py')

# Pypi wants the description to be in reStrcuturedText, but
# we have it in Markdown. So, let's convert formats.
# Set up thinkgs so that if pypandoc is not installed, it
# just issues a warning.
try:
    import pypandoc
    long_description = pypandoc.convert(readme_md, 'rst')
except (IOError, ImportError):
    print("Warning: pypandoc module not found, or pandoc not installed. "
          "Using md instead of rst")
    with codecs.open(readme_md, encoding='utf-8') as f:
        long_description = f.read()


def files_in_subdir(dir, subdir):
    """Find all files in a directory."""
    paths = []
    for (path, dirs, files) in os.walk(os.path.join(dir, subdir)):
        for file in files:
            paths.append(os.path.relpath(os.path.join(path, file), dir))
    return paths


template_files = files_in_subdir('manuscripts', 'latex_template')
print("Template files: " + str(template_files))

with codecs.open(version_py, 'r', encoding='utf-8') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

setup(name="manuscripts",
      description="Produce reports based on GrimoireLab data",
      long_description=long_description,
      url="https://github.com/chaoss/grimoirelab-manuscripts",
      version=version,
      author="Bitergia",
      author_email="grimoirelab-discussions@lists.linuxfoundation.org",
      license="GPLv3",
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'Topic :: Software Development',
          'License :: OSI Approved :: ' +
          'GNU General Public License v3 or later (GPLv3+)',
          'Programming Language :: Python :: 3'
      ],
      keywords="development repositories analytics",
      packages=[
          'manuscripts',
          'manuscripts.metrics',
          'manuscripts2'
      ],
      package_data={'': template_files},
      # package_data={'': ['latex_template/report.tex']},
      install_requires=[
          'matplotlib',
          'prettyplotlib',
          'elasticsearch-dsl',
          'grimoire-elk>=0.30.4',
          'sortinghat>=0.4.2'
      ],
      scripts=[
          'bin/manuscripts'
      ],
      zip_safe=False)
