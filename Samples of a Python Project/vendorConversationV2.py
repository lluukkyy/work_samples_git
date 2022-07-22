"""
@author: Zhicheng(Stark) Guo
@email: guoz6@rpi.edu
"""

# CODE 48.88  48.68  角和分  x块x毛x分 lucky numbers
# MENU 体恤衫->T恤衫 lucky numbers

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

    def get_current_price(self):
        return self.current_price

    def get_initial_price(self):
        return self.initial_price

    def yield_price(self):
        new_current_price = random.randint(int(self.final_price), int(self.current_price) - 1)
        CN_rate = round(float(new_current_price) / float(self.current_price), 2) * 100
        EN_rate = 1 - CN_rate
        ret_CN_rate = str(CN_rate)
        ret_EN_rate = str(EN_rate)

        if min(self.in_stock - 1, int(self.max_batch_sale_amount) + 1) - 2 > 0:
            batch_sale_amount = random.randint(2, min(self.in_stock - 1, int(self.max_batch_sale_amount) + 1))
            cond_price0 = self.current_price * batch_sale_amount
            cond_price1 = (self.current_price - new_current_price) * batch_sale_amount
            if min(self.in_stock - batch_sale_amount, int(self.max_free_amount) + 1) - 1 > 0:
                free_amount = random.randint(1, min(self.in_stock - batch_sale_amount, int(self.max_free_amount) + 1))
            else:
                free_amount = 0
        else:
            batch_sale_amount = 0
            free_amount = 0

        price_discount = self.current_price - self.current_price * CN_rate / 100
        self.current_price = self.current_price * CN_rate / 100
        if CN_rate % 10 == 0:
            ret_CN_rate = ret_CN_rate[0]
        if EN_rate % 10 == 0:
            ret_EN_rate = ret_EN_rate[0]

        return self.current_price, price_discount, batch_sale_amount, free_amount, ret_CN_rate, ret_EN_rate, cond_price0, cond_price1

    def check_yield(self):
        return self.current_price - 1 > self.final_price

    def get_stock_amt(self):
        return self.in_stock

    def check_unit(self, player_unit):
        return player_unit in self.units["CN"]

    def sold_update(self, batch_flag):
        amt = self.buying_amount
        if batch_flag and amt >= self.batch_sale_amount:
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
        self.username = userId
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
        self.discount_info = {
            'current_price': None,
            'price_discount': None,
            'batch_sale_amount': None,
            'free_amount': None,
            'CN_rate': None,
            'EN_rate': None,
            'cond_price0': None,
            'cond_price1': None
        }
        self.discount_batch_used = False
        self.discount_cond_used = False

        # self.unit_check_result = True
        # self.unit_checked = False

        system = systemHandler.SystemHandler()
        if not system.IsReady:
            pass
        self.sender = commHandler.commHandler(system.settings['server_ip'])

    @staticmethod
    def price_format(price):
        num_dict = {'1': '一', '2': '二', '3': '三', '4': '四', '5': '五',
                    '6': '六', '7': '七', '8': '八', '9': '九'}
        price_dict = {'-2': '分', '-1': '毛', '0': '块', '1': '十',
                      '2': '百', '3': '千', '4': '万', '8': '亿'}
        f = float(price)
        if float(f) == int(f):
            price = str(int(f))
        price = price.split('.')
        price_str = []
        for index, value in enumerate(price[0][::-1]):
            remain = index % 4
            if value != '0':
                if remain != 0:
                    if num_dict[value] == '一' and price_dict[str(remain)] == '十':
                        price_str.insert(0, price_dict[str(remain)])
                    else:
                        price_str.insert(0, num_dict[value] + price_dict[str(remain)])
                else:
                    price_str.insert(0, num_dict[value] + price_dict[str(index)])
            elif remain == 0 and (index + 1) != len(price[0]):
                price_str.insert(0, price_dict[str(index)])
        if len(price) > 1:
            for index, value in enumerate(price[1]):
                if index > 1:
                    break
                if value != 0:
                    price_str.append(num_dict[value] + price_dict['-' + str(index + 1)])
        return ''.join(price_str)

    def reset_discount_info(self):
        self.discount_info = {
            'current_price': None,
            'price_discount': None,
            'batch_sale_amount': None,
            'free_amount': None,
            'CN_rate': None,
            'EN_rate': None,
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
        self.reset_discount_info()

    def calc_bill(self):
        if self.discount_active:
            if self.discount_batch_used:
                print(self.items[self.item_we_are_talking_EN].get_current_price(), self.items[self.item_we_are_talking_EN].get_buying_amt(), self.discount_info['cond_price1'])
                if self.items[self.item_we_are_talking_EN].get_buying_amt() >= self.discount_info['batch_sale_amount']:
                    return self.items[self.item_we_are_talking_EN].get_current_price() * \
                            self.items[self.item_we_are_talking_EN].get_buying_amt()
                else:
                    return self.items[self.item_we_are_talking_EN].get_initial_price() * \
                           self.items[self.item_we_are_talking_EN].get_buying_amt()
            elif self.discount_cond_used:
                print(self.items[self.item_we_are_talking_EN].get_initial_price(), self.items[self.item_we_are_talking_EN].get_buying_amt(), self.discount_info['cond_price1'])
                if self.items[self.item_we_are_talking_EN].get_initial_price() * \
                           self.items[self.item_we_are_talking_EN].get_buying_amt() >= self.discount_info['cond_price0']:
                    return self.items[self.item_we_are_talking_EN].get_initial_price() * \
                           self.items[self.item_we_are_talking_EN].get_buying_amt() - self.discount_info['cond_price1']
                else:
                    return self.items[self.item_we_are_talking_EN].get_initial_price() * \
                           self.items[self.item_we_are_talking_EN].get_buying_amt()
            else:
                return self.items[self.item_we_are_talking_EN].get_current_price() * \
                       self.items[self.item_we_are_talking_EN].get_buying_amt()
        else:
            return self.items[self.item_we_are_talking_EN].get_initial_price() * \
                   self.items[self.item_we_are_talking_EN].get_buying_amt()

    def discount_operations(self, item_name):
        self.reset_discount_info()
        self.discount_active = True
        current_price, price_discount, batch_sale_amount, free_amount, CN_rate, EN_rate \
            , cond_price0, cond_price1 = self.items[item_name].yield_price()
        self.discount_info['current_price'] = current_price
        self.discount_info['price_discount'] = price_discount
        self.discount_info['batch_sale_amount'] = batch_sale_amount
        self.discount_info['free_amount'] = free_amount
        self.discount_info['CN_rate'] = CN_rate
        self.discount_info['EN_rate'] = EN_rate
        self.discount_info['cond_price0'] = cond_price0
        self.discount_info['cond_price1'] = cond_price1

    # preventing trade while no context
    def avoid_lunatic(self):
        return self.item_we_are_talking_CN.__len__() == 0 or self.item_we_are_talking_EN.__len__() == 0

    def buy_check(self):
        return self.checked_item and self.checked_amount and self.checked_spec

    def vendor_has_it(self, item_name_):
        print(self.items.keys())
        if item_name_ in self.items.keys():
            stock_amt = self.items[item_name_].get_stock_amt()
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
        elif intent == 'ask_discount':
            if len(self.item_we_are_talking_EN) == 0:
                text = self._randomResponse('item_not_mentioned', difficulty)
            elif self.checked_spec and not self.checked_amount:
                text = self._randomResponseWithSlot('agent_ask_amount', difficulty, preFill=['agent_ask_spec'])
                self.UserIntent.append(intent)
            elif self.checked_amount and not self.checked_spec:
                text = self._randomResponseWithSlot('agent_ask_spec', difficulty, preFill=['agent_ask_amount'])
                self.UserIntent.append(intent)
            else:
                item_name = self.item_we_are_talking_EN
                if self.items[item_name].check_yield():
                    self.discount_operations(item_name)
                    if self.discount_info['batch_sale_amount'] * self.discount_info['free_amount'] == 0:
                        text = self._randomResponse('default_positive_to_ask_discount', difficulty)
                    else:
                        text = self._randomResponse('positive_to_ask_discount', difficulty)
                else:
                    new_intent = "negative_to_ask_discount"
                    text = self._randomResponse(new_intent, difficulty)
                    self.UserIntent.append(new_intent)
        elif intent == 'positive' or intent == 'negative':
            self.detailed_intent = intent + '_to_' + self.UserIntent[-1]
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
        elif intent == 'purchase':
            self.checked_spec = 'spec' in entities or self.checked_spec
            self.checked_amount = 'sys-number' in entities or 'number' in entities or self.checked_amount
            if 'item' not in entities and len(self.item_we_are_talking_EN) == 0:
                text = self._randomResponse('no_item', difficulty)
            else:
                if not self.vendor_has_it(entities['item']['value']):
                    text = self._randomResponse('no_item', difficulty)
                else:
                    if len(self.item_we_are_talking_EN) == 0:
                        self.item_we_are_talking_EN = entities['item']['value']
                    if 'unit' in entities:
                        self.unit_checked = True
                        unit = entities['unit']['value']
                        self.unit_check_result = self.items[self.item_we_are_talking_EN].check_unit(unit)
                    if 'sys-number' in entities:
                        self.items[self.item_we_are_talking_EN].set_buying_amount(int(entities['sys-number']['value']))
                    elif 'number' in entities:
                        self.items[self.item_we_are_talking_EN].set_buying_amount(int(entities['number']['value']))
                    if self.checked_spec and self.checked_amount:
                        text = self._randomResponse('purchase', difficulty)
                    elif self.checked_spec and not self.checked_amount:
                        text = self._randomResponseWithSlot('agent_ask_amount', difficulty, preFill=['agent_ask_spec'])
                    elif self.checked_amount and not self.checked_spec:
                        text = self._randomResponseWithSlot('agent_ask_spec', difficulty, preFill=['agent_ask_amount'])
                    else:
                        text = self._randomResponseWithSlot('agent_ask_spec', difficulty)

                    if 'spec' in entities:
                        spec = entities['spec']['value']
                        if not self.items[self.item_we_are_talking_EN].check_spec(spec):
                            text = self._randomResponseWithSlot('no_spec', difficulty)
                    if 'number' in entities:
                        number = entities['number']['value']
                        if not self.items[self.item_we_are_talking_EN].get_stock_amt() - int(number) >= 0:
                            text = self._randomResponseWithSlot('no_stock', difficulty)

                self.UserIntent.append(intent)
            # unit check
            # if 'unit' in entities.keys():
            #     entities['unit']['value'] in
        elif intent in ['check_price', 'check_if_in_stock_have']:
            if 'item' not in entities:
                text = self._randomResponse('no_item', difficulty)
            else:
                self.item_we_are_talking_EN = entities['item']['value']
                text = self._randomResponse(intent, difficulty)
                self.UserIntent.append(intent)
        elif intent == 'pay':
            if len(self.item_we_are_talking_EN) == 0:
                text = self._randomResponse('item_not_mentioned', difficulty)
            elif self.checked_spec and not self.checked_amount:
                text = self._randomResponseWithSlot('agent_ask_amount', difficulty, preFill=['agent_ask_spec'])
                self.UserIntent.append(intent)
            elif self.checked_amount and not self.checked_spec:
                text = self._randomResponseWithSlot('agent_ask_spec', difficulty, preFill=['agent_ask_amount'])
                self.UserIntent.append(intent)
            else:
                text = self._randomResponse(intent, difficulty)
                self.UserIntent.append(intent)
                self.prepare_for_next_trade()
        else:
            text = self._randomResponse(intent, difficulty)
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
        if '_@price_' in text:
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace('_@price_', str(self.items[self.item_we_are_talking_EN].get_current_price()))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace('_@price_', self.price_format(str(self.items[self.item_we_are_talking_EN].get_current_price())))
            if lang == 'CN':
                text = text.replace('_@price_', self.price_format(str(self.items[self.item_we_are_talking_EN].get_current_price())))
            else:
                text = text.replace('_@price_', str(self.items[self.item_we_are_talking_EN].get_current_price()))
        elif '_@total_price_' in text:
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace('_@total_price_', str(round(self.calc_bill(), 2)))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace('_@total_price_', self.price_format(str(round(self.calc_bill(), 2))))
            if lang == 'CN':
                text = text.replace('_@total_price_', self.price_format(str(round(self.calc_bill(), 2))))
            else:
                text = text.replace('_@total_price_', str(round(self.calc_bill(), 2)))
        elif '_@item_' in text:
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace('_@item_', self.item_we_are_talking_EN)
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace('_@item_', self.item_we_are_talking_CN)
            text = text.replace('_@item_', self.item_we_are_talking_EN if lang=='EN' else self.item_we_are_talking_CN)
        elif '_@items_' in text:
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace('_@items_', ', '.join(self.EN_item_lst))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace('_@items_', ', '.join(self.CN_item_lst))
            text = text.replace('_@items_', ', '.join(self.EN_item_lst if lang=='EN' else self.CN_item_lst))
        elif '_@specs_' in text:
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace('_@specs_', ', '.join(self.items[self.item_we_are_talking_EN].get_specs('EN')[:-1]) + ' or ' + self.items[self.item_we_are_talking_EN].get_specs(lang)[-1])
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace('_@specs_', ', '.join(self.items[self.item_we_are_talking_EN].get_specs('CN')[:-1]) + '还是' + self.items[self.item_we_are_talking_EN].get_specs(lang)[-1])
            text = text.replace('_@specs_', ', '.join(self.items[self.item_we_are_talking_EN].get_specs(lang)[:-1]) + (' or ' if lang=='EN' else '还是') +self.items[self.item_we_are_talking_EN].get_specs(lang)[-1])
        elif '_@unit_' in text:
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace('_@unit_', ', '.join(self.items[self.item_we_are_talking_EN].get_unit('EN')))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace('_@unit_', ', '.join(self.items[self.item_we_are_talking_EN].get_unit("CN")))
            text = text.replace('_@unit_', ', '.join(self.items[self.item_we_are_talking_EN].get_unit(lang)))
        # elif '_@unit_check_' in text:
        #     if not self.unit_check_result:
        #         result = {
        #             'CN': '(请注意量词!)',
        #             'EN': '(Be ware of the unit!)'
        #         }
        #     else:
        #         result = {
        #             'CN': '',
        #             'EN': ''
        #         }
        #     self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace('_@unit_check_', result['EN'])
        #     self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace('_@unit_check_', result['CN'])
        #     text = text.replace('_@unit_check_', result[lang])

        elif '_@discount_price_' in text and '_@current_price_' in text:
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@discount_price_",  self.price_format(str(round(float(self.discount_info['price_discount']), 2))))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@discount_price_", str(round(float(self.discount_info['price_discount']), 2)))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@current_price_",  self.price_format(str(round(float(self.discount_info['current_price']), 2))))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@current_price_", str(round(float(self.discount_info['current_price']), 2)))
            if lang == 'CN':
                text = text.replace('_@discount_price_',  self.price_format(str(round(float(self.discount_info['price_discount']), 2))))
                text = text.replace('_@current_price_',  self.price_format(str(round(float(self.discount_info['current_price']), 2))))
            else:
                text = text.replace('_@discount_price_', str(round(float(self.discount_info['price_discount']), 2)))
                text = text.replace('_@current_price_', str(round(float(self.discount_info['current_price']), 2)))
        elif '_@batch_sale_amount_' in text and '_@current_price_' in text:
            self.discount_batch_used = True
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@batch_sale_amount_", str(int(self.discount_info['batch_sale_amount'])))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@batch_sale_amount_", str(int(self.discount_info['batch_sale_amount'])))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@current_price_", self.price_format(str(round(float(self.discount_info['current_price']) * self.discount_info['batch_sale_amount'], 2))))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@current_price_", str(round(float(self.discount_info['current_price']) * self.discount_info['batch_sale_amount'], 2)))
            text = text.replace('_@batch_sale_amount_', str(int(self.discount_info['batch_sale_amount'])))
            if lang == 'CN':
                text = text.replace('_@current_price_', self.price_format(str(round(float(self.discount_info['current_price']) * self.discount_info['batch_sale_amount'], 2))))
            else:
                text = text.replace('_@current_price_', str(round(float(self.discount_info['current_price']) * self.discount_info['batch_sale_amount'], 2)))
        elif '_@batch_sale_amount_' in text and '_@free_amount_' in text:
            self.items[self.item_we_are_talking_EN].set_free_amount(self.discount_info['free_amount'])
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@batch_sale_amount_", str(int(self.discount_info['batch_sale_amount'])))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@batch_sale_amount_", str(int(self.discount_info['batch_sale_amount'])))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@free_amount_", str(int(self.discount_info['free_amount'])))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@free_amount_", str(int(self.discount_info['free_amount'])))
            text = text.replace('_@batch_sale_amount_', str(int(self.discount_info['batch_sale_amount'])))
            text = text.replace('_@free_amount_', str(int(self.discount_info['free_amount'])))
        elif '_@discount_rate_' in text:
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@discount_rate_", str((round(float(self.discount_info['CN_rate']), 2))))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@discount_rate_", str((round(float(self.discount_info['EN_rate']), 2))))
            if lang == 'CN':
                text = text.replace('_@discount_rate_', str(round(float(self.discount_info['CN_rate']))))
            else:
                text = text.replace('_@discount_rate_', str(round(float(self.discount_info['EN_rate']))))
        elif '_@cond0_' in text and '_@cond1_' in text:
            self.discount_cond_used = True
            self.items[self.item_we_are_talking_EN].set_free_amount(self.discount_info['free_amount'])
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@cond0_", self.price_format(str(round(float(self.discount_info['cond_price0']), 2))))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@cond0_", str(round(float(self.discount_info['cond_price0']), 2)))
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@cond1_", self.price_format(str(round(float(self.discount_info['cond_price1']), 2))))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@cond1_", str(round(float(self.discount_info['cond_price1']), 2)))
            if lang == 'CN':
                text = text.replace('_@cond0_', self.price_format(str(round(float(self.discount_info['cond_price0']), 2))))
                text = text.replace('_@cond1_', self.price_format(str(round(float(self.discount_info['cond_price1']), 2))))
            else:
                text = text.replace('_@cond0_', str(round(float(self.discount_info['cond_price0']), 2)))
                text = text.replace('_@cond1_', str(round(float(self.discount_info['cond_price1']), 2)))
        elif '_@current_price_' in text:
            self.AgentUtterances[-1]['CN'] = self.AgentUtterances[-1]['CN'].replace("_@current_price_", self.price_format(str(round(float(self.discount_info['current_price']), 2))))
            self.AgentUtterances[-1]['EN'] = self.AgentUtterances[-1]['EN'].replace("_@current_price_", str(round(float(self.discount_info['current_price']), 2)))
            if lang == 'CN':
                text = text.replace('_@current_price_', self.price_format(str(round(float(self.discount_info['current_price']), 2))))
            else:
                text = text.replace('_@current_price_', str(round(float(self.discount_info['current_price']), 2)))
        # return
        return text


    def takeActions(self,userInput, agentResponse, debugInfo, gameProgressProfile):
        super().takeActions(userInput, agentResponse, debugInfo, gameProgressProfile)
        if agentResponse['user_intent'] == 'deliver':
            message = self.apiHandler.updateResponseForCreditBalance(userInput, agentResponse)
            agentResponse['paras']['balance'] = message['balance']
            if len(message['EN']) != 0:
                agentResponse['text'] = message['CN'] if self._ifContainChinese(agentResponse['text']) else message['EN']
            else:
                print(gameProgressProfile['lisa_on_street'].getTaskProcess('street'))
                self.apiHandler.checkOffQuest(agentResponse['IP'], 'street', gameProgressProfile['lisa_on_street'].getTaskProcess('street'))
        # elif agentResponse['user_intent'] == 'pay':
        #     message = self.apiHandler.updateResponseForCreditBalance(userInput['username'], self.calc_bill())
        #     print("MONEY SPENT: aft_spent", message['balance'])
        #     if self._ifContainChinese(agentResponse['text']):
        #         agentResponse['text'] += ' '
        #         agentResponse['text'] += message['CN']
        #     else:
        #         agentResponse['text'] += ' '
        #         agentResponse['text'] += message['EN']
        #     agentResponse['paras']['balance'] = message['balance']



