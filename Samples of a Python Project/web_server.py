# -*- coding: utf-8 -*-
"""
Created on Tue May 21 23:23:30 2019

@author: Xiangyang Mou
@email: moutaigua8183@gmail.com
"""

import os, json, sys, time
import copy
import subprocess


from flask import Flask
from flask import render_template, request, send_from_directory
from flask_socketio import SocketIO, send, emit, join_room, leave_room
import logging


UiFolder = os.path.dirname(os.path.abspath(__file__))
VxFolder = os.path.dirname(UiFolder)
ResourceFolder = os.path.join(VxFolder, 'resources/')
TemplateFolder = os.path.join(UiFolder, 'static/html')
LanguageDictByUuid = dict()
ResourceDict = dict()
ConnectionDict = dict()


sys.path.append(VxFolder)
sys.path.append(os.path.join(VxFolder, 'dependencies'))
from conversationHandler import ConversationHandler
from dependencies import systemHandler, commHandler, mics



app = Flask(__name__, template_folder=TemplateFolder)
socketio = SocketIO(app)
# disable logging in console
log = logging.getLogger('werkzeug')
log.disabled = True

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('dialogue_test.html')

@app.route("/html/dashboard.html", methods=['GET', 'POST'])
def open_page_dashboard():
    return render_template('dashboard.html')

@app.route("/html/dialogue_test.html", methods=['GET', 'POST'])
def open_page_test():
    return render_template('dialogue_test.html')

@app.route("/html/language_editor.html", methods=['GET', 'POST'])
def open_page_editor():
    return render_template('language_editor.html')

@app.route("/html/dialogue_builder.html", methods=['GET', 'POST'])
def open_page_builder():
    return render_template('dialogue_builder.html')

@app.route('/file/<path:filename>')
def open_file(filename):
    return send_from_directory('static/file', filename)




@socketio.on('connect')
def handle_on_connect():
    global system, ResourceDict
    source = request.args.get('from')
    connId = request.args.get('connId')
    if source=='dashboard':
        join_room('dialogue_dashboard')
        emit('server_info', SERVER_INFO, room='dialogue_dashboard')
    elif source=='test':
        ConnectionDict[connId] = dict()
        ConnectionDict[connId]['created_at'] = time.time()
        ConnectionDict[connId]['handler'] = ConversationHandler()
        ConnectionDict[connId]['handler'].GlobalSetting['difficulty'] = system.getDifficultyLevel()
        # print(ConnectionDict)
        emit('config_setting', {'difficulty_level_init': system.getDifficultyLevel()})
    elif source=='editor':
        LoadPolicyFiles()
        languagePool = __reformatAllLanguages() 
        emit('language_loaded', languagePool)
    elif source=='builder':
        if len(ResourceDict)==0:
            LoadPolicyFiles()
        emit('resource_loaded', ResourceDict)




@socketio.on('server_status_change')
def handle_on_server_status_change(message):
    global VxFolder, SERVER_INFO, system
    PidFile = os.path.join(VxFolder, 'dialogue_engine_subprocess_pid.dat')
    if message['action'] == 'start':
        if not os.path.exists(PidFile):
            serverPid = subprocess.Popen([system.settings['python_command'], 'start_dialogue_engine.py'], cwd=VxFolder).pid
            with open(PidFile, 'w') as file:
                print(serverPid, file=file)
            SERVER_INFO['logs'].append('[*] Server is running...\n')
            socketio.emit('server_info', SERVER_INFO, room='dialogue_dashboard')
    elif message['action'] == 'stop':
        if os.path.exists(PidFile):
            mics.killPidByFile(PidFile)
            SERVER_INFO['logs'].append('[*] Server has been terminated...\n')
            socketio.emit('server_info', SERVER_INFO, room='dialogue_dashboard')
            

@socketio.on('server_reset_user')
def handle_on_server_reset(message):
    global serverSender
    serverSender.send('amq.topic', 'MpDialogue.server.reset', json.dumps(message))




@socketio.on('utterance_submit_from_test_page')
def handle_utterance_submit_from_test_page(message):
    global ConnectionDict, system
    connId = message['connId']
    text = message['text']
    agent = message['agent']
    outLanguage = message['language']
    ConnectionDict[connId]['handler'].GlobalSetting["output_language"]=outLanguage
    difficulty = message['difficulty']


    if agent not in ConnectionDict[connId]['handler'].ConversationDict:
        ConnectionDict[connId]['handler'].startConversation(connId, connId, agent=agent.lower())


    # if agent not in ConnectionDict[connId]['handler'].ConversationDict:
    #     ConnectionDict[connId]['handler'].startConversation('Test_Page_Debugger',connId, agent=agent.lower())
    # if system.settings['transcript_correction']:
    #     correctedText = ConnectionDict[connId]['handler'].correctTranscript(text, agent)
    #     if correctedText != text:
    #         text = correctedText
    #         print('Corrected >>', correctedText)
    
    response, debug_info = ConnectionDict[connId]['handler'].getResponse(
        agent, 
        {'msg': text, 'wakeword': agent, 'username': 'on_test_page', 'channelIndex': 0, 'userId': 0}, 
        difficulty,
        outLanguage
    )

    emit('utterance_response', {
                'response': response,
                'debug_info': debug_info
            })

    for i in ConnectionDict[connId]['handler'].GlobalSetting:
        print(i,ConnectionDict[connId]['handler'].GlobalSetting[i])
    emit('config_setting', {
            'output_language': outLanguage,
            'difficulty_level': ConnectionDict[connId]['handler'].GlobalSetting['difficulty']
            })
    

@socketio.on('utterance_submit_from_dashboard_page')
def handle_utterance_submit_from_dashboard_page(message):
    global serverSender
    serverSender.send('amq.topic', 'Unity.transcript', json.dumps(message))
    


    
@socketio.on('conversation_reset')
def handle_conversation_reset(message):
    global ConnectionDict
    connId = message['connId']
    agent = message['agent'].lower()
    if agent in ConnectionDict[connId]['handler'].ConversationDict:
        ConnectionDict[connId]['handler'].ConversationDict[agent].reset()

        
@socketio.on('language_edited')
def handle_language_edited(message):
    global LanguageDictByUuid
    for langId, updates in message['update'].items():
        LanguageDictByUuid[langId]['CN'] = updates['CN']
        LanguageDictByUuid[langId]['EN'] = updates['EN']
        LanguageDictByUuid[langId]['difficulty'] = int(updates['difficulty'])
        LanguageDictByUuid[langId]['slot'] = updates['slot']
        LanguageDictByUuid[langId]['jump_to_intent'] = updates['jump_to_intent']
    for eachOperation in message['add_del']:
        if eachOperation['operation'] == 'delete':
            print('delete', eachOperation['object'])
            del LanguageDictByUuid[eachOperation['object']]
            __deleteLanguageByUuid(eachOperation['object'])
    UpdatePolicyFiles()
    
@socketio.on('update_json_from_builder')
def updatePolicyJsonFromBuilder(new_json, mode):
    global ResourceDict
    if (mode == 'policy'):
        with open(os.path.join(ResourceFolder, 'policy.json'), 'w', encoding='utf-8') as fp:
            json.dump(new_json, fp, ensure_ascii=False, indent=4)
    elif (mode == 'placeholder'):
        with open(os.path.join(ResourceFolder, 'placeholder_data.json'), 'w', encoding='utf-8') as fp:
            json.dump(new_json, fp, ensure_ascii=False, indent=4)
    LoadPolicyFiles()
    emit('resource_loaded', ResourceDict)

@socketio.on('create_slot_file_from_builder')
def createSlotFileFromBuilder(agent):
    global ResourceDict
    template = {"slot": [], "option": []}
    with open(os.path.join(ResourceFolder, agent + '_slot_auxiliary.json'), 'w', encoding='utf-8') as fp:
        json.dump(template, fp, ensure_ascii=False, indent=4)
    LoadPolicyFiles()
    emit('slot_file_reload', ResourceDict)

@socketio.on('remove_slot_file_from_builder')
def removeSlotFileFromBuilder(agent):
    global ResourceDict
    os.remove(os.path.join(ResourceFolder, agent + '_slot_auxiliary.json'))
    LoadPolicyFiles()
    emit('slot_file_reload', ResourceDict)

@socketio.on('update_slot_file_from_builder')
def updateSlotFileFromBuilder(filename, slot_json):
    global ResourceDict
    with open(os.path.join(ResourceFolder, filename), 'w', encoding='utf-8') as fp:
        json.dump(slot_json, fp, ensure_ascii=False, indent=4)
    LoadPolicyFiles()
    emit('slot_file_reload', ResourceDict)


def __reformatAllLanguages():
    ''' reformat the files '''
    global ResourceDict, LanguageDictByUuid
    LanguageDictByUuid.clear()
    languagePool = dict()
    for filename, eachFile in ResourceDict.items():
        if 'option' in eachFile:
            # xxxxx_auxiliary.json file
            languagePool[filename] = dict()
            languagePool[filename]['slot'] = eachFile['slot']
            languagePool[filename]['language'] = []
            for eachBlock in eachFile['option']:
                LanguageDictByUuid[eachBlock['uuid']] = eachBlock
                newCopy = copy.deepcopy(eachBlock)
                newCopy['condition'] = 'When trying to fill out the slot of '
                newCopy['condition_para'] = newCopy['slot']
                newCopy['path'] = 'option'
                languagePool[filename]['language'].append(newCopy)
                if 'auto_fill' in eachBlock:
                    for eachAutoBlock in eachBlock['auto_fill']:
                        LanguageDictByUuid[eachAutoBlock['uuid']] = eachAutoBlock
                        newCopy = copy.deepcopy(eachAutoBlock)
                        newCopy['condition'] = 'The auto_fill for the slot of '
                        newCopy['condition_para'] = eachBlock['slot']
                        newCopy['path'] = 'option/auto_fill'
                        languagePool[filename]['language'].append(newCopy)
        elif 'policy' in filename:
            # policy.json file
            for agentName, eachAgent in eachFile.items():
                languagePool[agentName] = dict()
                languagePool[agentName]['language'] = []
                for intentName, intentContent in eachAgent['action'].items():
                    if intentName == 'error_handling':
                        for error_type, error_responses in intentContent.items():
                            for eachBlock in error_responses:
                                LanguageDictByUuid[eachBlock['uuid']] = eachBlock
                                newCopy = copy.deepcopy(eachBlock)
                                newCopy['condition'] = 'When a certain error happens: '
                                newCopy['condition_para'] = error_type
                                newCopy['path'] = 'action/' + error_type
                                languagePool[agentName]['language'].append(newCopy)
                                if 'auto_fill' in eachBlock:
                                    for eachAutoBlock in eachBlock['auto_fill']:
                                        LanguageDictByUuid[eachAutoBlock['uuid']] = eachAutoBlock
                                        newCopy = copy.deepcopy(eachAutoBlock)
                                        newCopy['condition'] = 'The auto_fill for the error of '
                                        newCopy['condition_para'] = error_type
                                        newCopy['path'] = 'action/' + error_type + '/auto_fill'
                                        languagePool[filename]['language'].append(newCopy)
                    elif type(intentContent) == list:
                        for eachBlock in intentContent:
                            LanguageDictByUuid[eachBlock['uuid']] = eachBlock
                            newCopy = copy.deepcopy(eachBlock)
                            newCopy['condition'] = 'When user means '
                            newCopy['condition_para'] = intentName
                            newCopy['path'] = 'action/' + intentName
                            languagePool[agentName]['language'].append(newCopy)
                            if 'auto_fill' in eachBlock:
                                for eachAutoBlock in eachBlock['auto_fill']:
                                    LanguageDictByUuid[eachAutoBlock['uuid']] = eachAutoBlock
                                    newCopy = copy.deepcopy(eachAutoBlock)
                                    newCopy['condition'] = 'The auto_fill for the intent of '
                                    newCopy['condition_para'] = intentName
                                    newCopy['path'] = 'action/' + intentName + '/auto_fill'
                                    languagePool[agentName]['language'].append(newCopy)
    return languagePool


def __deleteLanguageByUuid(langId):
    global ResourceDict
    for filename, eachFile in ResourceDict.items():
        if 'option' in eachFile:
            # xxxxx_auxiliary.json file
            for idx in range(len(eachFile['option'])):
                if eachFile['option'][idx]['uuid'] == langId:
                    del eachFile['option'][idx]
                    return
                if 'auto_fill' in eachFile['option'][idx]:
                    for autoIdx in range(len(eachFile['option'][idx]['auto_fill'])):
                        if eachFile['option'][idx]['auto_fill'][autoIdx]['uuid'] == langId:
                            del eachFile['option'][idx]['auto_fill'][autoIdx]
                            return
        else:
            # policy.json file
            for agentName, eachAgent in eachFile.items():
                for intentName, intentContent in eachAgent['action'].items():
                    if intentName == 'error_handling':
                        for error_type, error_responses in intentContent.items():
                            for idx in range(len(error_responses)):
                                if error_responses[idx]['uuid'] == langId:
                                    del error_responses[idx]
                                    return
                                if 'auto_fill' in error_responses[idx]:
                                    for autoIdx in range(len(error_responses[idx]['auto_fill'])):
                                        if error_responses[idx]['auto_fill'][autoIdx]['uuid'] == langId:
                                            del error_responses[idx]['auto_fill'][autoIdx]
                                            return
                    elif type(intentContent) == list:
                        for idx in range(len(intentContent)):
                            if intentContent[idx]['uuid'] == langId:
                                del intentContent[idx]
                                return
                            if 'auto_fill' in intentContent[idx]:
                                for autoIdx in range(len(intentContent[idx]['auto_fill'])):
                                    if intentContent[idx]['auto_fill'][autoIdx]['uuid'] == langId:
                                        del intentContent[idx]['auto_fill'][autoIdx]
                                        return



def UpdatePolicyFiles():
    global ResourceDict
    for filename, content in ResourceDict.items():
        with open(os.path.join(ResourceFolder, filename), 'w', encoding='utf-8') as fp:
            json.dump(content, fp, ensure_ascii=False, indent=4)


def LoadPolicyFiles():
    global ResourceFolder, ResourceDict
    ResourceDict.clear()
    for root, dirs, files in os.walk(ResourceFolder):
        for filename in files:
            if '.json' not in filename:
                continue
            with open(os.path.join(ResourceFolder, filename), 'r', encoding='utf-8') as fp:
                content = json.load(fp)
                ResourceDict[filename] = content

def regularClearConversation():
    global ConnectionDict
    now = time.time()
    try:
        for connId, value in ConnectionDict.items():
            if (now - value['created_at'] > 2 * 60 * 60):   # 3 mins
                del ConnectionDict[connId]
    except:
        # RuntimeError: dictionary changed size during iteration
        return




SERVER_INFO = {
    'users': [],
    'last_activity': 0,
    'running': False,
    'logs': []
}       
def regularCheckServerStatus():
    # If a sensor fail to update for a period of time, set it diconnected.
    # No need to keep update disconnected sensor
    # connection
    global SERVER_INFO
    if (time.time() - SERVER_INFO['last_activity'] < 2):  # 2 seconds
        SERVER_INFO['running'] = True
    else:
        SERVER_INFO['running'] = False
    socketio.emit('server_status', SERVER_INFO, room='dialogue_dashboard')
    
def onServerStatusCheckResponse(ch, method, properties, body):
    global SERVER_INFO
    rec = json.loads(body.decode("utf-8"))
    if rec['from'] == 'dialogue_engine_service' and rec['topic'] == 'status_update':
        SERVER_INFO['last_activity'] = time.time()

def onServerUserListUpdate(ch, method, properties, body):
    global SERVER_INFO
    rec = json.loads(body.decode("utf-8"))
    if rec['from'] == 'dialogue_engine_service' and rec['topic'] == 'user_list':
        SERVER_INFO['users'] = rec['data']['user']
        SERVER_INFO['last_activity'] = time.time()
        SERVER_INFO['logs'].append('[*] A new user joins the conversation.\n')
        socketio.emit('server_info', SERVER_INFO, room='dialogue_dashboard')
        
def onServerUserDeleted(ch, method, properties, body):
    global SERVER_INFO
    rec = json.loads(body.decode("utf-8"))
    if rec['from'] == 'dialogue_engine_service' and rec['topic'] == 'user_deleted':
        SERVER_INFO['users'] = rec['data']['current_users']
        SERVER_INFO['last_activity'] = time.time()
        SERVER_INFO['logs'].append('[*] Conversations for <{}> have been reset.\n'.format(rec['data']['deleted_users']))
        socketio.emit('server_info', SERVER_INFO, room='dialogue_dashboard')

def onServerResponseReceived(ch, method, properties, body):
    global SERVER_INFO
    rec = json.loads(body.decode("utf-8"))
    if rec['from'] == 'dialogue_engine_service' and rec['topic'] == 'response':
        SERVER_INFO['last_activity'] = time.time()
        socketio.emit('server_response', rec['data'], room='dialogue_dashboard')

if __name__ == '__main__':
    system = systemHandler.SystemHandler()
    
    # regularly clean depracated conversations:   60 sec * 60 min
    recycler = mics.RepeatedExecutor(60*60, regularClearConversation)
    recycler.start()
    # regularly check the backend dialogue service for MP
    serverExaminer = mics.RepeatedExecutor(1, regularCheckServerStatus)
    serverExaminer.start()
    
    
    # run dialogue engine server for MP application
    PidFile = os.path.join(VxFolder, 'dialogue_engine_subprocess_pid.dat')
    if os.path.exists(PidFile):
        subprocess.Popen([system.settings['python_command'], 'stop_dialogue_engine.py'], cwd=VxFolder)
        time.sleep(2)
    serverPid = subprocess.Popen([system.settings['python_command'], 'start_dialogue_engine.py'], cwd=VxFolder).pid
    with open(PidFile, 'w') as file:
        print(serverPid, file=file)
    
    # RabbitMQ
    serverSender = commHandler.commHandler(system.settings['server_ip'])
    
    serverStatusCheckListener = commHandler.commHandler(system.settings['server_ip'])
    serverStatusCheckListener.listen('amq.topic', 'MpDialogue.server.status', onServerStatusCheckResponse)
    serverUserListListener = commHandler.commHandler(system.settings['server_ip'])
    serverUserListListener.listen('amq.topic', 'MpDialogue.server.user', onServerUserListUpdate)
    serverUserDetetedListener = commHandler.commHandler(system.settings['server_ip'])
    serverUserDetetedListener.listen('amq.topic', 'MpDialogue.server.DeleteUser', onServerUserDeleted)
    serverResponseListener = commHandler.commHandler(system.settings['server_ip'])
    serverResponseListener.listen('amq.topic', 'MpDialogue.server.Response', onServerResponseReceived)
    
        
    # Flask
    socketio.run(app, host='0.0.0.0', port=8184, debug=True, use_reloader=False)
