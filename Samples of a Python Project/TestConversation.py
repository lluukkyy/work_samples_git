"""
@author: Sylvia Hua
@email: huaz2@rpi.edu
"""
'''
copied from LisaOnCampusConversation
USED FOR TEST AND DEBUG ONLY
'''



from conversation import Conversation


class testConversation(Conversation):

    def _generateResponseText(self, intent, entities, difficulty):
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
        elif intent == "repeat":
            old_language = self.OutputLanguage
            if "language" in entities:
                self.OutputLanguage = entities["language"]["value"]
            if len(self.AgentUtterances) > 0 and len(self.UserIntent) != 0:
                last_intent = self.UserIntent[-1]
                if "difficulty" in entities:
                    if entities["difficulty"]["value"] == "hard":
                        if difficulty < self.DifficultyLevel:
                            difficulty += 1
                    else:
                        if difficulty > 0:
                            difficulty -= 1
                    text = self._randomResponse(last_intent, difficulty)
                else:
                    text = self._getAllRepeatText()
                self.OutputLanguage = old_language
            else:
                text = self._randomResponse(intent, difficulty)
                self.OutputLanguage = old_language

        else:
            if len(self.AgentUtterances) == 0:
                text = self._randomResponse(intent, difficulty)
                self.UserIntent.append(intent)
                return text
            correct_intent = self.AgentUtterances[-1]["slot"]
            if len(correct_intent) == 0:
                if intent == 'positive' or intent == 'negative':
                    self.UserIntent.append(intent)
                    return ''
                self.UserIntent.append(intent)
                return self._randomResponse(intent, difficulty)
            last_question = self.AgentUtterances[-1][self.OutputLanguage]
            if correct_intent == "answer-visiting":
                if intent == "positive":
                    detailed_intent = "answer-visiting-positive"
                    text = self._randomResponse(detailed_intent, difficulty)
                    self.UserIntent.append(detailed_intent)
                elif intent == "negative":
                    detailed_intent = "answer-visiting-negative"
                    self.UserIntent.append(detailed_intent)
                    text = self._randomResponse(detailed_intent, difficulty)
                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        text = last_question
            elif correct_intent == "answer-course":
                if intent == "positive" or intent == "negative" and "difficulty" not in entities:
                    text = self._randomResponse(correct_intent, difficulty)
                    self.UserIntent.append(correct_intent)
                elif intent == "ask-course-detail" or "difficulty" in entities:
                    text = self._randomResponse(intent, difficulty)
                    self.UserIntent.append(intent)
                    if "activity" in entities:
                        text = text.replace("@activity",entities["activity"])
                elif intent == "ask-course-recommendation":
                    text = self._randomResponse(intent, difficulty)
                    self.UserIntent.append(intent)
                elif intent == correct_intent:
                    text = self._randomResponse(correct_intent, difficulty)
                    self.UserIntent.append(correct_intent)
                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        text = last_question
            elif correct_intent == "answer-greeting":
                if intent == 'answer-greeting-and-ask':
                    text = self._randomResponse(intent, difficulty)
                elif intent == correct_intent or intent == 'positive' or intent == 'negative':
                    self.UserIntent.append('answer-greeting')
                    text = self._randomResponse('answer-greeting', difficulty)
                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        text = last_question
                self.UserIntent.append(intent)
            elif intent == correct_intent:
                text = self._randomResponse(intent, difficulty)
                self.UserIntent.append(intent)
            else:
                if (self.GlobalSetting['learning_mode'] == True):
                    text = self.LearningMode[self.OutputLanguage]
                else:
                    text = last_question
        return text

