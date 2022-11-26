import sys
from string import ascii_letters, digits
from os import path


class Config:
    DEV_MODE = True
    KEY_INPUT_ENABLED = False
    KEY_INPUT_WATCH = ascii_letters + digits
    SAVE_FILE_PREFIX = "Sofa_Baron_Save#"

    if hasattr(sys, "_MEIPASS"):
        WORKING_PATH = sys._MEIPASS
    else:
        WORKING_PATH = path.realpath(path.dirname("__file__"))
    PATH_JSON = path.normpath(WORKING_PATH + "/json/")
    PATH_JSON_EVENTS = path.normpath(WORKING_PATH + "/json/")
    PATH_TEXT_EVENTS = path.normpath(WORKING_PATH + "/text/")
    PATH_IMAGES = path.normpath(WORKING_PATH + "/images/")
    PATH_GUI_IMAGES = path.normpath(WORKING_PATH + "/images/gui/")

    DOT_NUMBERS = ("zero", "one", "two", "three", "four", "five")

    REF_TYPE = "type"
    REF_EID = "eid"
    REF_GOTO_MOMENT = "goto"
    REF_MOMENTS = "moments"
    REF_MID = "mid"
    REF_TEXT = "text"
    REF_CHOICE_PROMPT = "text"
    REF_CHOICES = "choices"
    REF_CHOICE_LABEL = "label"
    REF_CHOICE_ENABLED = "enabled_if"
    REF_CHOICE_SHOWN = "show_if"
    REF_CHOICE_RID = "choice_id"
    REF_STATE_CHANGE_EXPR = "evex"
    REF_EVAL_TAG = "evex"

    REF_MESSYCRIT = "messycrit"
    REF_CRIT = "crit"
    REF_WIN = "win"
    REF_FAIL = "fail"
    REF_BEASTFAIL = "beastfail"

    HUNGER_MAX = 5
    HUNGER_MIN = 1
    HUNGER_MIN_KILL = 0
    MAX_HUMANITY = 8
    MIN_HUMANITY = 4
    KILL_HUNT_HUMANITY_THRESHOLD_INC = 4
    RESIST_MAX_HUNGER_HUMANITY_THRESHOLD_INC = 8
    WEAK_TO_HUNGER_HUMANITY_THRESHOLD_INC = 5

    CLAN_NOSFERATU = "Nosferatu"
    CLAN_RAVNOS = "Ravnos"
    CLAN_VENTRUE = "Ventrue"

    REF_CLAN_EPITHET = "clan_epithet"
    REF_CLAN_NICKNAME = "clan_nickname"
    REF_CLAN_SLUR = "clan_slur"
    REF_CLAN_CHOSEN = "post_choice_text"

    BLURBS_CLANS = {
        CLAN_NOSFERATU: {
            REF_CLAN_EPITHET: "the Clan of the Hidden",
            REF_CLAN_NICKNAME: "Lurker",
            REF_CLAN_SLUR: "Sewer Rat"
        },
        CLAN_RAVNOS: {
            REF_CLAN_EPITHET: "the Doomed Wanderers",
            REF_CLAN_NICKNAME: "Nomad",
            REF_CLAN_SLUR: "Raven"
        },
        CLAN_VENTRUE: {
            REF_CLAN_EPITHET: "the Clan of Kings",
            REF_CLAN_NICKNAME: "Blue Blood",
            REF_CLAN_SLUR: "Blue Blood"
        }
    }

    MAX_SCORE = 5
    MIN_SCORE_ATTR = 1
    MIN_SCORE = 0

    TRACK_HP = "hit_points"
    TRACK_WILL = "willpower"
    DMG_SPF = "superficial_dmg"
    DMG_FULL_SPF = "unhalved_superficial_dmg"
    DMG_AGG = "aggravated_dmg"
    DMG_NONE = "clear"

    REF_ATTRS_ALL = "All Attributes"
    REF_ATTRS = "attrs"
    REF_SKILLS_ALL = "All Skills"
    REF_SKILLS = "skills"

    AT_STR = "Strength"
    AT_DEX = "Dexterity"
    AT_STA = "Stamina"
    AT_CHA = "Charisma"
    AT_MAN = "Manipulation"
    AT_COM = "Composure"
    AT_INT = "Intelligence"
    AT_WIT = "Wits"
    AT_RES = "Resolve"

    SK_ATHL = "Athletics"
    SK_CLAN = "Clandestine"  # Larceny, Stealth
    SK_COMB = "Combat"  # Brawl, Melee
    SK_FIRE = "Firearms"
    SK_TRAV = "Traversal"  # Drive, Survival
    SK_DIPL = "Diplomacy"  # Animal Ken, Etiquette, Persuasion
    SK_INTI = "Intimidation"
    SK_INTR = "Intrigue"  # Insight, Subterfuge
    SK_LEAD = "Leadership"
    SK_STWS = "Streetwise"
    SK_ACAD = "Academics"  # Academics, Politics
    SK_INSP = "Inspection"  # Awareness, Investigation
    SK_OCCL = "Occult"
    SK_SCIE = "Science"  # Science, Medicine
    SK_TECH = "Technology"

    REF_BG_NAME = "background_name"
    REF_ROLL_BONUS_PREFIX = "bonus_"
    REF_ROLL_EVENT_BONUS = "bonus_current_event"
    REF_ROLL_FORCE_NOSBANE = "nosbane"
    CHAR_BACKGROUNDS = {
        "test_bg_med_student": {
            REF_BG_NAME: "Med Student",
            REF_ATTRS_ALL: 1, AT_DEX: 1, AT_CHA: -1, AT_COM: 1, AT_INT: 1, AT_RES: 1,
            REF_SKILLS_ALL: 1, SK_TECH: 1, SK_SCIE: 2, SK_LEAD: 1, SK_ACAD: 2, SK_INSP: 2, SK_INTI: -1,
            SK_ATHL: -1
        }
    }

    BG_BEAUTIFUL = "Beautiful"

    PT_ALLEYCAT = "Alley Cat"  # +1 Combat, +1 Intimidation, +1 Potence, -1 Humanity, +3 Contacts
    PT_BAGGER = "Bagger"  # +1 Clandestine, +Streetwise, +1 Obfuscate, more notoriety
    PT_FARMER = "Farmer"  # +1 Diplomacy, +1 Traversal, +1 Animalism, +1 Humanity, costs willpower to feed on humans
    PT_SIREN = "Siren"  # +1 Diplomacy, +1 Intrigue, +1 Presence, +Beautiful, more notoriety?

    DISC_ANIMALISM = "Animalism"
    DISC_DOMINATE = "Dominate"
    DISC_FORTITUDE = "Fortitude"
    DISC_OBFUSCATE = "Obfuscate"
    DISC_POTENCE = "Potence"
    DISC_PRESENCE = "Presence"

    VAL_DISC_LOCKED = 0  # Cost multipliers, with 0 being locked.
    VAL_DISC_OUTCLAN = 1.4
    VAL_DISC_CAITIFF = 1.2
    VAL_DISC_INCLAN = 1

    POWER_ANIMALISM_FAMULUS = "Bond Famulus"
    POWER_ANIMALISM_SPEAK = "Feral Whispers"
    POWER_ANIMALISM_SUCCULENCE = "Animal Succulence"
    POWER_ANIMALISM_HIVE = "Unliving Hive"

    POWER_DOMINATE_FORGET = "Cloud Memory"
    POWER_DOMINATE_COMPEL = "Compel"
    POWER_DOMINATE_MESMERIZE = "Mesmerize"
    POWER_DOMINATE_REWRITE = "Forgetful Mind"

    POWER_FORTITUDE_HP = "Resilience"
    POWER_FORTITUDE_WILL = "Unswayable Mind"
    POWER_FORTITUDE_TOUGH = "Toughness"
    POWER_FORTITUDE_BANE = "Defy Bane"

    POWER_OBFUSCATE_FADE = "Cloak of Shadows"
    POWER_OBFUSCATE_STEALTH = "Unseen Passage"
    POWER_OBFUSCATE_ILLUSION = "Chimerstry"
    POWER_OBFUSCATE_MASK = "Mask of a Thousand Faces"
    POWER_OBFUSCATE_LAUGHINGMAN = "Ghost in the Machine"

    POWER_POTENCE_FATALITY = "Lethal Body"
    POWER_POTENCE_SUPERJUMP = "Soaring Leap"
    POWER_POTENCE_PROWESS = "Prowess"
    POWER_POTENCE_MEGASUCK = "Brutal Feed"
    POWER_POTENCE_RAGE = "Spark of Rage"

    POWER_PRESENCE_AWE = "Awe"
    POWER_PRESENCE_DAUNT = "Daunt"
    POWER_PRESENCE_ENTRANCE = "Entracement"
    POWER_PRESENCE_SCARYFACE = "Dread Gaze"

    SEM_HUB_MAIN = "haven-hub-default"

    DP_DISCLAIMER = "This game was created as a part of Vampire: The Masquerade game jam. "
    DP_DISCLAIMER += "Events portrayed in this game are not canon within World of Darkness."



