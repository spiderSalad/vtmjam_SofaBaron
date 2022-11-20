import kivy.uix.button
from kivy.graphics import Rectangle, Color
from kivy.properties import BooleanProperty, NumericProperty, ListProperty, Clock
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

from config import Config
from utils import Utils


class GuiUtils:
    SOFA_BARON_RED = (0.7, 0, 0, 0.8)
    CHOICE_RED = "#ff0f0f"
    DISABLED_GREY = "#353535"
    ENABLED_WHITE = "#efefef"

    GUI_STATE_MAIN_MENU = "gui_state_main_menu"
    GUI_STATE_PLAY_HAVEN = "gui_state_play_haven"
    GUI_STATE_PLAY_EVENT = "gui_state_play_event"

    @staticmethod
    def basic_toggle_display(widget, show):
        if hasattr(widget, "saved_attrs"):
            if show:
                widget.height, widget.size_hint_y, widget.opacity, widget.disabled = widget.saved_attrs
                del widget.saved_attrs
        elif not show:
            widget.saved_attrs = widget.height, widget.size_hint_y, widget.opacity, widget.disabled
            widget.height, widget.size_hint_y, widget.opacity, widget.disabled = 0, None, 0, True

    @staticmethod
    def translate_dice_pool_params(pool_params):
        adjusted_params = []
        for param in pool_params:
            if param == Config.REF_ROLL_FORCE_NOSBANE:
                adjusted_params.append(GuiUtils.malus_color("Nosferatu"))
            elif param == Config.BG_BEAUTIFUL:
                adjusted_params.append(GuiUtils.bonus_color("Beautiful"))
            else:
                adjusted_params.append(str(param).capitalize())
        return " + ".join([str(p) for p in adjusted_params])

    @staticmethod
    def bonus_color(txt):
        return "[color=#23ed23]{}[/color]".format(txt)

    @staticmethod
    def malus_color(txt):
        return "[color=#ed2323]{}[/color]".format(txt)


class MainGuiFrame(FloatLayout):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui


class OverlayFrame(AnchorLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self.texture_rect = None
        self.default_src = "images/1x1.png"
        self.bind(size=self.on_resize)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.texture_rect = Rectangle(pos=self.pos, size=self.size, source=self.default_src)

    def show_hunger_overlay(self, hunger):
        if not Utils.has_int(hunger) or hunger < 3:
            olsource = self.default_src
        else:
            olsource = "images/overlays/hunger_{}.png".format(["three", "four", "five"][min(hunger, Config.HUNGER_MAX) - 3])
        self.texture_rect.source = olsource

    def on_resize(self, widget, new_size):
        self.texture_rect.size = new_size


class ScreenJuggler(ScreenManager):
    def __init__(self, gui, **kwargs):
        super().__init__(**kwargs)
        self.gui = gui
        self.screen_buttons = {}
        self.transition = FadeTransition()
        self.tab_whitelist = ("tab_credits", "tab_settings")

    def change_screen(self, screen_name):
        if self.gui.game_running() or screen_name in self.tab_whitelist:
            self.current = screen_name

    def add_screenlike_widget(self, screenlike):
        if not screenlike.gui:
            screenlike.gui = self.gui
        screenlike.console = screenlike.gui.console
        self.add_widget(screenlike)

    def on_pre_enter_response(self, screenlike):
        shown_btn = self.gui.console.get_associated_console_button(screenlike.name)
        allbtns = self.gui.console.get_console_buttons()
        for btn in allbtns:
            btn.disabled = False
        if shown_btn:
            shown_btn.disabled = True
        self.gui.audio.ui_swap1.play()


class Screenlike(Screen):
    def __init__(self, gui=None, **kwargs):
        super().__init__(**kwargs)
        self.gui = gui

    def on_pre_enter(self, *args):
        self.manager.on_pre_enter_response(self)

    def update(self, pc_ref):
        Utils.log("Unimplemented update() called for {} \"{}\".".format(self.__class__, self.name))


class NullScreen(Screenlike):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0)


class EventScreen(Screenlike):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(self.ids)
        self.dice_roll_console = self.ids["dice_roll_console"]
        self.roll_readout, self.roll_record = self.ids["roll_readout"], self.ids["roll_record"]
        self.dice_pool_readout, self.full_dice_result = self.ids["dice_pool_readout"], self.ids["full_dice_result"]
        self.full_dice_result.markup = self.roll_record.markup = self.dice_pool_readout.markup = True
        self.better_btn, self.no_messy_btn = self.ids["reroll_for_better"], self.ids["reroll_for_safety"]
        self.continue_button = self.ids["continue"]

    def prep_roll(self):
        # self.better_btn.disabled = True
        # self.no_messy_btn.disabled = True
        self.continue_button.disabled = False

    def on_click_continue(self):
        self.gui.advance_via_roll_continue_btn()


class CharacterScreen(Screenlike):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pc = None

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self.update(self.gui.game.state.playerchar)

    def update(self, pc_ref):
        dossier, attrs, skills = self.ids["cs_dossier"], self.ids["cs_attributes"], self.ids["cs_skills"]
        dossier.update(pc_ref)
        attrs.update(pc_ref, Config.REF_ATTRS)
        skills.update(pc_ref, Config.REF_SKILLS)


class HavenScreen(Screenlike):
    pass


class DomainScreen(Screenlike):
    pass


class CreditsScreen(Screenlike):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.credits_json = None
        self.credits_container = BoxLayout()
        self.credits_text = Label()
        self.credits_text.font_size = '18sp'
        # self.credits_text.text_size = self.credits_text.size
        # self.credits_text.halign, self.credits_text.valign = 'left', 'top'
        self.credits_text.bind(on_ref_press=CreditsScreen.hyperlink)
        self.add_widget(self.credits_container)
        self.path = Config.PATH_JSON + "credits.json"
        try:
            self.credits_json = Utils.get_json_from_file(self.path)
            # print(json.dumps(self.credits_json, sort_keys=True, indent=2))
            self.display_credits()
        except FileNotFoundError as fnfe:
            Utils.log("{}: Couldn't find file \"{}\".".format(fnfe.__class__, self.path), fnfe)
        except Exception as e:
            Utils.log("Unexplained {} loading JSON credits file.".format(e.__class__), e)

    @staticmethod
    def hyperlink(widget, value):
        Utils.open_url(str(value))

    def sort_credits(self, credits_json=None):
        if credits_json is None:
            credits_json = self.credits_json
        sorted_credits = {}
        for credit in credits_json:
            ctype = credit["type"]
            if ctype and ctype not in sorted_credits:
                sorted_credits[ctype] = []
            if ctype:
                sorted_credits[ctype].append(credit)
        # print("END OF SORT_CREDITS:\n", sorted_credits, "\n", self.credits_json)
        return sorted_credits

    def display_credits(self, sorted_credits=None):
        if sorted_credits is None:
            sorted_credits = self.sort_credits()
        credits_markup = "Contributing Creators:\n"
        for ctype in sorted_credits:
            cat_text = ' ' * 2
            cat_text += "{t}s ({c}):\n".format(t=ctype.replace("_", " ").capitalize(), c=len(sorted_credits[ctype]))
            for cred in sorted_credits[ctype]:
                cred_text = ' ' * 4
                cred_text += "{cname}".format(cname=cred["name"])
                for wk in cred["works"]:
                    work_text = ' ' * 6
                    work_text += "{}".format(wk["name"])
                    work_text += " [ref=\"{url}\"][u](License)[/u][/ref]".format(url=wk["licenseUrl"])
                    cred_text += "\n{}".format(work_text)
                if "website" in cred and cred["website"]:
                    cred_text += ' ' * 4
                    cred_text += "\n[ref=\"{url}\"](Website Link)[/ref]".format(url=cred["website"])
                for soc in cred["socials"]:
                    soc_text = ' ' * 6
                    soc_text += "[ref=\"{url}\"]{sms}: ({hdl})[/ref]".format(url=soc["url"], sms=soc["site"], hdl=soc["handle"])
                    cred_text += "\n{}".format(soc_text)
                cat_text += "\n{}".format(cred_text)
            credits_markup += "\n\n{}".format(cat_text)
        self.credits_text.text = credits_markup
        self.credits_text.markup = True
        self.credits_container.add_widget(self.credits_text)


class VolumeSlider(BoxLayout):
    sound_value = NumericProperty(0)

    def __init__(self, audio_type="sound", gui=None, default_volume=0.25, **kwargs):
        super().__init__(**kwargs)
        self.gui = gui
        self.audio_type = audio_type
        self.label = Label()
        self.label.text, self.label.size_hint = self.audio_type.capitalize(), (0.3, 1)
        self.add_widget(self.label)
        self.slider = Slider()
        self.slider.min, self.slider.max = 0, 100
        self.slider.bind(value=self.on_value_ch)
        self.slider.value = default_volume * 100
        self.add_widget(self.slider)

    def on_value_ch(self, widget, value):
        self.sound_value = min(1, max(value / 100, 0))
        self.label.text = "{}: {:.1f}%".format(self.audio_type.capitalize(), self.sound_value * 100)
        if self.gui is not None:
            if self.audio_type == "sound":
                self.gui.audio.sfx_volume = self.sound_value
            else:
                self.gui.audio.music_volume = self.sound_value
        else:
            raise ValueError("{}: Missing gui reference!".format(self.__class__))


class SettingsScreen(Screenlike):
    CUSTOM_RED = GuiUtils.SOFA_BARON_RED

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        sfx_slider = VolumeSlider("sound", gui=self.gui)
        music_slider = VolumeSlider("music", gui=self.gui)
        audio_settings = self.ids["audio_settings"]
        audio_settings.add_widget(sfx_slider)
        audio_settings.add_widget(music_slider)


class MainConsole(BoxLayout):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui

    def get_associated_console_button(self, name: str):
        if name in self.ids:
            return self.ids[name]
        return None

    def get_console_buttons(self):
        fbtns = []
        for wid in self.ids:
            if isinstance(self.ids[wid], kivy.uix.button.ButtonBehavior):
                fbtns.append(self.ids[wid])
        return fbtns


class MainTextFeed(FloatLayout):
    hidden = BooleanProperty(False)
    CUSTOM_RED = ListProperty(GuiUtils.SOFA_BARON_RED)

    def __init__(self, gui):
        super().__init__()
        self.anchor_x, self.anchor_y = "right", "bottom"
        self.gui = gui
        self.readout, self.readout_container = self.ids["readout"], self.ids["readout_container"]
        self.next_button, self.display_switch = self.ids["next_text_button"], self.ids["display_switch"]
        self.choices_container, self.choice_prompt = self.ids["choices_container"], self.ids["choice_prompt"]
        self.choice_list_container = self.ids["choice_list_container"]
        self.readout.markup = True
        self.choice_list = []
        self.default_feed_height = self.readout.height
        self._text = ""
        self.on_toggle_display(self.display_switch)
        # self.readout_container.bind(on_touch_down=self.on_click_text)

    def on_toggle_display(self, widget):
        self.hidden = widget.state != "down"
        widget.text = "Show Text" if self.hidden else "Hide Text"

        # def gooey(widg, lvl):
        #     GuiUtils.basic_toggle_display(widg, not self.hidden)

        # GuiUtils.traverse_widget_tree(gooey, self, exempt=[self, widget])
        GuiUtils.basic_toggle_display(self.readout_container, not self.hidden)
        GuiUtils.basic_toggle_display(self.next_button, not self.hidden)
        GuiUtils.basic_toggle_display(self.choices_container, not self.hidden)
        self.gui.audio.ui_swap1.play()

    # def on_click_text(self, *args):
    #     touch = args[1]
    #     if touch.is_touch:
    #         self.gui.input_advance_from_main()

    def on_click_next(self):
        self.gui.advance_via_next_btn()

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, new_text):
        self._text = new_text
        self.readout.text = self._text

    def read_line(self, txt):
        if Config.DEV_MODE:
            Utils.log("\nReading line: {}".format(txt))
        self.text = txt

    def append_line(self, txt):
        self.text = self.text + '\n' + txt

    def clear_text(self):
        self.text = ""

    def prep_choices(self):
        self.clear_text()
        self.next_button.disabled = True

    def prep_roll(self):
        self.next_button.disabled = True

    def main_text_pick_choice(self, index=None, goto=None):
        self.gui.user_gui_choice(index=index, goto=goto)
        self.clear_choices()

    def clear_choices(self):
        GuiUtils.basic_toggle_display(self.choices_container, False)
        self.choice_prompt.text = ""
        for i in range(len(self.choice_list_container.children) - 1, -1, -1):  # Iterate backwards so we don't skip any elements.
            child = self.choice_list_container.children[i]
            if isinstance(child, PressLabel):
                self.choice_list_container.remove_widget(child)
        self.choice_list = []

    def create_choice_labels(self, choices, prompt):
        self.clear_choices()
        self.choice_prompt.text = prompt
        choice_set_id = Utils.generate_random_id_str(4)

        def get_choice_result_func(goto, main_text_self):
            def choice_result_func():
                main_text_self.main_text_pick_choice(goto=goto)
            return choice_result_func
        for i, choice in enumerate(choices):
            if Config.REF_CHOICE_SHOWN not in choice or choice[Config.REF_CHOICE_SHOWN]:  # TODO evaluate
                gt = choice[Config.REF_GOTO_MOMENT]
                self.choice_list.append(gt)
                clabel = PressLabel(bid="choice#{}-option#{}".format(choice_set_id, int(i+1)), on_press=get_choice_result_func(gt, self))
                clabel.markup, cl_enabled = True, (Config.REF_CHOICE_ENABLED not in choice or choice[Config.REF_CHOICE_ENABLED])  # TODO: evaluate
                clabel.disabled = not cl_enabled
                cl_color = "[color={}]".format(GuiUtils.ENABLED_WHITE if cl_enabled else GuiUtils.DISABLED_GREY)
                clabel.text = "{}{}. {}[/color]".format(cl_color, int(i+1), choice[Config.REF_TEXT])
                self.choice_list_container.add_widget(clabel)
        GuiUtils.basic_toggle_display(self.choices_container, True)


class DevConsole(BoxLayout):
    def __init__(self, gui, **kwargs):
        super().__init__(**kwargs)
        self.gui = gui
        self.dev_readout = self.ids["dev_readout"]


class DarkPackDisclaimer(AnchorLayout):
    pass


class PlusMinusButton(Button):
    def __init__(self, btn_text="+", **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (40, 40)
        self.text = btn_text


class FitButton(Button):
    def __init__(self, buffer_width=15, custom_height=None, **kwargs):
        super().__init__(**kwargs)
        self.custom_height = custom_height
        self.size_hint = (None, None if self.custom_height else 1)
        if self.custom_height:
            self.height = custom_height
        self.buffer_width = buffer_width
        self.halign = "center"
        self.valign = "middle"

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        Clock.schedule_once(self.update_texture_size_next_frame, 0)

    def update_texture_size_next_frame(self, *args):
        self.width = self.texture_size[0] + self.buffer_width


class PressLabel(ButtonBehavior, Label):
    def __init__(self, bid, font_size="20sp", align=("left", "middle"), on_press=None, **kwargs):
        super().__init__(**kwargs)
        self.bid = bid
        self.on_press_param = on_press
        self.font_size = font_size
        self.halign, self.valign = align
        self.size_hint = (1, 1)
        self.saved_attrs = {"color": self.color}

    def on_touch_down(self, touch):
        super().on_touch_down(touch)
        if self.collide_point(*touch.pos):
            # self.saved_attrs["color"] = self.color
            self.color = GuiUtils.CHOICE_RED

    def on_touch_up(self, touch):
        super().on_touch_up(touch)
        if self.collide_point(*touch.pos):
            self.color = self.saved_attrs["color"]

    def on_press(self):
        if self.on_press_param:
            self.on_press_param()

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        Clock.schedule_once(self.update_text_size_next_frame, 0)

    def update_text_size_next_frame(self, *args):
        self.text_size = self.width, None


class DotScore(BoxLayout):
    def __init__(self, score_label, score=0, dot_color="red", **kwargs):
        self.score_label = score_label
        self._score = score
        self.dot_color = dot_color
        self.max = Config.MAX_SCORE
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self.orientation = "horizontal"
        self.padding = [2, 0, 5, 0]
        self.spacing = 0
        self.label = Label(text=score_label)
        self.label.size_hint = (0.5, 1)
        self.label.padding = (0, 0)
        self.label.halign, self.label.valign = "right", "middle"
        self.label.font_size = "16sp"
        number_word = Config.DOT_NUMBERS[self.score]
        self.dots = Image(source="{}dots_{}_{}.png".format(Config.PATH_GUI_IMAGES, self.dot_color, number_word))
        self.dots.size_hint = (0.45, 1)
        self.add_widget(self.label)
        self.add_widget(self.dots)
        print("Dotscore - label.width = {}".format(self.label.width))

    def __repr__(self):
        # For some reason super().__init() calls __repr__() so we can't reference anything established in DotScore.__init__()
        return "<dotscore| \"{}\" :: {} dot{}>".format(self.score_label, self.score, "s" if self.score != 1 else "")

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, new_score):
        do_update = (self._score != new_score)
        self._score = new_score
        if do_update:
            self.update()

    def update(self):
        number_word = Config.DOT_NUMBERS[self.score]
        self.dots.source = "{}dots_{}_{}.png".format(Config.PATH_GUI_IMAGES, self.dot_color, number_word)


class CSDossier(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols, self.rows = 2, 4
        self.orientation = "lr-tb"
        self.padding = (5, 5, 5, 5)
        self.size_hint = (0.42, 0.2)
        self.pos_hint = {"x": 0.05, "top": 0.85}
        # self.row_force_default = True
        # self.row_default_height = "30dp"
        self.pc_name = self.pc_clan = None
        self.pc_humanity = self.pc_humanity_box = self.pc_hunger = self.pc_hunger_box = None
        self.pc_humanity_tagline = self.pc_hunger_tagline = None
        self.hp_track = self.will_track = None
        char_info = Utils.get_json_from_file(Config.PATH_JSON + "char_info.json")
        self.humanity_scores, self.hunger_quotes = char_info["humanity_scores"], char_info["hunger_quotes"]
        self.init_name_clan()
        self.init_undeath_params()
        self.init_trackers()

    def init_name_clan(self):
        self.pc_name = Label(text="Name:  ", font_size="18sp")
        self.pc_clan = Label(text="Clan:  ", font_size="18sp")
        self.pc_name.size_hint, self.pc_clan.size_hint = (1, 1), (1, 1)
        # self.pc_name.width = self.pc_name.texture_size[0]
        self.pc_name.halign = self.pc_clan.halign = "left"
        self.pc_name.valign = self.pc_clan.valign = "middle"
        self.pc_name.size_hint, self.pc_clan.size_hint = (1, 1), (1, 1)
        self.add_widget(self.pc_name)
        self.add_widget(self.pc_clan)

    def init_undeath_params(self):
        self.pc_humanity = DotScore(score_label="Humanity", score=4, dot_color="bright")
        self.pc_hunger = DotScore(score_label="Hunger", score=3)
        self.pc_humanity_box, self.pc_hunger_box = BoxLayout(orientation="vertical"), BoxLayout(orientation="vertical")
        self.pc_humanity_tagline, self.pc_hunger_tagline = Label(text="hoomanity"), Label(text="hangry")
        self.pc_humanity_tagline.halign = self.pc_hunger_tagline.halign = "left"
        self.pc_humanity_tagline.valign = self.pc_hunger_tagline.valign = "middle"
        self.pc_humanity_tagline.markup, self.pc_hunger_tagline.markup = True, True
        self.pc_humanity_box.add_widget(self.pc_humanity)
        self.pc_hunger_box.add_widget(self.pc_hunger)
        self.add_widget(self.pc_hunger_box)
        self.add_widget(self.pc_humanity_box)
        self.add_widget(self.pc_hunger_tagline)
        self.add_widget(self.pc_humanity_tagline)

    def init_trackers(self):
        self.hp_track, self.will_track = TrackerLine(5, trackertype=Config.TRACK_HP), TrackerLine(5, trackertype=Config.TRACK_WILL)
        self.add_widget(self.hp_track)
        self.add_widget(self.will_track)

    def update(self, pc_ref):
        pass  # TODO: update damage trackers and humanity/hunger scores here
        self.pc_name.text, self.pc_clan.text = "Alias:  \"{}\"".format(pc_ref.nickname), "Clan:  {}".format(pc_ref.clan)
        hanger, hoomanity = pc_ref.hunger, pc_ref.humanity - 3
        self.pc_hunger_tagline.text = self.hunger_quotes[hanger][max(0, hoomanity - 2)]
        self.pc_humanity_tagline.text = self.humanity_scores[hoomanity - 1]
        self.pc_hunger.score = hanger
        self.pc_humanity.score = hoomanity
        self.hp_track.aggravated, self.hp_track.superficial = pc_ref.hp.agg_damage, pc_ref.hp.spf_damage
        self.will_track.aggravated, self.will_track.superficial = pc_ref.will.agg_damage, pc_ref.will.spf_damage


class ScorePanel(GridLayout):
    def __init__(self, score_key, **kwargs):
        super().__init__(**kwargs)
        self.dotscores = {}
        self.padding = (5, 5, 15, 5)
        self.min_score = Config.MIN_SCORE_ATTR if score_key == "AT_" else Config.MIN_SCORE
        self.score_names = [getattr(Config, score_name) for score_name in Config.__dict__ if str(score_name).startswith(score_key)]
        for score in self.score_names:
            self.dotscores[score] = DotScore(score_label=score, score=self.min_score)
            self.add_widget(self.dotscores[score])

    def update(self, pc_ref, scores_dict_key):
        scores_dict = getattr(pc_ref, scores_dict_key)
        for dskey in scores_dict:
            if dskey in self.dotscores:
                self.dotscores[dskey].score = scores_dict[dskey]


class CSAttributePanel(ScorePanel):
    def __init__(self, **kwargs):
        super().__init__(score_key="AT_", **kwargs)
        self.cols, self.rows = 3, 3
        self.orientation = "tb-lr"
        self.size_hint = (0.42, 0.25)
        self.pos_hint = {"x": 0.05, "top": 0.63}


class CSSkillPanel(ScorePanel):
    def __init__(self, **kwargs):
        super().__init__(score_key="SK_", **kwargs)
        self.cols, self.rows = 3, 5
        self.orientation = "tb-lr"
        self.size_hint = (0.42, 0.4)
        self.pos_hint = {"right": 0.95, "top": 0.85}


class TrackerBox(Image):
    PREFIXES = {
        Config.TRACK_HP: "Health",
        Config.TRACK_WILL: "Willpower",
        Config.DISC_FORTITUDE: "Fort",
        Config.DMG_SPF: "superficial",
        Config.DMG_AGG: "aggravated",
        Config.DMG_NONE: "clear"
    }

    def __init__(self, trackertype=Config.TRACK_HP, init_dtype=Config.DMG_NONE, fort=False, init_source="", orientation="horizontal", **kwargs):
        super().__init__(**kwargs)
        self.trackertype = trackertype
        self.size_hint = (None, 1) if orientation == "horizontal" else (1, None)
        self.size = (30, 30)
        self._dtype = init_dtype
        self._fort = fort
        if init_source:
            self.source = init_source
        else:
            self.set_image()

    @property
    def dtype(self):
        return self._dtype

    @dtype.setter
    def dtype(self, new_dtype):
        do_update = (new_dtype != self._dtype)
        self._dtype = new_dtype
        if do_update:
            self.set_image()

    @property
    def fort(self):
        return self._fort

    @fort.setter
    def fort(self, new_fort):
        do_update = (new_fort != self._fort)
        self._fort = new_fort
        if do_update:
            self.set_image()

    def set_image(self):
        self.source = "{}{}{}_{}.png".format(
            Config.PATH_GUI_IMAGES, TrackerBox.PREFIXES[self.trackertype],
            TrackerBox[Config.DISC_FORTITUDE] if self.fort else "", TrackerBox.PREFIXES[self.dtype]
        )


class TrackerLine(BoxLayout):
    def __init__(self, total, trackertype=Config.TRACK_HP, init_spf=0, init_agg=0, fort_bonus=0, orientation="horizontal", **kwargs):
        super().__init__(**kwargs)
        self.trackertype = trackertype
        self.orientation = orientation
        self.size_hint = (1, None)
        self.height = "50dp"
        # self.spacing = [1, 1]
        ltext = "Health" if self.trackertype == Config.TRACK_HP else "Willpower"
        self.label = Label(text=ltext)
        # self.label.pos_hint = {"center_y": 0.5}
        self.box_container = BoxLayout(orientation=self.orientation)
        self.box_container.pos_hint = {"center_y": 0.5}
        if self.orientation == "horizontal":
            self.label.halign, self.label.valign = "right", "middle"
            self.label.size_hint = (0.4, 1)
            self.box_container.size_hint = (0.6, 1)
        else:
            self.label.halign, self.label.valign = "center", "bottom"
            self.label.size_hint = (1, 0.14)
            self.box_container.size_hint = (1, 0.84)
        self.label.text_size = (self.label.width + 5, self.label.height)
        self.total, self.fort_bonus = total, fort_bonus
        self._aggravated = init_agg
        self._superficial = init_spf
        self.boxes = []
        self.add_widget(self.label)
        self.add_widget(self.box_container)
        self.update()

    @property
    def aggravated(self):
        return self._aggravated

    @aggravated.setter
    def aggravated(self, new_agg):
        do_update = (self._aggravated != new_agg)
        self._aggravated = new_agg
        if do_update:
            self.update()

    @property
    def superficial(self):
        return self._superficial

    @superficial.setter
    def superficial(self, new_spf):
        do_update = (self._superficial != new_spf)
        self._superficial = new_spf
        if do_update:
            self.update()

    def update(self):
        for i in range(0, self.total + self.fort_bonus):
            if i < self.aggravated:
                dtype = Config.DMG_AGG
            elif i < self.aggravated + self.superficial:
                dtype = Config.DMG_SPF
            else:
                dtype = Config.DMG_NONE
            fort = True if (self.fort_bonus > 0 and i >= self.total) else False
            if len(self.boxes) <= i:
                the_box = TrackerBox(trackertype=self.trackertype, init_dtype=dtype, fort=fort)
                self.boxes.append(the_box)
                self.box_container.add_widget(the_box)
            else:
                self.boxes[i].dtype = dtype
                self.boxes[i].fort = fort

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        Clock.schedule_once(self.update_text_size_next_frame, 0)

    def update_text_size_next_frame(self, *args):
        self.label.text_size = (self.label.width + 5, self.label.height)

