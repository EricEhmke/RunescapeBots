import time
import random
import datetime
import numpy as np
import cv2
import pytesseract
import re
import pyautogui
import PIL


from Custom_Modules.realmouse import move_mouse_to


def get_image_of_region(region):
    return np.array(pyautogui.screenshot(region=region))


def calc_score(qty, price, time_order_placed):
    return (qty * price) / (datetime.datetime.now() - time_order_placed).seconds


def box_to_region(top_left_corner, bottom_right_corner):
    """

    :param top_left_corner: coordinates of the top left corner of a box
    :param bottom_right_corner: coordinates of the top left corner of a box
    :return: a pyautogui region
    """
    left = top_left_corner[0]
    top = top_left_corner[1]
    width = bottom_right_corner[0] - top_left_corner[0]
    height = bottom_right_corner[1] - top_left_corner[1]
    return left, top, width, height


def check_price(location):
    """
    A function that reads a price from the screen via Tesseract OCR
    :param location: X, Y coords of the upper right and lower left hand corners of the area to be read
    :return: int
    """
    numpy_array = screengrab_as_numpy_array(location)
    quantity, cost = tesser_price_image(numpy_array)
    return int(quantity) / int(cost)


def check_quantity(location):
    """
    A function that reads a price from the screen via Tesseract OCR
    :param location: X, Y coords of the upper right and lower left hand corners of the area to be read
    :return: int
    """
    numpy_array = screengrab_as_numpy_array(location)
    quantity, cost = tesser_price_image(numpy_array)
    return quantity


def tesser_price_image(image):
    # TODO: Refactor this to return both the quantity and price of the item.
    # Enlarge image for easier processing
    image = cv2.resize(src=image, dsize=None, fx=5, fy=5)
    # Convert image to grayscale
    image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    # Apply a threshold to change to complete black or white
    retval, image = cv2.threshold(image, 100, 255, cv2.THRESH_BINARY)
    # Invert image so text is black on white
    image = 255 - image

    # TODO: This needs to be improved. Has trouble with 4, vs 9 and 6
    txt = pytesseract.image_to_string(image, lang='eng', config='--psm 6')
    txt = txt.replace(",", "")
    txt = re.findall(r'\d+', txt)
    quantity, cost = txt[1], txt[0]
    return quantity, cost


def screengrab_as_numpy_array(location):
    """
    Takes a screenshot at provided location and returns screenshot as a numpy array
    :param location: x,y location points of bottom left and top right corners of an area on screen
    :return: numpy.array
    """
    # top_left, bottom_right = location
    # width = top_left[0] - top_left[1]
    # height = bottom_right[1] - top_left[1]
    region = box_to_region(*location)
    im = np.array(pyautogui.screenshot(region=region))
    return im


def calc_break(func):
    """
    A decorator function that puts a random delay between tasks or begins an extended break
    :param func: decorated function
    :return: the decorated function after a random break
    """

    def wrapper(self, *args, **kwargs):
        time_of_last_action = datetime.datetime.now()
        time_delta = time_of_last_action - self.time_of_last_break

        if (time_delta.seconds / 60) > 20:
            sleep_short = 2
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
        return func(self, *args, **kwargs)

    return wrapper


# Types a word at a random speed for each letter
def random_typer(word):
    for letter in word:
        pyautogui.typewrite(letter.lower(), interval=random.random() / 4)


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
            move_mouse_to(
                random.randint(runescape_window.top_left_corner[0], runescape_window.bottom_right_corner[0]),
                random.randint(runescape_window.top_left_corner[1], runescape_window.bottom_right_corner[1]))
            # pyautogui.click()
            time_entered = time.time()


def members_status_check(top_left_corner, bottom_right_corner):
    width = bottom_right_corner[0] - top_left_corner[0]
    height = bottom_right_corner[1] - top_left_corner[1]
    if len(list(pyautogui.locateAllOnScreen('Tools/screenshots/non_mems_slot.png',
                                            region=(top_left_corner[0], top_left_corner[1], width, height)))) != 0:
        return (False)
    else:
        return (True)


def percent_of(buy_price, sell_price):
    return 1 - (buy_price / sell_price)
