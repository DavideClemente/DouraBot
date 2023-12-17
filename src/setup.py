from setuptools import setup, find_packages
import os

setup(
    # other setup parameters
    packages=find_packages(),
    package_dir={'utilities': os.path.join('src', 'logic', 'utilities')}
)
