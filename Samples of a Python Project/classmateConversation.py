from conversation import Conversation


class ClassmateConversation(Conversation):

    def _generateResponseText(self, intent, entities, difficulty):
        text = ''
        self.detailed_intent = None
        #section for help functions
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
        elif intent == 'positive':
            second_last_intent = self.UserIntent[-1]
            self.detailed_intent = 'positive_to_' + second_last_intent
            text = self._randomResponse(self.detailed_intent, difficulty)
            self.UserIntent.append(self.detailed_intent)
        elif type(self.Actions[intent]) == str:
            if len(self.AgentUtterances) != 0 and intent != self.AgentUtterances[-1]['slot']:
                if self.GlobalSetting['learning_mode']:
                    text = self.LearningMode[self.OutputLanguage]
                else:
                    text = self.AgentUtterances[-1][self.OutputLanguage]
            else:
                text = self._randomResponseWithSlot(intent, difficulty)
                self.UserIntent.append(intent)



        # #when the user answers yes after the agent asks if they lost their book
        # elif intent == "positive" and self.AgentUtterances[-1]["slot"] == "answer-book":
        #     detailed_intent = "positive-name"
        #     text = self._randomResponse(detailed_intent, difficulty)
        #     self.UserIntent.append(detailed_intent)
        # #when the user answers with their name after the agent asks for their name
        # elif intent == "answer-name" and self.AgentUtterances[-1]["slot"] == "answer-name":
        #     detailed_intent = "answer-name-positive"
        #     text = self._randomResponse(detailed_intent, difficulty)
        #     self.UserIntent.append(detailed_intent)
        # #begin classmate-specific agent logic
        # elif intent == 'hello':
        #     text = self._randomResponse(intent, difficulty)
        #     self.UserIntent.append(intent)
        # #temporary detection of incorrect answers for advanced dialogue
        # elif intent == "answer-book-type" and entities["type-of-book"]["value"] != "中 文":
        #     detailed_intent = "no_intent"
        #     text = self._randomResponse(detailed_intent, difficulty)
        #     self.UserIntent.append(detailed_intent)
        # elif intent == "answer-book-color" and entities["color"]["value"] != "蓝 色":
        #     detailed_intent = "no_intent"
        #     text = self._randomResponse(detailed_intent, difficulty)
        #     self.UserIntent.append(detailed_intent)
        #standard edge cases
        else:
            text = self._randomResponse(intent, difficulty)
            self.UserIntent.append(intent)
#                return text
#            correct_intent = self.AgentUtterances[-1]["slot"]
#            last_question = self.AgentUtterances[-1][self.OutputLanguage]
#            #
#            if len(correct_intent) == 0:
#                if intent == 'positive' or intent == 'negative':
#                    self.UserIntent.append(intent)
#                    return ''
#                self.UserIntent.append(intent)
#                text = self._randomResponse(intent, difficulty)
#            if correct_intent == "answer-book":
            
#               else:
#                    if (self.GlobalSetting['learning_mode'] == True):
#                        text = self.LearningMode[self.OutputLanguage]
#                    else:
#                        text = last_question
#            
#            else:
#                #if the UserIntent exists
#
#                text = self._randomResponse(intent, difficulty)
#                self.UserIntent.append(intent)

        return text

    def takeActions(self,userInput, agentResponse, debugInfo, gameProgressProfile):
        super().takeActions(userInput, agentResponse, debugInfo, gameProgressProfile)
        if agentResponse['agent'] == 'classmate' and debugInfo['slot_final']:
            gameProgressProfile['lisa_on_street'].updateTaskProcess('book')
            print(gameProgressProfile['lisa_on_street'].getTaskProcess('garden'))
            self.apiHandler.checkOffQuest(agentResponse['IP'], 'garden', gameProgressProfile['lisa_on_street'].getTaskProcess('garden'))