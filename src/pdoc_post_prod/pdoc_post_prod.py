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

# ---------------------------------- Class PdocPostProd -----------------
class PdocPostProd(object):
    '''
    Reads a pdoc-produced HTML file. Finds the 
    :param, :type, :return, :rtype, and :raises
    lines. Replaces them with HTML.
    
    :param foo: this tells about fum
    :type foo: int
    
    Is turned into: 
        <b>foo</b> (<i>int</i>): this tells about fum<br>
    '''

    span_open    = '<span class="sd">        '
    span_close   = '</span>'
    parm_markers = [':param', ':type', ':return', ':rtype', ':raises']
    param_pat    = re.compile('<span class="sd">[ ]*:param([^:]*):([^<]*)</span>$')
    type_pat     = re.compile('<span class="sd">[ ]*:type([^:]*):([^<]*)</span>$')
    # Be forgiving; accept ':return ', ':return:', ':returns ', and ':returns:' 
    return_pat   = re.compile('<span class="sd">[ ]*:return[s]{0,1}[:| ]([^<]*)</span>$')
    rtype_pat    = re.compile('<span class="sd">[ ]*:rtype[:| ]([^<]*)</span>$')
    raises_pat   = re.compile('<span class="sd">[ ]*:raises[:| ]([^<]*)</span>$')
        
    #-------------------------
    # Constructor 
    #--------------
    
    def __init__(self, 
                 in_fd=sys.stdin, 
                 out_fd=sys.stdout,
                 raise_errors=True,
                 warnings_on=True):
        '''
        
        @param in_fd:
        @type in_fd:
        @param out_fd:
        @type out_fd:
        @param raise_errors:
        @type raise_errors:
        @param warnings_on:
        @type warnings_on:
        '''
        '''
        Constructor
        '''
        self.out_fd = out_fd
        self.raise_errors = raise_errors
        self.warnings = warnings_on
        self.parse(in_fd)

    #-------------------------
    # parse 
    #--------------
        
    def parse(self, in_fd):
        
        self.curr_parm_match = None
        
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
            self.out_fd.write(line + '\n')
            
    #-------------------------
    # check_param_spec 
    #--------------
    
    def check_param_spec(self, line, line_num):
        
        parm_match = self.param_pat.search(line)
        if parm_match is None:
            return HandleRes.NOT_HANDLED
        else:
            # Got a parameter spec
            parm_name = parm_match.groups()[0].strip()
            parm_desc = parm_match.groups()[1].strip()
            self.curr_parm_match = (parm_name, parm_desc)
            self.out_fd.write(self.span_open +\
                             '<b>' + parm_name + '(<i>'
                             )
            return HandleRes.HANDLED

    #-------------------------
    # check_type_spec 
    #--------------
    
    def check_type_spec(self, line, line_num):
        
        type_match = self.type_pat.search(line)
        
        # For convenience and good error messages:
        if self.curr_parm_match is not None:
            (parm_name, parm_desc) = self.curr_parm_match
            
        # Have a prior parameter spec, but no type spec at all?
        if type_match is None and self.curr_parm_match is not None:
            # Prev line was a parameter spec, but this line is
            # not a type spec
            msg = "Parameter spec (%s) without type; line %s" % (parm_name, line_num)
            self.error_notify(msg, NoTypeError)
            self.curr_parm_match = None
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
            self.out_fd.write(type_desc + \
                             '</i>):</b> ' + \
                             parm_desc + \
                             self.span_close + \
                             '\n'
                             )
            self.curr_parm_match = None
            return HandleRes.HANDLED
        # Not a type spec, and no prior param spec:
        return HandleRes.NOT_HANDLED
        
    #-------------------------
    # check_return_spec 
    #--------------
    
    def check_return_spec(self, line, line_num):
        return_match = self.return_pat.search(line)
        if return_match is None:
            return HandleRes.NOT_HANDLED
        else:
            # Got a 'return:' spec
            return_desc = return_match.groups()[0].strip()
            self.out_fd.write(self.span_open +\
                             '<b>returns:</b> ' + return_desc + \
                             self.span_close + \
                             '\n'
                              
                             )
            return HandleRes.HANDLED
    
    #-------------------------
    # check_rtype_spec 
    #--------------
    
    def check_rtype_spec(self, line, line_num):
        
        rtype_match = self.rtype_pat.search(line)
        if rtype_match is None:
            return HandleRes.NOT_HANDLED
        else:
            # Got an 'rtype:' spec
            rtype_desc = rtype_match.groups()[0].strip()
            self.out_fd.write(self.span_open +\
                             '<b>return type:</b> ' + rtype_desc + \
                             self.span_close + \
                             '\n'
                             )
            return HandleRes.HANDLED
        

    #-------------------------
    # check_raises_spec 
    #--------------
    
    def check_raises_spec(self, line, line_num):

        raises_match = self.raises_pat.search(line)
        if raises_match is None:
            return HandleRes.NOT_HANDLED
        else:
            # Got an 'rtype:' spec
            raises_desc = raises_match.groups()[0].strip()
            self.out_fd.write(self.span_open +\
                             '<b>raises:</b> ' + raises_desc + \
                             self.span_close + \
                             '\n'
                             )
            return HandleRes.HANDLED
        
    #-------------------------
    # write_out 
    #--------------
                    
    def write_out(self, txt, nl=True):
        self.out_fd.write(txt + '\n' if nl else '')
            
    #-------------------------
    # error_notify 
    #--------------
    
    def error_notify(self, msg, error_inst):
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
    
    
    