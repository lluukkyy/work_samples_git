"""
@author: Siyi Zhou
@email: zhous4@rpi.edu
"""

import json
import os, sys
import warnings

from conversation import Conversation

V1Folder = os.path.dirname(os.path.abspath(__file__))
sys.path.append(V1Folder)
from dependencies import learningAssistantHandler


class ShiFuConversation(Conversation):
    def _generateResponseText(self, intent, entities, difficulty):
        self.detailed_intent = None
        if intent == 'skip':
            text = self._simulateUserInput()
        elif intent == 'hint':
            text = self._generateHint()
        elif intent == "repeat":
            old_language = self.OutputLanguage
            if 'language' in entities:
                self.OutputLanguage = entities["language"]["value"]
            if len(self.AgentUtterances) == 0:
                text = self._randomResponse(intent, difficulty)
            elif 'difficulty' in entities and len(self.UserIntent) > 0:
                last_intent = self.UserIntent[-1]
                difficulty += int(entities['difficulty']['value'] == 'hard')
                difficulty -= int(entities['difficulty']['value'] == 'easy')
                difficulty  = max(min(difficulty, self.DifficultyLevel), 1)
                text        = self._randomResponse(last_intent, difficulty)
            else:
                text = self._getAllRepeatText()
            self.OutputLanguage = old_language
        elif intent == 'hello':
            text = self._randomResponse(intent, difficulty)
            self.UserIntent.append(intent)
        elif intent == 'positive':
            second_last_intent = self.UserIntent[-1]
            self.detailed_intent = 'positive_to_' + second_last_intent
            text = self._randomResponse(self.detailed_intent, difficulty)
            self.UserIntent.append(self.detailed_intent)
        elif intent == 'negative':
            second_last_intent = self.UserIntent[-1]
            self.detailed_intent = 'negative_to_' + second_last_intent
            text = self._randomResponse(self.detailed_intent, difficulty)
            self.UserIntent.append(self.detailed_intent)
        elif intent == 'test':
            text = ''
            self.UserIntent.append(intent)
        else:
            text = self._randomResponse(intent, difficulty)
            self.UserIntent.append(intent)
        
        return text

    def takeActions(self,userInput, agentResponse, debugInfo, gameProgressProfile):
        super().takeActions(userInput, agentResponse, debugInfo, gameProgressProfile)
        if agentResponse['user_intent'] == 'hello':
            self.apiHandler.startOrStopTaiji(True, userInput['IP'])
        elif agentResponse['user_intent'] == 'test':
            self.apiHandler.startOrStopTaiji(False, userInput['IP'])

