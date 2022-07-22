# -*- coding: utf-8 -*-
"""
Created on Fri May 17 11:21:40 2019

@author: Xiangyang Mou
@email: moutaigua8183@gmail.com
"""

import os, sys, json
import warnings, time
import socket
import traceback
from dependencies import apiWrapper

V1Folder = os.path.dirname(os.path.abspath(__file__))
PublicFileFolder = os.path.join(V1Folder, 'server/static/file')
ResourceFolder = os.path.join(V1Folder, 'resources')
sys.path.append(V1Folder)
from dependencies import commHandler, systemHandler, mics, learningAssistantHandler, gameHandler
from conversationHandler import ConversationHandler
from dependencies import actionHandler
import thulac

thu = thulac.thulac(seg_only=True)

AllConversations = dict()
MicLanguageSetting = ['en-US', 'en-US', 'zh-CN', 'zh-CN', 'en-US', 'en-US']

DIALOGUE_ENGINE_NAME = 'on_campus'
LAST_IP = ''
PCTA_MODE = False
PRACTICE = False


def ifContainChinese(self, text):
    for ch in text:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
    return False


def getLocalExternalIp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def containChinese(text):
    for ch in text:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
    return False


def __cutChineseString(text):
    array = []
    for ch in text:
        if u'\u4e00' <= ch <= u'\u9fff':
            # if contain chinese, cut
            segments = thu.cut(text, text=True).split()
            for each_string in segments:
                array.append(each_string[:each_string.find('_')])
            break
    return array


def __sendPTCAVideo(IP_Addr, agentResponse):
    global mpSender, pcHandler, LAST_IP, THIS_IP
    video = pcHandler.getDataByWord(agentResponse['paras']['value'])
    if video is None:
        error = {
            'CN': '无法从服务器获取语音',
            'EN': 'Sorry, cannot download data from the server'
        }
    else:
        error = None
        # write video
        nativePCAFilename = 'nativePCA_on_campus.webm'
        # ResponseFile = os.path.join(system.settings['webm_path'], nativePCAFilename)
        ResponseFile = os.path.join(PublicFileFolder, nativePCAFilename)
        file = open(ResponseFile, 'wb+')
        file.write(video)
        file.close()
        # to STT
        mpSender.send('amq.topic', 'CIR.pitchtone.executor', json.dumps(
            {
                'type': 'start_listen',
                'word': agentResponse['paras']['value'],
                'pcaRequestedBy': DIALOGUE_ENGINE_NAME
            }))
        ### set mic channel to CN input
        mpSender.send('amq.topic', 'switchLanguage.transcript.command', json.dumps({
            'micLang': ['zh-CN', 'zh-CN', 'zh-CN', 'zh-CN', 'zh-CN', 'zh-CN'],
            'set_by_campus_dialogue': 'ignore'
        }))
        # to Unity
        mpSender.send('amq.topic', 'mp-ui-controller', json.dumps({
            'name': 'unityAction',
            'parameters': {
                "pitch_show": {
                    "id": 1,
                    "x": 4900,
                    "y": 500,
                    "word": agentResponse['paras']['value'],
                    "englishWord": agentResponse['paras']['vocab']
                }
            },
            'IP': IP_Addr
        }))
        LAST_IP = IP_Addr
        pca_type = 'pca_native'
        # mpSender.send('amq.topic', 'mp-ui-controller',
        #               json.dumps({'id': 1, 'URL': 'http://128.113.21.144:7827/PCA/' + nativePCAFilename, 'type': pca_type}))
        mpSender.send('amq.topic', 'mp-ui-controller',
                      json.dumps({'id': 1, 'URL': 'http://{}:8184/file/{}'.format(THIS_IP, nativePCAFilename),
                                  'type': pca_type}))
        # print('http://{}:8184/file/{}'.format(THIS_IP, nativePCAFilename))
    return error



def __commonActionsBeforeResponse(userInput, agentResponse, debugInfo, gameProgressProfile):
    global MicLanguageSetting, mpSender, PCTA_MODE, PRACTICE, apiHandler, CurrentScene
    if agentResponse['user_intent'] == 'switch-input-language' or \
            (agentResponse['user_intent'] == 'switch-output-language' and agentResponse[
                'user_input'].lower().strip() in ['中文', '英文', 'chinese', 'english']):
        if agentResponse['paras']['value'] == 'EN':
            MicLanguageSetting[int(userInput['channelIndex'])] = 'en-US'
        elif agentResponse['paras']['value'] == 'CN':
            MicLanguageSetting[int(userInput['channelIndex'])] = 'zh-CN'
        else: return
        mpSender.send('amq.topic', 'switchLanguage.transcript.command', json.dumps({
            'micLang': MicLanguageSetting
        }))
    elif agentResponse['user_intent'] == 'scene-switch':
        if 'scene' in debugInfo['entities']:
            sceneName = debugInfo['entities']['scene']['value'].capitalize() + '_Environment'
            apiHandler.switchScene(display_ip=agentResponse['IP'], by_name=sceneName)
        else:
            if CurrentScene.lower() == 'upperstreet':
                apiHandler.switchScene(display_ip=agentResponse['IP'], by_waypoint='LowerStreet')
            elif CurrentScene.lower() == 'lowerstreet':
                apiHandler.switchScene(display_ip=agentResponse['IP'], by_waypoint='UpperStreet')
            elif CurrentScene.lower() == 'campusmain':
                apiHandler.switchScene(display_ip=agentResponse['IP'], by_waypoint='CampusFacilities')
            elif CurrentScene.lower() == 'campusfacilities':
                apiHandler.switchScene(display_ip=agentResponse['IP'], by_waypoint='CampusMain')
    elif agentResponse['user_intent'] == 'ptca':
        if len(debugInfo['paras']['error']) == 0:
            PCTA_MODE = True
            err = __sendPTCAVideo(userInput['IP'], agentResponse)
            if err is None:
                return
            if containChinese(agentResponse['text']):
                agentResponse['text'] = err['CN']
            else:
                agentResponse['text'] = err['EN']
        else:
            print('[*] {}:  {}'.format(debugInfo['paras']['error'], debugInfo['paras']['value']))
    elif agentResponse['user_intent'] == 'practice' or agentResponse['user_intent'] == 'practice-mode':
        PRACTICE = True
        apiHandler.showPitchGraph(userInput['IP'], agentResponse['text'])
    elif agentResponse['user_intent'] == 'exit_practice':
        PRACTICE = False

def commandCallback(ch, method, properties, body):
    '''
    The coming message format
    {'msg': ' 你好', 'wakeword': 'lisha', 'username': 'xxx', 'channelIndex': 0, 'userId' : }
    '''
    global system, AllConversations, mpSender, actionHandler
    global apiHandler, CurrentScene
    try:
        rec = json.loads(body.decode("utf-8"))
        # starting
        print('\n>>>>> Input Received:')
        print(rec)
        if rec['wakeword'] == '':
            print('Not talking to any of the agents...')
            return
        username = 'Debug user' if ('username' not in rec or rec['username'] == '') else rec['username']
        #username = 'Debug user'
        rec['username'] = username
        # create a new user if not exist
        if username not in AllConversations:
            AllConversations[username] = dict()
            AllConversations[username]['created_at'] = time.time()
            AllConversations[username]['handler'] = ConversationHandler(cnHelper=thu)
            AllConversations[username]['handler'].GlobalSetting['difficulty'] = system.getDifficultyLevel()
            apiHandler.sendAllConversationsToFlask(AllConversations)
        # parse the addressee
        rec['msg'] = rec['msg'].replace(rec['wakeword'], '')
        agentId = system.getAgentIdByWakeupWord(rec['wakeword'])
        agent = system.getDialogueIdById(agentId)

        if agent == 'lisa' and 'campus' in CurrentScene.lower():
            agent = 'lisa_on_campus'
        elif agent == 'lisa' and 'street' in CurrentScene.lower():
            agent = 'lisa_on_street'
        else:
            agent = rec['wakeword']     # in case rec['wakeword'] == lisa_on_street or == lisa_on_campus

        rec['wakeword'] = agent


        if agent not in AllConversations[rec['username']]['handler'].ConversationDict:
            AllConversations[rec['username']]['handler'].startConversation(rec['username'],str(rec['userId']), agent=agent.lower())

         

        
        #AllConversations[username]['handler'].load(rec)
        
        
        # generate response 
        response, debug_info = AllConversations[username]['handler'].getResponse(agent, rec, difficulty=AllConversations[username]['handler'].GlobalSetting['difficulty'])
        # Send to Unity and Flask

        if type(response) is dict:
            response['IP'] = rec['IP']
            debug_info['IP'] = rec['IP']
            
            if response['user_intent'] == 'answer-hobby':
                with open(os.path.join(ResourceFolder, 'club_list.dat'), 'r', encoding='utf-8') as fp:
                    clubArray = fp.readlines()
                    clubListStr = ''
                    for each in clubArray:
                        clubListStr += each
                    extraActions = {'showClubList': clubListStr}
                # msgToUnity['parameters']['actions']['showClubList'] = clubListStr
            elif response['user_intent'] == 'answer-next-book-negative':
                extraActions = {'money': response['paras']['balance']}
                # msgToUnity['parameters']['actions']['money'] = agentResponse['paras']['balance']
            else:
                extraActions = None

            __commonActionsBeforeResponse(rec, response, debug_info,AllConversations[username]['handler'].getGameProgressProfile())
            AllConversations[username]['handler'].takeActions(rec, response, debug_info, AllConversations[username]['handler'].getGameProgressProfile())
            
            
            #AllConversations[username]['handler'].save(rec)
            if len(response['text'])>0:
                apiHandler.sendAgentResponseToUnity(rec, agentId, response, extra_actions=extraActions)
                apiHandler.sendDebugInfoToFlask(debug_info)
                apiHandler.sendToSpeakerWorker(response['text'], system.getGenderById(agentId))
                 # ending
                print('\n<<<<< Agent Response:')
                print(response)
            else: 
                print("\n<<<<< Empty Agent Response")
    except Exception as e:
        # exc_type, exc_obj, exc_tb = sys.exc_info()
        # fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print('\n---------- error -----------')
        print('Dialogue_Server Error:{}\n'.format(e.args))
        traceback.print_exc()
        print('------------------------------\n')


# def commandCallbackV2(ch, method, properties, body):
#     '''
#     The coming message format
#     {
#         'msg': ' 你好', 'wakeword': 'lisha', 'username': 'xxx', 'channelIndex': 0,
#         'raw': {
#             "workerID": "multichannel-transcript-worker", 
#             "channelName": "zh-CN", 
#             "channelIndex": 1, 
#             "language": "zh-CN", 
#             "result": {
#                 "alternatives": [
#                     {
#                         "timestamps": [["丽", 2626.88, 2627.13], ["莎", 2627.13, 2627.53], ["我", 2627.67, 2627.96], ["学", 2627.96, 2628.33], ["金融", 2628.37, 2629.05]], 
#                         "confidence": 1, 
#                         "transcript": "丽莎我学金融", 
#                         "word_confidence": [["丽", 1], ["莎", 1], ["我", 1], ["学", 1], ["金融", 1]]
#                     }, 
#                     {"transcript": "利 莎 我 学 金融 "}, 
#                     {"transcript": "利 沙 我 学 金融 "}
#                 ], 
#                 "final": True
#             }, 
#         "total_time": 2629.05, 
#         "timestamp": "2019-07-24T03:15:27.244Z", 
#         "transcriptTimes": [1563938122931, 1563938125931], 
#         "username": "Hui"
#         }
#     }
#     '''
#     pass


def serverStatusUpdate():
    global mpSender
    mpSender.send('amq.topic', 'MpDialogue.server.status', json.dumps({
        'from': 'dialogue_engine_service',
        'topic': 'status_update',
        'data': {
            'status': True
        }
    }))


def sttCallback(ch, method, properties, body):
    # {‘pca-done’: true}
    global LAST_IP, MicLanguageSetting, mpSender, PCTA_MODE, PRACTICE
    rec = json.loads(body.decode("utf-8"))
    if rec['pca-done'] and \
            'pcaRequestedBy' in rec and rec['pcaRequestedBy'] == DIALOGUE_ENGINE_NAME and \
            (PCTA_MODE or PRACTICE):

        # set mic channel to (CN/EN) the same input as before
        mpSender.send('amq.topic', 'switchLanguage.transcript.command', json.dumps({
            'micLang': MicLanguageSetting
        }))
        mpSender.send('amq.topic', 'mp-ui-controller', json.dumps({
            "name": "agentAction",
            "parameters": {
                "actions": {
                    "speak": ["Here's how close you got."]
                }
            },
            "IP": LAST_IP
        }))
        time.sleep(15)  # wait 15 sec
        mpSender.send('amq.topic', 'mp-ui-controller', json.dumps({
            "name": "unityAction",
            "parameters": {
                "pitch_hide": {
                    "id": 1
                }
            },
            "IP": LAST_IP
        }))
        if PRACTICE:
            message = json.dumps({'msg': 'okay', 'wakeword': 'laoshi', 'username': 'xxx'})
            mpSender.send('amq.topic', 'mou', message)


def serverResetCallback(ch, method, properties, body):
    global AllConversations, mpSender
    rec = json.loads(body.decode("utf-8"))
    if rec['username'] == 'All Users':
        mpSender.send('amq.topic', 'MpDialogue.server.DeleteUser', json.dumps({
            'from': 'dialogue_engine_service',
            'topic': 'user_deleted',
            'data': {
                'deleted_users': list(AllConversations.keys()),
                'current_users': []
            }
        }))
        AllConversations.clear()
    elif rec['username'] in AllConversations:
        del AllConversations[rec['username']]
        mpSender.send('amq.topic', 'MpDialogue.server.DeleteUser', json.dumps({
            'from': 'dialogue_engine_service',
            'topic': 'user_deleted',
            'data': {
                'deleted_users': [rec['username']],
                'current_users': list(AllConversations.keys())
            }
        }))


def unityCallback(ch, method, properties, body):
    '''
    Respond to Unity actions, e.g.  scene switch
    '''
    global CurrentScene
    rec = json.loads(body.decode("utf-8"))
    
    if rec['to'] == 'dialogue' and rec['topic']=='scene_switch' and 'waypoint' in rec['data']:
        CurrentScene = rec['data']['waypoint']
        print('CurrentScene:', CurrentScene)
   


def languageSwitchCallback(ch, method, properties, body):
    global MicLanguageSetting
    rec = json.loads(body.decode("utf-8"))
    print('****** languageSwitchCallback() ******')
    print(rec)
    print('**************************************')
    if 'set_by_campus_dialogue' in rec and rec['set_by_campus_dialogue'] == 'ignore':
        return
    MicLanguageSetting = rec['micLang']


def regularClearConversation():
    global AllConversations
    now = time.time()
    try:
        for key, value in AllConversations.items():
            if (now - value['created_at'] > 60 * 60):  # 60 mins
                del AllConversations[key]
                print('[*] All conversations of User <{}> have been deleted because they keep idle for too long'.format(key))
                apiHandler.sendAllConversationsToFlask(AllConversations)
    except Exception as e:
        # RuntimeError: dictionary changed size during iteration
        print('\n---------- error -----------')
        print('Dialogue_Server Error:{}\n'.format(e.args))
        traceback.print_exc()
        print('------------------------------\n')



if __name__ == '__main__':
    system = systemHandler.SystemHandler()
    if not system.IsReady:
        sys.exit()
    THIS_IP = getLocalExternalIp()
    print('[*] This IP:', THIS_IP)
    CurrentScene = system.settings['starting_scene']

    masterHandler = ConversationHandler(cnHelper=thu)
    masterHandler.manageUUID()
    apiHandler = apiWrapper.APIWrapper(cnHelper=thu)

    ### something wrong with the learning assistant
    ### It would affect "teacher" conversation to be initiated
    ### Uncomment one line below only if the learning assistant goes back to work
    ### Do the same things for LaoshiConversation --> __init__()
    pcHandler = None  # learningAssistantHandler.PitchhContourHandler()

    # Sender for results
    mpSender = commHandler.commHandler(system.settings['server_ip'])
    # Listerner for receving commands
    languageSwitcherListener = commHandler.commHandler(system.settings['server_ip'])
    languageSwitcherListener.listen('amq.topic', 'switchLanguage.transcript.command', languageSwitchCallback)
    unityTranscriptListener = commHandler.commHandler(system.settings['server_ip'])
    unityTranscriptListener.listen('amq.topic', 'Unity.transcript', commandCallback)
    serverResetListener = commHandler.commHandler(system.settings['server_ip'])
    serverResetListener.listen('amq.topic', 'MpDialogue.server.reset', serverResetCallback)
    sttListener = commHandler.commHandler(system.settings['server_ip'])
    sttListener.listen('amq.topic', 'to-dialogue-executors', sttCallback)
    unityListener = commHandler.commHandler(system.settings['server_ip'])
    unityListener.listen('amq.topic', 'Unity.bulletin', unityCallback)


    # regularly clean conversation
    recycler = mics.RepeatedExecutor(60 * 5, regularClearConversation)
    recycler.start()
    serverStatucSender = mics.RepeatedExecutor(1, serverStatusUpdate)
    serverStatucSender.start()


    