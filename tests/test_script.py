import unittest

from tei_transformer import tei_transformer_script

from unittest import mock


class TestScript(unittest.TestCase):

    def pa(self, args):
        ga = tei_transformer_script.get_args
        x = ga(args)
        return x

    @mock.patch('tei_transformer.tei_transformer_script.transform_tei')
    def ia(self, args, mock_transform):
        ga = tei_transformer_script.interpret_args
        x = ga(args)
        return mock_transform

    name_args = ['-t', 'hello.xml']
    outputname_args = ['-o', 'goodbye.pdf']
    force_args = ['-f']
    quiet_args = ['-q']
    standalone_args = ['-s']

    def _name_right(self, x):
        return x.transform == self.name_args[1]

    def _out_right(self, x):
        return x.outputname == self.outputname_args[1]

    def force_right(self, x):
        return x.force is True

    def quiet_right(self, x):
        return x.quiet is True

    def standalone_right(self, x):
        return x.standalone is True

    def all_false_but(self, x, x_attrs):
        for y in (self._name_right, self._out_right, self.force_right, self.quiet_right, self.standalone_right):
            if y == self._name_right:
                self.assertTrue(y(x))
            elif y in x_attrs:
                self.assertTrue(y(x))
            else:
                self.assertFalse(y(x))

    kwargs_dict = {
        'outname': None,
        'force': False,
        'quiet': False,
        'standalone': False,
        }

    kwargs_dict_all_true = {
        'outname': outputname_args[1],
        'force': True,
        'quiet': True,
        'standalone': True,
        }

    def called_name_only(self, x):
        x.assert_called_once_with(self.name_args[1], **self.kwargs_dict)

    def called_name_and_outputname(self, x):
        kwargs_dict = self.kwargs_dict.copy()
        kwargs_dict['outname'] = self.outputname_args[1]
        x.assert_called_once_with(self.name_args[1], **kwargs_dict)

    def called_name_and_force(self, x):
        kwargs_dict = self.kwargs_dict.copy()
        kwargs_dict['force'] = True
        x.assert_called_once_with(self.name_args[1], **kwargs_dict)


    def called_name_and_quiet(self, x):
        kwargs_dict = self.kwargs_dict.copy()
        kwargs_dict['quiet'] = True
        x.assert_called_once_with(self.name_args[1], **kwargs_dict)


    def called_name_and_standalone(self, x):
        kwargs_dict = self.kwargs_dict.copy()
        kwargs_dict['standalone'] = True
        x.assert_called_once_with(self.name_args[1], **kwargs_dict)

    def called_all_args(self, x):
        kwargs_dict = self.kwargs_dict_all_true
        x.assert_called_once_with(self.name_args[1], **kwargs_dict)


    def test_name_only(self):
        x = self.pa(self.name_args)
        self.all_false_but(x, [])
        called = self.ia(x)
        self.called_name_only(called)

    def test_outputname(self):
        x = self.pa(self.name_args + self.outputname_args)
        self.all_false_but(x, [self._out_right])
        self.called_name_and_outputname(self.ia(x))

    def test_force(self):
        x = self.pa(self.name_args + self.force_args)
        self.all_false_but(x, [self.force_right])
        self.called_name_and_force(self.ia(x))

    def test_quiet(self):
        x = self.pa(self.name_args + self.quiet_args)
        self.all_false_but(x, [self.quiet_right])
        self.called_name_and_quiet(self.ia(x))

    def test_standalone(self):
        x = self.pa(self.name_args + self.standalone_args)
        self.all_false_but(x, [self.standalone_right])
        self.called_name_and_standalone(self.ia(x))


    def all_args(self):
        all_args = self.name_args + self.outputname_args + self.force_args + self.quiet_args + self.standalone_args
        all_arg_tests = [self._name_right, self._out_right, self.force_right, self.quiet_right, self.standalone_right]
        return self.pa(all_args), all_arg_tests

    def test_all_args(self):
        y = self.all_args()
        self.all_false_but(*y)
        self.called_all_args(self.ia(y[0]))


