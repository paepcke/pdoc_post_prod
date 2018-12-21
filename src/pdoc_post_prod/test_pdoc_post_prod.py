'''
Created on Dec 20, 2018

@author: paepcke
'''
from _io import StringIO
import unittest
from unittest import skipIf

from pdoc_post_prod.pdoc_post_prod import PdocPostProd 
from pdoc_post_prod.pdoc_post_prod import NoParamError, NoTypeError, ParamTypeMismatch

RUN_ALL = True
#RUN_ALL = False

class TestPdocPostProd(unittest.TestCase):

    content_good = \
    '''Foo is bar
       <span class="sd">        :param tableName: name of new table</span>
       <span class="sd">        :type tableName: String</span>
       Blue is green
       '''

    content_no_type = \
    '''Foo is bar
       <span class="sd">        :param tableName: name of new table</span>
       Blue is green
       '''
    content_no_param = \
    '''Foo is bar
       <span class="sd">        :type tableName: String</span>
       Blue is green
       '''
    
    content_param_type_mismatch = \
    '''Foo is bar
       <span class="sd">        :param tableName: name of new table</span>
       <span class="sd">        :type bluebell: String</span>
       Blue is green
       '''
    content_return_variationA = \
    '''Foo is bar
       <span class="sd">        :return a number between 1 and 10</span>
       Blue is green
       '''
    content_return_variationB = \
    '''Foo is bar
       <span class="sd">        :returns a number between 1 and 10</span>
       Blue is green
       '''
    content_return_variationC = \
    '''Foo is bar
       <span class="sd">        :return: a number between 1 and 10</span>
       Blue is green
       '''
    content_return_variationD = \
    '''Foo is bar
       <span class="sd">        :returns: a number between 1 and 10</span>
       Blue is green
       '''
    content_rtype_variationA = \
    '''Foo is bar
       <span class="sd">        :rtype {int | str}</span>
       Blue is green
       '''
    content_rtype_variationB = \
    '''Foo is bar
       <span class="sd">        :rtype: {int | str}</span>
       Blue is green
       '''    
    
    content_raises_variationA = \
    '''Foo is bar
       <span class="sd">        :raises ValueError</span>
       Blue is green
       '''
    content_raises_variationB = \
    '''Foo is bar
       <span class="sd">        :raises: ValueError</span>
       Blue is green
       '''    
    
    
    
    
    #-------------------------
    # setUp 
    #--------------

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.capture_stream = StringIO()

    #-------------------------
    # testParamAndTypeAllOK
    #--------------

    @skipIf(not RUN_ALL, 'Temporarily disabled')
    def testParamAndTypeAllOK(self):
        in_stream      = StringIO(TestPdocPostProd.content_good)
        PdocPostProd(in_stream, self.capture_stream)
        
        res = self.capture_stream.getvalue()
        expected = 'Foo is bar\n' +\
                   '<span class="sd">        <b>tableName(<i>String</i>):</b> name of new table</span>\n' +\
                   'Blue is green'
        self.assertEqual(res.strip(), expected)
    
    #-------------------------
    # testParamWithTypeMissing 
    #--------------
        
    @skipIf(not RUN_ALL, 'Temporarily disabled')
    def testParamWithTypeMissing(self):
        in_stream = StringIO(TestPdocPostProd.content_no_type)
        with self.assertRaises(NoTypeError):
            PdocPostProd(in_stream, self.capture_stream)

    #-------------------------
    # testTypeWithParamMissing 
    #--------------

    @skipIf(not RUN_ALL, 'Temporarily disabled')
    def testTypeWithParamMissing(self):
        in_stream = StringIO(TestPdocPostProd.content_no_param)
        with self.assertRaises(NoParamError):
            PdocPostProd(in_stream, self.capture_stream)
        
    #-------------------------
    # testParamTypeMismatch 
    #--------------
        
    @skipIf(not RUN_ALL, 'Temporarily disabled')        
    def testParamTypeMismatch(self):
        in_stream = StringIO(TestPdocPostProd.content_param_type_mismatch)
        with self.assertRaises(ParamTypeMismatch):
            PdocPostProd(in_stream, self.capture_stream)
        
    #-------------------------
    # testReturnSpec 
    #--------------
    
    @skipIf(not RUN_ALL, 'Temporarily disabled')
    def testReturnSpec(self):
        for _input in [TestPdocPostProd.content_return_variationA,
                       TestPdocPostProd.content_return_variationB,
                       TestPdocPostProd.content_return_variationC,
                       TestPdocPostProd.content_return_variationD
                       ]:
            in_stream      = StringIO(_input)
            PdocPostProd(in_stream, self.capture_stream)
            
            res = self.capture_stream.getvalue()
            expected = 'Foo is bar\n' +\
                       '<span class="sd">        <b>returns:</b> a number between 1 and 10</span>\n' +\
                       'Blue is green'
            self.assertEqual(res.strip(), expected)
            # Make a new capture stream so the old
            # content won't confuse us on the next loop:
            self.capture_stream = StringIO()
        
    #-------------------------
    # testRtypeSpec 
    #--------------
    
    @skipIf(not RUN_ALL, 'Temporarily disabled')
    def testRtypeSpec(self):
        for _input in [TestPdocPostProd.content_rtype_variationA,
                       TestPdocPostProd.content_rtype_variationB
                       ]:
            in_stream      = StringIO(_input)
            PdocPostProd(in_stream, self.capture_stream)
            
            res = self.capture_stream.getvalue()
            expected = 'Foo is bar\n' +\
                       '<span class="sd">        <b>return type:</b> {int | str}</span>\n' +\
                       'Blue is green'
            self.assertEqual(res.strip(), expected)
            # Make a new capture stream so the old
            # content won't confuse us on the next loop:
            self.capture_stream = StringIO()
        
    @skipIf(not RUN_ALL, 'Temporarily disabled')
    def testRaisesSpec(self):
        for _input in [TestPdocPostProd.content_raises_variationA,
                       TestPdocPostProd.content_raises_variationB
                       ]:
            in_stream      = StringIO(_input)
            PdocPostProd(in_stream, self.capture_stream)
            
            res = self.capture_stream.getvalue()
            expected = 'Foo is bar\n' +\
                       '<span class="sd">        <b>raises:</b> ValueError</span>\n' +\
                       'Blue is green'
            self.assertEqual(res.strip(), expected)
            # Make a new capture stream so the old
            # content won't confuse us on the next loop:
            self.capture_stream = StringIO()
        
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test']
    unittest.main()