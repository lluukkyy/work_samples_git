import os, json, uuid, sys
import time
from dependencies.actionHandler import ActionHandler
from taichiMasterConversation import ShiFuConversation
from dependencies.gameHandler import GameLogicConstraint
# from dependencies import transcriptHandlerV2
# insert new agents here
from laoshiConversation import LaoshiConversation
from roommateConversation import RoommateConversation
from lisaOnCampusConversation import LisaOnCampusConversation
from TestConversation import testConversation
from lisaOnStreetConversation import LisaOnStreetConversation
from registrarConversation import RegistrarConversation
from classmateConversation import ClassmateConversation
from vendorConversationV2 import VendorConversation
from restaurantConversation import RestaurantConversation
from restaurantConversationV2 import RestaurantConversationV2


# nlp tool for Chinese segmentation
import spacy
import thulac



class ConversationHandler:

    def __init__(self, cnHelper=None, enHelper=None):
        self.ConversationDict = dict()
        self.RootFolder = os.path.dirname(os.path.abspath(__file__))
        self.GlobalSetting = {
                                'input_language':   'CN',
                                'output_language':  'CN',
                                'difficulty':       1 ,
                                'learning_mode':    True
                            }
        self.CNHelper = thulac.thulac() if cnHelper is None else cnHelper
        self.ENHelper = spacy.load('en') if enHelper is None else enHelper
        self.GameProgressProfile = dict()
        self.GameProgressProfile['lisa_on_street'] = GameLogicConstraint('lisa_on_street')
        self.ActionHandler = ActionHandler()
        self.ActionHandler.startListening()
        # print(' [*] Preparing for transcriptHandler ...... ')
        # self.TranscriptHandlerDict = {
        #     'teacher':  transcriptHandlerV2.TranscriptCorrection('teacher', self.CNHelper),
        #     'lisa_on_campus':   transcriptHandlerV2.TranscriptCorrection('lisa_on_campus', self.CNHelper),
        #     'roommate': transcriptHandlerV2.TranscriptCorrection('roommate', self.CNHelper),
        #     'registrar':    transcriptHandlerV2.TranscriptCorrection('registrar', self.CNHelper)
        # }


    def startConversation(self, username, userId, agent):
        # add new agents here
        if agent == 'lisa_on_campus':
            new_agent = LisaOnCampusConversation(username, userId, agent, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile) 
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'lisa_on_street':
            new_agent = LisaOnStreetConversation(username, userId, agent, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile) 
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'teacher':
            new_agent = LaoshiConversation(username, userId, agent, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile) 
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'roommate':
            new_agent = RoommateConversation(username, userId, agent, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile)  
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'registrar':
            new_agent = RegistrarConversation(username, userId, agent, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile)
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'classmate':
            new_agent = ClassmateConversation(username, userId, agent, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile)
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'friend':
            menu = 'drink'
            new_agent = VendorConversation(username, userId, agent, menu, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile)
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'boss':
            menu = 'foodsnack'
            new_agent = VendorConversation(username, userId, agent, menu, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile)
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'miss':
            menu = 'souvenir'
            new_agent = VendorConversation(username, userId, agent, menu, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile)
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'auntie':
            menu = 'travelnecessities'
            new_agent = VendorConversation(username, userId, agent, menu, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile)
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'master':
            new_agent = ShiFuConversation(username, userId, agent, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile)
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'waiter':
            new_agent = RestaurantConversationV2(username, userId, agent, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile, actionHandler=self.ActionHandler)
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        elif agent == 'test':
            new_agent = testConversation(username, userId, agent, self.CNHelper, self.ENHelper, gameProgress=self.GameProgressProfile)
            new_agent.GlobalSetting = self.GlobalSetting
            self.ConversationDict[agent] = new_agent
            return new_agent
        

    def correctTranscript(self, text, agent):
        return self.ConversationDict[agent].guessUserInput(text)
    

    def getResponse(self, agent, inputText, difficulty=None, output_language=None):
        if agent not in self.ConversationDict:
            return '[*] Error: conversation has not been initiated', '[*] Error: conversation has not been initiated'
        response, debug_info = self.ConversationDict[agent].getResponse(inputText, difficulty, output_language)
        return response, debug_info

    def takeActions(self,userInput, agentResponse, debugInfo, gameProgressProfile):
        self.ConversationDict[userInput['wakeword']].takeActions(userInput, agentResponse, debugInfo, gameProgressProfile)
        self.ConversationDict[userInput['wakeword']].save()

    def getGameProgressProfile(self):
        return self.GameProgressProfile


    def __loadAuxiliaryJson(self):
        auxDict = dict()
        self.ResourceFolder = os.path.join(self.RootFolder, 'resources/')
        for root, dirs, files in os.walk(self.ResourceFolder):
            for file in files:
                if file.endswith('auxiliary.json'):
                    with open(os.path.join(self.ResourceFolder, file), 'r', encoding='utf-8') as fp:
                        auxDict[file] = json.load(fp)
        return auxDict


    def manageUUID(self):
        '''
        Assign a UUID to a language block that doesn't have UUID;
        Re-assign a new UUID to a language block that has a duplicate UUID
        '''
        uuid_pool = list()
        # policy.json
        self.PolicyFile = os.path.join(self.RootFolder, 'resources/policy.json')
        with open(self.PolicyFile, 'r', encoding='utf-8') as file:
            policy = json.load(file)
        for agent, agentContent in policy.items():
            for intent, value in agentContent['action'].items():
                if intent == 'error_handling':
                    for error_type, responses in value.items():
                        for eachRes in responses:
                            if 'uuid' not in eachRes.keys() or eachRes['uuid']=='' or eachRes['uuid'] in uuid_pool:
                                eachRes['uuid'] = str(uuid.uuid4())
                            uuid_pool.append(eachRes['uuid'])
                            if 'jump_to_intent' not in eachRes.keys():
                                eachRes['jump_to_intent'] = ''
                            for eachAuto in eachRes['auto_fill']:
                                if 'uuid' not in eachAuto.keys():
                                    eachAuto['uuid'] = str(uuid.uuid4())
                                uuid_pool.append(eachRes['uuid'])
                                if 'jump_to_intent' not in eachAuto.keys():
                                    eachAuto['jump_to_intent'] = ''
                elif type(value)==list:
                    for eachRes in value:
                        if 'uuid' not in eachRes.keys():
                            eachRes['uuid'] = str(uuid.uuid4())
                        uuid_pool.append(eachRes['uuid'])
                        if 'jump_to_intent' not in eachRes.keys():
                            eachRes['jump_to_intent'] = ''
                        for eachAuto in eachRes['auto_fill']:
                            if 'uuid' not in eachAuto.keys():
                                eachAuto['uuid'] = str(uuid.uuid4())
                            uuid_pool.append(eachRes['uuid'])
                            if 'jump_to_intent' not in eachAuto.keys():
                                eachAuto['jump_to_intent'] = ''
                elif type(value) == str:
                        continue
        policyFile = os.path.join(self.RootFolder, 'resources/policy.json')
        with open(policyFile, 'w', encoding='utf-8') as fp:
            json.dump(policy, fp, ensure_ascii=False, indent=4)
        # _auxiliary.json
        auxiliaryFiles = self.__loadAuxiliaryJson()
        for filename, content in auxiliaryFiles.items():
            for eachRes in content['option']:
                if 'uuid' not in eachRes.keys():
                    eachRes['uuid'] = str(uuid.uuid4())
                uuid_pool.append(eachRes['uuid'])
                if 'jump_to_intent' not in eachRes.keys():
                    eachRes['jump_to_intent'] = ''
                for eachAuto in eachRes['auto_fill']:
                    if 'uuid' not in eachAuto.keys():
                        eachAuto['uuid'] = str(uuid.uuid4())
                    uuid_pool.append(eachRes['uuid'])
                    if 'jump_to_intent' not in eachAuto.keys():
                        eachAuto['jump_to_intent'] = ''
            auxFile = os.path.join(self.RootFolder, 'resources/{}'.format(filename))
            with open(auxFile, 'w', encoding='utf-8') as fp:
                json.dump(auxiliaryFiles[filename], fp, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    # add new agents here

    "{'msg': '你的句子', 'wakeword': 'lisha', 'username': 'xxx', 'channelIndex': 0, 'userId' : }"
    c = ConversationHandler()
    w = c.startConversation('xx',99, agent='waiter')
    print(c.getResponse('waiter', '坐包间'))
    # print(w.getResponse('不 用 了', difficulty=1))
    # print(vendor.getResponse('你卖什么', difficulty=10))
    # print(vendor.getResponse('我想买蛋糕', difficulty=10))
    # print(vendor.getResponse('我要一个', difficulty=10))
    # print(vendor.getResponse('我要圆的', difficulty=10))
    # print(vendor.getResponse('能便宜点 吗', difficulty=10))
    # print(vendor.getResponse('能便宜点 吗', difficulty=10))
    # print(vendor.getResponse('能便宜点 吗', difficulty=10))
    # print(vendor.getResponse('我要二块', difficulty=10))
    # print(vendor.getResponse('我买了', difficulty=10))
    # print(vendor.getResponse('微信支付', difficulty=10))
    # print(vendor.getResponse('谢谢', difficulty=10))
    # print(vendor.getResponse('我想买两块蛋糕', difficulty=10))
    # print(vendor.getResponse('我想方的蛋糕', difficulty=10))
    # print(vendor.getResponse('现金', difficulty=10))
    # print(vendor.getResponse('我想买三块圆的蛋糕', difficulty=10))
    # print(vendor.getResponse('支付宝', difficulty=10))
    # print(vendor.getResponse('能不能便宜点', difficulty=10))
    # print(vendor.getResponse('我买五个', difficulty=10))

    # print(vendor.getResponse('你 好', difficulty=5))
    # print(vendor.getResponse('我 想 买 蛋 糕', difficulty=5))
    # print(vendor.getResponse('我 要 圆 的', difficulty=5))
    # print(vendor.getResponse('我 要 一 斤', difficulty=5))
    # print(vendor.getResponse('能 便 宜 点 吗', difficulty=5))
    # print(vendor.getResponse('我 买 一 个', difficulty=5))
    # print(vendor.getResponse('好 的，我 买 了', difficulty=5))
    # print(vendor.getResponse('我 用 微 信 支 付', difficulty=5))

    # print(vendor.getResponse('好 的', difficulty=10))
    # print(vendor.getResponse('微 信', difficulty=10))
    # print(vendor.getResponse('谢 谢', difficulty=10))

    # roommate = c.startConversation(user='Mou', agent='roommate')
    # registrar = c.startConversation(user='Mou',agent='registrar')
    # lisa = c.startConversation(user='Mou',agent='lisa_on_campus')
    # restaurant
    # lisaOnStreet = c.startConversation(user='Mou',agent='lisa_on_street')
    # restaurant = c.startConversation(user='Mou',agent='restaurant')
    # laoshi = c.startConversation(user='Mou',agent='teacher')
    # classmate = c.startConversation(user='Mou',agent='classmate')

    # use this for debugging

    # beginner classmate dialogue
    # print(roommate.getResponse('你 好'))
    # print(classmate.getResponse('你好，我正在找一本书'))
    # print(classmate.getResponse('是的，是我丢的。'))
    # print(classmate.getResponse('我叫刘英.'))
    # print(classmate.getResponse('谢谢你'))
    
    # advanced classmate dialogue
    # print(classmate.getResponse('你好', difficulty=2))
    # print(classmate.getResponse('你好，我正在找一本书', difficulty=2))
    # print(classmate.getResponse('太好了。你可以把书给我吗？', difficulty=2))
    # print(classmate.getResponse('我丢了我的中文课本', difficulty=2))
    # print(classmate.getResponse('蓝色的', difficulty=2))
    # print(classmate.getResponse('我叫刘英.', difficulty=2))
    # print(classmate.getResponse('一五六', difficulty=2))
    # print(classmate.getResponse('谢谢你', difficulty=2))

    # restaurant
    # print(restaurant.getResponse('我 想 要 凉 拌 黄 瓜', difficulty=5))
    # print(restaurant.getResponse('没 有 了', difficulty=5))
    # print(restaurant.getResponse('我 想 吃 北 京 烤 鸭', difficulty=5))
    # print(restaurant.getResponse('就 这 些', difficulty=5))
    # print(restaurant.getResponse('很 辣', difficulty=5))
    # print(restaurant.getResponse('来 五 份 包 子', difficulty=5))
    # print(restaurant.getResponse('好 的', difficulty=5))
    # print(restaurant.getResponse('微 信 支 付', difficulty=5))
    # print(restaurant.getResponse('我 想 要 这 个'))
    # print(restaurant.getResponse('请 给 我 一 份 炒 饭'))
    # print(restaurant.getResponse('我 想 要 一 杯 绿 茶'))
    # print(restaurant.getResponse('不 可 以'))
    # print(restaurant.getResponse('我 想 要 一 杯 绿 茶'))
    # print(restaurant.getResponse('可 以'))
    # print(restaurant.getResponse('请 给 我 一 份 炒 饭'))
    # print(restaurant.getResponse('请 给 我 一 碗 酸 辣 汤'))
    # print(restaurant.getResponse('请 给 我 一 份 炒 饭 和 一 碗 酸 辣 汤'))
    # print(restaurant.getResponse('不 了 谢 谢'))
    # print(restaurant.getResponse('菜 很 好 吃'))
    # print(restaurant.getResponse('菜 很 好 吃'))
    # print(restaurant.getResponse('不 了 谢 谢'))
    # print(restaurant.getResponse('是 的'))
    # print(restaurant.getResponse('给 你'))

    # restaurantV2 = c.startConversation('xx', agent='waiter')
    # print(restaurantV2.getResponse('你好', difficulty=5))
    # print(restaurantV2.getResponse('坐包间', difficulty=5))
    # print(restaurantV2.getResponse('能重复一遍吗', difficulty=5))
    # print(restaurantV2.getResponse('能用英文重复一遍吗', difficulty=5))
    # print(restaurantV2.getResponse('能重复一遍吗', difficulty=5))
    # print(restaurantV2.getResponse('好 的', difficulty=5))
    # print(restaurantV2.getResponse('我 想 吃 北 京 烤 鸭', difficulty=5))
    # print(restaurantV2.getResponse('不 用 了', difficulty=5))
    # print(restaurantV2.getResponse('能重复一遍吗', difficulty=5))
    # print(restaurantV2.getResponse('不 用 了', difficulty=5))
    # print(restaurantV2.getResponse('不 用 了', difficulty=5))
    # print(restaurantV2.getResponse('不 用 了', difficulty=5))
    # print(restaurantV2.getResponse('很 辣', difficulty=5))

    # master = c.startConversation('xx', agent='master')
    # print(master.getResponse('你好', difficulty=5))
    # print(master.getResponse('对的', difficulty=5))
    # print(master.getResponse('对的', difficulty=5))





