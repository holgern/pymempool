import codecs
import io
import os
import sys

from setuptools import setup

VERSION = '0.0.1'

tests_require = ['pytest']

requires = [
    "urllib3",
    "requests",
    "response"
]

if __name__ == '__main__':
    setup(
        name='pymempool',
        version=VERSION,
        description='Python Api for mempool.info',
        long_description=open('README.md').read(),
        long_description_content_type="text/markdown",
        author='Holger Nahrstaedt',
        author_email='nahrstaedt@gmail.com',
        url='http://www.github.com/holgern/pymempool',
        keywords=['btc', 'mempool'],
        packages=[
            "pymempool",
        ],
        classifiers=[
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3',
        ],
        install_requires=requires,
        tests_require=tests_require,
    )    