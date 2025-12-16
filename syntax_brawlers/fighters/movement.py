"""
Movement Controller
===================
Mengelola pergerakan fighter: walking, advancing, retreating, knockback.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional
from enum import Enum, auto
import math
import sys
sys.path.insert(0, '..')

from config import (
    MOVEMENT_SPEED, ADVANCE_SPEED, RETREAT_SPEED, KNOCKBACK_FORCE,
    RING_LEFT, RING_RIGHT, RING_FLOOR_Y,
    CLINCH_RANGE, PUNCH_RANGE, MEDIUM_RANGE, SAFE_RANGE,
    FIGHTER_WIDTH, EasingType
)


class MovementState(Enum):
    """State pergerakan fighter"""
    IDLE = auto()
    WALKING_FORWARD = auto()
    WALKING_BACKWARD = auto()
    ADVANCING = auto()      # Moving forward during attack
    RETREATING = auto()     # Moving back after hit/dodge
    KNOCKBACK = auto()      # Being pushed back from hit
    KNOCKED_DOWN = auto()   # On the ground


@dataclass
class MovementController:
    """
    Mengontrol semua aspek pergerakan fighter.
    """
    x: float = 0
    y: float = RING_FLOOR_Y

    # Movement state
    state: MovementState = MovementState.IDLE
    facing_right: bool = True

    # Velocity
    velocity_x: float = 0
    velocity_y: float = 0

    # Movement modifiers
    speed_mult: float = 1.0

    # Knockback
    knockback_velocity: float = 0
    knockback_decay: float = 0.85

    # Movement target (untuk advance/retreat)
    target_x: Optional[float] = None
    advance_duration: float = 0

    # Bounds
    min_x: float = RING_LEFT + FIGHTER_WIDTH // 2
    max_x: float = RING_RIGHT - FIGHTER_WIDTH // 2

    def update(self, dt: float, opponent_x: Optional[float] = None):
        """Update posisi per frame"""
        # Apply knockback
        if self.knockback_velocity != 0:
            self.x += self.knockback_velocity * dt
            self.knockback_velocity *= self.knockback_decay
            if abs(self.knockback_velocity) < 1:
                self.knockback_velocity = 0

        # Handle movement based on state
        if self.state == MovementState.WALKING_FORWARD:
            direction = 1 if self.facing_right else -1
            self.x += direction * MOVEMENT_SPEED * self.speed_mult * dt

        elif self.state == MovementState.WALKING_BACKWARD:
            direction = -1 if self.facing_right else 1
            self.x += direction * MOVEMENT_SPEED * self.speed_mult * dt

        elif self.state == MovementState.ADVANCING:
            if self.target_x is not None:
                direction = 1 if self.target_x > self.x else -1
                self.x += direction * ADVANCE_SPEED * self.speed_mult * dt

                # Check if reached target
                if (direction > 0 and self.x >= self.target_x) or \
                   (direction < 0 and self.x <= self.target_x):
                    self.x = self.target_x
                    self.target_x = None
                    self.state = MovementState.IDLE

        elif self.state == MovementState.RETREATING:
            if self.target_x is not None:
                direction = 1 if self.target_x > self.x else -1
                self.x += direction * RETREAT_SPEED * self.speed_mult * dt

                if (direction > 0 and self.x >= self.target_x) or \
                   (direction < 0 and self.x <= self.target_x):
                    self.x = self.target_x
                    self.target_x = None
                    self.state = MovementState.IDLE

        # Apply velocity
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt

        # Clamp to ring bounds
        self.x = max(self.min_x, min(self.max_x, self.x))

        # Keep on ground (no jumping in boxing)
        self.y = RING_FLOOR_Y

        # Update facing based on opponent position
        if opponent_x is not None:
            self.facing_right = opponent_x > self.x

    def walk_forward(self):
        """Mulai jalan maju"""
        if self.state not in (MovementState.KNOCKBACK, MovementState.KNOCKED_DOWN):
            self.state = MovementState.WALKING_FORWARD

    def walk_backward(self):
        """Mulai jalan mundur"""
        if self.state not in (MovementState.KNOCKBACK, MovementState.KNOCKED_DOWN):
            self.state = MovementState.WALKING_BACKWARD

    def stop(self):
        """Berhenti bergerak"""
        if self.state in (MovementState.WALKING_FORWARD, MovementState.WALKING_BACKWARD):
            self.state = MovementState.IDLE

    def advance(self, distance: float):
        """
        Maju sejumlah distance (untuk serangan).
        """
        if self.state == MovementState.KNOCKED_DOWN:
            return

        direction = 1 if self.facing_right else -1
        self.target_x = self.x + (direction * distance)
        self.target_x = max(self.min_x, min(self.max_x, self.target_x))
        self.state = MovementState.ADVANCING

    def retreat(self, distance: float):
        """
        Mundur sejumlah distance (untuk dodge/knockback).
        """
        if self.state == MovementState.KNOCKED_DOWN:
            return

        direction = -1 if self.facing_right else 1
        self.target_x = self.x + (direction * distance)
        self.target_x = max(self.min_x, min(self.max_x, self.target_x))
        self.state = MovementState.RETREATING

    def apply_knockback(self, force: float, from_right: bool):
        """
        Terapkan knockback dari serangan.
        from_right: True jika serangan datang dari kanan
        """
        direction = -1 if from_right else 1
        self.knockback_velocity = direction * force
        self.state = MovementState.KNOCKBACK

    def knock_down(self):
        """Fighter jatuh ke tanah"""
        self.state = MovementState.KNOCKED_DOWN
        self.velocity_x = 0
        self.knockback_velocity = 0

    def get_up(self):
        """Fighter bangun dari knockdown"""
        self.state = MovementState.IDLE

    def set_position(self, x: float, y: float = RING_FLOOR_Y):
        """Set posisi langsung"""
        self.x = max(self.min_x, min(self.max_x, x))
        self.y = y

    def get_position(self) -> Tuple[float, float]:
        """Dapatkan posisi saat ini"""
        return (self.x, self.y)

    def get_distance_to(self, other_x: float) -> float:
        """Hitung jarak ke posisi lain"""
        return abs(self.x - other_x)

    def is_in_range(self, other_x: float, range_type: str) -> bool:
        """
        Cek apakah dalam range tertentu.
        range_type: 'clinch', 'punch', 'medium', 'safe'
        """
        distance = self.get_distance_to(other_x)

        if range_type == 'clinch':
            return distance <= CLINCH_RANGE
        elif range_type == 'punch':
            return distance <= PUNCH_RANGE
        elif range_type == 'medium':
            return distance <= MEDIUM_RANGE
        elif range_type == 'safe':
            return distance <= SAFE_RANGE

        return False

    def get_range_zone(self, other_x: float) -> str:
        """
        Dapatkan zone range saat ini.
        Return: 'clinch', 'punch', 'medium', 'safe', atau 'far'
        """
        distance = self.get_distance_to(other_x)

        if distance <= CLINCH_RANGE:
            return 'clinch'
        elif distance <= PUNCH_RANGE:
            return 'punch'
        elif distance <= MEDIUM_RANGE:
            return 'medium'
        elif distance <= SAFE_RANGE:
            return 'safe'
        else:
            return 'far'

    def can_move(self) -> bool:
        """Cek apakah fighter bisa bergerak"""
        return self.state not in (MovementState.KNOCKBACK, MovementState.KNOCKED_DOWN)

    def is_moving(self) -> bool:
        """Cek apakah fighter sedang bergerak"""
        return self.state in (
            MovementState.WALKING_FORWARD,
            MovementState.WALKING_BACKWARD,
            MovementState.ADVANCING,
            MovementState.RETREATING
        )


def calculate_optimal_distance(attacker_range: float,
                                attacker_speed: float,
                                defender_speed: float) -> float:
    """
    Hitung jarak optimal untuk menyerang.
    Mempertimbangkan range serangan dan kecepatan kedua fighter.
    """
    # Jarak ideal: cukup dekat untuk menyerang, cukup jauh untuk avoid counter
    base_distance = attacker_range * 0.9

    # Adjust berdasarkan speed differential
    speed_ratio = attacker_speed / defender_speed if defender_speed > 0 else 1

    if speed_ratio > 1:
        # Lebih cepat = bisa lebih dekat
        base_distance *= 0.95
    else:
        # Lebih lambat = perlu lebih hati-hati
        base_distance *= 1.05

    return base_distance


def interpolate_position(start: float, end: float, t: float,
                          easing: EasingType = EasingType.LINEAR) -> float:
    """
    Interpolasi posisi dengan easing.
    t: 0.0 - 1.0 (progress)
    """
    # Apply easing
    if easing == EasingType.LINEAR:
        ease_t = t
    elif easing == EasingType.EASE_IN:
        ease_t = t * t
    elif easing == EasingType.EASE_OUT:
        ease_t = 1 - (1 - t) ** 2
    elif easing == EasingType.EASE_IN_OUT:
        ease_t = 3 * t * t - 2 * t * t * t
    elif easing == EasingType.EASE_OUT_BACK:
        c1 = 1.70158
        c3 = c1 + 1
        ease_t = 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)
    elif easing == EasingType.EASE_IN_OUT_CUBIC:
        if t < 0.5:
            ease_t = 4 * t * t * t
        else:
            ease_t = 1 - pow(-2 * t + 2, 3) / 2
    elif easing == EasingType.BOUNCE:
        if t < 1 / 2.75:
            ease_t = 7.5625 * t * t
        elif t < 2 / 2.75:
            t2 = t - 1.5 / 2.75
            ease_t = 7.5625 * t2 * t2 + 0.75
        elif t < 2.5 / 2.75:
            t2 = t - 2.25 / 2.75
            ease_t = 7.5625 * t2 * t2 + 0.9375
        else:
            t2 = t - 2.625 / 2.75
            ease_t = 7.5625 * t2 * t2 + 0.984375
    else:
        ease_t = t

    return start + (end - start) * ease_t
