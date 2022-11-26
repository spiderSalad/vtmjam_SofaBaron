from os import environ
from utils import Utils

if Utils.get_platform() == 'win':
    environ['KIVY_GL_BACKEND'] = 'angle_sdl2'
    environ['GST_REGISTRY'] = '%USERPROFILE%\\gst_registry.bin'

from kivy.config import Config as KivyConfig

GAME_WINDOW_WIDTH, GAME_WINDOW_HEIGHT = 1440, 810
KivyConfig.set('graphics', 'width', str(GAME_WINDOW_WIDTH))
KivyConfig.set('graphics', 'height', str(GAME_WINDOW_HEIGHT))

from kivy.app import App
from kivy.core.window import Window
from kivy.resources import resource_add_path  # , resource_find
from kivy.uix.floatlayout import FloatLayout

from gui_widgets import MainGuiFrame, MainConsole, DevConsole, ScreenJuggler, MainTextFeed, DarkPackDisclaimer, \
    NullScreen, CharacterScreen, HavenScreen, DomainScreen, CreditsScreen, SettingsScreen, OverlayFrame, GuiUtils, \
    EventScreen
from config import Config
from core_game import CoreGame
from audio import AudioHandler, init_audio


class MainWidget(FloatLayout):
    from user_input import on_keyboard_down, on_keyboard_up, keyboard_closed

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "pc_ref"):
            self.pc_ref = None
        self.dice_box = None
        self.temp_summary, self.temp_roll = None, None
        if Utils.is_desktop():
            self.keyboard = Window.request_keyboard(self.keyboard_closed, self)
            self.keyboard.bind(on_key_down=self.on_keyboard_down)
            self.keyboard.bind(on_key_up=self.on_keyboard_up)

    def on_game_init(self):
        self.set_gui_state(GuiUtils.GUI_STATE_MAIN_MENU)
        self.audio.default_test_track.loop()
        self.dice_box = self.sm.get_screen("tab_dicegame")

    def game_running(self):
        return self.game.game_running()

    def refresh_screen(self, screen_name):
        self.sm.get_screen(screen_name).update(self.pc_ref)

    def set_gui_state(self, gui_state: str):
        self.console.ids["start_game_button"].text = "Dice" if self.game_running() else "New Game"
        if gui_state == GuiUtils.GUI_STATE_MAIN_MENU:
            GuiUtils.basic_toggle_display(self.main_text, False)
            GuiUtils.basic_toggle_display(self.console.ids["tab_charsheet"], False)
            GuiUtils.basic_toggle_display(self.console.ids["tab_haven"], False)
            GuiUtils.basic_toggle_display(self.console.ids["tab_domain"], False)
        elif gui_state == GuiUtils.GUI_STATE_PLAY_EVENT:
            GuiUtils.basic_toggle_display(self.main_text, True)
            GuiUtils.basic_toggle_display(self.console.ids["tab_charsheet"], True)
            GuiUtils.basic_toggle_display(self.console.ids["tab_haven"], True)
            GuiUtils.basic_toggle_display(self.console.ids["tab_domain"], True)
        elif gui_state == GuiUtils.GUI_STATE_PLAY_HAVEN:
            GuiUtils.basic_toggle_display(self.main_text, True)
            GuiUtils.basic_toggle_display(self.console.ids["tab_charsheet"], True)
            GuiUtils.basic_toggle_display(self.console.ids["tab_haven"], True)
            GuiUtils.basic_toggle_display(self.console.ids["tab_domain"], True)
        else:
            raise ValueError("Invalid GUI gui_state \"{}\"".format(gui_state))

    def start_game_default(self):
        self.game.load_game()
        self.set_gui_state(GuiUtils.GUI_STATE_PLAY_EVENT)

    def primary_game_button(self):
        if self.game_running():
            self.set_gui_state(GuiUtils.GUI_STATE_PLAY_EVENT)
            self.sm.change_screen("tab_dicegame")
        else:
            self.start_game_default()

    def display_roll(self, roll_summary=None, game_roll=None):
        if roll_summary and game_roll:
            self.temp_summary, self.temp_roll = roll_summary, game_roll
        self.sm.change_screen("tab_dicegame")
        delim, pool_readout, roll_result, full_result_text = "   ", "", "", ""
        pool_readout = str(self.temp_summary.pool_text).replace(" ", delim)
        if not self.dice_box:
            self.dice_box = self.sm.get_screen("tab_dicegame")
        if self.temp_summary.has_opponent:
            test_summary = "versus {}, margin is {}".format(self.temp_roll.opp_ws, self.temp_roll.margin)
        else:
            test_summary = "difficulty {}, margin is {}".format(self.temp_roll.difficulty, self.temp_roll.margin)
        roll_result = "{}! {} successes out of {} dice. ({})".format(
            self.temp_roll.outcome, self.temp_roll.num_successes, self.temp_roll.pool, test_summary
        )
        full_result_text = delim.join(["< {} >".format(dr) for dr in self.temp_roll.black_results])
        full_result_text += delim + delim.join(["[color=#ef0404]< {} >[/color]".format(dr) for dr in self.temp_roll.red_results])
        self.dice_box.dice_pool_readout.text = pool_readout
        self.dice_box.roll_readout.text = roll_result
        self.dice_box.full_dice_result.text = full_result_text
        self.dice_box.roll_record.text += "Roll:   " + "  |  ".join([pool_readout, full_result_text, roll_result]) + "\n"
        if self.game.available_pc_will() > 0:
            self.dice_box.better_btn.disabled = not self.temp_summary.can_reroll_to_improve or self.temp_roll.rerolled
            self.dice_box.no_messy_btn.disabled = not self.temp_summary.can_reroll_to_avert_mc or self.temp_roll.rerolled
        else:
            self.dice_box.better_btn.disabled = True
            self.dice_box.no_messy_btn.disabled = True

    def reroll_from_main(self, messy_crit=False):
        self.game.reroll(messy_crit=messy_crit)
        self.display_roll()

    def set_hunger_overlay(self, hunger):
        self.overlay.show_hunger_overlay(hunger)

    def block_from_main(self):
        self.main_text.next_button.disabled = True
        self.dice_box.continue_button.disabled = True
        # self.game.input_block()

    def input_advance_from_main(self):
        self.main_text.next_button.disabled = False
        self.dice_box.continue_button.disabled = True
        self.game.player_input_unblock()

    def advance_via_roll_continue_btn(self):
        self.game.confirm_roll()
        self.input_advance_from_main()

    def advance_via_next_btn(self):
        self.input_advance_from_main()

    def user_gui_choice(self, index=None, goto=None):
        if index is None and goto is None:
            raise ValueError("Missing argument - either choice index or choice moment tag.")
        else:
            self.game.current_event_repoint(target_mindex=index, target_mid=goto)
        self.input_advance_from_main()

    def on_keypress(self, keycode):
        if not self.game_running() or not Config.KEY_INPUT_ENABLED:
            return
        if keycode == 'enter':
            if not self.main_text.next_button.disabled:
                self.input_advance_from_main()
        elif str(keycode).isdigit():
            self.main_text.main_text_pick_choice(goto=self.main_text.choice_list[int(keycode) - 1])

    @staticmethod
    def on_press_quit():
        App.get_running_app().stop()
        quit()


class VtmJamSofaBaronApp(App):
    CUSTOM_RED = GuiUtils.SOFA_BARON_RED

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gui = None
        self.game = None

    def build(self):
        self.gui = MainWidget()
        self.gui.audio = AudioHandler()
        init_audio(self.gui.audio)
        self.gui.game = self.game = CoreGame(self.gui)
        self.gui.sm = ScreenJuggler(self.gui)
        self.gui.stem = MainGuiFrame(self.gui)
        self.gui.overlay = OverlayFrame()
        self.gui.add_widget(self.gui.stem)
        self.gui.add_widget(self.gui.overlay)
        self.gui.dpd_string = Config.DP_DISCLAIMER
        self.gui.add_widget(DarkPackDisclaimer())
        self.gui.console = MainConsole(self.gui)
        self.gui.sm.add_screenlike_widget(NullScreen(name="empty_screen"))
        self.gui.sm.add_screenlike_widget(EventScreen(name="tab_dicegame", gui=self.gui))
        self.gui.sm.add_screenlike_widget(CharacterScreen(name="tab_charsheet", gui=self.gui))
        self.gui.sm.add_screenlike_widget(HavenScreen(name="tab_haven", gui=self.gui))
        self.gui.sm.add_screenlike_widget(DomainScreen(name="tab_domain", gui=self.gui))
        self.gui.sm.add_screenlike_widget(CreditsScreen(name="tab_credits", gui=self.gui))
        self.gui.sm.add_screenlike_widget(SettingsScreen(name="tab_settings", gui=self.gui))
        self.gui.main_text = MainTextFeed(self.gui)
        self.gui.stem.add_widget(self.gui.sm)
        self.gui.stem.add_widget(self.gui.main_text)
        self.gui.stem.add_widget(self.gui.console)
        if Config.DEV_MODE:
            self.gui.dev_console = DevConsole(self.gui)
            self.gui.add_widget(self.gui.dev_console)
        self.gui.on_game_init()
        return self.gui


if __name__ == '__main__':
    resource_add_path(Utils.get_resource_path(""))
    VtmJamSofaBaronApp().run()
