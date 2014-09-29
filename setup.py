#!/usr/bin/env python
from setuptools import setup

setup(
    name='kademlia_aio',
    version='0.1',
    description='The Kademlia distributed hash table, implemented for Python 3.4 asyncio.',
    url='https://github.com/chrisguidry/kademlia_aio',
    license='MIT',
    author='Chris Guidry',
    author_email='chris@theguidrys.us',
    packages=['kademlia_aio'],
    test_suite='tests'
)
