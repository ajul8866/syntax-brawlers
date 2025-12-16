"""
Camera System
=============
Camera dengan smooth follow, zoom, dan shake.
"""

import pygame
import math
import random
from typing import Tuple, Optional
from dataclasses import dataclass
import sys
sys.path.insert(0, '..')

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    RING_LEFT, RING_RIGHT, RING_CENTER_X, RING_CENTER_Y,
    CAMERA_SMOOTHING, CAMERA_ZOOM_MIN, CAMERA_ZOOM_MAX,
    DRAMATIC_ZOOM_AMOUNT, SHAKE_DECAY
)


@dataclass
class CameraBounds:
    """Bounds untuk camera movement"""
    min_x: float
    max_x: float
    min_y: float
    max_y: float


class Camera:
    """
    Camera system untuk game.
    Supports smooth follow, zoom, shake, dan cinematic effects.
    """

    def __init__(self):
        # Position (center of view)
        self.x = RING_CENTER_X
        self.y = RING_CENTER_Y

        # Target (untuk smooth follow)
        self.target_x = self.x
        self.target_y = self.y

        # Zoom
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.zoom_speed = 2.0

        # Shake
        self.shake_intensity = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0

        # Smoothing
        self.smoothing = CAMERA_SMOOTHING

        # Bounds
        self.bounds = CameraBounds(
            min_x=RING_LEFT + SCREEN_WIDTH // 4,
            max_x=RING_RIGHT - SCREEN_WIDTH // 4,
            min_y=200,
            max_y=400
        )

        # Mode
        self.mode = 'follow'  # follow, fixed, cinematic

        # Cinematic
        self._cinematic_timer = 0
        self._cinematic_target = None

    def update(self, dt: float, fighter1=None, fighter2=None):
        """Update camera position and effects"""
        # Update target based on mode
        if self.mode == 'follow' and fighter1 and fighter2:
            self._update_follow_target(fighter1, fighter2)
        elif self.mode == 'cinematic' and self._cinematic_target:
            self._update_cinematic(dt)

        # Smooth lerp to target
        self.x += (self.target_x - self.x) * self.smoothing
        self.y += (self.target_y - self.y) * self.smoothing

        # Clamp to bounds
        self.x = max(self.bounds.min_x, min(self.bounds.max_x, self.x))
        self.y = max(self.bounds.min_y, min(self.bounds.max_y, self.y))

        # Update zoom
        if self.zoom != self.target_zoom:
            diff = self.target_zoom - self.zoom
            self.zoom += diff * self.zoom_speed * dt
            if abs(diff) < 0.01:
                self.zoom = self.target_zoom

        # Update shake
        if self.shake_intensity > 0:
            self.shake_offset_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_offset_y = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_intensity *= SHAKE_DECAY
            if self.shake_intensity < 0.5:
                self.shake_intensity = 0
                self.shake_offset_x = 0
                self.shake_offset_y = 0

    def _update_follow_target(self, fighter1, fighter2):
        """Update target untuk follow mode (focus between fighters)"""
        # Get fighter positions
        f1_x = fighter1.x
        f2_x = fighter2.x

        # Target is midpoint between fighters
        mid_x = (f1_x + f2_x) / 2
        mid_y = RING_CENTER_Y

        self.target_x = mid_x
        self.target_y = mid_y

        # Auto-zoom berdasarkan jarak
        distance = abs(f2_x - f1_x)

        if distance < 150:
            # Close - zoom in
            self.target_zoom = 1.2
        elif distance < 300:
            # Medium
            self.target_zoom = 1.0
        else:
            # Far - zoom out
            self.target_zoom = 0.9

    def _update_cinematic(self, dt: float):
        """Update cinematic mode"""
        self._cinematic_timer -= dt
        if self._cinematic_timer <= 0:
            self.mode = 'follow'
            self._cinematic_target = None
            self.target_zoom = 1.0
        else:
            self.target_x = self._cinematic_target[0]
            self.target_y = self._cinematic_target[1]

    def shake(self, intensity: float):
        """Trigger camera shake"""
        self.shake_intensity = max(self.shake_intensity, intensity)

    def set_zoom(self, zoom: float, speed: float = 2.0):
        """Set zoom target"""
        self.target_zoom = max(CAMERA_ZOOM_MIN, min(CAMERA_ZOOM_MAX, zoom))
        self.zoom_speed = speed

    def focus_on(self, x: float, y: float, duration: float = 1.0,
                 zoom: float = 1.3):
        """Focus kamera pada point tertentu (cinematic)"""
        self.mode = 'cinematic'
        self._cinematic_target = (x, y)
        self._cinematic_timer = duration
        self.target_zoom = zoom

    def dramatic_zoom(self, target_x: float, target_y: float):
        """Dramatic zoom untuk big moments"""
        self.focus_on(target_x, target_y, duration=0.5, zoom=DRAMATIC_ZOOM_AMOUNT)

    def reset(self):
        """Reset camera ke default"""
        self.mode = 'follow'
        self.target_zoom = 1.0
        self.zoom = 1.0
        self.shake_intensity = 0
        self.x = RING_CENTER_X
        self.y = RING_CENTER_Y

    def get_offset(self) -> Tuple[float, float]:
        """
        Get offset untuk rendering.
        Semua objek di-render dengan offset ini.
        """
        # Calculate offset dari center screen
        offset_x = SCREEN_WIDTH // 2 - self.x * self.zoom
        offset_y = SCREEN_HEIGHT // 2 - self.y * self.zoom

        # Add shake
        offset_x += self.shake_offset_x
        offset_y += self.shake_offset_y

        return (offset_x, offset_y)

    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convert world coordinates ke screen coordinates"""
        offset_x, offset_y = self.get_offset()

        screen_x = int((world_x * self.zoom) + offset_x)
        screen_y = int((world_y * self.zoom) + offset_y)

        return (screen_x, screen_y)

    def screen_to_world(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """Convert screen coordinates ke world coordinates"""
        offset_x, offset_y = self.get_offset()

        world_x = (screen_x - offset_x) / self.zoom
        world_y = (screen_y - offset_y) / self.zoom

        return (world_x, world_y)

    def is_visible(self, x: float, y: float, margin: float = 100) -> bool:
        """Check apakah point visible dalam camera view"""
        screen_x, screen_y = self.world_to_screen(x, y)

        return (-margin < screen_x < SCREEN_WIDTH + margin and
                -margin < screen_y < SCREEN_HEIGHT + margin)

    def get_visible_rect(self) -> Tuple[float, float, float, float]:
        """Get visible area dalam world coordinates"""
        top_left = self.screen_to_world(0, 0)
        bottom_right = self.screen_to_world(SCREEN_WIDTH, SCREEN_HEIGHT)

        return (
            top_left[0], top_left[1],
            bottom_right[0] - top_left[0],
            bottom_right[1] - top_left[1]
        )


class CameraController:
    """
    High-level camera control.
    Handles camera logic berdasarkan game events.
    """

    def __init__(self, camera: Camera):
        self.camera = camera

        # Presets
        self.presets = {
            'wide': {'zoom': 0.85, 'y': 350},
            'normal': {'zoom': 1.0, 'y': RING_CENTER_Y},
            'close': {'zoom': 1.3, 'y': RING_CENTER_Y + 50},
            'dramatic': {'zoom': 1.5, 'y': RING_CENTER_Y}
        }

    def on_hit(self, damage: float, hit_position: Tuple[float, float]):
        """Handle camera reaction to hit"""
        if damage >= 30:
            # Big hit - shake and brief zoom
            self.camera.shake(damage * 0.4)
            self.camera.dramatic_zoom(hit_position[0], hit_position[1])
        elif damage >= 15:
            self.camera.shake(damage * 0.3)
        else:
            self.camera.shake(damage * 0.2)

    def on_knockdown(self, fighter_x: float, fighter_y: float):
        """Handle camera reaction to knockdown"""
        self.camera.focus_on(fighter_x, fighter_y, duration=1.5, zoom=1.4)
        self.camera.shake(15)

    def on_ko(self, winner_x: float, winner_y: float):
        """Handle camera reaction to KO"""
        self.camera.focus_on(winner_x, winner_y, duration=3.0, zoom=1.5)

    def on_round_start(self):
        """Camera setup untuk round start"""
        self.camera.reset()
        self.apply_preset('wide')

    def on_round_end(self):
        """Camera untuk round end"""
        self.apply_preset('normal')

    def apply_preset(self, name: str):
        """Apply camera preset"""
        if name in self.presets:
            preset = self.presets[name]
            self.camera.set_zoom(preset.get('zoom', 1.0))
            if 'y' in preset:
                self.camera.target_y = preset['y']
