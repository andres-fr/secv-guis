# -*- coding:utf-8 -*-


"""
This module contains the ``QGraphicsScene+QGraphicsView`` binomial, typically
used in Qt apps to display and navigate images, together with some specific
functionality to annotate.
"""


import numpy as np
from PySide2 import QtCore, QtWidgets, QtGui
#
from .utils import RandomColorGenerator, rgb_arr_to_rgb_pixmap, \
    bool_arr_to_rgba_pixmap, pixmap_to_arr
from .mouse_event_manager import MouseEventManager
from .objects import ObjectContainer


# #############################################################################
# ## SCENE (PAINT ETC)
# #############################################################################
class MaskedImageScene(QtWidgets.QGraphicsScene, ObjectContainer):
    """
    Basic area that allows to display a color image, together with a set of
    binary masks on top of it.
    """
    DEFAULT_MASK_ALPHA = 100  # 255 is opaque. Used if no colors are specified

    def __init__(self, img_arr=None, parent=None):
        """
        :param img_arr: See ``update_image``
        """
        # super().__init__(parent)
        QtWidgets.QGraphicsScene.__init__(self, parent)
        ObjectContainer.__init__(self)
        #
        self.img_pmi = None
        self.h = None
        self.w = None
        #
        self.mask_pmis = {}  # pmi_ref : (r, g, b, a)
        if img_arr is not None:
            self.update_image(img_arr)

    def update_image(self, img_arr):
        """
        Clears whole scene, and adds the given numpy array as Pixmap.

        :param img_arr: A ``np.uint8(h, w [, ?])`` array.
        """
        pm = rgb_arr_to_rgb_pixmap(img_arr)
        self.clear()
        self.img_pmi = self.addPixmap(pm)
        #
        self.h, self.w = img_arr.shape[:2]
        self.setSceneRect(0, 0, self.w, self.h)

    def num_items(self):
        """
        Number of items in this scene, ordered from foreground to background.
        """
        return len(self.items(QtCore.Qt.DescendingOrder))

    def items(self, ascending=True):
        """
        :returns: This scene's items.
        :param ascending: If true, items are given from background to
          foreground.
        """
        o = QtCore.Qt.AscendingOrder if ascending else QtCore.Qt.AscendingOrder
        return super().items(o)

    def add_mask(self, mask_arr, rgba=None, item_on_top=None):
        """
        :param mask_arr: A ``np.bool(h, w)`` array.
        :param item_on_top: If given, mask will be added underneath that item.
          Otherwise will be added on top of item stack.
        :returns: The added ``PixmapItem``.
        """
        # sanity check mask
        assert mask_arr.dtype == np.bool, "Mask must be np.bool(h, w)!"
        assert len(mask_arr.shape) == 2, "Mask must be np.bool(h, w)!"
        assert mask_arr.shape == (self.h, self.w), \
            "Mask must have same (h, w) as image!"
        # sanity check color
        if rgba is None:
            r, g, b = next(RandomColorGenerator().generate(form="rgbArray"))
            rgba = (r, g, b, self.DEFAULT_MASK_ALPHA)
        assert all([0 <= c <= 255 for c in rgba]), \
            "RGBA must be in [0, 255] range!"
        # add pixmap: if this fails, the method raises with no side effect
        pm = bool_arr_to_rgba_pixmap(mask_arr, rgba)
        pmi = self.addPixmap(pm)
        self.mask_pmis[pmi] = rgba
        # now we have side FX: if this fails roll back the add Pixmap
        if item_on_top is not None:
            try:
                pmi.stackBefore(item_on_top)
            except Exception:
                # roll back addition
                del self.mask_pmis[pmi]
                self.removeItem(pmi)
                raise RuntimeError(
                    "Invalid other_item? {}".format(item_on_top))
        #
        return pmi

    def remove_mask(self, pmi):
        """
        :param pmi: The PixmapItem to remove. It has to be a mask added via
          ``add_mask``
        """
        # check that exists in our dict
        rgba = self.mask_pmis[pmi]
        #
        self.removeItem(pmi)
        del self.mask_pmis[pmi]
        return rgba

    def replace_mask_pmi(self, pmi, new_mask_arr, new_rgba=None):
        """
        If we call ``remove_mask`` and then ``add_mask`` fails, we will lose
        the removed mask forever. This method updates the mask in an atomary
        way: either succeeds or does nothing.

        .. warning::
          The input ``pmi`` gets removed from the scene and the reference
          becomes invalid. Use the reference returned by this function instead.
        """
        # the problem is if we successfully remove and then fail to add. A
        # fix is to first add below the to-be-removed, and then remove
        old_rgba = self.mask_pmis[pmi]
        if new_rgba is None:
            new_rgba = old_rgba
        new_pmi = self.add_mask(new_mask_arr, rgba=new_rgba, item_on_top=pmi)
        self.remove_mask(pmi)
        return new_pmi

    def mask_as_bool_arr(self, pmi):
        """
        Asserts that the given ``pmi`` is in ``self.mask_pmis``, and returns
        the map as ``np.bool(h, w)`` array, in which all non-zero values are
        true.
        """
        assert pmi in self.mask_pmis, "Given Item is not in mask_pmis!"
        # a has shape (h, w, 4) where 4->RGBA
        pixmap_format = QtGui.QImage.Format_RGBA8888
        arr = pixmap_to_arr(pmi.pixmap(), pixmap_format)
        mask = (arr > 0).any(axis=-1)
        return mask


# #############################################################################
# ## VIEW (EVENTS ETC)
# #############################################################################
class DisplayView(MouseEventManager, QtWidgets.QGraphicsView):
    """
    In Qt applications, it is usual to wrap a scene with a view. This allows
    to dynamically and easily change the perspective on the scene.
    """
    def __init__(self, scene=None, parent=None, scale_percent=15):
        """
        :param scene: The scene to view. It can be set also afterwards via
          ``self.setScene``.
        """
        QtWidgets.QGraphicsView.__init__(self, scene, parent)
        MouseEventManager.__init__(self, True)
        self.scale_factor_up = 1 + float(scale_percent) / 100
        self.scale_factor_down = 1.0 / self.scale_factor_up
        #
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # Set Anchors
        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)
        #
        if scene is not None:
            self.fit_in_scene()

    def fit_in_scene(self):
        """
        Moves perspective so that the whole scene can be seen in view.
        """
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio)

    def zoom(self, pos_x, pos_y, zoom_out=False):
        """
        Source for wheel zoom: https://stackoverflow.com/a/29026916/4511978
        """
        # Save the scene pos
        qpos = QtCore.QPoint(pos_x, pos_y)
        old_pos = self.mapToScene(qpos)
        # Zoom
        scale_factor = (self.scale_factor_down if zoom_out
                        else self.scale_factor_up)
        self.scale(scale_factor, scale_factor)
        # Get the new position
        new_pos = self.mapToScene(qpos)
        # Move scene to old position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def shift_view(self, delta_x, delta_y):
        """
        Move perspective to shift through the scene
        """
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() - delta_x)
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value() - delta_y)

    def on_mid_press(self, event):
        """
        Override me
        """
        self.fit_in_scene()

    def on_wheel(self, event, has_ctrl, has_alt, has_shift):
        """
        Override me
        """
        if (has_ctrl, has_alt, has_shift) == (False, False, False):
            zoom_out = event.delta() <= 0
            self.zoom(*event.pos().toTuple(), zoom_out)

    def on_right_press(self, event):
        """
        Override me
        """
        self.setDragMode(self.ScrollHandDrag)

    def on_right_release(self, event):
        """
        Override me
        """
        self.setDragMode(self.NoDrag)

    def on_move(self, event, has_left, has_mid, has_right, this_pos, last_pos):
        """
        Override me
        """
        #
        # shift scene with right button
        if has_right:
            delta_x, delta_y = (this_pos - last_pos).toTuple()
            self.shift_view(delta_x, delta_y)
