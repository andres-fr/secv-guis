# -*- coding:utf-8 -*-


"""
Object composite commands are intended for composite objects (like e.g.
a train of points). The main difference with the regular commands is that
they implement a ``state`` method (which e.g. for a train of points returns
a list of (x, y) tuples), and a ``clear`` method, which allows to 'remove'
the object without having to roll back or break the undo queue.
"""


from PySide2 import QtCore, QtGui
from .commands import CompositeCommand, UndoableLambda


# #############################################################################
# ## HELPERS
# #############################################################################


# #############################################################################
# ## OBJECT COMPOSITE COMMANDS
# #############################################################################
class PointList(CompositeCommand):
    """
    This class provides functionality to add circles to a scene (optionally
    connected by lines), and to return their centers as a list of ``(x, y)``
    positions. It also
    """
    COMMAND_NAME = "Draw point list"

    def __init__(self, scene, diameter, fill_rgba=(100, 100, 100, 100),
                 contour_rgba=(0, 0, 0, 255),
                 draw_lines_between_dots=False,
                 comp_mode=QtGui.QPainter.CompositionMode_SourceOver,
                 parent=None):
        """
        :scene: A pointer to the ``QGraphicsScene`` to add points to.
        :fill_rgba: inner circle (and optionally line) color.
        :contour_rgba: circle contour color
        :draw_lines_between_dots: If true, connect the dots
        :comp_mode: ``SourceOver`` means alphas get added. Check Qt composition
          modes.
        """
        super().__init__(parent)
        #
        self.scene = scene
        self.diameter = diameter
        self.comp_mode = comp_mode
        #
        self.fill_rgba = fill_rgba
        self.contour_rgba = contour_rgba
        fill_color = QtGui.QColor(*fill_rgba)
        contour_color = QtGui.QColor(*contour_rgba)
        self.dot_brush = QtGui.QBrush(fill_color, bs=QtCore.Qt.SolidPattern)
        self.dot_pen = QtGui.QPen(contour_color)
        # "all points" can only grow, it will remember even if we undo
        # "points" will show the "active", not deleted points only
        self._all_points = []
        self.points = []
        #
        self.with_lines = draw_lines_between_dots
        r, g, b, a = fill_rgba
        line_color = QtGui.QColor(r, g, b, a // 2)
        self.line_pen = QtGui.QPen(line_color)
        self._lines = {}

    def state(self):
        """
        :returns: A list in the form ``[(x1, y1), ...]`` with the center
          of the currently active points.
        """
        centers = [elt.rect().center().toTuple() for elt in self.points]
        return centers

    def clear(self):
        """
        Removes all the active points from the datastructure and the scene.
        """
        while self.points:
            pmi = self.points.pop()
            self.scene.removeItem(pmi)
            try:
                line = self._lines[pmi]
                self.scene.removeItem(line)
            except KeyError:
                pass

    def action(self, x, y, undo_stack=None):
        """
        Add a new point at given position.
        :param undo_stack: If given, this action is added to the undo stack.
        """
        d = self.diameter
        radius = float(d) / 2
        rect = QtCore.QRect(*(x - radius, y - radius, d, d))
        pmi = self.scene.addEllipse(rect, pen=self.dot_pen,
                                    brush=self.dot_brush)
        #
        self._all_points.append(pmi)
        self.points.append(pmi)
        #
        if self.with_lines:
            centers = self.state()
            if len(centers) >= 2:
                x1, y1 = centers[-2]
                x2, y2 = centers[-1]
                line_pmi = self.scene.addLine(x1, y1, x2, y2,
                                              pen=self.line_pen)
                self._lines[pmi] = line_pmi
        #
        if undo_stack is not None:
            # deep copy is needed
            pmis_before = list(self.points[:-1])
            pmis_after = list(self.points)
            #
            cmd = UndoableLambda(
                "Draw point", lambda: self._set_active_pmis(pmis_before),
                lambda: self._set_active_pmis(pmis_after))
            undo_stack.push(cmd)

    def _set_active_pmis(self, pmis):
        """
        Given a collection of ``pmi`` s that exist in ``self._all_points``,
        set those, and only those, as active.
        """
        assert all([p in self._all_points for p in pmis]), \
            "All pmis must preexist!"
        self.clear()
        for pmi in pmis:
            self.scene.addItem(pmi)
            self.points.append(pmi)
            try:
                line_pmi = self._lines[pmi]
                self.scene.addItem(line_pmi)
            except KeyError:
                pass

    def redo(self):
        """
        Unused
        """
        self._set_active_pmis(self._all_points)

    def undo(self):
        """
        Unused
        """
        self._set_active_pmis([])

    def finish(self, undo_stack=NotImplemented):
        """
        Simply sets ``self.finished`` to true, because the undo stack gets
        the separate ``actions`` instead of the whole composite one.
        """
        self.finished = True


# #############################################################################
# ## OBJECT CONTAINER
# #############################################################################
class ObjectContainer:
    """
    This class is a Mixin. When a ``QGraphicsScene`` inherits from it, it
    acquires functionality to add multiple composite objects from this module.
    """
    def __init__(self):
        """
        """
        # objects come on the top of masks
        self.objects = {}
        self._current_object_action = None

    def close_current_object_action(self, undo_stack=None):
        """
        If there is an open object action, closes it and optionally adds it to
        the undo stack
        """
        cmd = self._current_object_action
        if cmd is not None:
            cmd.finish(undo_stack)
            self._current_object_action = None

    def object_action(self, obj_class, action_args, obj_instantiation_args,
                      undo_stack=None):
        """
        This function implements a protocol to add composite objects to the
        scene.

        1. If a different composite action was running, it closes it and starts
            this one, adding it to ``self.objects``.
        2. If no composite action was running, starts this one and adds it.
        3. If ``obj_class`` is already running, does nothing here.

        In all cases, including if ``obj_class`` was already running,
        performs the action ``obj.action(*action_args)``.

        .. note::
          The scene simply calls the object's action. The object is responsible
          for keeping track of the ``scene items`` it generates, and also
          removing/adding them to the scene when needed.

        :param obj_instantiation_args: If this action needs to be started, it
          will be called via ``cmd = action_class(*instantiation_args)``
        :param action_args: The action will be called with this args.

        Usage example::

          # adds a point to the existing cloud or starts one otherwise
          scene.object_action(ExamplePointCloud, [x, y],
                              [cloud_color, points_size...])
          # check the state of the last added point cloud (this one):
          scene.objects[ExamplePointCloud][-1].state()
        """
        cmd = self._current_object_action
        # if changed to this action without releasing the prior one, release it
        action_changed = obj_class is not cmd.__class__
        cmd_finished = cmd is not None and cmd.finished
        #
        if action_changed:
            self.close_current_object_action(undo_stack)
            cmd = self._current_object_action  # this should be None
        # if no open action of this class, create
        if cmd is None or cmd_finished:
            cmd = obj_class(*obj_instantiation_args)
            self._current_object_action = cmd
            self.objects.setdefault(obj_class, []).append(cmd)
        cmd.action(*action_args)
