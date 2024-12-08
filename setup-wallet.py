import os
from setuptools import setup, find_packages


def get_here(file: str):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), file)


def get_long_description():
    readme = get_here('README.md')
    if os.path.isfile(readme):
        with open(readme, 'r') as f:
            return f.read()
    return ''


def get_name():
    return 'satorilib'


def get_version():
    return '0.0.1'


def get_requirements():
    requirements = get_here('requirements-api.wallet.txt')
    if os.path.isfile(requirements):
        with open(requirements, 'r') as f:
            return f.read().splitlines()
    return []


setup(
    name=get_name(),
    version=get_version(),
    description='satorilib contains domain model and apis for the Satori Network',
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    packages=['satorilib.wallet'],
    dependency_links=[
        'git+https://github.com/SatoriNetwork/python-evrmorelib.git#egg=python-evrmorelib'
    ],
    install_requires=get_requirements(),
    python_requires='>=3.9.5',
    author='Jordan Miller',
    author_email="jordan@satorinet.io",
    url=f'https://github.com/SatoriNetwork/{get_name()}',
    download_url=f'https://github.com/SatoriNetwork/{get_name()}',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            f"{get_name()} = {get_name()}.cli:main",
        ]
    },
)
