from kivy.core.audio.audio_sdl2 import SoundLoader

from utils import Utils


class AudioWrapper:
    def __init__(self, audio_path, audio_id="audio-wrapper-object", ffpyplayer_bug=True, internal_volume=1):
        self.audio = SoundLoader.load(audio_path)
        self.id = audio_id
        self.FFPYPLAYER_BUG = ffpyplayer_bug
        self.internal_volume = internal_volume

    def play(self, loop=False):
        self.audio.loop = loop
        if self.FFPYPLAYER_BUG:
            self.audio.seek(0)
        self.audio.play()

    def loop(self):
        self.play(True)

    def stop(self):
        self.audio.stop()

    def seek(self, position):
        self.audio.seek(position)

    def set_volume(self, volume):
        self.audio.volume = self.internal_volume * volume

    def get_state(self):
        return self.audio.state

    def get_pos(self):
        return self.audio.get_pos()

    def get_length(self):
        return self.audio.length

    def get_source(self):
        return self.audio.source


class AudioHandler:
    def __init__(self, default_volume=1, ffpyplayer_bug=True):
        self.default_volume = default_volume
        self._sfx_volume = self.default_volume
        self._music_volume = self.default_volume
        self.sound_list = []
        self.track_list = []
        self.FFPYPLAYER_BUG = ffpyplayer_bug

    def register(self, name, path, volume=-1, audio_type="sound"):
        audio_obj = AudioWrapper(path, name, ffpyplayer_bug=self.FFPYPLAYER_BUG)
        setattr(self, "_{}".format(name), audio_obj)
        if volume < 0.0:
            volume = self.default_volume
        audio_obj.internal_volume = volume
        if str(audio_type).lower() == "sound":
            audio_obj.set_volume(self.sfx_volume)
            self.sound_list.append(audio_obj)
        else:
            audio_obj.set_volume(self.music_volume)
            self.track_list.append(audio_obj)
        return audio_obj

    def register_track(self, name, path, volume=-1):
        if volume < 0.0:
            volume = self.default_volume
        return self.register(name, path, volume, "track")

    @property
    def sfx_volume(self):
        return self._sfx_volume

    @sfx_volume.setter
    def sfx_volume(self, volume):
        self._sfx_volume = volume
        for sound in self.sound_list:
            sound.set_volume(self.sfx_volume)

    @property
    def music_volume(self):
        return self._music_volume

    @music_volume.setter
    def music_volume(self, volume):
        self._music_volume = volume
        for track in self.track_list:
            track.set_volume(self.music_volume)


def init_audio(ah: AudioHandler):
    # sfx
    ah.ui_swap1 = ah.register("ui_swap1", "audio/sound/86886__timbre__74829-jobro-heartbeat-timbre-s-variant-1b-loop.mp3")
    # music
    ah.default_test_track = ah.register_track("default_test_track", "audio/music/Darkstar83 - Shadow Walker.mp3")
    Utils.log("Audio initialized.")

