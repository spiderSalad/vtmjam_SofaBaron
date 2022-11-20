import math

from config import Config
from utils import Utils


class Tracker:
    def __init__(self, pc, boxes: int, trackertype: str, armor: int = 0, bonus: int = 0):
        self.playerchar = pc
        self.trackertype = trackertype
        self._boxes = boxes
        self._armor = armor
        self.armor_active = False
        self._bonus = bonus
        self.spf_damage = 0
        self.agg_damage = 0

    @property
    def boxes(self):
        return self._boxes

    @boxes.setter
    def boxes(self, new_num_boxes: int):
        self._boxes = new_num_boxes

    @property
    def armor(self):  # Blocks superficial damage prior to halving.
        if self.trackertype == Config.TRACK_HP:
            return self.playerchar.get_fort_toughness_armor()
        return self._armor

    @armor.setter
    def armor(self, new_armor_val):
        self._armor = new_armor_val

    @property
    def bonus(self):
        if self.trackertype == Config.TRACK_HP:
            return self.playerchar.get_fort_resilience_bonus()
        return self._bonus

    @bonus.setter
    def bonus(self, new_bonus: int):
        self._bonus = new_bonus

    def damage(self, dtype, amount):
        total_boxes = self.boxes + self.bonus

        temp_armor = self.armor if self.armor_active else 0

        dented = False
        injured = False
        true_amount = amount
        if dtype == Config.DMG_SPF:
            true_amount = math.ceil(float(amount) / 2)

        for point in range(int(true_amount)):
            if temp_armor > 0:
                dented = True
                temp_armor -= 1
                continue

            clear_boxes = total_boxes - (self.spf_damage + self.agg_damage)
            if clear_boxes > 0:  # clear spaces get filled first
                self.playerchar.impair(True, self.trackertype)
                if dtype == Config.DMG_SPF or dtype == Config.DMG_FULL_SPF:
                    self.spf_damage += 1
                else:
                    self.agg_damage += 1
                Utils.log("====> damage " + str(point) + ": filling a clear space")
            elif self.spf_damage > 0:  # if there are no clear boxes, tracker is filled with a mix of aggravated and superficial damage
                self.playerchar.impair(True, self.trackertype)
                self.spf_damage -= 1
                self.agg_damage += 1  # if there's any superficial damage left, turn it into an aggravated
                Utils.log("====> damage " + str(point) + ": removing a superficial and replacing with aggravated")

            if self.agg_damage >= total_boxes:
                # A tracker completely filled with aggravated damage = game over: torpor, death, or a total loss of faculties, face and status
                self.playerchar.handle_demise(self.trackertype)
                Utils.log("====> damage " + str(point) + ": oh shit you dead")

            injured = True
        if dented and not injured:
            # renpy.sound.queue(audio.pc_hit_fort_melee, u'sound')  # TODO: add sounds here
            pass
        elif injured:
            # renpy.sound.queue(audio.stab2, u'sound')
            pass

    def mend(self, dtype, amount):
        if dtype == Config.DMG_SPF or dtype == Config.DMG_FULL_SPF:
            damage = self.spf_damage
            self.spf_damage = max(damage - amount, 0)
        else:
            damage = self.agg_damage
            self.agg_damage = max(damage - amount, 0)


class PlayerChar:
    def __init__(self, anames, snames, dnames):
        self.nickname = "That lick from around the way"
        self.pronouns = {}  # TODO: implement this
        self.clan = None
        self.predator_type = None
        self.blood_potency = 1
        self._hunger = 1
        self._humanity = 7
        self.hp, self.will = Tracker(self, 3, Config.TRACK_HP), Tracker(self, 3, Config.TRACK_WILL)
        self.crippled, self.shocked = False, False
        self.clan_blurbs = {}
        self.anames, self.snames, self.dnames = anames, snames, dnames
        self.attrs = {}
        self.skills = {}
        self._backgrounds = []
        self.available_disciplines = {}
        self.discipline_levels = {}
        self.powers = []
        self.reset_charsheet_stats()

    @property
    def hunger(self):
        return self._hunger

    @hunger.setter
    def hunger(self, new_hunger):
        self._hunger = max(0, min(new_hunger, Config.HUNGER_MAX + 1))
        if self.hunger > Config.HUNGER_MAX:
            print("Hunger tested at 5; frenzy check?")  # TODO: frenzy check
            self.hunger = Config.HUNGER_MAX
        else:
            Utils.log("Hunger now set at {}".format(self.hunger))

    @property
    def humanity(self):
        return self._humanity

    @humanity.setter
    def humanity(self, new_humanity):
        self._humanity = new_humanity

    @property
    def backgrounds(self):
        return self._backgrounds

    def reset_charsheet_stats(self):
        for aname in self.anames:
            self.attrs[aname] = Config.MIN_SCORE_ATTR
        for sname in self.snames:
            self.skills[sname] = Config.MIN_SCORE
        for dname in self.dnames:
            self.available_disciplines[dname] = Config.VAL_DISC_LOCKED
            self.discipline_levels[dname] = Config.MIN_SCORE

    def validate_charsheet_stats(self):
        for aname in self.anames:
            self.attrs[aname] = max(Config.MIN_SCORE_ATTR, min(self.attrs[aname], Config.MAX_SCORE))
        for sname in self.snames:
            self.skills[sname] = max(Config.MIN_SCORE, min(self.skills[sname], Config.MAX_SCORE))

    def recalculate_stats(self):
        self.reset_charsheet_stats()
        self.apply_xp()
        for bg in self.backgrounds:
            Utils.log("Applying background: ", bg)
            for bg_stat_name in bg:
                if bg_stat_name in self.attrs:
                    self.attrs[bg_stat_name] += bg[bg_stat_name]
                elif bg_stat_name in self.skills:
                    self.skills[bg_stat_name] += bg[bg_stat_name]
            if Config.REF_ATTRS_ALL in bg:
                for attr in self.attrs:
                    self.attrs[attr] += bg[Config.REF_ATTRS_ALL]
            if Config.REF_SKILLS_ALL in bg:
                for skill in self.skills:
                    self.skills[skill] += bg[Config.REF_SKILLS_ALL]
        self.validate_charsheet_stats()
        self.recalibrate_trackers()

    def recalibrate_trackers(self):
        self.hp.boxes = int(self.attrs[Config.AT_STA]) + 3
        self.will.boxes = int(self.attrs[Config.AT_COM]) + int(self.attrs[Config.AT_RES])

    def apply_background(self, background: (dict, str)):
        bg = background
        if isinstance(background, str):
            bg = Config.CHAR_BACKGROUNDS[background]
        self._backgrounds.append(bg)
        self.recalculate_stats()

    def apply_xp(self):
        return self  # TODO: implement this

    def impair(self, impaired, tracker_type):
        if tracker_type == Config.TRACK_HP:
            self.crippled = impaired
        elif tracker_type == Config.TRACK_WILL:
            self.shocked = impaired

    def get_fort_resilience_bonus(self):
        if Config.POWER_FORTITUDE_HP not in self.powers:
            return 0
        return self.discipline_levels[Config.DISC_FORTITUDE]

    def get_fort_toughness_armor(self):
        if Config.POWER_FORTITUDE_TOUGH not in self.powers:
            return 0
        return self.discipline_levels[Config.DISC_FORTITUDE]

    def choose_clan(self, clan):
        self.clan = clan
        self.clan_blurbs = Config.BLURBS_CLANS[self.clan]
        if clan == Config.CLAN_NOSFERATU:
            self.available_disciplines[Config.DISC_ANIMALISM] = Config.VAL_DISC_INCLAN
            self.available_disciplines[Config.DISC_OBFUSCATE] = Config.VAL_DISC_INCLAN
            self.available_disciplines[Config.DISC_POTENCE] = Config.VAL_DISC_INCLAN
            # self.clan_blurbs[Config.REF_CLAN_CHOSEN] = "Your curse makes feeding a hassle. People don't react well to getting a good look at you."
        elif clan == Config.CLAN_RAVNOS:
            self.available_disciplines[Config.DISC_ANIMALISM] = Config.VAL_DISC_INCLAN
            self.available_disciplines[Config.DISC_OBFUSCATE] = Config.VAL_DISC_INCLAN
            self.available_disciplines[Config.DISC_PRESENCE] = Config.VAL_DISC_INCLAN
            # self.clan_blurbs[Config.REF_CLAN_CHOSEN] = "Feeding isn't the problem so much as finding a place to crash afterward."
        elif clan == Config.CLAN_VENTRUE:
            self.available_disciplines[Config.DISC_DOMINATE] = Config.VAL_DISC_INCLAN
            self.available_disciplines[Config.DISC_PRESENCE] = Config.VAL_DISC_INCLAN
            self.available_disciplines[Config.DISC_FORTITUDE] = Config.VAL_DISC_INCLAN
            # self.clan_blurbs[Config.REF_CLAN_CHOSEN] = "You have certain... dietary restrictions. It's not easy being a picky vampire."
        else:
            raise ValueError("Invalid clan \"{}\".".format(clan))

    def choose_predator_type(self, pt):
        self.predator_type = pt
        if pt == Config.PT_ALLEYCAT:
            self.humanity -= 1
        elif pt == Config.PT_FARMER:
            self.humanity += 1
        self.recalculate_stats()

    def handle_demise(self, tracker_type):
        pass
