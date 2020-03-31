# -*- coding:utf-8 -*-


"""
This module contains a simple test that always passes.
It can be useful to make sure that the testing facilities
are working.
"""


import unittest


class Tautology(unittest.TestCase):
    """
    Contains a simple test that always passes
    """

    def test_tautology(self) -> None:
        """
        A  simple test that always passes
        """
        self.assertTrue(True)
