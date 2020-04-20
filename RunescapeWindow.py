import datetime
import pyautogui
import screenshots as gui

from GESlot import GESlot
from Custom_Modules import items_to_merch_module
from Custom_Modules import gelimitfinder
from item import Item
from Custom_Modules import pointfrombox
from Custom_Modules.realmouse import move_mouse_to
from utilities.utils import calc_break, tesser_money_image, tesser_price_image, screengrab_as_numpy_array


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
    width = bottom_right_corner[0] - top_left_corner[0]
    height = bottom_right_corner[1] - top_left_corner[1]
    # Commenting out the region arg for testing
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
    for i in count_ge_slots(top_left_corner, bottom_right_corner):
        ge_slots.append(GESlot(((i[0], i[1]), (i[0] + i[2], i[1] + i[3])), runescape_window))
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
        self.money = 100_000
        self.profit = 0
        self.time_of_last_break = datetime.datetime.now()
        # TODO: Change this to a simple left click or somthing According to authoer this is here just to make sure game doesn log out. Commented out just for testing
        # examine_money(position)
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
                (item.meets_profit_threshold() or item.is_aged())]
