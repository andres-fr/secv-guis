# -*- coding:utf-8 -*-


"""
This module contains helper functions and utilities that may be used anywhere
else in the project.
"""


import os
import itertools
from pathlib import Path
#
import numpy as np
import randomcolor
from PIL import Image
import exifread
from PySide2 import QtGui


# #############################################################################
# ##
# #############################################################################
class RandomColorGenerator(randomcolor.RandomColor):
    """
    Flexible generator for nice random colors. For more details check
    https://pypi.org/project/randomcolor/

    Usage example::
      r, g, b = next(RandomColorGenerator().generate(form="rgbArray"))
    """

    def generate(self, hue=None, luminosity=None, count=1, form="rgbArray"):
        """
        :param form: Popular ones: ``rgbArray, rgba, hex, rgb``
        :returns: A generator with ``count`` random colors.

        Overriden to return a generator instead of a list. Source:
          https://github.com/kevinwuhoo/randomcolor-py
        """
        for _ in range(count):
            # First we pick a hue (H)
            H = self.pick_hue(hue)
            # Then use H to determine saturation (S)
            S = self.pick_saturation(H, hue, luminosity)
            # Then use S and H to determine brightness (B).
            B = self.pick_brightness(H, S, luminosity)
            # Then we return the HSB color in the desired format
            yield self.set_format([H, S, B], form)


def unique_filename(path, suffix="_({})", max_iters=10000):
    """
    Given a path, returns the same path if unique, or adds ``(N)`` before the
    extension to make it unique, for ``N`` being the lowest integer possible
    starting from 1.
    """
    if not Path(path).is_file():
        return path
    else:
        prefix, ext = os.path.splitext(path)
        for i in itertools.count(start=1, step=1):
            p = prefix + suffix.format(i) + ext
            if not Path(p).is_file():
                return p
            assert i < max_iters, "max no. of iters reached!"


# #############################################################################
# ## NUMPY <-> QT_PIXMAP INTERFACING
# #############################################################################
def rgb_arr_to_rgb_pixmap(arr):
    """
    :param arr: Expects a ``np.uint8(h, w, 3)`` array.
    :returns: A ``QtGui.QPixmap`` in format ``RGB888(w, h)``.
    """
    h, w, c = arr.shape
    assert c == 3, "Only np.uint8 arrays of shape (h, w, 3) expected!"
    img = QtGui.QImage(arr.data, w, h,
                       arr.strides[0], QtGui.QImage.Format_RGB888)
    pm = QtGui.QPixmap.fromImage(img)
    return pm


def bool_arr_to_rgba_pixmap(arr, rgba=(255, 0, 0, 255)):
    """
    :param arr: Expects a ``np.bool(h, w)`` array.
    :param rgba: 4 values between 0 and 255. Alpha=255 means full opacity.
    :returns: A ``QtGui.QPixmap`` in format ``RGBA8888(w, h)``, where the
      ``false`` values are all zeros and the ``true`` values have the specified
      ``rgba`` color.
    """
    # When painting ``(r, g, b, 0)`` Qt actually paints ``(0, 0, 0, 0)``. The
    # workaround of inverting all pixel values before and after painting
    # didn't work... TODO
    # forum.qt.io/topic/73787/qimage-qpixmal-loses-alpha-color-when-drawing/5
    # also topic/88000/qpainter-loosing-color-of-transparent-pixels-critical
    assert rgba[-1] > 0, "Alpha can't be zero, Qt will delete all :("
    h, w = arr.shape
    marr = np.zeros((h, w, 4), dtype=np.uint8)
    y_idxs, x_idxs = np.where(arr)
    marr[y_idxs, x_idxs] = rgba
    # HERE WOULD COME THE BUGFIX: try harder the "invert colors" approach?
    #
    img = QtGui.QImage(marr.data, w, h, marr.strides[0],
                       QtGui.QImage.Format_RGBA8888)
    #
    pm = QtGui.QPixmap.fromImage(img)
    return pm


def pixmap_to_arr(pm, img_format=QtGui.QImage.Format_RGBA8888):
    """
    :param pm: A Pixmap to be converted
    :param img_format: The ``QtGui.QImage`` format that ``pm`` corresponds to.
      https://doc.qt.io/qtforpython/PySide2/QtGui/QImage.html#image-formats
    :returns: A ``np.uint8(h, w, C)`` array, where the number of channels ``C``
      depends on the image format.

    ..note::
      Pixmaps are in format (w, h, ...) but arrays are returned
      in ``(h, w, ...)``, as usual for numpy
    """
    img = pm.toImage().convertToFormat(img_format)
    w, h = img.size().toTuple()
    arr = np.array(img.constBits()).reshape(h, w, -1)
    return arr


# #############################################################################
# ## IMAGE I/O
# #############################################################################
def load_exif(img_path):
    """
    :returns: A dictionary with the EXIF data contained at ``img_path``.
    """
    with open(img_path, "rb") as f:
        exif_dict = exifread.process_file(f)
        return exif_dict


def load_img_and_exif(img_path: str, as_np_array=True,
                      ignore_alpha=True):
    """
    Loads the image at given path using PIL, and its EXIF data. If the EXIF
    data contains extra info about orientation, also rotates the image
    accordingly.

    :param as_np_array: If true, the image will be converted from PIL format
      to np via ``np.asarray(image)``
    :param ignore_alpha: If the type of the image is ``RGBA``, it will be
      converted to ``RGB``.

    :returns: A tuple ``(image, exif_dict)``.

    Inspired in https://stackoverflow.com/a/26928142
    """
    exif_dict = load_exif(img_path)
    image = Image.open(img_path)
    if ignore_alpha and image.mode == "RGBA":
        image = image.convert("RGB")

    # Img orientation seems to have tag 274
    try:
        orientation: int = exif_dict["Image Orientation"].values[0]
        if orientation == 3:
            image = image.rotate(180, expand=True)
        elif orientation == 6:
            image = image.rotate(270, expand=True)
        elif orientation == 8:
            image = image.rotate(90, expand=True)
    except KeyError:
        pass
    if as_np_array:
        image = np.asarray(image)
    return image, exif_dict
