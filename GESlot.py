import pyautogui
import time
import numpy
import random
import screenshots as gui
import datetime
import numpy as np

from Custom_Modules.realmouse import move_mouse_to
from Custom_Modules import pointfrombox
from utilities.utils import box_to_region, get_image_of_region


class GESlot:

    def __init__(self, region, runescape_instance):
        self.location_object = GESlotRegion(region)
        self.buy_or_sell = None
        self.item = None
        self.runescape_instance = runescape_instance
        self.image_object = GESlotItemImage(self.region)

    @property
    def region(self):
        return self.location_object.region

    @property
    def top_left_corner(self):
        return self.region.top_left_corner

    @property
    def bottom_right_corner(self):
        return self.region.bottom_right_corner

    @property
    def image_of_slot(self):
        return self.image_object.image

    @property
    def time_of_last_screenshot(self):
        return self.image_object.time_of_last_screenshot

    def location(self):
        return self.location_object.location

    def update_buy_or_sell_state(self, state):
        self.buy_or_sell = state
        self.item.set_current_state(state)

    def set_item_in_ge_slot(self, item_instance):
        self.item = item_instance
        self.item.ge_slot = self

    def set_image_of_slot(self):
        self.image_object.set_new_image()
        self.image_object.set_time_of_last_screenshot()
        print('Image of {} has been updated'.format(self.item.item_name))

    def reset_slot(self):
        self.update_buy_or_sell_state(None)
        self.item.ge_slot = None
        self.item = None


class GESlotItemImage:

    def __init__(self, ge_slot_region):
        self.ge_slot_region = ge_slot_region
        self.width = 165
        self.height = 10
        self.offset_from_left_corner = 90
        self.image = None
        self.time_of_last_screenshot = None

    @property
    def region(self):
        top, left, *rest = self.ge_slot_region
        return top, left + self.offset_from_left_corner, self.width, self.height

    def set_new_image(self):
        self.image = get_image_of_region(region=self.region)

    def set_time_of_last_screenshot(self):
        self.time_of_last_screenshot = datetime.datetime.now()


class GESlotRegion:

    def __init__(self, region):
        self.region = region

    @property
    def top_left_corner(self):
        return self.region[0], self.region[1]

    @property
    def bottom_right_corner(self):
        left, top, width, height = self.region
        return left + width, top + height

    @property
    def location(self):
        location = pointfrombox.random_point(self.top_left_corner, self.bottom_right_corner)
        return location

