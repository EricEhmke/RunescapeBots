import os
import time
import random
import functools
import datetime

import pyautogui

from Custom_Modules.realmouse import move_mouse_to


# from RunescapeBots.GeMercher import examine_money, runescape_instance


# def prevent_logout(top_left_corner, bottom_right_corner, runescape_window):
#     seed = random.random()
#     x, y = pyautogui.size()
#     if seed > 0.5:  # opens up the sale history tab for 5 seconds then returns to ge tab
#         while (True):
#             realmouse.move_mouse_to(random.randint(0, x), random.randint(0, y))
#             if len(list(pyautogui.locateAllOnScreen('Tools/screenshots/sale_history_button.png', region=(
#                     top_left_corner[0], top_left_corner[1], bottom_right_corner[0] - top_left_corner[0],
#                     bottom_right_corner[1] - top_left_corner[1])))) > 0:
#                 move_mouse_to_box('Tools/screenshots/sale_history_button.png', top_left_corner, bottom_right_corner)
#                 pyautogui.click()
#                 time.sleep(9 * random.random() + 1)
#                 move_mouse_to_box('Tools/screenshots/grand_exchange_button.png', top_left_corner, bottom_right_corner)
#                 pyautogui.click()
#                 break
#     else:  # examines the money pouch
#         examine_money(bottom_right_corner)

class HumanBreaks:
    # TODO: This should be tied to a runescape instance
    def __init__(self, func, start_time=datetime.datetime.now()):
        functools.update_wrapper(self, func)
        self.func = func
        self.time_of_last_break = start_time
        self.time_of_last_action = None

    def __call__(self, instance, *args, **kwargs):
        self.calc_break()
        return self.func(instance, *args, **kwargs)

    def __get__(self, instance, owner):
        self.calc_break()
        return functools.partial(self, instance)

    def calc_break(self):
        self.time_of_last_action = datetime.datetime.now()
        time_delta = self.time_of_last_action - self.time_of_last_break
        print(time_delta)
        if (time_delta.seconds / 60) > 20:
            sleep_short = 90
            sleep_long = 280
            time_to_sleep = random.randint(sleep_short, sleep_long)
            time.sleep(time_to_sleep)
            self.time_of_last_break = datetime.datetime.now()
        else:
            if random.random() > .95:
                time.sleep(random.random() + random.randint(1, 10))
            elif random.random() < .3:
                time.sleep(random.random() + 1)
            else:
                time.sleep(random.random() + .5)

    def set_time_of_last_action(self):
        self.time_of_last_action = datetime.datetime.now()

# Types a word at a random speed for each letter
def random_typer(word):
    for letter in word:
        pyautogui.typewrite(letter.lower(), interval=random.random() / 4)


# module to return a random point from a box
# This should be a circle with points being weighted from center
def random_point(top_left, bottom_right):
    x = random.randint(top_left[0], bottom_right[0])
    y = random.randint(top_left[1], bottom_right[1])

    return x, y


# Locates an image on screen and moves the mouse to a random point within that image
def move_mouse_to_image_within_region(image, region=None):
    """
    # Locates an image on screen and moves the mouse to a random point within that image.
    """
    image_loc = pyautogui.locateOnScreen(image, region=region)

    while image_loc is None:
        image_loc = pyautogui.locateOnScreen(image, region=region)

    point_to_click = random_point((image_loc[0], image_loc[1]),
                                  (image_loc[0] + image_loc[2], image_loc[1] + image_loc[3]))

    move_mouse_to(point_to_click[0], point_to_click[1])


def move_mouse_to_box(image_of_box, top_left_corner, bottom_right_corner):
    box_to_click = pyautogui.locateOnScreen(image_of_box)
    random_x = random.randint(0, box_to_click[2])
    random_y = random.randint(0, box_to_click[3])
    move_mouse_to(box_to_click[0] + random_x, box_to_click[1] + random_y)


def wait_for(image, runescape_window):
    # adding a possible failsafe in here
    time_entered = time.time()
    # time_entered = time()
    # could add a failsafe in here incase we misclick or something, this
    # should be something to come back to
    failsafe_count = 0
    while (True):
        found = pyautogui.locateOnScreen(image)
        if found != None:
            break

        elif failsafe_count > 10:
            print("We can't seem to fix the problem so the script is now aborting")
            quit()
        # If the image can't be found it moves the mouse in case the mouse is over the image.
        elif time.time() - time_entered > 5:
            # elif time() - time_entered > 5:
            failsafe_count += 1
            print('We appear to be stuck so attempting to move the mouse and see if this fixes it')
            # print('For debug:')
            # print(runescape_window.bottom_right_corner[0], runescape_window.top_left_corner[0])
            # print(runescape_window.bottom_right_corner[1], runescape_window.top_left_corner[1])
            move_mouse_to(
                random.randint(runescape_window.top_left_corner[0], runescape_window.bottom_right_corner[0]),
                random.randint(runescape_window.top_left_corner[1], runescape_window.bottom_right_corner[1]))
            # pyautogui.click()
            time_entered = time.time()


# This probably belongs here in a more generalized form
# def check_if_image_exists(item_name):
#     global client_version
#     file_name = 'Tools/screenshots/items/' + client_version + '_items/' + item_name.replace(' ', '_') + '.png'
#     if os.path.isfile(file_name):
#         return (file_name)
#     else:
#         print(
#             'You do not have an image file for {} so the script is aborting.'.format(
#                 item_name, item_name))

def members_status_check(top_left_corner, bottom_right_corner):
    width = bottom_right_corner[0] - top_left_corner[0]
    height = bottom_right_corner[1] - top_left_corner[1]
    if len(list(pyautogui.locateAllOnScreen('Tools/screenshots/non_mems_slot.png',
                                            region=(top_left_corner[0], top_left_corner[1], width, height)))) != 0:
        return (False)
    else:
        return (True)

# def move_and_resize_runescape_windows():
#     pass  # this will move and resize the detected windows.
# # Initially this will just pass since we don't know how to do this, but
# # further down the road we can add to this and implement it
