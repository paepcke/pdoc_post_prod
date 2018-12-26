#!/usr/bin/env python
'''
Created on Dec 25, 2018

@author: paepcke
'''
import argparse
import os
import subprocess
import sys
import tempfile

from pdoc_prep import PdocPrep


class PdocRunner(object):
    
    def __init__(self, pdoc_prep_args, pdoc_arg_list):

        # The python module to process:
        python_module = pdoc_prep_args['python_module']
        if not os.path.exists(python_module):
            raise ValueError("Python module %s does not exist." % python_module)
        
        python_module_dir    = os.path.dirname(python_module)
        if pdoc_arg_list is None:
            pdoc_arg_list = []
        
        # Temp file for the output of preprodcessing:
        prepped_module_file  = tempfile.NamedTemporaryFile(prefix='tmp_pdoc_prep_',
                                                           suffix='.py',
                                                           dir=python_module_dir,
                                                           mode='w',
                                                           encoding='utf-8'
                                                           )
        with open(python_module, 'r') as python_module_fd:
            with open(prepped_module_file.name, 'w') as out_fd:
                # Create temporary file with the necessary HTML transformations:
                pdoc_prepper = PdocPrep(python_module_fd,
                                        out_fd=out_fd,
                                        delimiter_char=pdoc_prep_args['delimiter'],
                                        force_type_spec=pdoc_prep_args['typecheck'],
                                        )
        
        # Prepare the argument list for pdoc:
        
        # Ensure that either caller specified an html target dir.
        # If not, we specify it as the python module's dir (which is
        # pdoc's default)
        (html_out_dir, pdoc_arg_list) = self.ensure_html_dir_spec(pdoc_arg_list, python_module_dir)
        
        # Ensure presence of --html option in call to pdoc:
        try:
            pdoc_arg_list.index('--html')
        except ValueError:
            # No --html specified; add it at the front:
            pdoc_arg_list.insert(0, '--html')
            
        # Run pdoc over the transformed file:
        
        pdoc_args = self.modify_module_to_pdoc(pdoc_arg_list, prepped_module_file.name)

        # Get a CompletedProcess instance from running pdoc:
        cmd_res = subprocess.run(['pdoc'] + pdoc_args)
        if cmd_res.returncode != 0:
            print("Error during pdoc run; quitting.")
            sys.exit()
        
        # Now rename pdoc's output file to be the module name
        # with the .m. added: foo.py ==> foo.m.html. The current
        # name reflects the temp name:
        
        html_output_name = self.tmp_module_name
        #os.rename(os.path.join(html_out_dir,                               ) 

        
        
    #-------------------------
    # ensure_html_dir_spec 
    #--------------

        
    def ensure_html_dir_spec(self, pdoc_arg_list, python_module_dir):

        try:
            html_out_dir_pos = pdoc_arg_list.index('--html-dir')
            html_out_dir     = pdoc_arg_list[html_out_dir_pos + 1]
        except ValueError:
            # No html out dir specified for pdoc. No problem,
            # make it same dir as the python module being documented:
            html_out_dir = python_module_dir
            pdoc_arg_list = pdoc_arg_list + ['--html-dir', html_out_dir]
        except IndexError:
            # A pdoc --html-dir option without a subsequent
            # value for the option:
            raise ValueError("Specified option --html-dir without a value.")
        
        return (html_out_dir, pdoc_arg_list)
    
    
    #-------------------------
    # modify_module_to_pdoc 
    #--------------
    
    def modify_module_to_pdoc(self, pdoc_arg_list, tmp_module_name):
        
        pdoc_arg_list = pdoc_arg_list + [tmp_module_name]
        
        # The following commented code attempts to guess whether
        # CLI contained an 'ident_name' as the last parameter, 
        # *in addition to* a repeat of the module name to be documented.
        # But giving up on this for now. 
        
#         indx_arg_list = [(indx, arg) for (indx, arg) in enumerate(pdoc_arg_list) if arg.endswith('.py')]
#         if len(indx_arg_list) == 0:
#             # The python module was only provided in the args
#             # for this method. That's fine. Splice it in before
#             # a possible 'ident_name' argument in the pdoc part of the cmd:
#             if len(pdoc_arg_list) == 0:
#                 pdoc_arg_list = [tmp_module_name]
#             else:
#                 # Is the last pdoc arg an option? If so, put
#                 # the module name right after it. Else the last
#                 # arg is an ident_name, and we have to put the 
#                 # module name just before it.
#                 if pdoc_arg_list[-1].startswith('-'):
#                     pdoc_arg_list.append(tmp_module_name)
#                 else:
#                     # An existing indent_name:
#                     pdoc_arg_list = pdoc_arg_list[0:-1].extend([tmp_module_name,pdoc_arg_list[-1]])

        return pdoc_arg_list
    
    #-------------------------
    # tmp_html_name 
    #--------------
    
    def tmp_html_name(self, python_module_name):
        return python_module_name[0:-3] + '.m' + '.html'
        
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     description="Preprocess Python module for use with pdoc tool, then runs pdoc."
                                     )

    parser.add_argument('-d', '--delimiter',
                        help="One of '@' and ':', which precede the parameter/return/rtyp \n" +\
                             "specs in your module. Default: '@'",
                        default='@')
    parser.add_argument('-t', '--typecheck',
                        help="If present, require a 'type' spec for each parameter, \n" +\
                                "and an 'rtype' for each return. Default: False",
                        default=False)
    parser.add_argument('python_module',
                        help='fully qualified path of Python module to be documented.',
                        )

    # Use parse_known_args() to get the pdoc args-to-be
    # into a list, and the pdoc_prep args into a namespace:
    (args_namespace, pdoc_arg_list) = parser.parse_known_args();
    
    # Turn the args intended for pdoc_prep into a dict:
    pdoc_prep_args = vars(args_namespace)

    if pdoc_arg_list is None:
        pdoc_arg_list = []
    
    PdocRunner(pdoc_prep_args, pdoc_arg_list)