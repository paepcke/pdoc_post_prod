from setuptools import setup, find_packages

with open('README.md') as file:
    long_description = file.read()
    
setup(
    name = "pdoc_prep",
    version = "0.0.3",
    packages = find_packages(),

    # Dependencies on other packages:
    setup_requires   = [],
    install_requires = ['pdoc>=0.3.2',
                        ],

    # Unit tests; they are initiated via 'python setup.py test'
    test_suite       = 'nose.collector', 

    # metadata for upload to PyPI
    author="Andreas Paepcke",
    author_email="paepcke@cs.stanford.edu",
    long_description_content_type="text/markdown",
    description="Add processing of sphinx-like docstring specs to pdoc via preprocessor.",
    long_description=long_description,
    license="BSD",
    keywords="pdoc, python documentation",
    url="https://github.com/paepcke/pdoc_prep"
)
