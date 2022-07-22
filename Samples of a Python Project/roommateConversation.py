from conversation import Conversation


class RoommateConversation(Conversation):
    def _generateResponseText(self, intent, entities, difficulty):
        text = ''
        self.detailed_intent = None
        if intent == 'hello':
            text = self._randomResponse(intent, difficulty)
            self.UserIntent.append(intent)
        elif intent == 'skip':
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
            return ''
        elif type(self.Actions[intent]) == str:
            if len(self.AgentUtterances) != 0:
                if intent == self.AgentUtterances[-1]['slot']:
                    text = self._randomResponseWithSlot(intent, difficulty)
                    self.UserIntent.append(intent)
                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        text = self.AgentUtterances[-1][self.OutputLanguage]
            else:
                text = self._randomResponseWithSlot(intent, difficulty)
                self.UserIntent.append(intent)
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
            if correct_intent == 'final':
                text = self._randomResponse(intent, difficulty)
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
