import datetime
import random

import pyautogui
import screenshots as gui
import time

from GESlot import GESlot
from Custom_Modules import items_to_merch_module
from Custom_Modules import gelimitfinder
from item import Item
from Custom_Modules import pointfrombox
from Custom_Modules.realmouse import move_mouse_to
from utilities.utils import calc_break, tesser_money_image, tesser_price_image, screengrab_as_numpy_array, \
    move_mouse_to_image_within_region, random_typer, wait_for, check_price


class RunescapeWindow:

    def __init__(self, position, parent_script):
        self.bottom_right_corner = position
        self.top_left_corner = (position[0] - 482, position[1] - 304)
        self.region = (self.top_left_corner[0], self.top_left_corner[1], 484, 303)
        self.member_status = True
        self.loc_price = (self.bottom_right_corner[0] - 396, self.bottom_right_corner[1] - 61), \
                         (self.bottom_right_corner[0] - 179, self.bottom_right_corner[1] - 28)

        self.list_of_ge_slots = initialise_ge_slots(self.top_left_corner, self.bottom_right_corner, self)
        # TODO: Fix the money detection
        # self.money = detect_money(self.top_left_corner, self.bottom_right_corner) TESSER NEEDS FIXING
        self.money = 100_000
        self.profit = 0
        self.time_of_last_break = datetime.datetime.now()
        self.items_to_merch = items_to_merch(self.member_status, self)
        self.number_of_empty_ge_slots = empty_ge_slot_check(self.list_of_ge_slots)
        self.items_in_use = [ge_slot.item for ge_slot in self.list_of_ge_slots]

        print('Initialised a window with {}Kgp and {} ge slots'.format(int(self.money / 1000),
                                                                       self.number_of_empty_ge_slots))

        self.loc_inventory_item = (self.bottom_right_corner[0] + 64, self.bottom_right_corner[1] - 107), \
                                  (self.bottom_right_corner[0] + 88, self.bottom_right_corner[1] - 84)
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
                (item.meets_profit_threshold() or item.price_is_outdated())]

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
        move_mouse_to(*ge_slot.location())
        pyautogui.click()
        wait_for(gui.completed_offer, self)

    @calc_break
    def select_buy_bag(self, ge_slot):
        move_mouse_to_image_within_region(gui.buy_bag, ge_slot.region)
        pyautogui.click()

    @calc_break
    def select_sell_bag(self, ge_slot):
        move_mouse_to_image_within_region(gui.sell_bag, ge_slot.region)
        pyautogui.click()

    def collect_items_and_return_price(self, ge_slot):
        self.open_ge_slot(ge_slot)
        price = check_price(self.loc_price)

        if item_in_slot(self.region):
            self.collect_2()

        self.collect_1()
        wait_for(gui.view_all_offers, self)

        return price


def item_in_slot(slot_region):
    # TODO: Need to verify the region is correct
    if pyautogui.locateOnScreen(gui.empty_collect_slot, region=slot_region) is None:
        return True
    return False


@calc_break
def prevent_logout(top_left_corner, bottom_right_corner, runescape_window):
    # TODO: Rewrite this to simple right click at a random point.
    pass


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


def empty_ge_slot_check(list_of_ge_slots):
    number_of_ge_slots_open = 0
    for slot in list_of_ge_slots:
        if slot.buy_or_sell is None:
            number_of_ge_slots_open += 1
    return number_of_ge_slots_open


def initialise_ge_slots(top_left_corner, bottom_right_corner, runescape_window):
    ge_slots = []
    for found_slot_region in count_ge_slots(top_left_corner, bottom_right_corner):
        ge_slots.append(GESlot(region=found_slot_region, runescape_instance=runescape_window))
    return ge_slots


def detect_money(top_left_corner, bottom_right_corner):
    # TODO: Update this screenshot. Function currently unused.
    money_icon_path = 'Tools/screenshots/money_icon.png'
    money_icon_loc = pyautogui.locateOnScreen(money_icon_path, region=(
        top_left_corner[0], top_left_corner[1], bottom_right_corner[0] - top_left_corner[0],
        bottom_right_corner[1] - top_left_corner[1]))
    money_val_loc = (money_icon_loc[0] + 22, money_icon_loc[1], money_icon_loc[0] + 100, money_icon_loc[1] + 18)
    image = screengrab_as_numpy_array(money_val_loc)
    money_val = tesser_money_image(image)
    return money_val


