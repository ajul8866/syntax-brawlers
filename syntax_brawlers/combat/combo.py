"""
Combo System
============
Tracking dan validasi combo sequences.
"""

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import sys
sys.path.insert(0, '..')

from config import ActionType


class ComboType(Enum):
    """Tipe combo yang dikenali"""
    NONE = auto()
    BASIC = auto()        # Any 2+ hits
    ONE_TWO = auto()      # Jab -> Cross
    THREE_PIECE = auto()  # Jab -> Cross -> Hook
    BODY_WORK = auto()    # Multiple body shots
    FINISHER = auto()     # Sequence ending with Uppercut
    FURY = auto()         # 5+ hit combo


@dataclass
class ComboSequence:
    """Definisi combo sequence"""
    name: str
    combo_type: ComboType
    sequence: List[ActionType]
    damage_bonus: float = 1.0
    style_points: int = 0


# Defined combos
COMBO_SEQUENCES = [
    ComboSequence(
        name="One-Two",
        combo_type=ComboType.ONE_TWO,
        sequence=[ActionType.JAB, ActionType.CROSS],
        damage_bonus=1.1,
        style_points=10
    ),
    ComboSequence(
        name="Three Piece",
        combo_type=ComboType.THREE_PIECE,
        sequence=[ActionType.JAB, ActionType.CROSS, ActionType.HOOK],
        damage_bonus=1.2,
        style_points=25
    ),
    ComboSequence(
        name="The Finisher",
        combo_type=ComboType.FINISHER,
        sequence=[ActionType.JAB, ActionType.JAB, ActionType.UPPERCUT],
        damage_bonus=1.3,
        style_points=30
    ),
    ComboSequence(
        name="Body Breaker",
        combo_type=ComboType.BODY_WORK,
        sequence=[ActionType.HOOK, ActionType.HOOK, ActionType.CROSS],
        damage_bonus=1.15,
        style_points=20
    ),
]


class ComboTracker:
    """
    Track combo untuk satu fighter.
    """

    def __init__(self):
        self.current_count = 0
        self.total_damage = 0.0
        self.hit_sequence: List[ActionType] = []
        self.combo_timer = 0.0
        self.combo_timeout = 0.8  # Seconds before combo resets

        # Best combo tracking
        self.best_combo = 0
        self.best_damage = 0.0

        # Recognized combos
        self.active_combo: Optional[ComboSequence] = None
        self.total_style_points = 0

    def add_hit(self, action: ActionType, damage: float) -> Optional[ComboSequence]:
        """
        Add hit ke combo.
        Return ComboSequence jika combo dikenali.
        """
        self.current_count += 1
        self.total_damage += damage
        self.hit_sequence.append(action)
        self.combo_timer = self.combo_timeout

        # Update best
        if self.current_count > self.best_combo:
            self.best_combo = self.current_count
        if self.total_damage > self.best_damage:
            self.best_damage = self.total_damage

        # Check for recognized combos
        recognized = self._check_combo_sequence()
        if recognized:
            self.active_combo = recognized
            self.total_style_points += recognized.style_points
            return recognized

        return None

    def _check_combo_sequence(self) -> Optional[ComboSequence]:
        """Check apakah sequence saat ini match dengan combo"""
        for combo in COMBO_SEQUENCES:
            seq_len = len(combo.sequence)
            if len(self.hit_sequence) >= seq_len:
                # Check last N hits
                recent = self.hit_sequence[-seq_len:]
                if recent == combo.sequence:
                    return combo

        return None

    def update(self, dt: float):
        """Update combo timer"""
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.reset()

    def reset(self):
        """Reset current combo"""
        self.current_count = 0
        self.total_damage = 0
        self.hit_sequence.clear()
        self.combo_timer = 0
        self.active_combo = None

    @property
    def is_active(self) -> bool:
        """Cek apakah combo sedang aktif"""
        return self.current_count > 0 and self.combo_timer > 0

    def get_damage_bonus(self) -> float:
        """Get current damage bonus berdasarkan combo"""
        # Base bonus dari count
        count_bonus = 1.0 + (self.current_count - 1) * 0.05  # +5% per hit

        # Bonus dari recognized combo
        if self.active_combo:
            return count_bonus * self.active_combo.damage_bonus

        return count_bonus

    def get_sequence_name(self) -> str:
        """Get nama combo saat ini"""
        if self.active_combo:
            return self.active_combo.name
        elif self.current_count >= 5:
            return "FURY!"
        elif self.current_count >= 3:
            return "COMBO!"
        elif self.current_count >= 2:
            return "Nice!"
        return ""

    def get_info(self) -> Dict[str, Any]:
        """Get full combo info"""
        return {
            'count': self.current_count,
            'damage': self.total_damage,
            'sequence': [a.value for a in self.hit_sequence],
            'combo_name': self.get_sequence_name(),
            'damage_bonus': self.get_damage_bonus(),
            'style_points': self.total_style_points,
            'best_combo': self.best_combo,
            'best_damage': self.best_damage,
            'time_remaining': self.combo_timer
        }


class ComboSuggester:
    """
    Suggest next action untuk combo optimal.
    Digunakan oleh AI.
    """

    @staticmethod
    def get_next_action(current_sequence: List[ActionType],
                        stamina: float) -> Optional[ActionType]:
        """
        Suggest aksi berikutnya untuk combo.
        """
        if not current_sequence:
            # Start with jab
            return ActionType.JAB

        last_action = current_sequence[-1]
        seq_len = len(current_sequence)

        # Check untuk lanjutkan known combos
        for combo in COMBO_SEQUENCES:
            if seq_len < len(combo.sequence):
                # Check apakah sequence saat ini match awal combo
                matches = True
                for i, action in enumerate(current_sequence):
                    if i >= len(combo.sequence) or action != combo.sequence[i]:
                        matches = False
                        break

                if matches:
                    # Return next action in combo
                    return combo.sequence[seq_len]

        # Default suggestions
        if last_action == ActionType.JAB:
            if stamina >= 18:
                return ActionType.CROSS
            return ActionType.JAB

        elif last_action == ActionType.CROSS:
            if stamina >= 28:
                return ActionType.HOOK
            return ActionType.JAB

        elif last_action == ActionType.HOOK:
            if stamina >= 35:
                return ActionType.UPPERCUT
            return ActionType.JAB

        # Default: jab
        return ActionType.JAB

    @staticmethod
    def get_combo_options(current_sequence: List[ActionType],
                          stamina: float) -> List[Tuple[ActionType, str]]:
        """
        Get list opsi aksi dengan reasoning.
        Return list of (action, reason)
        """
        options = []

        # Jab selalu opsi (low cost)
        options.append((ActionType.JAB, "Quick, safe"))

        # Cross jika cukup stamina
        if stamina >= 18:
            options.append((ActionType.CROSS, "Power follow-up"))

        # Hook jika sudah ada setup
        if stamina >= 28 and len(current_sequence) >= 2:
            options.append((ActionType.HOOK, "Heavy finisher"))

        # Uppercut untuk KO potential
        if stamina >= 35 and len(current_sequence) >= 2:
            options.append((ActionType.UPPERCUT, "KO potential!"))

        return options
