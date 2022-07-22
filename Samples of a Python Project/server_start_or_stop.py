# -*- coding: utf-8 -*-
"""
Created on Fri Oct 11 19:48:01 2019

@author: Xiangyang Mou
@email: moutaigua8183@gmail.com
"""


import os, sys
import subprocess
VersionFolder   = os.path.dirname(os.path.abspath(__file__))
RootFolder      = os.path.dirname(VersionFolder)
sys.path.insert(0, os.path.join(VersionFolder, 'dependencies'))
import systemHandler
import mics


ServerFolder = os.path.join(VersionFolder, 'server')
ServerPidFile = os.path.join(ServerFolder, 'server_subprocess_pid.dat')
EnginePidFile = os.path.join(VersionFolder, 'dialogue_engine_subprocess_pid.dat')
SpeakerWorkerFolder = os.path.join(RootFolder, 'speaker_worker_helper')



if __name__ == '__main__':
    system = systemHandler.SystemHandler()
    if not os.path.exists(ServerPidFile):
        serverPid = subprocess.Popen([system.settings['python_command'], 'web_server.py'], cwd=ServerFolder, shell=False).pid
        try:
            speakerWorkerPid = subprocess.Popen(['node', 'mp_speaker_worker.js'], cwd=SpeakerWorkerFolder, shell=False).pid
        except:
            speakerWorkerPid = ''
        with open(ServerPidFile, 'w') as fp:
            print(serverPid,        file=fp)
            print(speakerWorkerPid, file=fp)
    else:
        mics.killPidByFile(ServerPidFile)
        mics.killPidByFile(EnginePidFile)