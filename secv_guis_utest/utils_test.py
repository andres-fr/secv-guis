# -*- coding:utf-8 -*-


"""
https://docs.python.org/3/library/unittest.html#assert-methods
"""


import unittest
import numpy as np
from PySide2 import QtGui, QtWidgets
from secv_guis.utils import RandomColorGenerator
from secv_guis.utils import rgb_arr_to_rgb_pixmap, bool_arr_to_rgba_pixmap, \
    pixmap_to_arr


APP = QtWidgets.QApplication(["SECV UTEST GUI"])


class RandomColorGeneratorTestCase(unittest.TestCase):
    """
    """
    def setUp(self):
        """
        """
        self.rcg = RandomColorGenerator()

    def test_rgb_arrays(self) -> None:
        """
        """
        for r, g, b in self.rcg.generate(form="rgbArray", count=1000):
            self.assertTrue(0 <= r <= 255)
            self.assertTrue(0 <= g <= 255)
            self.assertTrue(0 <= b <= 255)
            self.assertIsInstance(r, int)
            self.assertIsInstance(g, int)
            self.assertIsInstance(b, int)


class NumpyAndPixmapTestCase(unittest.TestCase):
    """
    Test interactions between numpy arrays ans Qt Pixmaps
    """
    SHAPE = (1000, 1000, 3)

    def setUp(self):
        """
        """
        self.rgb_arr = np.random.randint(0, 256, size=self.SHAPE,
                                         dtype=np.uint8)
        self.mask = np.random.randint(0, 2, size=self.SHAPE[:2], dtype=np.bool)

    def test_rgb_array(self) -> None:
        """
        """
        rgb_pm = rgb_arr_to_rgb_pixmap(self.rgb_arr)
        re_rgb_arr = pixmap_to_arr(rgb_pm,
                                   img_format=QtGui.QImage.Format_RGB888)
        self.assertTrue((self.rgb_arr == re_rgb_arr).all())

    def test_mask_array(self) -> None:
        """
        """
        mask_pm = bool_arr_to_rgba_pixmap(self.mask, rgba=(255, 255, 255, 255))
        re_mask_arr = pixmap_to_arr(
            mask_pm, img_format=QtGui.QImage.Format_RGB888)[:, :, 0] > 0
        #
        self.assertTrue((self.mask == re_mask_arr).all())
