from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name="robotoff",
    version="1.0.13",
    author="Openfoodfacts Team",
    description="Real-time and batch prediction service for Openfoodfacts",
    url="https://github.com/openfoodfacts/robotoff",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    install_requires=[
        "requests>=2.13.0,<3.0.0",
        "peewee==3.13.3",
        "psycopg2-binary>=2.8,<2.9",
        "elasticsearch==6.3.1",
        "Click==7.1.2",
        "Pillow>=5.0.0",
        "numpy>=1.16.0",
        "protobuf>=3.5.1",
        "Pint==0.11",
        'dataclasses>=0.6;python_version<"3.7"',
        "flashtext==2.7",
        "langid==1.1.6",
        "more-itertools>=8.0.0,<9.0.0",
        "spacy>=2.2.0,<2.3.0",
        "pymongo>=3.0.0<3.1.0",
        "dacite==1.5.0",
    ],
    include_package_data=True,
    tests_require=["pytest", "pytest-mock"],
)
