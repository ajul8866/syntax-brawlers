"""
UI Manager
==========
Main manager yang mengintegrasikan semua UI components.
"""

import pygame
from typing import Optional, Tuple, Any
import sys
sys.path.insert(0, '..')

from config import GameState, SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, RED, BLUE
from ui.hud import HUD
from ui.text_box import TrashTalkDisplay, AnnouncerText
from ui.menu import MainMenu, PauseMenu, CharacterSelectMenu
from ui.combo_display import DualComboDisplay


class UIManager:
    """
    Manages semua UI dalam game.
    """

    def __init__(self):
        # HUD
        self.hud = HUD()

        # Menus
        self.main_menu = MainMenu()
        self.pause_menu = PauseMenu()
        self.character_select = CharacterSelectMenu()

        # Displays
        self.trash_talk = TrashTalkDisplay()
        self.announcer = AnnouncerText()
        self.combo_display = DualComboDisplay()

        # State
        self._current_menu = None

    def update(self, dt: float, game_state: GameState,
               fighter1=None, fighter2=None,
               round_time: float = 180.0, round_num: int = 1,
               f1_wins: int = 0, f2_wins: int = 0):
        """Update UI based on game state"""
        # Update HUD during fighting
        if game_state == GameState.FIGHTING:
            self.hud.update(dt, fighter1, fighter2, round_time, round_num, f1_wins, f2_wins)

        # Update displays
        self.trash_talk.update(dt)
        self.announcer.update(dt)
        self.combo_display.update(dt)

    def render(self, surface: pygame.Surface, game_state: GameState):
        """Render UI based on game state"""
        if game_state == GameState.MAIN_MENU:
            self.main_menu.render(surface)

        elif game_state == GameState.CHARACTER_SELECT:
            self.character_select.render(surface)

        elif game_state in (GameState.FIGHTING, GameState.PRE_FIGHT,
                           GameState.ROUND_END, GameState.MATCH_END):
            # HUD
            self.hud.render(surface)

            # Combo displays
            self.combo_display.render(surface)

            # Trash talk
            self.trash_talk.render(surface)

            # Announcer (on top)
            self.announcer.render(surface)

        elif game_state == GameState.PAUSED:
            # Show HUD behind pause menu
            self.hud.render(surface)
            self.pause_menu.render(surface)

    # Menu handling
    def show_main_menu(self):
        """Show main menu"""
        self._current_menu = self.main_menu

    def update_main_menu(self, input_handler) -> Optional[str]:
        """Update main menu and return action"""
        return self.main_menu.update(0.016, input_handler)

    def show_character_select(self):
        """Show character select"""
        self._current_menu = self.character_select

    def update_character_select(self, input_handler) -> Optional[Tuple[str, str]]:
        """Update character select and return selections"""
        return self.character_select.update(input_handler)

    def show_llm_config(self):
        """Show LLM config (placeholder for now)"""
        pass

    def update_llm_config(self, input_handler) -> Optional[dict]:
        """Update LLM config"""
        # For now, just return default config on enter
        if input_handler.is_key_just_pressed(pygame.K_RETURN):
            return {'use_llm': True}
        return None

    def show_pause_menu(self):
        """Show pause menu"""
        self._current_menu = self.pause_menu

    def update_pause_menu(self, input_handler) -> Optional[str]:
        """Update pause menu and return action"""
        return self.pause_menu.update(0.016, input_handler)

    # Display methods
    def add_trash_talk(self, text: str, speaker: str, is_fighter1: bool = True):
        """Add trash talk message"""
        color = RED if is_fighter1 else BLUE
        self.trash_talk.add_message(text, speaker, color)

    def show_announcer_text(self, text: str, subtitle: str = "",
                            duration: float = 2.0):
        """Show big announcer text"""
        self.announcer.show(text, subtitle, duration)

    def update_combo(self, fighter_index: int, count: int,
                     damage: float = 0, name: str = ""):
        """Update combo display for fighter"""
        if fighter_index == 0:
            self.combo_display.set_fighter1_combo(count, damage, name)
        else:
            self.combo_display.set_fighter2_combo(count, damage, name)

    def show_round_result(self, winner_index: int, round_num: int):
        """Show round end result"""
        winner = "FIGHTER 1" if winner_index == 0 else "FIGHTER 2"
        self.show_announcer_text(f"{winner} WINS", f"Round {round_num}", 3.0)

    def show_match_result(self, winner_index: int):
        """Show match end result"""
        winner = "FIGHTER 1" if winner_index == 0 else "FIGHTER 2"
        self.show_announcer_text(f"{winner} WINS!", "K.O.!", 5.0)

    def show_round_start(self, round_num: int):
        """Show round start announcement"""
        self.show_announcer_text(f"ROUND {round_num}", "FIGHT!", 2.0)

    def show_ko(self):
        """Show KO announcement"""
        self.show_announcer_text("K.O.!", "", 3.0)

    def clear_displays(self):
        """Clear all temporary displays"""
        self.trash_talk.clear()
        self.combo_display.reset()

    def reset(self):
        """Reset all UI for new match"""
        self.clear_displays()
        self.combo_display.reset()
