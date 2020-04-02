# -*- coding:utf-8 -*-


"""
This module contains the logic and widgets pertaining to the main window
of the bimask app: An app that allows displaying an image, editing a mask
on it and also displaying/editing a preannotation mask.

It can be used to efficiently annotate large images with pixel precision.
Check instructions.txt for more details.
"""


import os
from PySide2 import QtCore, QtWidgets, QtGui
import numpy as np
from PIL import Image
import json
#
from skimage.filters import apply_hysteresis_threshold
#
from .dialogs import InstructionsDialog, AboutDialog, KeymapsDialog, \
    SavedStateTracker
#
from ..masked_scene import MaskedImageScene, DisplayView
from ..base_widgets import FileList, MaskPaintForm, SaveForm
from ..utils import load_img_and_exif, unique_filename
from ..commands import DrawCommand, EraseCommand, DrawOverlappingCommand
from ..objects import PointList


# #############################################################################
# ## APPLICATION LOGIC FOR QUICK MASKING
# #############################################################################
def exp_lambda_estimator(elts):
    """
    :param elts: A collection of elements (can also be numpy).

    Given a set of elements, assumed to be exponentially distributed, returns
    the unbiased estimator for the lambda parameter of the exp distribution.
    """
    try:
        num_elts = elts.size
        elt_sum = elts.sum()
    except Exception:
        num_elts = len(elts)
        elt_sum = sum(elts)
    #
    lmbd = num_elts / elt_sum
    lmbd = lmbd - (lmbd / num_elts)
    return lmbd


def exp_threshold(keep_p_value, lmbd):
    """
    :param keep_p_value: Scalar in range ``(0, 1]``
    :param elts: collection of values, assumed to be sampled from an
      exponential distribution.
    :returns: A threshold ``t``, so that the integral for ``exp(lambda)`` from
      t to infinity equals ``keep_p_value``.

    This function assumes that the given ``elts`` have been sampled from an
    exponential distribution. Then inferes lambda, using the unbiased ML
    estimator (see https://en.wikipedia.org/wiki/Exponential_distribution)
    and returns the threshold ``t`` that fulfills ``keep_p_value`` for the
    distribution above ``t``.
    """
    assert 0 < keep_p_value <= 1, "area_p_conserve must be in (0, 1]"
    threshold = -np.log(keep_p_value) / lmbd
    return threshold


def pmap_to_mask(pmap, keep_highest_pval=0.05, discard_lowest_pval=0.5):
    """
    This method performs the following steps:

    1. Assuming that pmap values are exponentially distributed, extracts the
         unbiased lambda parameter and the cumulative distribution.
    2. Applies threshold to the given low/high p-values

    This method uses the standard connected component extraction mechanism
    in Python, i.e. ``scipy.ndimage.measurements.label`` and
    ``skimage.measure.regionprops``.

    :param pmap: A float array of shape ``h, w``.
    :param keep_highest_pval: The p-value designing the amount of top 'pmap'
      scores to be surely kept.
    :param discard_lowest_pval: The p-value designing the amount of bottom
      'pmap' scores to be surely discarded.
    :returns: The output mask
    """
    # print("PMAP TO MASK CALLED:", keep_highest_pval, discard_lowest_pval)
    assert keep_highest_pval < discard_lowest_pval, \
        "highest-P-val must be lower than lowest-P-val."

    lmbd = exp_lambda_estimator(pmap.ravel())
    t_keep_above = exp_threshold(keep_highest_pval, lmbd)
    t_discard_below = exp_threshold(discard_lowest_pval, lmbd)
    out_mask = apply_hysteresis_threshold(pmap, t_discard_below, t_keep_above)

    # sure keep: pmap>=t_keep_above   sure discard: pmap <= t_discard_below

    # t = exp_threshold(keep_below_pval, pmap.ravel())
    # mask = pmap >= t
    # # label performs connected component identification, by default
    # # using a cross-shape structuring elt.
    # labels, nlabels = label(mask)
    # # compute a set of feats for each isolated component
    # props = regionprops(labels, pmap)
    # #
    # areas = [p.area for p in props]
    # areas_threshold = exp_threshold(keep_p_value, areas)
    #
    # out_mask = np.zeros_like(mask)
    # for p in props:
    #     if p.area >= areas_threshold:
    #         coords_y, coords_x = p.coords.T
    #         out_mask[(coords_y, coords_x)] = True

    return out_mask


# #############################################################################
# ## WIDGET EXTENSIONS AND COMPOSITIONS TO ADD SPECIFIC LOGIC+LAYOUT
# #############################################################################
class FileLists(QtWidgets.QWidget):
    """
    A cluster of 3 file lists: one for images, one for masks and one for
    preannotations.
    """
    def __init__(self, parent=None, img_extensions=[".png", ".jpg", ".jpeg"],
                 mask_extensions=None, preannot_extensions=None):
        """
        If given, the extensions are case-insensitive lists in the form
        ``[".png", ".jpg"]`` that filter the files that are shown in the list
        by allowing only the given terminations.
        """
        super().__init__(parent)
        # create widgets
        self.img_list = FileList("Images\nfolder", extensions=img_extensions)
        self.mask_list = FileList("Masks\nfolder")
        self.preannot_list = FileList("Pre-annotations\nfolder")
        # add widgets to layout
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addWidget(self.img_list)
        self.main_layout.addWidget(self.mask_list)
        self.main_layout.addWidget(self.preannot_list)
        self.setLayout(self.main_layout)


class IntegratedSaveForm(SaveForm):
    """
    A ``SaveForm`` that implements this app's logic, namely, it features 2
    masks, one for annot and one for preannot, and saves them as B&W png.
    """
    def __init__(self, main_window, default_path=None,
                 save_dialog_timeout_ms=1000):
        """
        :param main_window: A reference to the ``BimaskMainWindow``
        :param str default_path: If non given, 'home' is picked.
        :param save_dialog_timeout: When successfully saving, a dialog
          will pop up, and disappear after this many miliseconds.
        """
        super().__init__(None, default_path)
        self.main_window = main_window
        self.add_checkbox("preannot.", initial_val=False,
                          initial_txt="_preannot.png")
        self.add_checkbox("annot.", initial_txt="_annot.png")
        self.add_checkbox("points", initial_txt="_points.json")
        # This reference is needed otherwise dialogs get garbage collected?
        self.dialog = None
        self.dialog_ms = save_dialog_timeout_ms

    def save_masks(self, states, suffixes, overwrite):
        """
        Overriden method that we don't call directly. See ``SaveForm`` for
        interface details.
        """
        save_preannot, save_annot, save_points = states
        suff_preannot, suff_annot, suff_points = suffixes
        img_name = self.main_window.current_img_basename
        #
        a_pmi = self.main_window.graphics_view.annot_pmi
        pa_pmi = self.main_window.graphics_view.preannot_pmi
        #
        scene = self.main_window.graphics_view.scene()
        saved = {}
        if save_preannot and pa_pmi is not None:
            pa_path = os.path.join(self.save_path, img_name + suff_preannot)
            if not overwrite:
                pa_path = unique_filename(pa_path)
            pa_msk_arr = scene.mask_as_bool_arr(pa_pmi)
            self.save_bool_arr_as_img(pa_msk_arr, pa_path, overwrite)
            saved["preannotation mask"] = pa_path
        if save_annot and a_pmi is not None:
            a_path = os.path.join(self.save_path, img_name + suff_annot)
            if not overwrite:
                a_path = unique_filename(a_path)
            msk_arr = scene.mask_as_bool_arr(a_pmi)
            self.save_bool_arr_as_img(msk_arr, a_path, overwrite)
            saved["annotation mask"] = a_path
        if save_points and scene.objects:
            state_dict = {k.__name__: [elt.state() for elt in v if elt.state()]
                          for k, v in scene.objects.items()}
            p_path = os.path.join(self.save_path, img_name + suff_points)
            if not overwrite:
                p_path = unique_filename(p_path)
            with open(p_path, "w") as f:
                # f.write(str(state_dict))
                json.dump(state_dict, f)
            saved["point lists"] = p_path
        #
        if saved:
            self.main_window.graphics_view.saved_state_tracker.save(
                saved, self.dialog_ms)

    def save_bool_arr_as_img(self, arr, outpath, overwrite_existing=False):
        """
        Output: RGB PNG image where false is black (0, 0, 0) and true is white
        (255, 255, 255).
        """
        if not overwrite_existing:
            outpath = unique_filename(outpath)
        img = Image.fromarray(arr)
        img.save(outpath)


class IntegratedDisplayView(DisplayView):
    """
    This class implements the main component of the main window: it features a
    view of the image and the masks, together with a set of operations that can
    be done on them (painting, updating...), and the callback mechanisms to
    trigger those operations.
    """
    def __init__(self, main_window, scale_percent=15):
        """
        :param scale_percent: Each zoom in/out operation will scale the view
          by this much (in percent).
        """
        super().__init__(scene=None, parent=None, scale_percent=scale_percent)
        self._scene = MaskedImageScene()
        self.main_window = main_window
        self.shape = None
        self.setScene(self._scene)
        #
        self._preannot_pmap = None
        self.preannot_pmi = None
        self.annot_pmi = None
        #
        #
        self._current_clickdrag_action = None
        #
        self.saved_state_tracker = None

    # MEMORY ACTIONS
    def new_image(self, img_path, initial_mask_color=(219, 54, 148, 150),
                  initial_preannot_color=(102, 214, 123, 100)):
        """
        If successful, removes all elements from the scene and the undo stack,
        and loads a fresh image and masks. If there are unsaved changes, a
        dialog asking for confirmation will pop up.

        :returns: True if the action completed successfully, False if the user
          decides to abort.
        """
        if self.saved_state_tracker is not None:
            is_delete_ok = self.saved_state_tracker.delete()
            if not is_delete_ok:
                # If user didn't want to delete unsaved changes
                return False
        # Go on with the update
        img_arr = load_img_and_exif(img_path)[0]
        self.shape = img_arr.shape
        self._scene.update_image(img_arr)
        dummy_preannot = np.zeros(img_arr.shape[:2], dtype=np.bool)
        dummy_mask = np.zeros_like(dummy_preannot)
        self.preannot_pmi = self._scene.add_mask(
            dummy_preannot, initial_preannot_color)
        self.annot_pmi = self._scene.add_mask(
            dummy_mask, initial_mask_color)
        self.fit_in_scene()
        #
        self.main_window.undo_stack.clear()
        #
        self.saved_state_tracker = SavedStateTracker()
        return True

    def preannot_from_path(self, preannot_path, rgba, keep_p_value=0.05,
                           discard_p_value=0.5, normalize=False):
        """
        This method is prototype-ish: It loads an ``.npz`` file with and
        'entropy' field, expected to have a numpy float matrix with same
        shape as the image.
        """
        assert self.scene().img_pmi is not None, \
            "You need to load an image first!"
        self._preannot_pmap = np.load(preannot_path)["entropy"]
        if normalize:
            try:
                self._preannot_pmap /= self._preannot_pmap.max()
            except ZeroDivisionError:
                pass
        m = pmap_to_mask(self._preannot_pmap, keep_p_value, discard_p_value)
        self.preannot_pmi = self.scene().replace_mask_pmi(
            self.preannot_pmi, m)
        #
        self.saved_state_tracker.edit()

    def mask_from_path(self, mask_path, rgba):
        """
        :param mask_path: Path to an image containing a binary mask, where
          zero pixels are considered false and non-zero true.
        :param rgba: Color of the loaded mask

        Loads a binary mask into the scene as an RGBA-colored mask.
        """
        assert self.scene().img_pmi is not None, \
            "You need to load an image first!"
        arr = load_img_and_exif(mask_path)[0]
        if len(arr.shape) == 2:
            mask = arr > 0
        elif len(arr.shape) == 3:
            mask = arr.any(axis=-1)
        else:
            raise RuntimeError("Mask must be rank 2 or 3!")
        self.annot_pmi = self.scene().replace_mask_pmi(
            self.annot_pmi, mask)
        #
        self.saved_state_tracker.edit()

    # MASK SINGLE-SHOT ACTIONS
    def change_preannot_pval(self, keep_p_value, discard_p_value=0.5):
        """
        Updates the preannot->mask threshold.
        """
        if self._preannot_pmap is not None:
            new_m = pmap_to_mask(self._preannot_pmap, keep_p_value,
                                 discard_p_value)
            self.preannot_pmi = self.scene().replace_mask_pmi(
                self.preannot_pmi, new_m)
        #
        self.saved_state_tracker.edit()

    def change_preannot_rgba(self, rgba):
        """
        Updates the preannot mask color.
        """
        if self.preannot_pmi is not None:
            m = self.scene().mask_as_bool_arr(self.preannot_pmi)
            self.preannot_pmi = self.scene().replace_mask_pmi(
                self.preannot_pmi, m, rgba)

    def change_annot_rgba(self, rgba):
        """
        Updates the annot mask color.

        """
        if self.annot_pmi is not None:
            m = self.scene().mask_as_bool_arr(self.annot_pmi)
            self.annot_pmi = self.scene().replace_mask_pmi(
                self.annot_pmi, m, rgba)

    # MASK COMPOSITE ACTIONS
    def _finish_clickdrag_action(self):
        """
        finishes any click+drag action that may be active (does nothing if
        none active).
        """
        cmd = self._current_clickdrag_action
        if cmd is not None:
            cmd.finish(self.main_window.undo_stack)
            self._current_clickdrag_action = None

    def _perform_composite_action(self, action_class, action_args,
                                  construction_args):
        """
        This function is the recommended way to perform a composite
        action for the following reasons:

        1. If ``action_class`` is already running, it simply continues it.
        2. If a different composite action was running, it closes it and starts
            this one.
        3. If no composite action was running, starts this one

        And finally performs the action.

        :param construction_args: If this action needs to be started, it will
          be called via ``cmd = action_class(*construction_args)``
        :param action_args: The command will be called via ``cmd(action_args)``

        Usage example::
          x, y = current_action_position...
          pmi = ...
          brush_size = ...
          rgba = self.scene().mask_pmis[pmi]
          self._perform_composite_action(DrawCommand, [x, y],
                                         [pmi, rgba, brush_size])
        """
        cmd = self._current_clickdrag_action
        # if changed to this action without releasing the prior one, release it
        action_changed = action_class is not cmd.__class__
        cmd_finished = cmd is not None and cmd.finished
        if action_changed:
            self._finish_clickdrag_action()  # sets current action to None
            cmd = self._current_clickdrag_action
        # if no open action of this class, create
        if cmd is None or cmd_finished:
            cmd = action_class(*construction_args)
            self._current_clickdrag_action = cmd
        cmd.action(*action_args)

    def clickdrag_action(self, x, y):
        """
        Paint to the currently selected mask, with the currently selected
        brush type, at the given position.
        The given ``x, y`` position is in 'scene coordinates', i.e. the
        position from a mouse event has to be translated as follows::

          xpos, ypos = self.mapToScene(event.pos()).toTuple()
          self.clickdrag_action(xpos, ypos)
        """
        # retrieve pmi info
        # expected idx: 0 for preannot, 1 for annot
        idx_map = {0: self.preannot_pmi, 1: self.annot_pmi}
        mask_idx = self.main_window.paint_form.current_button_idx
        pmi = idx_map[mask_idx]
        # paint only if this pmi
        if pmi is None:
            return
        # retrieve brush info
        p_txt, e_txt, mp_txt = [self.main_window.PAINTER_TXT,
                                self.main_window.ERASER_TXT,
                                self.main_window.MASKED_PAINTER_TXT]
        brush_type = self.main_window.paint_form.current_brush_type
        brush_size = self.main_window.paint_form.current_brush_size
        # if no open action exists, create:
        did_something = False
        if brush_type == p_txt:
            rgba = self.scene().mask_pmis[pmi]
            self._perform_composite_action(DrawCommand, [x, y],
                                           [pmi, rgba, brush_size])
            did_something = True
        elif brush_type == e_txt:
            self._perform_composite_action(EraseCommand, [x, y],
                                           [pmi, brush_size])
            did_something = True
        elif brush_type == mp_txt:
            rgba = self.scene().mask_pmis[pmi]
            ref_pmi = self.preannot_pmi  # preannot is always the ref
            self._perform_composite_action(DrawOverlappingCommand, [x, y],
                                           [pmi, ref_pmi, rgba, brush_size])
            did_something = True
        #
        if did_something:
            self.saved_state_tracker.edit()

    def add_point(self, x, y, close_after=False):
        """
        """
        if self.scene().img_pmi is None:
            return
        brush_size = self.main_window.paint_form.current_brush_size
        self.scene().object_action(
            PointList, [x, y, self.main_window.undo_stack],
            [self.scene(), brush_size, (0, 0, 0, 100), (0, 0, 0, 255),
             True])  # draw lines
        #
        if close_after:
            self.scene().close_current_object_action(
                self.main_window.undo_stack)

    # EVENT HANDLING
    def on_left_press(self, event):
        """
        """
        xpos, ypos = self.mapToScene(event.pos()).toTuple()
        brush_type = self.main_window.paint_form.current_brush_type
        if brush_type == self.main_window.POINT_LIST_TXT:
            mods = event.modifiers()
            has_ctrl = bool(mods & QtCore.Qt.ControlModifier)
            self.add_point(xpos, ypos, close_after=has_ctrl)
        else:
            self.clickdrag_action(xpos, ypos)

    def on_left_release(self, event):
        """
        If there is an open macro command, closes it and adds it to the undo
        stack
        """
        self._finish_clickdrag_action()

    def on_move(self, event, has_left, has_mid, has_right, this_pos, last_pos):
        """
        Callback implementation, calls ``clickdrag_action`` if moving while
        pressing left.
        """
        super().on_move(event, has_left, has_mid, has_right, this_pos,
                        last_pos)
        #
        if has_left:
            xpos, ypos = self.mapToScene(event.pos()).toTuple()
            self.clickdrag_action(xpos, ypos)


class CrackAnnotPaintForm(MaskPaintForm):
    """
    A ``MaskPaintForm`` that holds a reference to the app's main window and
    connects its callbacks with the main window's corresponding components.
    """
    def __init__(self, main_window, brushes, max_brush_size=100, parent=None,
                 thresh_min=0, thresh_max=1, thresh_num_steps=100):
        """
        :param main_window: A reference to the bimask app main window instance.
        :param brushes: A list of brush names to be featured in the form.
        """
        super().__init__(brushes, max_brush_size, parent, thresh_min,
                         thresh_max, thresh_num_steps, min_alpha=1)
        self.main_window = main_window
        self.current_brush_type = self.brush_names[
            self.brush_combo_box.currentIndex()]
        self.current_brush_size = self.brush_size_slider.value()
        self.current_button_idx = None  # activate when calling addItem

    def button_pressed(self, but):
        """
        Setter
        """
        self.current_button_idx = self._buttons.index(but)

    def threshold_slider_changed(self, idx, val):
        """
        :param int idx: The mask index. 0 is the index of the preannotation,
          1 for annotation.
        :param val: The new p-value.

        Update preannotation mask with new p-value by calling the
        ``change_preannot_val`` method of the view. Only works if idx is 0.
        """
        if idx == 0:
            self.main_window.graphics_view.change_preannot_pval(
                val, self.main_window.DISCARD_P_VALUE)

    def rgba_box_changed(self, idx, r, g, b, a):
        """
        Update corresponding mask with new RGBA color.
        """
        # NOTE: THIS ASSUMES THAT BOX 0 IS ANNOT AND BOX 1 IS PREANNOT!
        assert idx in {0, 1}, "This GUI wasn't prepared for more than 2 masks"
        # self.main_window.graphics_view.scene().change_mask_color(
        #     idx, r, g, b, a)
        view = self.main_window.graphics_view
        # idx_map = {0: view.preannot_pmi, 1: view.annot_pmi}
        # pmi = idx_map[idx]
        if idx == 0:
            view.change_preannot_rgba((r, g, b, a))
            self.main_window.preannot_color = (r, g, b, a)
        elif idx == 1:
            view.change_annot_rgba((r, g, b, a))
            self.main_window.mask_color = (r, g, b, a)

    def brush_type_changed(self, idx):
        """
        Setter
        """
        self.current_brush_type = self.brush_names[idx]

    def brush_size_changed(self, sz):
        """
        Setter
        """
        self.current_brush_size = sz


# #############################################################################
# ## MAIN WINDOW
# #############################################################################
class MainWindow(QtWidgets.QMainWindow):
    """
    This is the central widget for the bimask application. It is a composition
    of all the used elements, together with the logic that binds them.
    """

    # These variables handle the preannotation thresholding. Check pmap_to_mask
    DISCARD_P_VALUE = 0.5  # Number in range (thresh_slider_max, 1]
    THRESH_MIN = 0.0000001
    THRESH_MAX = 0.000000001
    THRESH_NUM_STEPS = 400
    #
    PAINTER_TXT = "Painter"
    ERASER_TXT = "Eraser"
    MASKED_PAINTER_TXT = "Masked painter"
    POINT_LIST_TXT = "Points"

    def __init__(self, parent=None, initial_mask_color=(255, 54, 76, 150),
                 initial_preannot_color=(102, 214, 123, 100),
                 max_brush_size=200):
        """
        """
        super().__init__(parent)
        self.graphics_view = IntegratedDisplayView(self)
        #
        self.mask_color = initial_mask_color
        self.preannot_color = initial_preannot_color
        #
        self.current_img_basename = None
        #
        self.instructions_dialog = InstructionsDialog()
        self.about_dialog = AboutDialog()
        self.keymaps_dialog = KeymapsDialog(
            {k: v.toString() for k, v in self.keymaps().items()})
        # define controller widgets
        self.file_lists = FileLists()
        self.paint_form = CrackAnnotPaintForm(
            self, [self.PAINTER_TXT, self.ERASER_TXT, self.MASKED_PAINTER_TXT,
                   self.POINT_LIST_TXT],
            max_brush_size, thresh_min=self.THRESH_MIN,
            thresh_max=self.THRESH_MAX, thresh_num_steps=self.THRESH_NUM_STEPS)
        self.save_form = IntegratedSaveForm(self, default_path=None)

        self.paint_form.add_item("preannot.", self.preannot_color,
                                 slider_visible=True, activate=False)
        self.paint_form.add_item("annot.", self.mask_color,
                                 slider_visible=False, activate=True)
        # create controller layout
        controller_layout = QtWidgets.QVBoxLayout()
        controller_layout.addWidget(self.paint_form)
        controller_layout.addWidget(self.save_form)
        controller_widget = QtWidgets.QWidget()
        controller_widget.setLayout(controller_layout)
        self.controller_splitter = QtWidgets.QSplitter()
        self.controller_splitter.setOrientation(QtCore.Qt.Vertical)
        self.controller_splitter.addWidget(self.file_lists)
        self.controller_splitter.addWidget(controller_widget)
        # create main layout, add controller and graphics:
        self.main_splitter = QtWidgets.QSplitter()
        self.main_splitter.setOrientation(QtCore.Qt.Horizontal)
        self.main_splitter.addWidget(self.controller_splitter)
        self.main_splitter.addWidget(self.graphics_view)
        # fine-tune main layout: sizes and such
        self.controller_splitter.setMinimumWidth(10)
        left_width = self.controller_splitter.width()
        right_width = self.graphics_view.width()
        self.main_splitter.setSizes([left_width, right_width * 2])
        self.setCentralWidget(self.main_splitter)
        # add connections
        self.file_lists.img_list.file_list.itemDoubleClicked.connect(
            lambda elt: self._handle_img_selection(elt.text()))
        self.file_lists.mask_list.file_list.itemDoubleClicked.connect(
            lambda elt: self._handle_mask_selection(elt.text()))
        self.file_lists.preannot_list.file_list.itemDoubleClicked.connect(
            lambda elt: self._handle_preannot_selection(elt.text()))
        #
        self._setup_undo()
        self._setup_menu_bar()
        self._add_keymaps()

    def _setup_undo(self):
        """
        Set up undo stack and undo view
        """
        self.undo_stack = QtWidgets.QUndoStack(self)
        self.undo_view = QtWidgets.QUndoView(self.undo_stack)
        self.undo_view.setWindowTitle("Undo View")
        self.undo_view.setAttribute(QtCore.Qt.WA_QuitOnClose, False)

    def _setup_menu_bar(self):
        """
        Set up menu bar: create actions and connect them to methods.
        """
        # edit menu
        edit_menu = self.menuBar().addMenu("Edit")
        self.undo_action = edit_menu.addAction("Undo")
        self.undo_action.triggered.connect(self.undo_stack.undo)
        self.redo_action = edit_menu.addAction("Redo")
        self.redo_action.triggered.connect(self.undo_stack.redo)
        edit_menu.addSeparator()
        self.view_undo_action = edit_menu.addAction("View undo stack")
        self.view_undo_action.triggered.connect(self.undo_view.show)
        # help menu
        help_menu = self.menuBar().addMenu("Help")
        self.keyboard_shortcuts = help_menu.addAction("Keyboard shortcuts")
        self.keyboard_shortcuts.triggered.connect(self.keymaps_dialog.show)
        self.instructions = help_menu.addAction("Instructions")
        self.instructions.triggered.connect(self.instructions_dialog.show)
        self.about = help_menu.addAction("About")
        self.about.triggered.connect(self.about_dialog.show)

    def keymaps(self):
        """
        :returns: A dictionary in the form ``name: QtGui.QKeySequence``,
          where the

        Define this GUI's specific key mappings. Note that this method can
        be overriden to return a different mapping, but the ``name``s have
        to remain identical, in order to be recognized by ``_add_keymaps``.
        """
        d = {
            "Undo": QtGui.QKeySequence("Ctrl+Z"),
            "Redo": QtGui.QKeySequence("Ctrl+Y"),
            "View undo list": QtGui.QKeySequence("Alt+Z"),
            #
            "Load image path": QtGui.QKeySequence("Ctrl+I"),
            "Load mask path": QtGui.QKeySequence("Ctrl+M"),
            "Load preannotation path": QtGui.QKeySequence("Ctrl+P"),
            #
            "Save mask path": QtGui.QKeySequence("Alt+S"),
            "Save mask(s)": QtGui.QKeySequence("Ctrl+S"),
            #
            "Set painter": QtGui.QKeySequence("a"),
            "Set eraser": QtGui.QKeySequence("e"),
            "Set masked painter": QtGui.QKeySequence("m"),
            #
            "Next image": QtGui.QKeySequence("Space"),
            "Previous image": QtGui.QKeySequence("Ctrl+Space")
        }
        return d

    def _add_keymaps(self):
        """
        This function is closeley connected to ``keymaps``. There, the
        shortcuts are defined, here, they are applied.
        """
        km = self.keymaps()
        # add menu shortcuts
        self.undo_action.setShortcut(km["Undo"])
        self.redo_action.setShortcut(km["Redo"])
        self.view_undo_action.setShortcut(km["View undo list"])
        # add widget shortcuts
        #
        self.file_lists.img_list.file_button.setShortcut(km["Load image path"])
        self.file_lists.mask_list.file_button.setShortcut(km["Load mask path"])
        self.file_lists.preannot_list.file_button.setShortcut(
            km["Load preannotation path"])
        #
        self.save_form.file_dialog_button.setShortcut(km["Save mask path"])
        self.save_form.save_button.setShortcut(km["Save mask(s)"])
        # Paint region (wheel event has the brush size)
        QtWidgets.QShortcut(  # combobox shortcuts are a little more complex
            km["Set painter"], self.paint_form.brush_combo_box,
            lambda: self.paint_form.brush_combo_box.setCurrentText(
                self.PAINTER_TXT))
        QtWidgets.QShortcut(
            km["Set eraser"], self.paint_form.brush_combo_box,
            lambda: self.paint_form.brush_combo_box.setCurrentText(
                self.ERASER_TXT))
        QtWidgets.QShortcut(
            km["Set masked painter"], self.paint_form.brush_combo_box,
            lambda: self.paint_form.brush_combo_box.setCurrentText(
                self.MASKED_PAINTER_TXT))
        #
        QtWidgets.QShortcut(
            km["Next image"], self, lambda: self._switch_img(1))
        QtWidgets.QShortcut(
            km["Previous image"], self, lambda: self._switch_img(-1))

    def _switch_img(self, step=1):
        """
        An alternative way of double clicking on an image list is to call
        this method, which will switch to the image located at
        ``curent_img + step`` in the list.
        """
        curr_idx = self.file_lists.img_list.file_list.currentRow()
        nxt_item = self.file_lists.img_list.file_list.item(curr_idx + step)
        if nxt_item is not None:
            success = self._handle_img_selection(nxt_item.text())
            if success:
                self.file_lists.img_list.file_list.setCurrentItem(nxt_item)

    def _handle_img_selection(self, basename):
        """
        This protected method is triggered when double clicking on an
        image list item, or called by ``_switch_img``.
        """
        abspath = os.path.join(self.file_lists.img_list.dirpath, basename)
        success = self.graphics_view.new_image(abspath, self.mask_color,
                                               self.preannot_color)
        if success:
            self.current_img_basename = basename
        return success

    def _handle_mask_selection(self, basename):
        """
        This protected method is triggered when double clicking on an
        annotation list item.
        """
        abspath = os.path.join(self.file_lists.mask_list.dirpath, basename)
        self.graphics_view.mask_from_path(abspath, self.mask_color)

    def _handle_preannot_selection(self, basename):
        """
        This protected method is triggered when double clicking on a
        preannotation list item.
        """
        abspath = os.path.join(self.file_lists.preannot_list.dirpath, basename)
        pval = self.paint_form.slider_to_p_val(
            self.paint_form._sliders[-1].value())
        self.graphics_view.preannot_from_path(
            abspath, self.preannot_color, keep_p_value=pval,
            discard_p_value=self.DISCARD_P_VALUE)

    def wheelEvent(self, event):
        """
        The ``DisplayView`` has zoom functionality associated to the wheel.
        Here we associate 'brush size change' functionality when the wheel
        is rolled while pressing Control.
        """
        mods = event.modifiers()
        has_ctrl = bool(mods & QtCore.Qt.ControlModifier)
        has_alt = bool(mods & QtCore.Qt.AltModifier)
        has_shift = bool(mods & QtCore.Qt.ShiftModifier)
        if (has_ctrl, has_alt, has_shift) == (True, False, False):
            current = self.paint_form.brush_size_slider.value()
            delta = 1 if event.delta() >= 0 else - 1
            self.paint_form.brush_size_slider.setValue(current + delta)
