import string
import json
from os import path
from random import randint, choices as random_choices
from kivy import platform
from config import Config


class ObjectWrapper:
    def __init__(self, **kwargs):
        for kw in kwargs:
            if kwargs[kw] is not None:
                setattr(self, kw, kwargs[kw])

    @staticmethod
    def wrap_dict_in_obj(kwargs_dict):
        return ObjectWrapper(**kwargs_dict)

    @staticmethod
    def build_obj_from_values(**kwargs):
        return ObjectWrapper(**kwargs)


class Utils:
    @staticmethod
    def nudge_int_value(current_val, delta, value_desc="this variable", floor=None, ceiling=None):
        dstr = str(delta)
        dint = int(dstr.replace('=', ''))
        if "+" in dstr and "-" in dstr:
            raise ValueError("Attempting to add and substract at the same time?")
        elif "+" in dstr:
            new_val = current_val + dint
        elif "-" in dstr:
            new_val = current_val - abs(dint)
        elif not Utils.has_int(dstr):
            raise ValueError("Can't set {} to a non-integer value.".format(value_desc))
        else:
            new_val = dint
        if floor is not None:
            new_val = max(floor, new_val)
        if ceiling is not None:
            new_val = min(ceiling, new_val)
        return new_val

    @staticmethod
    def has_int(val):
        try:
            int(val)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_number(val):
        try:
            float(val)
            return True
        except ValueError:
            return False
        except TypeError:
            return False

    @staticmethod
    def is_iterable(obj):
        try:
            iter(obj)
            return True
        except Exception as e:
            e.__repr__()
            return False

    @staticmethod
    def generate_random_id_str(leng=6, label: str = None):
        return "{}_{}".format(label if label else "rid", ''.join(random_choices(string.ascii_letters, k=leng)))

    @staticmethod
    def make_dice_roll(max_val, num_dice):
        return [randint(1, max_val) for _ in range(num_dice)]

    @staticmethod
    def get_json_from_file(file_name, mode='r'):
        file_path = path.normpath(Config.PATH_JSON + '/' + file_name)
        with open(file_path, mode) as read_file:
            data = json.load(read_file)
            return data

    @staticmethod
    def read_text_from_file(file_name, mode='r'):
        file_path = path.normpath(Config.PATH_TEXT_EVENTS + '/' + file_name)
        with open(file_path, mode) as read_file:
            data = read_file.readlines()
            return data

    @staticmethod
    def get_image_file_path(file_name, image_type="gui"):
        if image_type == "gui":
            return path.normpath(Config.PATH_GUI_IMAGES + '/' + file_name)
        return path.normpath(Config.PATH_IMAGES + '/' + file_name)

    @staticmethod
    def get_resource_path(relative_path):
        # if hasattr(sys, "_MEIPASS"):
        #     resource_path = path.join(sys._MEIPASS, relative_path)
        # else:
        #     resource_path = path.join(path.abspath("."), relative_path)
        resource_path = path.normpath(path.join(Config.WORKING_PATH, relative_path))
        print("get resource path ==> {}".format(resource_path))
        return resource_path

    @staticmethod
    def get_platform():
        return platform

    @staticmethod
    def is_desktop():
        plat = Utils.get_platform()
        if plat in ('win', 'linux', 'macosx'):
            return True
        return False

    @staticmethod
    def get_excerpt(exstr: str, start_token, end_token):
        tokens = exstr.split(start_token, maxsplit=1)
        if len(tokens) < 2:
            return exstr
        return tokens[1].split(end_token)[0]

    @staticmethod
    def truncate_string(tstring, leng=20):
        leng = 5 if leng < 5 else leng
        return tstring[:leng-3] + "..." if len(tstring) > leng else tstring

    @staticmethod
    def open_url(url):  # TODO: implement this
        print("opening url: {}".format(url))

    @staticmethod
    def log(*args):
        print(*args)


class V5DiceRoll:
    D10_WIN_INC = 6
    D10_MAX = 10

    RESULT_BESTIAL_FAIL = "Bestial Failure"
    RESULT_FAIL = "Failure"
    RESULT_WIN = "Success"
    RESULT_CRIT = "Critical"
    RESULT_MESSY_CRIT = "Messy Critical"

    def __init__(self, pool, difficulty, hunger=1, include_hunger=True):
        self.hunger = int(hunger) if include_hunger else 0
        self.pool, self.difficulty = int(pool), int(difficulty)
        self.opp_ws = None
        self.red_results, self.red_ones, self.red_tens = [], 0, 0
        self.black_tens, self.black_failures = 0, 0
        self.result_descriptor = V5DiceRoll.RESULT_FAIL
        self.rerolled = self.crit = False
        self.black_failures = self.num_successes = 0
        self.outcome, self.margin = None, 0
        self.black_pool = pool - max(self.hunger, 0) if include_hunger else pool
        self.black_results = Utils.make_dice_roll(V5DiceRoll.D10_MAX, self.black_pool)
        self.included_hunger = include_hunger
        if self.included_hunger:
            self.red_results = Utils.make_dice_roll(V5DiceRoll.D10_MAX, min(self.hunger, self.pool))
        self.calculate()

    def calculate(self):
        successes = [dv for dv in self.black_results if dv >= V5DiceRoll.D10_WIN_INC]  # TODO: here!!
        self.black_failures = self.black_pool - len(successes)
        self.black_tens = len([ten for ten in successes if ten >= V5DiceRoll.D10_MAX])
        if self.included_hunger:  # and not self.rerolled:  TODO: why did I do this?
            red_successes = [dv for dv in self.red_results if dv >= V5DiceRoll.D10_WIN_INC]
            self.red_tens = len([ten for ten in red_successes if ten >= V5DiceRoll.D10_MAX])
            self.red_ones = len([one for one in self.red_results if one < 2])
            successes += red_successes
        self.num_successes = len(successes)
        if self.red_tens + self.black_tens > 1:
            self.crit = True
            self.num_successes += (self.red_tens + self.black_tens)
        self.margin = self.num_successes - self.difficulty
        if self.margin >= 0:
            if self.red_tens > 0 and self.included_hunger and self.crit:
                self.outcome = V5DiceRoll.RESULT_MESSY_CRIT
            elif self.crit:
                self.outcome = V5DiceRoll.RESULT_CRIT
            else:
                self.outcome = V5DiceRoll.RESULT_WIN
        else:
            if self.red_ones > 0 and self.included_hunger:
                self.outcome = V5DiceRoll.RESULT_BESTIAL_FAIL
            else:
                self.outcome = V5DiceRoll.RESULT_FAIL


class DiceRoller:
    def __init__(self):
        self.current_roll = None
        self.current_opp_roll = None
        self.can_reroll_to_improve = False
        self.can_reroll_to_avert_mc = False
        self.player_wins = False

    def test(self, pool, difficulty, hunger=1, include_hunger=True):
        self.current_opp_roll = None
        self.current_roll = V5DiceRoll(int(pool), int(difficulty), hunger=hunger, include_hunger=include_hunger)
        if self.current_roll.black_failures > 0:
            self.can_reroll_to_improve = True
        if self.current_roll.outcome == V5DiceRoll.RESULT_MESSY_CRIT and self.current_roll.red_tens < 2 and self.current_roll.black_tens < 4:
            self.can_reroll_to_avert_mc = True
        return self.current_roll

    def contest(self, pool1, pool2, hunger=1, include_hunger=True):
        self.current_opp_roll = V5DiceRoll(int(pool2), 0, include_hunger=False)
        self.current_roll = V5DiceRoll(int(pool1), self.current_opp_roll.num_successes, hunger=hunger, include_hunger=include_hunger)
        margin = self.current_roll.num_successes - self.current_opp_roll.num_successes
        self.current_roll.margin = margin
        self.current_roll.opp_ws = self.current_opp_roll.num_successes
        if margin >= 0:
            self.player_wins = True
        if self.current_roll.black_failures > 0:
            self.can_reroll_to_improve = True
        if self.current_roll.outcome == V5DiceRoll.RESULT_MESSY_CRIT and self.current_roll.red_tens < 2 and self.current_roll.black_tens < 4:
            self.can_reroll_to_avert_mc = True
        return self.current_roll

    def reroll_fails(self):
        if self.current_roll.rerolled:
            raise ValueError("Should not be able to reroll a single roll more than once.")
        self.current_roll.rerolled = True
        num_rerolls = min(3, self.current_roll.black_failures)
        for i, d10result in enumerate(self.current_roll.black_results):
            if num_rerolls <= 0:
                break
            if d10result < V5DiceRoll.D10_WIN_INC:
                tmp = Utils.make_dice_roll(V5DiceRoll.D10_MAX, 1)[0]
                print("rerolling a {} at i = {}, and it's now a {}".format(self.current_roll.black_results[i], i, tmp))
                self.current_roll.black_results[i] = tmp
                num_rerolls -= 1
        self.current_roll.calculate()
        return self.current_roll

    def reroll_messy_crit(self):
        if self.current_roll.rerolled:
            raise ValueError("Should not be able to reroll a single roll more than once.")
        if self.current_roll.outcome != V5DiceRoll.RESULT_MESSY_CRIT:
            raise ValueError("This option should only be available if there's a messy critical.")
        self.current_roll.rerolled = True
        num_rerolls = min(3, self.current_roll.black_tens)
        for i, d10result in enumerate(self.current_roll.black_results):
            if num_rerolls <= 0:
                break
            if d10result == V5DiceRoll.D10_MAX:
                self.current_roll.black_results[i] = Utils.make_dice_roll(V5DiceRoll.D10_MAX, 1)[0]
                num_rerolls -= 1
        self.current_roll.calculate()
        return self.current_roll

