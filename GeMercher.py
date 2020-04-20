import operator
import pandas as pd
import pyautogui
import time
import pickle
import random
import screenshots as gui
import datetime
import numpy as np

from GESlot import record_transaction, collect_items_from_ge_slot
from RunescapeWindow import RunescapeWindow
from utilities.utils import wait_for, move_mouse_to_image_within_region, random_typer, screengrab_as_numpy_array, \
    tesser_quantity_image


def load_previous_items():
    """
    Loads a dict of previously used items if it exists. Starts an empty list if not.
    :return: list
    """
    try:
        with (open("list_of_items_in_use.txt", "rb")) as openfile:
            list_of_items_in_use = pickle.load(openfile)
    except IOError:
        list_of_items_in_use = []

    return list_of_items_in_use


def find_slots_with_state(state_img, runescape_window):
    """
    Finds ge_slots in a window with a state matching the supplied screenshot
    :param state_img: A screenshot of the desired state
    :param runescape_window: a runescape window
    :return: None or a generator object of slots with the desired state
    """
    for ge_slot in runescape_window.list_of_ge_slots:
        desired_state = pyautogui.locateOnScreen(state_img, region=ge_slot.region)
        if desired_state is not None:
            yield ge_slot
        else:
            continue
    return None


def clear_completed_offers(runescape_windows, scores_valid):
    # TODO: This function is doing more than one thing
    for runescape_window in runescape_windows:
        for ge_slot in find_slots_with_state(gui.completed_ge_slot, runescape_window):
            price = collect_items_from_ge_slot(ge_slot)
            # mark score invalid if the offer completed outside of script runtime
            if not scores_valid:
                ge_slot.item.set_score_invalid()

            if ge_slot.buy_or_sell == 'buy':
                record_transaction(ge_slot=ge_slot, qty=ge_slot.item.quantity_to_buy, price=price, action='Buy')
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


def fill_empty_slots(script):
    # TODO: This function does more than one thing
    # IF I have a pickled file I should verify whether its good or not
    empty_slots = []
    for instance in sorted(script.runescape_windows, key=operator.attrgetter('money')):
        for ge_slot in instance.list_of_ge_slots:
            if ge_slot.buy_or_sell is None and ge_slot.runescape_instance.items_available():
                empty_slots.append(ge_slot)

    if not empty_slots:
        print('No empty GE slots found or no items available')
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

    previous_total_profit = None
    # TODO: Find better way to pickle whole state

    while True:
        print('Loop started')
        # TODO: Is this clearing offers that completed during script downtime?
        clear_completed_offers(runescape_windows=merchant.runescape_windows, scores_valid=merchant.score_items)
        if not merchant.score_items:
            print('Loaded from save: Previous scores are being marked as invalid and will not effect ratings')
            merchant.score_items = True
        fill_empty_slots(script=merchant)

        # Check in process offers
        in_process_offers = [ge_slot
                             for instance in merchant.runescape_windows
                             for ge_slot in instance.list_of_ge_slots
                             if ge_slot.buy_or_sell is not None]

        for ge_slot in in_process_offers:
            # TODO: This feature needs a complete re-write & verification that it works
            # Check if the old screenshot is the same as the current state
            if not (ge_slot.image_of_slot == np.array(pyautogui.screenshot(
                    region=(ge_slot.top_left_corner[0], ge_slot.top_left_corner[1] + 90, 165, 10)))).all():
                ge_slot.set_image_of_slot()
            elif datetime.datetime.now() - ge_slot.time_of_last_screenshot > 1800:
                print('Image of {} has not been updated in 30 minutes so we are aborting the offer'.format(
                    ge_slot.item.item_name))
                # run cancel offer code
                # first we cancel the offer
                # print('We are about to cancel an offer that we believe to be in the window with coords {}, we are at line 287'.format(runescape_window.bottom_right_corner))
                cancel_offer(ge_slot.top_left_corner)
                wait_for(gui.offer_canceled, ge_slot.runescape_instance)
                print("Cancelled {} since the offer hasn't been updated in a while".format(
                    ge_slot.item.item_name))
                # then if the item was a buy we handle it
                if ge_slot.buy_or_sell == 'buy':
                    handle_cancelling_buy(ge_slot.runescape_instance, ge_slot, ge_slot.runescape_instance.items_in_use)
                elif ge_slot.buy_or_sell == 'sell':
                    handle_cancelling_sell(ge_slot, ge_slot.runescape_instance.items_in_use)
                # we check if any of the item  bought and if so try to sell it
                # we could check the sale history to read the number of items bought and update accordingly
                # then if it was a sell we handle it
                # we would simply retrieve the items and money and update accordingly, then find the new sell price and sell
                break_check = True
            elif time.time() - ge_slot.time_of_last_screenshot > 3600 and ge_slot.buy_or_sell == 'sell':
                print('Image of {} has not been updated in 1 hour so we are aborting the offer'.format(
                    ge_slot.item.item_name))
                # run cancel offer code
                # first we cancel the offer
                # print('We are about to cancel an offer that we believe to be in the window with coords {}, we are at line 287'.format(runescape_window.bottom_right_corner))
                cancel_offer(ge_slot.top_left_corner)
                wait_for(gui.offer_canceled, ge_slot.runescape_instance)
                # print("Cancelled {} since the offer hasn't been updated in a while".format(ge_slot.item.item_name))
                handle_cancelling_sell(ge_slot, ge_slot.runescape_instance.items_in_use)
                # we check if any of the item  bought and if so try to sell it
                # we could check the sale history to read the number of items bought and update accordingly
                # then if it was a sell we handle it
                # we would simply retrieve the items and money and update accordingly, then find the new sell price and sell
                break_check = True
            elif time.time() - ge_slot.time_of_last_screenshot > 5400 and ge_slot.buy_or_sell == 'buy':
                print('Image of {} has not been updated in 1.5 hours so we are aborting the offer'.format(
                    ge_slot.item.item_name))
                # run cancel offer code
                # first we cancel the offer
                # print('We are about to cancel an offer that we believe to be in the window with coords {}, we are at line 287'.format(runescape_window.bottom_right_corner))
                cancel_offer(ge_slot.top_left_corner)
                wait_for(gui.offer_canceled, ge_slot.runescape_instance)

                # print("Cancelled {} since the offer hasn't been updated in a while".format(ge_slot.item.item_name))
                handle_cancelling_buy(ge_slot.runescape_instance, ge_slot, ge_slot.runescape_instance.items_in_use)
                # we check if any of the item  bought and if so try to sell it
                # we could check the sale history to read the number of items bought and update accordingly
                # then if it was a sell we handle it
                # we would simply retrieve the items and money and update accordingly, then find the new sell price and sell
    #             break_check = True
    #     if break_check:
    #         break
    # if break_check:
    #     break
    # time_of_last_update_check = time.time()
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


class Merchant:

    def __init__(self):

        self.transaction_record = pd.DataFrame(columns=['Item', 'Timestamp', 'Action', 'Qty', 'Price', 'Msg', 'Score'])
        self.runescape_windows = None
        self.start_time = datetime.datetime.now()
        self.score_items = None
        self.time_last_save = datetime.datetime.now()

    def detect_windows(self):
        runescape_windows = detect_runescape_windows(self)
        if not runescape_windows:
            print("Could not detect a Runescape Window, script aborting")
            quit()
        else:
            print(f'We have detected {len(runescape_windows)} window(s)')
        self.runescape_windows = runescape_windows

    def set_time_last_save(self):
        self.time_last_save = datetime.datetime.now()

    def load_transaction_record(self):
        try:
            with (open("transaction_record.csv", "rb")) as openfile:
                self.transaction_record = pd.read_csv(openfile)
        except IOError:
            print("No prior transaction record found")

    def save_transaction_record(self):
        with (open("transaction_record.csv", "w")) as openfile:
            self.transaction_record.to_csv(openfile)

    def add_transaction(self, item, action, qty, price, score):
        self.transaction_record = self.transaction_record.append(
            {'Item': item.item_name,
             'Timestamp': datetime.datetime.now(),
             'Action': action, 'Qty': qty,
             'Price': price,
             'Score': score}, ignore_index=True)
        self.save_transaction_record()


def handle_cancelling_sell(ge_slot, list_of_items_in_use):
    # TODO: Rewrite or eliminate
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
    # TODO: Rewrite or delete
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

    print(f'Buying: {ge_slot.item.item_name} At Price Each: {ge_slot.item.price_instant_sold_at}')

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


if __name__ == '__main__':
    main()
