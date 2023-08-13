#!/usr/bin/env python
import os
from setuptools import setup, find_packages

ROOT = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(ROOT, 'README.md'), encoding='utf-8') as f:
    readme = f.read()

version = os.environ.get('DCU_VERSION', '0.0.0')


setup(
    name='drf-chunked-upload',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    version=version,
    description=('Upload large files to Django REST Framework in multiple chunks,' +
                 ' with the ability to resume if the upload is interrupted.'),
    long_description=readme,
    long_description_content_type='text/markdown',
    author='Jarrett Keifer',
    author_email='jkeifer0@gmail.com',
    url='https://github.com/jkeifer/drf-chunked-upload',
    install_requires=[
        'Django>=2.2',
        'djangorestframework>=3.11',
    ],
    python_requires='>3.7',
    license='MIT-Zero',
)
