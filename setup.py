import re
import ast
from setuptools import setup, find_packages

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('pgspecial/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

description = 'Meta-commands handler for Postgres Database.'


setup(
    name='pgspecial',
    author='Pgcli Core Team',
    author_email='pgcli-dev@googlegroups.com',
    version=version,
    license='LICENSE.txt',
    url='https://www.dbcli.com',
    packages=find_packages(),
    description=description,
    long_description=open('README.rst').read(),
    install_requires=[
        'click >= 4.1',
        'sqlparse >= 0.1.19',
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: SQL',
        'Topic :: Database',
        'Topic :: Database :: Front-Ends',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
