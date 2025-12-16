"""
Menu System
===========
Main menu, pause menu, dan menu screens lainnya.
"""

import pygame
from typing import List, Optional, Callable, Tuple
from dataclasses import dataclass
import sys
sys.path.insert(0, '..')

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GAME_TITLE,
    WHITE, BLACK, GRAY, DARK_GRAY, RED, BLUE, YELLOW, GOLD
)


@dataclass
class MenuItem:
    """Single menu item"""
    text: str
    action: str
    enabled: bool = True
    selected: bool = False


class MenuSystem:
    """
    Base menu system dengan selection dan navigation.
    """

    def __init__(self):
        self.items: List[MenuItem] = []
        self.selected_index = 0

        # Visual settings
        self.x = SCREEN_WIDTH // 2
        self.y_start = SCREEN_HEIGHT // 2
        self.item_spacing = 50

        # Fonts
        self.font = None
        self.title_font = None
        self._init_fonts()

        # Colors
        self.normal_color = WHITE
        self.selected_color = YELLOW
        self.disabled_color = GRAY

        # Animation
        self.selection_offset = 0.0
        self.selection_timer = 0.0

    def _init_fonts(self):
        self.font = pygame.font.Font(None, 42)
        self.title_font = pygame.font.Font(None, 72)

    def add_item(self, text: str, action: str, enabled: bool = True):
        """Add menu item"""
        self.items.append(MenuItem(text=text, action=action, enabled=enabled))

    def clear_items(self):
        """Clear all items"""
        self.items.clear()
        self.selected_index = 0

    def move_selection(self, direction: int):
        """Move selection up or down"""
        if not self.items:
            return

        # Find next enabled item
        new_index = self.selected_index
        for _ in range(len(self.items)):
            new_index = (new_index + direction) % len(self.items)
            if self.items[new_index].enabled:
                break

        self.selected_index = new_index
        self.selection_timer = 0  # Reset animation

    def select_current(self) -> Optional[str]:
        """Select current item and return action"""
        if self.items and self.items[self.selected_index].enabled:
            return self.items[self.selected_index].action
        return None

    def update(self, dt: float, input_handler) -> Optional[str]:
        """Update menu and handle input"""
        # Navigation
        if input_handler.is_key_just_pressed(pygame.K_UP):
            self.move_selection(-1)
        elif input_handler.is_key_just_pressed(pygame.K_DOWN):
            self.move_selection(1)

        # Selection
        if input_handler.is_key_just_pressed(pygame.K_RETURN):
            return self.select_current()

        # Mouse handling
        mouse_pos = input_handler.get_mouse_pos()
        for i, item in enumerate(self.items):
            item_y = self.y_start + i * self.item_spacing
            item_rect = pygame.Rect(
                self.x - 150, item_y - 20,
                300, 40
            )
            if item_rect.collidepoint(mouse_pos):
                if item.enabled:
                    self.selected_index = i
                    if input_handler.is_mouse_clicked(0):
                        return self.select_current()

        # Animation
        self.selection_timer += dt
        self.selection_offset = 5 * abs(pygame.math.Vector2(1, 0).rotate(self.selection_timer * 360).x)

        return None

    def render(self, surface: pygame.Surface, title: str = ""):
        """Render menu"""
        if self.font is None:
            self._init_fonts()

        # Title
        if title:
            title_surface = self.title_font.render(title, True, WHITE)
            title_rect = title_surface.get_rect(center=(self.x, self.y_start - 150))
            surface.blit(title_surface, title_rect)

        # Items
        for i, item in enumerate(self.items):
            y = self.y_start + i * self.item_spacing

            # Color
            if not item.enabled:
                color = self.disabled_color
            elif i == self.selected_index:
                color = self.selected_color
            else:
                color = self.normal_color

            # Render text
            text_surface = self.font.render(item.text, True, color)
            text_rect = text_surface.get_rect(center=(self.x, y))

            # Selection indicator
            if i == self.selected_index:
                # Arrow indicator
                arrow = self.font.render(">", True, self.selected_color)
                arrow_x = text_rect.left - 30 - self.selection_offset
                surface.blit(arrow, (arrow_x, y - arrow.get_height() // 2))

            surface.blit(text_surface, text_rect)


class MainMenu(MenuSystem):
    """
    Main menu screen.
    """

    def __init__(self):
        super().__init__()
        self.y_start = SCREEN_HEIGHT // 2 + 50

        # Add items
        self.add_item("START FIGHT", "start")
        self.add_item("SETTINGS", "settings")
        self.add_item("QUIT", "quit")

        # Background animation
        self._bg_offset = 0

    def update(self, dt: float, input_handler) -> Optional[str]:
        self._bg_offset += dt * 20
        return super().update(dt, input_handler)

    def render(self, surface: pygame.Surface):
        # Background
        surface.fill((10, 10, 20))

        # Animated background lines
        for i in range(20):
            y = (i * 50 + self._bg_offset) % SCREEN_HEIGHT
            alpha = 30 + int(20 * abs(pygame.math.Vector2(1, 0).rotate(i * 18).x))
            line_surface = pygame.Surface((SCREEN_WIDTH, 2), pygame.SRCALPHA)
            line_surface.fill((255, 255, 255, alpha))
            surface.blit(line_surface, (0, y))

        # Title
        if self.title_font is None:
            self._init_fonts()

        # Main title
        title1 = self.title_font.render("SYNTAX", True, RED)
        title2 = self.title_font.render("BRAWLERS", True, BLUE)

        title1_rect = title1.get_rect(center=(SCREEN_WIDTH // 2, 150))
        title2_rect = title2.get_rect(center=(SCREEN_WIDTH // 2, 220))

        surface.blit(title1, title1_rect)
        surface.blit(title2, title2_rect)

        # Subtitle
        sub_font = pygame.font.Font(None, 28)
        subtitle = sub_font.render("LLM Arena Fighting v2.0", True, GRAY)
        sub_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 280))
        surface.blit(subtitle, sub_rect)

        # Menu items
        super().render(surface, "")


class PauseMenu(MenuSystem):
    """
    Pause menu overlay.
    """

    def __init__(self):
        super().__init__()

        self.add_item("RESUME", "resume")
        self.add_item("RESTART", "restart")
        self.add_item("QUIT TO MENU", "quit")

    def render(self, surface: pygame.Surface):
        # Darken background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        # Title
        super().render(surface, "PAUSED")


class CharacterSelectMenu:
    """
    Character/personality selection screen.
    """

    def __init__(self):
        self.personalities = [
            ('DESTROYER', 'Aggressive powerhouse', RED),
            ('TACTICIAN', 'Calculated fighter', BLUE),
            ('GHOST', 'Evasive counter-puncher', WHITE),
            ('WILDCARD', 'Unpredictable chaos', YELLOW),
        ]

        self.fighter1_selection = 0
        self.fighter2_selection = 1
        self.current_selector = 0  # 0 = fighter 1, 1 = fighter 2

        self.font = None
        self.title_font = None
        self._init_fonts()

    def _init_fonts(self):
        self.font = pygame.font.Font(None, 32)
        self.title_font = pygame.font.Font(None, 48)

    def update(self, input_handler) -> Optional[Tuple[str, str]]:
        """Update and return selection when confirmed"""
        # Switch selector
        if input_handler.is_key_just_pressed(pygame.K_TAB):
            self.current_selector = 1 - self.current_selector

        # Navigate
        if input_handler.is_key_just_pressed(pygame.K_UP):
            if self.current_selector == 0:
                self.fighter1_selection = (self.fighter1_selection - 1) % len(self.personalities)
            else:
                self.fighter2_selection = (self.fighter2_selection - 1) % len(self.personalities)

        if input_handler.is_key_just_pressed(pygame.K_DOWN):
            if self.current_selector == 0:
                self.fighter1_selection = (self.fighter1_selection + 1) % len(self.personalities)
            else:
                self.fighter2_selection = (self.fighter2_selection + 1) % len(self.personalities)

        # Confirm
        if input_handler.is_key_just_pressed(pygame.K_RETURN):
            p1 = self.personalities[self.fighter1_selection][0].lower()
            p2 = self.personalities[self.fighter2_selection][0].lower()
            return (p1, p2)

        return None

    def render(self, surface: pygame.Surface):
        if self.font is None:
            self._init_fonts()

        surface.fill((10, 10, 20))

        # Title
        title = self.title_font.render("SELECT FIGHTERS", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 80))
        surface.blit(title, title_rect)

        # Fighter 1 column
        self._render_column(surface, 250, "FIGHTER 1", self.fighter1_selection,
                           self.current_selector == 0, RED)

        # Fighter 2 column
        self._render_column(surface, SCREEN_WIDTH - 250, "FIGHTER 2", self.fighter2_selection,
                           self.current_selector == 1, BLUE)

        # Instructions
        instr = self.font.render("TAB to switch | UP/DOWN to select | ENTER to confirm", True, GRAY)
        instr_rect = instr.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        surface.blit(instr, instr_rect)

    def _render_column(self, surface: pygame.Surface, x: int, title: str,
                       selection: int, is_active: bool, color: Tuple[int, int, int]):
        """Render one selection column"""
        # Title
        title_surface = self.title_font.render(title, True, color)
        title_rect = title_surface.get_rect(center=(x, 150))
        surface.blit(title_surface, title_rect)

        # Active indicator
        if is_active:
            pygame.draw.rect(surface, color,
                           (x - 150, 180, 300, len(self.personalities) * 80 + 40), 3)

        # Options
        for i, (name, desc, pcolor) in enumerate(self.personalities):
            y = 220 + i * 80

            # Selection highlight
            if i == selection:
                highlight = pygame.Surface((280, 70), pygame.SRCALPHA)
                highlight.fill((*color, 50))
                surface.blit(highlight, (x - 140, y - 10))

            # Name
            name_color = pcolor if i == selection else GRAY
            name_surface = self.font.render(name, True, name_color)
            name_rect = name_surface.get_rect(center=(x, y + 10))
            surface.blit(name_surface, name_rect)

            # Description
            if i == selection:
                desc_font = pygame.font.Font(None, 24)
                desc_surface = desc_font.render(desc, True, WHITE)
                desc_rect = desc_surface.get_rect(center=(x, y + 35))
                surface.blit(desc_surface, desc_rect)
