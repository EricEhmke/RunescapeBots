import pandas as pd
import datetime
import os
import screenshots as gui
import pyautogui
import time
import random

from utilities.utils import percent_of, wait_for, random_typer, move_mouse_to_image_within_region, record_transaction,\
    screengrab_as_numpy_array, tesser_quantity_image


def check_if_image_exists(item_name):
    file_name = 'Tools/screenshots/items/legacy_items/' + item_name.replace(' ', '_') + '.png'
    if os.path.isfile(file_name):
        return file_name
    else:
        print(
            'You do not have an image file for {} so the script is aborting, to fix this issue either take'
            ' a screenshot of {} or remove it from the list of items to merch'.format(
                item_name, item_name))


class Item:

    def __init__(self, name, limit, runescape_instance):
        self.item_name = name
        self.limit = limit
        self.number_available_to_buy = limit
        self.image_in_ge_search = check_if_image_exists(name)
        self.price_instant_bought_at = None
        self.price_instant_sold_at = None
        self.current_state = None  # this will track if the item is currently being bought, sold or neither (None)
        self.is_score_valid = None
        self.time_buy_order_placed = None
        self.time_of_last_pc = None
        self.quantity_to_buy = None
        self.max_item_age = 1800
        self.runescape_instance = runescape_instance
        self.ge_slot = None

    def set_score_valid(self):
        self.is_score_valid = True

    def set_score_invalid(self):
        self.is_score_valid = False

    def set_time_item_buy_was_placed(self):
        self.time_buy_order_placed = datetime.datetime.now()

    def update_number_available_to_buy(self, number):
        self.number_available_to_buy = number

    def set_time_of_last_pc(self):
        self.time_of_last_pc = datetime.datetime.now()

    def set_price_instant_bought_at(self, price):
        self.price_instant_bought_at = price

    def set_price_instant_sold_at(self, price):
        self.price_instant_sold_at = price

    def set_quantity_to_buy(self, number):
        self.quantity_to_buy = number

    def set_current_state(self, state):
        self.current_state = state

    def price_is_outdated(self):
        if self.time_of_last_pc is None:
            return True
        else:
            return (datetime.datetime.now() - self.time_of_last_pc).seconds > self.max_item_age

    def qty_available_to_buy(self):
        transactions = self.runescape_instance.GEMerch.transaction_record
        aged_threshold = datetime.datetime.now() - datetime.timedelta(hours=4)
        item_mask = transactions['Item'] == self.item_name
        time_mask = pd.to_datetime(transactions['Timestamp']) > aged_threshold
        num_items_on_cooldown = transactions.loc[item_mask & time_mask]['Qty'].sum()
        return self.limit - num_items_on_cooldown

    def score(self):
        # filter transaction record for item calculate GP/hr and return as score
        df_transaction = self.runescape_instance.GEMerch.transaction_record
        mask_item = df_transaction.Item == self.item_name
        df_item = df_transaction.loc[mask_item]
        # TODO: Make this a weighted average
        item_score = df_item['Score'].mean()
        return item_score if not pd.isnull(item_score) else 0

    def return_on_investment(self):
        return percent_of(buy_price=self.price_instant_bought_at,
                          sell_price=self.price_instant_sold_at)

    def meets_profit_threshold(self):
        if self.price_instant_bought_at or self.price_instant_sold_at is None:
            return True

        return (self.return_on_investment() > 0.025) and (self.price_instant_bought_at - self.price_instant_sold_at > 3)

    def find_current_buy_price(self):
        self.runescape_instance.select_sell_bag(self.ge_slot)
        wait_for(gui.sell_offer, self.runescape_instance)
        self.runescape_instance.select_inventory_item()
        price = 1
        self.runescape_instance.enter_price(price)
        self.runescape_instance.confirm_offer()
        self.ge_slot.update_buy_or_sell_state('buy')
        wait_for(gui.view_all_offers, self.ge_slot.runescape_instance)
        price = self.runescape_instance.collect_items_and_return_price(self.ge_slot)
        self.ge_slot.update_buy_or_sell_state(None)
        wait_for(gui.view_all_offers, self.ge_slot.runescape_instance)
        record_transaction(ge_slot=self.ge_slot, qty=1, price=price, action="Find_Buy")
        self.set_time_of_last_pc()
        self.set_price_instant_bought_at(price)
        print('Current buy price for {} is {} gp'.format(self.item_name, price))

    def find_current_sell_price(self):
        self.runescape_instance.select_buy_bag(self.ge_slot)
        wait_for(gui.buy_prompt, self.runescape_instance)
        random_typer(str(self.item_name))
        wait_for(self.image_in_ge_search, self.runescape_instance.region)
        move_mouse_to_image_within_region(self.image_in_ge_search)
        pyautogui.click()
        self.runescape_instance.enter_price(1000)
        self.runescape_instance.confirm_offer()
        self.ge_slot.update_buy_or_sell_state('sell')
        wait_for(gui.view_all_offers, self.runescape_instance)
        price = self.runescape_instance.collect_items_and_return_price(self.ge_slot)
        self.ge_slot.update_buy_or_sell_state(None)
        wait_for(gui.view_all_offers, self.runescape_instance)
        record_transaction(ge_slot=self.ge_slot, qty=1, price=price, action='Find_Sell')
        self.set_time_of_last_pc()
        self.set_price_instant_sold_at(price)
        print('Current sell price for {} is {} gp'.format(self.item_name, price))

    def buy_item(self):
        self.runescape_instance.select_buy_bag(self.ge_slot)
        wait_for(gui.buy_prompt, self.runescape_instance)

        random_typer(str(self.item_name))
        wait_for(self.image_in_ge_search, self.runescape_instance)
        move_mouse_to_image_within_region(self.image_in_ge_search)
        pyautogui.click()

        self.runescape_instance.enter_price(self.price_instant_sold_at)
        print(f'Buying: {self.item_name} At Price Each: {self.price_instant_sold_at}')
        self.set_quantity_to_buy(int(min(self.qty_available_to_buy() - 2,
                                         (self.runescape_instance.money / self.price_instant_sold_at) /
                                         self.runescape_instance.number_of_empty_ge_slots)))
        self.runescape_instance.update_money(
            self.runescape_instance.money - (self.quantity_to_buy * self.price_instant_sold_at))

        self.runescape_instance.enter_quantity(self.quantity_to_buy)
        self.runescape_instance.confirm_offer()
        self.set_time_item_buy_was_placed()
        wait_for(gui.view_all_offers, self.runescape_instance)

        # update states accordingly
        self.ge_slot.update_buy_or_sell_state('buy')
        self.runescape_instance.check_for_empty_ge_slots()
        print('Placed a buy order for {} {} at {} each'.format(self.quantity_to_buy, self.item_name,
                                                               self.price_instant_sold_at))
        time.sleep(2 + random.random())
        self.ge_slot.set_image_of_slot()

    def sell_items(self, record_number_selling=False):
        # click correct sell bag
        # TODO: Finish refactoring this func
        self.runescape_instance.select_sell_bag()

        wait_for(gui.sell_offer, self.runescape_instance.region)
        # click item in inv
        self.runescape_instance.select_inventory_item()

        # We are selling what was an incomplete buy order
        if record_number_selling:
            try:
                # Click the all button because we don't know where in the inventory all of the items are.
                loc_of_all_button = pyautogui.locateOnScreen('Tools/screenshots/All_button.png',
                                                             region=self.runescape_instance.region)
                # Check how many we're actually selling
                number_selling_image = screengrab_as_numpy_array((loc_of_all_button[0] - 100, loc_of_all_button[1] - 27,
                                                                  loc_of_all_button[0] - 3, loc_of_all_button[1] - 12))
                quantity = tesser_quantity_image(number_selling_image)
                # Return the money to the pool (before we actually have it?)
                self.runescape_instance.update_money(self.runescape_instance.money + (
                        (self.quantity_to_buy - quantity) * self.price_instant_sold_at))
                print('Updating the quantity to buy to {}'.format(quantity))
                self.set_quantity_to_buy(quantity)

            except:
                print(
                    "Couldn't read the quantity bought correctly so setting score to invalid to prevent artificial high scores, money for the window may now be wrong too, we think there is {}gp in this window available".format(
                        self.runescape_instance.money))
                self.set_score_invalid()
        # click price button

        self.runescape_instance.enter_price(str(self.price_instant_bought_at))
        self.runescape_instance.confirm_offer()

        # update state of ge slot
        self.ge_slot.update_buy_or_sell_state('sell')
        wait_for(gui.view_all_offers, self.runescape_instance.region)
        print('Placed a sell order for {} {} at {} each'.format(self.quantity_to_buy, self.item_name,
                                                                self.price_instant_bought_at))
        time.sleep(2 + random.random())
        self.ge_slot.set_image_of_slot()

