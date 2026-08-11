from setuptools import find_packages, setup

setup(
	name="functional_demo",
	version="0.1.0",
	description="Sales & Functional Demo Management application for Frappe v15 / ERPNext v15",
	license="GPL-3.0",
	packages=find_packages(),
	include_package_data=True,
	python_requires=">=3.10",
	zip_safe=False,
)
