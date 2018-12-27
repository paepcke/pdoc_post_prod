# pdoc_prep: Add sphinx-like function doc specs to pdoc #

Prepares Python files that use sphinx-like parameter and return  specifications for input to the pdoc documentation tool (https://pypi.org/project/pdoc/). 

## Motivation:

The pdoc HTML output does not recognize function/method parameter and return specifications in doc strings as special. So,

       :param foo: controls whether bar is set to None
       :type foo: int
       :return True for success, else False
       :rtype bool


will show up literally. If a module to be documentated is  instead preprocessed using this script, then the pdoc documentation will look like this:
```
          foo (int): controls whether bar is set to None
          returns True for success, else False
          return type: bool
```

The keywords, such as **returns**, and parameters, such as **foo (int)** will be bold faced.

**Note:** whether '**:**' is used to introduce a specification, or '**@**' is controlled from a command line option. See main section below.

## Usage

    shell> pdoc_run.py --html-dir docs src/pdoc_prep/pdoc_prep.py

This command may be run from the project root, from within the evolving docs directory, or in the package directory. Obviously, the paths need to be adjusted accordingly.

## Notes

**Note 1:**
You may see:

    DeprecationWarning: the imp module is deprecated in favour of importlib; see the module's documentation for alternative uses
    import imp

This warning occurs in pdoc, which is not modified by this preprocessor. To suppress the warning, you can define an environment variable:

    export PYTHONWARNINGS=ignore

in the shell where you are working.

**Note2:**
It would be more sensible to include this functionality in the pdoc HTML production code itself. Alas, not enough time.

