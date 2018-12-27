from setuptools import setup, find_packages

setup(
    name = "pdoc_prep",
    version = "0.0.1",
    packages = find_packages(),

    # Dependencies on other packages:
    setup_requires   = [],
    install_requires = ['pdoc>=0.3.2',
                        ],

    # Unit tests; they are initiated via 'python setup.py test'
    test_suite       = 'nose.collector', 

    # metadata for upload to PyPI
    author = "Andreas Paepcke",
    author_email = "paepcke@cs.stanford.edu",
    description = "Add processing of sphinx-like docstring specs to pdoc via preprocessor.",
    license = "BSD",
    keywords = "pdoc, python documentation",
    url = "git@github.com:paepcke/pdoc_prep.git",   # project home page, if any
)
