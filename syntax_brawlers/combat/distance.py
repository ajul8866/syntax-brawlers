"""
Distance & Range System
======================
Mengelola jarak dan range calculations.
"""

from typing import Tuple, Optional
from enum import Enum, auto
import sys
sys.path.insert(0, '..')

from config import (
    CLINCH_RANGE, PUNCH_RANGE, MEDIUM_RANGE, SAFE_RANGE,
    ACTION_DATA, ActionType
)


class RangeZone(Enum):
    """Zone jarak dalam pertarungan"""
    CLINCH = auto()      # Sangat dekat, hampir clinch
    PUNCH = auto()       # Dalam jangkauan pukulan
    MEDIUM = auto()      # Harus maju sedikit untuk menyerang
    SAFE = auto()        # Aman dari sebagian besar serangan
    FAR = auto()         # Terlalu jauh untuk combat


class DistanceManager:
    """
    Mengelola jarak antara dua fighter.
    """

    def __init__(self):
        self.distance = 0.0
        self.previous_distance = 0.0
        self.closing_speed = 0.0  # Rate of distance change

        # Fighter positions
        self.fighter1_x = 0.0
        self.fighter2_x = 0.0

    def update(self, f1_x: float, f2_x: float):
        """Update distance dengan posisi baru"""
        self.previous_distance = self.distance
        self.fighter1_x = f1_x
        self.fighter2_x = f2_x
        self.distance = abs(f2_x - f1_x)

        # Calculate closing speed
        self.closing_speed = self.previous_distance - self.distance

    def get_zone(self) -> RangeZone:
        """Get current range zone"""
        if self.distance <= CLINCH_RANGE:
            return RangeZone.CLINCH
        elif self.distance <= PUNCH_RANGE:
            return RangeZone.PUNCH
        elif self.distance <= MEDIUM_RANGE:
            return RangeZone.MEDIUM
        elif self.distance <= SAFE_RANGE:
            return RangeZone.SAFE
        else:
            return RangeZone.FAR

    def in_punch_range(self) -> bool:
        """Cek apakah dalam jangkauan pukulan"""
        return self.distance <= PUNCH_RANGE

    def in_clinch_range(self) -> bool:
        """Cek apakah hampir clinch"""
        return self.distance <= CLINCH_RANGE

    def is_closing(self) -> bool:
        """Cek apakah jarak semakin dekat"""
        return self.closing_speed > 0

    def is_retreating(self) -> bool:
        """Cek apakah jarak semakin jauh"""
        return self.closing_speed < 0

    def get_optimal_attack_range(self) -> float:
        """Get optimal range untuk menyerang"""
        # Sedikit di dalam punch range untuk hit confirm
        return PUNCH_RANGE * 0.85

    def distance_to_punch_range(self) -> float:
        """Berapa jauh harus maju untuk masuk punch range"""
        if self.distance <= PUNCH_RANGE:
            return 0
        return self.distance - PUNCH_RANGE

    def can_hit_with(self, action: ActionType) -> bool:
        """Cek apakah action bisa hit di jarak saat ini"""
        action_data = ACTION_DATA.get(action)
        if action_data is None:
            return False

        # Add movement distance from action
        effective_range = action_data.range + action_data.move_distance
        return self.distance <= effective_range

    def get_reachable_actions(self) -> list:
        """Get list actions yang bisa hit"""
        reachable = []
        for action in [ActionType.JAB, ActionType.CROSS,
                       ActionType.HOOK, ActionType.UPPERCUT]:
            if self.can_hit_with(action):
                reachable.append(action)
        return reachable

    def get_zone_info(self) -> dict:
        """Get detailed zone information"""
        zone = self.get_zone()
        return {
            'zone': zone.name,
            'distance': self.distance,
            'closing_speed': self.closing_speed,
            'is_closing': self.is_closing(),
            'in_punch_range': self.in_punch_range(),
            'reachable_actions': [a.value for a in self.get_reachable_actions()],
            'distance_to_punch': self.distance_to_punch_range()
        }


class RangeChecker:
    """
    Utility class untuk range checking.
    """

    @staticmethod
    def is_in_range(attacker_x: float, defender_x: float,
                    action: ActionType) -> bool:
        """Cek apakah attacker dalam range untuk action"""
        distance = abs(defender_x - attacker_x)
        action_data = ACTION_DATA.get(action)

        if action_data is None:
            return False

        effective_range = action_data.range + action_data.move_distance
        return distance <= effective_range

    @staticmethod
    def get_distance(x1: float, x2: float) -> float:
        """Calculate distance"""
        return abs(x2 - x1)

    @staticmethod
    def get_direction(from_x: float, to_x: float) -> int:
        """Get direction (-1 left, 1 right, 0 same)"""
        if to_x > from_x:
            return 1
        elif to_x < from_x:
            return -1
        return 0

    @staticmethod
    def calculate_intercept(attacker_x: float, defender_x: float,
                            attacker_speed: float, defender_speed: float,
                            defender_direction: int) -> Optional[Tuple[float, float]]:
        """
        Calculate intercept point jika defender bergerak.
        Return (x_position, time) atau None jika tidak bisa intercept.
        """
        distance = abs(defender_x - attacker_x)
        direction = 1 if defender_x > attacker_x else -1

        # Relative speed
        if defender_direction == direction:
            # Moving away
            relative_speed = attacker_speed - defender_speed
            if relative_speed <= 0:
                return None  # Can't catch
        else:
            # Moving toward or perpendicular
            relative_speed = attacker_speed + defender_speed * abs(defender_direction)

        if relative_speed <= 0:
            return None

        # Time to intercept
        time = distance / relative_speed

        # Intercept position
        intercept_x = attacker_x + direction * attacker_speed * time

        return (intercept_x, time)


class PositionAnalyzer:
    """
    Analyze positioning untuk tactical decisions.
    """

    @staticmethod
    def get_ring_position(x: float, ring_left: float,
                          ring_right: float) -> str:
        """Get position dalam ring"""
        ring_width = ring_right - ring_left
        relative_pos = (x - ring_left) / ring_width

        if relative_pos < 0.2:
            return "corner_left"
        elif relative_pos > 0.8:
            return "corner_right"
        elif 0.4 <= relative_pos <= 0.6:
            return "center"
        elif relative_pos < 0.4:
            return "left_side"
        else:
            return "right_side"

    @staticmethod
    def is_cornered(fighter_x: float, opponent_x: float,
                    ring_left: float, ring_right: float,
                    threshold: float = 100) -> bool:
        """Cek apakah fighter terpojok"""
        # Near left edge and opponent on right
        if fighter_x - ring_left < threshold and opponent_x > fighter_x:
            return True
        # Near right edge and opponent on left
        if ring_right - fighter_x < threshold and opponent_x < fighter_x:
            return True
        return False

    @staticmethod
    def get_escape_direction(fighter_x: float, opponent_x: float,
                             ring_left: float, ring_right: float) -> int:
        """
        Get best direction to escape.
        Return: -1 (left), 1 (right), 0 (no escape needed)
        """
        # Prioritize moving away from corner
        left_space = fighter_x - ring_left
        right_space = ring_right - fighter_x

        # Move toward more open space
        if left_space > right_space + 50:
            return -1
        elif right_space > left_space + 50:
            return 1

        # Move away from opponent
        if opponent_x > fighter_x:
            return -1
        elif opponent_x < fighter_x:
            return 1

        return 0

    @staticmethod
    def analyze_positioning(f1_x: float, f2_x: float,
                            ring_left: float, ring_right: float) -> dict:
        """Full positioning analysis"""
        distance = abs(f2_x - f1_x)
        f1_pos = PositionAnalyzer.get_ring_position(f1_x, ring_left, ring_right)
        f2_pos = PositionAnalyzer.get_ring_position(f2_x, ring_left, ring_right)

        f1_cornered = PositionAnalyzer.is_cornered(f1_x, f2_x, ring_left, ring_right)
        f2_cornered = PositionAnalyzer.is_cornered(f2_x, f1_x, ring_left, ring_right)

        return {
            'distance': distance,
            'fighter1': {
                'x': f1_x,
                'position': f1_pos,
                'cornered': f1_cornered,
                'escape_dir': PositionAnalyzer.get_escape_direction(
                    f1_x, f2_x, ring_left, ring_right
                ) if f1_cornered else 0
            },
            'fighter2': {
                'x': f2_x,
                'position': f2_pos,
                'cornered': f2_cornered,
                'escape_dir': PositionAnalyzer.get_escape_direction(
                    f2_x, f1_x, ring_left, ring_right
                ) if f2_cornered else 0
            },
            'center_control': 'fighter1' if abs(f1_x - (ring_left + ring_right)/2) <
                                           abs(f2_x - (ring_left + ring_right)/2) else 'fighter2'
        }
