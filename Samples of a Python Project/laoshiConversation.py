"""
@author: Sylvia Hua
@email: huaz2@rpi.edu
"""
import json
import os, sys
import warnings

from conversation import Conversation
V1Folder = os.path.dirname(os.path.abspath(__file__))
sys.path.append(V1Folder)
from dependencies import learningAssistantHandler


class LaoshiConversation(Conversation):
    PRACTICE_MODE = False
    practice_language_switch= ""
    def __init__(self, username, userId, gesture_handler, agent, cnHelper=None, enHelper=None, gameProgress=None):
        super().__init__(username, userId, gesture_handler, agent, cnHelper, enHelper, gameProgress)
        ### something wrong with the learning assistant
        ### It would affect "teacher" conversation to be initiated
        ### Uncomment the 4 lines below only if the learning assistant goes back to work
        ### Do the same things for start_dialogue_engine.py --> __main__()
        # self.ptcaHandler = learningAssistantHandler.PitchhContourHandler()
        # self.ptca_words = self.__loadWordList()
        # self.practice_data = self.__loadPracticeData()
        # self.practice_list = None

    def _generateResponseText(self, intent, entities, difficulty):
        # if self.PRACTICE_MODE:
        #     if len(self.practice_list) == 0:
        #         self.PRACTICE_MODE = False
        #         self.detailed_intent = 'exit_practice'
        #         return '练习完成'
        #     else:
        #         self.detailed_intent = 'practice'
        #         return self.practice_list.pop()
        text = ''
        if intent == 'language-switch':
            text = self._randomResponse(intent, difficulty)
        elif intent == 'switch-input-language':
            text = self._randomResponse(intent, difficulty)
        elif intent == 'switch-output-language':
            if self.PRACTICE_MODE: 
                intent += "-practice-"+ self.practice_language_switch
            text = self._randomResponse(intent, difficulty) 
        elif intent == 'skip':
            text = self._randomResponse(intent, difficulty)
        elif intent == 'ptca':
            text = self._randomResponse(intent, difficulty)
        elif intent == 'repeat' or intent == 'hint':
            if self.PRACTICE_MODE: intent += '-practice'
            if "language" in entities:
                self.OutputLanguage = entities["language"]["value"]
            text = self._randomResponse(intent, difficulty)
        elif intent == 'storytelling':
            if self.PRACTICE_MODE:
                if True:
                #if self.ActionHandler.getGestureBy(userID=str(self.UserId)) == "train":
                    intent += '-practice'
                    self.PRACTICE_MODE = False
            text = self._randomResponse(intent, difficulty)
        elif intent == 'switch-difficulty':
            text = self._randomResponse(intent,difficulty)
        elif intent == 'onboarding':
            self.PRACTICE_MODE = True
            # if 'category' not in entities:
            #     return 'practice_error'
            # text = self._practice(entities['category']['value'])
            text = self._randomResponse(intent, difficulty)
        elif intent == 'scene-switch':
            text = self._randomResponse(intent,difficulty)
        return text

    def _resolveParameters(self, rawText, intent, entity=None):
        paras = {
            'value': '',
            'error': ''
        }
        if self.PRACTICE_MODE:
            if intent == 'switch-output-language':
                if '中文' in rawText or 'chinese' in rawText.lower():
                    self.practice_language_switch = "CN"
                elif '英文' in rawText or 'english' in rawText.lower():
                    self.practice_language_switch = "EN"
            else:
                paras['value'] = 'practice_next'
            return paras
        if len(intent) == 0:
            paras["error"] = "no_intent"
            return paras
        if intent == 'language-switch':
            if '中文' in rawText or 'chinese' in rawText:
                self.OutputLanguage = 'CN'
                self.GlobalSetting['output_language'] = 'CN'
            elif '英文' in rawText or 'english' in rawText:
                self.OutputLanguage = 'EN'
                self.GlobalSetting['output_language'] = 'EN'
            else:
                if self.GlobalSetting['output_language'] == 'CN':
                    self.OutputLanguage = 'EN'
                    self.GlobalSetting['output_language'] = 'EN'
                else:
                    self.GlobalSetting['output_language'] = 'CN'
                    self.OutputLanguage = 'CN'
            self.GlobalSetting['output_language'] = self.OutputLanguage
        elif intent == 'switch-input-language':
            if 'language' in entity:
                value = entity['language']['value']
            else:
                firstLetter = self.GlobalSetting['input_language'][0]
                value = str(chr(2*ord('D') - ord(firstLetter))) + 'N'
            self.GlobalSetting['input_language'] = value
            paras['value'] = value
        elif intent == 'switch-output-language':
            if 'language' in entity:
                value = entity['language']['value']
            else:
                firstLetter = self.GlobalSetting['output_language'][0]
                value = str(chr(2*ord('D') - ord(firstLetter))) + 'N'
            self.OutputLanguage = value
            self.GlobalSetting['output_language'] = value
            paras['value'] = value
        elif intent == 'ptca':
            if '词汇' in entity:
                paras['value'] = entity['词汇']['value'].replace(' ', '')
            elif 'vocabulary' in entity:
                paras['vocab'] = entity['vocabulary']['value']
                paras['value'] = self._mapWord(paras['vocab'].strip())
                if len(paras['value']) == 0:
                    paras['error'] = 'ptca_data_not_available'
            else:
                nouns = self._extractNouns(rawText)
                if len(nouns) > 0:
                    paras['vocab'] = paras['value']
                    new_word = self._mapWord(nouns[0].strip())
                    paras['value'] = new_word
                    if len(new_word) == 0:
                        paras['error'] = 'ptca_data_not_available'
                else:
                    paras['error'] = 'ptca_no_param'
        elif intent == 'storytelling':
            if '词汇' in entity:
                paras['value'] = entity['词汇']['value'].replace(' ', '')
            elif 'vocabulary' in entity:
                paras['value'] = entity['vocabulary']['value'].replace(' ', '')
            else:
                # find all nouns in raw text
                nouns = self._extractNouns(rawText)
                if len(nouns) > 0:
                    paras['vocab'] = paras['value']
                    paras['value'] = nouns[0]
                else:
                    paras['error'] = 'storytelling_no_param'
        elif intent == 'switch-difficulty':
            if "difficulty" in entity:
                if entity["difficulty"]["value"] == "hard":
                    if self.Difficulty < self.DifficultyLevel:
                        self.Difficulty += 1
                else:
                    if self.Difficulty > 1:
                        self.Difficulty -= 1
                self.GlobalSetting['difficulty'] = self.Difficulty
        return paras

    def __loadWordList(self):
        self.RootFolder = os.path.dirname(os.path.abspath(__file__))
        self.ResponseFile = os.path.join(self.RootFolder, 'resources/ptca_words.json')
        if not os.path.exists(self.ResponseFile):
            warnings.warn('Fail to load response pool: <ptca_words.json> file is missing in /resources ...')
            return None
        with open(self.ResponseFile, 'r', encoding='utf-8') as file:
            words = json.load(file)
            return words

    def __loadPracticeData(self):
        self.RootFolder = os.path.dirname(os.path.abspath(__file__))
        self.ResponseFile = os.path.join(self.RootFolder, 'resources/practice_data.json')
        if not os.path.exists(self.ResponseFile):
            warnings.warn('Fail to load response pool: <practice_data.json> file is missing in /resources ...')
            return None
        with open(self.ResponseFile, 'r', encoding='utf-8') as file:
            words = json.load(file)
            return words


    def _mapWord(self,word):
        if word in self.ptca_words:
            return self.ptca_words[word]
        return ''

    def _practice(self,category):
        self.practice_list = self.practice_data[category].copy()
        return self.practice_list.pop()

    def takeActions(self,userInput, agentResponse, debugInfo, gameProgressProfile):
        pass



