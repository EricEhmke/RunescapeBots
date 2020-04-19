import pyautogui
import time
import numpy
import random
import screenshots as gui
import datetime
import numpy as np

from Custom_Modules.realmouse import move_mouse_to
from Custom_Modules import pointfrombox
from utilities.utils import wait_for, move_mouse_to_image_within_region, random_typer, calc_break,\
    screengrab_as_numpy_array, tesser_price_image, check_price


def calc_score(qty, price, time_order_placed):
    return (qty * price) / (datetime.datetime.now() - time_order_placed).seconds


# TODO: This can probably be refined to make it static or a class method
def record_transaction(ge_slot, qty, price, action, score=np.nan):
    if action in ['Sell']:
        score = calc_score(qty=qty, price=price, time_order_placed=ge_slot.item.time_buy_order_placed)
    ge_slot.runescape_instance.GEMerch.add_transaction(
        item=ge_slot.item, action=action, qty=qty, price=price, score=score)


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
    # Collect the gold
    is_slot_empty = pyautogui.locateOnScreen(gui.empty_collect_slot, region=ge_slot.runescape_instance.region)

    if is_slot_empty is None:
        ge_slot.collect_2()

    ge_slot.collect_1()
    wait_for(gui.view_all_offers, ge_slot.runescape_instance)

    return price


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