# -*- coding: utf-8 -*-
from pathlib import Path

from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# Read the version without importing the package. Importing whitelabel here
# would also import Frappe, which may not be available in an isolated build.
version = {}
exec((Path(__file__).parent / "whitelabel" / "version.py").read_text(), version)

setup(
	name='whitelabel',
	version=version["__version__"],
	description='ERPNext Whitelabel',
	author='Rishabh',
	author_email='rishabh@onehash.ai',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
