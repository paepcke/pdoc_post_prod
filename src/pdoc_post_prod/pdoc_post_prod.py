#!/usr/bin/env python
'''
Created on Dec 18, 2018

Post production upgrade of HTML output from the pdoc
Python documentation tool (https://pypi.org/project/pdoc/).

The pdoc HTML output does not consider function/method
parameter and return specifications in doc stringts as special.
This tool can be used as a filter that modifies the HTML produced
by pdoc to provide that special treatment.
 
    Usage: cat myPdocHtmlOut.html | pdoc_post_prod.py > new myPdocHtmlOut.html
    
Note: it would be more sensible to include this functionality in
the pdoc HTML production code itself. 
     
@author: paepcke
'''
import re
import sys

# ---------------------------------- Special Exception and Enums -----------------
class NoTypeError(Exception):
    pass
class NoParamError(Exception):
    pass
class ParamTypeMismatch(Exception):
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

        if delimiter_char not in [':', '@']:
            raise ValueError("Delimiter char must be one of ':' or '@'.")
                    
        self.span_open    = '<span class="sd">        '
        self.span_close   = '</span>'
        
        if delimiter_char == ':':
            self.parm_markers = [':param', ':type', ':return', ':rtype', ':raises']
        elif delimiter_char == '@':
            self.parm_markers = ['@param', '@type', '@return', '@rtype', '@raises']
        
        if delimiter_char == ':':
            # Find <span class="sd">     :param myParm: meaning of my parm</span>
            self.param_pat    = re.compile('<span class="sd">[ ]*:param([^:]*):([^<]*)</span>$')
            # Find <span class="sd">     :type myParm: int</span>
            self.type_pat     = re.compile('<span class="sd">[ ]*:type([^:]*):([^<]*)</span>$')
            # Be forgiving; accept ':return ', ':return:', ':returns ', and ':returns:' 
            self.return_pat   = re.compile('<span class="sd">[ ]*:return[s]{0,1}[:| ]([^<]*)</span>$')
            # Find <span class="sd">     :rtype int</span> and allow an optional colon after the 'rtype':
            self.rtype_pat    = re.compile('<span class="sd">[ ]*:rtype[:| ]([^<]*)</span>$')
            # Find <span class="sd">     :raises ValueError</span> and allow an optional colon after the 'raises':              
            self.raises_pat   = re.compile('<span class="sd">[ ]*:raises[:| ]([^<]*)</span>$')
        else:
            # Same, but using '@' as the delimiter:
            self.param_pat    = re.compile('<span class="sd">[ ]*@param([^:]*):([^<]*)</span>$')
            self.type_pat     = re.compile('<span class="sd">[ ]*@type([^:]*):([^<]*)</span>$')
            # Be forgiving; accept ':return ', ':return:', ':returns ', and ':returns:' 
            self.return_pat   = re.compile('<span class="sd">[ ]*@return[s]{0,1}[:| ]([^<]*)</span>$')
            self.rtype_pat    = re.compile('<span class="sd">[ ]*@rtype[:| ]([^<]*)</span>$')
            self.raises_pat   = re.compile('<span class="sd">[ ]*@raises[:| ]([^<]*)</span>$')

# ---------------------------------- Class PdocPostProd -----------------

class PdocPostProd(object):
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
        @param: delimiter_char: starting char of a directive: ':' or '@'. Default: '@'
        @type delimiter_char: char
        '''
        
        self.out_fd = out_fd
        self.raise_errors = raise_errors
        self.warnings = warnings_on
        self.force_type_spec = force_type_spec
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
        
        try:
            # Try finding in every line each of the special directives,
            # and transform if found, alse pass through.
            for (line_num, line) in enumerate(in_fd.readlines()):
                line = line.strip()
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
                # A regular line to output. Are we in the middle of
                # a parameter specification? If so, this is likely a continuation
                # line:
                if self.curr_parm_match is not None:
                    (param_name, param_desc) = self.curr_parm_match
                    param_desc += '\n' + line +'\n'
                    self.curr_parm_match = (param_name, param_desc)
                    continue
                self.out_fd.write(line + '\n')
        finally:
            # Ensure that a possibly open parameter spec is closed:
            self.finish_parameter_spec()
            
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
                self.curr_parm_match = None
                
            parm_name = parm_match.groups()[0].strip()
            parm_desc = parm_match.groups()[1].strip()
            
            self.curr_parm_match = (parm_name, parm_desc)
            self.out_fd.write(self.parseInfo.span_open +\
                             '<b>' + parm_name + '</b> '
                             )
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
            type_name = type_match.groups()[0].strip()
            type_desc = type_match.groups()[1].strip()
            if type_name != parm_name:
                # Have a parm spec followed by a type spec,
                # but the type spec doesn't match the parameter:
                msg = "Type %s, but preceding param %s; line %s.\n" %\
                        (type_name, parm_name, line_num)
                self.error_notify(msg, ParamTypeMismatch)
                return HandleRes.NOT_HANDLED
            
            # Finally...all is good:
            self.out_fd.write('(<b></i>' + type_desc + '</i></b>): ' + \
                             parm_desc
                             )
            self.finish_parameter_spec(type_found=True, line_no=line_num)
            self.curr_parm_match = None
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
        else:
            # Got a 'return:' spec
            # If there is an open parameter spec, finish it:
            self.finish_parameter_spec()
            return_desc = return_match.groups()[0].strip()
            self.out_fd.write(self.parseInfo.span_open +\
                             '<b>returns:</b> ' + return_desc + \
                             self.parseInfo.span_close + \
                             '\n'
                              
                             )
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
            
            # If there is an open parameter spec, finish it:
            self.finish_parameter_spec()
            
            rtype_desc = rtype_match.groups()[0].strip()
            self.out_fd.write(self.parseInfo.span_open +\
                             '<b>return type:</b> ' + rtype_desc + \
                             self.parseInfo.span_close + \
                             '\n'
                             )
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
            
            raises_desc = raises_match.groups()[0].strip()
            self.out_fd.write(self.parseInfo.span_open +\
                             '<b>raises:</b> ' + raises_desc + \
                             self.parseInfo.span_close + \
                             '\n'
                             )
            return HandleRes.HANDLED
    
    #-------------------------
    # finish_parameter_spec 
    #--------------
    
    def finish_parameter_spec(self, type_found=False, line_no=None):
        
        if self.curr_parm_match is None:
            return
        
        (parm_name, parm_desc) = self.curr_parm_match
        # We are to enforce type specs then ensure that
        # we have a type:
        if self.force_type_spec and not type_found:
            self.error_notify('No type spec found for parameter %s at line %s' %\
                              (parm_name, line_no), NoTypeError
                              )
        
        # Parameter description will already have 
        # a closing '</span>\n' if its multi-line.
        # Else add that closure here: 
        if not parm_desc.endswith('</span>\n'):
            self.out_fd.write(self.parseInfo.span_close + '\n')
                          
        self.curr_parm_match = None

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
    with open('/tmp/pdoc_test.py', 'r') as fd:
        PdocPostProd(fd)
    
    
    