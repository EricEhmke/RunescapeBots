import pandas as pd
import datetime
import os
from utilities.utils import percent_of


def check_if_image_exists(item_name):
    file_name = 'Tools/screenshots/items/legacy_items/' + item_name.replace(' ', '_') + '.png'
    if os.path.isfile(file_name):
        return file_name
    else:
        print(
            'You do not have an image file for {} so the script is aborting, to fix this issue either take'
            ' a screenshot of {} or remove it from the list of items to merch'.format(
                item_name, item_name))


class Item:

    def __init__(self, name, limit, runescape_instance):
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
        self.max_item_age = 1800
        self.runescape_instance = runescape_instance

    def set_score_valid(self):
        self.is_score_valid = True

    def set_score_invalid(self):
        self.is_score_valid = False

    def set_time_item_buy_was_placed(self):
        self.time_buy_order_placed = datetime.datetime.now()

    def update_number_available_to_buy(self, number):
        self.number_available_to_buy = number

    def set_time_of_last_pc(self):
        self.time_of_last_pc = datetime.datetime.now()

    def set_price_instant_bought_at(self, price):
        self.price_instant_bought_at = price

    def set_price_instant_sold_at(self, price):
        self.price_instant_sold_at = price

    def set_quantity_to_buy(self, number):
        self.quantity_to_buy = number

    def set_current_state(self, state):
        self.current_state = state

    def is_aged(self):
        if self.time_of_last_pc is None:
            return True
        else:
            return (datetime.datetime.now() - self.time_of_last_pc).seconds > self.max_item_age

    def qty_available_to_buy(self):
        transactions = self.runescape_instance.GEMerch.transaction_record
        aged_threshold = datetime.datetime.now() - datetime.timedelta(hours=4)
        item_mask = transactions['Item'] == self.item_name
        time_mask = pd.to_datetime(transactions['Timestamp']) > aged_threshold
        num_items_on_cooldown = transactions.loc[item_mask & time_mask]['Qty'].sum()
        return self.limit - num_items_on_cooldown

    def score(self):
        # filter transaction record for item calculate GP/hr and return as score
        df_transaction = self.runescape_instance.GEMerch.transaction_record
        mask_item = df_transaction.Item == self.item_name
        df_item = df_transaction.loc[mask_item]
        # TODO: Make this a weighted average
        item_score = df_item['Score'].mean()
        return item_score if not pd.isnull(item_score) else 0

    def return_on_investment(self):
        return percent_of(buy_price=self.price_instant_bought_at,
                          sell_price=self.price_instant_sold_at)

    def meets_profit_threshold(self):
        if self.price_instant_bought_at or self.price_instant_sold_at is None:
            return True

        return (self.return_on_investment() > 0.025) and (self.price_instant_bought_at - self.price_instant_sold_at > 3)
