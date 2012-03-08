import unittest

import sys; sys.path.append('..')
from conf_reader import read_yaml_conf
from __exceptions import ConfigurationError


class TestConfReader(unittest.TestCase):
    def setUp(self):
        self.reader = {'type' : 'stdin'}
        self.writer = {'type' : 'stdout'}
        self.base = {'specs': [], 'conf' : []}
        self.base['conf'] = [{'reader' : self.reader,
                             'writer' : self.writer}]

    def tearDown(self):
        # back with initial stage
        self.setUp()

    def test_raise_exception_if_checkpoint_path_is_missing(self):
        self.reader['checkpoint_enabled'] = True
        self.reader['type'] = 'stdin'
        self.writer['type'] = 'stdout'
        self.writer['checkpoint_enabled'] = True
        self.assertRaises(ConfigurationError, read_yaml_conf, (self.base))

    def test_raise_exception_if_conf_is_empty(self):
        self.base['conf'] = None
        self.assertRaises(ConfigurationError, read_yaml_conf, (self.base))

    def test_raise_exception_if_blockable_and_periodic_at_the_same_time(self):
        self.reader['blockable'] = True
        self.reader['period'] = 1

        self.writer['blockable'] = True
        self.writer['period'] = 1
        self.assertRaises(ConfigurationError, read_yaml_conf, (self.base))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestConfReader))
    return suite


if __name__ == '__main__':
    unittest.main()
