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


def slot_is_empty(ge_slot):
    if pyautogui.locateOnScreen(gui.empty_collect_slot, region=ge_slot.runescape_instance.region) is None:
        return True
    return False


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

    def reset_slot(self):
        self.update_buy_or_sell_state(None)
        # self.item.set_price_instant_bought_at(None)
        # self.item.set_price_instant_sold_at(None)
        self.set_item_in_ge_slot(None)

    def collect_items_and_return_price(self):
        self.open_ge_slot()
        price = check_price(self.loc_price)

        if not slot_is_empty(self.ge_slot):
            self.collect_2()

        self.collect_1()
        wait_for(gui.view_all_offers, self.runescape_instance)

        return price
