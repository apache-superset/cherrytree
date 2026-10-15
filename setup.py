import io
import os

from setuptools import find_packages, setup

VERSION = '2.0.1'
REPO = 'https://github.com/apache-superset/cherrytree'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

with io.open('README.md', encoding='utf-8') as f:
    long_description = f.read()


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
        'GitPython>=3.1.62',
        'delegator.py',
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
