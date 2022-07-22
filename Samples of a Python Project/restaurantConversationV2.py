from conversation import Conversation
import json
import math
import random
import os
import word2number.w2n as w2n
from dependencies.apiWrapper import APIWrapper


# dish recommend repeat issue
# simple version


class RestaurantItem():
    def __init__(self, item_dict):
        self.item_name = item_dict["Item_name"]  # String: String
        self.price = item_dict["Price"]
        self.specs = item_dict["Spec"]
        self.units = item_dict["Unit"]
        self.category = item_dict["Category"]
        self.special = item_dict["Special"]

    def get_name(self, lang):
        return self.item_name[lang]

    def check_price(self):
        return self.price

    def check_unit(self, player_unit):
        return player_unit in self.units["CN"]

    def check_spec(self, spec_):
        return spec_ in self.specs["EN"]

    def get_specs(self, lang):
        return self.specs[lang]

    def get_cat(self, lang):
        return self.category[lang]

    def translate_spec_from(self, spec, curr_lang):
        EN_specs = self.specs["EN"]
        CN_specs = self.specs["CN"]
        # for cat in self.specs.values():
        #     for spec_ in cat['CN']:
        #         CN_specs.append(spec_)
        #     for spec_ in cat['EN']:
        #         EN_specs.append(spec_)
        # lang here means current language
        if curr_lang == 'EN':
            return CN_specs[EN_specs.index(spec)]
        else:
            return EN_specs[CN_specs.index(spec)]

    def is_special(self):
        return self.special == "1"


class RestaurantConversationV2(Conversation):
    def __init__(self, username, userId, agent, cnHelper=None, enHelper=None, gameProgress=None, actionHandler=None):
        super().__init__(username, userId, agent, cnHelper=cnHelper, enHelper=enHelper, gameProgress=gameProgress,
                         actionHandler=actionHandler)
        self.user_id = userId
        self.items = dict()
        self.V2Folder = os.path.dirname(os.path.abspath(__file__))
        self.MenuFile = os.path.join(self.V2Folder, 'resources/')
        self.MenuFile = self.MenuFile + 'restaurant_menu.json'

        self.special_dish = None
        self.CN_item_lst = []
        self.EN_item_lst = []
        with open(self.MenuFile, encoding='utf-8') as f:
            item_lists = json.load(f)
            for item_dict in item_lists:
                a_item = RestaurantItem(item_dict)
                if a_item.is_special():
                    if a_item.get_cat('EN') == 'Dish':
                        self.special_dish = a_item
                self.items[a_item.get_name("EN")] = a_item
                self.CN_item_lst.append(a_item.get_name('CN'))
                self.EN_item_lst.append(a_item.get_name('EN'))
        self.item_we_are_talking_EN = ''
        self.item_we_are_talking_CN = ''

        self.ordered_drink = False
        self.ordered_appetizers = False
        self.ordered_dish = False
        self.ordered_dessert = False

        self.recom_dish = None

        self.MoneySpent = 0
        self.order_history = []

    def calc_bill(self):
        total_price = 0
        for item in self.order_history:
            item_name = item[0]
            price = self.items[item_name].check_price()
            total_price += float(price)
        return str(total_price)

    def menu_has_it(self, item_name_):
        if isinstance(item_name_, str):
            return item_name_ in self.items.keys()
        elif isinstance(item_name_, list):
            flag = True
            for item in item_name_:
                if item not in self.items.keys():
                    flag = False
            return flag
        else:
            return False

    def add_to_notepad(self, entities_, item_name):
        if "number" in entities_.keys():
            ordered_item = str(self.items[item_name].get_name('CN')) + 'x' + str(w2n.word_to_num(
                entities_["number"]["value"]))
            ordered_price = str(self.items[self.items[item_name].get_name('EN')].check_price() * w2n.word_to_num(
                entities_["number"]["value"]))
        else:
            ordered_item = str(self.items[item_name].get_name('CN'))
            ordered_price = self.items[self.items[item_name].get_name('EN')].check_price()
        self.ordered_item = ordered_item
        self.ordered_price = ordered_price
        self.detailed_intent = 'deliver'

    def check_expected_condition(self, expected_entry):
        all_values = [item for sublist in self.AgentUtterances[-1]["expected_condition"].values() for item in sublist]
        return expected_entry in all_values

    def _generateResponseText(self, intent, entities, difficulty):
        # reset detailed_intent

        print(self.ordered_dish, self.ordered_appetizers, self.ordered_dessert, self.ordered_drink)

        if 'pronoun' in entities.keys():
            # get_menu
            print(entities['pronoun']['value'])
            GestureData = self.ActionHandler.getGestureBy(userID=str(self.user_id))
            print('\n\n')
            print(self.user_id, GestureData)
            print('\n\n')
            if GestureData:
                if self.OutputLanguage == 'CN':
                    pointed_value = self.ActionHandler.getGestureBy(userID=str(self.user_id))['chineseName']
                else:
                    pointed_value = self.ActionHandler.getGestureBy(userID=str(self.user_id))['englishName']
                if len(pointed_value) == 0:
                    if len(self.AgentUtterances) >= 2: 
                        self.AgentUtterances[-1]["expected_intent"] = self.AgentUtterances[-2]["expected_intent"]
                    return self._randomResponse("wrong_answer_order", difficulty)
                else:
                    actual_value = " ".join(pointed_value)
                    _, new_entities = self.WatsonHandler.recognizeIntentAndEntity(actual_value)
                    entities_ = entities.copy()
                    del entities_['pronoun']
                    entities_.update(new_entities)
                    return self._generateResponseText(intent, entities_, difficulty)
            else:
                if len(self.AgentUtterances) >= 2: 
                        self.AgentUtterances[-1]["expected_intent"] = self.AgentUtterances[-2]["expected_intent"]
                return self._randomResponse("wrong_answer_order", difficulty)

        if intent != 'ask_order':
            self.detailed_intent = None

        if len(self.AgentUtterances) > 0:
            if len(self.AgentUtterances[-1]["auto_fill"]) > 0:
                print(intent, self.AgentUtterances[-1]["auto_fill"][0]["slot"])

        # dialog logic
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

        elif intent == 'answer_ppl_count':
            text = self._randomResponse(intent, difficulty)
            # self.detailed_intent = 'show_menu'

        elif (intent == 'positive' and self.check_expected_condition('answer_seating')) or \
                intent == 'answer_seating':
            text = self._randomResponse("answer_seating", difficulty)
            self.UserIntent.append(intent)
            # self.detailed_intent = 'show_menu'

        elif intent == 'ask_order':
            self.detailed_intent = 'show_menu'
            text = self._randomResponseWithSlot(intent, difficulty)
            self.UserIntent.append(intent)

        elif intent == 'check_out':
            self.detailed_intent = 'hide_menu'
            if self.ordered_dessert or self.ordered_dish or self.ordered_drink or self.ordered_appetizers:
                text = self._randomResponse("check_out", difficulty)
            else:
                text = self._randomResponse("song_ke", difficulty)
            self.UserIntent.append(intent)

        elif intent == 'answer_taste_comment':
            text = self._randomResponse("positive_to_answer_taste_comment", difficulty)
            self.UserIntent.append(intent)

        # answer_order_drink_MISC
        elif intent == 'positive' and self.check_expected_condition('drink'):
            self.UserIntent.append(intent)
            if self.item_we_are_talking_EN:
                self.ordered_drink = True
                text = self._randomResponse("more_answer_order_drink", difficulty)
                self.add_to_notepad(entities, self.item_we_are_talking_EN)
            else:
                text = self._randomResponse("wrong_answer_order", difficulty)
                if len(self.AgentUtterances) >= 2: 
                        self.AgentUtterances[-1]["expected_intent"] = self.AgentUtterances[-2]["expected_intent"]
        elif intent == 'confirm_spec' and self.check_expected_condition('drink'):
            self.UserIntent.append(intent)
            self.ordered_drink = True
            text = self._randomResponse("more_answer_order_drink", difficulty)
            self.add_to_notepad(entities, self.item_we_are_talking_EN)

        # answer_order_appetizers_MISC
        elif intent == 'negative':
            self.UserIntent.append(intent)
            text = self._randomResponseWithSlot("ask_order", difficulty)

        # answer_order_dish_MISC
        elif intent == 'positive' and self.check_expected_condition('dish'):
            self.UserIntent.append(intent)
            print(self.recom_dish)
            if self.recom_dish:
                text = self._randomResponse("ask_taste_comment", difficulty)
                self.add_to_notepad(entities, self.recom_dish)
            else:
                text = self._randomResponse("wrong_answer_order", difficulty)
                if len(self.AgentUtterances) >= 2: 
                        self.AgentUtterances[-1]["expected_intent"] = self.AgentUtterances[-2]["expected_intent"]
        elif intent == 'negative' and self.check_expected_condition('dish'):
            self.UserIntent.append(intent)
            if self.ordered_dish:  # if ordered dish, ask taste
                text = self._randomResponse("ask_taste_comment", difficulty)
            else:  # if never ordered dish, just keep asking
                text = self._randomResponseWithSlot("ask_order", difficulty)

        # payment MISC
        elif (intent == 'confirm_check' or intent == 'positive') and self.check_expected_condition('check_out'):
            self.UserIntent.append(intent)
            text = self._randomResponse("give_payment", difficulty)
        elif intent == 'negative' and self.check_expected_condition('check_out'):
            self.UserIntent.append(intent)
            text = self._randomResponse("wrong_answer_order", difficulty)
            if len(self.AgentUtterances) >= 2: 
                        self.AgentUtterances[-1]["expected_intent"] = self.AgentUtterances[-2]["expected_intent"]
        elif intent == 'give_payment' and self.check_expected_condition('give_payment'):
            self.UserIntent.append(intent)
            # self.MoneySpent += float(self.calc_bill())
            text = self._randomResponse("song_ke", difficulty)

        # answer_orders
        elif intent == 'answer_order':
            self.UserIntent.append(intent)
            if 'drink' in entities.keys():
                ordered_drink = entities["drink"]["value"]
                self.item_we_are_talking_EN = ordered_drink
                self.item_we_are_talking_CN = self.items[ordered_drink].get_name("CN")
                if self.menu_has_it(ordered_drink):
                    if "spec" in entities.keys():
                        self.ordered_drink = True
                        text = self._randomResponse("more_answer_order_drink", difficulty)
                        self.add_to_notepad(entities, self.item_we_are_talking_EN)
                    else:
                        text = self._randomResponse("spec_answer_order_drink", difficulty)
                else:
                    text = self._randomResponse("menu_does_not_contain", difficulty)
            elif 'appetizer' in entities.keys():
                ordered_appetizer = entities["appetizer"]["value"]
                self.item_we_are_talking_EN = ordered_appetizer
                self.item_we_are_talking_CN = self.items[ordered_appetizer].get_name("CN")
                if self.menu_has_it(ordered_appetizer):
                    self.ordered_appetizers = True
                    self.add_to_notepad(entities, ordered_appetizer)
                    text = self._randomResponse('more_answer_order_appetizers', difficulty)
                else:
                    text = self._randomResponse("menu_does_not_contain", difficulty)
            elif 'dish' in entities.keys():
                print(self.AgentUtterances[-1]["auto_fill"][0]["slot"])
                ordered_dish = entities["dish"]["value"]
                self.item_we_are_talking_EN = ordered_dish
                self.item_we_are_talking_CN = self.items[ordered_dish].get_name("CN")
                if self.menu_has_it(ordered_dish):
                    self.ordered_dish = True
                    self.add_to_notepad(entities, ordered_dish)
                    text = self._randomResponse("answer_order_dish", difficulty)
            elif 'dessert' in entities.keys():
                ordered_dessert = entities["dessert"]["value"]
                self.item_we_are_talking_EN = ordered_dessert
                self.item_we_are_talking_CN = self.items[ordered_dessert].get_name("CN")
                if self.menu_has_it(ordered_dessert):
                    self.ordered_dessert = True
                    text = self._randomResponseWithSlot("ask_order", difficulty)
                    self.add_to_notepad(entities, ordered_dessert)
                else:
                    text = self._randomResponse("menu_does_not_contain", difficulty)


            else:
                text = self._randomResponse("wrong_answer_order", difficulty)
                if len(self.AgentUtterances) >= 2: 
                    self.AgentUtterances[-1]["expected_intent"] = self.AgentUtterances[-2]["expected_intent"]

        elif intent == 'goodbye':
            text = self._randomResponse("goodbye", difficulty)
            self.UserIntent.append(intent)
        elif intent == 'wrong_gesture':
            text = self._randomResponse("wrong_gesture", difficulty)
            self.UserIntent.append(intent)
        return text

    def _replacePlaceholder(self, text):
        if "@" not in text or '_' not in text:
            return text
        if self._ifContainChinese(text):
            lang = 'CN'
        else:
            lang = 'EN'
        # replace
        if '_@specs' in text and '_@drink_name_' in text and '_@recom_' in text:
            specs = self.items[self.item_we_are_talking_EN].get_specs("CN")
            recommendation = random.choice(specs)
            specs_text_CN = ', '
            specs_text_CN = specs_text_CN.join(self.items[self.item_we_are_talking_EN].get_specs("CN"))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@specs_", str(specs_text_CN))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@recom_", str(recommendation))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@drink_name_", str(self.items[self.item_we_are_talking_EN].get_name("CN")))
            specs_text_EN = ', '
            specs_text_EN = specs_text_EN.join(self.items[self.item_we_are_talking_EN].get_specs("EN"))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@specs_", str(specs_text_EN))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@recom_", str(self.items[self.item_we_are_talking_EN].translate_spec_from(recommendation, "CN")))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@drink_name_", str(self.item_we_are_talking_EN))

            if lang == 'CN':
                text = text.replace('_@specs_', specs_text_CN)
                text = text.replace('_@recom_', recommendation)

            else:
                text = text.replace('_@specs_', specs_text_EN)
                text = text.replace('_@recom_', str(self.items[self.item_we_are_talking_EN].translate_spec_from(recommendation, lang)))
            text = text.replace('_@drink_name_', self.items[self.item_we_are_talking_EN].get_name(lang))

        elif '_@recom_' in text:
            recommendation_pool = []
            for k in self.items.keys():
                if self.items[k].get_cat('EN').lower() == 'dish' and k != self.item_we_are_talking_EN:
                    recommendation_pool.append(k)
            recom = random.choice(recommendation_pool)
            self.recom_dish = recom
            text = text.replace('_@recom_', self.items[recom].get_name(lang))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@recom_", str(self.special_dish.get_name('CN')))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@recom_", str(self.special_dish.get_name('EN')))

        return text

    def takeActions(self,userInput, agentResponse, debugInfo, gameProgressProfile):
        super().takeActions(userInput, agentResponse, debugInfo, gameProgressProfile)
        if debugInfo['detailed_intent'] == 'show_menu':
            print('show menu \n\n\n')
            self.apiHandler.showMenu(agentResponse['IP'], 1, [{"id": 1, "text": "abc", "cost": "100"}, {"id": 2, "text": "abc", "cost": "10"}])
            self.apiHandler.showNotepad(agentResponse['IP'], 1)
        elif debugInfo['detailed_intent'] == 'hide_menu':
            self.apiHandler.hideMenu(agentResponse['IP'], 1)
        elif debugInfo['detailed_intent'] == 'deliver':
            if debugInfo['paras']['ordered_item']:
                self.apiHandler.addItem2Notepad(agentResponse['IP'], 1, [
                    {
                        "id": 0,
                        "text": debugInfo['paras']['ordered_item'],
                        "cost": '¥' + str(debugInfo['paras']['ordered_price'])
                    }
                ])
                self.MoneySpent += float(debugInfo['paras']['ordered_price'])
        elif agentResponse['user_intent'] == 'give_payment':
            self.apiHandler.hideNotepad(agentResponse['IP'], 1)
            message = self.apiHandler.updateResponseForCreditBalance(userInput, agentResponse)
            print("MONEY SPENT: aft_spent", message['balance'])
            agentResponse['paras']['balance'] = message['balance']
            if len(message['EN']) != 0:
                agentResponse['text'] = message['CN'] if self._ifContainChinese(agentResponse['text']) else message['EN']
            else:
                print(gameProgressProfile['lisa_on_street'].getTaskProcess('street'))
                self.apiHandler.checkOffQuest(agentResponse['IP'], 'street',
                                              gameProgressProfile['lisa_on_street'].getTaskProcess('street'))
