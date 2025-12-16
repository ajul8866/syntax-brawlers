"""
HUD System
==========
Health bars, stamina bars, timer, round indicator.
"""

import pygame
from typing import Tuple, Optional
import sys
sys.path.insert(0, '..')

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    WHITE, BLACK, GRAY, DARK_GRAY,
    RED, DARK_RED, BRIGHT_RED,
    GREEN, DARK_GREEN, HEALTH_GREEN, HEALTH_YELLOW, HEALTH_RED,
    YELLOW, GOLD, STAMINA_GOLD,
    BLUE, DARK_BLUE
)


class HealthBar:
    """
    Health bar dengan animasi smooth dan efek visual.
    """

    def __init__(self, x: int, y: int, width: int, height: int,
                 is_flipped: bool = False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.is_flipped = is_flipped

        # Values
        self.current = 100.0
        self.target = 100.0
        self.max_value = 100.0

        # Animation
        self.damage_display = 100.0  # Delayed damage bar
        self.damage_delay = 0.0
        self.lerp_speed = 5.0
        self.damage_lerp_speed = 2.0

        # Colors
        self.bg_color = DARK_GRAY
        self.border_color = WHITE
        self.damage_color = RED

    def set_value(self, value: float, max_value: float = 100.0):
        """Set health value"""
        self.target = max(0, min(max_value, value))
        self.max_value = max_value

    def update(self, dt: float):
        """Update animation"""
        # Smooth lerp current to target
        diff = self.target - self.current
        self.current += diff * self.lerp_speed * dt

        # Delayed damage bar
        if self.damage_delay > 0:
            self.damage_delay -= dt
        else:
            diff = self.current - self.damage_display
            self.damage_display += diff * self.damage_lerp_speed * dt

        # Trigger delay when damage taken
        if self.target < self.damage_display - 1:
            self.damage_delay = 0.3

    def render(self, surface: pygame.Surface):
        """Render health bar"""
        # Background
        pygame.draw.rect(surface, self.bg_color,
                        (self.x, self.y, self.width, self.height))

        # Calculate fill widths
        current_ratio = self.current / self.max_value
        damage_ratio = self.damage_display / self.max_value

        current_width = int(self.width * current_ratio)
        damage_width = int(self.width * damage_ratio)

        # Determine fill direction
        if self.is_flipped:
            # Right to left
            current_x = self.x + self.width - current_width
            damage_x = self.x + self.width - damage_width
        else:
            # Left to right
            current_x = self.x
            damage_x = self.x

        # Damage bar (red, behind health)
        if damage_width > current_width:
            pygame.draw.rect(surface, self.damage_color,
                           (damage_x if not self.is_flipped else current_x,
                            self.y,
                            damage_width - current_width if not self.is_flipped else damage_width,
                            self.height))

        # Health bar (gradient based on health)
        health_color = self._get_health_color(current_ratio)
        if current_width > 0:
            pygame.draw.rect(surface, health_color,
                           (current_x, self.y, current_width, self.height))

        # Border
        pygame.draw.rect(surface, self.border_color,
                        (self.x, self.y, self.width, self.height), 2)

        # Highlight at top
        highlight_rect = pygame.Rect(self.x + 2, self.y + 2,
                                    self.width - 4, self.height // 4)
        highlight_surface = pygame.Surface(highlight_rect.size, pygame.SRCALPHA)
        highlight_surface.fill((255, 255, 255, 40))
        surface.blit(highlight_surface, highlight_rect.topleft)

    def _get_health_color(self, ratio: float) -> Tuple[int, int, int]:
        """Get color based on health ratio"""
        if ratio > 0.6:
            return HEALTH_GREEN
        elif ratio > 0.3:
            return HEALTH_YELLOW
        else:
            return HEALTH_RED


class StaminaBar:
    """
    Stamina bar dengan style berbeda dari health.
    """

    def __init__(self, x: int, y: int, width: int, height: int,
                 is_flipped: bool = False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.is_flipped = is_flipped

        self.current = 100.0
        self.target = 100.0
        self.max_value = 100.0
        self.lerp_speed = 8.0

        self.bg_color = (30, 30, 40)
        self.fill_color = STAMINA_GOLD
        self.exhausted_color = (100, 80, 40)
        self.border_color = (80, 70, 50)

    def set_value(self, value: float, max_value: float = 100.0):
        self.target = max(0, min(max_value, value))
        self.max_value = max_value

    def update(self, dt: float):
        diff = self.target - self.current
        self.current += diff * self.lerp_speed * dt

    def render(self, surface: pygame.Surface):
        # Background
        pygame.draw.rect(surface, self.bg_color,
                        (self.x, self.y, self.width, self.height))

        # Fill
        ratio = self.current / self.max_value
        fill_width = int(self.width * ratio)

        if fill_width > 0:
            color = self.fill_color if ratio > 0.2 else self.exhausted_color

            if self.is_flipped:
                fill_x = self.x + self.width - fill_width
            else:
                fill_x = self.x

            pygame.draw.rect(surface, color,
                           (fill_x, self.y, fill_width, self.height))

        # Border
        pygame.draw.rect(surface, self.border_color,
                        (self.x, self.y, self.width, self.height), 1)


class RoundTimer:
    """
    Round timer display.
    """

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.time_remaining = 180.0
        self.is_critical = False

        self.font = None
        self._init_font()

    def _init_font(self):
        self.font = pygame.font.Font(None, 48)

    def set_time(self, seconds: float):
        self.time_remaining = max(0, seconds)
        self.is_critical = self.time_remaining <= 30

    def update(self, dt: float):
        # Timer update dilakukan di game logic
        pass

    def render(self, surface: pygame.Surface):
        if self.font is None:
            self._init_font()

        # Format time
        minutes = int(self.time_remaining // 60)
        seconds = int(self.time_remaining % 60)
        time_str = f"{minutes}:{seconds:02d}"

        # Color
        color = RED if self.is_critical else WHITE

        # Render
        text = self.font.render(time_str, True, color)
        text_rect = text.get_rect(center=(self.x, self.y))
        surface.blit(text, text_rect)


class RoundIndicator:
    """
    Round number and wins indicator.
    """

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.current_round = 1
        self.max_rounds = 3
        self.fighter1_wins = 0
        self.fighter2_wins = 0

        self.font = None
        self._init_font()

    def _init_font(self):
        self.font = pygame.font.Font(None, 28)

    def set_round(self, round_num: int, f1_wins: int, f2_wins: int):
        self.current_round = round_num
        self.fighter1_wins = f1_wins
        self.fighter2_wins = f2_wins

    def render(self, surface: pygame.Surface):
        if self.font is None:
            self._init_font()

        # Round text
        round_text = f"ROUND {self.current_round}"
        text = self.font.render(round_text, True, WHITE)
        text_rect = text.get_rect(center=(self.x, self.y))
        surface.blit(text, text_rect)

        # Win indicators
        indicator_y = self.y + 25
        indicator_size = 10
        spacing = 15

        # Fighter 1 wins (left)
        for i in range(self.max_rounds - 1):
            x = self.x - 40 - i * spacing
            color = GOLD if i < self.fighter1_wins else DARK_GRAY
            pygame.draw.circle(surface, color, (x, indicator_y), indicator_size // 2)

        # Fighter 2 wins (right)
        for i in range(self.max_rounds - 1):
            x = self.x + 40 + i * spacing
            color = GOLD if i < self.fighter2_wins else DARK_GRAY
            pygame.draw.circle(surface, color, (x, indicator_y), indicator_size // 2)


class HUD:
    """
    Main HUD class combining all elements.
    """

    def __init__(self):
        # Health bars
        bar_width = 350
        bar_height = 25
        bar_y = 30

        self.health_bar1 = HealthBar(50, bar_y, bar_width, bar_height, is_flipped=False)
        self.health_bar2 = HealthBar(SCREEN_WIDTH - 50 - bar_width, bar_y, bar_width, bar_height, is_flipped=True)

        # Stamina bars
        stamina_width = 300
        stamina_height = 10
        stamina_y = bar_y + bar_height + 5

        self.stamina_bar1 = StaminaBar(50, stamina_y, stamina_width, stamina_height, is_flipped=False)
        self.stamina_bar2 = StaminaBar(SCREEN_WIDTH - 50 - stamina_width, stamina_y, stamina_width, stamina_height, is_flipped=True)

        # Timer
        self.timer = RoundTimer(SCREEN_WIDTH // 2, 45)

        # Round indicator
        self.round_indicator = RoundIndicator(SCREEN_WIDTH // 2, 80)

        # Names
        self.fighter1_name = "FIGHTER 1"
        self.fighter2_name = "FIGHTER 2"
        self.name_font = None

    def _init_fonts(self):
        if self.name_font is None:
            self.name_font = pygame.font.Font(None, 24)

    def update(self, dt: float, fighter1=None, fighter2=None,
               round_time: float = 180.0, round_num: int = 1,
               f1_wins: int = 0, f2_wins: int = 0):
        """Update HUD dengan game state"""
        if fighter1:
            self.health_bar1.set_value(fighter1.stats.health, fighter1.stats.max_health)
            self.stamina_bar1.set_value(fighter1.stats.stamina, fighter1.stats.max_stamina)
            self.fighter1_name = fighter1.name

        if fighter2:
            self.health_bar2.set_value(fighter2.stats.health, fighter2.stats.max_health)
            self.stamina_bar2.set_value(fighter2.stats.stamina, fighter2.stats.max_stamina)
            self.fighter2_name = fighter2.name

        self.timer.set_time(round_time)
        self.round_indicator.set_round(round_num, f1_wins, f2_wins)

        # Update animations
        self.health_bar1.update(dt)
        self.health_bar2.update(dt)
        self.stamina_bar1.update(dt)
        self.stamina_bar2.update(dt)

    def render(self, surface: pygame.Surface):
        """Render entire HUD"""
        self._init_fonts()

        # Background panel
        panel_height = 100
        panel = pygame.Surface((SCREEN_WIDTH, panel_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        surface.blit(panel, (0, 0))

        # Health bars
        self.health_bar1.render(surface)
        self.health_bar2.render(surface)

        # Stamina bars
        self.stamina_bar1.render(surface)
        self.stamina_bar2.render(surface)

        # Names
        name1 = self.name_font.render(self.fighter1_name, True, RED)
        name2 = self.name_font.render(self.fighter2_name, True, BLUE)
        surface.blit(name1, (55, 10))
        surface.blit(name2, (SCREEN_WIDTH - 55 - name2.get_width(), 10))

        # Timer
        self.timer.render(surface)

        # Round indicator
        self.round_indicator.render(surface)
