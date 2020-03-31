# -*- coding:utf-8 -*-


"""
This module is a library of reusable, extendable widgets.
"""


import os
from PySide2 import QtCore, QtWidgets


# #############################################################################
# # BASIC WIDGETS
# #############################################################################
class FileList(QtWidgets.QWidget):
    """
    A file dialog button followed by a list that shows the files in the
    selected folder.
    """
    def __init__(self, label, parent=None,
                 default_path=None, extensions=None, sort=True):
        """
        :param extensions: A list of string terminations to match, or ``None``
          for match-all.
        :param default_path: If None, 'home' is picked as default.
        :param sort: If true, contents will always be shown sorted
        """
        super().__init__(parent)
        self.sort = sort
        self.dirpath = (os.path.expanduser("~") if default_path is None
                        else default_path)
        self.extensions = [""] if extensions is None else extensions
        self.label = label
        # create widgets
        self.file_button = QtWidgets.QPushButton(self.label)
        self.file_list = QtWidgets.QListWidget()
        # add widgets to layout
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.addWidget(self.file_button)
        self.main_layout.addWidget(self.file_list)
        # connect
        self.file_button.pressed.connect(self._file_dialog_handler)
        # track filesystem changes
        self.file_watcher = QtCore.QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(
            lambda: self.update_path(self.dirpath))
        self.file_watcher.directoryChanged.connect(
            lambda: self.update_path(self.dirpath))

    def update_path(self, dirname):
        """
        :param str dirname: The new directory path to be listed.
        """
        file_names = [f for f in os.listdir(dirname)
                      if f.lower().endswith(tuple(self.extensions))]
        self.file_list.clear()
        self.file_list.addItems(file_names)
        #
        self.file_watcher.removePath(self.dirpath)
        self.file_watcher.addPath(dirname)
        #
        self.dirpath = dirname
        if self.sort:
            self.file_list.sortItems(QtCore.Qt.AscendingOrder)

    def _file_dialog_handler(self):
        """
        Opens a file dialog which returns the selected path.
        """
        dirname = QtWidgets.QFileDialog.getExistingDirectory(
            self, self.label, self.dirpath)
        if dirname:
            self.update_path(dirname)


class CheckBoxGroup(QtWidgets.QWidget):
    """
    A group of ``CheckBox`` es
    """
    def __init__(self, parent=None, horizontal=False):
        """
        """
        super().__init__(parent=parent)
        ly = QtWidgets.QHBoxLayout() if horizontal else QtWidgets.QVBoxLayout()
        self.setLayout(ly)

    def add_box(self, name, tristate=False, initial_val=True):
        """
        :param bool tristate: If true, the added check box will have 3 states.
        """
        b = QtWidgets.QCheckBox(name)
        b.setTristate(tristate)
        b.setChecked(initial_val)
        self.layout().addWidget(b)

    def remove_box(self, idx):
        """
        :param int idx: Boxes are added in increasing index order, so this
          the lower this index the 'older' the box that is being removed.
        """
        b = self.layout().takeAt(idx)
        b.widget().setParent(QtWidgets.QWidget())  # this is needed...

    def state(self):
        """
        :returns: A list with all the current states, in index order.
        """
        ly = self.layout()
        return [ly.itemAt(i).widget().checkState() for i in range(ly.count())]


# #############################################################################
# # PAINTING SECTION
# #############################################################################
class RGBASpinbox(QtWidgets.QWidget):
    """
    A cluster of 4 [0-255] spin boxes, representing (and having) an RGBA
    color. Use ``self.connect`` to wire this widget to any method.
    """

    def __init__(self, initial_rgba=(0, 255, 0, 100), parent=None,
                 min_alpha=1, max_alpha=255):
        """
        """
        super().__init__(parent)
        self.main_layout = QtWidgets.QHBoxLayout(self)
        # create widgets
        self.label = QtWidgets.QLabel("RGBA:")
        r, g, b, a = initial_rgba
        self.r = self._make_box(initial=r)
        self.g = self._make_box(initial=g)
        self.b = self._make_box(initial=b)
        self.a = self._make_box(a, min_alpha, max_alpha)
        # add widgets to layout
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.r)
        self.main_layout.addWidget(self.g)
        self.main_layout.addWidget(self.b)
        self.main_layout.addWidget(self.a)
        # connect widgets to color listener
        self.r.valueChanged.connect(
            lambda: self._set_currentcolor_stylesheet())
        self.g.valueChanged.connect(
            lambda: self._set_currentcolor_stylesheet())
        self.b.valueChanged.connect(
            lambda: self._set_currentcolor_stylesheet())
        self.a.valueChanged.connect(
            lambda: self._set_currentcolor_stylesheet())
        #
        self._set_currentcolor_stylesheet()

    @staticmethod
    def _make_box(initial=100, minimum=0, maximum=255, step=8):
        """
        """
        b = QtWidgets.QSpinBox()
        b.setRange(minimum, maximum)
        b.setSingleStep(step)
        b.setValue(initial)
        return b

    def get_current_rgba(self):
        """
        :returns: Current state as ``(r, g, b, a)`` numeric tuple.
        """
        r = self.r.value()
        g = self.g.value()
        b = self.b.value()
        a = self.a.value()
        return(r, g, b, a)

    def _set_currentcolor_stylesheet(self):
        """
        """
        r, g, b, _ = self.get_current_rgba()
        ssheet = "QSpinBox {color: rgb(%d, %d, %d)}" % (r, g, b)
        self.r.setStyleSheet(ssheet)
        self.g.setStyleSheet(ssheet)
        self.b.setStyleSheet(ssheet)
        self.a.setStyleSheet(ssheet)

    def connect(self, fn):
        """
        :param fn: A function to connect this widget to. It must have the
          following signature``fn(idx, r, g, b, a)``.

        When calling ``self.connect(f)``, any value changes in R, G, B or
        A will trigger ``f(r, g, b, a)`` with the changed values
        """
        # NOTE THAT LAMBDAS WITH SELF INSIDE WILL PREVENT THE WIDGET
        # TO BE GARBAGE-COLLECTED: https://stackoverflow.com/a/48501804/4511978
        # THIS IS BAD FOR WIDGETS THAT GET INSTANTIATED MANY TIMES
        self.r.valueChanged.connect(lambda: fn(*self.get_current_rgba()))
        self.g.valueChanged.connect(lambda: fn(*self.get_current_rgba()))
        self.b.valueChanged.connect(lambda: fn(*self.get_current_rgba()))
        self.a.valueChanged.connect(lambda: fn(*self.get_current_rgba()))


class MaskPaintForm(QtWidgets.QWidget):
    """
    This widget contains one section for the masks and one for the painter.
    The mask section contains a set of elements, one per mask. A radio button
    selects the currently active mask, and each mask features an RGBA box
    and a thershold slider. The painter section contains a ComboBox to select
    the painter type, and a slider for the painter size.

    To use it in specific applications override ``button_pressed,
    combo_box_changed, rgba_box_changed...``
    """
    def __init__(self, brush_names, max_brush_size=100, parent=None,
                 thresh_min=0, thresh_max=1, thresh_num_steps=100,
                 min_alpha=1, max_alpha=255):
        """
        """
        super().__init__(parent)
        # self.masks = masks
        self.brush_names = brush_names
        self.max_brush_size = max_brush_size
        self.thresh_min = thresh_min
        self.thresh_max = thresh_max
        self.thresh_num_steps = thresh_num_steps
        self.min_alpha = min_alpha
        self.max_alpha = max_alpha
        #
        self._buttons = []
        self._boxes = []
        self._labels = []
        self._sliders = []
        #
        self.paint_button_group = QtWidgets.QButtonGroup(self)
        self._define_layout()
        # add connections
        # NOTE THAT LAMBDAS WITH SELF INSIDE WILL PREVENT THE WIDGET
        # TO BE GARBAGE-COLLECTED: https://stackoverflow.com/a/48501804/4511978
        # THIS IS BAD FOR WIDGETS THAT GET INSTANTIATED MANY TIMES
        self.paint_button_group.buttonClicked.connect(
            lambda _: self.button_pressed(
                self.paint_button_group.checkedButton()))
        self.brush_combo_box.currentIndexChanged.connect(
            self.brush_type_changed)
        self.brush_size_slider.valueChanged.connect(self._update_brush_size)

    def _define_layout(self):
        """
        """
        # make brush selector and size widgets
        self.brush_combo_box = QtWidgets.QComboBox()
        self.brush_combo_box.addItems(self.brush_names)
        self.brush_size_label = QtWidgets.QLabel()
        self.brush_size_slider = QtWidgets.QSlider(None)  # vertical
        self.brush_size_slider.setMinimum(1)
        self.brush_size_slider.setMaximum(self.max_brush_size)
        self.brush_size_slider.setValue(self.max_brush_size // 2)
        self.brush_size_slider.setSingleStep(1)
        self._set_brush_size_label(self.brush_size_slider.value())
        # Layout hierarchy:
        main_layout = QtWidgets.QHBoxLayout()
        # this is modified with add/remove
        self.masks_layout = QtWidgets.QVBoxLayout()
        # make sub-layout with [brush_type; brush_size]
        brush_layout = QtWidgets.QVBoxLayout()
        brush_layout.addWidget(self.brush_combo_box)
        brush_layout.addWidget(self.brush_size_label)
        brush_layout.addWidget(self.brush_size_slider)
        brush_layout.setAlignment(QtCore.Qt.AlignRight)
        # connect layout hierarchy
        main_layout.addLayout(self.masks_layout)
        main_layout.addLayout(brush_layout)
        self.setLayout(main_layout)

    def add_item(self, name, rgba, slider_visible=True, activate=False):
        """
        Add an element to the 'mask' section, with the given name and color.

        :param slider_visible: If false, the slider will be still there but
          hidden.
        :param activate: Once created, select this item in the radio buttons.
        """
        # sub-layout with 2-row elts: [button, colordialog; label, threshold]
        but = QtWidgets.QRadioButton(name)
        box = RGBASpinbox(rgba, None, self.min_alpha, self.max_alpha)
        sl = QtWidgets.QSlider(None, orientation=QtCore.Qt.Horizontal)
        lbl = QtWidgets.QLabel()
        sl.setVisible(slider_visible)
        lbl.setVisible(slider_visible)
        sl.setMinimum(0)
        sl.setMaximum(self.thresh_num_steps)
        sl.setSingleStep(1)
        sl.setValue(sl.maximum() // 2)
        #
        self._buttons.append(but)
        self._boxes.append(box)
        self._labels.append(lbl)
        self._sliders.append(sl)
        # local layout hierarchy
        lyt = QtWidgets.QVBoxLayout()
        top = QtWidgets.QHBoxLayout()
        bottom = QtWidgets.QHBoxLayout()
        top.addWidget(but)
        top.addWidget(box)
        bottom.addWidget(lbl)
        bottom.addWidget(sl)
        lyt.addLayout(top)
        lyt.addLayout(bottom)
        # add local hierarchy to main layout and button to group
        self.masks_layout.addLayout(lyt)
        self.paint_button_group.addButton(but)
        # add connections
        box.connect(
            lambda r, g, b, a: self._handle_rgba_box_changed(box, r, g, b, a))
        sl.valueChanged.connect(
            lambda val: self._handle_threshold_slider_changed(sl, val))
        # initialize label
        self._set_thresh_label(lbl, sl.value())
        #
        if activate:
            but.click()

    def remove_item(self, idx):
        """
        Remove an element from the 'mask' section by index. Indexes are in
        increasing order, so lowest is oldest.
        """
        # remove from self placeholders
        but = self._buttons.pop(idx)
        box = self._boxes.pop(idx)
        lbl = self._labels.pop(idx)
        sl = self._sliders.pop(idx)
        lyt = self.masks_layout.takeAt(idx)
        # reassign dummy parent to remove from QT placeholders
        w = QtWidgets.QWidget()  # this is needed...
        but.setParent(w)
        box.setParent(w)
        lbl.setParent(w)
        sl.setParent(w)
        lyt.setParent(w)

    def slider_to_p_val(self, sl_val):
        """
        Since the slider goes from 0 to ``thresh_num_steps``, this function
        linearly interpolates the, so that 0 maps to ``thresh_min`` and
        ``thresh_num_steps`` maps to ``thresh_max``. Note that min does not
        neccesarily have to be smaller than max.

        :param int sl_val: The actual slider value from 0 to num_steps.
        :returns: The converted and interpolated value.
        """
        delta = float(sl_val) / self.thresh_num_steps
        pval = self.thresh_min + delta * (self.thresh_max - self.thresh_min)
        return pval

    def _set_thresh_label(self, lbl, sl_val):
        """
        """
        t = self.slider_to_p_val(sl_val)
        lbl.setText("Thresh: {:.10f}".format(t))
        return t

    def _set_brush_size_label(self, sl_val):
        """
        """
        self.brush_size_label.setText("Brush size: {}".format(sl_val))

    def _handle_threshold_slider_changed(self, sl, sl_val):
        """
        """
        idx = self._sliders.index(sl)
        t = self._set_thresh_label(self._labels[idx], sl_val)
        self.threshold_slider_changed(idx, t)

    def _handle_rgba_box_changed(self, box, r, g, b, a):
        """
        """
        idx = self._boxes.index(box)
        self.rgba_box_changed(idx, r, g, b, a)

    def _update_brush_size(self, sl_val):
        """
        """
        self._set_brush_size_label(sl_val)
        self.brush_size_changed(sl_val)

    def button_pressed(self, but):
        """
        Override me!

        :param int idx: Starts with 0 and respects ordering given at
          construction. So when overriding this method, you can assume
          that 0 will correspond to the firstly added element, and
          so on. Implementation example::

            i = self._buttons.index(but)
            print("button pressed: >>>", i, but.text())
        """
        pass

    def brush_type_changed(self, idx):
        """
        Override me!

        :param int idx: Starts with 0 and respects ordering given at
          construction. So when overriding this method, you can assume
          that 0 will correspond to the firstly added element, and
          so on.
        """
        pass

    def brush_size_changed(self, sz):
        """
        Override me!
        """
        pass

    def rgba_box_changed(self, idx, r, g, b, a):
        """
        Override me!
        """
        pass

    def threshold_slider_changed(self, idx, val):
        """
        Override me!
        """
        pass


# #############################################################################
# # SAVING SECTON
# #############################################################################
class SaveForm(QtWidgets.QWidget):
    """
    A formulary providing functionality for selecting what to save, where to
    save, the output suffix and overwriting policy.
    """

    SAVE_TEXT = "Save\nselected"
    DIALOG_TEXT = "Output\nfolder"
    OVERWRITE_TEXT = "Overwrite\nsaved"

    def __init__(self, parent=None, default_path=None):
        """
        :param str default_path: If not given, 'home' is picked as default.
        """
        super().__init__(parent)
        self.save_path = (os.path.expanduser("~") if default_path is None
                          else default_path)
        # create widgets
        self.save_group = CheckBoxGroup()
        self.text_boxes = QtWidgets.QVBoxLayout()
        self.file_dialog_button = QtWidgets.QPushButton(self.DIALOG_TEXT)
        self.save_button = QtWidgets.QPushButton(self.SAVE_TEXT)
        self.overwrite_button = QtWidgets.QCheckBox(self.OVERWRITE_TEXT)
        self.overwrite_button.setChecked(True)
        # build layout hierarchy
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addWidget(self.save_group)
        self.main_layout.addLayout(self.text_boxes)
        #
        lyt = QtWidgets.QVBoxLayout()
        lyt.addWidget(self.file_dialog_button)
        lyt.addWidget(self.save_button)
        lyt.addWidget(self.overwrite_button)
        self.main_layout.addLayout(lyt)
        self.setLayout(self.main_layout)
        # add connections
        self.file_dialog_button.clicked.connect(self._change_save_path)
        self.save_button.clicked.connect(self._handle_save_masks)

    def add_checkbox(self, checkbox_name, initial_val=True, initial_txt=None):
        """
        Adds an element that can be selected to be saved.

        :param checkbox_name: The element identifier
        :param initial_txt: The initial suffix to be appended to the files. If
          none is given, the ``checkbox_name`` is picked as default. The user
          can change this from the GUI.
        """
        if initial_txt is None:
            initial_txt = checkbox_name
        tb = QtWidgets.QLineEdit(initial_txt)
        #
        self.save_group.add_box(checkbox_name, False, initial_val)
        self.text_boxes.addWidget(tb)

    def _change_save_path(self):
        """
        """
        dir_name = QtWidgets.QFileDialog.getExistingDirectory(
            self, self.DIALOG_TEXT, self.save_path)
        if dir_name:
            self.save_path = dir_name

    def _handle_save_masks(self):
        """
        """
        states = [s == QtCore.Qt.CheckState.Checked
                  for s in self.save_group.state()]
        suffixes = [self.text_boxes.itemAt(i).widget().text()
                    for i in range(self.text_boxes.count())]
        overwrite = self.overwrite_button.isChecked()
        self.save_masks(states, suffixes, overwrite)

    def save_masks(self, states, suffixes, overwrite):
        """
        :param states: A list with booleans, representing the checkbox
          states for the contained elements.
        :param suffixes: A list with the corresponding suffixes
        :param overwrite: A boolean determining whether the 'overwrite'
          checkbox has been activated.

        Override me!
        """
        print("check boxes:", states, "suffixes:", suffixes,
              "out path:", self.save_path, "overwrite:", overwrite)
