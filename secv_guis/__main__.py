# -*- coding:utf-8 -*-


"""
"""


import sys
import argparse
#
from PySide2 import QtWidgets
#
from .bimask_app.main_window import MainWindow as BimaskMainWindow
from .dialogs import ExceptionDialog


def run_bimask_app():
    """
    """
    app = QtWidgets.QApplication(["SECV GUI"])
    mw = BimaskMainWindow()
    mw.show()
    # Wrap any exceptions into a dialog
    sys.excepthook = ExceptionDialog.excepthook
    # run app
    sys.exit(app.exec_())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run different GUIs.")

    parser.add_argument("--app", type=str, default="bimask",
                        help="The name of the app you want to run")
    args = parser.parse_args()
    #
    APP_NAME = args.app
    #
    if APP_NAME == "bimask":
        run_bimask_app()
    else:
        print("Unknown app name!")
