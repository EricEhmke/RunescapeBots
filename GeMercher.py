import pyautogui
import time
import pickle
import os
import pytesseract
import cv2
import numpy
import random
import PIL
import re
import screenshots as gui

from Custom_Modules.realmouse import move_mouse_to
from Custom_Modules import pointfrombox
from Custom_Modules import gelimitfinder
from Custom_Modules import items_to_merch_module
from utilities.utils import wait_for, members_status_check, move_mouse_to_image_within_region, \
    random_typer, move_mouse_to_box, HumanBreaks


def box_to_region(top_left_corner, bottom_right_corner):
    return top_left_corner[0], top_left_corner[1], bottom_right_corner[0] - top_left_corner[0], bottom_right_corner[1] - \
           top_left_corner[1]


def main():
    global client_version
    try:
        with (open("list_of_runescape_windows.txt", "rb")) as openfile:
            list_of_runescape_windows = pickle.load(openfile)
        with (open("list_of_items_in_use.txt", "rb")) as openfile:
            list_of_items_in_use = pickle.load(openfile)
        with (open("client_version.txt", "rb")) as openfile:
            client_version = pickle.load(openfile)
        with (open("start_time.txt", "rb")) as openfile:
            start_time = pickle.load(openfile)
        with (open("time_of_last_save.txt", "rb")) as openfile:
            time_of_last_save = pickle.load(openfile)
        print('We have found previous save data so will attempt to pick up where we left off previously')
        print('If you would not like this then please delete any of the 4 save files and try to run this again')
        # score_items = False
        if time.time() - time_of_last_save > 300:
            print('Not counting scores since it was over 5 minutes ago since our last save')
            score_items = False  # this variable prevents false scores being obtained by tracking when a save is loaded and not letting items be scored straight after a load
        else:
            print('Counting scores since it was under 5 minutes ago since our last save')
            score_items = True
    except Exception as e:
        print(e)
        score_items = True
        # client_version = input("Which version of the runescape client are you using? (please answer either 'nxt' or 'legacy'\n:")
        client_version = 'legacy'

        with (open("client_version.txt", "wb")) as openfile:
            pickle.dump(client_version, (openfile))
        start_time = time.time()
        with (open("start_time.txt", "wb")) as openfile:
            pickle.dump(start_time, (openfile))
        # maybe we should add a pickle load up here so that we can load in a previous state if we have one?
        # this would mean we can save instances and only have to initialise one if we don't have a save file to load
        # we should also have a variable that tells us whether or not we loaded from a saved instance
        # this is important because if we did we don't want to be scoring items immediately (this would create articifically low scores)
        # ask me for more info on this
        # returns a list of object of runescape windows and all their features
        list_of_runescape_windows = detect_runescape_windows()
        if len(list_of_runescape_windows) > 1:
            print('We have detected {} windows'.format(len(list_of_runescape_windows)))
        elif len(list_of_runescape_windows) == 1:
            print('We have detected {} window'.format(len(list_of_runescape_windows)))
        elif len(list_of_runescape_windows) == 0:
            print("Failed, we couldn't detect a runescape window, script will now abort")
            quit()
        list_of_items_in_use = []
    try:
        with (open("list_of_item_names_with_scores.txt", "rb")) as openfile:
            list_of_item_names_with_scores = pickle.load(openfile)
        list_of_item_names_with_scores.sort(key=lambda x: x[1])
    except:
        list_of_item_names_with_scores = []
        print("We couldn't find a save file for item scores so items will be picked randomly")
    # this will check if all items used are scored and if not will give them a default score of 10
    print(list_of_item_names_with_scores)
    for i in (items_to_merch_module.p2p_items() + items_to_merch_module.f2p_items()):
        item_not_in_list = True
        for j in list_of_item_names_with_scores:
            if i in j[0]:
                item_not_in_list = False
        if item_not_in_list:
            list_of_item_names_with_scores.append([i, 500])
            print('{} was added to our list of items with scores and given a score of 500'.format(i))
    # this will check for negative values and set them equal to 10
    for i in range(len(list_of_item_names_with_scores)):
        if list_of_item_names_with_scores[i][1] < 1:
            list_of_item_names_with_scores[i][1] = 100
            print('{} was a negative score so we have set it to 100'.format(list_of_item_names_with_scores[i][0]))
    with (open("list_of_item_names_with_scores.txt", "wb")) as openfile:
        pickle.dump(list_of_item_names_with_scores, (openfile))
    logout_prevention_random_number = random.randint(150, 200)
    previous_total_profit = None
    time_of_last_save = time.time()
    last_saved_list_of_runescape_windows = list_of_runescape_windows
    last_saved_list_of_items_in_use = list_of_items_in_use
    time_of_last_update_check = time.time()
    time_of_last_save = time.time()

    while (True):
        print('Loop started')
        time.sleep(3)
        total_profit = 0
        for runescape_window in list_of_runescape_windows:
            if time.time() - HumanBreaks.time_of_last_action > logout_prevention_random_number:  # prevent auto logout
                logout_prevention_random_number = random.randint(150, 200)

                prevent_logout(runescape_window.top_left_corner, runescape_window.bottom_right_corner, runescape_window)

                wait_for(gui.view_all_offers, runescape_window)
        # for each window we need to check if there are any completed offers
        # and if so handle them
        completed_offer_check = False  # variable to see if there was a completed offer
        # this will be used so that if there is one we can skip the rest of the code
        # and cycle back through to check again untill there is no completed offers
        # to handle, and we can continue filling ge slots, this gives completed offers
        # 100% priority, hopefully increasing performance

        for runescape_window in list_of_runescape_windows:
            # We are correcly locating the completed offer
            coords_of_completed_offer = pyautogui.locateOnScreen(gui.completed_ge_slot)
            if coords_of_completed_offer == None:
                continue
            else:
                completed_offer_check = True
                for ge_slot in runescape_window.list_of_ge_slots:
                    # This is checking if the current GE slot is a completed offer
                    # TODO: Improve this using the locateAllonScreen func?
                    if ge_slot.top_left_corner[0] < coords_of_completed_offer[0] and ge_slot.top_left_corner[1] < \
                            coords_of_completed_offer[1] and ge_slot.bottom_right_corner[0] > coords_of_completed_offer[
                        0] and ge_slot.bottom_right_corner[1] > coords_of_completed_offer[1]:
                        # collects the items from the offer
                        collect_items_from_ge_slot(ge_slot)
                        # do stuff based on buy or sell
                        if not score_items:  # if the item has an offer complete during downtime of the script the score will be mark invalid and not be counted
                            ge_slot.item.set_score_invalid()
                        if ge_slot.buy_or_sell == 'buy':
                            # if the item was bought then it would simply sell it at the correct price (assuming the order was filled in under
                            # a certain amount of time), if the item took too long to buy then we would buy another just to confirm that our
                            # price is right). We would also place the item in the cooldown list as a tuple. this tuple would contain
                            # the item name, the time it was bought, the quantity that were bought
                            # do buy stuff
                            # place the item on cooldown
                            runescape_window.add_to_items_on_cooldown(ge_slot.item)
                            # ge_slot.item.number_available_to_buy -= ge_slot.item.quantity_to_buy old line, new is below
                            ge_slot.item.update_number_available_to_buy(
                                ge_slot.item.number_available_to_buy - ge_slot.item.quantity_to_buy)
                            if time.time() - ge_slot.item.time_of_last_pc > 1800:
                                # grab a new price to sell items at since it
                                # has been a long time since we collected this
                                # info
                                if ge_slot.item.number_available_to_buy > 0:
                                    ge_slot.find_current_sell_price()
                                    # find_up_to_date_sell_price(runescape_window, ge_slot)
                                    if ge_slot.item.price_instant_bought_at - ge_slot.item.price_instant_sold_at > 5:
                                        ge_slot.item.set_price_instant_bought_at(
                                            ge_slot.item.price_instant_bought_at - 1)
                            # sell our items at the price instant bought at
                            sell_items(runescape_window, ge_slot)
                            wait_for(gui.view_all_offers, runescape_window)
                            # time.sleep(2+random.random())
                            # ge_slot.set_image_of_slot()
                        elif ge_slot.buy_or_sell == 'sell':
                            runescape_window.update_money(runescape_window.money + (
                                    (ge_slot.item.quantity_to_buy - 1) * ge_slot.item.price_instant_bought_at))
                            runescape_window.update_profit((ge_slot.item.quantity_to_buy - 2) * (
                                    ge_slot.item.price_instant_bought_at - ge_slot.item.price_instant_sold_at))
                            print('Total profit made from this window is {}'.format(runescape_window.profit))
                            # score the item
                            # check if the item has a score, if it does update the score, if not then set the score
                            if ge_slot.item.is_score_valid:
                                for i in range(len(list_of_item_names_with_scores)):
                                    if list_of_item_names_with_scores[i][0] == ge_slot.item.item_name:
                                        print("{} is about to have it's score updated, it's current score is {}".format(
                                            ge_slot.item.item_name, list_of_item_names_with_scores[i][1]))
                                        list_of_item_names_with_scores[i][1] = int(((list_of_item_names_with_scores[i][
                                                                                         1] * 5) + ((
                                                                                                            10 * ge_slot.item.quantity_to_buy * (
                                                                                                            ge_slot.item.price_instant_bought_at - ge_slot.item.price_instant_sold_at)) / (
                                                                                                            time.time() - ge_slot.item.time_buy_order_placed))) / 6)
                                        print("{} has had it's score updated, it's new score is {}".format(
                                            ge_slot.item.item_name, list_of_item_names_with_scores[i][1]))
                                        break
                                    if list_of_item_names_with_scores[i] == list_of_item_names_with_scores[-1]:
                                        list_of_item_names_with_scores.append([ge_slot.item.item_name, int(((
                                                                                                                    10 * ge_slot.item.quantity_to_buy * (
                                                                                                                    ge_slot.item.price_instant_bought_at - ge_slot.item.price_instant_sold_at)) / (
                                                                                                                    time.time() - ge_slot.item.time_buy_order_placed)))])
                                        print('{} was added to the list of scores with a score of {}'.format(
                                            ge_slot.item.item_name, list_of_item_names_with_scores[-1][1]))
                                if len(list_of_item_names_with_scores) == 0:
                                    print("The list of scored items is about to have it's first entry added")
                                    list_of_item_names_with_scores.append([ge_slot.item.item_name, int(((
                                                                                                                ge_slot.item.quantity_to_buy * (
                                                                                                                ge_slot.item.price_instant_bought_at - ge_slot.item.price_instant_sold_at)) / (
                                                                                                                time.time() - ge_slot.item.time_buy_order_placed)))])
                            with (open("list_of_item_names_with_scores.txt", "wb")) as openfile:
                                pickle.dump(list_of_item_names_with_scores, (openfile))
                            # if the item was sold then we would score the item based on the profit it made us and the time it took to buy and sell
                            ge_slot.update_buy_or_sell_state(
                                None)  # updates the buy or sell state to none to indiate the slot is now empty
                            # still need to update lists of items in use accordingly
                            # perhaps like this
                            list_of_items_in_use.remove(ge_slot.item.item_name)
                            ge_slot.item.set_price_instant_bought_at(None)
                            ge_slot.item.set_price_instant_sold_at(None)
                            ge_slot.set_item_in_ge_slot(None)
                        break
        if not score_items:
            print(
                'Since we have just loaded from a save all scores are currently being marked as invalid and will not effect their rating')
        if not completed_offer_check:
            if not score_items:
                print('Scores from now will be valid')
                score_items = True
            empty_slot_check = False  # check if we have found an empty slot, this will be used to break out
            # once we have, so that we only place 1 order before going back through
            # the loop to check for completed offers and such

            highest_cash = 0
            for runescape_window in list_of_runescape_windows:
                if runescape_window.number_of_empty_ge_slots > 0:
                    highest_cash = max(highest_cash, runescape_window.money)

            for runescape_window in list_of_runescape_windows:
                if runescape_window.money == highest_cash:  # scans until it finds the window with the most money in
                    for ge_slot in runescape_window.list_of_ge_slots:
                        if ge_slot.buy_or_sell == None:
                            # we have found an empty slot, so lets place an order
                            list_of_items_available = []
                            for item in runescape_window.items_to_merch:
                                if item.item_name not in list_of_items_in_use:
                                    if item.number_available_to_buy > 0.2 * item.limit:
                                        list_of_items_available.append(item)
                            if len(list_of_items_available) > 0:
                                ###########################################################################################################################################################################################################################################################################
                                if len(list_of_item_names_with_scores) > 0:
                                    # need to filter list_of_item_names_with_scores to only include items that are also in list_of_items_available
                                    temp_list_of_item_names_with_scores = []
                                    temp_list_of_items_available_by_name = []
                                    for i in range(len(list_of_items_available)):
                                        temp_list_of_items_available_by_name.append(
                                            list_of_items_available[i].item_name)
                                    for i in range(len(list_of_item_names_with_scores)):
                                        if list_of_item_names_with_scores[i][0] in temp_list_of_items_available_by_name:
                                            temp_list_of_item_names_with_scores.append(list_of_item_names_with_scores[
                                                                                           i])  ##################################THIS WHOLE SECTION IS UN TESTED
                                    list_of_items = []
                                    list_of_scores = []
                                    for i in range(len(temp_list_of_item_names_with_scores)):
                                        list_of_items.append(temp_list_of_item_names_with_scores[i][0])
                                        list_of_scores.append(temp_list_of_item_names_with_scores[i][1])
                                    normalised_scores = []
                                    for i in range(len(list_of_scores)):
                                        normalised_scores.append(list_of_scores[i] / sum(list_of_scores))
                                    # print(normalised_scores)
                                    # print(list_of_items)
                                    seed = random.random()
                                    for i in range(len(normalised_scores)):
                                        seed -= normalised_scores[i]
                                        if seed < 0:
                                            for item in runescape_window.items_to_merch:
                                                if item.item_name == list_of_items[i]:
                                                    ge_slot.set_item_in_ge_slot(item)
                                                    print('We picked {} from our list of items with scores'.format(
                                                        ge_slot.item.item_name))

                                                    for i in range(len(list_of_item_names_with_scores)):
                                                        if list_of_item_names_with_scores[i][
                                                            0] == ge_slot.item.item_name:
                                                            list_of_item_names_with_scores[i][1] = int(
                                                                list_of_item_names_with_scores[i][1] * 0.9)
                                                    break
                                            break
                                ###########################################################################################################################################################################################################################################################################
                                else:
                                    ge_slot.set_item_in_ge_slot(random.choice(
                                        list_of_items_available))  # This is the line where I will later be choosing items based on score instead of randomly
                                    print(
                                        'We picked {} from our list of items randomly since our list of item names with scores is empty'.format(
                                            ge_slot.item.item_name))
                                try:
                                    list_of_items_in_use.append(ge_slot.item.item_name)
                                    print(ge_slot.item.item_name)  # TESTING TAKING THIS BLOCK OF CODE OUT
                                except:
                                    ge_slot.set_item_in_ge_slot(random.choice(list_of_items_available))
                                    list_of_items_in_use.append(ge_slot.item.item_name)
                                    print('We picked {} from our list of items randomly'.format(ge_slot.item.item_name))
                                wait_for(gui.buy_bag, ge_slot)
                                ge_slot.find_current_sell_price()
                                # find_up_to_date_sell_price(runescape_window, ge_slot)
                                wait_for(gui.sell_bag, ge_slot)
                                ge_slot.find_current_buy_price()
                                # find_up_to_date_buy_price(runescape_window, ge_slot)
                                if ge_slot.item.price_instant_bought_at < ge_slot.item.price_instant_sold_at:
                                    temp = ge_slot.item.price_instant_bought_at
                                    ge_slot.item.set_price_instant_bought_at(ge_slot.item.price_instant_sold_at)
                                    ge_slot.item.set_price_instant_sold_at(temp)
                                if ge_slot.item.price_instant_bought_at - ge_slot.item.price_instant_sold_at > 5:
                                    ge_slot.item.set_price_instant_bought_at(ge_slot.item.price_instant_bought_at - 1)
                                    ge_slot.item.set_price_instant_sold_at(ge_slot.item.price_instant_sold_at + 1)
                                ge_slot.item.set_score_valid()
                                wait_for(gui.buy_bag, ge_slot)
                                buy_item(runescape_window, ge_slot)
                                wait_for(gui.view_all_offers, runescape_window)
                                # time.sleep(2+random.random())
                                # ge_slot.set_image_of_slot()
                            empty_slot_check = True
                        if empty_slot_check == True:
                            break
                if empty_slot_check == True:
                    break
        for runescape_window in list_of_runescape_windows:
            runescape_window.check_for_empty_ge_slots()  # this will update states of ge slots correctly
            # we can also add other updates into here such as checking items on cooldown, more to add later
            if len(runescape_window.list_of_items_on_cooldown) > 0:
                cooldown_tuple = runescape_window.list_of_items_on_cooldown[0]
                if time.time() - cooldown_tuple[1] > 14400:  # then it has been 4 hours so remove from list
                    for item in runescape_window.items_to_merch:
                        if item.item_name == cooldown_tuple[0]:
                            cooldown_tuple[3].update_number_available_to_buy(
                                item.number_available_to_buy + cooldown_tuple[2])
                            runescape_window.pop_oldest_item_on_cooldown()
                            break
            total_profit += runescape_window.profit
        # if time.time()-time_of_last_update_check > 10:
        break_check = False
        for runescape_window in list_of_runescape_windows:
            for ge_slot in runescape_window.list_of_ge_slots:
                if ge_slot.buy_or_sell != None:
                    # TODO: Either eliminate this or improve its function
                    # check_for_in_progress_or_view_offer(ge_slot)
                    # print('Last screenshot of {} was taken {} seconds ago'.format(ge_slot.item.item_name, time.time()-ge_slot.time_of_last_screenshot))
                    if not (ge_slot.image_of_slot == numpy.array(pyautogui.screenshot(
                            region=(ge_slot.top_left_corner[0], ge_slot.top_left_corner[1] + 90, 165, 10)))).all():
                        ge_slot.set_image_of_slot()
                    elif time.time() - ge_slot.time_of_last_screenshot > 1800 and not completed_offer_check and not empty_slot_check:
                        print('Image of {} has not been updated in 30 minutes so we are aborting the offer'.format(
                            ge_slot.item.item_name))
                        # run cancel offer code
                        # first we cancel the offer
                        # print('We are about to cancel an offer that we believe to be in the window with coords {}, we are at line 287'.format(runescape_window.bottom_right_corner))
                        cancel_offer(ge_slot.top_left_corner)
                        wait_for(gui.offer_canceled, runescape_window)
                        print("Cancelled {} since the offer hasn't been updated in a while".format(
                            ge_slot.item.item_name))
                        # then if the item was a buy we handle it
                        if ge_slot.buy_or_sell == 'buy':
                            handle_cancelling_buy(runescape_window, ge_slot, list_of_items_in_use)
                        elif ge_slot.buy_or_sell == 'sell':
                            handle_cancelling_sell(runescape_window, ge_slot, list_of_items_in_use)
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
                        handle_cancelling_sell(runescape_window, ge_slot, list_of_items_in_use)
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
                        handle_cancelling_buy(runescape_window, ge_slot, list_of_items_in_use)
                        # we check if any of the item  bought and if so try to sell it
                        # we could check the sale history to read the number of items bought and update accordingly
                        # then if it was a sell we handle it
                        # we would simply retrieve the items and money and update accordingly, then find the new sell price and sell
                        break_check = True
                if break_check:
                    break
            if break_check:
                break
            # time_of_last_update_check = time.time()

        if time.time() - time_of_last_save > 60 or last_saved_list_of_runescape_windows != list_of_runescape_windows or last_saved_list_of_items_in_use != list_of_items_in_use or total_profit != previous_total_profit:
            previous_total_profit = total_profit
            last_saved_list_of_runescape_windows = list_of_runescape_windows
            last_saved_list_of_items_in_use = list_of_items_in_use
            time_of_last_save = time.time()
            with (open("list_of_items_in_use.txt", "wb")) as openfile:
                pickle.dump(list_of_items_in_use, (openfile))
            with (open("list_of_runescape_windows.txt", "wb")) as openfile:
                pickle.dump(list_of_runescape_windows, (openfile))
            with (open("list_of_item_names_with_scores.txt", "wb")) as openfile:
                pickle.dump(list_of_item_names_with_scores, (openfile))
            with (open("time_of_last_save.txt", "wb")) as openfile:
                pickle.dump(time_of_last_save, (openfile))
            print('State has now been saved, you may be able to close the script and return from this point later')
            print(
                'Total profit made across all windows so far is {}. We have been running for {} minutes, this is a profit per hour of {}k per hour.'.format(
                    total_profit, int((time.time() - start_time) / 60),
                    int(3.6 * total_profit / (time.time() - start_time))))
            time_of_last_save = time.time()
            # print('Current scored item list {}'.format(list_of_item_names_with_scores))
        '''if total_profit != previous_total_profit:
            previous_total_profit = total_profit
            #label = myfont.render("Current Total Profit: {}".format(total_profit), 1, (255,255,0))
            #game_display.blit(label, (10, 10))
            #pygame.display.update()
            print('Total profit made across all windows so far is {}. We have been running for {} minutes, this is a profit per hour of {}k per hour.'.format(total_profit, int((time.time()-start_time)/60), int(3.6*total_profit/(time.time()-start_time))))'''


# if there are no completed orders then we need to
# check for empty ge slots and fill them with
# orders
# all orders should be unique, ie not buying coal on 2 windows at once, this would harm profit since they would be
# competing with eachother. Instead one window should buy it, then once it has sold the next window can start to buy

class item():

    def __init__(self, name, limit):
        self.item_name = name
        self.limit = limit
        self.number_available_to_buy = limit
        self.image_in_ge_search = check_if_image_exists(name)
        self.price_instant_bought_at = None
        self.price_instant_sold_at = None
        self.current_state = None  # this will track if the item is currently being bought, sold or neither (None)
        self.is_score_valid = None
        self.time_buy_order_placed = None
        self.time_of_last_pc = None
        self.quantity_to_buy = None

    def set_score_valid(self):
        self.is_score_valid = True

    def set_score_invalid(self):
        self.is_score_valid = False

    def set_time_item_buy_was_placed(self):
        self.time_buy_order_placed = time.time()

    def update_number_available_to_buy(self, number):
        self.number_available_to_buy = number

    def set_time_of_last_pc(self):
        self.time_of_last_pc = time.time()

    def set_price_instant_bought_at(self, price):
        self.price_instant_bought_at = price

    def set_price_instant_sold_at(self, price):
        self.price_instant_sold_at = price

    def set_quantity_to_buy(self, number):
        self.quantity_to_buy = number

    def set_current_state(self, state):
        self.current_state = state


class runescape_window():
    # TODO: Make a seperate function to initialize this one
    # TODO: This class should be split in 2. 1 for GE related things and 1 for the RS window
    def __init__(self, position):
        self.bottom_right_corner = position
        # I am leaving these numbers hard coded for 1440p until I find another solution
        self.top_left_corner = (position[0] - 482, position[1] - 304)
        self.region = (self.top_left_corner[0], self.top_left_corner[1], 484, 303)

        # Checks to see if player has members
        # TODO: Change this for OSRS. Iself.region am commenting it out and setting it to True for now
        # self.member_status = members_status_check(self.top_left_corner, self.bottom_right_corner)

        self.member_status = True
        # TODO: Move this to the GE slot class
        self.loc_price = (self.bottom_right_corner[0] - 396, self.bottom_right_corner[1] - 61), \
                         (self.bottom_right_corner[0] - 179, self.bottom_right_corner[1] - 28)

        self.list_of_ge_slots = initialise_ge_slots(self.top_left_corner, self.bottom_right_corner,
                                                    self)  # this returns a list of ge_slot objects
        # TODO: Fix the money detection
        # self.money = detect_money(self.top_left_corner, self.bottom_right_corner) TESSER NEEDS FIXING
        self.money = 14_000
        self.profit = 0
        self.last_action_time = time.time()
        # TODO: Change this to a simple left click or somthing According to authoer this is here just to make sure game doesn log out. Commented out just for testing
        # examine_money(position)
        self.items_to_merch = items_to_merch(self.member_status)
        self.list_of_items_on_cooldown = []
        self.number_of_empty_ge_slots = empty_ge_slot_check(self.list_of_ge_slots)

        print('Initialised a window with {}Kgp and {} ge slots'.format(int(self.money / 1000),
                                                                       self.number_of_empty_ge_slots))

        self.loc_inventory_item = (self.bottom_right_corner[0] + 950, self.bottom_right_corner[1] + 329), \
                                  (self.bottom_right_corner[0] + 973, self.bottom_right_corner[1] + 349)
        self.loc_collection_box_gp = (self.bottom_right_corner[0] - 105, self.bottom_right_corner[1] - 51), \
                                     (self.bottom_right_corner[0] - 71, self.bottom_right_corner[1] - 21)
        self.loc_collection_box_item = (self.bottom_right_corner[0] - 55, self.bottom_right_corner[1] - 51), \
                                       (self.bottom_right_corner[0] - 20, self.bottom_right_corner[1] - 21)

    def update_profit(self, number):
        self.profit = self.profit + number

    def pop_oldest_item_on_cooldown(self):
        self.list_of_items_on_cooldown.pop(0)

    def check_for_empty_ge_slots(self):
        self.number_of_empty_ge_slots = empty_ge_slot_check(self.list_of_ge_slots)

    def set_time_of_last_action(self):
        self.last_action_time = time.time()

    def add_to_items_on_cooldown(self, item):
        self.list_of_items_on_cooldown.append((item.item_name, time.time(), item.quantity_to_buy, item))

    def add_single_item_to_cooldown(self, item):
        self.list_of_items_on_cooldown.append((item.item_name, time.time(), 1, item))

    def update_money(self, number):
        self.money = number

    @HumanBreaks
    def select_inventory_item(self):
        item_location = pointfrombox.random_point(*self.loc_inventory_item)
        move_mouse_to(item_location[0], item_location[1])
        pyautogui.click()


class ge_slot:

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
        self.loc_price = self.runescape_instance.loc_price

    def update_buy_or_sell_state(self, state):
        self.buy_or_sell = state

    def set_item_in_ge_slot(self, item):
        self.item = item

    def set_time_of_last_screenshot(self):
        self.time_of_last_screenshot = time.time()

    def set_image_of_slot(self):
        self.set_time_of_last_screenshot()
        print('Image of {} has been updated'.format(self.item.item_name))

    def location(self):
        location = pointfrombox.random_point(self.top_left_corner, self.bottom_right_corner)
        return location

    @HumanBreaks
    def open_ge_slot(self):
        move_mouse_to(*self.location())
        pyautogui.click()
        wait_for(gui.completed_offer, self.runescape_instance)

    @HumanBreaks
    def confirm_offer(self):
        move_mouse_to_image_within_region(gui.confirm_offer, self.runescape_instance.region)
        pyautogui.click()

    @HumanBreaks
    def select_buy_bag(self):
        move_mouse_to_image_within_region(gui.buy_bag, self.region)
        pyautogui.click()

    @HumanBreaks
    def select_sell_bag(self):
        move_mouse_to_image_within_region(gui.sell_bag, self.region)
        pyautogui.click()

    # TODO: find a better way to handle the region so this is not static
    @HumanBreaks
    def enter_price(self, price):
        move_mouse_to_image_within_region(gui.enter_price_box, region=(1177, 632, 221, 76))
        pyautogui.click()
        time.sleep(1 + random.random())
        random_typer(str(price))
        time.sleep(random.random() + .25)
        pyautogui.press('enter')

    # TODO: find a better way to handle the region so this is not static
    @HumanBreaks
    def enter_quantity(self, quantity):
        move_mouse_to_image_within_region(gui.enter_quantity_box, region=(954, 632, 221, 76))
        pyautogui.click()
        time.sleep(.5 + random.random())
        random_typer(str(quantity))
        time.sleep(random.random() + .25)
        pyautogui.press('enter')

    @HumanBreaks
    def collect_1(self):
        top_left, bottom_right = pointfrombox.random_point(*self.runescape_instance.loc_collection_box_gp)
        move_mouse_to(top_left, bottom_right)
        pyautogui.click()

    @HumanBreaks
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
        wait_for(gui.view_all_offers, self.runescape_instance)
        price = collect_items_from_ge_slot(self)

        self.item.set_price_instant_bought_at(price)
        self.runescape_instance.add_single_item_to_cooldown(self.item)
        self.item.update_number_available_to_buy(self.item.number_available_to_buy - 1)
        self.item.set_time_of_last_pc()
        print('Current buy price for {} is {} gp'.format(self.item.item_name, price))

    def find_current_sell_price(self):
        self.select_buy_bag()
        wait_for(gui.buy_prompt, self.runescape_instance)
        random_typer(str(self.item.item_name))
        wait_for(self.item.image_in_ge_search, self.runescape_instance.region)
        move_mouse_to_image_within_region(self.item.image_in_ge_search)
        pyautogui.click()
        # # TODO: put a wait here for the price window
        # time.sleep(1 + random.random())
        self.enter_price(1000)
        self.confirm_offer()
        wait_for(gui.view_all_offers, self.runescape_instance)
        price = collect_items_from_ge_slot(self)
        wait_for(gui.view_all_offers, self.runescape_instance)
        self.item.set_price_instant_bought_at(price)
        self.runescape_instance.add_single_item_to_cooldown(self.item)
        self.item.update_number_available_to_buy(self.item.number_available_to_buy - 1)
        self.item.set_time_of_last_pc()
        self.item.set_price_instant_sold_at(price)
        print('Current sell price for {} is {} gp'.format(self.item.item_name, price))


def handle_cancelling_sell(runescape_window, ge_slot, list_of_items_in_use):
    ge_slot.collect_2()
    # runescape_window.update_money(runescape_window.money+((ge_slot.item.quantity_to_buy-2)*ge_slot.item.price_instant_sold_at)) think this line is breaking it
    ge_slot.collect_1()
    # if not then click box 2 and proceed to sell the item
    wait_for(gui.view_all_offers, ge_slot.runescape_instance)
    if ge_slot.item.number_available_to_buy > 0:
        # find_up_to_date_sell_price(runescape_window, ge_slot)
        ge_slot.find_current_sell_price()
        ge_slot.item.set_price_instant_bought_at(ge_slot.item.price_instant_bought_at - 1)
    else:
        ge_slot.item.set_price_instant_bought_at(int(ge_slot.item.price_instant_bought_at * 0.98) - 1)
    sell_items(runescape_window, ge_slot)
    # item didnt buy any of so we can just mark this slot as open and start again


def handle_cancelling_buy(runescape_window, ge_slot, list_of_items_in_use):
    # click box 1
    ge_slot.collect_1()
    # runescape_window.update_money(runescape_window.money+((ge_slot.item.quantity_to_buy-2)*ge_slot.item.price_instant_sold_at)) think this line is breaking it
    # wait and check if we have jumped back to the main window, handle this
    if not len(list(pyautogui.locateAllOnScreen(gui.view_all_offers, region=ge_slot.runescape_instance.region))) > 0:
        # we have to click box 2 still so click it and handle it
        ge_slot.collect_2()
        # if not then click box 2 and proceed to sell the item
        wait_for(gui.view_all_offers, runescape_window)
        if ge_slot.item.number_available_to_buy > 0:
            # find_up_to_date_sell_price(runescape_window, ge_slot)
            ge_slot.find_current_sell_price()
            ge_slot.item.set_price_instant_bought_at(ge_slot.item.price_instant_bought_at - 1)
        sell_items(runescape_window, ge_slot, record_number_selling=True)
        runescape_window.add_to_items_on_cooldown(ge_slot.item)
        ge_slot.item.update_number_available_to_buy(ge_slot.item.number_available_to_buy - ge_slot.item.quantity_to_buy)
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


    print('Min afunc is using values of {} and {}'.format(
        ge_slot.item.number_available_to_buy - 2,
        (runescape_window.money / ge_slot.item.price_instant_sold_at) / runescape_window.number_of_empty_ge_slots))

    ge_slot.item.set_quantity_to_buy(int(min(ge_slot.item.number_available_to_buy - 2, (
            runescape_window.money / ge_slot.item.price_instant_sold_at) / runescape_window.number_of_empty_ge_slots)))

    runescape_window.update_money(
        runescape_window.money - (ge_slot.item.quantity_to_buy * ge_slot.item.price_instant_sold_at))

    ge_slot.enter_quantity(ge_slot.item.quantity_to_buy)

    # click confirm off
    ge_slot.confirm_offer()
    ge_slot.item.set_time_item_buy_was_placed()
    wait_for(gui.view_all_offers, runescape_window)
    # update states accordingly
    runescape_window.set_time_of_last_action()
    ge_slot.update_buy_or_sell_state('buy')
    runescape_window.check_for_empty_ge_slots()
    print('Placed a buy order for {} {} at {} each'.format(ge_slot.item.quantity_to_buy, ge_slot.item.item_name,
                                                           ge_slot.item.price_instant_sold_at))
    time.sleep(2 + random.random())
    ge_slot.set_image_of_slot()


def sell_items(runescape_window, ge_slot, record_number_selling=False):
    # click correct sell bag
    # TODO: Finish refactoring this func
    ge_slot.select_sell_bag()

    wait_for(gui.sell_offer, ge_slot.runescape_instance.region)
    # click item in inv
    runescape_window.select_inventory_item()

    if record_number_selling:
        try:
            time.sleep(1 + random.random())
            # TODO: Update screenshot
            loc_of_all_button = pyautogui.locateOnScreen('Tools/screenshots/All_button.png',
                                                         region=ge_slot.runescape_instance.region)

            number_selling_image = screengrab_as_numpy_array((loc_of_all_button[0] - 100, loc_of_all_button[1] - 27,
                                                              loc_of_all_button[0] - 3, loc_of_all_button[1] - 12))
            quantity = tesser_quantity_image(number_selling_image)
            runescape_window.update_money(runescape_window.money + (
                    (ge_slot.item.quantity_to_buy - quantity) * ge_slot.item.price_instant_sold_at))
            print('Updating the quantity to buy to {}'.format(quantity))
            ge_slot.item.set_quantity_to_buy(quantity)

        except:
            print(
                "Couldn't read the quantity bought correctly so setting score to invalid to prevent artificial high scores, money for the window may now be wrong too, we think there is {}gp in this window available".format(
                    runescape_window.money))
            ge_slot.item.set_score_invalid()
    # click price button

    ge_slot.enter_price(str(ge_slot.item.price_instant_bought_at))
    ge_slot.confirm_offer()

    # update state of ge slot
    ge_slot.update_buy_or_sell_state('sell')
    wait_for(gui.view_all_offers, ge_slot.runescape_instance.region)
    runescape_window.set_time_of_last_action()
    print('Placed a sell order for {} {} at {} each'.format(ge_slot.item.quantity_to_buy, ge_slot.item.item_name,
                                                            ge_slot.item.price_instant_bought_at))
    time.sleep(2 + random.random())
    ge_slot.set_image_of_slot()


def check_price(location):
    """
    A function that reads a price from the screen via Tesseract OCR
    :param location: X, Y coords of the upper right and lower left hand corners of the area to be read
    :return: int
    """
    price = tesser_price_image(screengrab_as_numpy_array(location))
    return price


# Merch related function
def detect_money(top_left_corner, bottom_right_corner):
    global client_version
    money_icon_path = 'Tools/screenshots/money_icon_' + client_version + '.png'
    money_icon_loc = pyautogui.locateOnScreen(money_icon_path, region=(
        top_left_corner[0], top_left_corner[1], bottom_right_corner[0] - top_left_corner[0],
        bottom_right_corner[1] - top_left_corner[1]))
    money_val_loc = (money_icon_loc[0] + 22, money_icon_loc[1], money_icon_loc[0] + 100, money_icon_loc[1] + 18)
    image = screengrab_as_numpy_array(money_val_loc)
    money_val = tesser_money_image(image)
    return (money_val)


# Merch related function
def tesser_money_image(image):
    # image = cv2.resize(image, (0,0), fx=2, fy=2)
    image = PIL.Image.fromarray(image)
    txt = pytesseract.image_to_string(image, config='-psm 7')
    txt_list = list(txt)
    for i in range(len(txt_list)):
        if txt_list[i] == 'o':
            txt_list[i] = '0'
        elif txt_list[i] == 'O':
            txt_list[i] = '0'
        elif txt_list[i] == 'l':
            txt_list[i] = '1'
        elif txt_list[i] == 'I':
            txt_list[i] = '1'
        elif txt_list[i] == 'i':
            txt_list[i] = '1'
        elif txt_list[i] == 'M':
            txt_list[i] = '000000'
        elif txt_list[i] == 'K':
            txt_list[i] = '000'
        elif txt_list[i] == 'm':
            txt_list[i] = '000000'
        elif txt_list[i] == 'k':
            txt_list[i] = '000'
        elif txt_list[i] == 's':
            txt_list[i] = '5'
        elif txt_list[i] == 'S':
            txt_list[i] = '5'
        elif txt_list[i] == 'W':
            txt_list[i] = '40'
    txt = int(''.join(txt_list))
    return (txt)


# Merch related function
def tesser_quantity_image(image):
    image = cv2.resize(image, (0, 0), fx=2, fy=2)
    image = PIL.Image.fromarray(image)
    txt = pytesseract.image_to_string(image, config='-psm 7')
    txt = txt.replace(",", "")
    txt = txt.replace(" ", "")
    txt = txt.replace(".", "")
    if len(txt) == 0:
        txt = pytesseract.image_to_string(image, config='-psm 10')
    try:
        txt = int(txt)
    except:
        txt_list = list(txt)
        for i in range(len(txt_list)):
            if txt_list[i] == 'B':
                txt_list[i] = '8'
            elif txt_list[i] == 'l':
                txt_list[i] = '1'
            elif txt_list[i] == 'L':
                txt_list[i] = '1'
            elif txt_list[i] == 'i':
                txt_list[i] = '1'
            elif txt_list[i] == 'I':
                txt_list[i] = '1'
            elif txt_list[i] == 'o':
                txt_list[i] = '0'
            elif txt_list[i] == 'O':
                txt_list[i] = '0'
            elif txt_list[i] == 'z':
                txt_list[i] = '2'
            elif txt_list[i] == 'Z':
                txt_list[i] = '2'
            elif txt_list[i] == 'Q':
                txt_list[i] = '0'
            elif txt_list[i] == 's':
                txt_list[i] = '5'
            elif txt_list[i] == 'S':
                txt_list[i] = '5'
            elif txt_list[i] == '.':
                txt_list[i] = '9'
            elif txt_list[i] == ':':
                txt_list[i] = '8'
        if len(txt_list) > 1:
            txt = int(''.join(txt_list))
        else:
            txt = int(txt_list[0])
    return (txt)


# Converts a screenshot/image into a numpy array
def screengrab_as_numpy_array(location):
    """
    Takes a screenshot at provided location and returns screenshot as a numpy array
    :param location: x,y location points of bottom left and top right corners of an area on screen
    :return: numpy.array
    """
    top_left, bottom_right = location
    width = top_left[0] - top_left[1]
    height = bottom_right[1] - top_left[1]
    im = numpy.array(pyautogui.screenshot(region=(top_left[0], top_left[1], width, height)))
    return im


# Merch related function
def tesser_price_image(image):
    # Enlarge image for easier processing
    image = cv2.resize(src=image, dsize=None, fx=5, fy=5)
    # Convert image to grayscale
    image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    # Apply a threshold to change to complete black or white
    retval, image = cv2.threshold(image, 100, 255, cv2.THRESH_BINARY)
    # Invert image so text is black on white
    image = 255 - image
    # Show image
    # plt.imshow(image, cmap='gray')
    # Convert image to string
    # TODO: This needs to be improved. Has trouble with 4, vs 9 and 6
    txt = pytesseract.image_to_string(image, lang='eng', config='--psm 6')
    txt = txt.replace(",", "")
    txt = re.findall(r'\d+', txt)
    try:
        price = int(txt[1]) / int(txt[0])
    except:
        print('Problem with tesser_price_image ocr occured. Price could not be found')

    return int(price)


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
    # TODO: Move this into the runescape_instance class?
    # Collect the gold
    is_slot_empty = pyautogui.locateOnScreen(gui.empty_collect_slot, region=ge_slot.runescape_instance.region)
    if is_slot_empty is None:
        ge_slot.collect_2()

    ge_slot.collect_1()

    wait_for(gui.view_all_offers, runescape_window)

    return price


# Merch related function
def empty_ge_slot_check(list_of_ge_slots):
    number_of_ge_slots_open = 0
    for slot in list_of_ge_slots:
        if slot.buy_or_sell == None:
            number_of_ge_slots_open += 1
    return number_of_ge_slots_open


# This should be a more generalized function
# This should continue and take a screenshot for items that don't have one
def check_if_image_exists(item_name):
    global client_version
    file_name = 'Tools/screenshots/items/' + client_version + '_items/' + item_name.replace(' ', '_') + '.png'
    if os.path.isfile(file_name):
        return (file_name)
    else:
        print(
            'You do not have an image file for {} so the script is aborting, to fix this issue either take a screenshot of {} or remove it from the list of items to merch'.format(
                item_name, item_name))


# Merch related function
def items_to_merch(member_status):
    if member_status:
        items_to_merch = []
        # below is a list of members items to merch
        list_of_items = items_to_merch_module.p2p_items()
        list_of_item_limits = gelimitfinder.find_ge_limit(list_of_items)
        for i in range(len(list_of_item_limits)):
            list_of_item_limits[i] -= 1
        for i in range(len(list_of_items)):
            items_to_merch.append(item(list_of_items[i], list_of_item_limits[i]))
        # we are a member so initialise a members item list
    else:
        items_to_merch = []
        # below is a list of f2p items to merch
        list_of_items = items_to_merch_module.f2p_items()
        list_of_item_limits = gelimitfinder.find_ge_limit(list_of_items)
        for i in range(len(list_of_item_limits)):
            list_of_item_limits[i] -= 1
        for i in range(len(list_of_items)):
            items_to_merch.append(item(list_of_items[i], list_of_item_limits[i]))
        # we are f2p so initialise a f2p item list
    return (items_to_merch)


# Merch related function
# TODO: Make this just right click on a random place on the screen instead.
def examine_money(position):
    pass
    # # this whole block just examines the amount of money
    # point = pointfrombox.random_point((138, 94), (189, 109))
    # # that the account has just for auto log out purposes
    # money_pouch = (position[0] - point[0], position[1] - point[1])
    # # so that it has a recording of the last time an action
    # realmouse.move_mouse_to(money_pouch[0], money_pouch[1])
    # # was taken and can keep track of this value in future to stop logouts
    # # occuring
    # pyautogui.click(button='right')
    # point = pointfrombox.random_point((-75, -32), (74, -24))
    # examine = (money_pouch[0] - point[0], money_pouch[1] - point[1])
    # realmouse.move_mouse_to(examine[0], examine[1])
    # pyautogui.click()


# Merch related function
def initialise_ge_slots(top_left_corner, bottom_right_corner, runescape_window):
    ge_slots = []
    for i in count_ge_slots(top_left_corner, bottom_right_corner):
        ge_slots.append(ge_slot(((i[0], i[1]), (i[0] + i[2], i[1] + i[3])), runescape_window))
    return ge_slots


def detect_runescape_windows():  # this function will detect how many runescape windows are present and where they are
    list_of_runescape_windows = []
    for i in pyautogui.locateAllOnScreen(gui.main_ge_window):
        list_of_runescape_windows.append(
            runescape_window((i[0] + i[2], i[1] + i[3])))
    return (list_of_runescape_windows)


# this checks how many slots a particular window has available
def count_ge_slots(top_left_corner, bottom_right_corner):
    width = bottom_right_corner[0] - top_left_corner[0]
    height = bottom_right_corner[1] - top_left_corner[1]
    # Commenting out the region arg for testing
    list_of_ge_slots = list(
        pyautogui.locateAllOnScreen(gui.ge_open_slot, region=(top_left_corner[0], top_left_corner[1], width, height),
                                    confidence=0.9))
    # list_of_ge_slots = list(
    #     pyautogui.locateAllOnScreen(ge_open_slot))

    return list_of_ge_slots


# Swaps from history to exchange tab or examines money to reset the logout timer
# TODO: Change this to just right click somewhere. Commeting out for testing.
@HumanBreaks
def prevent_logout(top_left_corner, bottom_right_corner, runescape_window):
    pass
    # seed = random.random()
    # x, y = pyautogui.size()
    # if seed > 0.5:  # opens up the sale history tab for 5 seconds then returns to ge tab
    #     while (True):
    #         move_mouse_to(random.randint(0, x), random.randint(0, y))
    #         # we will never break out of this loop if this image is not found
    #         if len(list(pyautogui.locateAllOnScreen(gui.history_button, region=(
    #                 top_left_corner[0], top_left_corner[1], bottom_right_corner[0] - top_left_corner[0],
    #                 bottom_right_corner[1] - top_left_corner[1])))) > 0:
    #             # we will never break out of this loop if this is not found
    #             move_mouse_to_box(gui.history_button, top_left_corner, bottom_right_corner)
    #             pyautogui.click()
    #             time.sleep(9 * random.random() + 1)
    #
    #             move_mouse_to_box(gui.exchange_button, top_left_corner, bottom_right_corner)
    #             pyautogui.click()
    #             break
    #         else:
    #             print('Could not find sales history button, broke to prevent infinite loop')
    #             break
    # else:  # examines the money pouch
    #     examine_money(bottom_right_corner)


if __name__ == '__main__':
    main()
    # move_mouse_to_image_within_region(enter_price_box, region=(1177, 632, 221, 76))
    # coords_of_completed_offer = pyautogui.locateOnScreen(completed_ge_slot)
    # print(coords_of_completed_offer)
