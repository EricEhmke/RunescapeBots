import pyautogui
import datetime
import numpy as np


from Custom_Modules import pointfrombox
from utilities.utils import box_to_region, get_image_of_region


class GESlot:

    def __init__(self, region, runescape_instance):
        self.region = region
        self.runescape_instance = runescape_instance
        self.image = None
        self.item = None
        self.time_of_last_screenshot = None

    @property
    def top_left_corner(self):
        return self.region[0], self.region[1]

    @property
    def bottom_right_corner(self):
        left, top, width, height = self.region
        return left + width, top + height

    @property
    def image_is_current(self):
        return self.image == np.array(pyautogui.screenshot(region=self.region)).all()

    @property
    def offer_is_aged(self):
        return datetime.datetime.now() - self.time_of_last_screenshot > self.runescape_instance.GEMerch.max_offer_age_seconds

    @property
    def location(self):
        location = pointfrombox.random_point(self.top_left_corner, self.bottom_right_corner)
        return location

    @property
    def current_state(self):
        return self.item.current_state if self.item is not None else None

    def set_new_image(self):
        self.image = get_image_of_region(region=self.region)

    def set_time_of_last_screenshot(self):
        self.time_of_last_screenshot = datetime.datetime.now()

    def set_item_in_ge_slot(self, item_instance):
        self.item = item_instance
        self.item.ge_slot = self

    def set_new_image_of_slot(self):
        self.set_new_image()
        self.set_time_of_last_screenshot()
        print(f'Image of {self.item.item_name} has been updated')
