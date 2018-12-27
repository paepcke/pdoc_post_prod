class Foo(object):
    def __init__(self):
        self.do_something()

    def do_something(self, parm1, parm2):
        '''
        This does something.

        :param parm1: Does the first thing.
        :type parm1: str
        :param parm2: This is a thing
            with an NL in it.
        :type parm2: str
        '''
        pass

    def do_something_else(self, parm3, parm4):
        '''
        This does something.

        :param parm3: Does the first thing.
        :param parm4:  This is a thing
            with an NL in it.\n
        :returns nothing
        :rtype str
        '''
