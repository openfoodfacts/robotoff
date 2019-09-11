from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name="robotoff",
    version="1.0.7",
    author="Openfoodfacts Team",
    description="Real-time and batch prediction service for Openfoodfacts",
    url="https://github.com/openfoodfacts/robotoff",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    install_requires=[
        "requests>=2.13.0,<3.0.0",
        "peewee==3.10.0",
        "psycopg2-binary>=2.8,<2.9",
        "elasticsearch==6.3.1",
        "Click==7.0",
        "sentry-sdk==0.7.6",
        "Pillow>=5.0.0",
        "numpy>=1.9.1",
        "protobuf>=3.5.1",
        "Pint==0.9",
        'dataclasses>=0.6;python_version<"3.7"',
    ],
)
