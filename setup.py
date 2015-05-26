# -*- coding: utf-8 -*-
import sys
import os.path
from setuptools import Command, find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))

README_PATH = os.path.join(HERE, 'README.rst')
try:
    README = open(README_PATH).read()
except IOError:
    README = ''

setup(
    name='rollbar-udp-agent',
    version='0.0.14',
    description='Rollbar server-side UDP agent',
    long_description=README,
    author='Luis Rascão',
    author_email='luis.rascao@gmail.com',
    url='http://github.com/lrascao/rollbar-udp-agent',
    entry_points={
        "console_scripts": [
            "rollbar-udp-agent=rollbar_udp_agent:main"
        ],
    },
    packages=['rollbar_udp_agent'],
    data_files=[('/etc', ['rollbar-udp-agent.conf']),
                ('/etc/init.d', ['rollbar-udp-agent'])],
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
        "Topic :: Software Development",
        "Topic :: Software Development :: Bug Tracking",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Quality Assurance",
        ],
    install_requires=[
        'requests'
    ],
    )
