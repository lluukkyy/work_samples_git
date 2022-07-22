from conversation import Conversation


class RegistrarConversation(Conversation):
    price = 0
    textbook_end_flag = False

    def _generateResponseText(self, intent, entities, difficulty):
        text = ''
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
        else:
            if len(self.AgentUtterances) == 0:
                text = self._randomResponse(intent, difficulty)
                self.UserIntent.append(intent)
                return text
            correct_intent = self.AgentUtterances[-1]["slot"]
            last_question = self.AgentUtterances[-1][self.OutputLanguage]
            if len(correct_intent) == 0:
                if intent == 'positive' or intent == 'negative':
                    self.UserIntent.append(intent)
                    return ''
                self.UserIntent.append(intent)
                text = self._randomResponse(intent, difficulty)
                if intent == "answer-next-book-negative":
                    text = text.replace("_@price_", str(self.price))
                return text
            elif correct_intent == "answer-major":
                if intent == "answer-book-for-course":
                    text = self._randomResponse("answer-major", difficulty)
                    self.UserIntent.append("answer-major")
                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        text = last_question
            elif correct_intent == "answer-process":
                if intent == "positive":
                    detailed_intent = "answer-process-positive"
                    text = self._randomResponse(detailed_intent, difficulty)
                    self.UserIntent.append(detailed_intent)
                elif intent == 'negative':
                    detailed_intent = "answer-process-negative"
                    text = self._randomResponse(detailed_intent, difficulty)
                    self.UserIntent.append(detailed_intent)
                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        text = last_question
            elif correct_intent == "answer-student-id-insurance":
                if intent == "answer-student-id":
                    text = self._randomResponse(correct_intent, difficulty)
                    self.UserIntent.append(correct_intent)
                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        if (self.GlobalSetting['learning_mode'] == True):
                            text = self.LearningMode[self.OutputLanguage]
                        else:
                            text = last_question
            elif correct_intent == 'answer-student-id-schedule':
                if intent == "answer-student-id":
                    text = self._randomResponse(correct_intent, difficulty)
                    self.UserIntent.append(correct_intent)
                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        if (self.GlobalSetting['learning_mode'] == True):
                            text = self.LearningMode[self.OutputLanguage]
                        else:
                            text = last_question
            elif correct_intent == 'answer-citizenship' or correct_intent == 'answer-university':
                if intent == 'answer-citizenship-or-university':
                    text = self._randomResponse(correct_intent, difficulty)
                    self.UserIntent.append(correct_intent)
                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        if (self.GlobalSetting['learning_mode'] == True):
                            text = self.LearningMode[self.OutputLanguage]
                        else:
                            text = last_question
            elif correct_intent == 'answer-foreign-student':
                if intent == 'negative' or intent == 'positive':
                    text = self._randomResponse(correct_intent, difficulty)
                    self.UserIntent.append(correct_intent)
                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        if (self.GlobalSetting['learning_mode'] == True):
                            text = self.LearningMode[self.OutputLanguage]
                        else:
                            text = last_question
            elif (intent == 'negative' or intent == 'end-of-purchase') and correct_intent == "answer-book-for-course":
                new_intent = "answer-next-book-negative"
                text = self._randomResponse(new_intent, difficulty)
                self.UserIntent.append(new_intent)
                self.detailed_intent = new_intent
                entities['price'] = {"value": self.price}
                text = text.replace("_@price_", str(self.price))
                self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@price_", str(self.price))
                self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@price_", str(self.price))
                self.price = 0
            elif correct_intent == "answer-exercise":
                if intent == 'positive' or intent == 'negative':
                    new_intent = "answer-exercise-" + intent
                    text = self._randomResponse(new_intent, difficulty)
                    self.UserIntent.append(new_intent)
                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        text = last_question
            elif correct_intent == intent:
                text = self._randomResponse(intent, difficulty)
                self.UserIntent.append(intent)
                if intent == 'answer-book-type':
                    value = entities['book_type']['value']
                    if value:
                        price = self.PlaceholderDict['@bookprice'][value]
                        self.price += price
                        text = text.replace("_@price_", str(price))
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@price_", str(price))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@price_", str(price))
            elif intent == 'positive' or intent == 'negative':
                return ''
            else:
                if len(self.UserIntent) > 0:
                    last_user_intent = self.UserIntent[-1]
                    if last_user_intent == 'hello' or last_user_intent == "answer-process-positive":
                        if intent == 'negative' or intent == "thanks":
                            text = self._randomResponse("goodbye", difficulty)
                            self.UserIntent.append("goodbye")
                        else:
                            if (self.GlobalSetting['learning_mode'] == True):
                                text = self.LearningMode[self.OutputLanguage]
                            else:
                                text = last_question
                    else:
                        if (self.GlobalSetting['learning_mode'] == True):
                            text = self.LearningMode[self.OutputLanguage]
                        else:
                            text = last_question

                else:
                    if (self.GlobalSetting['learning_mode'] == True):
                        text = self.LearningMode[self.OutputLanguage]
                    else:
                        text = last_question

        return text

    def takeActions(self,userInput, agentResponse, debugInfo, gameProgressProfile):
        super().takeActions(userInput, agentResponse, debugInfo, gameProgressProfile)
        if agentResponse['user_intent'] == 'answer-next-book-negative':
            if 'price' in debugInfo['entities']:
                self.MoneySpent = debugInfo['entities']['price']['value']
                message = self.apiHandler.updateResponseForCreditBalance(userInput, agentResponse)
                agentResponse['paras']['balance'] = message['balance']
                if len(message['EN']) != 0:
                    agentResponse['text'] = message['CN'] if self._ifContainChinese(agentResponse['text']) else message['EN']