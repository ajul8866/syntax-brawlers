"""
Hitbox & Hurtbox System
=======================
Sistem collision detection untuk combat.
- Hitbox: Area yang bisa melukai (aktif saat menyerang)
- Hurtbox: Area yang bisa terkena hit (selalu aktif)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum
import sys
sys.path.insert(0, '..')

from config import (
    HitZone, FIGHTER_WIDTH, FIGHTER_HEIGHT,
    HEAD_DAMAGE_MULT, BODY_DAMAGE_MULT, LEGS_DAMAGE_MULT
)


@dataclass
class Hitbox:
    """
    Area hitbox untuk serangan.
    Koordinat relatif terhadap posisi fighter.
    """
    x_offset: float  # Offset dari center fighter
    y_offset: float  # Offset dari feet (0 = ground level)
    width: float
    height: float
    damage_mult: float = 1.0
    is_active: bool = False
    hit_zone: HitZone = HitZone.BODY

    def get_rect(self, fighter_x: float, fighter_y: float,
                 facing_right: bool = True) -> Tuple[float, float, float, float]:
        """
        Dapatkan rectangle (x, y, width, height) dalam world coordinates.
        fighter_y adalah posisi feet (ground level).
        """
        # Flip x offset berdasarkan facing direction
        x_off = self.x_offset if facing_right else -self.x_offset - self.width

        # Y offset dari feet (naik ke atas, jadi dikurangi)
        actual_x = fighter_x + x_off
        actual_y = fighter_y - self.y_offset - self.height

        return (actual_x, actual_y, self.width, self.height)

    def collides_with(self, other: 'Hitbox',
                      self_pos: Tuple[float, float], self_facing: bool,
                      other_pos: Tuple[float, float], other_facing: bool) -> bool:
        """
        Cek collision dengan hitbox lain.
        """
        if not self.is_active:
            return False

        # Dapatkan rectangles
        r1 = self.get_rect(self_pos[0], self_pos[1], self_facing)
        r2 = other.get_rect(other_pos[0], other_pos[1], other_facing)

        # AABB collision
        return (r1[0] < r2[0] + r2[2] and
                r1[0] + r1[2] > r2[0] and
                r1[1] < r2[1] + r2[3] and
                r1[1] + r1[3] > r2[1])


@dataclass
class Hurtbox:
    """
    Area yang bisa terkena hit.
    Setiap fighter punya beberapa hurtbox untuk bagian tubuh berbeda.
    """
    x_offset: float
    y_offset: float  # Offset dari feet
    width: float
    height: float
    zone: HitZone = HitZone.BODY
    is_active: bool = True

    def get_rect(self, fighter_x: float, fighter_y: float,
                 facing_right: bool = True) -> Tuple[float, float, float, float]:
        """Dapatkan rectangle dalam world coordinates"""
        x_off = self.x_offset if facing_right else -self.x_offset - self.width
        actual_x = fighter_x + x_off
        actual_y = fighter_y - self.y_offset - self.height
        return (actual_x, actual_y, self.width, self.height)

    def get_damage_mult(self) -> float:
        """Dapatkan damage multiplier berdasarkan zone"""
        if self.zone == HitZone.HEAD:
            return HEAD_DAMAGE_MULT
        elif self.zone == HitZone.BODY:
            return BODY_DAMAGE_MULT
        elif self.zone == HitZone.LEGS:
            return LEGS_DAMAGE_MULT
        return 1.0


class HurtboxManager:
    """
    Mengelola semua hurtbox untuk satu fighter.
    Hurtbox berubah berdasarkan animasi/state.
    """

    def __init__(self):
        # Default hurtboxes (idle stance)
        self.hurtboxes: List[Hurtbox] = []
        self._create_default_hurtboxes()

        # State-specific hurtbox sets
        self._hurtbox_sets = {
            'idle': self._create_idle_hurtboxes(),
            'blocking': self._create_blocking_hurtboxes(),
            'crouching': self._create_crouching_hurtboxes(),
            'attacking': self._create_attacking_hurtboxes(),
            'knockdown': self._create_knockdown_hurtboxes(),
        }

    def _create_default_hurtboxes(self):
        """Buat hurtbox default (idle stance)"""
        # Head
        self.hurtboxes.append(Hurtbox(
            x_offset=-15, y_offset=120,
            width=30, height=30,
            zone=HitZone.HEAD
        ))
        # Body (upper)
        self.hurtboxes.append(Hurtbox(
            x_offset=-20, y_offset=70,
            width=40, height=50,
            zone=HitZone.BODY
        ))
        # Body (lower) / Legs
        self.hurtboxes.append(Hurtbox(
            x_offset=-18, y_offset=0,
            width=36, height=70,
            zone=HitZone.LEGS
        ))

    def _create_idle_hurtboxes(self) -> List[Hurtbox]:
        """Hurtboxes untuk idle stance"""
        return [
            Hurtbox(-15, 120, 30, 30, HitZone.HEAD),
            Hurtbox(-20, 70, 40, 50, HitZone.BODY),
            Hurtbox(-18, 0, 36, 70, HitZone.LEGS),
        ]

    def _create_blocking_hurtboxes(self) -> List[Hurtbox]:
        """Hurtboxes saat blocking (lebih kecil karena guard)"""
        return [
            Hurtbox(-12, 115, 24, 25, HitZone.HEAD),  # Protected head
            Hurtbox(-25, 60, 50, 55, HitZone.BODY),   # Guard stance
            Hurtbox(-18, 0, 36, 60, HitZone.LEGS),
        ]

    def _create_crouching_hurtboxes(self) -> List[Hurtbox]:
        """Hurtboxes saat crouching/ducking"""
        return [
            Hurtbox(-15, 70, 30, 25, HitZone.HEAD),   # Lower head
            Hurtbox(-22, 30, 44, 40, HitZone.BODY),   # Crouched body
            Hurtbox(-20, 0, 40, 30, HitZone.LEGS),
        ]

    def _create_attacking_hurtboxes(self) -> List[Hurtbox]:
        """Hurtboxes saat attacking (extended)"""
        return [
            Hurtbox(-15, 120, 30, 30, HitZone.HEAD),
            Hurtbox(-15, 70, 50, 50, HitZone.BODY),   # Extended body
            Hurtbox(-18, 0, 36, 70, HitZone.LEGS),
        ]

    def _create_knockdown_hurtboxes(self) -> List[Hurtbox]:
        """Hurtboxes saat knockdown (on ground)"""
        return [
            Hurtbox(-50, 0, 100, 30, HitZone.BODY),  # Laying down
        ]

    def set_state(self, state: str):
        """Update hurtboxes berdasarkan state"""
        if state in self._hurtbox_sets:
            self.hurtboxes = self._hurtbox_sets[state]

    def check_hit(self, hitbox: Hitbox,
                  attacker_pos: Tuple[float, float], attacker_facing: bool,
                  defender_pos: Tuple[float, float], defender_facing: bool) -> Optional[Tuple[HitZone, float]]:
        """
        Cek apakah hitbox mengenai salah satu hurtbox.
        Return (zone, damage_mult) jika hit, None jika miss.
        Prioritas: HEAD > BODY > LEGS
        """
        # Cek collision dengan setiap hurtbox
        hits = []
        for hurtbox in self.hurtboxes:
            if not hurtbox.is_active:
                continue

            h_rect = hitbox.get_rect(attacker_pos[0], attacker_pos[1], attacker_facing)
            hurt_rect = hurtbox.get_rect(defender_pos[0], defender_pos[1], defender_facing)

            # AABB collision
            if (h_rect[0] < hurt_rect[0] + hurt_rect[2] and
                h_rect[0] + h_rect[2] > hurt_rect[0] and
                h_rect[1] < hurt_rect[1] + hurt_rect[3] and
                h_rect[1] + h_rect[3] > hurt_rect[1]):
                hits.append((hurtbox.zone, hurtbox.get_damage_mult()))

        if not hits:
            return None

        # Prioritas hit zone (head > body > legs)
        priority = {HitZone.HEAD: 0, HitZone.BODY: 1, HitZone.LEGS: 2}
        hits.sort(key=lambda x: priority.get(x[0], 99))

        return hits[0]


class AttackHitboxes:
    """
    Factory untuk hitbox berbagai jenis serangan.
    """

    @staticmethod
    def create_jab(facing_right: bool = True) -> Hitbox:
        """Hitbox untuk jab (quick, short range)"""
        return Hitbox(
            x_offset=30 if facing_right else -60,
            y_offset=100,  # Chest/face level
            width=50,
            height=25,
            damage_mult=1.0,
            hit_zone=HitZone.HEAD
        )

    @staticmethod
    def create_cross(facing_right: bool = True) -> Hitbox:
        """Hitbox untuk cross (powerful straight)"""
        return Hitbox(
            x_offset=25 if facing_right else -75,
            y_offset=95,
            width=70,
            height=30,
            damage_mult=1.2,
            hit_zone=HitZone.HEAD
        )

    @staticmethod
    def create_hook(facing_right: bool = True) -> Hitbox:
        """Hitbox untuk hook (wide arc)"""
        return Hitbox(
            x_offset=20 if facing_right else -70,
            y_offset=90,
            width=60,
            height=40,
            damage_mult=1.4,
            hit_zone=HitZone.HEAD
        )

    @staticmethod
    def create_uppercut(facing_right: bool = True) -> Hitbox:
        """Hitbox untuk uppercut (rising attack)"""
        return Hitbox(
            x_offset=15 if facing_right else -45,
            y_offset=80,
            width=40,
            height=60,
            damage_mult=1.6,
            hit_zone=HitZone.HEAD
        )

    @staticmethod
    def create_body_shot(facing_right: bool = True) -> Hitbox:
        """Hitbox untuk body shot"""
        return Hitbox(
            x_offset=25 if facing_right else -65,
            y_offset=60,
            width=55,
            height=35,
            damage_mult=1.0,
            hit_zone=HitZone.BODY
        )


def check_collision(hitbox: Hitbox, hurtbox_manager: HurtboxManager,
                    attacker_pos: Tuple[float, float], attacker_facing: bool,
                    defender_pos: Tuple[float, float], defender_facing: bool) -> Optional[Tuple[HitZone, float, Tuple[float, float]]]:
    """
    Fungsi utilitas untuk cek collision dan return hit info.
    Return: (zone, damage_mult, hit_position) atau None
    """
    result = hurtbox_manager.check_hit(
        hitbox, attacker_pos, attacker_facing,
        defender_pos, defender_facing
    )

    if result:
        zone, mult = result
        # Calculate hit position (for particle effects)
        h_rect = hitbox.get_rect(attacker_pos[0], attacker_pos[1], attacker_facing)
        hit_x = h_rect[0] + h_rect[2] / 2
        hit_y = h_rect[1] + h_rect[3] / 2
        return (zone, mult, (hit_x, hit_y))

    return None
