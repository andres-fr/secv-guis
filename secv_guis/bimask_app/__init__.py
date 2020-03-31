# -*- coding:utf-8 -*-


"""
"""


import os


__author__ = "Andres FR"
__email__ = "aferro@em.uni-frankfurt.de"


with open(os.path.join(os.path.dirname(__file__),
                       "instructions.txt"), "r") as f:
    INSTRUCTIONS = f.read()
with open(os.path.join(os.path.dirname(__file__),
                       "about.txt"), "r") as f:
    ABOUT = f.read()
