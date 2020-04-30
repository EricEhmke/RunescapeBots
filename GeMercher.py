import operator
import pandas as pd
import pyautogui
import time
import pickle
import random
import screenshots as gui
import datetime
import numpy as np


from RunescapeWindow import RunescapeWindow
from utilities.utils import wait_for, move_mouse_to_image_within_region, random_typer, screengrab_as_numpy_array, \
     check_quantity, calc_score


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


def find_slots_with_state_in_window(state_img, runescape_window):
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


def ge_slot_image_is_current(ge_slot):
    return (ge_slot.image_of_slot == np.array(pyautogui.screenshot(
                    region=(ge_slot.top_left_corner[0], ge_slot.top_left_corner[1] + 90, 165, 10)))).all()


def ge_slot_image_is_aged(ge_slot):
    return datetime.datetime.now() - ge_slot.time_of_last_screenshot > 1800


def detect_runescape_windows():
    return [window for window in pyautogui.locateAllOnScreen(gui.main_ge_window)]


def main():
    merchant = Merchant()
    merchant.initialize_windows()
    merchant.load_transaction_record()

    # TODO: Find better way to pickle whole state

    while True:
        print('Loop started')
        merchant.score_items = True
        merchant.clear_completed_offers()

        if not merchant.score_items:
            print('Loaded from save: Previous scores are being marked as invalid and will not effect ratings')
            merchant.score_items = True

        merchant.fill_empty_slots()
        merchant.check_in_process_offers()

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


class Merchant:

    def __init__(self):

        self.transaction_record = pd.DataFrame(columns=['Item', 'Timestamp', 'Action', 'Qty', 'Price', 'Msg', 'Score'])
        self.runescape_windows = []
        self.start_time = datetime.datetime.now()
        self.score_items = None
        self.time_last_save = datetime.datetime.now()
        self.max_offer_age_seconds = 1800

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

    def add_transaction(self, item, action, qty, price):

        if action in ['Buy', 'Sell']:
            score = calc_score(qty=qty, price=price, time_order_placed=item.time_of_last_pc)
        else:
            score = np.nan

        self.transaction_record = self.transaction_record.append(
            {'Item': item.item_name,
             'Timestamp': datetime.datetime.now(),
             'Action': action, 'Qty': qty,
             'Price': price,
             'Score': score}, ignore_index=True)

        self.save_transaction_record()

    def attach_runescape_windows_to_class(self):
        for window in detect_runescape_windows():
            self.runescape_windows.append(RunescapeWindow((window[0] + window[2], window[1] + window[3]), self))

    def check_for_windows(self):
        """
        Detects the number of Runescape Windows on screen
        :return: a list of Runescape Windows and their locations
        """
        if self.runescape_windows:
            print(f'We have detected {len(self.runescape_windows)} window(s)')
        else:
            print("Could not detect a Runescape Window, script aborting")
            quit()

    def initialize_windows(self):
        self.attach_runescape_windows_to_class()
        self.check_for_windows()

    def clear_completed_offers(self):
        # TODO: This function is doing more than one thing
        for runescape_instance in self.runescape_windows:
            for ge_slot in find_slots_with_state_in_window(gui.completed_ge_slot, runescape_instance):
                item = ge_slot.item
                price = runescape_instance.collect_items_and_return_price(ge_slot)
                # mark score invalid if the offer completed outside of script runtime
                if not self.score_items:
                    item.score_valid = False

                if item.current_state == 'buy':
                    self.add_transaction(item=item, qty=item.quantity_to_buy, price=price, action='Buy')
                    if item.price_is_outdated() and item.qty_available_to_buy() > 0:
                        item.find_current_sell_price()
                    # sell our items at the price instant bought at
                    item.sell_items()

                elif item.current_state == 'sell':
                    runescape_instance.update_money(
                        runescape_instance.money + ((item.quantity_to_buy - 1) * item.sell_price))
                    runescape_instance.update_profit(
                        (item.quantity_to_buy - 2) *
                        (item.sell_price - item.buy_price))
                    self.add_transaction(item=item, qty=item.quantity_to_buy, price=price, action='Sell')
                    print('Total profit made from this window is {}'.format(runescape_instance.profit))

                    # Reset GE slot of next transaction
                    item.reset_item_and_slot()

    def fill_empty_slots(self):
        # TODO: This function does more than one thing
        # IF I have a pickled file I should verify whether its good or not
        empty_slots = []
        for instance in sorted(self.runescape_windows, key=operator.attrgetter('money')):
            for ge_slot in instance.empty_ge_slots():
                empty_slots.append(ge_slot)

        if not empty_slots:
            print('No empty GE slots found or no items available')
            return

        empty_slot = empty_slots[0]

        # If item price_is_outdated() & score < 0 then reset score to 0 and see if its profitable?

        top_item = empty_slot.runescape_instance.best_item_available

        print(f'Top scored item is {top_item.item_name}')
        # Find the current sell price for the item chosen
        wait_for(gui.buy_bag, empty_slot)
        if top_item.price_is_outdated():
            # TODO: Refactor these functions so that they return the price and not set it to the item property
            top_item.find_current_sell_price()
            wait_for(gui.sell_bag, top_item.ge_slot)
            top_item.find_current_buy_price()

            # If this item is profitable, set prices for instant buy and sell

            if top_item.meets_profit_threshold():
                temp = top_item.sell_price
                top_item.set_price_instant_bought_at(top_item.buy_price)
                top_item.set_price_instant_sold_at(temp)

                # If this item has more than 5gp margin then undercut for faster sales
                if top_item.sell_price - top_item.buy_price > 5:
                    top_item.set_price_instant_bought_at(top_item.sell_price - 1)
                    top_item.set_price_instant_sold_at(top_item.buy_price + 1)

            else:
                print('Item does not meet profitability threshold, returning')
                return

        top_item.score_valid = True
        wait_for(gui.buy_bag, top_item.ge_slot)

        quantity = top_item.optimal_max_quantity
        price = top_item.buy_price
        top_item.buy_item(price=price, quantity=quantity)

    def check_in_process_offers(self):
        in_process_offers = [ge_slot
                             for instance in self.runescape_windows
                             for ge_slot in instance.list_of_ge_slots
                             if ge_slot.current_state is not None]

        for ge_slot in in_process_offers:

            if not ge_slot.image_is_current:
                ge_slot.set_new_image_of_slot()

            elif ge_slot.offer_is_aged:
                print('Image of {} has not been updated in 30 minutes so we are aborting the offer'.format(
                    ge_slot.item.item_name))
                # TODO: This chaining is bad
                runescape_instance = ge_slot.runescape_instance

                runescape_instance.cancel_offer(ge_slot)
                wait_for(gui.offer_canceled, runescape_instance)
                print(f"Cancelled {ge_slot.item.item_name} since the offer hasn't been updated in a while")
                # then if the item was a buy we handle it

                # if ge_slot.current_state == 'buy':
                #     handle_cancelling_buy(ge_slot.runescape_instance, ge_slot, ge_slot.runescape_instance.items_in_use)
                # elif ge_slot.current_state == 'sell':
                #     handle_cancelling_sell(ge_slot, ge_slot.runescape_instance.items_in_use)
                # we check if any of the item  bought and if so try to sell it
                # we could check the sale history to read the number of items bought and update accordingly
                # then if it was a sell we handle it
                # we would simply retrieve the items and money and update accordingly, then find the new sell price and sell
                break_check = True


            # elif time.time() - ge_slot.time_of_last_screenshot > 5400 and ge_slot.current_state == 'buy':
            #     print('Image of {} has not been updated in 1.5 hours so we are aborting the offer'.format(
            #         ge_slot.item.item_name))
            #     # run cancel offer code
            #     # first we cancel the offer
            #     # print('We are about to cancel an offer that we believe to be in the window with coords {}, we are at line 287'.format(runescape_window.bottom_right_corner))
            #     cancel_offer(ge_slot.top_left_corner)
            #     wait_for(gui.offer_canceled, ge_slot.runescape_instance)
            #
            #     # print("Cancelled {} since the offer hasn't been updated in a while".format(ge_slot.item.item_name))
            #     handle_cancelling_buy(ge_slot.runescape_instance, ge_slot, ge_slot.runescape_instance.items_in_use)
            #     # we check if any of the item  bought and if so try to sell it
            #     # we could check the sale history to read the number of items bought and update accordingly
            #     # then if it was a sell we handle it
            #     # we would simply retrieve the items and money and update accordingly, then find the new sell price and sell



# def handle_cancelling_sell(ge_slot, list_of_items_in_use):
#     # TODO: Rewrite or eliminate
#     ge_slot.collect_2()
#     # runescape_window.update_money(runescape_window.money+((ge_slot.item.quantity_to_buy-2)*ge_slot.item.price_instant_sold_at)) think this line is breaking it
#     ge_slot.collect_1()
#     # if not then click box 2 and proceed to sell the item
#     wait_for(gui.view_all_offers, ge_slot.runescape_instance)
#     if ge_slot.item.qty_available_to_buy() > 0:
#         # find_up_to_date_sell_price(runescape_window, ge_slot)
#         ge_slot.find_current_sell_price()
#         ge_slot.item.set_price_instant_bought_at(ge_slot.item.sell_price - 1)
#     else:
#         ge_slot.item.set_price_instant_bought_at(int(ge_slot.item.sell_price * 0.98) - 1)
#     sell_items(ge_slot)
#     # item didnt buy any of so we can just mark this slot as open and start again
#
#
# def handle_cancelling_buy(runescape_window, ge_slot, list_of_items_in_use):
#     """
#     Handles a cancelled buy order.
#     :param runescape_window:
#     :param ge_slot:
#     :param list_of_items_in_use:
#     :return:
#     """
#     # Collects money from items not already bought
#     ge_slot.collect_1()
#
#     # If some items got bought, collect and sell them if we aren't at limit
#     if not len(list(pyautogui.locateAllOnScreen(gui.view_all_offers, region=ge_slot.runescape_instance.region))) > 0:
#         # we have to click box 2 still so click it and handle it
#         ge_slot.collect_2()
#         # if not then click box 2 and proceed to sell the item
#         wait_for(gui.view_all_offers, runescape_window)
#         if ge_slot.item.qty_available_to_buy() > 0:
#             # find_up_to_date_sell_price(runescape_window, ge_slot)
#             ge_slot.find_current_sell_price()
#             ge_slot.item.set_price_instant_bought_at(ge_slot.item.sell_price - 1)
#         sell_items(ge_slot, record_number_selling=True)
#         return ()
#
#     # If no items bought at all just mark the slot as open and return money to the pool
#     runescape_window.update_money(
#         runescape_window.money + ((ge_slot.item.quantity_to_buy - 2) * ge_slot.item.buy_price))
#     ge_slot.update_buy_or_sell_state(None)
#     list_of_items_in_use.remove(ge_slot.item.item_name)
#     ge_slot.item.set_price_instant_bought_at(None)
#     ge_slot.item.set_price_instant_sold_at(None)
#     ge_slot.set_item_in_ge_slot(None)


# def buy_item(runescape_window, ge_slot):
#     # click the correct buy bag
#     runescape_window.select_buy_bag()
#     wait_for(gui.buy_prompt, runescape_window)
#
#     random_typer(str(ge_slot.item.item_name))
#     wait_for(ge_slot.item.image_in_ge_search, runescape_window)
#
#     # click item
#     move_mouse_to_image_within_region(ge_slot.item.image_in_ge_search)
#     pyautogui.click()
#
#     # Sometimes this will enter 1gp more or less to undercut/overcut and move items quickly
#     runescape_window.enter_price(ge_slot.item.buy_price)
#
#     print(f'Buying: {ge_slot.item.item_name} At Price Each: {ge_slot.item.buy_price}')
#
#     ge_slot.item.set_quantity_to_buy(int(min(ge_slot.item.qty_available_to_buy() - 2, (
#             runescape_window.money / ge_slot.item.buy_price) / runescape_window.number_of_empty_ge_slots)))
#
#     runescape_window.update_money(
#         runescape_window.money - (ge_slot.item.quantity_to_buy * ge_slot.item.buy_price))
#
#     runescape_window.enter_quantity(ge_slot.item.quantity_to_buy)
#
#     # click confirm off
#     runescape_window.confirm_offer()
#     ge_slot.item.set_time_of_last_pc()
#     wait_for(gui.view_all_offers, runescape_window)
#     # update states accordingly
#     ge_slot.update_buy_or_sell_state('buy')
#     runescape_window.check_for_empty_ge_slots()
#     print('Placed a buy order for {} {} at {} each'.format(ge_slot.item.quantity_to_buy, ge_slot.item.item_name,
#                                                            ge_slot.item.buy_price))
#     time.sleep(2 + random.random())
#     ge_slot.set_new_image_of_slot()
#
#
# def sell_items(runescape_instance, ge_slot, record_number_selling=False):
#     # click correct sell bag
#     # TODO: Finish refactoring this func
#     ge_slot.runescape_instance.select_sell_bag()
#
#     wait_for(gui.sell_offer, ge_slot.runescape_instance.region)
#     # click item in inv
#     ge_slot.runescape_instance.select_inventory_item()
#
#     if record_number_selling:
#         try:
#             time.sleep(1 + random.random())
#             # TODO: Update screenshot
#             loc_of_all_button = pyautogui.locateOnScreen('Tools/screenshots/All_button.png',
#                                                          region=ge_slot.runescape_instance.region)
#
#             number_selling_image = screengrab_as_numpy_array((loc_of_all_button[0] - 100, loc_of_all_button[1] - 27,
#                                                               loc_of_all_button[0] - 3, loc_of_all_button[1] - 12))
#             quantity = tesser_quantity_image(number_selling_image)
#             ge_slot.update_money(ge_slot.money + (
#                     (ge_slot.item.quantity_to_buy - quantity) * ge_slot.item.buy_price))
#             print('Updating the quantity to buy to {}'.format(quantity))
#             ge_slot.item.set_quantity_to_buy(quantity)
#
#         except:
#             print(
#                 "Couldn't read the quantity bought correctly so setting score to invalid to prevent artificial high scores, money for the window may now be wrong too, we think there is {}gp in this window available".format(
#                     ge_slot.money))
#             ge_slot.item.score_valid = False
#     # click price button
#
#     ge_slot.runescape_instance.enter_price(str(ge_slot.item.sell_price))
#     ge_slot.runescape_instance.confirm_offer()
#
#     # update state of ge slot
#     ge_slot.update_buy_or_sell_state('sell')
#     wait_for(gui.view_all_offers, ge_slot.runescape_instance.region)
#     print('Placed a sell order for {} {} at {} each'.format(ge_slot.item.quantity_to_buy, ge_slot.item.item_name,
#                                                             ge_slot.item.sell_price))
#     time.sleep(2 + random.random())
#     ge_slot.set_new_image_of_slot()


if __name__ == '__main__':
    main()
