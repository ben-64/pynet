from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name='pynet',
    version='0.64',
    description='Some useful tunneling/proxying toolz in python',
    long_description=long_description,
    author='ben64',
    author_email='ben64@time0ut.org',
    packages=['pynet','pynet/endpoints','pynet/modules','pynet/tools',"pynet/proxys"],
    scripts=['bin/pycat','bin/pytun','bin/pyproxy']
)
