"""
Main Renderer
=============
Menggabungkan semua sistem graphics untuk rendering.
"""

import pygame
from typing import List, Optional, Tuple
import sys
sys.path.insert(0, '..')

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    RING_LEFT, RING_RIGHT, RING_TOP, RING_BOTTOM, RING_FLOOR_Y,
    FIGHTER_WIDTH, FIGHTER_HEIGHT,
    BLACK, WHITE, RED, BLUE, DARK_RED, DARK_BLUE,
    RING_CANVAS, RING_ROPE_RED, RING_ROPE_WHITE, RING_ROPE_BLUE,
    RING_POST, RING_APRON, DEBUG_HITBOXES, DEBUG_DISTANCES,
    AnimationState
)
from graphics.sprites import FighterSprites, RingSprites, BackgroundSprites
from graphics.effects import EffectsManager


class Renderer:
    """
    Main renderer untuk game.
    """

    def __init__(self):
        # Initialize sprites
        self.fighter1_sprites = FighterSprites(RED, DARK_RED)
        self.fighter2_sprites = FighterSprites(BLUE, DARK_BLUE)

        # Background surfaces (cached)
        self._background = None
        self._ring = None
        self._create_static_surfaces()

        # Effects manager
        self.effects = EffectsManager()

        # Debug
        self.debug_hitboxes = DEBUG_HITBOXES
        self.debug_distances = DEBUG_DISTANCES

    def _create_static_surfaces(self):
        """Create cached static surfaces"""
        # Background
        self._background = BackgroundSprites.create_crowd_surface(
            SCREEN_WIDTH, SCREEN_HEIGHT
        )

        # Ring
        self._ring = RingSprites.create_ring_surface(
            SCREEN_WIDTH, SCREEN_HEIGHT
        )

    def render(self, surface: pygame.Surface,
               fighters: List,
               particle_system=None,
               offset_x: float = 0,
               offset_y: float = 0,
               zoom: float = 1.0):
        """
        Render complete game frame.
        """
        # Clear
        surface.fill(BLACK)

        # Apply camera transform
        # For simplicity, we'll apply offset without zoom for now
        # Full zoom would require scaling surfaces

        # Draw background
        surface.blit(self._background, (0, 0))

        # Draw ring
        surface.blit(self._ring, (offset_x, offset_y))

        # Draw fighters
        if fighters:
            # Sort by Y for proper layering
            sorted_fighters = sorted(fighters, key=lambda f: f.y)

            for i, fighter in enumerate(sorted_fighters):
                sprites = self.fighter1_sprites if fighter.is_player_one else self.fighter2_sprites
                self._render_fighter(surface, fighter, sprites, offset_x, offset_y)

        # Draw particles
        if particle_system:
            particle_system.render(surface, offset_x, offset_y)

        # Draw effects
        self.effects.render(surface)

        # Debug overlays
        if self.debug_hitboxes and fighters:
            self._render_debug_hitboxes(surface, fighters, offset_x, offset_y)

        if self.debug_distances and len(fighters) >= 2:
            self._render_debug_distances(surface, fighters, offset_x, offset_y)

    def _render_fighter(self, surface: pygame.Surface,
                        fighter, sprites: FighterSprites,
                        offset_x: float, offset_y: float):
        """Render single fighter"""
        # Get sprite
        sprite = sprites.get_sprite(
            fighter.animation_state,
            fighter.animation_frame,
            fighter.facing_right
        )

        # Calculate position
        x = fighter.x - FIGHTER_WIDTH // 2 + offset_x
        y = fighter.y - FIGHTER_HEIGHT + offset_y

        # Apply flash effect
        if hasattr(fighter, 'flash_timer') and fighter.flash_timer > 0:
            # Create white flash version
            flash_sprite = sprite.copy()
            flash_sprite.fill((255, 255, 255, 128), special_flags=pygame.BLEND_ADD)
            surface.blit(flash_sprite, (x, y))
        else:
            surface.blit(sprite, (x, y))

        # Draw shadow
        shadow_y = RING_FLOOR_Y + 5 + offset_y
        shadow_width = FIGHTER_WIDTH * 0.8
        shadow_height = 10
        shadow_x = fighter.x - shadow_width // 2 + offset_x

        shadow_surface = pygame.Surface((int(shadow_width), int(shadow_height)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 80),
                           (0, 0, shadow_width, shadow_height))
        surface.blit(shadow_surface, (shadow_x, shadow_y))

    def _render_debug_hitboxes(self, surface: pygame.Surface,
                                fighters: List,
                                offset_x: float, offset_y: float):
        """Render hitbox/hurtbox debug overlay"""
        for fighter in fighters:
            # Hurtboxes (green)
            for hurtbox in fighter.hurtbox_manager.hurtboxes:
                rect = hurtbox.get_rect(fighter.x, fighter.y, fighter.facing_right)
                pygame.draw.rect(surface, (0, 255, 0, 100),
                               (rect[0] + offset_x, rect[1] + offset_y,
                                rect[2], rect[3]), 2)

            # Active hitbox (red)
            if (hasattr(fighter, 'current_action') and
                fighter.current_action and
                fighter.current_action.hitbox and
                fighter.current_action.hitbox.is_active):

                hitbox = fighter.current_action.hitbox
                rect = hitbox.get_rect(fighter.x, fighter.y, fighter.facing_right)
                pygame.draw.rect(surface, (255, 0, 0, 150),
                               (rect[0] + offset_x, rect[1] + offset_y,
                                rect[2], rect[3]), 3)

    def _render_debug_distances(self, surface: pygame.Surface,
                                 fighters: List,
                                 offset_x: float, offset_y: float):
        """Render distance debug info"""
        if len(fighters) < 2:
            return

        f1, f2 = fighters[0], fighters[1]
        distance = abs(f2.x - f1.x)

        # Draw line between fighters
        y = RING_FLOOR_Y - 50 + offset_y
        pygame.draw.line(surface, WHITE,
                        (f1.x + offset_x, y),
                        (f2.x + offset_x, y), 2)

        # Distance text
        font = pygame.font.Font(None, 24)
        text = font.render(f"{int(distance)}px", True, WHITE)
        text_x = (f1.x + f2.x) / 2 - text.get_width() // 2 + offset_x
        surface.blit(text, (text_x, y - 20))

    def render_ui_background(self, surface: pygame.Surface):
        """Render UI background elements"""
        # Top bar
        pygame.draw.rect(surface, (20, 20, 30),
                        (0, 0, SCREEN_WIDTH, 80))

        # Bottom bar
        pygame.draw.rect(surface, (20, 20, 30),
                        (0, SCREEN_HEIGHT - 100, SCREEN_WIDTH, 100))

    def trigger_hit_effect(self, position: Tuple[float, float],
                           damage: float, is_crit: bool = False):
        """Trigger visual effects untuk hit"""
        self.effects.spawn_hit_spark(position[0], position[1],
                                     size=20 + damage, is_crit=is_crit)
        self.effects.spawn_damage_popup(position[0], position[1] - 50,
                                        int(damage), is_crit=is_crit)

        if damage >= 20:
            self.effects.trigger_flash(WHITE, 0.05, 0.3)

        if is_crit:
            self.effects.trigger_shake(damage * 0.3)
            self.effects.trigger_vignette(0.3)

    def trigger_block_effect(self, position: Tuple[float, float]):
        """Trigger visual effects untuk block"""
        self.effects.spawn_text_popup(
            position[0], position[1] - 60,
            "BLOCKED", (100, 150, 255), 20, 0.5
        )

    def trigger_ko_effect(self, position: Tuple[float, float]):
        """Trigger KO visual effects"""
        self.effects.trigger_flash(RED, 0.2, 0.8)
        self.effects.trigger_shake(20)
        self.effects.trigger_vignette(0.7)
        self.effects.spawn_text_popup(
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100,
            "K.O.!", RED, 72, 3.0
        )

    def update_effects(self, dt: float) -> float:
        """Update effects dan return modified dt"""
        return self.effects.update(dt)

    def clear_effects(self):
        """Clear all effects"""
        self.effects.clear()
