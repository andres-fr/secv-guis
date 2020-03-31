# -*- coding:utf-8 -*-


"""
"""


import unittest
from PySide2 import QtGui
from secv_guis.bimask_app.main_window import MainWindow


class BasicMainWindowTestCase(unittest.TestCase):
    """
    """
    def setUp(self):
        """
        """
        self.mw = MainWindow()

    def test_keymaps(self) -> None:
        """
        """
        for k, v in self.mw.keymaps().items():
            self.assertIsInstance(k, str)
            self.assertIsInstance(v, QtGui.QKeySequence)
