#!/usr/bin/env python
'''
Created on Dec 18, 2018

Prepares Python files that use sphinx-like parameter and return 
specifications for input to the pdoc documentation tool
(https://pypi.org/project/pdoc/). 

**Motivation:**

The pdoc HTML output does not recognize function/method
parameter and return specifications in doc strings as special.
So,
<pre>
      :param foo: controls whether bar is set to None
      :type foo: int
      :return True for success, else False
      :rtype bool
</pre>     
will show up literally. If a module to be documentated is 
instead preprocessed using this scripts, then the pdoc 
documentation will look like this:
<pre>
      foo (int): controls whether bar is set to None
      returns True for success, else False
      return type: bool
</pre>     

**Note:** whether '<b>:</b>' is used to introduce a specification,
or '<b>@</b>' is controlled from a command line option. See main
section below.

This module can be used directly, either to process an input
file, or as part of a pipe. In general it is much more
conventient to use *pdoc_run.py*:

    ```
    shell> pdoc_run.py --html-dir docs src/pdoc_prep/pdoc_prep.py
    ```
<br>
Used directly:<br>
    ```
    shell> cat myMod.py | pdoc_prep.py > new myModTmp.py; pdoc --html myModTmp.py
    ```
    
**Note:** it would be more sensible to include this functionality in
the pdoc HTML production code itself. Alas, not enough time. 
     
@author: Andreas Paepcke
'''
import argparse
import os
import re
import sys


# ---------------------------------- Special Exception and Enums -----------------
class NoTypeError(Exception):
    pass

class NoParamError(Exception):
    pass

class ParamTypeMismatch(Exception):
    pass

class DoubleReturnError(Exception):
    pass

class HandleRes(enumerate):
    HANDLED     = True
    NOT_HANDLED = False

# ---------------------------------- Class ParseInfo -----------------

class ParseInfo(object):
    '''
    Holds regexp patterns and other constants used
    in finding parameter and return doc string fragments
    in the pdoc HTML output.  
    '''
    
    def __init__(self, delimiter_char):
        '''
        Initialize different regexp and other constants
        depending on whether the delimiter for starting
        a parameter/type/return, or raises directive. Legal
        starting delimiters are ':' and '@', as in ':param...',
        and '@param...'.
        
        @param delimiter_char: char literal in [':', '@']
        @type delimiter_char: char
        '''

        self.curr_in_docstr = False
        
        if delimiter_char not in [':', '@']:
            raise ValueError("Delimiter char must be one of ':' or '@'.")
                   
        if delimiter_char == ':':
            self.parm_markers = [':param', ':type', ':return', ':rtype', ':raises']
        elif delimiter_char == '@':
            self.parm_markers = ['@param', '@type', '@return', '@rtype', '@raises']

        self.line_sep = '</br>'
        
        self.line_blank_pat    = re.compile(r'^[\s]*$')
        
        if delimiter_char == ':':
            # Find :param myParm: meaning of my parm
            self.param_pat    = re.compile(r'(^[ ]+):param([^:]*):(.*)$')
            # Find :type myParm: int
            self.type_pat     = re.compile(r'(^[ ]+):type([^:]*):(.*)$')
            # Be forgiving; accept ':return ', ':return:', ':returns ', and ':returns:' 
            self.return_pat   = re.compile(r'(^[ ]+):return[s]{0,1}[:| ]{0,1}(.*)$')
            # Find :rtype int</span> and allow an optional colon after the 'rtype':
            self.rtype_pat    = re.compile(r'(^[ ]+):rtype[:| ]{0,1}(.*)$')
            # Find :raises ValueError, and allow an optional colon after the 'raises'.
            # Accepts 'raise', 'raises', and 'raised'              
            self.raises_pat   = re.compile(r'(^[ ]+):raise[s|d]{0,1}[:| ]{0,1}(.*)$')
        else:
            # Same, but using '@' as the delimiter:
            self.param_pat    = re.compile(r'(^[ ]+)@param([^:]*):(.*)$')
            self.type_pat     = re.compile(r'(^[ ]+)@type([^:]*):(.*)$')
            # Be forgiving; accept ':return ', ':return:', ':returns ', and ':returns:' 
            self.return_pat   = re.compile(r'(^[ ]+)@return[s]{0,1}[:| ]{0,1}(.*)$')
            self.rtype_pat    = re.compile(r'(^[ ]+)@rtype[:| ]{0,1}(.*)$')
            # Accepts 'raise', 'raises', and 'raised'                          
            self.raises_pat   = re.compile(r'(^[ ]+)@raise[s|d]{0,1}[:| ]{0,1}(.*)$')

        self.single_quote_one_liner     = re.compile(r"^[\s]*[']{3}[^']+[']{3}$")

        self.single_quote_doc_open_pat  = re.compile(r"^[\s]*[']{3}")
        self.single_quote_doc_close_pat = re.compile(r"[']{3}[\s]*$")

        self.double_quote_doc_open_pat  = re.compile(r'^[\s]*["]{3}')
        self.double_quote_doc_close_pat = re.compile(r'["]{3}[\s]*$')

    #-------------------------
    # in_docstr 
    #--------------

    def in_docstr(self, line):
        '''
        Given a string, return True if parsing is currently in a
        docstr, else False. Handles delimiters triple single-quotes
        and triple double-quotes. 
        
        Requires nothing but white space before and after the
        docstring delimiter. 
        
        Maintains self.curr_in_docstr for needed context
        
        @param line: one line of text
        @type line: str
        '''

        single_open_m  = self.single_quote_doc_open_pat.search(line) 
        single_close_m = self.single_quote_doc_close_pat.search(line)

        double_open_m  =  self.double_quote_doc_open_pat.search(line) 
        double_close_m = self.double_quote_doc_close_pat.search(line)
        
        # If found both, open and close delimiter, it's either
        # one delimiter on an otherwise empty line, or two delimiter
        # with text in between, i.e. a one-line docstr. Regex matches 
        # for close and open contain the span of the respective matches.
        #
        # E.g.: for a single delim in a line, starting at char 8, the open
        # and close spans are (0,11) and (8,12): the opening delimiter ends 
        # after the delim, at 11. The match for the same delim starts before 
        # the delimiter, at 8. There is only one delim iff the start of the closing 
        # match is off from the end of the opening match by the length of the 
        # delimiter (i.e. 3):
         
        if single_open_m and single_close_m and (single_close_m.span()[0] + 3 != single_open_m.span()[1]) or\
           double_open_m and double_close_m and (double_close_m.span()[0] + 3 != double_open_m.span()[1]):
            # One-liner:
            return False
        
        # May have both, open and close delimiter matches, but they
        # are the same delimiter on an empty line:        
        if self.curr_in_docstr == "'''" and single_open_m and single_close_m:
            single_open_m = None
        elif self.curr_in_docstr == '"""' and double_open_m and double_close_m:
            double_open_m = None
        elif not self.curr_in_docstr and single_open_m and single_close_m:
            # Single-line docstring: opens and closes in one line:
            single_close_m = False
        elif not self.curr_in_docstr and double_open_m and double_close_m:
            # Single-line docstring: opens and closes in one line:
            double_close_m = False
        
        
        # Check for single line docstr, which we just pass through:
        if (single_open_m and single_close_m) or (double_open_m and double_close_m):
            return False
        
        # We are newly opening a docstr if we are not already in a docstr,
        # and we are opening one now with either ''' or """:
        
        opening_docstr = None
        if not self.curr_in_docstr:
            if single_open_m:
                opening_docstr = "'''"
            elif double_open_m:
                opening_docstr = '"""'
        
        # If currently in a docstr, then closing means that we 
        # found a closing ''' or """ that matches the delimiter used
        # to open the docstr:
        closing_docstr = None
        if self.curr_in_docstr:
            if single_close_m and self.curr_in_docstr == "'''":
                closing_docstr = "'''"
            elif double_close_m:
                closing_docstr = '"""'
                            
        if self.curr_in_docstr and closing_docstr:
            self.curr_in_docstr = None
        elif not self.curr_in_docstr and opening_docstr:
            self.curr_in_docstr = opening_docstr
        
        return self.curr_in_docstr

# ---------------------------------- Class PdocPrep -----------------

class PdocPrep(object):
    '''
    Reads a pdoc-produced HTML file. Finds the 
    :param, :type, :return, :rtype, and :raises
    lines. Replaces them with HTML.
    
    :param foo: this tells about fum
    :type foo: int
    
    Is turned into: 
        <b>foo</b>(<i>int</i>): this tells about fum<br>
        
    Similarly for :return/:rtype, and :raises
    '''
        
    #-------------------------
    # Constructor 
    #--------------
    
    def __init__(self, 
                 in_fd=sys.stdin, 
                 out_fd=sys.stdout,
                 raise_errors=True,
                 warnings_on=False,
                 delimiter_char='@',
                 force_type_spec=False):
        '''
        Constructor
        
        @param in_fd: source of pdoc-produced HTML file. Default: stdin
        @type in_fd: file-like
        @param out_fd: destination of transformed html. Default: stdout
        @type out_fd: file-like
        @param raise_errors: if True then irregularities will raise errors. Default: True
        @type raise_errors: boolean
        @param warnings_on: if True then irregularities generate warnings to stderr.
            Ignored if raise_errors is True
        @type warnings_on: boolean
        @param delimiter_char: starting char of a directive: ':' or '@'. Default: '@'
        @type delimiter_char: char
        '''
        
        self.out_fd = out_fd
        self.raise_errors = raise_errors
        self.warnings = warnings_on
        self.force_type_spec = force_type_spec
        self.delimiter_char = delimiter_char
        self.parseInfo = ParseInfo(delimiter_char)
        self.parse(in_fd)

    #-------------------------
    # parse 
    #--------------
        
    def parse(self, in_fd):
        '''
        Goes through each HTML line looking for relevatn
        doc string snippets to transform 
        
        
        @param in_fd: input stream
        @type in_fd: file-like
        '''
        
        self.curr_parm_match = None
        self.curr_return_desc = None
        
        try:
            # Try finding in every line each of the special directives,
            # and transform if found, alse pass through.
            for (line_num, line) in enumerate(in_fd.readlines()):
                
                # Before consuming current line, which could finish
                # a docstr we are currently processing, remember
                # state now:
                in_docstr_before_this_line = self.parseInfo.curr_in_docstr
                
                # Update whether in docstr or not:
                self.parseInfo.in_docstr(line)
                
                # If we are not in a docstr, just pass the line though.
                # But special case: if it's the current line that finishes
                # a docstr, we need to process it. Could be something like
                #      :return'''
                
                if not self.parseInfo.curr_in_docstr and not in_docstr_before_this_line:
                    self.out_fd.write(line)
                    continue
                
                # We are working through a docstr:
                
                # Empty lines within a docstr get a terminating </br>:
                if self.is_blank_line(line):
                    # Keep indentation (spaces/tabs), but replace NL with </br>
                    self.out_fd.write(line[0:len(line)-1] + self.parseInfo.line_sep)
                    continue
                
                if self.check_param_spec(line, line_num) == HandleRes.HANDLED:
                    continue
                if self.check_type_spec(line, line_num)  == HandleRes.HANDLED:
                    continue
                if self.check_return_spec(line, line_num)  == HandleRes.HANDLED:
                    continue
                if self.check_rtype_spec(line, line_num) == HandleRes.HANDLED:
                    continue
                if self.check_raises_spec(line, line_num) == HandleRes.HANDLED:
                    continue

                if self.curr_parm_match is not None:
                    self.append_to_parm_desc(line)
                    continue
                elif self.curr_return_desc is not None:
                    self.append_to_return_desc(line)
                    continue

                # We are in a docstring area, but not in 
                # any parameter/return/type spec:
                self.out_fd.write(line)
                continue

        finally:
            # Ensure that a possibly open parameter spec is closed:
            if self.curr_parm_match is not None:
                self.finish_parameter_spec(type_found=False, line_no=line_num)
            # Same for return spec:                
            elif self.curr_return_desc is not None:
                self.finish_return_spec(rtype_found=False, line_no=line_num)
        
    #-------------------------
    # handle_multiline_spec 
    #--------------
    
    def handle_multiline_spec(self, line):
        '''
        Both, parameter and return specifications can 
        run across multiple lines. Those lines need
        to be collected and placed into one string.
        
        @param line: current line to parse
        @type line: str
        @returns True if a multiline was detected, else False
        @rtype bool
        '''
        # In the middle of a multiline parm spec?
        if self.curr_parm_match is not None:
            (param_name, param_desc) = self.curr_parm_match
            param_desc += ' ' + line
            self.curr_parm_match = (param_name, param_desc)
            return True
        
        # Are we in the middle of a return specification? If so, this 
        # is likely a continuation line:
        if self.curr_return_desc is not None:
            self.curr_return_desc += ' ' + line.strip()
            return True
        
        return False

    #-------------------------
    # check_param_spec 
    #--------------
    
    def check_param_spec(self, line, line_num):
        '''
        Handle :param and @param.
        
        @param line: line to check for directive
        @type line: str
        @param line_num: line number in original HTML file. Used for error msgs.
        @type line_num: int
        @returns whether the given line was handled and output,
            or nothing was done.
        @rtype HandleRes
        '''
        
        parm_match = self.parseInfo.param_pat.search(line)
        if parm_match is None:
            return HandleRes.NOT_HANDLED
        else:
            # Got a parameter spec
            # Is there one already, waiting for a type,
            # and caller has force_type_spec set to True:
            if self.curr_parm_match is not None:
                (parm_name_prev, _parm_desc_prev) = self.curr_parm_match
                if self.force_type_spec:
                    msg = "Parameter being defined at line %s, but parameter %s still needs a type." %\
                            (line_num,parm_name_prev)
                    # Throw error or print warning:
                    self.error_notify(msg, NoTypeError)
                self.finish_parameter_spec()
                
            # The regexp groups look like this:
            #    ('       ', ' tableName', ' name of new table')
            # Keep the indentation before the parameter name:
            frags = parm_match.groups()
            indent    = frags[0]
            parm_name = frags[1].strip()
            parm_desc = frags[2].strip()
            
            self.curr_parm_match = (parm_name, parm_desc)
            self.out_fd.write(indent + '<b>' + parm_name + '</b> ')
            return HandleRes.HANDLED

    #-------------------------
    # check_type_spec 
    #--------------
    
    def check_type_spec(self, line, line_num):
        '''
        Handle :type and @type.
        
        @param line: line to check for directive
        @type line: str
        @param line_num: line number in original HTML file. Used for error msgs.
        @type line_num: int
        @returns whether the given line was handled and output,
            or nothing was done.
        @rtype HandleRes
        @raises NoTypeError, NoParamError, ParamTypeMismatch
        '''
        
        type_match = self.parseInfo.type_pat.search(line)
        
        # For convenience and good error messages:
        if self.curr_parm_match is not None:
            (parm_name, parm_desc) = self.curr_parm_match
            
        # Have a prior parameter spec, but no type spec?
        if type_match is None and self.curr_parm_match is not None:
            # Prev line was a parameter spec, but this line is
            # not a type spec. That's fine, b/c parameter specs
            # can be multiline.
            return HandleRes.NOT_HANDLED
        
        # Have a type match but not a prior parameter spec?
        elif type_match is not None and self.curr_parm_match is None:
            msg = "Type declaration without prior parameter; line %s" % line_num
            self.error_notify(msg, NoParamError)
            return HandleRes.NOT_HANDLED
        
        # Almost home: 
        elif type_match is not None and self.curr_parm_match is not None:
            # Had a prior ":param" line, and now a type.  
            # Ensure that the type is about the same parameter:
            
            # Have groups like this:
            #    ('       ', ' tableName', ' String')
            # Keep the indentation before the parameter name:
            frags = type_match.groups()
            _indent    = frags[0]
            type_name = frags[1].strip()
            type_desc = frags[2].strip()

            if type_name != parm_name:
                # Have a parm spec followed by a type spec,
                # but the type spec doesn't match the parameter:
                msg = "Type %s, but preceding param %s; line %s.\n" %\
                        (type_name, parm_name, line_num)
                self.error_notify(msg, ParamTypeMismatch)
                return HandleRes.NOT_HANDLED
            
            # Finally...all is good:
            self.out_fd.write('(<b></i>' + type_desc + '</i></b>): ')
            self.finish_parameter_spec(type_found=True, line_no=line_num)
            return HandleRes.HANDLED
        # Not a type spec, and no prior param spec:
        return HandleRes.NOT_HANDLED
        
    #-------------------------
    # check_return_spec 
    #--------------
    
    def check_return_spec(self, line, line_num):
        '''
        Handle :return and @return.
        
        @param line: line to check for directive
        @type line: str
        @param line_num: line number in original HTML file. Used for error msgs.
        @type line_num: int
        @returns whether the given line was handled and output,
            or nothing was done.
        @rtype HandleRes
        '''
        return_match = self.parseInfo.return_pat.search(line)
        if return_match is None:
            return HandleRes.NOT_HANDLED
    
        # Got a 'return: ' or 'return ' or 'returns ' or 'returns ' spec
        # If there is an open parameter spec, finish it:

        # Finish any possibly open parameter spec:        
        self.finish_parameter_spec()

        # Is there is (an open) return spec already, that's bad, only one allowed.
        # We don't check for already completed prior return specs. We should.
        
        if self.curr_return_desc is not None:
            msg = "Missing '%srtype' in previous '%sreturn' spec, or two '%sreturn' specs in same docstr (line %s)" % \
                        (self.delimiter_char, self.delimiter_char, self.delimiter_char, line_num)
            self.error_notify(msg, DoubleReturnError)
            self.finish_return_spec()
            self.curr_return_desc = None

        # Have groups like this:
        #    ('       ', 'a number between 1 and 10')
        # Keep the indentation before the parameter name:
        frags = return_match.groups()
        indent    = frags[0]
        self.curr_return_desc = frags[1].strip()

        self.out_fd.write(indent + '<b>returns:</b> ')
        return HandleRes.HANDLED
    
    #-------------------------
    # check_rtype_spec 
    #--------------
    
    def check_rtype_spec(self, line, line_num):
        '''
        Handle :rtype and @rtype.
        
        @param line: line to check for directive
        @type line: str
        @param line_num: line number in original HTML file. Used for error msgs.
        @type line_num: int
        @returns whether the given line was handled and output,
            or nothing was done.
        @rtype HandleRes
        '''
        
        rtype_match = self.parseInfo.rtype_pat.search(line)
        if rtype_match is None:
            return HandleRes.NOT_HANDLED
        else:
            # Got an 'rtype:' spec
            
            # If there is an open parameter or return spec, finish it:
            self.finish_parameter_spec()
            self.finish_return_spec(rtype_found=True, line_no=line_num)
            
            # Have groups like this:
            #    ('       ', '{int | str}')
            # Keep the indentation before the parameter name:
            frags = rtype_match.groups()
            indent     = frags[0]
            rtype_desc = frags[1].strip()
            
            self.out_fd.write(indent + '<b>return type:</b> ' + rtype_desc + self.parseInfo.line_sep)
            return HandleRes.HANDLED

    #-------------------------
    # check_raises_spec 
    #--------------
    
    def check_raises_spec(self, line, line_num):
        '''
        Handle :raises and @raises.
        
        @param line: line to check for directive
        @type line: str
        @param line_num: line number in original HTML file. Used for error msgs.
        @type line_num: int
        @returns whether the given line was handled and output,
            or nothing was done.
        @rtype HandleRes
        '''

        raises_match = self.parseInfo.raises_pat.search(line)
        if raises_match is None:
            return HandleRes.NOT_HANDLED
        else:
            # Got an 'rtype:' spec
            
            # If there is an open parameter spec, finish it:
            self.finish_parameter_spec()
            
            # Have groups like this:
            #    ('       ', 'ValueError')
            # Keep the indentation before the parameter name:
            frags = raises_match.groups()
            indent    = frags[0]
            raises_desc = frags[1].strip()
            
            self.out_fd.write(indent + '<b>raises:</b> ' + raises_desc + self.parseInfo.line_sep)
            return HandleRes.HANDLED
    
    #-------------------------
    # finish_parameter_spec 
    #--------------
    
    def finish_parameter_spec(self, type_found=False, line_no=None):
        '''
        If a parameter spec is being constructed, finish it. If
        no parameter spec is being constructed, do nothing. If
        type_found is False, and client has indicated force_type_spec
        when instantiating this object, an error is raised.
        
        Parameters specs are closed adding a line separator if
        non is already part of the param_desc part of curr_parm_match.  
        
        @param type_found: whether a type specification was found
        @type type_found: bool
        @param line_no: line in which parameter spec was found. Used
            in error messages.
        @type line_no: int
        @raised NoTypeError
        '''
        
        if self.curr_parm_match is None:
            return
        
        (parm_name, parm_desc) = self.curr_parm_match
        # We are to enforce type specs then ensure that
        # we have a type:
        if self.force_type_spec and not type_found:
            self.error_notify('No type spec found for parameter %s at line %s' %\
                              (parm_name, line_no), NoTypeError
                              )
        self.out_fd.write(parm_desc)
        if not parm_desc.endswith(self.parseInfo.line_sep):
            self.out_fd.write(self.parseInfo.line_sep)

        self.curr_parm_match = None

    #-------------------------
    # append_to_parm_desc 
    #--------------
    
    def append_to_parm_desc(self, line):
        '''
        Assuming that we are currently processing a
        parameter spec, append line to the parameter description.
        We assume that self.curr_parm_match is a tuple:
        (parm_name, parm_desc).
        
        Surrounding white space in line is removed.
        
        @param line: text to add
        @type line: str
        '''
        (_parm_name, parm_desc) = self.curr_parm_match
        self.curr_parm_match = (_parm_name, parm_desc + ' ' + line.strip())

    #-------------------------
    # append_to_return_desc 
    #--------------
    
    def append_to_return_desc(self, line):
        '''
        Assuming that we are currently processing a
        return spec, append line to the return description.
        We assume that self.curr_return_desc is a string!
        
        Surrounding white space in line is removed.
        
        @param line: text to add
        @type line: str
        '''
        self.curr_return_desc += ' ' + line.strip()
     

    #-------------------------
    # finish_return_spec 
    #--------------
    
    def finish_return_spec(self, rtype_found=False, line_no=None):
        '''
        If a return spec is being constructed, finish it. If
        no return spec is being constructed, do nothing.
        
        Return specs are closed adding a line separator if
        non is already part of the return_desc part of curr_return_desc.  
        
        @param rtype_found: whether a type specification was found
        @type rtype_found: bool        
        @param line_no: line in which parameter spec was found. Used
            in error messages.
        @type line_no: int
        '''
        
        if self.curr_return_desc is None:
            return
        
        # We are to enforce type specs then ensure that
        # we have an rtype:
        if self.force_type_spec and not rtype_found:
            self.error_notify('No return type (rtype spec) found by line %s' %\
                              (line_no), NoTypeError
                              )
        
        self.out_fd.write(self.curr_return_desc)
        if not self.curr_return_desc.endswith(self.parseInfo.line_sep):
            self.out_fd.write(self.parseInfo.line_sep)

        self.curr_return_desc = None

    #-------------------------
    # is_blank_line 
    #--------------
    
    def is_blank_line(self, line ):
        
        return self.parseInfo.line_blank_pat.search(line) is not None        


    #-------------------------
    # write_out 
    #--------------
                    
    def write_out(self, txt, nl=True):
        self.out_fd.write(txt + '\n' if nl else '')
            
    #-------------------------
    # error_notify 
    #--------------
    
    def error_notify(self, msg, error_inst):
        '''
        Handles either raising error, printing
        warning to stderr, or staying silent. All
        controlled by parameters to constructor.
        
        @param msg: msg to use for error msg or warning
        @type msg: str
        @param error_inst: instance of error to raise. Only needed
            if raise_errors is True in the constructor call.
        @type error_inst: Exception
        '''
        if self.raise_errors:
            raise error_inst(msg)
        elif self.warnings:
            sys.stderr.write("****Warning: " + msg + '\n')
        else:
            # No notification
            pass
    
        
if __name__ == '__main__':

    # A couple of test cases, though test_pdoc_prep.py unittests
    # is the way to test.
    
#     with open(os.path.join(os.path.dirname(__file__), 'test_doc.py'), 'r') as fd:
#         PdocPrep(fd, delimiter_char=':')
#     sys.exit()
    
    # For testing: create preprocessed file from this file:
#     with open(os.path.join(os.path.dirname(__file__), 'pdoc_prep.py'), 'r') as fd:
#         PdocPrep(fd)
#     sys.exit()
        
    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     description="Preprocess Python module for use with pdoc tool."
                                     )

    parser.add_argument('-f', '--file',
                        help='fully qualified path to Python module. Default: stdin',
                        default=None)
    parser.add_argument('-o', '--outfile',
                        help='fully qualified path to output file. Default: stdout',
                        default=None)                        
    parser.add_argument('-d', '--delimiter',
                        help="One of '@' and ':', which precede the parameter/return/rtyp specs in your module. Default: '@'",
                        default='@')
    parser.add_argument('-t', '--typecheck',
                        help="If present, require a 'type' spec for each parameter, and an 'rtype' for each return. Default: False",
                        default=False)

    args = parser.parse_args();
    
    try:
        if args.file is None:
            in_fd = sys.stdin
        else:
            in_fd = open(args.file, 'r')
            
        if args.outfile is None:
            out_fd = sys.stdout
        else:
            out_fd = open(args.outfile, 'w')
            
        
        PdocPrep(in_fd=in_fd, 
                 out_fd=out_fd,
                 delimiter_char=args.delimiter,
                 force_type_spec=args.typecheck)
    finally:
        if in_fd != sys.stdin:
            in_fd.close()
        if out_fd != sys.stdout:
            out_fd.close()
    
    
    