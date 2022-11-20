from typing import List

from config import Config
from utils import Utils


class Moment:  # A single event within an Event, consisting of a type and a unique mid for reference. Normally handled sequentially.
    M_TEXT_BLURB = "blurb"
    M_USER_CHOICE = "choice"
    M_STATE_CHANGE = "state_change"
    M_DICE_ROLL = "roll"
    M_JUMP_2_EVENT = "jump_to_event"

    def __init__(self, mid=None):
        self.type = None
        self.mid = mid

    def __repr__(self):
        if self.__class__ == Moment.__class__:
            return "<M0-#{} >".format(self.mid)
        else:
            return "<{}#{}".format(self.type, self.mid)

    @staticmethod
    def validate_mtype(mstr):
        if mstr == Moment.M_TEXT_BLURB or mstr[:1] == Moment.M_TEXT_BLURB[:1]:
            return Moment.M_TEXT_BLURB
        elif mstr == Moment.M_USER_CHOICE or mstr[:1] == Moment.M_USER_CHOICE[:1]:
            return Moment.M_USER_CHOICE
        elif mstr == Moment.M_DICE_ROLL or mstr[:1] == Moment.M_DICE_ROLL[:1]:
            return Moment.M_DICE_ROLL
        elif mstr == Moment.M_STATE_CHANGE or mstr[:1] == Moment.M_STATE_CHANGE[:1]:
            return Moment.M_STATE_CHANGE
        elif mstr is not None and mstr is "":
            return Moment.M_TEXT_BLURB
        else:
            return None


Script = List[Moment]


class TextBlurb(Moment):  # A blurb is just text that gets read into the GUI.
    def __init__(self, mid=None, text="<Insert text here>", goto=None):
        super().__init__(mid=mid)
        self.type = Moment.M_TEXT_BLURB
        self.text = text
        self.goto = goto

    def __repr__(self):
        return super().__repr__() + "  |  {}".format(Utils.truncate_string(self.text, 20))


class UserChoice(Moment):  # A list of decisions, each with text and the mid of another Moment that serves as its "consequence".
    def __init__(self, mid, text="", choices=None):
        super().__init__(mid=mid)
        self.type = Moment.M_USER_CHOICE
        self.text = text
        self.choices = choices if choices else []

    def __repr__(self):
        return super().__repr__() + ", ".join(["{}".format(Utils.truncate_string(c[Config.REF_CHOICE_LABEL])) for c in self.choices])


class StateChange(Moment):  # Payload is a function that takes the gamestate as a parameter and can operate on it.
    def __init__(self, mid=None, result_func=None, expr=None, goto=None, text=None):
        super().__init__(mid=mid)
        self.type = Moment.M_STATE_CHANGE
        self.goto = goto
        self.text = text  # text optional
        if result_func is None and expr is None:
            raise ValueError("Either a function or an expression is required.")
        self.result_func = result_func
        self.expr = expr


class DiceRoll(Moment):  # A V5 d10 contest, against a set difficulty or an opponent's pool, and consequences for each result.
    def __init__(self, player_pool, mid=None, difficulty=3, opposing_pool=None, win_mid=None, lose_mid=None):
        super().__init__(mid=mid)
        self.type = Moment.M_DICE_ROLL
        self.pool = player_pool
        self.difficulty = difficulty
        self.opp_pool = opposing_pool
        self.mid_win, self.mid_lose = win_mid, lose_mid
        self.mid_messycrit = self.mid_crit = self.mid_beastfail = None


class EventJump(Moment):
    def __init__(self, mid=None, destination_eid=None, text=None):
        super().__init__(mid=mid)
        self.type = Moment.M_JUMP_2_EVENT
        self.destination_eid = destination_eid
        self.text = text


class GameEvent:  # A packaged bundle of moments that constitute a scene. Building blocks of the game.
    EVT_HUB_MAIN = "haven-hub-default"
    EVT_HUNT_RANDOM = "hunt-random"
    EVT_SORTIE_GENERAL = "defense-random"
    EVT_DAYBREAK = "next-sunrise"

    def __init__(self, etype, eid=None, itinerary: Script = ()):
        self._itinerary = list(itinerary)
        self.type = etype
        self.eid = eid
        if not self.eid:
            self.eid = Utils.generate_random_id_str(label="gevent_{}".format(self.type))
        self.index = 0
        if len(self._itinerary) > 0:
            # self.index = self._itinerary[0].mid
            self.repoint(mindex=None, mid=self._itinerary[0].mid)

    def __repr__(self):
        return "<Event#{} :: {} moments, index = {} >".format(self.eid, len(self.itinerary), self.index)

    def __str__(self):
        event_str = self.__repr__() + "\n ^--moments:"
        for i, moment in enumerate(self.itinerary):
            event_str += "\n{}.  {}".format(str(i+1).zfill(2), moment.__repr__())
        return event_str

    @property
    def itinerary(self):
        return self._itinerary

    @itinerary.setter
    def itinerary(self, new_itin):
        self._itinerary = new_itin

    def next_moment(self):
        if 0 > self.index >= len(self.itinerary):
            return None
        return self.itinerary[self.index]

    def repoint(self, *not_used, mindex: (int, None), mid: (str, None)):
        if mindex is None and mid is None:
            self.index += 1
        elif mid is None:
            self.index = mindex
        else:
            old_index = self.index
            indexed_moment = [(index, elem) for index, elem in enumerate(self.itinerary) if elem.mid == mid]
            if len(indexed_moment) < 1:
                raise ValueError("Failed mid lookup in repoint(); no match for mid=\"{}\" (old index was {})!".format(mid, old_index))
            try:
                self.index = indexed_moment[0][0]  # NOTE: Moment ids must be unique within an event.
                Utils.log("event.index changed via mid: {} --> {}".format(old_index, self.index))
            except Exception as e:
                Utils.log("Unexplained {} occurred during mid lookup in repoint()".format(e.__class__), e)

    @staticmethod
    def build_from_txt(filename, eid):
        event_txt_lines = Utils.read_text_from_file(Config.PATH_TEXT_EVENTS + filename, mode='r')
        evt = GameEvent(etype="event_from_text", eid=eid)
        current_moment, i, goto_tag = None, 0, "goto=\""
        c_enabled_tag, c_shown_tag = "enabled={", "shown={"
        while i < len(event_txt_lines):
            line, line_tokens, tag, goto = event_txt_lines[i], None, None, None
            special_token = line.startswith(">|")
            if special_token:
                line_tokens = line.split('|')
                tag = line_tokens[1]
            if current_moment is None and ((not special_token) or "label" in line_tokens[1]):  # TextBlurb
                b_text, i_jump = GameEvent.compile_single_blurb(event_txt_lines, i)
                tb_mid = tag.split('"')[1] if tag else None
                line_tokens = b_text.split('|')
                for btt in line_tokens:
                    if goto_tag in btt:
                        goto = btt.split('"')[1]
                    elif "label" in btt:
                        tb_mid = btt.split('"')[1]
                    else:
                        b_text = btt
                if goto:
                    print("FFFF")
                # if b_text.find(goto_tag) > -1:
                #     line_tokens = b_text.split(goto_tag)
                #     b_text, goto = line_tokens[0], line_tokens[1].strip("\"\n")
                #     goto = goto.split('"')[0]
                if b_text:
                    b_text_tokens = b_text.split('|')
                    tokens_dropped = 0
                    for ibt in range(len(b_text_tokens) - 1, -1, -1):
                        bt = b_text_tokens[ibt]
                        if not bt or bt == ">":
                            b_text_tokens.remove(bt)
                            tokens_dropped += 1
                    # if len(b_text_tokens) > 1:
                    b_text = b_text_tokens[-1]
                    evt.itinerary.append(TextBlurb(text=b_text.strip('\n'), goto=goto, mid=tb_mid))
                i = i_jump
            else:
                if i == 0 and "event_start" not in tag:
                    raise ValueError("There should be an event tag in the first line.")
                if Utils.is_iterable(tag) and "choice_start" in tag:  # start of UserChoice
                    uc_mid = tag.split('"')[1]
                    current_moment = UserChoice(mid=uc_mid, text=line_tokens[2].strip('\n'))
                elif Utils.is_iterable(tag) and "choice_end" in tag and isinstance(current_moment, UserChoice):  # end of UserChoice
                    evt.itinerary.append(current_moment)
                    current_moment = None
                elif isinstance(current_moment, UserChoice):  # UserChoice options
                    if not line.strip("\n"):
                        i += 1
                        continue
                    line_tokens, cl_text, choice_opt = line.split('|'), "", {}
                    for ltoken in line_tokens:
                        if c_enabled_tag in ltoken:
                            choice_opt[Config.REF_CHOICE_ENABLED] = Utils.get_excerpt(ltoken, "{", "}")
                        elif c_shown_tag in ltoken:
                            choice_opt[Config.REF_CHOICE_SHOWN] = Utils.get_excerpt(ltoken, "{", "}")
                        elif goto_tag in ltoken:
                            goto = choice_opt[Config.REF_GOTO_MOMENT] = ltoken.split(goto_tag)[1].strip("\"\n")
                        else:
                            cl_text = choice_opt[Config.REF_CHOICE_LABEL] = ltoken
                    # cl_text, goto = line_tokens[0], line_tokens[1].split(goto_tag)[1].strip("\"\n")
                    if not goto:
                        raise ValueError("Every choice option needs a goto mid link.")
                    if cl_text and cl_text != "\n":
                        current_moment.choices.append(choice_opt)
                elif Utils.is_iterable(tag) and "roll" in tag:
                    r_text, i_jump = GameEvent.compile_single_blurb(event_txt_lines, i)
                    line_tokens, dice_roll = r_text.split('|'), DiceRoll("wits+inspection")
                    for ltoken in line_tokens:
                        if "{" in ltoken and "}" in ltoken:
                            contest = Utils.get_excerpt(ltoken, "{", "}").split('#')
                            dice_roll.pool, challenge = contest[0], contest[1]
                            if "diff" in challenge:
                                dice_roll.difficulty = challenge.split("diff")[1]
                            elif "pool" in challenge:
                                dice_roll.opp_pool = challenge.split("pool")[1]
                            else:
                                raise ValueError("An enemy pool or base difficulty is required for a DiceRoll object!")
                        elif "roll=\"" in ltoken:
                            dice_roll.mid = ltoken.split('"')[1]
                        elif (Config.REF_WIN + "=\"") in ltoken:
                            dice_roll.mid_win = ltoken.split('"')[1]
                        elif (Config.REF_FAIL + "=\"") in ltoken:
                            dice_roll.mid_lose = ltoken.split('"')[1]
                        elif (Config.REF_CRIT + "=\"") in ltoken:
                            dice_roll.mid_crit = ltoken.split('"')[1]
                        elif (Config.REF_MESSYCRIT + "=\"") in ltoken:
                            dice_roll.mid_messycrit = ltoken.split('"')[1]
                        elif (Config.REF_BEASTFAIL + "=\"") in ltoken:
                            dice_roll.mid_beastfail = ltoken.split('"')[1]
                    evt.itinerary.append(dice_roll)
                    i = i_jump
                elif Utils.is_iterable(tag) and "statechange" in tag:  # StateChange should always be able to fit on one line.
                    sc_text, sc_expr, goto = None, None, None
                    for ltoken in line_tokens:
                        if "text=\"" in ltoken:
                            sc_text = ltoken.split('"')[1]
                        elif "{" in ltoken and "}" in ltoken:
                            sc_expr = ltoken.split('{')[1].split('}')[0]
                        elif goto_tag in ltoken:
                            goto = ltoken.split(goto_tag)[1].strip("\"\n")
                    mid_in_tag = tag.split('"')
                    sc = StateChange(mid=mid_in_tag[1] if len(mid_in_tag) > 1 else mid_in_tag[0], goto=goto, expr=sc_expr, text=sc_text)
                    evt.itinerary.append(sc)
                elif "event_end" in tag:
                    break
                elif i > 0:
                    raise NotImplemented("We haven't implemented anything past this!")
            i += 1
        return evt

    @staticmethod
    def compile_single_blurb(lines, index):
        blurb_text, end_i = "", index
        for i in range(index, len(lines) - 1):
            line = lines[i]
            if line == "\n" or not line:
                end_i = i
                break
            blurb_text += line + "\n"
        return blurb_text, end_i


class EventParser:  # TODO: mitigate some of the issues with eval being used here
    @staticmethod
    def evaluate_event_param(key: str, expression, toolkit):
        if key == Config.REF_CHOICE_SHOWN or \
                key == Config.REF_CHOICE_ENABLED or \
                False:
            return EventParser.eval_event_bool(expression, toolkit)
        elif key == Config.REF_STATE_CHANGE_EXPR:
            return EventParser.eval_event_state_change(expression, toolkit)
        elif key == Config.REF_TEXT or key == Config.REF_CHOICE_LABEL:
            return EventParser.eval_event_text(expression, toolkit)
        raise ValueError("Invalid event evaluation parameter key \"{}\".".format(key))

    @staticmethod
    def eval_event_bool(expr, toolkit):
        if expr is None or expr == "":  # If the expression doesn't exist or is empty, we assume it should evaluate to True.
            return True
        evl = eval(expr, {}, {"tk": toolkit})
        print("BOOL EVAL RESULT from expression \"{}\": {}".format(expr, evl))
        return evl

    @staticmethod
    def eval_event_text(expr, toolkit):
        if expr is None or expr == "":
            return ""
        evl = eval(expr, {}, {"tk": toolkit})
        print("STRING EVAL RESULT from expression \"{}\": {}".format(expr, evl))
        return evl

    @staticmethod
    def eval_event_state_change(expr, toolkit):
        if expr is None or expr == "":
            raise ValueError("Invalid expression encountered during attempted state change.")
        evl = eval(expr, {}, {"tk": toolkit})
        print("state change EVAL RESULT from expression \"{}\": {}".format(expr, evl))
        return evl


class StandardEvents:
    @staticmethod
    def get_standard_event(etype, game):
        if etype == GameEvent.EVT_HUB_MAIN:
            return StandardEvents.get_standard_haven_hub_event(game)
        elif etype == GameEvent.EVT_HUNT_RANDOM:
            return StandardEvents.get_standard_hunt_event(game)
        elif etype == GameEvent.EVT_SORTIE_GENERAL:
            return StandardEvents.get_standard_sortie_event(game)
        elif etype == GameEvent.EVT_DAYBREAK:
            return StandardEvents.get_standard_new_day_event(game)
        else:
            raise ValueError("No standard event of type \"{}\".".format(etype))

    @staticmethod
    def get_standard_haven_hub_event(game):
        shhe = GameEvent("standard_haven_hub")
        status_text = "You make your way back to your haven."
        game.gui.sm.change_screen("tab_haven")
        hub_itin = shhe.itinerary
        hub_itin.append(TextBlurb(text=status_text))
        base_hub_choice = UserChoice(Config.SEM_HUB_MAIN, "What do you want to do?")
        hunt_choice_label = "hunt_choice"
        base_hub_choices = [
            {
                Config.REF_CHOICE_LABEL: {Config.REF_EVAL_TAG: "tk.get_hunt_choice_label()"},
                Config.REF_GOTO_MOMENT: "hub-hunt-choice",
                Config.REF_CHOICE_ENABLED: "tk.pc_can_hunt()",
                Config.REF_CHOICE_RID: hunt_choice_label
            },
            {
                Config.REF_CHOICE_LABEL: "I need to do something impossible!",
                Config.REF_GOTO_MOMENT: "invisible-choice",
                Config.REF_CHOICE_SHOWN: "1 + 1 == 3"
            },
            {
                Config.REF_CHOICE_LABEL: "I think tonight's the night for some self-improvement.",
                Config.REF_GOTO_MOMENT: "hub-training-choice",
            },
            {
                Config.REF_CHOICE_LABEL: "I'm getting worried. I need to deal with some of these threats before they deal with me.",
                Config.REF_GOTO_MOMENT: "hub-defense-choice"
            }
        ]
        for choice in base_hub_choices:
            if Config.REF_CHOICE_RID not in choice or choice[Config.REF_CHOICE_RID] != hunt_choice_label:
                if Config.REF_CHOICE_ENABLED in choice:
                    choice[Config.REF_CHOICE_ENABLED] = "(" + choice[Config.REF_CHOICE_ENABLED] + ") and tk.pc_can_delay_hunt()"
                else:
                    choice[Config.REF_CHOICE_ENABLED] = "tk.pc_can_delay_hunt()"

        base_hub_choice.choices = base_hub_choices
        hub_itin.append(base_hub_choice)
        # TODO: placeholders; implement these as actual choices with their own events
        hub_itin.append(TextBlurb(mid="hub-hunt-choice", text="You set out into the night to hunt prey, to slake your endless Hunger."))
        hub_itin.append(TextBlurb(text="It takes some time, but you find a suitable vessel and drink your fill."))
        hub_itin.append(StateChange(expr="tk.set_hunger(\"-=2\")", goto=Config.SEM_HUB_MAIN))
        hub_itin.append(TextBlurb(mid="hub-training-choice", text="Why not? You'll live a long time if you play your cards right."))
        hub_itin.append(TextBlurb(text="You spend several late hours at 24-hour gym, getting swole.", goto=Config.SEM_HUB_MAIN))
        hub_itin.append(TextBlurb(mid="hub-defense-choice", text="The walls are closing in. Other licks, hunters, God knows what else."))
        hub_itin.append(TextBlurb(text="You have to do something, so you go out and crack some skulls.", goto=Config.SEM_HUB_MAIN))
        return shhe

    @staticmethod
    def get_standard_hunt_event(game):
        pass

    @staticmethod
    def get_standard_new_day_event(game):
        pass

    @staticmethod
    def get_standard_sortie_event(game):
        pass


class NonStandardEvents:
    @staticmethod
    def get_test_playerchar_event(gamestate):
        pc = gamestate.playerchar
        tpce = GameEvent("player_char_test_build")
        pc_itin = tpce.itinerary
        clan_choices, clan_responses = [], []
        playable_clans = [clan for clan in Config.__dict__ if str(clan).startswith("CLAN")]
        print("PLAYABLE CLANS:\n", playable_clans)
        clan_choice = UserChoice(mid="devchar", text="As one of...")
        pc_itin.append(clan_choice)

        def get_clan_choice_func(p_clan_name):
            return lambda gs: gs.playerchar.choose_clan(p_clan_name)

        for pc_clan in playable_clans:
            clan_name = getattr(Config, pc_clan)
            clan_blurbs = getattr(Config, "BLURBS_CLANS")[clan_name]
            clan_epithet, post_clan_mid = clan_blurbs[clan_name][Config.REF_CLAN_EPITHET], "post_{}".format(clan_name[0])
            clan_choice_mid = "chosen_clan_{}".format(clan_name)
            clan_choices.append({
                Config.REF_CHOICE_LABEL: "{}, Clan {}".format(str(clan_epithet).capitalize(), clan_name),
                Config.REF_GOTO_MOMENT: clan_choice_mid
            })
            pc_itin.append(StateChange(mid=clan_choice_mid, result_func=get_clan_choice_func(clan_name), goto=post_clan_mid))
            cb_text = "{tk.get_pc_attr(\"clan_blurbs\")[\"" + Config.REF_CLAN_CHOSEN + "\"]}"
            pc_itin.append(TextBlurb(mid=post_clan_mid, text=cb_text, goto="pt_preamble"))
        clan_choice.choices = clan_choices
        pc_itin.append(TextBlurb(mid="pt_preamble", text=(
            "So in light of such difficulties, you've developed a set of useful strategies and techniques for getting what you need. " +
            "Some would say they're just a set of bad habits."
        )))
        pc_itin.append(UserChoice(mid="pt_choice", text="Either way, you hunt by..."))
        available_pts, pt_choices = [pt for pt in Config.__dict__ if str(pt).startswith("PT_")], []
        print("PREDATOR TYPES:\n", available_pts)
        for pc_pt in available_pts:
            pred_type = getattr(Config, pc_pt)
            pt_choice_mid = "chosen_pt_{}".format(pred_type)
            pt_choices.append({
                Config.REF_CHOICE_LABEL: "{}",
                Config.REF_GOTO_MOMENT: pt_choice_mid
            })
        return tpce
