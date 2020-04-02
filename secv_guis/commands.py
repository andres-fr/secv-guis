# -*- coding:utf-8 -*-


"""
This module contains all the 'undoable' actions. They must implement a way
to undo and redo them.

Composite commands deserve a special mention: they are trains of actions
that only track, store and report the initial and final state. They are
particularly useful when performing interactive editings on big datastructures
like pixmaps, to prevent memory bloating.
"""


import numpy as np
from PySide2 import QtCore, QtWidgets, QtGui
from .utils import pixmap_to_arr


# #############################################################################
# ## SINGLE-SHOT COMMANDS
# #############################################################################
class UndoableLambda(QtWidgets.QUndoCommand):
    """
    This kind of functor can be used to create them on the spot and send them
    to the UndoStack. Useful to split down a composite action in arbitrary
    undo-able subactions. Usage example::

      # in action ... do something ...
      cmd = UndoableLambda("My partial action",
                           lambda: print("undo"), lambda: print("redo"))
      undo_stack.push(cmd)
    """
    def __init__(self, command_name, undo_fn, redo_fn, parent=None):
        """
        """
        super().__init__(command_name, parent)
        self.undo_fn = undo_fn
        self.redo_fn = redo_fn

    def undo(self):
        """
        """
        self.undo_fn()

    def redo(self):
        """
        """
        self.redo_fn()

# #############################################################################
# ## SINGLE-SHOT COMMANDS
# #############################################################################


# #############################################################################
# ## COMPOSITE COMMANDS
# #############################################################################
class CompositeCommand(QtWidgets.QUndoCommand):
    """
    In some cases like painting a stroke into a pixmap, it doesn't make sense
    to store every single update: rather, the prior and finished states only.
    This class provides a structure for such cases:

    1. Instantiate the command with the parameters that belong to the whole
        composite action.
    2. Call ``action`` for every desired update of the finished state
    3. Call ``finish`` to crystalize the final state. No further ``action`` s
        will be allowed, and (optionally) the action will be added to a Qt
        ``UndoStack``.

    The following is required to extend the class:
    1. Define a ``COMMAND_NAME``
    2. Extend the ``__init__``, ``action``, ``undo`` and ``redo`` methods.
    """
    # override this when extending!
    COMMAND_NAME = NotImplemented

    def __init__(self, parent=None):
        """
        """
        super().__init__(self.COMMAND_NAME, parent)
        self.finished = False

    def action(self):
        """
        Extend me!
        """
        assert not self.finished, \
            "This CompositeCommand has already been finished!"

    def finish(self, undo_stack=None):
        """
        :param undo_stack: If given, this command will be added to the stack,
          wich then allows to undo/redo.

        Call this function once you are done with the ``action`` s. Once finish
        is called, no more ``action`` s are possible, so that the undo/redo
        actions stay frozen.
        """
        self.finished = True
        if undo_stack is not None:
            undo_stack.push(self)


class DrawCommand(CompositeCommand):
    """
    A composite command to draw a stroke of circles into a ``PixmapIten``.
    """
    COMMAND_NAME = "Draw"

    def __init__(self, pmi, rgba, diameter,
                 comp_mode=QtGui.QPainter.CompositionMode_Source, parent=None):
        """
        :param pmi: A ``PixmapItem``, where this command will apply.
        :param rgba: A tuple ``(r, g, b, a)`` of ``0-255`` values.
        :param diameter: In pixels, diameter of the circle to be drawn.
        :param comp_mode: The "Source" mode ensures that the alphas don't
          get added.
        """
        super().__init__(parent)
        # Caution: memory intensive? (<100 commands on 4k*6k seems ok)
        self.original_pixmap = pmi.pixmap()
        self.final_pixmap = pmi.pixmap()
        #
        self.pmi = pmi
        self.rgba = rgba
        self.diameter = diameter
        self.comp_mode = comp_mode
        #
        color = QtGui.QColor(*rgba)
        self.brush = QtGui.QBrush(color, bs=QtCore.Qt.SolidPattern)
        self.pen = QtGui.QPen(color)

    def action(self, x_pos, y_pos):
        """
        Once the object has been constructed **and ``finish()`` hasn't been
        called yet**, Call this function to paint a circle at given position.
        Check constructor for further variables.
        """
        super().action()
        # get painter and set it up
        painter = QtGui.QPainter(self.final_pixmap)
        painter.setCompositionMode(self.comp_mode)
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        #
        diameter = self.diameter
        radius = diameter // 2
        xywh = (x_pos - radius, y_pos - radius, diameter, diameter)
        painter.drawEllipse(QtCore.QRect(*xywh))
        painter.end()
        self.pmi.setPixmap(self.final_pixmap)

    def redo(self):
        """
        This function implements the interface for the UndoStack. Don't call
        this directly.
        """
        self.pmi.setPixmap(self.final_pixmap)

    def undo(self):
        """
        This function implements the interface for the UndoStack. Don't call
        this directly.
        """
        self.pmi.setPixmap(self.original_pixmap)

    def finish(self, undo_stack=None):
        """
        Usually we don't override ``finish``, but since pixmaps are so big,
        we don't want to store the command if original and final are equal.
        """
        self.finished = True
        if undo_stack is not None:
            original_arr = pixmap_to_arr(self.original_pixmap,
                                         QtGui.QImage.Format_RGBA8888)
            final_arr = pixmap_to_arr(self.final_pixmap,
                                      QtGui.QImage.Format_RGBA8888)
            # Add to stack only if there is any difference
            if not np.array_equal(original_arr, final_arr):
                undo_stack.push(self)


class EraseCommand(DrawCommand):
    """
    A composite command to erase a stroke of circles into a ``PixmapIten``.
    See ``DrawCommand`` docstrings for more info.
    """
    COMMAND_NAME = "Erase"

    def __init__(self, pmi, diameter,
                 comp_mode=QtGui.QPainter.CompositionMode_Source, parent=None):
        """
        See ``DrawCommand`` docstrings for more info.
        """
        super().__init__(pmi, (0, 0, 0, 0), diameter, comp_mode)


class DrawOverlappingCommand(DrawCommand):
    """
    Like ``DrawCommand``, but accepts 2 PixmapItems instead of one, so that
    the drawing onto the first is only allowed if the same pixel is active in
    the second.
    """
    COMMAND_NAME = "Draw Overlapping"

    def __init__(self, pmi, ref_pmi, rgba, diameter,
                 comp_mode=QtGui.QPainter.CompositionMode_Source, parent=None):
        """
        :param ref_pmi: This ``PixmapItem`` should be of same shape as ``pmi``.
        See ``DrawCommand`` docstrings for more info.
        """
        super().__init__(pmi, rgba, diameter, comp_mode)
        self._reference_pmi = ref_pmi

    def action(self, x_pos, y_pos):
        """
        Paint a circle on ``pmi`` at given position, masked by ``ref_pmi``.
        """
        # get painter and set it up
        painter = QtGui.QPainter(self.final_pixmap)
        painter.setCompositionMode(self.comp_mode)
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        #
        diameter = self.diameter
        radius = diameter // 2
        xywh = (x_pos - radius, y_pos - radius, diameter, diameter)
        #
        # mask out the relevant region from the other mask: for that find the
        # zeros, and mask out anything that IS a zero
        other_pm = self._reference_pmi.pixmap().copy(QtCore.QRect(*xywh))
        other_mask = other_pm.createMaskFromColor(
            QtGui.QColor(0, 0, 0, a=0), mode=QtCore.Qt.MaskInColor)
        other_region = QtGui.QRegion(other_mask)
        # translate region to global coords and apply mask to painter
        other_region.translate(x_pos - radius, y_pos - radius)
        painter.setClipRegion(other_region)
        # draw and refresh
        painter.drawEllipse(QtCore.QRect(*xywh))
        painter.end()
        self.pmi.setPixmap(self.final_pixmap)
