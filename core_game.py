from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty

from config import Config
from gui_widgets import GuiUtils
from utils import Utils, ObjectWrapper, DiceRoller, V5DiceRoll
from game_events import GameEvent, Moment, StandardEvents, EventParser
from player_character import PlayerChar


class InGameClock:  # TODO: implement this later
    DAY_MINUTES_MIN = 0
    DAY_MINUTES_MAX = 1439

    def __init__(self, start_time, gui_widget=None):
        self._time = start_time
        self.gui_widget = gui_widget

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, new_time):
        self._time = new_time

    def __iadd__(self, other):
        if Utils.is_number(other):
            self.time = self.time + int(other)


class GameState(EventDispatcher):
    busy = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.busy = False
        self.game_id = None
        self.session_id = None
        self.session_number = 0
        self._hunger = 1
        self._humanity = 7
        # self.game_clock = InGameClock(0)
        self.game_running = False
        self._current_event = None
        self._event_queue = []
        self.temp_dice_roll_moment = None
        configvars = Config.__dict__
        self.attr_names = [getattr(Config, aname) for aname in configvars if str(aname).startswith("AT_")]
        self.skill_names = [getattr(Config, sname) for sname in configvars if str(sname).startswith("SK_")]
        self.discipline_names = [getattr(Config, dname) for dname in configvars if str(dname).startswith("DISC_")]
        self.playerchar = PlayerChar(anames=self.attr_names, snames=self.skill_names, dnames=self.discipline_names)
        self.current_roll = None

    @property
    def hunger(self):
        return self.playerchar.hunger

    @property
    def humanity(self):
        return self.playerchar.humanity

    @property
    def current_event(self):
        return self._current_event

    @current_event.setter
    def current_event(self, new_event):
        self._current_event = new_event

    @property
    def event_queue(self):
        return self._event_queue

    @event_queue.setter
    def event_queue(self, new_queue):
        raise Exception("Shouldn't be reassigning this, probably.")  # TODO: check this against later functionality

    def get_pc_attr(self, attr_name):
        if attr_name == "clan_blurbs":
            return self.playerchar.clan_blurbs
        else:
            raise ValueError("Invalid or protected attribute, \"{}\"".format(attr_name))

    def pc_can_hunt(self):
        if self.hunger > Config.HUNGER_MIN:
            return True
        if self.hunger > Config.HUNGER_MIN_KILL and self.humanity <= Config.KILL_HUNT_HUMANITY_THRESHOLD_INC:
            return True
        return False

    def pc_can_delay_hunt(self):
        if self.hunger < Config.HUNGER_MAX - 1:
            return True
        if self.hunger < Config.HUNGER_MAX and self.humanity > Config.WEAK_TO_HUNGER_HUMANITY_THRESHOLD_INC:
            return True
        if self.humanity >= Config.RESIST_MAX_HUNGER_HUMANITY_THRESHOLD_INC:
            return True
        return False

    def pc_can_drink_swill(self):
        if self.playerchar.clan == Config.CLAN_VENTRUE:
            return False
        if self.playerchar.blood_potency > 2:  # TODO: animal succulence
            return False
        return True

    def get_hunt_choice_label(self):
        if self.hunger > Config.HUNGER_MAX - 1 and self.humanity >= Config.RESIST_MAX_HUNGER_HUMANITY_THRESHOLD_INC:
            return "It hurts too much. Can't think of anything else. I need to feed, before I lose control and do something I regret."
        elif self.hunger > Config.HUNGER_MAX - 1:
            return "Blood... BLOOD! I'M [i]FUCKING [b]STARVING![/b][/i]"
        elif self.hunger > 3:
            return "My veins are dry, my head is pounding... I need to eat. [i]Now.[/i]"
        else:
            return "I need to hunt."


class CoreGame:
    def __init__(self, gui):
        self.gui = gui
        self.state = GameState()
        self.dev_event_loop_tracker = 0
        self.log = None
        self.dice_roller = DiceRoller()
        self.current_roll_summary = None

    def player_input_unblock(self):
        if not self.state.busy:
            self.game_loop()
        else:
            Utils.log("Player input ignored because game is busy!")

    def set_hunger(self, delta, killed=False, innocent=False):
        if killed or self.state.hunger <= Config.HUNGER_MIN_KILL:
            hunger_floor = Config.HUNGER_MIN_KILL
        else:
            hunger_floor = Config.HUNGER_MIN
        # Possible frenzy check.
        new_hunger = Utils.nudge_int_value(self.state.hunger, delta, "Hunger", floor=hunger_floor, ceiling=(Config.HUNGER_MAX + 1))
        self.state.playerchar.hunger = new_hunger
        if killed and innocent and self.state.playerchar.humanity > Config.WEAK_TO_HUNGER_HUMANITY_THRESHOLD_INC:
            Utils.log("~*Humanity loss chime*~")
            self.set_humanity("-=1")
        self.gui.refresh_screen("tab_charsheet")
        self.gui.set_hunger_overlay(self.state.hunger)

    def set_humanity(self, delta):
        new_humanity = Utils.nudge_int_value(self.state.humanity, delta, "Humanity", floor=Config.MIN_HUMANITY, ceiling=Config.MAX_HUMANITY)
        self.state.playerchar.humanity = new_humanity
        self.gui.refresh_screen("tab_charsheet")

    def validate_event(self, event: GameEvent):
        return True if self and event else False  # TODO: implement this if we need to discard events

    def game_running(self):
        return self.state.game_running

    def load_next_event(self):
        if len(self.state.event_queue) < 1:
            return None
        while True:
            new_event = self.state.event_queue.pop(0)  # NOTE: this makes it so that we aren't tracking the discarding of events.
            if self.validate_event(new_event):
                break
        self.state.current_event = new_event
        return self.state.current_event

    def load_standard_event(self, eid):
        self.state.current_event = GameEvent.build_from_txt(filename="intro.txt", eid=eid)
        return self.state.current_event

    def load_game(self, save_path=None):
        self.state.game_running = True
        if save_path:
            pass  # TODO: implement loading savestate here, much later - we'd want to check where we are in existing event
            self.new_session()
            self.log.load()
            self.game_loop()
        else:  # New game, or if I don't get around to save/load functionality, every game.
            starting_event = self.load_standard_event("test_intro")
            self.state.event_queue.append(starting_event)
            self.state.game_id = Utils.generate_random_id_str(label=Config.SAVE_FILE_PREFIX)
            self.new_session()
            if Config.DEV_MODE:
                self.load_test_char_1()
            self.log = GameLog(self.state.session_id)
            self.game_loop(starting_event)

    def im_having_a_moment(self):  # Returns mid for the next moment, or None if sequential.
        moment = self.state.current_event.next_moment()
        if not moment:
            return None, False
        print("current moment we're having: ", moment)
        mtype = Moment.validate_mtype(str(moment.type).lower())
        # ---- Text blurbs
        if mtype == Moment.M_TEXT_BLURB:
            if moment.text and "{" in moment.text and "}" in moment.text:
                m_text = Utils.get_excerpt(moment.text, "{", "}")
                moment.text = EventParser.evaluate_event_param(Config.REF_TEXT, m_text, self.get_exposed_funcs())
            if moment.text:
                self.log.record(moment.text)
                self.gui.main_text.read_line(moment.text)
            if hasattr(moment, Config.REF_GOTO_MOMENT):
                return getattr(moment, Config.REF_GOTO_MOMENT), True
            return None, True  # A text blurb usually just points to the next moment, but blocks for user input.
        # ---- Player choices
        elif mtype == Moment.M_USER_CHOICE:
            prompt, gui_choices = moment.text, []
            for choice in moment.choices:
                if Config.REF_CHOICE_ENABLED in choice:
                    enabled = EventParser.evaluate_event_param(Config.REF_CHOICE_ENABLED, choice[Config.REF_CHOICE_ENABLED], self.get_exposed_funcs())
                else:
                    enabled = True
                gui_choice = {
                    Config.REF_TEXT: None,  # Required, but we have work to do first.
                    Config.REF_GOTO_MOMENT: choice[Config.REF_GOTO_MOMENT],  # Required
                    Config.REF_CHOICE_ENABLED: enabled
                }
                text_val = choice[Config.REF_CHOICE_LABEL]
                if isinstance(text_val, dict) and Config.REF_EVAL_TAG in text_val:
                    gui_choice[Config.REF_TEXT] = EventParser.evaluate_event_param(
                        Config.REF_CHOICE_LABEL, text_val[Config.REF_EVAL_TAG], self.get_exposed_funcs()
                    )
                elif isinstance(text_val, str):
                    gui_choice[Config.REF_TEXT] = text_val
                else:
                    raise ValueError("Choice labels should be either strings or specific dictionaries.")
                if Config.REF_CHOICE_RID in choice:
                    gui_choice[Config.REF_CHOICE_RID] = choice[Config.REF_CHOICE_RID]
                # if Config.REF_CHOICE_SHOWN not in choice or CoreGame.evaluate_choice_shown(choice[Config.REF_CHOICE_SHOWN]):
                if Config.REF_CHOICE_SHOWN not in choice or \
                        EventParser.evaluate_event_param(Config.REF_CHOICE_SHOWN, choice[Config.REF_CHOICE_SHOWN], self.get_exposed_funcs()):
                    gui_choices.append(gui_choice)
            self.gui.main_text.prep_choices()
            self.gui.main_text.create_choice_labels(gui_choices, prompt)
            return None, True
            # raise NotImplemented("Choices are not yet implemented!")
        # ---- V5 dice roll contest
        elif mtype == Moment.M_DICE_ROLL:
            self.gui.main_text.prep_roll()
            self.gui.dice_box.prep_roll()
            self.current_roll_summary = self.get_roll_summary_object(moment.pool, True if moment.opp_pool else False)
            if moment.opp_pool:
                self.state.current_roll = self.dice_roller.contest(
                    pool1=self.current_roll_summary.num_dice, pool2=moment.opp_pool, hunger=self.state.hunger
                )
            elif moment.difficulty:
                self.state.current_roll = self.dice_roller.test(
                    self.current_roll_summary.num_dice, difficulty=moment.difficulty, hunger=self.state.hunger
                )
            else:
                raise AttributeError("Dice Roll moment must have either an opposition pool or flat difficulty!")
            self.current_roll_summary.can_reroll_to_improve = self.dice_roller.can_reroll_to_improve
            self.current_roll_summary.can_reroll_to_avert_mc = self.dice_roller.can_reroll_to_avert_mc
            self.gui.display_roll(self.current_roll_summary, self.state.current_roll)
            return None, True
            # raise NotImplemented("Dice rolls are not yet implemented!")
        # ---- Order to change game state
        elif mtype == Moment.M_STATE_CHANGE:
            if moment.result_func:
                moment.result_func(self.state)  # NOTE: Would need to limit this to toolkit functions if result_func could be loaded from file.
            else:
                EventParser.evaluate_event_param(Config.REF_STATE_CHANGE_EXPR, moment.expr, self.get_exposed_funcs())
            if moment.text:
                self.log.record(moment.text)
                self.gui.main_text.read_line(moment.text)
            block = True if moment.text else False
            if hasattr(moment, Config.REF_GOTO_MOMENT):
                return getattr(moment, Config.REF_GOTO_MOMENT), block
            return None, block
            # raise NotImplemented("State changes are not yet implemented!")
        elif mtype == Moment.M_JUMP_2_EVENT:
            evts = [attr_name for attr_name in vars(GameEvent) if str(attr_name).startswith("EVT")]
            if moment.destination_eid in evts:
                the_event = StandardEvents.get_standard_event(moment.destination_eid, self.state)
            else:
                the_event = None  # TODO: implement this, search event queue?
            self.state.event_queue.remove(self.state.current_event)
            self.state.event_queue.insert(0, the_event)
            self.state.current_event = the_event
            return None, False
        else:
            raise ValueError("Tried to handle a Moment of an invalid type, \"{}\"!".format(mtype))

    def reroll(self, messy_crit=False):
        if not messy_crit:
            self.dice_roller.reroll_fails()
        else:
            self.dice_roller.reroll_messy_crit()
        # cr, crs = self.dice_roller.current_roll, self.current_roll_summary
        self.deal_damage(Config.TRACK_WILL, Config.DMG_FULL_SPF, 1)
        self.confirm_roll()

    def confirm_roll(self):
        outcome, margin = self.state.current_roll.outcome, self.state.current_roll.margin
        roll_moment, actual_outcome_mid = self.state.temp_dice_roll_moment, None
        if outcome == V5DiceRoll.RESULT_WIN:
            actual_outcome_mid = roll_moment.mid_win
        elif outcome == V5DiceRoll.RESULT_FAIL:
            actual_outcome_mid = roll_moment.mid_lose
        if outcome == V5DiceRoll.RESULT_MESSY_CRIT:
            actual_outcome_mid = roll_moment.mid_messycrit
            if actual_outcome_mid is None:
                actual_outcome_mid = roll_moment.mid_crit
            if actual_outcome_mid is None:
                actual_outcome_mid = roll_moment.mid_win
        elif outcome == V5DiceRoll.RESULT_CRIT:
            actual_outcome_mid = roll_moment.mid_crit
            if actual_outcome_mid is None:
                actual_outcome_mid = roll_moment.mid_win
        elif outcome == V5DiceRoll.RESULT_BESTIAL_FAIL:
            actual_outcome_mid = roll_moment.mid_beastfail
            if actual_outcome_mid is None:
                actual_outcome_mid = roll_moment.mid_lose
        self.state.current_event.repoint(mid=actual_outcome_mid, mindex=None)

    def get_roll_summary_object(self, pool_text, has_opp=False):
        roll_obj, pool_stats, num_dice = {}, str(pool_text).split('+'), 0
        roll_obj["pool_text"] = GuiUtils.translate_dice_pool_params(pool_stats)  # " + ".join([str(ps).capitalize() for ps in pool_stats])
        roll_obj["has_opponent"] = has_opp
        roll_obj["bonuses"], bonuskey, bonus_total = False, Config.REF_ROLL_BONUS_PREFIX, 0
        for stat in pool_stats:
            stat = str(stat).capitalize()
            if stat in self.state.playerchar.attrs:
                num_dice += self.state.playerchar.attrs[stat]
            elif stat in self.state.playerchar.skills:
                num_dice += self.state.playerchar.skills[stat]
            elif stat in self.state.playerchar.discipline_levels:
                num_dice += self.state.playerchar.discipline_levels[stat]
            elif stat == Config.AT_CHA or stat == Config.SK_DIPL:
                roll_obj["bonuses"] = True
                if self.state.playerchar.clan == Config.CLAN_NOSFERATU:
                    roll_obj[bonuskey + Config.CLAN_NOSFERATU] = -2
                else:
                    bg_names = [bg[Config.REF_BG_NAME] for bg in self.state.playerchar.backgrounds]
                    if Config.BG_BEAUTIFUL in bg_names:
                        roll_obj[bonuskey + Config.BG_BEAUTIFUL] = 2
            elif self.state.playerchar.clan == Config.CLAN_NOSFERATU and str(stat).lower() == Config.REF_ROLL_FORCE_NOSBANE:
                roll_obj["bonuses"] = True
                roll_obj[bonuskey + Config.CLAN_NOSFERATU] = -2
            elif Utils.is_number(stat) and Utils.has_int(stat):
                roll_obj["bonuses"] = True
                roll_obj[Config.REF_ROLL_EVENT_BONUS] = stat
            else:
                # TODO: backgrounds, banes
                raise ValueError("Stat \"{}\" is not an attribute, skill, or discipline.".format(stat))
        for key in roll_obj:
            if str(key).startswith(bonuskey):
                bonus_total += int(roll_obj[key])
        roll_obj["num_dice"] = num_dice + bonus_total
        roll_obj["bonuses_total"] = bonus_total
        # roll_obj["can_reroll_to_improve"] = self.dice_roller.can_reroll_to_improve
        # roll_obj["can_reroll_to_avert_mc"] = self.dice_roller.can_reroll_to_avert_mc
        return ObjectWrapper.wrap_dict_in_obj(roll_obj)

    def current_event_repoint(self, target_mindex=None, target_mid=None):
        print("self.state.current_event = {}".format(self.state.current_event))
        print("self.state.event_queue:", self.state.event_queue)
        self.state.current_event.repoint(mindex=target_mindex, mid=target_mid)

    def handle_game_event(self, special_event=None):
        self.dev_event_loop_tracker += 1
        event = special_event if special_event else self.state.current_event
        if not event:
            return
        Utils.log("Handling event: {}".format(event.__repr__()))
        if event.index >= len(event.itinerary) and not special_event:
            if len(self.state.event_queue) > 0:
                self.state.event_queue.pop(0)  # TODO: del delete this event? is it possible/desirable?
            if len(self.state.event_queue) < 1:
                self.handle_empty_event_queue()
                return
            self.state.current_event = None
            return
        next_moment_id, blocked_for_input = self.im_having_a_moment()
        print("We had a moment, returning: ", next_moment_id, blocked_for_input)
        if not blocked_for_input or event.itinerary[event.index].type != Moment.M_DICE_ROLL:  # Waits to call event.repoint() for dice roll moments.
            event.repoint(mindex=None, mid=next_moment_id)
        else:
            self.state.current_event = event  # NOTE: Special events should not be dice rolls.
            self.state.temp_dice_roll_moment = event.itinerary[event.index]

        if not blocked_for_input:
            try:
                self.handle_game_event()
            except Exception as e:
                Utils.log("Unexplained {} occurred in game event handler, tracker # is {}.".format(e.__class__, self.dev_event_loop_tracker), e)

    def game_loop(self, special_event=None):
        if not self.state.current_event:
            Utils.log("No current event; let's load a new one.")
            self.load_next_event()
            if not self.state.current_event and len(self.state.event_queue) < 1:
                self.handle_empty_event_queue()
        if special_event:
            self.handle_game_event(special_event)
        else:
            self.handle_game_event()

    def handle_empty_event_queue(self):
        Utils.log("We've reached the end of the event queue.")
        pass  # TODO: implement default haven event
        if self.state.playerchar.clan and self.state.playerchar.predator_type:
            back_to_haven = StandardEvents.get_standard_haven_hub_event(self)
            self.state.event_queue.append(back_to_haven)
        else:
            print("We're missing either a clan ({}) or predator type ({})!".format(self.state.playerchar.clan, self.state.playerchar.predator_type))
            # init_post_intro = NonStandardEvents.get_test_playerchar_event(gamestate=self.state)
            init_post_intro = GameEvent.build_from_txt("clan_pt_choice.txt", eid="whatevs")
            self.state.event_queue.append(init_post_intro)
        self.state.current_event = self.state.event_queue[0]
        self.game_loop()

    def new_session(self):
        sesh = int(self.state.session_number)
        self.state.session_id = "{}-S#{}".format(self.state.game_id, str(sesh + 1).zfill(5))
        self.gui.pc_ref = self.state.playerchar
        if self.log:
            self.log.s_id = self.state.session_id

    def print_log(self):
        if self.log:
            self.log.print()
        else:
            Utils.log("No game log exists to print.")

    def deal_damage(self, tracker, dtype, amount):
        if tracker == Config.TRACK_HP:
            self.state.playerchar.hp.damage(dtype, amount)
        else:
            self.state.playerchar.will.damage(dtype, amount)
        self.gui.refresh_screen("tab_charsheet")

    def available_pc_will(self):
        willpower = self.state.playerchar.will
        return willpower.boxes - (willpower.spf_damage + willpower.agg_damage)

    def choose_predator_type_wrapper(self, pt):
        self.state.playerchar.choose_predator_type(pt=pt)
        self.gui.refresh_screen("tab_charsheet")

    def add_background_wrapper(self, bg):
        self.state.playerchar.apply_background(background=bg)
        self.gui.refresh_screen("tab_charsheet")

    def get_exposed_funcs(self):
        return ObjectWrapper.wrap_dict_in_obj({
            "set_hunger": self.set_hunger,
            "choose_clan": self.state.playerchar.choose_clan,
            "choose_pt": self.choose_predator_type_wrapper,
            "get_pc_attr": self.state.get_pc_attr,
            "add_background": self.add_background_wrapper,
            "get_hunt_choice_label": self.state.get_hunt_choice_label,
            "pc_can_hunt": self.state.pc_can_hunt,
            "pc_can_delay_hunt": self.state.pc_can_delay_hunt,
            "pc_can_drink_swill": self.state.pc_can_drink_swill,
            "pc_available_willpower": self.available_pc_will
        })

    def load_test_char_1(self):
        self.state.playerchar.choose_clan(Config.CLAN_NOSFERATU)
        self.state.playerchar.choose_predator_type(Config.PT_ALLEYCAT)
        self.state.playerchar.apply_background(Config.CHAR_BACKGROUNDS["test_bg_med_student"])
        self.gui.refresh_screen("tab_charsheet")

    @staticmethod
    def evaluate_choice_enabled(eval_tag):  # TODO: replace above code with these
        return True

    @staticmethod
    def evaluate_choice_shown(eval_tag):
        return True


class GameLog:
    def __init__(self, s_id=None):
        self.s_id = s_id
        self.entries = []

    def record(self, entry):
        self.entries.append("{}::  {}".format(self.s_id, str(entry)))

    def print(self):
        for i, entry in enumerate(self.entries):
            Utils.log("{}. {}".format(i, entry))

    def load(self):
        raise NotImplemented("No log loading yet.")
