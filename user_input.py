from config import Config


def keyboard_closed(self):
    self.keyboard.unbind(on_key_down=self.on_keyboard_down)
    self.keyboard.unbind(on_key_up=self.on_keyboard_up)
    self.keyboard = None


def on_keyboard_down(self, keyboard, keycode, text, modifiers):
    return True


def on_keyboard_up(self, keyboard, keycode):
    key = keycode[1]
    if key in Config.KEY_INPUT_WATCH:
        self.on_keypress(key)
    elif keycode[0] == 13:
        self.on_keypress(key)
    return True
