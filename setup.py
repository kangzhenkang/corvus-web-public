#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import os.path
from setuptools import setup, find_packages

import corvus_web


def find_files():
    data = []
    root = './corvus_web/'
    for d, _, files in os.walk(root + 'static'):
        data.extend(os.path.join(d, f) for f in files
                    if not (f.startswith('.') or f.endswith('.pyc')))
    return [d[len(root):] for d in data]


setup(
    name='corvus-web',
    version=corvus_web.__version__,
    description='Redis cluster administration dashboard',
    long_description=open('README.rst').read(),
    url='https://github.com/eleme/corvus-web',
    author='maralla',
    author_email='imaralla@icloud.com',
    license='MIT',
    keywords='redis cluster administration dashboard',
    packages=find_packages(),
    package_data={'corvus_web': find_files()},
    install_requires=[
        'ruskit>=0.0.11',
        'sqlalchemy',
        'flask',
        'flask_sqlalchemy',
        'flask_restless',
        'gevent',
        'requests',
        'pystatsd',
        'psutil',
    ],
    extras_require={
        'mysql': ['MySQL-python'],
    },
    entry_points={
        'console_scripts': ['corvus_web = corvus_web.cli:main']
    }
)
