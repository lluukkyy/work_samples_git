"""
@author: Zhicheng(Stark) Guo
@email: guoz6@rpi.edu
"""


from conversation import Conversation
from dependencies import commHandler, systemHandler
import json
import math
import random
import os
import word2number.w2n as w2n


class Items:
    def __init__(self, item_dict):
        """
        "Item_name": "Cake",
        "Initial_price": "9",
        "Final_price": "2",
        "Yield_price_range": "1, 1.5",
        "In_stock": "11",
        "Attrib":{
            "size": ["Big", "Small"],
            "color": ["Red", "Green"]
        },
        "Unit": ["ge"]
        """
        self.item_name = item_dict["Item_name"]  # String: String
        self.initial_price = float(item_dict["Initial_price"])  # float
        self.final_price = float(item_dict["Final_price"])  # float
        self.in_stock = int(item_dict["In_stock"])  # int
        self.specs = item_dict["Spec"]  # String: String: [String]
        self.units = item_dict["Unit"]  # [String]
        self.payment_methods = item_dict["Payment_method"]  # String:[String]
        self.current_price = self.initial_price  # float
        self.yield_counter = 0  # int
        self.max_free_amount = item_dict["Max_free_amount"]  # int
        self.max_batch_sale_amount = item_dict["Max_batch_sale_amount"]  # int
        self.free_amount_offset = 0
        self.batch_sale_amount = 0
        self.buying_amount = 0

    def set_buying_amount(self, amt):
        self.buying_amount = amt

    def set_free_amount(self, amt):
        self.free_amount_offset = amt

    def get_name(self, lang):
        return self.item_name[lang]

    def check_current_price(self):
        return self.current_price

    def check_initial_price(self):
        return self.initial_price

    def yield_price(self, use_rate):
        new_current_price = random.randint(int(self.final_price), int(self.current_price) - 1)
        price_discount = self.current_price - new_current_price
        CN_rate = round(float(new_current_price) / float(self.current_price), 2) * 100
        EN_rate = 1 - CN_rate
        ret_CN_rate = str(CN_rate)
        ret_EN_rate = str(EN_rate)
        if min(self.in_stock - 1, int(self.max_batch_sale_amount) + 1) - 2 > 0:
            batch_sale_amount = random.randint(2, min(self.in_stock - 1, int(self.max_batch_sale_amount) + 1))
            conditioned_price0 = self.current_price * batch_sale_amount
            conditioned_price1 = price_discount * batch_sale_amount
            if min(self.in_stock - batch_sale_amount, int(self.max_free_amount) + 1) - 1 > 0:
                free_amount = random.randint(1, min(self.in_stock - batch_sale_amount, int(self.max_free_amount) + 1))
            else:
                free_amount = 0
        else:
            batch_sale_amount = 0
            free_amount = 0
        if use_rate:
            self.current_price = self.current_price * CN_rate / 100
            if CN_rate % 10 == 0:
                ret_CN_rate = ret_CN_rate[0]
            if EN_rate % 10 == 0:
                ret_EN_rate = ret_EN_rate[0]
        else:
            self.current_price = new_current_price
        return [self.current_price, price_discount, batch_sale_amount, free_amount, ret_CN_rate, ret_EN_rate, conditioned_price0, conditioned_price1]

    def check_yield(self):
        return self.current_price - 1 > self.final_price

    def check_stock(self):
        return self.in_stock

    def check_unit(self, player_unit):
        return player_unit in self.units["CN"]

    def sold_update(self):
        amt = self.buying_amount
        if amt >= self.batch_sale_amount:
            self.in_stock -= amt
            self.in_stock -= self.free_amount_offset
        else:
            self.in_stock -= amt
        return True

    def get_unit(self, lang):
        return random.choice(self.units[lang])

    def check_spec(self, spec_):
        return spec_ in self.specs["EN"]

    def get_specs(self, lang):
        return self.specs[lang]

    def get_payment_methods(self, lang):
        return self.payment_methods[lang]

    def translate_spec_to(self, spec, lang):
        EN_specs = []
        CN_specs = []
        for cat in self.specs.values():
            for spec_ in cat['CN']:
                CN_specs.append(spec_)
            for spec_ in cat['EN']:
                EN_specs.append(spec_)
        if lang == 'EN':
            return CN_specs[EN_specs.index(spec)]
        else:
            return EN_specs[CN_specs.index(spec)]

    def get_buying_amt(self):
        return self.buying_amount


class VendorConversation(Conversation):
    def __init__(self, username, userId, agent, menu_name='drink', cnHelper=None, enHelper=None, gameProgress=None, actionHandler=None):
        super().__init__(username, userId, agent, cnHelper=cnHelper, enHelper=enHelper, gameProgress=gameProgress, actionHandler=actionHandler)
        self.items = dict()
        self.V2Folder = os.path.dirname(os.path.abspath(__file__))
        self.MenuFile = os.path.join(self.V2Folder, 'resources/VendorMenus/')
        self.MenuFile = self.MenuFile + '{}.json'.format(menu_name)

        self.CN_item_lst = []
        self.EN_item_lst = []
        with open(self.MenuFile,  encoding='utf-8') as f:
            item_lists = json.load(f)
            for item_dict in item_lists:
                a_item = Items(item_dict)
                self.items[a_item.get_name("EN")] = a_item
                self.CN_item_lst.append(a_item.get_name('CN'))
                self.EN_item_lst.append(a_item.get_name('EN'))

        self.item_we_are_talking_EN = ''
        self.item_we_are_talking_CN = ''

        self.checked_spec = False
        self.checked_amount = False
        self.checked_item = False

        self.discount_active = False
        self.discount_prerequests = {'batch_amt': None,
                                     'cond_price0': None,
                                     'cond_price1': None
                                     }

        system = systemHandler.SystemHandler()
        if not system.IsReady:
            pass
        self.sender = commHandler.commHandler(system.settings['server_ip'])

    def reset_discount_prerequests(self):
        self.discount_prerequests = {'batch_amt': None,
                                     'cond_price0': None,
                                     'cond_price1': None
                                     }

    def prepare_for_next_trade(self):
        print('\nprepare_for_next_trade(): {} \n'.format(self.item_we_are_talking_EN))
        self.detailed_intent = 'deliver'
        self.GameLogicHandler.updateTaskProcess(self.item_we_are_talking_EN)
        self.MoneySpent = self.calc_bill()
        self.checked_amount = False
        self.checked_item = False
        self.checked_spec = False
        self.item_we_are_talking_EN = ''
        self.item_we_are_talking_CN = ''

    def calc_bill(self):
        if self.discount_active:
            if self.discount_prerequests['batch_amt']:
                if self.items[self.item_we_are_talking_EN].get_buying_amt() >= self.discount_prerequests['batch_amt']:
                    return self.items[self.item_we_are_talking_EN].check_initial_price() * \
                            self.items[self.item_we_are_talking_EN].get_buying_amt()
                else:
                    return self.items[self.item_we_are_talking_EN].check_current_price() * \
                           self.items[self.item_we_are_talking_EN].get_buying_amt()
            elif self.discount_prerequests['cond_price0'] and self.discount_prerequests['cond_price1']:
                if self.items[self.item_we_are_talking_EN].check_initial_price() * \
                           self.items[self.item_we_are_talking_EN].get_buying_amt() >= self.discount_prerequests['cond_price0']:
                    return self.items[self.item_we_are_talking_EN].check_initial_price() * \
                           self.items[self.item_we_are_talking_EN].get_buying_amt() - self.discount_prerequests['cond_price1']
                else:
                    return self.items[self.item_we_are_talking_EN].check_initial_price() * \
                           self.items[self.item_we_are_talking_EN].get_buying_amt()
            else:
                return self.items[self.item_we_are_talking_EN].check_current_price() * \
                       self.items[self.item_we_are_talking_EN].get_buying_amt()
        else:
            return self.items[self.item_we_are_talking_EN].check_initial_price() * \
                   self.items[self.item_we_are_talking_EN].get_buying_amt()

    def discount_operations(self, item_name, use_rate):
        self.reset_discount_prerequests()
        self.discount_active = True
        current_price, price_discount, batch_sale_amount, free_amount, CN_rate, EN_rate \
            , conditioned_price0, conditioned_price1 = self.items[item_name].yield_price(use_rate=use_rate)
        return current_price, price_discount, batch_sale_amount, free_amount, CN_rate, EN_rate \
            , conditioned_price0, conditioned_price1

    # preventing trade while no context
    def avoid_lunatic(self):
        return self.item_we_are_talking_CN.__len__() == 0 or self.item_we_are_talking_EN.__len__() == 0

    def buy_check(self):
        return self.checked_item and self.checked_amount and self.checked_spec

    def vendor_has_it(self, item_name_):
        print(self.items.keys())
        if item_name_ in self.items.keys():
            stock_amt = self.items[item_name_].check_stock()
            if stock_amt > 0:
                in_stock = True
            else:
                in_stock = False
        else:
            in_stock = False
        return in_stock

    def _generateResponseText(self, intent, entities, difficulty):
        self.detailed_intent = None
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
                    self.UserIntent.append(last_intent)
                else:
                    text = self._getAllRepeatText()
                self.OutputLanguage = old_language
            else:
                text = self._randomResponse(intent, difficulty)
                self.UserIntent.append(intent)
        elif intent == 'hello':
            text1 = self._randomResponse(intent, difficulty)
            self.UserIntent.append(intent)
            if difficulty == 5:
                text = self._randomResponse("hello", difficulty)
                new_intent = 'ask_stocks'
                items_CN = ', '
                items_CN = items_CN.join(self.CN_item_lst)
                items_EN = ', '
                items_EN = items_EN.join(self.EN_item_lst)
                text += self._randomResponse(new_intent, difficulty)
                if self.OutputLanguage == 'CN':
                    text = text.replace('_@items_', items_CN)
                else:
                    text = text.replace('_@items_', items_EN)
                self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@items_", items_CN)
                self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@items_", items_EN)
            else:
                text = text1
            self.UserIntent.append(intent)
        elif intent == 'ask_stocks':
            items_CN = ', '
            items_CN = items_CN.join(self.CN_item_lst)
            items_EN = ', '
            items_EN = items_EN.join(self.EN_item_lst)
            text = self._randomResponse(intent, difficulty)
            if self.OutputLanguage == 'CN':
                text = text.replace('_@items_', items_CN)
            else:
                text = text.replace('_@items_', items_EN)
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@items_", items_CN)
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@items_", items_EN)
            self.UserIntent.append(intent)
        elif intent == 'ask_discount':
            if not self.avoid_lunatic():
                item_name = self.item_we_are_talking_EN
                if self.items[item_name].check_yield():
                    new_intent = "positive_to_ask_discount"
                    text = self._randomResponse(new_intent, difficulty)
                    if '_@discount_price_' in text and '_@current_price_' in text:
                        current_price, price_discount, batch_sale_amount, free_amount, CN_rate, EN_rate \
                            , conditioned_price0, conditioned_price1 = self.discount_operations(item_name, False)
                        text = text.replace('_@discount_price_', str(int(price_discount)))
                        text = text.replace('_@current_price_', str(int(current_price)))
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@discount_price_",
                                                                                                str(price_discount))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@discount_price_",
                                                                                                str(price_discount))
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@current_price_",
                                                                                                str(current_price))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@current_price_",
                                                                                                str(current_price))
                    elif '_@batch_sale_amount_' in text and '_@current_price_' in text:
                        current_price, price_discount, batch_sale_amount, free_amount, CN_rate, EN_rate \
                            , conditioned_price0, conditioned_price1 = self.discount_operations(item_name, False)
                        self.discount_prerequests['batch_amt'] = int(batch_sale_amount)
                        text = text.replace('_@batch_sale_amount_', str(int(batch_sale_amount)))
                        text = text.replace('_@current_price_', str(int(current_price) * batch_sale_amount))
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@batch_sale_amount_",
                                                                                                str(int(batch_sale_amount)))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@batch_sale_amount_",
                                                                                                str(int(batch_sale_amount)))
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@current_price_",
                                                                                                str(current_price * batch_sale_amount))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@current_price_",
                                                                                                str(current_price * batch_sale_amount))
                    elif '_@batch_sale_amount_' in text and '_@free_amount_' in text:
                        current_price, price_discount, batch_sale_amount, free_amount, CN_rate, EN_rate \
                            , conditioned_price0, conditioned_price1 = self.discount_operations(item_name, False)
                        self.discount_prerequests['batch_amt'] = int(batch_sale_amount)
                        if batch_sale_amount * free_amount != 0:
                            self.items[item_name].set_free_amount(free_amount)
                            text = text.replace('_@batch_sale_amount_', str(int(batch_sale_amount)))
                            text = text.replace('_@free_amount_', str(int(free_amount)))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@batch_sale_amount_",
                                                                                                    str(int(batch_sale_amount)))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@batch_sale_amount_",
                                                                                                    str(int(batch_sale_amount)))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@free_amount_",
                                                                                                    str(int(free_amount)))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@free_amount_",
                                                                                                    str(int(free_amount)))
                        else:
                            new_intent = "default_positive_to_ask_discount"
                            text = self._randomResponse(new_intent, difficulty)
                            current_price, price_discount, batch_sale_amount, free_amount, CN_rate, EN_rate \
                                , conditioned_price0, conditioned_price1 = self.items[item_name].yield_price(use_rate=False)
                            self.discount_active = True
                            text = text.replace('_@discount_price_', str(int(price_discount)))
                            text = text.replace('_@current_price_', str(int(current_price)))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@discount_price_",
                                                                                                    str(int(price_discount)))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@discount_price_",
                                                                                                    str(int(price_discount)))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@current_price_",
                                                                                                    str(int(current_price)))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@current_price_",
                                                                                                    str(int(current_price)))
                    elif '_@discount_rate_' in text:
                        current_price, price_discount, batch_sale_amount, free_amount, CN_rate, EN_rate \
                            , conditioned_price0, conditioned_price1 = self.discount_operations(item_name, True)
                        if self.OutputLanguage == 'CN':
                            text = text.replace('_@discount_rate_', str(int(float(CN_rate))))
                        else:
                            text = text.replace('_@discount_rate_', str(int(float(EN_rate))))
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@discount_rate_",
                                                                                                str(int(float(CN_rate))))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@discount_rate_",
                                                                                                str(int(float(EN_rate))))
                    elif '_@current_price_' in text:
                        current_price, price_discount, batch_sale_amount, free_amount, CN_rate, EN_rate \
                            , conditioned_price0, conditioned_price1 = self.discount_operations(item_name, True)
                        text = text.replace('_@current_price_', str(int(current_price)))
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@current_price_",
                                                                                                str(int(current_price)))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@current_price_",
                                                                                                str(int(current_price)))
                    elif '_@cond0_' in text and '_@cond1_' in text:
                        current_price, price_discount, batch_sale_amount, free_amount, CN_rate, EN_rate \
                            , conditioned_price0, conditioned_price1 = self.discount_operations(item_name, False)
                        self.discount_prerequests['cond_price0'] = conditioned_price0
                        self.discount_prerequests['cond_price1'] = conditioned_price1
                        if batch_sale_amount * free_amount != 0:
                            self.items[item_name]. set_free_amount(free_amount)
                            text = text.replace('_@cond0_', str(int(conditioned_price0)))
                            text = text.replace('_@cond1_', str(int(conditioned_price1)))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@cond0_",
                                                                                                    str(int(conditioned_price0)))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@cond0_",
                                                                                                    str(int(conditioned_price0)))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@cond1_",
                                                                                                    str(int(conditioned_price1)))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@cond1_",
                                                                                                    str(int(conditioned_price1)))
                        else:
                            new_intent = "give_yielded_price_positive_default"
                            text = self._randomResponse(new_intent, difficulty)
                            current_price, price_discount, batch_sale_amount, free_amount, CN_rate, EN_rate \
                                , conditioned_price0, conditioned_price1 = self.items[item_name].yield_price(use_rate=False)
                            text = text.replace('_@discount_price_', str(int(price_discount)))
                            text = text.replace('_@current_price_', str(int(current_price)))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@discount_price_",
                                                                                                    str(price_discount))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@discount_price_",
                                                                                                    str(price_discount))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@current_price_",
                                                                                                    str(current_price))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@current_price_",
                                                                                                    str(current_price))
                            self.UserIntent.append(new_intent)

                else:
                    new_intent = "negative_to_ask_discount"
                    text = self._randomResponse(new_intent, difficulty)
                    self.UserIntent.append(new_intent)
            else:
                new_intent = "no_intent"
                text = self._randomResponse(new_intent, difficulty)
                self.UserIntent.append(new_intent)
        elif intent == 'confirm_amount':
            if not self.avoid_lunatic():
                item_name = self.item_we_are_talking_EN
                unit = entities['unit']['value']
                amount = entities['number']['value']
                amount = int(w2n.word_to_num(amount))
                if amount <= self.items[item_name].check_stock():
                    self.checked_amount = True
                    self.items[item_name].set_buying_amount(amount)
                    if not self.checked_spec:
                        new_intent = 'ask_spec'
                        text = self._randomResponse(new_intent, difficulty)
                        if self.OutputLanguage == 'CN':
                            text = text.replace('_@spec1_', self.items[item_name].get_specs('CN')[0])
                            text = text.replace('_@spec2_', self.items[item_name].get_specs('CN')[1])
                        else:
                            text = text.replace('_@spec1_', self.items[item_name].get_specs('EN')[0])
                            text = text.replace('_@spec2_', self.items[item_name].get_specs('EN')[1])
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@spec1_", str(
                            self.items[item_name].get_specs('CN')[0]))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@spec1_", str(
                            self.items[item_name].get_specs("EN")[0]))
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@spec2_", str(
                            self.items[item_name].get_specs('CN')[1]))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@spec2_", str(
                            self.items[item_name].get_specs('EN')[1]))
                        self.UserIntent.append(new_intent)
                    else:
                        new_intent = 'deliver'
                        text = self._randomResponse(new_intent, difficulty)
                        if self.OutputLanguage == 'CN':
                            text = text.replace('_@item_', self.item_we_are_talking_CN)
                        else:
                            text = text.replace('_@item_', self.item_we_are_talking_EN)
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@item_", str(
                            self.item_we_are_talking_CN))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@item_", str(
                            self.item_we_are_talking_EN))
                        self.UserIntent.append(new_intent)
                        if difficulty <= 2:
                            self.prepare_for_next_trade()
                        else:
                            new_intent = 'show_bill'
                            text = self._randomResponse(new_intent, difficulty)
                            text = text.replace('_@price_', str(self.calc_bill()))
                            self.AgentUtterances[-1]['CN'] = \
                                self.AgentUtterances[-1]['CN'].replace("_@price_", str(self.calc_bill()))
                            self.AgentUtterances[-1]['EN'] = \
                                self.AgentUtterances[-1]['EN'].replace("_@price_", str(self.calc_bill()))
                else:
                    new_intent = 'negative_to_confirm_amount'
                    text = self._randomResponse(new_intent, difficulty)
                    self.UserIntent.append(new_intent)
                if not self.items[item_name].check_unit(unit):
                    text += ' (请注意量词！)'
            else:
                new_intent = "no_intent"
                text = self._randomResponse(new_intent, difficulty)
                self.UserIntent.append(new_intent)
        elif intent == 'confirm_spec':
            if not self.avoid_lunatic():
                item_name = self.item_we_are_talking_EN
                spec = entities['spec']['value']
                if self.items[item_name].check_spec(spec):
                    self.checked_spec = True
                    if not self.checked_amount:
                        new_intent = "ask_amount"
                        text = self._randomResponse(new_intent, difficulty)
                        if self.OutputLanguage == 'CN':
                            text = text.replace('_@unit_', self.items[item_name].get_unit("CN"))
                        else:
                            text = text.replace('_@unit_', self.items[item_name].get_unit("EN"))
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@unit_", str(
                            self.items[item_name].get_unit("CN")))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@unit_", str(
                            self.items[item_name].get_unit("EN")))
                        self.UserIntent.append(new_intent)
                    else:
                        new_intent = 'deliver'
                        text = self._randomResponse(new_intent, difficulty)
                        if self.OutputLanguage == 'CN':
                            text = text.replace('_@item_', self.item_we_are_talking_CN)
                        else:
                            text = text.replace('_@item_', self.item_we_are_talking_EN)
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@item_", str(
                            self.item_we_are_talking_CN))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@item_", str(
                            self.item_we_are_talking_EN))
                        self.UserIntent.append(new_intent)
                        if difficulty <= 2:
                            self.prepare_for_next_trade()
                        else:
                            new_intent = 'show_bill'
                            text = self._randomResponse(new_intent, difficulty)
                            text = text.replace('_@price_', str(self.calc_bill()))
                            self.AgentUtterances[-1]['CN'] = \
                                self.AgentUtterances[-1]['CN'].replace("_@price_", str(self.calc_bill()))
                            self.AgentUtterances[-1]['EN'] = \
                                self.AgentUtterances[-1]['EN'].replace("_@price_", str(self.calc_bill()))
                else:
                    new_intent = 'negative_to_confirm_spec'
                    text = self._randomResponse(new_intent, difficulty)
                    self.UserIntent.append(new_intent)
            else:
                new_intent = "no_intent"
                text = self._randomResponse(new_intent, difficulty)
                self.UserIntent.append(new_intent)
        elif intent == 'check_if_in_stock_with_amt':
            if 'item' in entities.keys():
                item_name = entities['item']['value']
                if self.vendor_has_it(item_name):
                    if item_name != self.item_we_are_talking_EN:
                        self.item_we_are_talking_EN = item_name
                        self.item_we_are_talking_CN = self.items[self.item_we_are_talking_EN].get_name("CN")
                        self.checked_item = True
                    amount = entities['number']['value']
                    amount = int(w2n.word_to_num(amount))
                    if amount <= self.items[item_name].check_stock():
                        self.checked_amount = True
                        self.items[item_name].set_buying_amount(amount)
                        if not self.checked_spec:
                            new_intent = 'ask_spec'
                            text = self._randomResponse(new_intent, difficulty)
                            if self.OutputLanguage == 'CN':
                                text = text.replace('_@spec1_', self.items[item_name].get_specs('CN')[0])
                                text = text.replace('_@spec2_', self.items[item_name].get_specs('CN')[1])
                            else:
                                text = text.replace('_@spec1_', self.items[item_name].get_specs('EN')[0])
                                text = text.replace('_@spec2_', self.items[item_name].get_specs('EN')[1])
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@spec1_", str(
                                self.items[item_name].get_specs('CN')[0]))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@spec1_", str(
                                self.items[item_name].get_specs("EN")[0]))
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@spec2_", str(
                                self.items[item_name].get_specs('CN')[1]))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@spec2_", str(
                                self.items[item_name].get_specs('EN')[1]))
                            self.UserIntent.append(new_intent)
                        else:
                            new_intent = 'deliver'
                            text = self._randomResponse(new_intent, difficulty)
                            if self.OutputLanguage == 'CN':
                                text = text.replace('_@item_', self.item_we_are_talking_CN)
                            else:
                                text = text.replace('_@item_', self.item_we_are_talking_EN)
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@item_", str(
                                self.item_we_are_talking_CN))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@item_", str(
                                self.item_we_are_talking_EN))
                            # self.send_trade_info(self.item_we_are_talking_EN, self.calc_bill())
                            self.UserIntent.append(new_intent)
                            if difficulty <= 2:
                                self.prepare_for_next_trade()
                            else:
                                new_intent = 'show_bill'
                                text = self._randomResponse(new_intent, difficulty)
                                text = text.replace('_@price_', str(self.calc_bill()))
                                self.AgentUtterances[-1]['CN'] = \
                                    self.AgentUtterances[-1]['CN'].replace("_@price_", str(self.calc_bill()))
                                self.AgentUtterances[-1]['EN'] = \
                                    self.AgentUtterances[-1]['EN'].replace("_@price_", str(self.calc_bill()))
                    else:
                        new_intent = 'negative_to_confirm_amount'
                        text = self._randomResponse(new_intent, difficulty)
                        self.UserIntent.append(new_intent)
                else:
                    new_intent = "negative_to_check_in_stock"
                    text = self._randomResponse(new_intent, difficulty)
                    self.UserIntent.append(new_intent)
            else:
                new_intent = "no_intent"
                text = self._randomResponse(new_intent, difficulty)
                self.UserIntent.append(new_intent)
        elif intent == 'check_if_in_stock_want' or intent == 'check_if_in_stock_have':
            print('\n\n')
            print(self.items.keys())
            if 'item' in entities.keys():
                item_name = entities['item']['value']
                prefix = ''
                if self.vendor_has_it(item_name):
                    if intent == 'check_if_in_stock_want' and self.OutputLanguage == 'CN':
                        prefix = '好的，'
                    elif intent == 'check_if_in_stock_have' and self.OutputLanguage == 'CN':
                        prefix = '有的，'
                    if item_name != self.item_we_are_talking_EN:
                        self.item_we_are_talking_EN = item_name
                        self.item_we_are_talking_CN = self.items[self.item_we_are_talking_EN].get_name("CN")
                        self.checked_item = True
                    new_intent = random.choice(["ask_amount", "ask_spec"])
                    text = self._randomResponse(new_intent, difficulty)
                    text = prefix + text
                    if new_intent == "ask_amount":
                        if self.OutputLanguage == 'CN':
                            text = text.replace('_@unit_', self.items[item_name].get_unit("CN"))
                        else:
                            text = text.replace('_@unit_', self.items[item_name].get_unit("EN"))
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@unit_", str(
                            self.items[item_name].get_unit("CN")))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@unit_", str(
                            self.items[item_name].get_unit("EN")))
                    elif new_intent == "ask_spec":
                        if self.OutputLanguage == 'CN':
                            text = text.replace('_@spec1_', self.items[item_name].get_specs('CN')[0])
                            text = text.replace('_@spec2_', self.items[item_name].get_specs('CN')[1])
                        else:
                            text = text.replace('_@spec1_', self.items[item_name].get_specs('EN')[0])
                            text = text.replace('_@spec2_', self.items[item_name].get_specs('EN')[1])
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@spec1_", str(
                            self.items[item_name].get_specs('CN')[0]))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@spec1_", str(
                            self.items[item_name].get_specs("EN")[0]))
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@spec2_", str(
                            self.items[item_name].get_specs('CN')[1]))
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@spec2_", str(
                            self.items[item_name].get_specs('EN')[1]))
                        self.UserIntent.append(new_intent)
                else:
                    new_intent = "negative_to_check_in_stock"
                    text = self._randomResponse(new_intent, difficulty)
                    self.UserIntent.append(new_intent)
            else:
                new_intent = "no_intent"
                text = self._randomResponse(new_intent, difficulty)
                self.UserIntent.append(new_intent)
        elif intent == 'check_price':
            if not self.avoid_lunatic():
                item_name = self.item_we_are_talking_EN
                stock_amt = self.items[item_name].check_stock()
                if stock_amt > 0:
                    # we have that
                    new_intent = "positive_to_check_price"
                    current_price = self.items[item_name].check_current_price()
                    text = self._randomResponse(new_intent, difficulty)
                    text = text.replace('_@price_', str(int(current_price)))
                    self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@price_", str(
                        current_price))
                    self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@price_", str(
                        current_price))
                    self.UserIntent.append(new_intent)
                else:
                    # we dont have that
                    new_intent = "negative_to_check_price"
                    text = self._randomResponse(new_intent, difficulty)
                    self.UserIntent.append(new_intent)
            else:
                new_intent = "no_intent"
                text = self._randomResponse(new_intent, difficulty)
                self.UserIntent.append(new_intent)
        elif intent == 'confirm_buy':
            if not self.avoid_lunatic():
                item_name = self.item_we_are_talking_EN
                if self.vendor_has_it(item_name) and self.buy_check():
                    new_intent = 'positive_to_confirm_buy'
                    text = self._randomResponse(new_intent, difficulty)
                    self.UserIntent.append(new_intent)
                else:
                    new_intent = 'negative_to_confirm_buy'
                    text = self._randomResponse(new_intent, difficulty)
                    self.UserIntent.append(new_intent)
                    if not self.checked_item:
                        if self.OutputLanguage == 'CN':
                            text = text.replace('_@issue_', '你要买什么')
                        else:
                            text = text.replace('_@issue_', 'what you want to buy')
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@issue_", '你要买什么')
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@issue_",
                                                                                                'what you want to buy')
                    elif not self.checked_amount:
                        if self.OutputLanguage == 'CN':
                            text = text.replace('_@issue_', '你要买多少')
                        else:
                            text = text.replace('_@issue_', 'how many/ much you want to buy')
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@issue_", '你要卖多少')
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@issue_",
                                                                                                'how many/ much you want to '
                                                                                                'buy')
                    elif not self.checked_spec:
                        if self.OutputLanguage == 'CN':
                            text = text.replace('_@issue_', '你要买哪种')
                        else:
                            text = text.replace('_@issue_', 'which kind you want to buy')
                        self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@issue_", '你要买哪种')
                        self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@issue_",
                                                                                                'which kind you want '
                                                                                                'to buy')
                    elif not self.vendor_has_it(item_name):
                        new_intent = 'negative_to_check_in_stock'
                        text = self._randomResponse(new_intent, difficulty)
                        self.UserIntent.append(new_intent)
            else:
                new_intent = "no_intent"
                text = self._randomResponse(new_intent, difficulty)
                self.UserIntent.append(new_intent)
        elif intent == 'pay':
            if not self.avoid_lunatic():
                item_name = self.item_we_are_talking_EN
                payment_method = entities['payment_method']['value']
                if self.vendor_has_it(item_name):
                    vendor_accepted_payment_methods_EN = self.items[item_name].get_payment_methods("EN")
                    vendor_accepted_payment_methods_CN = self.items[item_name].get_payment_methods("CN")
                    if payment_method in vendor_accepted_payment_methods_EN:
                        new_intent = 'deliver'
                        self.items[item_name].sold_update()
                        if difficulty != 1:
                            self.prepare_for_next_trade()
                        text = self._randomResponse(new_intent, difficulty)
                        self.UserIntent.append(new_intent)
                        if '@' in text:
                            if self.OutputLanguage == 'CN':
                                text = text.replace('_@item_', self.item_we_are_talking_CN)
                            else:
                                text = text.replace('_@item_', self.item_we_are_talking_EN)
                            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@price_", str(
                                self.item_we_are_talking_CN))
                            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@price_", str(
                                self.item_we_are_talking_EN))
                    else:
                        # text = "不好意思，我只接受"
                        # for i in range(len(vendor_accepted_payment_methods_CN) - 1):
                        #     text += vendor_accepted_payment_methods_CN[i]
                        #     if i != len(vendor_accepted_payment_methods_CN) - 2:
                        #         text += ', '
                        # text += "和"
                        # text += vendor_accepted_payment_methods_CN[-1]
                        new_intent = 'negative_to_pay'
                        text = self._randomResponse(new_intent, difficulty)
                        self.UserIntent.append(new_intent)
                else:
                    new_intent = 'negative_to_confirm_buy'
                    text = self._randomResponse(new_intent, difficulty)
                    self.UserIntent.append(new_intent)
            else:
                new_intent = "no_intent"
                text = self._randomResponse(new_intent, difficulty)
                self.UserIntent.append(new_intent)
        elif intent == 'thanks':
            new_intent = 'thanks'
            text = self._randomResponse(new_intent, difficulty)
            self.UserIntent.append(new_intent)
        elif intent == 'cant_buy':
            new_intent = 'answer_cant_buy'
            text = self._randomResponse(new_intent, difficulty)
            self.UserIntent.append(new_intent)
        else:
            text = self._randomResponse("negative", difficulty)
            self.UserIntent.append("negative")

        return text


