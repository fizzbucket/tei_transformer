import unittest
from unittest import mock
import os
import shutil

import random
import string

from tei_transformer import pathsmanager

PM = pathsmanager.PathManager


class TestPathManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.testdir = os.path.join(os.curdir, 'pathstesting')
        os.mkdir(cls.testdir)
        cls.inputpath = os.path.join(cls.testdir, 'hello.xml')
        with open(cls.inputpath, 'w') as o:
            o.write('Hello world.')

    def make_resourcesdir(self):
        self.rdir = os.path.join(self.testdir, pathsmanager.RESOURCEDIR_NAME)
        os.mkdir(self.rdir)

    def random_string(self):
        return ''.join([random.choice(string.printable) for n in range(25)])

    def populate_resourcesdir(self):
        pass

    def del_resourcesdir(self):
        shutil.rmtree(self.rdir)

    def test_noresourcedir(self):
        with self.assertRaises(IOError):
            PM(self.inputpath)

    def setup(self):
        self.make_resourcesdir()
        self.populate_resourcesdir()


    def test_paths(self):


    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.testdir)
