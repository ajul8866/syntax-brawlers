"""
Combo Display System
====================
Menampilkan combo counter dan bonus info.
"""

import pygame
import math
from typing import Optional, Tuple
import sys
sys.path.insert(0, '..')

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    WHITE, BLACK, YELLOW, ORANGE, RED, GOLD
)


class ComboDisplay:
    """
    Display untuk combo counter dengan animasi.
    """

    def __init__(self, x: int, y: int, is_right_side: bool = False):
        self.x = x
        self.y = y
        self.is_right_side = is_right_side

        # State
        self.combo_count = 0
        self.combo_damage = 0.0
        self.combo_name = ""
        self.is_active = False

        # Animation
        self.scale = 1.0
        self.shake_offset = (0, 0)
        self.pulse_timer = 0.0
        self.display_timer = 0.0
        self.fade_alpha = 255

        # Fonts
        self.count_font = None
        self.label_font = None
        self.name_font = None
        self._init_fonts()

    def _init_fonts(self):
        self.count_font = pygame.font.Font(None, 72)
        self.label_font = pygame.font.Font(None, 28)
        self.name_font = pygame.font.Font(None, 36)

    def set_combo(self, count: int, damage: float = 0,
                  name: str = "", show_duration: float = 2.0):
        """Set combo info"""
        if count > self.combo_count:
            # New hit in combo - trigger animation
            self.scale = 1.3
            self.shake_offset = (5, -5)

        self.combo_count = count
        self.combo_damage = damage
        self.combo_name = name
        self.is_active = count > 0
        self.display_timer = show_duration if count > 0 else 0
        self.fade_alpha = 255

    def update(self, dt: float):
        """Update animations"""
        if not self.is_active:
            return

        # Scale animation (settle back to 1.0)
        if self.scale > 1.0:
            self.scale -= dt * 2.0
            self.scale = max(1.0, self.scale)

        # Shake decay
        self.shake_offset = (
            self.shake_offset[0] * 0.9,
            self.shake_offset[1] * 0.9
        )

        # Pulse
        self.pulse_timer += dt
        pulse = 1.0 + 0.05 * math.sin(self.pulse_timer * 6)

        # Timer and fade
        self.display_timer -= dt
        if self.display_timer <= 0.5 and self.display_timer > 0:
            self.fade_alpha = int(255 * (self.display_timer / 0.5))
        elif self.display_timer <= 0:
            self.is_active = False
            self.combo_count = 0

    def render(self, surface: pygame.Surface):
        """Render combo display"""
        if not self.is_active or self.combo_count < 2:
            return

        if self.count_font is None:
            self._init_fonts()

        # Calculate position with shake
        x = self.x + self.shake_offset[0]
        y = self.y + self.shake_offset[1]

        # Alignment
        align = 'right' if self.is_right_side else 'left'

        # Combo count
        count_text = str(self.combo_count)
        count_surface = self.count_font.render(count_text, True, self._get_count_color())

        # Scale
        if self.scale != 1.0:
            new_size = (int(count_surface.get_width() * self.scale),
                       int(count_surface.get_height() * self.scale))
            count_surface = pygame.transform.scale(count_surface, new_size)

        count_surface.set_alpha(self.fade_alpha)

        # Position based on alignment
        if align == 'right':
            count_rect = count_surface.get_rect(topright=(x, y))
        else:
            count_rect = count_surface.get_rect(topleft=(x, y))

        surface.blit(count_surface, count_rect)

        # "HITS" label
        label_surface = self.label_font.render("HITS", True, WHITE)
        label_surface.set_alpha(self.fade_alpha)

        if align == 'right':
            label_rect = label_surface.get_rect(topright=(x, y + count_surface.get_height()))
        else:
            label_rect = label_surface.get_rect(topleft=(x, y + count_surface.get_height()))

        surface.blit(label_surface, label_rect)

        # Combo name (if any)
        if self.combo_name:
            name_color = GOLD if "!" in self.combo_name else YELLOW
            name_surface = self.name_font.render(self.combo_name, True, name_color)
            name_surface.set_alpha(self.fade_alpha)

            if align == 'right':
                name_rect = name_surface.get_rect(topright=(x, y + count_surface.get_height() + 25))
            else:
                name_rect = name_surface.get_rect(topleft=(x, y + count_surface.get_height() + 25))

            surface.blit(name_surface, name_rect)

        # Damage (smaller, below)
        if self.combo_damage > 0:
            damage_text = f"{int(self.combo_damage)} DMG"
            damage_font = pygame.font.Font(None, 24)
            damage_surface = damage_font.render(damage_text, True, ORANGE)
            damage_surface.set_alpha(self.fade_alpha)

            y_offset = count_surface.get_height() + 50
            if self.combo_name:
                y_offset += 30

            if align == 'right':
                damage_rect = damage_surface.get_rect(topright=(x, y + y_offset))
            else:
                damage_rect = damage_surface.get_rect(topleft=(x, y + y_offset))

            surface.blit(damage_surface, damage_rect)

    def _get_count_color(self) -> Tuple[int, int, int]:
        """Get color based on combo count"""
        if self.combo_count >= 10:
            return RED
        elif self.combo_count >= 5:
            return ORANGE
        elif self.combo_count >= 3:
            return YELLOW
        return WHITE

    def reset(self):
        """Reset combo display"""
        self.combo_count = 0
        self.combo_damage = 0
        self.combo_name = ""
        self.is_active = False
        self.scale = 1.0


class DualComboDisplay:
    """
    Manages combo displays untuk kedua fighters.
    """

    def __init__(self):
        # Fighter 1 (left side)
        self.display1 = ComboDisplay(50, 200, is_right_side=False)

        # Fighter 2 (right side)
        self.display2 = ComboDisplay(SCREEN_WIDTH - 50, 200, is_right_side=True)

    def update(self, dt: float):
        self.display1.update(dt)
        self.display2.update(dt)

    def render(self, surface: pygame.Surface):
        self.display1.render(surface)
        self.display2.render(surface)

    def set_fighter1_combo(self, count: int, damage: float = 0, name: str = ""):
        self.display1.set_combo(count, damage, name)

    def set_fighter2_combo(self, count: int, damage: float = 0, name: str = ""):
        self.display2.set_combo(count, damage, name)

    def reset(self):
        self.display1.reset()
        self.display2.reset()
