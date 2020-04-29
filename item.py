import pandas as pd
import datetime
import os
import screenshots as gui
import pyautogui


from utilities.utils import percent_of, wait_for, random_typer, move_mouse_to_image_within_region


class Item:

    def __init__(self, name, limit, runescape_instance):
        self.item_name = name
        self.runescape_instance = runescape_instance
        self.score_valid = False
        self._buy_or_sell = None
        self.qty_in_inventory = 0
        self.qty_in_process = 0
        self.money_in_process = 0
        self.limit = limit
        self.number_available_to_buy = limit
        self.sell_price = None
        self.buy_price = None
        self.time_buy_order_placed = None
        self.time_of_last_pc = None
        self.quantity_to_buy = None
        self.max_item_age = 1800
        self.ge_slot = None

    @property
    def optimal_max_quantity(self):
        limit = self.limit
        optimal_max = (self.runescape_instance.money / self.buy_price) / len(self.runescape_instance.empty_ge_slots)
        return int(min(limit, optimal_max))

    @property
    def image(self):
        file_name = 'Tools/screenshots/items/legacy_items/' + self.item_name.replace(' ', '_') + '.png'
        if os.path.isfile(file_name):
            return file_name
        else:
            print(
                f'You do not have an image file for {self.item_name} so the script is aborting, to fix this issue'
                f' either take a screenshot of {self.item_name} or remove it from the list of items to merch')

    @property
    def transaction_record(self):
        df_transaction = self.runescape_instance.transaction_record()
        mask_item = df_transaction.Item == self.item_name
        df_item = df_transaction.loc[mask_item]
        return df_item

    @property
    def current_state(self):
        return self._buy_or_sell

    @current_state.setter
    def current_state(self, value):
        assert value in ['buy', 'sell', None]
        self._buy_or_sell = value

    def score(self):
        df_item = self.transaction_record
        # TODO: MAke this a weighted average
        item_score = df_item['Score'].mean()
        return item_score if not pd.isnull(item_score) else 0

    def set_time_of_last_pc(self):
        self.time_of_last_pc = datetime.datetime.now()

    def set_price_instant_bought_at(self, price):
        self.sell_price = price

    def set_price_instant_sold_at(self, price):
        self.buy_price = price

    def set_quantity_to_buy(self, number):
        self.quantity_to_buy = number

    def set_time_buy_order_placed(self):
        self.time_buy_order_placed = datetime.datetime.now()

    def price_is_outdated(self):
        if self.time_of_last_pc is None:
            return True
        else:
            return (datetime.datetime.now() - self.time_of_last_pc).seconds > self.max_item_age

    def qty_available_to_buy(self):
        transactions = self.transaction_record
        aged_threshold = datetime.datetime.now() - datetime.timedelta(hours=4)
        item_mask = transactions['Item'] == self.item_name
        time_mask = pd.to_datetime(transactions['Timestamp']) > aged_threshold
        num_items_on_cooldown = transactions.loc[item_mask & time_mask]['Qty'].sum()
        return self.limit - num_items_on_cooldown

    def return_on_investment(self):
        return percent_of(buy_price=self.sell_price,
                          sell_price=self.buy_price)

    def meets_profit_threshold(self):
        if self.sell_price or self.buy_price is None:
            return True

        return (self.return_on_investment() > 0.025) and (self.sell_price - self.buy_price > 3)

    def find_current_buy_price(self):
        self.ge_slot = self.runescape_instance.empty_ge_slot()
        self.runescape_instance.select_sell_bag(self.ge_slot)
        wait_for(gui.sell_offer, self.runescape_instance)
        self.runescape_instance.select_inventory_item()
        price = 1
        self.runescape_instance.enter_price(price)
        self.runescape_instance.confirm_offer()
        wait_for(gui.view_all_offers, self.ge_slot.runescape_instance)
        price = self.runescape_instance.collect_items_and_return_price(self.ge_slot)
        self.runescape_instance.update_money(price)
        wait_for(gui.view_all_offers, self.ge_slot.runescape_instance)
        self.runescape_instance.GEMerch.add_transaction(item=self, qty=1, price=price, action="Find_Buy")
        self.set_time_of_last_pc()
        self.set_price_instant_bought_at(price)
        self.reset_item_and_slot()
        print('Current buy price for {} is {} gp'.format(self.item_name, price))

    def find_current_sell_price(self):
        self.ge_slot = self.runescape_instance.empty_ge_slot()
        self.runescape_instance.select_buy_bag(self.ge_slot)
        wait_for(gui.buy_prompt, self.runescape_instance)
        random_typer(str(self.item_name))
        wait_for(self.image, self.runescape_instance.region)
        move_mouse_to_image_within_region(self.image)
        pyautogui.click()
        test_price = 1000
        self.runescape_instance.enter_price(test_price)
        self.runescape_instance.confirm_offer()
        self.runescape_instance.update_money(-test_price)
        wait_for(gui.view_all_offers, self.runescape_instance)
        price_per_item = self.runescape_instance.collect_items_and_return_price(self.ge_slot)
        self.runescape_instance.update_money(test_price-price_per_item)
        wait_for(gui.view_all_offers, self.runescape_instance)
        self.runescape_instance.GEMerch.add_transaction(item=self, qty=1, price=price_per_item, action='Find_Sell')
        self.set_time_of_last_pc()
        self.set_price_instant_sold_at(price_per_item)
        self.reset_item_and_slot()
        print('Current sell price for {} is {} gp'.format(self.item_name, price_per_item))

    def buy_optimal_max(self, price):
        self.buy_item(price, quantity=self.optimal_max_quantity)

    def buy_item(self, price, quantity):
        assert price * quantity < self.runescape_instance.money
        self.ge_slot = self.runescape_instance.empty_ge_slot()

        self.runescape_instance.select_buy_bag(self.ge_slot)
        wait_for(gui.buy_prompt, self.runescape_instance)

        print(f'Buying: {self.item_name} At Price Each: {price}')
        random_typer(str(self.item_name))

        wait_for(self.image, self.runescape_instance)
        move_mouse_to_image_within_region(self.image)
        pyautogui.click()

        self.runescape_instance.enter_price(price)
        self.runescape_instance.enter_quantity(quantity)
        self.runescape_instance.confirm_offer()

        self.qty_in_process = quantity
        self.money_in_process = quantity * price
        self.runescape_instance.update_money(self.runescape_instance.money - self.money_in_process)
        self.set_time_buy_order_placed()
        self._buy_or_sell = 'buy'
        print(f'Placed a buy order for {quantity} {self.item_name} at {price} each')

        wait_for(gui.view_all_offers, self.runescape_instance)
        self.ge_slot.set_new_image_of_slot()

    def sell_items(self, price=None):
        if price is None:
            price = self.sell_price
        self.ge_slot = self.runescape_instance.empty_ge_slot()

        self.runescape_instance.select_sell_bag(self.ge_slot)
        wait_for(gui.sell_offer, self.runescape_instance.region)

        self.runescape_instance.select_inventory_item()
        self.qty_in_process = self.qty_in_inventory
        self.qty_in_inventory = 0

        self.runescape_instance.enter_price(str(price))
        self.runescape_instance.confirm_offer()

        self.current_state('sell')
        print(f'Placed a sell order for {self.qty_in_process} {self.item_name} at {price} each')

        wait_for(gui.view_all_offers, self.runescape_instance.region)
        self.ge_slot.set_new_image_of_slot()

    def reset_item_and_slot(self):
        self._buy_or_sell = None
        self.ge_slot.item = None
        self.ge_slot = None




