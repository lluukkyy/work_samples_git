# -*- coding: utf-8 -*-
"""
Created on Fri May 17 11:21:40 2019

@author: Xiangyang Mou
@email: moutaigua8183@gmail.com
"""

import os, sys
V1Folder = os.path.dirname(os.path.abspath(__file__))
sys.path.append(V1Folder)
from dependencies import mics


if __name__ == '__main__':
    PidFile = os.path.join(V1Folder, 'dialogue_engine_subprocess_pid.dat')
    mics.killPidByFile(PidFile)


