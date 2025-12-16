"""
Visual Effects System
=====================
Screen effects: flash, shake, zoom, slow-mo, etc.
"""

import pygame
import math
import random
from typing import Optional, Tuple, List
from dataclasses import dataclass
import sys
sys.path.insert(0, '..')

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    SHAKE_LIGHT, SHAKE_MEDIUM, SHAKE_HEAVY, SHAKE_DECAY,
    HIT_FREEZE_DURATION, HIT_FREEZE_SCALE,
    WHITE, RED, YELLOW, ORANGE
)


@dataclass
class ScreenFlash:
    """Screen flash effect"""
    color: Tuple[int, int, int]
    duration: float
    intensity: float  # 0.0 - 1.0
    timer: float = 0

    def update(self, dt: float) -> bool:
        """Update flash. Return True if still active."""
        self.timer += dt
        return self.timer < self.duration

    def get_alpha(self) -> int:
        """Get current alpha"""
        progress = self.timer / self.duration
        # Fade out
        return int(255 * self.intensity * (1 - progress))


@dataclass
class HitSpark:
    """Hit spark visual effect"""
    x: float
    y: float
    size: float
    duration: float
    timer: float = 0
    color: Tuple[int, int, int] = WHITE

    def update(self, dt: float) -> bool:
        self.timer += dt
        return self.timer < self.duration

    def get_scale(self) -> float:
        """Get current scale (expands then contracts)"""
        progress = self.timer / self.duration
        if progress < 0.3:
            return progress / 0.3  # Expand
        return 1 - (progress - 0.3) / 0.7  # Contract


@dataclass
class TextPopup:
    """Floating text popup (for damage numbers, combo text)"""
    text: str
    x: float
    y: float
    color: Tuple[int, int, int]
    font_size: int
    duration: float
    timer: float = 0
    velocity_y: float = -50
    fade: bool = True

    def update(self, dt: float) -> bool:
        self.timer += dt
        self.y += self.velocity_y * dt
        self.velocity_y *= 0.95  # Slow down
        return self.timer < self.duration

    def get_alpha(self) -> int:
        if not self.fade:
            return 255
        progress = self.timer / self.duration
        if progress > 0.7:
            return int(255 * (1 - (progress - 0.7) / 0.3))
        return 255


class EffectsManager:
    """
    Manages all visual effects.
    """

    def __init__(self):
        # Screen shake
        self.shake_intensity = 0.0
        self.shake_offset = (0, 0)

        # Hit freeze (slow-mo)
        self.hit_freeze_active = False
        self.hit_freeze_timer = 0.0
        self.time_scale = 1.0

        # Flash effects
        self.flashes: List[ScreenFlash] = []

        # Hit sparks
        self.sparks: List[HitSpark] = []

        # Text popups
        self.popups: List[TextPopup] = []

        # Vignette
        self.vignette_intensity = 0.0

        # Dramatic zoom
        self.zoom_target = 1.0
        self.zoom_current = 1.0
        self.zoom_speed = 2.0

    def update(self, dt: float) -> float:
        """
        Update all effects.
        Return modified dt for time scaling.
        """
        # Update hit freeze
        if self.hit_freeze_active:
            self.hit_freeze_timer -= dt
            if self.hit_freeze_timer <= 0:
                self.hit_freeze_active = False
                self.time_scale = 1.0
            dt *= self.time_scale

        # Update shake
        if self.shake_intensity > 0:
            self.shake_offset = (
                random.uniform(-self.shake_intensity, self.shake_intensity),
                random.uniform(-self.shake_intensity, self.shake_intensity)
            )
            self.shake_intensity *= SHAKE_DECAY
            if self.shake_intensity < 0.5:
                self.shake_intensity = 0
                self.shake_offset = (0, 0)

        # Update flashes
        self.flashes = [f for f in self.flashes if f.update(dt)]

        # Update sparks
        self.sparks = [s for s in self.sparks if s.update(dt)]

        # Update popups
        self.popups = [p for p in self.popups if p.update(dt)]

        # Update zoom
        if self.zoom_current != self.zoom_target:
            diff = self.zoom_target - self.zoom_current
            self.zoom_current += diff * self.zoom_speed * dt
            if abs(diff) < 0.01:
                self.zoom_current = self.zoom_target

        # Decay vignette
        if self.vignette_intensity > 0:
            self.vignette_intensity *= 0.95
            if self.vignette_intensity < 0.01:
                self.vignette_intensity = 0

        return dt

    def trigger_shake(self, intensity: float = SHAKE_MEDIUM):
        """Trigger screen shake"""
        self.shake_intensity = max(self.shake_intensity, intensity)

    def trigger_hit_freeze(self, duration: float = HIT_FREEZE_DURATION):
        """Trigger hit freeze (slow-mo)"""
        self.hit_freeze_active = True
        self.hit_freeze_timer = duration
        self.time_scale = HIT_FREEZE_SCALE

    def trigger_flash(self, color: Tuple[int, int, int] = WHITE,
                      duration: float = 0.1, intensity: float = 0.5):
        """Trigger screen flash"""
        self.flashes.append(ScreenFlash(
            color=color,
            duration=duration,
            intensity=intensity
        ))

    def spawn_hit_spark(self, x: float, y: float,
                        size: float = 30, is_crit: bool = False):
        """Spawn hit spark effect"""
        color = YELLOW if not is_crit else ORANGE
        duration = 0.15 if not is_crit else 0.25
        size = size if not is_crit else size * 1.5

        self.sparks.append(HitSpark(
            x=x, y=y,
            size=size,
            duration=duration,
            color=color
        ))

    def spawn_damage_popup(self, x: float, y: float,
                           damage: int, is_crit: bool = False):
        """Spawn floating damage number"""
        color = YELLOW if not is_crit else RED
        size = 28 if not is_crit else 36
        text = str(damage) if not is_crit else f"{damage}!"

        self.popups.append(TextPopup(
            text=text,
            x=x, y=y,
            color=color,
            font_size=size,
            duration=1.0,
            velocity_y=-80 if not is_crit else -120
        ))

    def spawn_text_popup(self, x: float, y: float, text: str,
                         color: Tuple[int, int, int] = WHITE,
                         size: int = 24, duration: float = 1.0):
        """Spawn custom text popup"""
        self.popups.append(TextPopup(
            text=text,
            x=x, y=y,
            color=color,
            font_size=size,
            duration=duration
        ))

    def set_dramatic_zoom(self, zoom: float, speed: float = 2.0):
        """Set zoom target for dramatic effect"""
        self.zoom_target = zoom
        self.zoom_speed = speed

    def reset_zoom(self):
        """Reset zoom to normal"""
        self.zoom_target = 1.0

    def trigger_vignette(self, intensity: float = 0.5):
        """Trigger vignette effect"""
        self.vignette_intensity = intensity

    def render(self, surface: pygame.Surface):
        """Render all effects on top of game"""
        # Render sparks
        for spark in self.sparks:
            self._render_spark(surface, spark)

        # Render popups
        for popup in self.popups:
            self._render_popup(surface, popup)

        # Render flashes
        for flash in self.flashes:
            self._render_flash(surface, flash)

        # Render vignette
        if self.vignette_intensity > 0:
            self._render_vignette(surface)

    def _render_spark(self, surface: pygame.Surface, spark: HitSpark):
        """Render hit spark"""
        scale = spark.get_scale()
        size = int(spark.size * scale)

        if size <= 0:
            return

        # Draw burst lines
        for i in range(8):
            angle = math.radians(i * 45)
            end_x = spark.x + math.cos(angle) * size
            end_y = spark.y + math.sin(angle) * size

            # Fade with distance
            alpha = int(255 * (1 - spark.timer / spark.duration))
            color = (*spark.color, alpha)

            # Draw line
            temp = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.line(temp, color,
                           (size, size),
                           (size + math.cos(angle) * size,
                            size + math.sin(angle) * size), 3)
            surface.blit(temp, (spark.x - size, spark.y - size))

        # Center glow
        glow_size = int(size * 0.5)
        glow_surface = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        alpha = int(200 * (1 - spark.timer / spark.duration))
        pygame.draw.circle(glow_surface, (*WHITE, alpha),
                          (glow_size, glow_size), glow_size)
        surface.blit(glow_surface, (spark.x - glow_size, spark.y - glow_size))

    def _render_popup(self, surface: pygame.Surface, popup: TextPopup):
        """Render text popup"""
        font = pygame.font.Font(None, popup.font_size)
        alpha = popup.get_alpha()

        # Render text with outline
        text_surface = font.render(popup.text, True, popup.color)

        # Create surface with alpha
        final_surface = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
        final_surface.blit(text_surface, (0, 0))
        final_surface.set_alpha(alpha)

        # Position (centered)
        x = popup.x - text_surface.get_width() // 2
        y = popup.y - text_surface.get_height() // 2

        surface.blit(final_surface, (x, y))

    def _render_flash(self, surface: pygame.Surface, flash: ScreenFlash):
        """Render screen flash"""
        alpha = flash.get_alpha()
        if alpha <= 0:
            return

        flash_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        flash_surface.fill((*flash.color, alpha))
        surface.blit(flash_surface, (0, 0))

    def _render_vignette(self, surface: pygame.Surface):
        """Render vignette effect"""
        vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        # Draw gradient from edges
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        max_radius = math.sqrt(center_x**2 + center_y**2)

        for i in range(10):
            radius = max_radius - (i * max_radius / 10)
            alpha = int(self.vignette_intensity * 255 * (1 - i / 10))
            pygame.draw.circle(vignette, (0, 0, 0, alpha),
                             (center_x, center_y), int(radius))

        surface.blit(vignette, (0, 0))

    def get_shake_offset(self) -> Tuple[float, float]:
        """Get current shake offset"""
        return self.shake_offset

    def get_zoom(self) -> float:
        """Get current zoom level"""
        return self.zoom_current

    def clear(self):
        """Clear all effects"""
        self.shake_intensity = 0
        self.shake_offset = (0, 0)
        self.hit_freeze_active = False
        self.time_scale = 1.0
        self.flashes.clear()
        self.sparks.clear()
        self.popups.clear()
        self.vignette_intensity = 0
        self.zoom_current = 1.0
        self.zoom_target = 1.0
