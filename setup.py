import io
import json
import os
import subprocess

from setuptools import find_packages, setup

VERSION =  '0.1.1'
REPO = 'https://github.com/apache-superset/cherrytree'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

with io.open('README.md', encoding='utf-8') as f:
    long_description = f.read()


def get_git_sha():
    try:
        s = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
        return s.decode().strip()
    except Exception:
        return ''


setup(
    name='cherrytree',
    description=(
        'A build tool to pick cherry, bake release branches, and power '
        'label-driven development'),
    long_description=long_description,
    long_description_content_type='text/markdown',
    version=VERSION,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    scripts=['cherrytree/bin/cherrytree'],
    install_requires=[
        'click',
        'pygithub',
        'python-dateutil',
        'GitPython',
        'delegator.py',
        'pyhocon',
        'pyyaml',
        'yaspin',
    ],
    author='Maxime Beauchemin',
    author_email='maximebeauchemin@gmail.com',
    url=REPO,
    download_url= REPO + '/tarball/' + VERSION,
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
