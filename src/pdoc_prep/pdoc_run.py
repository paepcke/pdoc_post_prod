#!/usr/bin/env python
'''
Created on Dec 25, 2018

@author: paepcke
'''
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

from pdoc_prep import PdocPrep


class PdocRunner(object):
    
    def __init__(self, pdoc_prep_args, pdoc_arg_list):

        # The python module to process:
        # CLI user may either put the python module
        # at the end of the pdoc_prep options, or at the
        # end of the line, i.e. after the pdoc options.
        
        (python_module, pymod_pos) = self.get_module_from_args(pdoc_arg_list)
        
        if not os.path.isabs(python_module):
            python_module = os.path.join(os.path.dirname(__file__), python_module)
        if not os.path.exists(python_module):
            raise ValueError("Python module %s does not exist." % python_module)
        
        python_module_dir = os.path.dirname(python_module)
        
        # Temp file for the output of preprodcessing:
        prepped_mod_name = self.create_tmp_file(python_module_dir)

        # Run the preprocessor, outputting to temp prepped-file:
        try:
            with open(python_module, 'r') as python_module_fd:
                with open(prepped_mod_name, 'w') as out_fd:
                    # Create temporary file with the necessary HTML transformations:
                    _pdoc_prepper = PdocPrep(python_module_fd,
                                             out_fd=out_fd,
                                             delimiter_char=pdoc_prep_args['delimiter'],
                                             force_type_spec=pdoc_prep_args['typecheck'],
                                             )
            
            # Prepare the argument list for pdoc:
            
            # Check whether the caller specified an html target dir.
            # If not, we specify it as the python module's dir (which is
            # pdoc's default)
            (html_out_dir, pdoc_arg_list) = self.ensure_html_dir_spec(pdoc_arg_list, python_module_dir)
            
            # Ensure presence of --html option in call to pdoc:
            try:
                pdoc_arg_list.index('--html')
            except ValueError:
                # No --html specified; add it at the front:
                pdoc_arg_list.insert(0, '--html')
                
            
            # In the pdoc argument list, replace the Python module
            # name with the preprocessed tmp file name:
            pdoc_args = self.modify_module_to_pdoc(pdoc_arg_list, prepped_mod_name, pymod_pos)
    
            # Run pdoc over the preprocessed file:
    
            # Get a CompletedProcess instance from running pdoc:
    
            pdoc_cmd = self.pdoc_path() + ' ' + ' '.join(pdoc_args)
            cmd_res = subprocess.run(pdoc_cmd, shell=True)
            if cmd_res.returncode != 0:
                print("Error during pdoc run; quitting.")
                sys.exit()
            
            # Now rename pdoc's output file to be the original module name
            # with the .m. added: foo.py ==> foo.m.html. The current
            # name reflects the temp name:
            
            html_output_name = self.derive_pdoc_out_file_name(python_module)
            html_output_path = os.path.join(html_out_dir, html_output_name)
            pdoc_res_file    = os.path.join(html_out_dir, 
                                            self.derive_pdoc_out_file_name(prepped_mod_name)
                                            )
            shutil.move(pdoc_res_file, html_output_path)
            
            # pdoc uses the python module name throughout its
            # generated HTML. Since we gave it the temp name
            # of the prepped file, those refs will all use
            # the temp file name. Fix that:
            self.replace_temp_name(python_module, html_output_path, prepped_mod_name)
            
        finally:
            if os.path.exists(prepped_mod_name):
                os.remove(prepped_mod_name)
        
        #print('done')

    #-------------------------
    # create_tmp_file 
    #--------------
    
    def create_tmp_file(self, directory):
        '''
        Given a directory, create a temp file there
        to use as destination for the preprocessed .py file.
        
        @param directory: target directory for tmp file
        @type directory: str
        @return: the full pathname of the new temp file
        @rtype str
        '''
        
        # Temp file for the output of preprodcessing:
        prepped_mod_tmp_file_obj  = tempfile.NamedTemporaryFile(prefix='tmp_pdoc_prep_',
                                                           suffix='.py',
                                                           dir=directory,
                                                           mode='w',
                                                           encoding='utf-8',
                                                           delete=False
                                                           )
        return prepped_mod_tmp_file_obj.name
        

    #-------------------------
    # derive_pdoc_out_file_name 
    #--------------
        
    def derive_pdoc_out_file_name(self, python_file_name):
        '''
        Given a path, such as /foo/bar/fum.py, return
        fum.m.py, which is the pdoc standard
        HTML module file convention
        
        @param python_file_name: full path to work with
        @type python_file_name: str
        @return modified path string
        @rtype str
        '''
        (_dir, file_name) = os.path.split(python_file_name)
        
        (name, _ext) = os.path.splitext(file_name)
        return name + '.m' + '.html'

    
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
            pdoc_arg_list = ['--html-dir', html_out_dir] + pdoc_arg_list 
        except IndexError:
            # A pdoc --html-dir option without a subsequent
            # value for the option:
            raise ValueError("Specified option --html-dir without a value.")
        
        return (html_out_dir, pdoc_arg_list)

    #-------------------------
    # get_module_from_args
    #--------------
    
    def get_module_from_args(self, pdoc_arg_list):
        '''
        # Unfortunately, pdoc has an optional positional arg
        # *after* the module name (i.e. ident_name). So, need to
        # pick out the python module name fromn the pdoc 
        # parameter list.
        #
        # Parm list could be something like:
        #    o ['--html', 'foo.py']
        # or o ['--html', 'foo.py' 'myFunc']
        #
        # In the first case return -1, in the second,
        # return -2. We spec relative to to list's end,
        # b/c args may be prepended in this list further on.
        
        @param pdoc_arg_list: list of arguments intended for pdoc
        @type pdoc_arg_list: [str]
        @return tuple with Python module to document and its position in the args list
        @rtype (str,int)
        @raise ValueError
        '''
        
        if pdoc_arg_list is None or len(pdoc_arg_list) == 0:
            raise ValueError("Missing name of Python module to document.")
        
        if pdoc_arg_list[-1].endswith('.py'):
            return (pdoc_arg_list[-1], -1)
        
        # Must have been given pdoc args with a trailing ident_name:
        if len(pdoc_arg_list) < 2:
            raise ValueError("Missing name of Python module to document (no arg with '.py' extension).")
        
        return (pdoc_arg_list[-2], -2)
    
    #-------------------------
    # pdoc_path 
    #--------------

    def pdoc_path(self):
        '''
        When debugging in Eclipse the PATH variable
        is not set to what it would be in a shell.
        When using subprocess.run(..., shell=True) the
        proper path is not set either. So the pdoc
        executable won't be found, even though it
        will be when this script is run in a shell.
        
        A clumsy workaround: In the Eclipse run/debug
        configuration Environment tab, create a variable
        like PDOC_PATH.
        
        '''
        provided_path = os.getenv('PDOC_PATH')
        return 'pdoc' if provided_path is None else provided_path 
    
    
    #-------------------------
    # modify_module_to_pdoc 
    #--------------
    
    def modify_module_to_pdoc(self, pdoc_arg_list, tmp_module_name, mod_name_pos):
        
        pdoc_arg_list[mod_name_pos] = tmp_module_name
        return pdoc_arg_list
    
    #-------------------------
    # tmp_html_name 
    #--------------
    
    def tmp_html_name(self, python_module_name):
        return python_module_name[0:-3] + '.m' + '.html'


    #-------------------------
    # replace_temp_name 
    #--------------
    
    def replace_temp_name(self, python_module, html_output_path, prepped_mod_name):
        '''
        Given the path to the intermediate (i.e. prepped) file,
        and the path to the final html file, purge uses of the
        temp file name from the html.
        
        Ex.: assuming the temp file name was tmp_pdoc_prep_g3g5hxni.py,
             and the original python module was test_doc.py, 
             the pdoc output html will contain lines like:

            <span class="class_name"><a href="#tmp_pdoc_prep_g3g5hxni.Foo">Foo</a></span>
            
        We replace lines like that to be:
        
            <span class="class_name"><a href="#test_doc.Foo">Foo</a></span>
        
        @param python_module path to original module that was to be documented
        @type python_module str
        @param html_output_path: path to final html file
        @type html_output_path: str
        @param prepped_mod_name: path to the intermediate file
        @type prepped_mod_name: str
        '''
        # Extract the root of the original python module, i.e.
        # 'test_doc' in the example above:
        (_orig_dir, orig_basename) = os.path.split(python_module)
        (orig_root, _ext) = os.path.splitext(orig_basename)
        
        # Same for the intermediate file name:
        (_prepped_dir, prepped_basename) = os.path.split(prepped_mod_name)
        (prepped_mod_root, _ext) = os.path.splitext(prepped_basename)
        
        pat = re.compile(prepped_mod_root)
        with open(html_output_path, 'r') as in_fd:
            content = in_fd.read()
            cleaned_content = pat.sub(orig_root, content)
            
        with open(html_output_path, 'w') as out_fd:
            out_fd.write(cleaned_content)
        


#------------------------- Main -------------------
        
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
                        action='store_true',
                        help="If present, require a 'type' spec for each parameter, \n" +\
                                "and an 'rtype' for each return. Default: False",
                        default=False)
    
    # We'll check for hte module name presence separately below:
#     parser.add_argument('python_module',
#                         help='fully qualified path of Python module to be documented.',
#                         )

    # Use parse_known_args() to get the pdoc args-to-be
    # into a list, and the pdoc_prep args into a namespace:
    (args_namespace, pdoc_arg_list) = parser.parse_known_args();
    
    # Turn the args intended for pdoc_prep into a dict:
    pdoc_prep_args = vars(args_namespace)

    PdocRunner(pdoc_prep_args, pdoc_arg_list)