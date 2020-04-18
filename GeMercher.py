import operator

import pandas as pd
import pyautogui
import time
import pickle
import os
import pytesseract
import cv2
import numpy
import random
import PIL
import re
import screenshots as gui
import datetime
import numpy as np

from Custom_Modules.realmouse import move_mouse_to
from Custom_Modules import pointfrombox
from Custom_Modules import gelimitfinder
from Custom_Modules import items_to_merch_module
from utilities.utils import wait_for, move_mouse_to_image_within_region, random_typer, calc_break


def box_to_region(top_left_corner, bottom_right_corner):
    """

    :param top_left_corner: coordinates of the top left corner of a box
    :param bottom_right_corner: coordinates of the top left corner of a box
    :return: a pyautogui region
    """
    return top_left_corner[0], top_left_corner[1], bottom_right_corner[0] - top_left_corner[0], \
           bottom_right_corner[1] - top_left_corner[1]


def load_previous_scores():
    """
    Loads a dict of previous scores if it exists, returns an empty dict for population if not
    :return: dict
    """
    try:
        with (open("item_names_with_scores.txt", "rb")) as openfile:
            item_names_with_scores = pickle.load(openfile)
        score_items = True
        print(item_names_with_scores)
    except:
        item_names_with_scores = {}
        score_items = False
        print("We couldn't find a save file for item scores so items will be picked randomly")
    # this will check if all items used are scored and if not will give them a default score of 10
    return item_names_with_scores, score_items


def load_previous_items():
    """
    Loads a dict of previously used items if it exists. Starts an empty list if not.
    :return: list
    """
    try:
        with (open("list_of_items_in_use.txt", "rb")) as openfile:
            list_of_items_in_use = pickle.load(openfile)
    except:
        list_of_items_in_use = []

    return list_of_items_in_use


def find_slots_with_state(state_img, runescape_window):
    """
    Finds ge_slots in a window with a state matching the supplied screenshot
    :param state_img: A screenshot of the desired state
    :param runescape_windows: a runescape window or list of runescape windows
    :return: None or a generator object of slots with the desired state
    """
    for ge_slot in runescape_window.list_of_ge_slots:
        desired_state = pyautogui.locateOnScreen(state_img, region=ge_slot.region)
        if desired_state is not None:
            yield ge_slot
        else:
            continue
    return None


def calc_score(qty, price, time_order_placed):
    return (qty * price) / (datetime.datetime.now() - time_order_placed).seconds


def record_transaction(ge_slot, qty, price, action, score=np.nan):
    if action in ['Sell']:
        score = calc_score(qty=qty, price=price, time_order_placed=ge_slot.item.time_buy_order_placed)
    ge_slot.runescape_instance.GEMerch.add_transaction(
        item=ge_slot.item, action=action, qty=qty, price=price, score=score)


def new_item_score(ge_slot, scored_items):
    return int(((scored_items[ge_slot.item.item_name] * 5) + ((10 * ge_slot.item.quantity_to_buy * (
            ge_slot.item.price_instant_bought_at - ge_slot.item.price_instant_sold_at)) /
                                                              (datetime.datetime.now() - ge_slot.item.time_buy_order_placed).seconds)) / 6)


def clear_completed_offers(runescape_windows, scored_items, scores_valid):
    # TODO: This function is doing more than one thing
    for runescape_window in runescape_windows:
        for ge_slot in find_slots_with_state(gui.completed_ge_slot, runescape_window):
            price = collect_items_from_ge_slot(ge_slot)
            # mark score invalid if the offer completed outside of script runtime
            if not scores_valid:
                ge_slot.item.set_score_invalid()

            if ge_slot.buy_or_sell == 'buy':
                record_transaction(ge_slot=ge_slot, qty=ge_slot.item.quantity_to_buy, price=price, action=['Buy'])
                if ge_slot.item.is_aged() and ge_slot.item.qty_available_to_buy() > 0:
                    ge_slot.find_current_sell_price()
                # sell our items at the price instant bought at
                sell_items(ge_slot)

            elif ge_slot.buy_or_sell == 'sell':
                ge_slot.runescape_instance.update_money(
                    ge_slot.runescape_instance.money +
                    ((ge_slot.item.quantity_to_buy - 1) *
                     ge_slot.item.price_instant_bought_at))
                ge_slot.runescape_instance.update_profit(
                    (ge_slot.item.quantity_to_buy - 2) *
                    (ge_slot.item.price_instant_bought_at - ge_slot.item.price_instant_sold_at))
                record_transaction(ge_slot=ge_slot, qty=ge_slot.item.quantity_to_buy, price=price, action='Sell')
                print('Total profit made from this window is {}'.format(ge_slot.runescape_instance.profit))

                # Reset GE slot of next transaction
                ge_slot.reset_slot()


def percent_of(buy_price, sell_price):
    return 1 - (buy_price / sell_price)


def fill_empty_slots(scored_items, script):
    # TODO: This function does more than one thing
    # IF I have a pickled file I should verify whether its good or not
    empty_slots = []
    for instance in sorted(script.runescape_windows, key=operator.attrgetter('money')):
        for ge_slot in instance.list_of_ge_slots:
            if ge_slot.buy_or_sell is None and ge_slot.runescape_instance.items_available:
                empty_slots.append(ge_slot)

    if not empty_slots:
        print('No empty GE slots found in all windows')
        return
    empty_slot = empty_slots[0]

    # If item is_aged() & score < 0 then reset score to 0 and see if its profitable?

    top_item = max(empty_slot.runescape_instance.items_available(), key=operator.methodcaller('score'))

    print(f'Top scored item is {top_item.item_name}')
    # I have picked a scored item, now I need to reference the instance of that item in the Runescape Window
    empty_slot.set_item_in_ge_slot(top_item)

    # Find the current sell price for the item chosen
    wait_for(gui.buy_bag, empty_slot)
    if empty_slot.item.is_aged():
        # TODO: Refactor these functions so that they return the price and not set it to the item property
        empty_slot.find_current_sell_price()
        wait_for(gui.sell_bag, empty_slot)
        empty_slot.find_current_buy_price()

        # If this item is profitable, set prices for instant buy and sell

        if empty_slot.item.meets_profit_threshold():
            temp = empty_slot.item.price_instant_bought_at
            empty_slot.item.set_price_instant_bought_at(empty_slot.item.price_instant_sold_at)
            empty_slot.item.set_price_instant_sold_at(temp)

            # If this item has more than 5gp margin then undercut for faster sales
            if empty_slot.item.price_instant_bought_at - empty_slot.item.price_instant_sold_at > 5:
                empty_slot.item.set_price_instant_bought_at(empty_slot.item.price_instant_bought_at - 1)
                empty_slot.item.set_price_instant_sold_at(empty_slot.item.price_instant_sold_at + 1)

        else:
            print('Item does not meet profitability threshold, returning')
            return

    # Buy the item and set the image for the slot.
    empty_slot.item.set_score_valid()
    wait_for(gui.buy_bag, empty_slot)
    buy_item(empty_slot.runescape_instance, empty_slot)
    wait_for(gui.view_all_offers, empty_slot.runescape_instance)
    empty_slot.set_image_of_slot()


def main():
    merchant = Merchant()
    merchant.detect_windows()
    merchant.load_transaction_record()
    merchant.load_previous_scores()
    merchant.set_default_scores()
    merchant.reset_negative_scores()
    merchant.save_scores()

    previous_total_profit = None
    # TODO: Find better way to pickle whole state

    while True:
        print('Loop started')
        total_profit = 0
        completed_offer_check = False  # variable to see if there was a completed offer
        clear_completed_offers(merchant.runescape_windows, merchant.scored_items, merchant.score_items)
        if not merchant.score_items:
            print('Loaded from save: Previous scores are being marked as invalid and will not effect ratings')
            merchant.score_items = True
        fill_empty_slots(merchant.scored_items, merchant)

        # if time.time()-time_of_last_update_check > 10:

        # Check in process offers
        # break_check = False
        # for runescape_window in runescape_windows:
        #     for ge_slot in runescape_window.list_of_ge_slots:
        #         # Checks for slots that are in process
        #         if ge_slot.buy_or_sell != None:
        #             # TODO: Either eliminate this or improve its function
        #             # check_for_in_progress_or_view_offer(ge_slot)
        #             # print('Last screenshot of {} was taken {} seconds ago'.format(ge_slot.item.item_name, time.time()-ge_slot.time_of_last_screenshot))
        #             if not (ge_slot.image_of_slot == numpy.array(pyautogui.screenshot(
        #                     region=(ge_slot.top_left_corner[0], ge_slot.top_left_corner[1] + 90, 165, 10)))).all():
        #                 ge_slot.set_image_of_slot()
        #             elif time.time() - ge_slot.time_of_last_screenshot > 1800 and not completed_offer_check and not empty_slot_check:
        #                 print('Image of {} has not been updated in 30 minutes so we are aborting the offer'.format(
        #                     ge_slot.item.item_name))
        #                 # run cancel offer code
        #                 # first we cancel the offer
        #                 # print('We are about to cancel an offer that we believe to be in the window with coords {}, we are at line 287'.format(runescape_window.bottom_right_corner))
        #                 cancel_offer(ge_slot.top_left_corner)
        #                 wait_for(gui.offer_canceled, runescape_window)
        #                 print("Cancelled {} since the offer hasn't been updated in a while".format(
        #                     ge_slot.item.item_name))
        #                 # then if the item was a buy we handle it
        #                 if ge_slot.buy_or_sell == 'buy':
        #                     handle_cancelling_buy(runescape_window, ge_slot, list_of_items_in_use)
        #                 elif ge_slot.buy_or_sell == 'sell':
        #                     handle_cancelling_sell(ge_slot, list_of_items_in_use)
        #                 # we check if any of the item  bought and if so try to sell it
        #                 # we could check the sale history to read the number of items bought and update accordingly
        #                 # then if it was a sell we handle it
        #                 # we would simply retrieve the items and money and update accordingly, then find the new sell price and sell
        #                 break_check = True
        #             elif time.time() - ge_slot.time_of_last_screenshot > 3600 and ge_slot.buy_or_sell == 'sell':
        #                 print('Image of {} has not been updated in 1 hour so we are aborting the offer'.format(
        #                     ge_slot.item.item_name))
        #                 # run cancel offer code
        #                 # first we cancel the offer
        #                 # print('We are about to cancel an offer that we believe to be in the window with coords {}, we are at line 287'.format(runescape_window.bottom_right_corner))
        #                 cancel_offer(ge_slot.top_left_corner)
        #                 wait_for(gui.offer_canceled, ge_slot.runescape_instance)
        #                 # print("Cancelled {} since the offer hasn't been updated in a while".format(ge_slot.item.item_name))
        #                 handle_cancelling_sell(runescape_window, ge_slot, list_of_items_in_use)
        #                 # we check if any of the item  bought and if so try to sell it
        #                 # we could check the sale history to read the number of items bought and update accordingly
        #                 # then if it was a sell we handle it
        #                 # we would simply retrieve the items and money and update accordingly, then find the new sell price and sell
        #                 break_check = True
        #             elif time.time() - ge_slot.time_of_last_screenshot > 5400 and ge_slot.buy_or_sell == 'buy':
        #                 print('Image of {} has not been updated in 1.5 hours so we are aborting the offer'.format(
        #                     ge_slot.item.item_name))
        #                 # run cancel offer code
        #                 # first we cancel the offer
        #                 # print('We are about to cancel an offer that we believe to be in the window with coords {}, we are at line 287'.format(runescape_window.bottom_right_corner))
        #                 cancel_offer(ge_slot.top_left_corner)
        #                 wait_for(gui.offer_canceled, ge_slot.runescape_instance)
        #
        #                 # print("Cancelled {} since the offer hasn't been updated in a while".format(ge_slot.item.item_name))
        #                 handle_cancelling_buy(runescape_window, ge_slot, list_of_items_in_use)
        #                 # we check if any of the item  bought and if so try to sell it
        #                 # we could check the sale history to read the number of items bought and update accordingly
        #                 # then if it was a sell we handle it
        #                 # we would simply retrieve the items and money and update accordingly, then find the new sell price and sell
        #                 break_check = True
        #         if break_check:
        #             break
        #     if break_check:
        #         break
        #     # time_of_last_update_check = time.time()
        #
        # # Saves the state if we've been running long enough
        # if time.time() - time_of_last_save > 60 or last_saved_list_of_runescape_windows != runescape_windows or last_saved_list_of_items_in_use != list_of_items_in_use or total_profit != previous_total_profit:
        #     previous_total_profit = total_profit
        #     last_saved_list_of_runescape_windows = runescape_windows
        #     last_saved_list_of_items_in_use = list_of_items_in_use
        #     time_of_last_save = time.time()
        #     with (open("list_of_items_in_use.txt", "wb")) as openfile:
        #         pickle.dump(list_of_items_in_use, (openfile))
        #     with (open("runescape_windows.txt", "wb")) as openfile:
        #         pickle.dump(runescape_windows, (openfile))
        #     with (open("scored_items.txt", "wb")) as openfile:
        #         pickle.dump(scored_items, (openfile))
        #     with (open("time_of_last_save.txt", "wb")) as openfile:
        #         pickle.dump(time_of_last_save, (openfile))
        #     print('State has now been saved, you may be able to close the script and return from this point later')
        #     print(
        #         'Total profit made across all windows so far is {}. We have been running for {} minutes, this is a profit per hour of {}k per hour.'.format(
        #             total_profit, int((time.time() - start_time) / 60),
        #             int(3.6 * total_profit / (time.time() - start_time))))
        #     time_of_last_save = time.time()
        #     # print('Current scored item list {}'.format(scored_items))
        # '''if total_profit != previous_total_profit:
        #     previous_total_profit = total_profit
        #     #label = myfont.render("Current Total Profit: {}".format(total_profit), 1, (255,255,0))
        #     #game_display.blit(label, (10, 10))
        #     #pygame.display.update()
        #     print('Total profit made across all windows so far is {}. We have been running for {} minutes, this is a profit per hour of {}k per hour.'.format(total_profit, int((time.time()-start_time)/60), int(3.6*total_profit/(time.time()-start_time))))'''


class Merchant:

    def __init__(self):

        self.transaction_record = pd.DataFrame(columns=['Item', 'Timestamp', 'Action', 'Qty', 'Price', 'Msg', 'Score'])
        self.runescape_windows = None
        self.start_time = datetime.datetime.now()
        self.score_items = None
        self.scored_items = {}
        self.time_last_save = datetime.datetime.now()

    def detect_windows(self):
        runescape_windows = detect_runescape_windows(self)
        if not runescape_windows:
            print("Could not detect a Runescape Window, script aborting")
            quit()
        else:
            print(f'We have detected {len(runescape_windows)} window(s)')
        self.runescape_windows = runescape_windows

    def load_previous_scores(self):
        try:
            with (open("item_names_with_scores.txt", "rb")) as openfile:
                self.scored_items = pickle.load(openfile)
            self.score_items = True
            print(self.scored_items)
        except:
            self.scored_items = {}
            self.score_items = False
            print("We couldn't find a save file for item scores so items will be picked randomly")

    def set_default_scores(self):
        f2p_and_p2p_items = items_to_merch_module.p2p_items() + items_to_merch_module.f2p_items()
        [self.scored_items.setdefault(item, 500) for item in f2p_and_p2p_items if item not in self.scored_items.keys()]

    def reset_negative_scores(self):
        for item, score in self.scored_items.items():
            if score < 1:
                self.scored_items[item] = 100
                print(f'{item} was a negative score so we have set it to 100')

    def save_scores(self):
        with (open("item_names_with_scores.txt", "wb")) as openfile:
            pickle.dump(self.scored_items, openfile)

    def set_time_last_save(self):
        self.time_last_save = datetime.datetime.now()

    def load_transaction_record(self):
        try:
            with (open("transaction_record.csv", "rb")) as openfile:
                self.transaction_record = pd.read_csv(openfile)
        except:
            print("No transaction found, new empty record created.")

    def save_transaction_record(self):
        with (open("transaction_record.csv", "wb")) as openfile:
            self.transaction_record.to_csv(openfile)

    def add_transaction(self, item, action, qty, price, score):
        self.transaction_record = self.transaction_record.append(
            {'Item': item.item_name,
             'Timestamp': datetime.datetime.now(),
             'Action': action, 'Qty': qty,
             'Price': price,
             'Score': score}, ignore_index=True)
        self.save_transaction_record()


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

    def is_aged(self):
        if self.time_of_last_pc is None:
            return True
        else:
            return (datetime.datetime.now() - self.time_of_last_pc).seconds > self.max_item_age

    def qty_available_to_buy(self):
        transactions = self.runescape_instance.GEMerch.transaction_record
        aged_threshold = datetime.datetime.now() - datetime.timedelta(hours=4)
        item_mask = transactions['Item'] == self.item_name
        time_mask = transactions['Timestamp'] > aged_threshold
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
        return self.return_on_investment() > 0.025


class RunescapeWindow:
    # TODO: This class should be split in 2. 1 for GE related things and 1 for the RS window
    def __init__(self, position, parent_script):
        self.bottom_right_corner = position
        # I am leaving these numbers hard coded for 1440p until I find another solution
        self.top_left_corner = (position[0] - 482, position[1] - 304)
        self.region = (self.top_left_corner[0], self.top_left_corner[1], 484, 303)
        self.member_status = True
        # TODO: Move this to the GE slot class
        self.loc_price = (self.bottom_right_corner[0] - 396, self.bottom_right_corner[1] - 61), \
                         (self.bottom_right_corner[0] - 179, self.bottom_right_corner[1] - 28)

        self.list_of_ge_slots = initialise_ge_slots(self.top_left_corner, self.bottom_right_corner, self)
        # TODO: Fix the money detection
        # self.money = detect_money(self.top_left_corner, self.bottom_right_corner) TESSER NEEDS FIXING
        self.money = 14_000
        self.profit = 0
        self.time_of_last_break = datetime.datetime.now()
        # TODO: Change this to a simple left click or somthing According to authoer this is here just to make sure game doesn log out. Commented out just for testing
        # examine_money(position)
        self.items_to_merch = items_to_merch(self.member_status, self)
        self.number_of_empty_ge_slots = empty_ge_slot_check(self.list_of_ge_slots)
        self.items_in_use = [ge_slot.item for ge_slot in self.list_of_ge_slots]

        print('Initialised a window with {}Kgp and {} ge slots'.format(int(self.money / 1000),
                                                                       self.number_of_empty_ge_slots))

        self.loc_inventory_item = (self.bottom_right_corner[0] + 950, self.bottom_right_corner[1] + 329), \
                                  (self.bottom_right_corner[0] + 973, self.bottom_right_corner[1] + 349)
        self.loc_collection_box_gp = (self.bottom_right_corner[0] - 105, self.bottom_right_corner[1] - 51), \
                                     (self.bottom_right_corner[0] - 71, self.bottom_right_corner[1] - 21)
        self.loc_collection_box_item = (self.bottom_right_corner[0] - 55, self.bottom_right_corner[1] - 51), \
                                       (self.bottom_right_corner[0] - 20, self.bottom_right_corner[1] - 21)
        self.GEMerch = parent_script

    def update_profit(self, amount):
        self.profit = self.profit + amount

    def check_for_empty_ge_slots(self):
        self.number_of_empty_ge_slots = empty_ge_slot_check(self.list_of_ge_slots)

    def update_money(self, amount):
        self.money = amount

    @calc_break
    def select_inventory_item(self):
        item_location = pointfrombox.random_point(*self.loc_inventory_item)
        move_mouse_to(item_location[0], item_location[1])
        pyautogui.click()

    def items_available(self):
        return [item for item in self.items_to_merch if
                item.qty_available_to_buy() <= item.limit
                and
                item.current_state is None
                and
                (item.meets_profit_threshold() or item.is_aged())]


class GESlot:

    def __init__(self, position, runescape_instance):
        self.top_left_corner = position[0]
        self.bottom_right_corner = position[1]
        self.image_of_slot = numpy.array(
            pyautogui.screenshot(region=(self.top_left_corner[0], self.top_left_corner[1] + 90, 165, 10)))
        self.time_of_last_screenshot = None
        self.region = (
            self.top_left_corner[0], self.top_left_corner[1], self.bottom_right_corner[0] - self.top_left_corner[0],
            self.bottom_right_corner[1] - self.top_left_corner[1])
        self.buy_or_sell = None
        self.item = None
        self.image_of_slot: None
        self.runescape_instance = runescape_instance

    def __getattr__(self, attr):
        return getattr(self.runescape_instance, attr)

    def update_buy_or_sell_state(self, state):
        self.buy_or_sell = state
        self.item.set_current_state(state)

    def set_item_in_ge_slot(self, item):
        self.item = item

    def set_time_of_last_screenshot(self):
        self.time_of_last_screenshot = datetime.datetime.now()

    def set_image_of_slot(self):
        self.set_time_of_last_screenshot()
        print('Image of {} has been updated'.format(self.item.item_name))

    def location(self):
        location = pointfrombox.random_point(self.top_left_corner, self.bottom_right_corner)
        return location

    @calc_break
    def open_ge_slot(self):
        move_mouse_to(*self.location())
        pyautogui.click()
        wait_for(gui.completed_offer, self.runescape_instance)

    @calc_break
    def confirm_offer(self):
        move_mouse_to_image_within_region(gui.confirm_offer, self.runescape_instance.region)
        pyautogui.click()

    @calc_break
    def select_buy_bag(self):
        move_mouse_to_image_within_region(gui.buy_bag, self.region)
        pyautogui.click()

    @calc_break
    def select_sell_bag(self):
        move_mouse_to_image_within_region(gui.sell_bag, self.region)
        pyautogui.click()

    # TODO: find a better way to handle the region so this is not static
    @calc_break
    def enter_price(self, price):
        move_mouse_to_image_within_region(gui.enter_price_box, region=(1158, 650, 221, 76))
        pyautogui.click()
        time.sleep(1 + random.random())
        random_typer(str(price))
        time.sleep(random.random() + .25)
        pyautogui.press('enter')

    # TODO: find a better way to handle the region so this is not static
    @calc_break
    def enter_quantity(self, quantity):
        move_mouse_to_image_within_region(gui.enter_quantity_box, region=(936, 650, 221, 76))
        pyautogui.click()
        time.sleep(.5 + random.random())
        random_typer(str(quantity))
        time.sleep(random.random() + .25)
        pyautogui.press('enter')

    @calc_break
    def collect_1(self):
        top_left, bottom_right = pointfrombox.random_point(*self.runescape_instance.loc_collection_box_gp)
        move_mouse_to(top_left, bottom_right)
        pyautogui.click()

    @calc_break
    def collect_2(self):
        top_left, bottom_right = pointfrombox.random_point(*self.runescape_instance.loc_collection_box_item)
        move_mouse_to(top_left, bottom_right)
        pyautogui.click()

    def find_current_buy_price(self):
        self.select_sell_bag()
        wait_for(gui.sell_offer, self.runescape_instance)
        self.runescape_instance.select_inventory_item()
        price = 1
        self.enter_price(price)
        self.confirm_offer()
        self.update_buy_or_sell_state('buy')
        wait_for(gui.view_all_offers, self.runescape_instance)
        price = collect_items_from_ge_slot(self)
        self.update_buy_or_sell_state(None)
        wait_for(gui.view_all_offers, self.runescape_instance)
        record_transaction(ge_slot=self, qty=1, price=price, action="Find_Buy")
        self.item.set_time_of_last_pc()
        self.item.set_price_instant_bought_at(price)
        print('Current buy price for {} is {} gp'.format(self.item.item_name, price))

    def find_current_sell_price(self):
        self.select_buy_bag()
        wait_for(gui.buy_prompt, self.runescape_instance)
        random_typer(str(self.item.item_name))
        wait_for(self.item.image_in_ge_search, self.runescape_instance.region)
        move_mouse_to_image_within_region(self.item.image_in_ge_search)
        pyautogui.click()
        self.enter_price(1000)
        self.confirm_offer()
        self.update_buy_or_sell_state('sell')
        wait_for(gui.view_all_offers, self.runescape_instance)
        price = collect_items_from_ge_slot(self)
        self.update_buy_or_sell_state(None)
        wait_for(gui.view_all_offers, self.runescape_instance)
        record_transaction(ge_slot=self, qty=1, price=price, action='Find_Sell')
        self.item.set_time_of_last_pc()
        self.item.set_price_instant_sold_at(price)
        print('Current sell price for {} is {} gp'.format(self.item.item_name, price))

    def reset_slot(self):
        self.update_buy_or_sell_state(None)
        # self.item.set_price_instant_bought_at(None)
        # self.item.set_price_instant_sold_at(None)
        self.set_item_in_ge_slot(None)


def handle_cancelling_sell(ge_slot, list_of_items_in_use):
    ge_slot.collect_2()
    # runescape_window.update_money(runescape_window.money+((ge_slot.item.quantity_to_buy-2)*ge_slot.item.price_instant_sold_at)) think this line is breaking it
    ge_slot.collect_1()
    # if not then click box 2 and proceed to sell the item
    wait_for(gui.view_all_offers, ge_slot.runescape_instance)
    if ge_slot.item.qty_available_to_buy() > 0:
        # find_up_to_date_sell_price(runescape_window, ge_slot)
        ge_slot.find_current_sell_price()
        ge_slot.item.set_price_instant_bought_at(ge_slot.item.price_instant_bought_at - 1)
    else:
        ge_slot.item.set_price_instant_bought_at(int(ge_slot.item.price_instant_bought_at * 0.98) - 1)
    sell_items(ge_slot)
    # item didnt buy any of so we can just mark this slot as open and start again


def handle_cancelling_buy(runescape_window, ge_slot, list_of_items_in_use):
    ge_slot.collect_1()

    if not len(list(pyautogui.locateAllOnScreen(gui.view_all_offers, region=ge_slot.runescape_instance.region))) > 0:
        # we have to click box 2 still so click it and handle it
        ge_slot.collect_2()
        # if not then click box 2 and proceed to sell the item
        wait_for(gui.view_all_offers, runescape_window)
        if ge_slot.item.qty_available_to_buy() > 0:
            # find_up_to_date_sell_price(runescape_window, ge_slot)
            ge_slot.find_current_sell_price()
            ge_slot.item.set_price_instant_bought_at(ge_slot.item.price_instant_bought_at - 1)
        sell_items(ge_slot, record_number_selling=True)
        return ()
    # item didnt buy any of so we can just mark this slot as open and start again
    runescape_window.update_money(
        runescape_window.money + ((ge_slot.item.quantity_to_buy - 2) * ge_slot.item.price_instant_sold_at))
    ge_slot.update_buy_or_sell_state(None)
    list_of_items_in_use.remove(ge_slot.item.item_name)
    ge_slot.item.set_price_instant_bought_at(None)
    ge_slot.item.set_price_instant_sold_at(None)
    ge_slot.set_item_in_ge_slot(None)


def cancel_offer(ge_slot):
    ge_slot.open_ge_slot()
    move_mouse_to_image_within_region(gui.abort_offer, region=ge_slot.runescape_instance.region)
    wait_for(gui.offer_canceled, ge_slot.runescape_instance)
    ge_slot.collect_1()
    wait_for(gui.view_all_offers, ge_slot.runescape_instance)


def buy_item(runescape_window, ge_slot):
    # click the correct buy bag
    ge_slot.select_buy_bag()
    wait_for(gui.buy_prompt, runescape_window)

    random_typer(str(ge_slot.item.item_name))
    wait_for(ge_slot.item.image_in_ge_search, runescape_window)

    # click item
    move_mouse_to_image_within_region(ge_slot.item.image_in_ge_search)
    pyautogui.click()

    # Sometimes this will enter 1gp more or less to undercut/overcut and move items quickly
    ge_slot.enter_price(ge_slot.item.price_instant_sold_at)

    print('Min afunc is using values of {} and {}'.format(
        ge_slot.item.qty_available_to_buy() - 2,
        (runescape_window.money / ge_slot.item.price_instant_sold_at) / runescape_window.number_of_empty_ge_slots))

    ge_slot.item.set_quantity_to_buy(int(min(ge_slot.item.qty_available_to_buy() - 2, (
            runescape_window.money / ge_slot.item.price_instant_sold_at) / runescape_window.number_of_empty_ge_slots)))

    runescape_window.update_money(
        runescape_window.money - (ge_slot.item.quantity_to_buy * ge_slot.item.price_instant_sold_at))

    ge_slot.enter_quantity(ge_slot.item.quantity_to_buy)

    # click confirm off
    ge_slot.confirm_offer()
    ge_slot.item.set_time_item_buy_was_placed()
    wait_for(gui.view_all_offers, runescape_window)
    # update states accordingly
    ge_slot.update_buy_or_sell_state('buy')
    runescape_window.check_for_empty_ge_slots()
    print('Placed a buy order for {} {} at {} each'.format(ge_slot.item.quantity_to_buy, ge_slot.item.item_name,
                                                           ge_slot.item.price_instant_sold_at))
    time.sleep(2 + random.random())
    ge_slot.set_image_of_slot()


def sell_items(ge_slot, record_number_selling=False):
    # click correct sell bag
    # TODO: Finish refactoring this func
    ge_slot.select_sell_bag()

    wait_for(gui.sell_offer, ge_slot.runescape_instance.region)
    # click item in inv
    ge_slot.select_inventory_item()

    if record_number_selling:
        try:
            time.sleep(1 + random.random())
            # TODO: Update screenshot
            loc_of_all_button = pyautogui.locateOnScreen('Tools/screenshots/All_button.png',
                                                         region=ge_slot.runescape_instance.region)

            number_selling_image = screengrab_as_numpy_array((loc_of_all_button[0] - 100, loc_of_all_button[1] - 27,
                                                              loc_of_all_button[0] - 3, loc_of_all_button[1] - 12))
            quantity = tesser_quantity_image(number_selling_image)
            ge_slot.update_money(ge_slot.money + (
                    (ge_slot.item.quantity_to_buy - quantity) * ge_slot.item.price_instant_sold_at))
            print('Updating the quantity to buy to {}'.format(quantity))
            ge_slot.item.set_quantity_to_buy(quantity)

        except:
            print(
                "Couldn't read the quantity bought correctly so setting score to invalid to prevent artificial high scores, money for the window may now be wrong too, we think there is {}gp in this window available".format(
                    ge_slot.money))
            ge_slot.item.set_score_invalid()
    # click price button

    ge_slot.enter_price(str(ge_slot.item.price_instant_bought_at))
    ge_slot.confirm_offer()

    # update state of ge slot
    ge_slot.update_buy_or_sell_state('sell')
    wait_for(gui.view_all_offers, ge_slot.runescape_instance.region)
    print('Placed a sell order for {} {} at {} each'.format(ge_slot.item.quantity_to_buy, ge_slot.item.item_name,
                                                            ge_slot.item.price_instant_bought_at))
    time.sleep(2 + random.random())
    ge_slot.set_image_of_slot()


def check_price(location):
    """
    A function that reads a price from the screen via Tesseract OCR
    :param location: X, Y coords of the upper right and lower left hand corners of the area to be read
    :return: int
    """
    price = tesser_price_image(screengrab_as_numpy_array(location))
    return price


def detect_money(top_left_corner, bottom_right_corner):
    # TODO: Update this screenshot
    money_icon_path = 'Tools/screenshots/money_icon.png'
    money_icon_loc = pyautogui.locateOnScreen(money_icon_path, region=(
        top_left_corner[0], top_left_corner[1], bottom_right_corner[0] - top_left_corner[0],
        bottom_right_corner[1] - top_left_corner[1]))
    money_val_loc = (money_icon_loc[0] + 22, money_icon_loc[1], money_icon_loc[0] + 100, money_icon_loc[1] + 18)
    image = screengrab_as_numpy_array(money_val_loc)
    money_val = tesser_money_image(image)
    return money_val


def tesser_money_image(image):
    # image = cv2.resize(image, (0,0), fx=2, fy=2)
    image = PIL.Image.fromarray(image)
    txt = pytesseract.image_to_string(image, config='-psm 7')
    txt_list = list(txt)
    for i in range(len(txt_list)):
        if txt_list[i] == 'o':
            txt_list[i] = '0'
        elif txt_list[i] == 'O':
            txt_list[i] = '0'
        elif txt_list[i] == 'l':
            txt_list[i] = '1'
        elif txt_list[i] == 'I':
            txt_list[i] = '1'
        elif txt_list[i] == 'i':
            txt_list[i] = '1'
        elif txt_list[i] == 'M':
            txt_list[i] = '000000'
        elif txt_list[i] == 'K':
            txt_list[i] = '000'
        elif txt_list[i] == 'm':
            txt_list[i] = '000000'
        elif txt_list[i] == 'k':
            txt_list[i] = '000'
        elif txt_list[i] == 's':
            txt_list[i] = '5'
        elif txt_list[i] == 'S':
            txt_list[i] = '5'
        elif txt_list[i] == 'W':
            txt_list[i] = '40'
    txt = int(''.join(txt_list))
    return (txt)


# Merch related function
def tesser_quantity_image(image):
    image = cv2.resize(image, (0, 0), fx=2, fy=2)
    image = PIL.Image.fromarray(image)
    txt = pytesseract.image_to_string(image, config='-psm 7')
    txt = txt.replace(",", "")
    txt = txt.replace(" ", "")
    txt = txt.replace(".", "")
    if len(txt) == 0:
        txt = pytesseract.image_to_string(image, config='-psm 10')
    try:
        txt = int(txt)
    except:
        txt_list = list(txt)
        for i in range(len(txt_list)):
            if txt_list[i] == 'B':
                txt_list[i] = '8'
            elif txt_list[i] == 'l':
                txt_list[i] = '1'
            elif txt_list[i] == 'L':
                txt_list[i] = '1'
            elif txt_list[i] == 'i':
                txt_list[i] = '1'
            elif txt_list[i] == 'I':
                txt_list[i] = '1'
            elif txt_list[i] == 'o':
                txt_list[i] = '0'
            elif txt_list[i] == 'O':
                txt_list[i] = '0'
            elif txt_list[i] == 'z':
                txt_list[i] = '2'
            elif txt_list[i] == 'Z':
                txt_list[i] = '2'
            elif txt_list[i] == 'Q':
                txt_list[i] = '0'
            elif txt_list[i] == 's':
                txt_list[i] = '5'
            elif txt_list[i] == 'S':
                txt_list[i] = '5'
            elif txt_list[i] == '.':
                txt_list[i] = '9'
            elif txt_list[i] == ':':
                txt_list[i] = '8'
        if len(txt_list) > 1:
            txt = int(''.join(txt_list))
        else:
            txt = int(txt_list[0])
    return (txt)


def screengrab_as_numpy_array(location):
    """
    Takes a screenshot at provided location and returns screenshot as a numpy array
    :param location: x,y location points of bottom left and top right corners of an area on screen
    :return: numpy.array
    """
    top_left, bottom_right = location
    width = top_left[0] - top_left[1]
    height = bottom_right[1] - top_left[1]
    im = numpy.array(pyautogui.screenshot(region=(top_left[0], top_left[1], width, height)))
    return im


# Merch related function
def tesser_price_image(image):
    # Enlarge image for easier processing
    image = cv2.resize(src=image, dsize=None, fx=5, fy=5)
    # Convert image to grayscale
    image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    # Apply a threshold to change to complete black or white
    retval, image = cv2.threshold(image, 100, 255, cv2.THRESH_BINARY)
    # Invert image so text is black on white
    image = 255 - image
    # Show image
    # plt.imshow(image, cmap='gray')
    # Convert image to string
    # TODO: This needs to be improved. Has trouble with 4, vs 9 and 6
    txt = pytesseract.image_to_string(image, lang='eng', config='--psm 6')
    txt = txt.replace(",", "")
    txt = re.findall(r'\d+', txt)
    try:
        txt = int(txt[1]) / int(txt[0])
    except:
        print('Problem with tesser_price_image ocr occured. Price could not be found')

    return int(txt)


def collect_items_from_ge_slot(ge_slot):
    """
    Collects items from a given GE slot and returns the price the item bought or sold at
    :param ge_slot: GE slot to return items from
    :return: int price the items bought or sold at
    """

    # TODO: Split this into 3 functions. One for opening the GE slots
    #  One for checking price and another for collecting items
    # Open specific GE slot
    ge_slot.open_ge_slot()

    # Check the buy or sell price of the items
    price = check_price(ge_slot.loc_price)
    # TODO: Click these in a random or almost random order?
    # TODO: Move this into the runescape_instance class?
    # Collect the gold
    is_slot_empty = pyautogui.locateOnScreen(gui.empty_collect_slot, region=ge_slot.runescape_instance.region)
    if is_slot_empty is None:
        ge_slot.collect_2()

    ge_slot.collect_1()

    wait_for(gui.view_all_offers, ge_slot.runescape_instance)

    return price


def empty_ge_slot_check(list_of_ge_slots):
    number_of_ge_slots_open = 0
    for slot in list_of_ge_slots:
        if slot.buy_or_sell is None:
            number_of_ge_slots_open += 1
    return number_of_ge_slots_open


# This should be a more generalized function
# This should continue and take a screenshot for items that don't have one
def check_if_image_exists(item_name):
    global client_version
    file_name = 'Tools/screenshots/items/legacy_items/' + item_name.replace(' ', '_') + '.png'
    if os.path.isfile(file_name):
        return (file_name)
    else:
        print(
            'You do not have an image file for {} so the script is aborting, to fix this issue either take a screenshot of {} or remove it from the list of items to merch'.format(
                item_name, item_name))


def items_to_merch(member_status, runescape_instance):
    if member_status:
        items_to_merch = []
        # below is a list of members items to merch
        list_of_items = items_to_merch_module.p2p_items()
        list_of_item_limits = gelimitfinder.find_ge_limit(list_of_items)
        for i in range(len(list_of_item_limits)):
            list_of_item_limits[i] -= 1
        for i in range(len(list_of_items)):
            items_to_merch.append(Item(list_of_items[i], list_of_item_limits[i], runescape_instance))
        # we are a member so initialise a members item list
    else:
        items_to_merch = []
        # below is a list of f2p items to merch
        list_of_items = items_to_merch_module.f2p_items()
        list_of_item_limits = gelimitfinder.find_ge_limit(list_of_items)
        for i in range(len(list_of_item_limits)):
            list_of_item_limits[i] -= 1
        for i in range(len(list_of_items)):
            items_to_merch.append(Item(list_of_items[i], list_of_item_limits[i], runescape_instance))
        # we are f2p so initialise a f2p item list
    return items_to_merch


# TODO: Make this just right click on a random place on the screen instead.
def examine_money(position):
    pass
    # # this whole block just examines the amount of money
    # point = pointfrombox.random_point((138, 94), (189, 109))
    # # that the account has just for auto log out purposes
    # money_pouch = (position[0] - point[0], position[1] - point[1])
    # # so that it has a recording of the last time an action
    # realmouse.move_mouse_to(money_pouch[0], money_pouch[1])
    # # was taken and can keep track of this value in future to stop logouts
    # # occuring
    # pyautogui.click(button='right')
    # point = pointfrombox.random_point((-75, -32), (74, -24))
    # examine = (money_pouch[0] - point[0], money_pouch[1] - point[1])
    # realmouse.move_mouse_to(examine[0], examine[1])
    # pyautogui.click()


# Merch related function
def initialise_ge_slots(top_left_corner, bottom_right_corner, runescape_window):
    ge_slots = []
    for i in count_ge_slots(top_left_corner, bottom_right_corner):
        ge_slots.append(GESlot(((i[0], i[1]), (i[0] + i[2], i[1] + i[3])), runescape_window))
    return ge_slots


def detect_runescape_windows(parent_script):
    """
    Detects the number of Runescape Windows on screen
    :return: a list of Runescape Windows and their locations
    """
    list_of_runescape_windows = []
    for i in pyautogui.locateAllOnScreen(gui.main_ge_window):
        list_of_runescape_windows.append(
            RunescapeWindow((i[0] + i[2], i[1] + i[3]), parent_script))
    return list_of_runescape_windows


# this checks how many slots a particular window has available
def count_ge_slots(top_left_corner, bottom_right_corner):
    width = bottom_right_corner[0] - top_left_corner[0]
    height = bottom_right_corner[1] - top_left_corner[1]
    # Commenting out the region arg for testing
    list_of_ge_slots = list(
        pyautogui.locateAllOnScreen(gui.ge_open_slot, region=(top_left_corner[0], top_left_corner[1], width, height),
                                    confidence=0.9))

    return list_of_ge_slots


# Swaps from history to exchange tab or examines money to reset the logout timer
# TODO: Change this to just right click somewhere. Commeting out for testing.
@calc_break
def prevent_logout(top_left_corner, bottom_right_corner, runescape_window):
    pass
    # seed = random.random()
    # x, y = pyautogui.size()
    # if seed > 0.5:  # opens up the sale history tab for 5 seconds then returns to ge tab
    #     while (True):
    #         move_mouse_to(random.randint(0, x), random.randint(0, y))
    #         # we will never break out of this loop if this image is not found
    #         if len(list(pyautogui.locateAllOnScreen(gui.history_button, region=(
    #                 top_left_corner[0], top_left_corner[1], bottom_right_corner[0] - top_left_corner[0],
    #                 bottom_right_corner[1] - top_left_corner[1])))) > 0:
    #             # we will never break out of this loop if this is not found
    #             move_mouse_to_box(gui.history_button, top_left_corner, bottom_right_corner)
    #             pyautogui.click()
    #             time.sleep(9 * random.random() + 1)
    #
    #             move_mouse_to_box(gui.exchange_button, top_left_corner, bottom_right_corner)
    #             pyautogui.click()
    #             break
    #         else:
    #             print('Could not find sales history button, broke to prevent infinite loop')
    #             break
    # else:  # examines the money pouch
    #     examine_money(bottom_right_corner)


if __name__ == '__main__':
    main()
