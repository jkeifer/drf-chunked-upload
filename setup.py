#!/usr/bin/env python
import os

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

with open('README.rst', 'r') as r:
    readme = r.read()

download_url = (
    'https://github.com/jkeifer/drf-chunked-upload/tarball/%s'
)

version = os.environ.get('DCU_VERSION', '0.0.0')

setup(
    name='drf-chunked-upload',
    packages=find_packages(exclude=['tests*']),
    version=version,
    description=('Upload large files to Django REST Framework in multiple chunks,' +
                 ' with the ability to resume if the upload is interrupted.'),
    long_description=readme,
    author='Jarrett Keifer',
    author_email='jkeifer0@gmail.com',
    url='https://github.com/jkeifer/drf-chunked-upload',
    download_url=download_url % version,
    install_requires=[
        'Django>=2.2',
        'djangorestframework>=3.11',
    ],
    license='MIT-Zero'
)
