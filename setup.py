# -*- coding: utf-8 -*-
"""
    zdairi.py
    ~~~~~~~~
    
    Zeppelin CLI tool for wrapper zeppelin REST API.
    
    :copyright: (c) 2016 by Terrence Chin.
    :license: BSD, see LICENSE for more details.
"""
from setuptools import setup, find_packages

classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: BSD License',
    'Operating System :: MacOS',
    'Operating System :: POSIX',
    'Operating System :: Unix',
    'Operating System :: Microsoft',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 2.7',
    'Topic :: Internet :: Proxy Servers',
    'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
]

setup(
    name                = 'zdairi',
    version             = '0.4',
    description         = 'Zeppelin CLI tool for wrapper zeppelin REST API',
    long_description    = open('README.md').read().strip(),
    author              = 'Terrence Chin',
    author_email        = 'del680202@gmail.com',
    url                 = 'https://github.com/del680202/zdairi.git',
    license             = 'BSD',
    packages            = find_packages(),
    install_requires    = [],
    classifiers         = classifiers,
    entry_points        = {
         'console_scripts': [
            'zdairi = zdairi.zdairi:main'
        ] 
    }
)
