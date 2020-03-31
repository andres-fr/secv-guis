# -*- coding:utf-8 -*-


"""
This module contains definitions for different kinds of dialogs and related
components that are specific for this application.
"""


from PySide2 import QtWidgets
#
from . import INSTRUCTIONS, ABOUT
from ..dialogs import InfoDialog, FlexibleDialog


# #############################################################################
# ## HELP DIALOGS
# #############################################################################
class InstructionsDialog(InfoDialog):
    """
    Info dialog showing instructions
    """
    def __init__(self):
        """
        """
        super().__init__("INSTRUCTIONS", INSTRUCTIONS, print_msg=False)


class AboutDialog(InfoDialog):
    """
    Info dialog showing about section
    """
    def __init__(self):
        """
        """
        super().__init__("ABOUT", ABOUT, print_msg=False)


class KeymapsDialog(FlexibleDialog):
    """
    Info dialog showing keymap list
    """
    def __init__(self, mappings, parent=None):
        """
        """
        self.mappings = mappings
        super().__init__(parent=parent)

    def setup_ui_body(self, widget):
        """
        """
        lyt = QtWidgets.QVBoxLayout(widget)
        #
        self.list_widget = QtWidgets.QListWidget()
        for k, v in self.mappings.items():
            self.list_widget.addItem("{} ({})".format(k, v))
        lyt.addWidget(self.list_widget)


# #############################################################################
# ## SAVE DIALOGS
# #############################################################################
class SavedInfoDialog(InfoDialog):
    """
    Informative dialog telling about saved paths.
    """
    def __init__(self, save_dict, timeout_ms=500):
        """
        :param save_dict: A dict with ``mask_name: save_path`` pairs.
        """
        super().__init__("SAVED", self.save_dict_to_str(save_dict),
                         timeout_ms=timeout_ms,
                         header_style="font-weight: bold; color: green")

    @staticmethod
    def save_dict_to_str(save_dict):
        """
        """
        msg = "\n".join(["Saved {} to {}".format(k, v)
                         for k, v in save_dict.items()])
        return msg


class SaveWarningDialog(InfoDialog):
    """
    A dialog to be prompted when trying to delete unsaved changes.
    Usage example::

      self.dialog = SaveWarningDialog()
      user_wants_to_remove = bool(self.dialog.exec_())
      ...
    """

    def __init__(self):
        """
        """
        super().__init__("WARNING",
                         "DELETE unsaved changes?",
                         "YES, delete and continue", "NO, go back",
                         print_msg=False)
        self.reject_b.setDefault(True)


class SavedStateTracker:
    """
    Create one of these every time a new state is loaded, call ``edited`` when
    the state has been changed, and ``saved`` when saved.

    The ``saved`` function will optionally show an informative dialog.

    Then call ``delete`` when the state is intended to be deleted. The method
    makes sure that unsaved changes are only deleted with user's confirmation.

    Note for developers:

    State machines with callbacks are a classic recipe for spaghetti alla
    callback inferno. Here we didn't provide a structured way to handle GUI
    state, so we are applying this as high in the API as possible.
    It works NOW, but consider restructuring it if it gets in the way.
    """

    def __init__(self):
        """
        """
        self._dialog = None
        #
        self._has_unsaved_changes = False
        self._has_been_deleted = False

    def edit(self):
        """
        Call this any time the state that we want to track has been edited
        """
        # bug factory
        # assert not self._has_been_deleted, \
        #     "Deleted tracker cannot be further used! create a new one"
        self._has_unsaved_changes = True

    def save(self, saved_dict=None, ok_dialog_ms=1000):
        """
        Call this any time the state that we want to track has been saved
        """
        # bug factory
        # assert not self._has_been_deleted, \
        #     "Deleted tracker cannot be further used! create a new one"
        self._has_unsaved_changes = False
        if saved_dict is not None:
            self.dialog = SavedInfoDialog(saved_dict, ok_dialog_ms)
            self.dialog.show()

    def delete(self):
        """
        Call this when we intend to delete the information that we are
        tracking. If unsaved changes, it will prompt the user to continue.
        """
        # bug factory
        # assert not self._has_been_deleted, \
        #     "Deleted tracker cannot be further used! create a new one"
        if self._has_unsaved_changes:
            self.dialog = SaveWarningDialog()
            user_wants_delete = bool(self.dialog.exec_())
            if not user_wants_delete:
                # in this case the user hit this by mistake, so
                # we return False and do nothing
                return False
        # if we reach this point, it means that either we don't have
        # unsaved changes, or we have but the user is OK with deleting them
        self._has_been_deleted = True
        return True
