from conversation import Conversation
import json
import math
import random
import os
import word2number.w2n as w2n
from dependencies.apiWrapper import APIWrapper


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

    def translate_spec_to(self, spec, lang):
        EN_specs = self.specs["EN"]
        CN_specs = self.specs["CN"]
        # for cat in self.specs.values():
        #     for spec_ in cat['CN']:
        #         CN_specs.append(spec_)
        #     for spec_ in cat['EN']:
        #         EN_specs.append(spec_)
        if lang == 'CN':
            return CN_specs[EN_specs.index(spec)]
        else:
            return EN_specs[CN_specs.index(spec)]

    def is_special(self):
        return self.special == "1"


class RestaurantConversation(Conversation):
    def __init__(self, username, userId, agent, cnHelper=None, enHelper=None, gameProgress=None, actionHandler=None):
        super().__init__(username, userId, agent, cnHelper=cnHelper, enHelper=enHelper, gameProgress=gameProgress, actionHandler=actionHandler)
        self.username = userId
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

        # flags
        self.checked_spec = False
        self.checked_amount = False
        self.checked_item = False
        self.asking_drink = False
        self.asking_dish = False
        self.asking_dessert = False
        self.asking_appetizers = False
        self.asking_special_dish = False
        self.confirming_check_out = False
        self.made_recommendation = False
        self.confirm_drink_order_finish = False
        self.ordered_anything = False
        self.ordered_dish = False

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


    def _generateResponseText(self, intent, entities, difficulty):
        self.detailed_intent = None
        self.ordered_item = None
        self.ordered_price = None

        text = ''
        if intent == 'skip':
            text = self._simulateUserInput()
        elif intent == 'hint':
            text = self._generateHint()
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
        elif intent == 'hello':
            text = self._randomResponse(intent, difficulty)
            self.UserIntent.append(intent)
        elif intent == 'answer_ppl_count':
            num_of_ppl = entities['number']['value']
            num_of_ppl = int(w2n.word_to_num(num_of_ppl))
            if num_of_ppl > 1:
                text = self._randomResponse("answer_ppl_count_multi", difficulty)
            else:
                text = self._randomResponse("answer_ppl_count_single", difficulty)
            if difficulty == 1:
                self.asking_drink = True
                self.detailed_intent = 'show_menu'
            self.UserIntent.append(intent)
        elif intent == 'answer_seating':
            text = self._randomResponse(intent, difficulty)
            self.asking_drink = True
            self.UserIntent.append(intent)
            self.detailed_intent = 'show_menu'
        elif intent == 'answer_order':
            if (self.asking_appetizers or self.asking_dessert or self.asking_dish or self.asking_drink or \
                    self.asking_special_dish) and 'pronoun' in entities.keys():
                return
            elif self.asking_drink:
                if "spec" in entities.keys() and "drink" in entities.keys():
                    self.ordered_anything = True
                    ordered_drink = entities["drink"]["value"]
                    self.item_we_are_talking_EN = ordered_drink
                    self.item_we_are_talking_CN = self.items[ordered_drink].get_name("CN")
                    text = self._randomResponse("deliver_drink", difficulty)
                    text += '\n'
                    text += self._randomResponse("confirm_drink_order_finish", difficulty)
                    if difficulty >= 5:
                        self.asking_appetizers = True
                        self.asking_drink = False
                    else:
                        self.confirm_drink_order_finish = True

                    if "number" in entities.keys():
                        ordered_item = str(self.items[ordered_drink].get_name('CN')) + 'x' + str(w2n.word_to_num(
                            entities["number"]["value "]))
                        ordered_price = float(str(self.items[self.items[ordered_drink].get_name('EN')].check_price()) * w2n.word_to_num(entities["number"]["value"]))
                    else:
                        ordered_item = str(self.items[ordered_drink].get_name('CN'))
                        ordered_price = self.items[self.items[ordered_drink].get_name('EN')].check_price()
                    self.ordered_item = ordered_item
                    self.ordered_price = ordered_price
                    self.detailed_intent = 'deliver'

                    if "number" in entities.keys():
                        num = entities["number"]["value"]
                        num = w2n.word_to_num(num)
                        for n in range(num):
                            self.order_history.append([self.items[ordered_drink].get_name('EN')])
                    else:
                        self.order_history.append([self.items[ordered_drink].get_name('EN')])
                elif "drink" in entities.keys():
                    self.ordered_anything = True
                    ordered_drink = entities["drink"]["value"]
                    self.item_we_are_talking_EN = ordered_drink
                    self.item_we_are_talking_CN = self.items[ordered_drink].get_name("CN")
                    specs = self.items[ordered_drink].get_specs("CN")
                    if self.menu_has_it(ordered_drink):
                        if len(specs) <= 1:
                            text = self._randomResponse("deliver_drink", difficulty)
                            text += '\n'
                            text += self._randomResponse("confirm_drink_order_finish", difficulty)
                            if difficulty >= 5:
                                self.asking_appetizers = True
                                self.asking_drink = False
                            else:
                                self.confirm_drink_order_finish = True

                            if "number" in entities.keys():
                                ordered_item = str(self.items[ordered_drink].get_name('CN')) + 'x' + str(
                                    w2n.word_to_num(
                                        entities["number"]["value"]))
                                ordered_price = str(self.items[self.items[ordered_drink].get_name(
                                    'EN')].check_price() * w2n.word_to_num(entities["number"]["value"]))
                            else:
                                ordered_item = str(self.items[ordered_drink].get_name('CN'))
                                ordered_price = self.items[self.items[ordered_drink].get_name('EN')].check_price()
                            self.ordered_item = ordered_item
                            self.ordered_price = ordered_price
                            self.detailed_intent = 'deliver'

                            if "number" in entities.keys():
                                num = entities["number"]["value"]
                                num = w2n.word_to_num(num)
                                for n in range(num):
                                    self.order_history.append([self.items[ordered_drink].get_name('EN')])
                            else:
                                self.order_history.append([self.items[ordered_drink].get_name('EN')])
                        else:
                            recommendation = random.choice(specs)
                            text = self._randomResponse("tell_spec_recommend", difficulty)
                            specs_text_CN = ', '
                            specs_text_CN = specs_text_CN.join(self.items[ordered_drink].get_specs("CN"))
                            text = text.replace('_@specs_', specs_text_CN)
                            text = text.replace('_@drink_name_', self.items[ordered_drink].get_name("CN"))
                            text = text.replace('_@recom_', recommendation)
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@specs_",
                                                                                                    str(specs_text_CN))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@recom_",
                                                                                                    str(recommendation))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@drink_name_",
                                                                                                    str(self.items[ordered_drink].get_name("CN")))
                            specs_text_EN = ', '
                            specs_text_EN = specs_text_EN.join(self.items[ordered_drink].get_specs("EN"))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@specs_",
                                                                                                    str(specs_text_EN))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@recom_",
                                                                                                    str(self.items[ordered_drink].translate_spec_to(recommendation, "EN")))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@drink_name_",
                                                                                                    str(ordered_drink))
                    else:
                        text = self._randomResponse("menu_does_not_contain", difficulty)
                else:
                    text = self._randomResponse("wrong_category_reply", difficulty)
                self.UserIntent.append(intent)
            elif self.asking_dish:
                if "spec" and "dish" in entities.keys() or "dish" in entities.keys():
                    self.ordered_anything = True
                    self.ordered_dish = True
                    ordered_dish = entities["dish"]["value"]
                    self.item_we_are_talking_EN = ordered_dish
                    self.item_we_are_talking_CN = self.items[ordered_dish].get_name("CN")
                    if self.menu_has_it(ordered_dish):
                        if difficulty == 1:
                            text = self._randomResponse("ask_for_more_orders", difficulty)
                        elif difficulty >= 5 and not self.made_recommendation and self.special_dish.get_name("EN") != ordered_dish:
                            text = self._randomResponse("recommend_dish", difficulty)
                            self.made_recommendation = True
                            self.asking_special_dish = True
                            text = text.replace('_@recom_', self.special_dish.get_name('CN'))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@recom_", str(
                                self.special_dish.get_name('CN')))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@recom_", str(
                                self.special_dish.get_name('EN')))
                        elif difficulty >= 5 and self.made_recommendation:
                            text = self._randomResponse("ask_for_more_orders", difficulty)
                            self.asking_special_dish = False
                        elif difficulty >= 5 and self.special_dish.get_name("EN") == ordered_dish:
                            text = self._randomResponse("ask_for_more_orders", difficulty)
                            self.asking_special_dish = False

                        if "number" in entities.keys():
                            ordered_item = str(self.items[ordered_dish].get_name('CN')) + 'x' + str(
                                w2n.word_to_num(
                                    entities["number"]["value"]))
                            ordered_price = str(self.items[self.items[ordered_dish].get_name(
                                'EN')].check_price() * w2n.word_to_num(entities["number"]["value"]))
                        else:
                            ordered_item = str(self.items[ordered_dish].get_name('CN'))
                            ordered_price = self.items[self.items[ordered_dish].get_name('EN')].check_price()
                        self.ordered_item = ordered_item
                        self.ordered_price = ordered_price
                        self.detailed_intent = 'deliver'

                        if "number" in entities.keys():
                            num = entities["number"]["value"]
                            num = w2n.word_to_num(num)
                            for n in range(num):
                                if isinstance(ordered_dish, list):
                                    self.order_history.append([self.items[ordered_dish].get_name('EN')])
                                elif isinstance(ordered_dish, str):
                                    self.order_history.append([self.items[ordered_dish].get_name('EN')])
                        else:
                            if isinstance(ordered_dish, list):
                                self.order_history.append([self.items[ordered_dish].get_name('EN')])
                            elif isinstance(ordered_dish, str):
                                self.order_history.append([self.items[ordered_dish].get_name('EN')])
                    else:
                        text = self._randomResponse("menu_does_not_contain", difficulty)
                else:
                    text = self._randomResponse("wrong_category_reply", difficulty)
                self.UserIntent.append(intent)
            elif self.asking_dessert:
                if "spec" in entities.keys() and "dessert" in entities.keys() or "dessert" in entities.keys():
                    self.ordered_anything = True
                    self.detailed_intent = 'hide_menu'
                    ordered_dessert = entities["dessert"]["value"]
                    self.item_we_are_talking_EN = ordered_dessert
                    self.item_we_are_talking_CN = self.items[ordered_dessert].get_name("CN")
                    if self.menu_has_it(ordered_dessert):
                        text = self._randomResponse("check_out", difficulty)
                        self.confirming_check_out = True
                        self.asking_dessert = False

                        if "number" in entities.keys():
                            ordered_item = str(self.items[ordered_dessert].get_name('CN')) + 'x' + str(
                                w2n.word_to_num(
                                    entities["number"]["value"]))
                            ordered_price = str(self.items[self.items[ordered_dessert].get_name(
                                'EN')].check_price() * w2n.word_to_num(entities["number"]["value"]))
                        else:
                            ordered_item = str(self.items[ordered_dessert].get_name('CN'))
                            ordered_price = self.items[self.items[ordered_dessert].get_name('EN')].check_price()
                        self.ordered_item = ordered_item
                        self.ordered_price = ordered_price
                        self.detailed_intent = 'deliver'

                        if "number" in entities.keys():
                            num = entities["number"]["value"]
                            num = w2n.word_to_num(num)
                            for n in range(num):
                                self.order_history.append([self.items[ordered_dessert].get_name('EN')])
                        else:
                            self.order_history.append([self.items[ordered_dessert].get_name('EN')])
                    else:
                        text = self._randomResponse("menu_does_not_contain", difficulty)
                else:
                    text = self._randomResponse("wrong_category_reply", difficulty)
                self.UserIntent.append(intent)
            elif self.asking_appetizers:
                if "spec" in entities.keys() and "appetizer" in entities.keys() or "appetizer" in entities.keys():
                    self.ordered_anything = True
                    ordered_appetizer = entities["appetizer"]["value"]
                    self.item_we_are_talking_EN = ordered_appetizer
                    self.item_we_are_talking_CN = self.items[ordered_appetizer].get_name("CN")
                    if self.menu_has_it(ordered_appetizer):
                        text = self._randomResponse("ask_for_more_orders", difficulty)

                        if "number" in entities.keys():
                            ordered_item = str(self.items[ordered_appetizer].get_name('CN')) + 'x' + str(
                                w2n.word_to_num(
                                    entities["number"]["value"]))
                            ordered_price = str(self.items[self.items[ordered_appetizer].get_name(
                                'EN')].check_price() * w2n.word_to_num(entities["number"]["value"]))
                        else:
                            ordered_item = str(self.items[ordered_appetizer].get_name('CN'))
                            ordered_price = self.items[self.items[ordered_appetizer].get_name('EN')].check_price()
                        self.ordered_item = ordered_item
                        self.ordered_price = ordered_price
                        self.detailed_intent = 'deliver'


                        if "number" in entities.keys():
                            num = entities["number"]["value"]
                            num = w2n.word_to_num(num)
                            for n in range(num):
                                self.order_history.append([self.items[ordered_appetizer].get_name('EN')])
                        else:
                            self.order_history.append([self.items[ordered_appetizer].get_name('EN')])
                    else:
                        text = self._randomResponse("menu_does_not_contain", difficulty)
                else:
                    text = self._randomResponse("wrong_category_reply", difficulty)
                self.UserIntent.append(intent)
        # elif intent == 'dish_delivered':
        #     text = self._randomResponse("ask_taste", difficulty)
        #     self.UserIntent.append(intent)
        elif intent == 'answer_taste_comment':
            text = self._randomResponse("ask_dessert", difficulty)
            self.asking_dessert = True
            self.UserIntent.append(intent)
        elif intent == "positive" and self.confirm_drink_order_finish:
            self.confirm_drink_order_finish = False
            if difficulty >= 5:
                self.asking_appetizers = True
                self.asking_drink = False
                text = self._randomResponse("ask_appetizers", difficulty)
            else:
                self.asking_dish = True
                self.asking_drink = False
                text = self._randomResponse("ask_main_dish", difficulty)
            self.UserIntent.append(intent)
        elif intent == "positive" and self.asking_special_dish:
            self.asking_special_dish = False

            if "number" in entities.keys():
                ordered_item = str(self.special_dish.get_name('CN')) + 'x' + str(
                    w2n.word_to_num(
                        entities["number"]["value"]))
                ordered_price = str(self.items[self.special_dish.get_name(
                    'EN')].check_price() * w2n.word_to_num(entities["number"]["value"]))
            else:
                ordered_item = str(self.special_dish.get_name('CN'))
                ordered_price = self.items[self.special_dish.get_name('EN')].check_price()
            self.ordered_item = ordered_item
            self.ordered_price = ordered_price
            self.detailed_intent = 'deliver'

            if "number" in entities.keys():
                num = entities["number"]["value"]
                num = w2n.word_to_num(num)
                for n in range(num):
                    self.order_history.append([self.special_dish.get_name('EN')])
            else:
                self.order_history.append([self.special_dish.get_name('EN')])
            self.asking_dish = True
            text = self._randomResponse("ask_for_more_orders", difficulty)
            self.UserIntent.append(intent)
        elif (intent == "positive" or intent == 'confirm_spec') and self.asking_drink:
            self.asking_drink = False
            if "number" in entities.keys():
                ordered_item = str(self.items[self.item_we_are_talking_EN].get_name('CN')) + 'x' + str(
                    w2n.word_to_num(
                        entities["number"]["value"]))
                ordered_price = str(self.items[self.items[self.item_we_are_talking_EN].get_name(
                    'EN')].check_price() * w2n.word_to_num(entities["number"]["value"]))
            else:
                ordered_item = str(self.items[self.item_we_are_talking_EN].get_name('CN'))
                ordered_price = self.items[self.items[self.item_we_are_talking_EN].get_name('EN')].check_price()
            self.ordered_item = ordered_item
            self.ordered_price = ordered_price
            self.detailed_intent = 'deliver'

            if "number" in entities.keys():
                num = entities["number"]["value"]
                num = w2n.word_to_num(num)
                for n in range(num):
                    self.order_history.append([self.item_we_are_talking_EN])
            else:
                self.order_history.append([self.item_we_are_talking_EN])
            if difficulty < 5:
                text = self._randomResponse("ask_dish", difficulty)
                self.asking_dish = True
            else:
                text = self._randomResponse("ask_appetizers", difficulty)
                self.asking_appetizers = True
            # self.asking_dish = True
            self.UserIntent.append(intent)
        elif intent == "negative" and self.asking_special_dish:
            self.asking_special_dish = False
            self.asking_dish = True
            text = self._randomResponse("ask_for_more_orders", difficulty)
            self.UserIntent.append(intent)
        elif intent == 'positive' and self.asking_dish:
            text = self._randomResponse("ask_for_more_orders", difficulty)
            self.UserIntent.append(intent)
        elif intent == 'negative' and self.asking_dish:
            self.asking_dish = False
            if self.ordered_anything:
                text = self._randomResponse("deliver", difficulty)
                if self.ordered_dish:
                    text += self._randomResponse("ask_taste", difficulty)
                    self.detailed_intent = "deliver_dish"
                else:
                    text += self._randomResponse("ask_dessert", difficulty)
                    self.asking_dessert = True
            else:
                text = self._randomResponse("ask_dessert", difficulty)
                self.asking_dessert = True
            self.UserIntent.append(intent)
        elif intent == 'negative' and self.asking_appetizers:
            self.asking_appetizers = False
            self.asking_dish = True
            text = self._randomResponse("ask_main_dish", difficulty)
            self.UserIntent.append(intent)
        elif intent == 'negative' and self.asking_drink:
            self.asking_drink = False
            if difficulty >= 5:
                self.asking_appetizers = True
                text = self._randomResponse("ask_appetizers", difficulty)
            else:
                self.asking_dish = True
                text = self._randomResponse("ask_dish", difficulty)
        elif intent == 'negative' and self.asking_dessert:
            self.asking_dessert = False
            self.detailed_intent = 'hide_menu'
            if self.ordered_anything:
                text = self._randomResponse("check_out", difficulty)
                self.confirming_check_out = True
            else:
                text = self._randomResponse("song_ke", difficulty)
        elif intent == 'positive' and self.confirming_check_out:
            self.confirming_check_out = False
            text = self._randomResponse("ask_payment_method", difficulty)
            self.UserIntent.append(intent)
        elif intent == 'negative' and self.confirming_check_out:
            self.UserIntent.append(intent)
        elif intent == 'confirm_check':
            if difficulty >= 5:
                text = self._randomResponse("show_check", difficulty)
                self.confirming_check_out = True
            else:
                text = self._randomResponse("show_total_price", difficulty)
                text = text.replace('_@price_', self.calc_bill())
                self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@price_", str(
                    self.calc_bill()))
                self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@recom_", str(
                    self.calc_bill()))
            self.UserIntent.append(intent)
        elif intent == 'give_payment':
            self.MoneySpent += float(self.calc_bill())
            text = self._randomResponse("song_ke", difficulty)
            print(self.order_history)
            print(self.MoneySpent)
            self.UserIntent.append(intent)
        elif intent == 'goodbye':
            text = self._randomResponse("goodbye", difficulty)
            self.UserIntent.append(intent)
        elif intent == 'wrong_gesture':
            text = self._randomResponse("wrong_gesture", difficulty)
            self.UserIntent.append(intent)
        return text



    # menu sections for drink dish.....
