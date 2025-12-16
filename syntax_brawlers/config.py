"""
Syntax Brawlers v2.0 - Configuration & Constants
=================================================
All game settings, colors, and constants in one place.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Tuple, Dict, Any

# =============================================================================
# DISPLAY SETTINGS
# =============================================================================

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GAME_TITLE = "SYNTAX BRAWLERS v2.0 - LLM Arena Fighting"

# =============================================================================
# COLORS
# =============================================================================

# Basic colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (40, 40, 40)
LIGHT_GRAY = (180, 180, 180)

# Primary colors
RED = (220, 50, 50)
DARK_RED = (150, 30, 30)
BRIGHT_RED = (255, 80, 80)
GREEN = (50, 200, 50)
DARK_GREEN = (30, 120, 30)
BLUE = (50, 100, 200)
DARK_BLUE = (30, 60, 150)
CYAN = (50, 200, 200)

# Accent colors
YELLOW = (230, 200, 50)
ORANGE = (230, 150, 50)
PURPLE = (150, 50, 200)
GOLD = (255, 215, 0)
PINK = (255, 100, 150)

# Environment colors
BROWN = (139, 90, 43)
TAN = (210, 180, 140)
SKIN_TONE = (255, 220, 180)
SKIN_TONE_DARK = (180, 140, 100)

# Ring colors
RING_CANVAS = (200, 180, 160)
RING_ROPE_RED = (200, 50, 50)
RING_ROPE_WHITE = (240, 240, 240)
RING_ROPE_BLUE = (50, 50, 200)
RING_POST = (80, 80, 80)
RING_APRON = (100, 80, 60)

# UI colors
UI_BG = (20, 20, 30)
UI_BORDER = (100, 100, 120)
HEALTH_GREEN = (50, 200, 50)
HEALTH_YELLOW = (200, 200, 50)
HEALTH_RED = (200, 50, 50)
STAMINA_GOLD = (200, 180, 50)

# =============================================================================
# RING / ARENA SETTINGS
# =============================================================================

RING_LEFT = 150
RING_RIGHT = 1130
RING_TOP = 250
RING_BOTTOM = 550
RING_CENTER_X = (RING_LEFT + RING_RIGHT) // 2
RING_CENTER_Y = (RING_TOP + RING_BOTTOM) // 2
RING_FLOOR_Y = 480  # Where fighters stand

# =============================================================================
# FIGHTER SETTINGS
# =============================================================================

# Starting positions
FIGHTER1_START_X = 400
FIGHTER2_START_X = 880
FIGHTER_START_Y = RING_FLOOR_Y

# Size
FIGHTER_WIDTH = 80
FIGHTER_HEIGHT = 150

# Movement
MOVEMENT_SPEED = 300  # pixels per second
ADVANCE_SPEED = 400   # when attacking
RETREAT_SPEED = 250   # when knocked back
KNOCKBACK_FORCE = 150

# Combat ranges (distance between fighter centers)
CLINCH_RANGE = 60
PUNCH_RANGE = 140
MEDIUM_RANGE = 200
SAFE_RANGE = 300

# =============================================================================
# COMBAT SETTINGS
# =============================================================================

# Base stats
DEFAULT_MAX_HEALTH = 100
DEFAULT_MAX_STAMINA = 100
DEFAULT_POWER = 1.0
DEFAULT_SPEED = 1.0
DEFAULT_DEFENSE = 1.0

# Stamina
STAMINA_REGEN_RATE = 5.0  # per second
STAMINA_REGEN_IDLE_BONUS = 8.0  # extra when not acting
EXHAUSTION_THRESHOLD = 20  # below this = penalties

# Damage modifiers
CRIT_MULTIPLIER = 2.0
COUNTER_MULTIPLIER = 1.5
BLOCK_REDUCTION = 0.7  # 70% damage reduction
EXHAUSTION_DAMAGE_PENALTY = 0.7  # 30% less damage when exhausted

# Hit zones
HEAD_DAMAGE_MULT = 1.5
BODY_DAMAGE_MULT = 1.0
LEGS_DAMAGE_MULT = 0.8

# Timing (in seconds)
HIT_STUN_LIGHT = 0.2
HIT_STUN_HEAVY = 0.4
BLOCK_STUN = 0.15
STAGGER_DURATION = 0.8
KNOCKDOWN_DURATION = 2.0

# =============================================================================
# ANIMATION SETTINGS
# =============================================================================

# Frame timing
ANIMATION_FPS = 30  # Internal animation frame rate
IDLE_ANIMATION_SPEED = 0.5  # Slower idle bobbing

# Easing types
class EasingType(Enum):
    LINEAR = auto()
    EASE_IN = auto()
    EASE_OUT = auto()
    EASE_IN_OUT = auto()
    EASE_OUT_BACK = auto()
    EASE_IN_OUT_CUBIC = auto()
    BOUNCE = auto()

# =============================================================================
# VISUAL EFFECTS SETTINGS
# =============================================================================

# Screen shake
SHAKE_LIGHT = 3
SHAKE_MEDIUM = 6
SHAKE_HEAVY = 12
SHAKE_DECAY = 0.9

# Hit freeze (slow-mo on impact)
HIT_FREEZE_DURATION = 0.05
HIT_FREEZE_SCALE = 0.1  # 10% speed

# Particles
MAX_PARTICLES = 500
PARTICLE_GRAVITY = 400

# Camera
CAMERA_SMOOTHING = 0.1
CAMERA_ZOOM_MIN = 0.8
CAMERA_ZOOM_MAX = 1.3
DRAMATIC_ZOOM_AMOUNT = 1.4

# =============================================================================
# GAME STATE ENUMS
# =============================================================================

class GameState(Enum):
    MAIN_MENU = auto()
    CHARACTER_SELECT = auto()
    LLM_CONFIG = auto()
    PRE_FIGHT = auto()
    FIGHTING = auto()
    ROUND_END = auto()
    MATCH_END = auto()
    PAUSED = auto()
    SETTINGS = auto()


class FightPhase(Enum):
    """Phases within a fight"""
    INTRO = auto()
    READY = auto()
    ACTIVE = auto()
    HIT_FREEZE = auto()
    KNOCKDOWN = auto()
    KO = auto()


class ActionType(Enum):
    """Available combat actions"""
    JAB = "JAB"
    CROSS = "CROSS"
    HOOK = "HOOK"
    UPPERCUT = "UPPERCUT"
    BLOCK = "BLOCK"
    DODGE = "DODGE"
    CLINCH = "CLINCH"
    IDLE = "IDLE"


class AnimationState(Enum):
    """Fighter animation states"""
    IDLE = "idle"
    WALK_FORWARD = "walk_forward"
    WALK_BACKWARD = "walk_backward"
    JAB = "jab"
    CROSS = "cross"
    HOOK = "hook"
    UPPERCUT = "uppercut"
    BLOCK = "block"
    BLOCK_HIT = "block_hit"
    DODGE = "dodge"
    HIT_LIGHT = "hit_light"
    HIT_HEAVY = "hit_heavy"
    STAGGER = "stagger"
    KNOCKDOWN = "knockdown"
    GETUP = "getup"
    VICTORY = "victory"
    DEFEAT = "defeat"


class PersonalityType(Enum):
    """AI personality types"""
    DESTROYER = "The Destroyer"
    TACTICIAN = "The Tactician"
    GHOST = "The Ghost"
    WILDCARD = "The Wildcard"


class HitZone(Enum):
    """Body zones for hit detection"""
    HEAD = "head"
    BODY = "body"
    LEGS = "legs"


# =============================================================================
# ACTION DEFINITIONS
# =============================================================================

@dataclass
class ActionData:
    """Data for each action type"""
    name: str
    damage_min: int
    damage_max: int
    stamina_cost: int
    hit_rate: float
    range: int
    startup_frames: int  # Frames before hit
    active_frames: int   # Frames hitbox is active
    recovery_frames: int # Frames after attack
    move_distance: int   # How far fighter advances
    crit_bonus: float = 0.0
    stun_chance: float = 0.0
    breaks_block: bool = False
    can_chain: int = 1
    easing: EasingType = EasingType.EASE_OUT


ACTION_DATA: Dict[ActionType, ActionData] = {
    ActionType.JAB: ActionData(
        name="Jab",
        damage_min=8, damage_max=12,
        stamina_cost=8,
        hit_rate=0.90,
        range=100,
        startup_frames=3,
        active_frames=2,
        recovery_frames=4,
        move_distance=60,
        can_chain=3,
        easing=EasingType.EASE_OUT
    ),
    ActionType.CROSS: ActionData(
        name="Cross",
        damage_min=18, damage_max=25,
        stamina_cost=18,
        hit_rate=0.75,
        range=120,
        startup_frames=5,
        active_frames=3,
        recovery_frames=6,
        move_distance=80,
        breaks_block=True,
        easing=EasingType.EASE_IN_OUT
    ),
    ActionType.HOOK: ActionData(
        name="Hook",
        damage_min=28, damage_max=38,
        stamina_cost=28,
        hit_rate=0.60,
        range=90,
        startup_frames=7,
        active_frames=3,
        recovery_frames=8,
        move_distance=70,
        crit_bonus=0.25,
        stun_chance=0.20,
        easing=EasingType.EASE_OUT_BACK
    ),
    ActionType.UPPERCUT: ActionData(
        name="Uppercut",
        damage_min=35, damage_max=45,
        stamina_cost=35,
        hit_rate=0.50,
        range=80,
        startup_frames=9,
        active_frames=4,
        recovery_frames=10,
        move_distance=50,
        crit_bonus=0.15,
        stun_chance=0.35,
        easing=EasingType.EASE_IN_OUT_CUBIC
    ),
    ActionType.BLOCK: ActionData(
        name="Block",
        damage_min=0, damage_max=0,
        stamina_cost=12,
        hit_rate=1.0,
        range=0,
        startup_frames=2,
        active_frames=30,
        recovery_frames=4,
        move_distance=0,
        easing=EasingType.LINEAR
    ),
    ActionType.DODGE: ActionData(
        name="Dodge",
        damage_min=0, damage_max=0,
        stamina_cost=15,
        hit_rate=0.70,
        range=0,
        startup_frames=3,
        active_frames=8,
        recovery_frames=5,
        move_distance=-80,  # Move backward
        easing=EasingType.EASE_OUT
    ),
    ActionType.CLINCH: ActionData(
        name="Clinch",
        damage_min=0, damage_max=0,
        stamina_cost=5,
        hit_rate=0.80,
        range=60,
        startup_frames=4,
        active_frames=20,
        recovery_frames=10,
        move_distance=40,
        easing=EasingType.LINEAR
    ),
    ActionType.IDLE: ActionData(
        name="Idle",
        damage_min=0, damage_max=0,
        stamina_cost=0,
        hit_rate=0,
        range=0,
        startup_frames=0,
        active_frames=0,
        recovery_frames=0,
        move_distance=0,
        easing=EasingType.LINEAR
    ),
}

# =============================================================================
# ROUND SETTINGS
# =============================================================================

MAX_ROUNDS = 3
ROUND_DURATION = 180  # seconds
ROUND_TRANSITION_TIME = 3.0  # seconds between rounds
KO_COUNT = 10  # 10-count for knockdown

# =============================================================================
# LLM SETTINGS
# =============================================================================

LLM_TIMEOUT = 10.0  # seconds
LLM_MAX_RETRIES = 2
LLM_DEFAULT_MODEL = "z-ai/glm-4.6"

# =============================================================================
# AUDIO SETTINGS
# =============================================================================

AUDIO_ENABLED = True
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2
AUDIO_BUFFER_SIZE = 512

# Volume levels (0.0 - 1.0)
MASTER_VOLUME = 0.8
SFX_VOLUME = 0.7
MUSIC_VOLUME = 0.5

# =============================================================================
# DEBUG FLAGS
# =============================================================================

DEBUG_HITBOXES = False
DEBUG_DISTANCES = False
DEBUG_FRAMERATE = True
DEBUG_AI_DECISIONS = False
