# -*- coding: utf-8 -*-
"""
Created on Thu May 16 00:38:34 2019

@author: Xiangyang Mou;  Sylvia Hua
@email: moutaigua8183@gmail.com;   huaz2@rpi.edu
"""
import math
import os, sys, json
import numpy as np
import warnings
from dependencies import watsonAssistantHandler, systemHandler, actionHandler, commHandler
from dependencies.gameHandler import GameLogicConstraint
import random
from dependencies import transcriptHandlerV2
from dependencies import apiWrapper
import thulac
import pickle

MicLanguageSetting = ['en-US', 'en-US', 'zh-CN', 'zh-CN', 'en-US', 'en-US']

# These functions begin with single underscore
# _resolveParameters()
# _errorMsgHandling()
# _generateHint()
# _simulateUserInput()
# _randomResponse()
# _randomResponseWithSlot()
# _generateResponseText()


class Conversation:
    def __init__(self, username, userId, agent, cnHelper=None, enHelper=None, gameProgress=None, actionHandler=None):
        self.apiHandler = apiWrapper.APIWrapper(cnHelper = cnHelper)
        self.system = systemHandler.SystemHandler()
        self.ActionHandler = actionHandler
        if not self.system.IsReady:
            sys.exit()
        self.AgentName          = agent
        self.AgentUtterances    = list()
        self.AgentCloudParams   = self.system.getAgentCloudParams(agent)
        if len(self.AgentCloudParams)>0:
            self.WatsonHandler  = watsonAssistantHandler.WatsonHandler(
                    self.AgentCloudParams['workspace_id'],
                    self.AgentCloudParams['username'],
                    self.AgentCloudParams['password'])
        else:
            warnings.warn('Fail to initialize Conversation instance: No agent is named {} in config.json'.format(agent))
            return
        self.UserName       = username
        self.UserId = userId
        self.UserUtterances = list()
        self.UserIntent     = list()    # update in derivative classes
        # system
        self.OutputLanguage = 'CN' # CN/EN
        self.RootFolder     = os.path.dirname(os.path.abspath(__file__))
        self.Actions        = self.__loadPolicy()
        self.Auxiliaries    = self.__loadAuxiliaryJson()
        self.SlotDict       = dict()
        self.PlaceholderDict    = self.__loadPlaceholderData()
        self.gameProgressProfile = gameProgress
        self.GameLogicHandler   = gameProgress['lisa_on_street'] if gameProgress else GameLogicConstraint(agent)
        self.CNHelper       = cnHelper
        self.ENHelper       = enHelper
        # init
        self.DifficultyLevel =self.system.getDifficultyLevel()
        self.Difficulty     = 1 # default value
        self.GlobalSetting  = None
        self.StatusList     = {}
        self.detailed_intent = None
        self.LearningMode   = {'CN': '请再试一次', 'EN': 'Please try again'}
        self.corrector      = transcriptHandlerV2.TranscriptCorrection(agent,cnHelper)
        self.ordered_item = None
        self.ordered_price = None
        self.MoneySpent = 0

        self.UserPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),"savingData/"+username)
        if os.path.exists(self.UserPath): self.load()



    def __loadPlaceholderData(self):
        placeholderDict = {}
        self.ResponseFile = os.path.join(self.RootFolder, 'resources/placeholder_data.json')
        with open(self.ResponseFile, "r", encoding='utf-8') as file:
            placeholderDict = json.load(file)
        return placeholderDict
    
    def __loadPolicy(self):
        self.ResponseFile = os.path.join(self.RootFolder, 'resources/policy.json')
        if not os.path.exists(self.ResponseFile):
            warnings.warn('Fail to load response pool: <policy.json> file is missing in /resources ...')
            return None
        with open(self.ResponseFile, 'r', encoding='utf-8') as file:
            action = json.load(file)[self.AgentName]['action']
            return action
        
    def __loadAuxiliaryJson(self):
        auxDict = dict()
        self.ResourceFolder = os.path.join(self.RootFolder, 'resources/')
        for root, dirs, files in os.walk(self.ResourceFolder):
            for file in files:
                if file.endswith('.json') and 'slot_auxiliary' in file:
                    with open(os.path.join(self.ResourceFolder, file), 'r', encoding='utf-8') as fp:
                        auxDict[file] = json.load(fp)
        return auxDict           

    def _ifContainChinese(self, text):
        for ch in text:
            if u'\u4e00' <= ch <= u'\u9fff':
                return True
        return False

    def __utterancePreprocess(self, text):
        if self._ifContainChinese(text):
            temp = ''
            for eachChar in text:
                temp += eachChar + ' ' if u'\u4e00' <= eachChar <= u'\u9fff' else ''
            return temp.strip()
        else:
            return text.lower()
        
    def _extractNouns(self, text):
        nouns = []
        if self._ifContainChinese(text) and self.CNHelper is not None:
            segments = self.CNHelper.cut(text,text=True).split()
            for each_string in segments:
                if each_string[-1] == 'n':
                    nouns.append(each_string.replace("_n",""))
                elif each_string[-2] == "n":
                    nouns.append(each_string[:-3])
        elif not self._ifContainChinese(text) and self.ENHelper is not None:
            segments = self.ENHelper(text)
            phrase = ''
            for token in segments:
                if token.pos_ == "NOUN" and token.text != "pronounce" and token.text != "pronunciation":
                    phrase += token.text
                    phrase += ' '
            nouns.append(phrase)
        return nouns    

    def _checkExpectedConditions(self, intent, entity):
        if len(self.AgentUtterances) >= 1 and intent != "positive" and intent != "negative":
            if "expected_condition" in self.AgentUtterances[-1].keys() and 'pronoun' not in entity.keys():
                all_values = [item for sublist in self.AgentUtterances[-1]["expected_condition"].values() for item in sublist]
                if len(all_values) > 0:
                    flg = True
                    expected_condition = self.AgentUtterances[-1]["expected_condition"]
                    for key, value in expected_condition.items():
                        if len(value) > 0:
                            if key == 'intent':
                                flg *= any(intent in x for x in expected_condition['intent'])
                            elif key == 'entities':
                                flg *= any(x in expected_condition['entities'] for x in entity)
                    return flg
        return True

    def _resolveParameters(self, rawText, intent, entity=None):
        paras = {
                'value': '', 
                'error': '',
                'money_spent': str(self.MoneySpent),
                'ordered_item': self.ordered_item,
                'ordered_price': self.ordered_price
                }
        if len(intent) == 0:
            paras["error"] = "no_intent"
        elif not self._checkExpectedConditions(intent, entity):
            paras["error"] = "not_expected"
        return paras
    
    
    def _errorMsgHandling(self, error, difficulty=None):
        '''
        Handle all the error messages at all steps
        '''
        if self.Actions and 'error_handling' in self.Actions:
            allres = self.Actions['error_handling']
            candidates = []
            if error not in allres:
                print('[*] A new error can not be handled')
                return ''
            for each in allres[error]:
                if difficulty and math.ceil(each['difficulty']*self.DifficultyLevel/5) > difficulty:
                    continue
                candidates.append(each)
            # random choose one in candidates
            selected = random.choice(candidates)
            return selected[self.OutputLanguage]
        else:
            if (self.GlobalSetting['learning_mode'] == True):
                return self.LearningMode[self.OutputLanguage]
            return ''
    
    def _generateHint(self):
        if len(self.AgentUtterances) == 0 or len(self.AgentUtterances[-1]['auto_fill']) == 0:
            return self._errorMsgHandling('no_hint')
        text = ''
        if self.OutputLanguage == 'CN':
            for each in self.AgentUtterances[-1]['auto_fill']:
                if len(text) == 0:
                    text += "你可以说，" + each["CN"]
                else:
                    text += " 或者 " + each["CN"]
        else:
            for each in self.AgentUtterances[-1]['auto_fill']:
                if len(text) == 0:
                    text += "you can say, " + each["EN"]
                else:
                    text += " or " + each["EN"]
        return text

    def _simulateUserInput(self):
        if len(self.AgentUtterances) == 0 or len(self.AgentUtterances[-1]['auto_fill']) == 0:
            return self._errorMsgHandling('cannot_skip')
        response, debuginfo = self.getResponse(self.AgentUtterances[-1]['auto_fill'][0][self.OutputLanguage], self.Difficulty, self.OutputLanguage)
        return response['text']


    def _randomResponse(self, intent, difficulty=None):
        if self.Actions and intent in self.Actions:
            allres = self.Actions[intent]
            candidates = []
            for each in allres:
                if difficulty and math.ceil(int(each['difficulty'])*self.DifficultyLevel/5) > difficulty:
                    continue
                candidates.append(each)
            # random choose one in candidates
            selected = random.choice(candidates)
            self.AgentUtterances.append(selected.copy())
            return selected[self.OutputLanguage]
        else:
            print('[*] Intent is not found')
            if self.GlobalSetting['learning_mode'] == True:
                return self.LearningMode[self.OutputLanguage]
            return ''


    def _getAllRepeatText(self):
        if len(self.AgentUtterances) == 1:
            return self.AgentUtterances[0][self.OutputLanguage]
        else:
            text_list = [self.AgentUtterances[-1][self.OutputLanguage]]
            temp = list(reversed(self.AgentUtterances))
            for i in range(1,len(temp)):
                if len(temp[i]["jump_to_intent"]) == 0:
                    break
                else:
                    text_list.append(temp[i][self.OutputLanguage])
            text_list.reverse()
            return ' '.join(text_list)




    def _randomResponseWithSlot(self, userIntent, difficulty=None, preFill=list()):
        if self.Actions and userIntent in self.Actions:
            if type(self.Actions[userIntent]) != str:
                print('[*] For user intent <{}>: Only support a string whose value is the json file')
                return ''
            auxFilename = self.Actions[userIntent]
            allres = self.Auxiliaries[auxFilename]['option']
            if auxFilename not in self.SlotDict:
                self.SlotDict[auxFilename] = dict()
                for each in self.Auxiliaries[auxFilename]['slot']:
                    self.SlotDict[auxFilename][each] = False if each not in preFill else True
            candidates = []
            finals = []
            print(self.SlotDict, auxFilename not in self.SlotDict)
            for each in allres:
                if difficulty < math.ceil(each['difficulty']*self.DifficultyLevel/5):
                    continue
                if each['slot'] in self.SlotDict[auxFilename].keys() and self.SlotDict[auxFilename][each['slot']]:
                    continue
                elif each['slot'] not in self.SlotDict[auxFilename].keys() and  not all([flag for flag in self.SlotDict[auxFilename].values()]):
                    continue
                elif each['slot'] in self.SlotDict[auxFilename].keys():
                    candidates.append(each)
                else:
                    finals.append(each)
            # random choose one in candidates or final
            if len(candidates) > 0:
                selected = random.choice(candidates)
                self.SlotDict[auxFilename][selected['slot']] = True
            else:
                selected = random.choice(finals)
                self.StatusList['self_introduction'] = True
                # clear the slot flag
                if all([flag for flag in self.SlotDict[auxFilename].values()]):
                    del self.SlotDict[auxFilename]
            # return 
            self.AgentUtterances.append(selected)
            return selected[self.OutputLanguage]
        else:
            print('[*] No responses.json files')
            return ''


    def _generateResponseText(self, intent, entities, difficulty):
        '''
        Need to be implemented in derivative classes 
        '''
        text = ''
        return text

    def _replacePlaceholder(self,text):
        if "@" not in text:
            return text
        current_placeholders = dict()
        CN_text = self.AgentUtterances[-1]["CN"]
        EN_text = self.AgentUtterances[-1]["EN"]
        if self._ifContainChinese(text):
            flag = 'CN'
        else:
            flag = 'EN'
        if "@" in CN_text:
            CN_text = CN_text.split("_")
            for i in range(len(CN_text)):
                if CN_text[i] == "@wear":
                    CN_text[i] = random.choice(list(self.PlaceholderDict["@wear"].keys()))
                    current_placeholders["@wear"] = CN_text[i]
                elif CN_text[i] == "@wearable":
                    if "@wear" in current_placeholders:
                        current_action = current_placeholders["@wear"]
                        placeholder_value = random.choice(self.PlaceholderDict["@wear"][current_action])
                        CN_text[i] = placeholder_value[0]
                        current_placeholders["@wearable"] = placeholder_value
                    else:
                        random_action = random.choice(list(self.PlaceholderDict["@wear"].keys()))
                        placeholder_value = random.choice(self.PlaceholderDict["@wear"][random_action])
                        CN_text[i] = placeholder_value[0]
                        current_placeholders["@wearable"] = placeholder_value
                elif "@bookprice" in CN_text[i]:
                    prices = self.PlaceholderDict['@bookprice']
                    if 'new' in CN_text[i]:
                        CN_text[i] = str(prices['new'])
                    elif 'used' in CN_text[i]:
                        CN_text[i] = str(prices['used'])
                    elif 'ebook' in CN_text[i]:
                        CN_text[i] = str(prices['ebook'])
                    elif 'paper' in CN_text[i]:
                        CN_text[i] = str(prices['paper'])
                else:
                    if (CN_text[i][0] == "@"):
                        placeholder = CN_text[i]
                        placeholder_value = random.choice(self.PlaceholderDict[placeholder])
                        CN_text[i] = placeholder_value[0]
                        current_placeholders[placeholder] = placeholder_value
            new_CN = self.AgentUtterances[-1]["CN"] = ''.join(CN_text)
            self.AgentUtterances[-1]["CN"] = new_CN
        if "@" in EN_text:
            EN_text = EN_text.split("_")
            for i in range(len(EN_text)):
                if (EN_text[i][0] == "@"):
                    if 'bookprice' in EN_text[i]:
                        prices = self.PlaceholderDict['@bookprice']
                        if 'new' in EN_text[i]:
                            EN_text[i] = str(prices['new'])
                        elif 'used' in EN_text[i]:
                            EN_text[i] = str(prices['used'])
                        elif 'ebook' in EN_text[i]:
                            EN_text[i] = str(prices['ebook'])
                        elif 'paper' in EN_text[i]:
                            EN_text[i] = str(prices['paper'])
                    else:
                        placeholder = EN_text[i]
                        placeholder_value = current_placeholders[placeholder]
                        EN_text[i] = placeholder_value[1]
            new_EN = self.AgentUtterances[-1]["EN"] = ''.join(EN_text)
            self.AgentUtterances[-1]["EN"] = new_EN

        return self.AgentUtterances[-1][flag]

    def reset(self):
        self.AgentUtterances.clear()
        self.UserUtterances.clear()
        self.UserIntent.clear()
        self.StatusList.clear()
        for each in self.SlotDict.keys():
            self.SlotDict[each].clear()

        self.deleteSavingData()
            

    # def guessUserInput(self, text):
    #     print('>>> Raw:', text)
    #     text = self.PYHandler.directReplacement(text)
    #     print('>>> After simple replacement:', text)
    #     text = self.PYHandler.checkingword(text, self.getExpectedUserIntent(), 0.5)
    #     print('>>> After Pinyin replacement:', text)
    #     return text

    def guessUserInputV2(self, txt):
        text = self.corrector.substitutePinyin(txt, self.getExpectedUserIntent())
        return text


    def getResponse(self, userInput, difficulty=None, output_language=None):
        '''
        Generate a response to the input text
        {
            'text':     '1234..',
            'language': 'CN'/'EN',
            'intent':   '',
            'paras':    '...'
        }
        '''
        inputText = userInput['msg']
        if not self.WatsonHandler:
            warnings.warn('[*] Not a valid WatsonHandler instance')
            return ''
        self.UserUtterances.append(inputText)
        DEBUG_INFO = {}
        DEBUG_INFO['agent'] = self.AgentName
        # preparation
        self.OutputLanguage = self.GlobalSetting['output_language']
        if not difficulty:
            difficulty = self.Difficulty
        else:
            self.Difficulty = difficulty
        if self.system.getCorrectionConfig() and self._ifContainChinese(inputText):
            inputText = self.guessUserInputV2(inputText)
        processedText = self.__utterancePreprocess(inputText)
        DEBUG_INFO['original_text'] = inputText
        DEBUG_INFO['processed_text'] = processedText
        DEBUG_INFO['difficulty'] = difficulty
        # get intent and entities of the input text ==> (intent, {entity dict})
        res = self.WatsonHandler.recognizeIntentAndEntity(processedText)
        intent = res[0]
        intent = self.GameLogicHandler.intentTransformer(self.AgentName,intent,self.StatusList)
        entities = res[1]
        DEBUG_INFO['intent'] = intent

        ''' intent can be None'''

        DEBUG_INFO['entities'] = entities
        # Extract detailed information based on different intents and entities
        paras = self._resolveParameters(inputText, intent, entities)
        DEBUG_INFO['global_difficulty'] = self.GlobalSetting['difficulty']
        DEBUG_INFO['global_input_language'] = self.GlobalSetting['input_language']
        DEBUG_INFO['global_output_language'] = self.GlobalSetting['output_language']
        DEBUG_INFO['output_language'] = self.OutputLanguage
        DEBUG_INFO['difficulty'] = difficulty
        if len(paras['error']) > 0:
            text = self._errorMsgHandling(paras['error'])
        else:
            # Generate output
            text = self._generateResponseText(intent, entities, difficulty)
        if len(self.AgentUtterances) > 0:
            while ("jump_to_intent" in self.AgentUtterances[-1] and len(self.AgentUtterances[-1]["jump_to_intent"]) > 0):
                next_intent = self.AgentUtterances[-1]["jump_to_intent"]
                DEBUG_INFO['slot_final'] = 'final' in self.AgentUtterances[-1]['slot']
                text += " "
                text += self._generateResponseText(next_intent,entities,difficulty)
                print(text)
        paras['money_spent'] = str(self.MoneySpent)
        paras['ordered_item'] = str(self.ordered_item)
        paras['ordered_price'] = str(self.ordered_price)
        DEBUG_INFO['paras'] = paras
        # check if there's still placeholder
        text = self._replacePlaceholder(text)
        DEBUG_INFO['agent_response'] = text

        if self.detailed_intent:
            DEBUG_INFO['detailed_intent'] = self.detailed_intent
        else:
            DEBUG_INFO['detailed_intent'] = ''

        if len(self.AgentUtterances) > 0:
            DEBUG_INFO['slot_final'] = 'final' in self.AgentUtterances[-1]['slot']
        # form a response
        response = dict()
        response['user_input']  = inputText
        response['user_intent'] = intent if self.detailed_intent is None else self.detailed_intent
        response['agent']       = self.AgentName
        response['language']    = self.OutputLanguage
        response['input_language'] = self.GlobalSetting['input_language']
        response['paras']       = paras
        response['difficulty']  = difficulty
        response['text']        = text

        return response, DEBUG_INFO

    def takeActions(self,userInput, agentResponse, debugInfo, gameProgressProfile):
        #inhereted in child classes
        pass


    def save(self):
        if not os.path.exists(self.UserPath):
            os.makedirs(self.UserPath)
        with open(self.UserPath+"/{}.pkl".format(self.AgentName),"wb+") as file:
            pickle.dump((
                self.UserUtterances,
                self.AgentUtterances,
                self.UserIntent,
                self.OutputLanguage,
                self.SlotDict,
                self.gameProgressProfile,
                self.Difficulty,
                self.StatusList,
                self.detailed_intent,
                self.ordered_item,
                self.ordered_price,
                self.MoneySpent
                ),file)
            print("****************Conversation of User: {} is Saved**************".format(self.UserName))




    def load(self):
        print("Loading...Username:",self.UserName)
        path = self.UserPath+"/{}.pkl".format(self.AgentName)
        if not os.path.exists(path):
            print("No saving data.")
            return
        with open(path,"rb") as file:
            self.UserUtterances,\
                self.AgentUtterances,\
                self.UserIntent,\
                self.OutputLanguage,\
                self.SlotDict,\
                self.gameProgressProfile,\
                self.Difficulty,\
                self.StatusList,\
                self.detailed_intent,\
                self.ordered_item,\
                self.ordered_price,\
                self.MoneySpent= pickle.load(file)
            print("****************Conversation of User: {} is Loaded**************".format(self.UserName))


    def deleteSavingData(self):
        path = self.UserPath+"/{}.pkl".format(self.AgentName)
        if os.path.exists(path):
            os.remove(path) 

        
    def getExpectedUserIntent(self):
        neg_pos_list = ['answer-visiting','answer-course','answer-process','answer-foreign-student','answer-greeting']
        if len(self.AgentUtterances) == 0:
            return ["hello"]
        if len(self.AgentUtterances[-1]['slot']):
            if self.AgentUtterances[-1]['slot'] in neg_pos_list:
                return ['negative','positive']
            if self.AgentUtterances[-1]['slot'] == 'answer-book-for-course':
                return ['answer-book-for-course','negative']
            return [self.AgentUtterances[-1]['slot']]
        else:
            s = set()
            if 'autofill' in self.AgentUtterances[-1]:
                for item in self.AgentUtterances[-1]['autofill']:
                    if len(item):
                        s.add(item)
            return list(s)

    def getAllUserIntent(self):
        return self.WatsonHandler.getIntentList()

#                       _oo0oo_
#                      o8888888o
#                      88" . "88
#                      (|3 _ 3|)
#                      0\  o  /0
#                    ___/`---'\___
#                  .' \\|     |// '.
#                 / \\|||  :  |||// \
#                / _||||| -:- |||||- \
#               |   | \\\  -  /// |   |
#               | \_|  ''\---/''  |_/ |
#               \  .-\__  '-'  ___/-. /
#             ___'. .'  /--.--\  `. .'___
#          ."" '<  `.___\_<|>_/___.' >' "".
#         | | :  `- \`.;`\ _ /`;.`/ - ` : | |
#         \  \ `_.   \_ __\ /__ _/   .-` /  /
#     =====`-.____`.___ \_____/___.-`___.-'=====
#                       `=---='
#
#
#     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#               佛祖保佑         永无BUG
