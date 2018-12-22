#!/usr/bin/env python

import codecs
import os
import re

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


version = get_version('drf_chunked_upload')
readme = codecs.open('README.rst', 'r', 'utf-8').read()

setup(
    name='drf-chunked-upload',
    packages=['drf_chunked_upload'],
    version=version,
    description="""Upload large files to Django REST Framework in multiple chunks, 
    with the ability to resume if the upload is interrupted.""",
    long_description=readme,
    author='Jarrett Keifer',
    author_email='jkeifer0@gmail.com',
    url='https://github.com/jkeifer/drf-chunked-upload',
    install_requires=[
        'Django>=1.11',
        'djangorestframework>=3.0.0',
    ],
    license='MIT-Zero',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ]
)
