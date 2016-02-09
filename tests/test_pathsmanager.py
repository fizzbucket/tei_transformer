import unittest
from unittest import mock
import os

from tei_transformer import pathsmanager

class TestPathManager(unittest.TestCase):
    pass

class TestBasePaths(unittest.TestCase):

    rpath = os.path.join(os.curdir, pathsmanager.RESOURCEDIR_NAME)
    wpath = os.path.join(os.curdir, pathsmanager.WORKDIR_NAME)

    @classmethod
    def setUpClass(cls):
        os.mkdir(cls.rpath)
        os.mkdir(cls.wpath)

    @classmethod
    def tearDownClass(cls):
        os.rmdir(cls.rpath)
        os.rmdir(cls.wpath)

    def setUp(self):
        pass
    
    def test_pathsexist(self):
        pass

    def test_textexists(self):
        pass

    def test_latexexists(self):
        pass


class TestFilePathsManager(unittest.TestCase):
    pass

class TestFilesReader(unittest.TestCase):
    pass

class TestLatexTransformRequires(unittest.TestCase):
    pass