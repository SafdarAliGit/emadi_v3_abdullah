from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in emadi_v3_abdullah/__init__.py
from emadi_v3_abdullah import __version__ as version

setup(
	name="emadi_v3_abdullah",
	version=version,
	description="this is app for emadi weaving (v3)",
	author="Safdar Ali",
	author_email="safdar211@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
