"""
@author: Xiangyang Mou
@email:  moutaigua8183@gmail.com
"""


from conversation import Conversation

# Merge LisaOnCampus and create LisaOnStreet
# THIS IS NOT TESTED

class LisaOnStreetConversation(Conversation):

    def _generateResponseText(self, intent, entities, difficulty):
        self.detailed_intent = None
        text = ''
        if intent == 'hello':
            text = self._randomResponse(intent, difficulty)
            self.UserIntent.append(intent)
        elif intent == 'skip':
            text = self._simulateUserInput()
        elif intent == 'hint':
            text = self._generateHint()
        elif intent == 'goodbye':
            text = self._randomResponse(intent, difficulty)
            self.UserIntent.append(intent)
        elif intent == 'repeat':
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
        elif intent == 'positive':
            second_last_intent = self.UserIntent[-1]
            self.detailed_intent = 'positive_to_' + second_last_intent
            text = self._randomResponse(self.detailed_intent, difficulty)
            if self.detailed_intent == 'positive_to_hello':
                self.GameLogicHandler.startTask('street')
            elif self.detailed_intent == 'positive_to_task_complete_street':
                self.GameLogicHandler.startTask('garden')
            self.UserIntent.append(self.detailed_intent)
        elif intent == 'task_complete':
            if self.GameLogicHandler.CurrentTask == '':
                self.detailed_intent = 'task_not_started'
            elif self.GameLogicHandler.checkCurrentTaskComplete():
                self.detailed_intent = intent + '_' + self.GameLogicHandler.CurrentTask
                self.GameLogicHandler.endTask()
                self.UserIntent.append(self.detailed_intent)
            else:
                self.detailed_intent = 'task_not_completed'
            text = self._randomResponse(self.detailed_intent, difficulty)
        else:
            text = self._randomResponse(intent, difficulty)
            self.UserIntent.append(intent)
        return text

    def takeActions(self,userInput, agentResponse, debugInfo, gameProgressProfile):
        super().takeActions(userInput, agentResponse, debugInfo, gameProgressProfile)
        if agentResponse['user_intent'] == 'positive_to_hello':
            # apiHandler.startQuest(agentResponse['IP'], 'task_1')
            self.apiHandler.showQuest(agentResponse['IP'], 'street', gameProgressProfile['lisa_on_street'].getTaskList('street'))
        elif agentResponse['user_intent'] == 'positive_to_task_complete_street':
            # apiHandler.startQuest(agentResponse['IP'], 'task_2')
            self.apiHandler.showQuest(agentResponse['IP'], 'garden', gameProgressProfile['lisa_on_street'].getTaskList('garden'))
        elif agentResponse['user_intent'] == 'task_complete_street':
            # apiHandler.completeQuest(agentResponse['IP'], 'task_1')
            self.apiHandler.hideQuest(agentResponse['IP'], 'street')
        elif agentResponse['user_intent'] == 'task_complete_garden':
            # apiHandler.completeQuest(agentResponse['IP'], 'task_2')
            self.apiHandler.hideQuest(agentResponse['IP'], 'garden')