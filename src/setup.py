from setuptools import setup, find_packages

setup(
    # other setup parameters
    packages=find_packages() + ['multidict._multilib'],
)
