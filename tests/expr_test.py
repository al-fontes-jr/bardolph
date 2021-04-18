#!/usr/bin/env python

import logging
from logging import handlers
import unittest

from bardolph.vm.vm_codes import Register

from tests import test_module
from tests.script_runner import ScriptRunner


class ExprTest(unittest.TestCase):
    def setUp(self):
        test_module.configure()
        self._runner = ScriptRunner(self)

    def _verify_vars(self, *pairs):
        it = iter(pairs)
        for pair in it:
            self._runner.assert_var_equal(pair, next(it))

    def test_cmp_and(self):
        script = """
            hue 0
            if {1 <= 2 and not 3 < 4}
                assign x 5
            else
                assign x 6
            hue x
        """
        self._runner.run_script(script)
        self._runner.assert_reg_equal(Register.HUE, 6)
        self._runner.assert_var_equal('x', 6)

    def test_prec(self):
        script = """
            assign a {12 + 3 * 4}
            assign b {15 - 4 / 2}
            assign c {5 + 6^3*2}
            assign d {2 ^ 1 + 6}
            assign e {2 ^ (1 + 6)}
        """
        self._runner.run_script(script)
        self._verify_vars('a', 24, 'b', 13, 'c', 437, 'd', 8, 'e', 128)

    def test_and_or_prec(self):
        script = """
            assign a 20
            assign b 0
            assign c 0
            if {5 > 1 or 10 < 100 and a == 30 } assign b 1
            if {(5 > 1 or 10 < 100) and a == 30 } assign c 1
        """
        self._runner.run_script(script)
        self._verify_vars('b', 1, 'c', 0)

    def test_paren(self):
        script = """
            assign a {(12 + 3) * 4}
            assign b {(16 - 4) / 2}
            assign c {(5 + 6)^3*2}
        """
        self._runner.run_script(script)
        self._verify_vars('a', 60, 'b', 6, 'c', 2662)

    def test_nested_paren(self):
        script = """
            assign a {(12 + (3*4)) * (4 + 5)}
            assign b {(16 - 4) / ((2))}
            assign c {(5 + 6)^((3)*2)}
        """
        self._runner.run_script(script)
        self._verify_vars('a', 216, 'b', 6, 'c', 1771561)

    def test_unary(self):
        script = """
            assign a {2-2 + -3 - -4}
            assign b {-(35 - 7)}
            assign c {+(-100 + 45)}
            assign d {-1 * -1}
            assign e {-2.0^-3}
            assign f {-2.0^+3}
        """
        self._runner.run_script(script)
        self._verify_vars(
            'a', 1, 'b', -28, 'c', -55, 'd', 1, 'e', -0.125, 'f', -8.0)

    def test_var_reference(self):
        script = """
            assign a 25
            assign b 3
            assign c {a * 2 + 180 / b}
        """
        self._runner.run_script(script)
        self._verify_vars('c', 110)

    def test_divide_by_zero(self):
        memory_handler = handlers.MemoryHandler(256)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(memory_handler)

        script = """
            assign a {1 / 0}
        """
        self._runner.run_script(script)
        self.assertTrue('division by zero' in memory_handler.buffer[0].msg)


if __name__ == '__main__':
    unittest.main()
