from distutils.core import setup
from setuptools import find_packages

app_id = 'djtimers'
app_name = 'djtimers'
app_description = "Django utils."
install_requires = [
]

VERSION = __import__(app_id).__version__

CLASSIFIERS = [
    'Framework :: Django',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Topic :: Software Development',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
]

setup(
    name=app_name,
    description=app_description,
    version=VERSION,
    author="heli",
    author_email="bbhe_gw@163.com",
    license='MIT License',
    platforms=['OS Independent'],
    url="",
    packages=find_packages(exclude=[""]),
    include_package_data=True,
    install_requires=install_requires,
    classifiers=CLASSIFIERS,
)
