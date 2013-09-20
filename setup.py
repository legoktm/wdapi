from setuptools import setup

setup(
    name='wdapi',
    version='1.2.0',
    packages=['wdapi'],
    url='https://github.com/legoktm/wdapi',
    license='Public domain',
    author='Kunal Mehta',
    author_email='legoktm@gmail.com',
    description='A simple API to parse constraints of properties on Wikidata for wmflabs.',
    install_requires=[
        'redis',
        'mwparserfromhell',
    ],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
    ],
    test_suite="tests",
)
