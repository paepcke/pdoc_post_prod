Prepares Python files that use sphinx-like parameter and return  specifications for input to the pdoc documentation tool (https://pypi.org/project/pdoc/). 

**Motivation:**

The pdoc HTML output does not recognize function/method parameter and return specifications in doc strings as special. So,

       :param foo: controls whether bar is set to None
       :type foo: int
       :return True for success, else False
       :rtype bool


will show up literally. If a module to be documentated is  instead preprocessed using this scripts, then the pdoc  documentation will look like this:
```
          <b>foo (int):</b> controls whether bar is set to None
          <b>returns</b> True for success, else False
          <b.return type:</b> bool
```

**Note:** whether '**:**' is used to introduce a specification, or '**@**' is controlled from a command line option. See main section below.

This module can be used directly, either to process an input file, or as part of a pipe. In general it is much more convenient to use *pdoc_run.py*:

    shell> pdoc_run.py --html-dir docs src/pdoc_prep/pdoc_prep.py

**Note:** it would be more sensible to include this functionality in the pdoc HTML production code itself. Alas, not enough time.
