import datetime
import operator
import random
from collections import deque

import pyautogui
import screenshots as gui
import time

from GESlot import GESlot
from Custom_Modules import items_to_merch_module
from Custom_Modules import gelimitfinder
from item import Item
from Custom_Modules import pointfrombox
from Custom_Modules.realmouse import move_mouse_to
from utilities.utils import calc_break, screengrab_as_numpy_array, \
    move_mouse_to_image_within_region, random_typer, wait_for, check_price, check_quantity, calc_score


class RunescapeWindow:

    def __init__(self, position, parent_script):
        self.bottom_right_corner = position
        self.top_left_corner = (position[0] - 482, position[1] - 304)
        self.region = (self.top_left_corner[0], self.top_left_corner[1], 484, 303)
        self.member_status = True
        self.loc_price = (self.bottom_right_corner[0] - 396, self.bottom_right_corner[1] - 61), \
                         (self.bottom_right_corner[0] - 179, self.bottom_right_corner[1] - 28)

        self.list_of_ge_slots = initialise_ge_slots(self.top_left_corner, self.bottom_right_corner, self)
        self.money = 100_000
        self.profit = 0
        self.time_of_last_break = datetime.datetime.now()
        self.items_to_merch = items_to_merch(self.member_status, self)
        self.items_in_use = [ge_slot.item for ge_slot in self.list_of_ge_slots]

        print('Initialised a window with {}Kgp and {} ge slots'.format(int(self.money / 1000),
                                                                       len(self.empty_ge_slots())))

        self.loc_inventory_item = (self.bottom_right_corner[0] + 64, self.bottom_right_corner[1] - 107), \
                                  (self.bottom_right_corner[0] + 88, self.bottom_right_corner[1] - 84)
        self.loc_collection_box_gp = (self.bottom_right_corner[0] - 105, self.bottom_right_corner[1] - 51), \
                                     (self.bottom_right_corner[0] - 71, self.bottom_right_corner[1] - 21)
        self.loc_collection_box_item = (self.bottom_right_corner[0] - 55, self.bottom_right_corner[1] - 51), \
                                       (self.bottom_right_corner[0] - 20, self.bottom_right_corner[1] - 21)
        self.GEMerch = parent_script

    def empty_ge_slots(self):
        return deque([ge_slot for ge_slot in self.list_of_ge_slots if ge_slot.item is None])

    def empty_ge_slot(self):
        assert self.empty_ge_slots()
        return self.empty_ge_slots().popleft()

    def transaction_record(self):
        return self.GEMerch.transaction_record

    def update_profit(self, amount):
        self.profit = self.profit + amount

    def update_money(self, amount):
        self.money += amount

    @calc_break
    def select_inventory_item(self):
        item_location = pointfrombox.random_point(*self.loc_inventory_item)
        move_mouse_to(item_location[0], item_location[1])
        pyautogui.click()

    @property
    def items_available(self):
        return [item for item in self.items_to_merch if
                item.qty_available_to_buy() <= item.limit
                and
                item.current_state is None
                and
                (item.meets_profit_threshold() or item.price_is_outdated())]

    @property
    def best_item_available(self):
        return max(self.items_available, key=operator.methodcaller('score'))

    @calc_break
    def enter_price(self, price):
        move_mouse_to_image_within_region(gui.enter_price_box, region=(
            self.region[0] + 243, self.region[1] + 134, 221, 76))
        pyautogui.click()
        time.sleep(1 + random.random())
        random_typer(str(price))
        time.sleep(random.random() + .25)
        pyautogui.press('enter')

    # TODO: find a better way to handle the region so this is not static
    @calc_break
    def enter_quantity(self, quantity):
        move_mouse_to_image_within_region(gui.enter_quantity_box, region=(
            self.region[0] + 22, self.region[1] + 134, 221, 76))
        pyautogui.click()
        time.sleep(.5 + random.random())
        random_typer(str(quantity))
        time.sleep(random.random() + .25)
        pyautogui.press('enter')

    @calc_break
    def collect_1(self):
        top_left, bottom_right = pointfrombox.random_point(*self.loc_collection_box_gp)
        move_mouse_to(top_left, bottom_right)
        pyautogui.click()

    @calc_break
    def collect_2(self):
        top_left, bottom_right = pointfrombox.random_point(*self.loc_collection_box_item)
        move_mouse_to(top_left, bottom_right)
        pyautogui.click()

    @calc_break
    def confirm_offer(self):
        move_mouse_to_image_within_region(gui.confirm_offer, self.region)
        pyautogui.click()

    @calc_break
    def open_ge_slot(self, ge_slot):
        move_mouse_to(*ge_slot.location)
        pyautogui.click()

    @calc_break
    def select_buy_bag(self, ge_slot):
        move_mouse_to_image_within_region(gui.buy_bag, ge_slot.region)
        pyautogui.click()

    @calc_break
    def select_sell_bag(self, ge_slot):
        move_mouse_to_image_within_region(gui.sell_bag, ge_slot.region)
        pyautogui.click()

    @calc_break
    def select_abort_offer(self, ge_slot):
        move_mouse_to_image_within_region(gui.abort_offer, region=ge_slot.region)
        pyautogui.click()

    def collect_items_and_return_price(self, ge_slot):
        self.open_ge_slot(ge_slot)
        price = check_price(self.loc_price)

        if item_in_slot(self.region):
            self.collect_2()

        self.collect_1()
        wait_for(gui.view_all_offers, self)

        return int(price)

    def collect_items(self):
        if item_in_slot(self.region):
            self.collect_2()

        self.collect_1()
        wait_for(gui.view_all_offers, self)

    def cancel_offer(self, ge_slot):
        self.open_ge_slot(ge_slot)
        self.select_abort_offer(ge_slot)
        wait_for(gui.offer_canceled, ge_slot.runescape_instance)
        quantity = check_quantity(self.loc_price) # You bought/sold a qty X
        price_per_item = check_price(self.loc_price) # For a total price of Y
        total_price = quantity * price_per_item
        self.GEMerch.add_transaction(item=ge_slot.item, action=ge_slot.item.current_state, qty=quantity,
                                     price=price_per_item)
        # If this is a buy offer, how much $ did I put into the slot originally?
        # then money += original_offer_amt - (qty_bought * price_per_item)
        # new_qty_to_sell = qty_bought
        # sell items at current sell price or check new buy price
        if ge_slot.item.current_state == 'buy':
            ge_slot.item.qty_in_inventory = quantity
            ge_slot.runescape_instance.money += ge_slot.item.money_in_process - total_price
            ge_slot.item.money_in_process = 0
            ge_slot.item.reset_item_and_slot()
            if quantity > 0:
                ge_slot.item.sell_items(price=ge_slot.item.buy_price)
        # If this is a sell offer, how many items did I originally try to sell?
        # new_qty_to_sell = original_qty_to_sell (quantity in process - quantity
        # then money += price_per_item * qty
        # sell items at original buy price to just unload or check new buy price
        if ge_slot.item.current_state == 'sell':
            ge_slot.runescape_instance.money += quantity * price_per_item
            ge_slot.item.money_in_process = 0
            ge_slot.item.qty_in_inventory += ge_slot.item.qty_in_process - quantity
            ge_slot.item.sell_items(price=ge_slot.item.buy_price)

        self.collect_items()

        ge_slot.item.reset_item_and_slot()

    def cancel_sell_offer(self, ge_slot):
        self.open_ge_slot(ge_slot)
        self.select_abort_offer(ge_slot)
        wait_for(gui.offer_canceled, ge_slot.runescape_instance)


def item_in_slot(slot_region):
    if pyautogui.locateOnScreen(gui.empty_collect_slot, region=slot_region) is None:
        return True
    return False


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


def count_ge_slots(top_left_corner, bottom_right_corner):
    width = abs(bottom_right_corner[0] - top_left_corner[0])
    height = abs(bottom_right_corner[1] - top_left_corner[1])
    list_of_ge_slots = list(
        pyautogui.locateAllOnScreen(gui.ge_open_slot, region=(top_left_corner[0], top_left_corner[1], width, height),
                                    confidence=0.9))

    return list_of_ge_slots


def initialise_ge_slots(top_left_corner, bottom_right_corner, runescape_window):
    ge_slots = []
    for found_slot_region in count_ge_slots(top_left_corner, bottom_right_corner):
        ge_slots.append(GESlot(region=found_slot_region, runescape_instance=runescape_window))
    return ge_slots



