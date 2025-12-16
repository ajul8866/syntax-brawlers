"""
Procedural Sprite Generator
===========================
Generate sprites secara procedural menggunakan pygame primitives.
Tidak memerlukan asset eksternal.
"""

import pygame
import math
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
import sys
sys.path.insert(0, '..')

from config import (
    AnimationState, FIGHTER_WIDTH, FIGHTER_HEIGHT,
    SKIN_TONE, SKIN_TONE_DARK, RED, BLUE, WHITE, BLACK,
    DARK_RED, DARK_BLUE, YELLOW, ORANGE
)


@dataclass
class BodyPart:
    """Definisi bagian tubuh"""
    x: float  # Relative to center
    y: float  # Relative to feet (0 = ground)
    width: float
    height: float
    color: Tuple[int, int, int]
    outline_color: Optional[Tuple[int, int, int]] = None
    shape: str = "rect"  # rect, circle, ellipse


class SpriteGenerator:
    """
    Generate sprite fighter secara procedural.
    """

    @staticmethod
    def create_fighter_surface(width: int, height: int,
                               primary_color: Tuple[int, int, int],
                               secondary_color: Tuple[int, int, int],
                               skin_color: Tuple[int, int, int] = SKIN_TONE,
                               facing_right: bool = True) -> pygame.Surface:
        """Create base fighter surface"""
        surface = pygame.Surface((width, height), pygame.SRCALPHA)

        # Body proportions
        head_size = height * 0.15
        torso_height = height * 0.3
        torso_width = width * 0.45
        leg_height = height * 0.35
        arm_length = height * 0.25

        center_x = width // 2
        ground_y = height

        # Draw legs (shorts)
        leg_y = ground_y - leg_height
        leg_width = width * 0.18

        # Left leg
        pygame.draw.rect(surface, primary_color,
                        (center_x - leg_width - 5, leg_y, leg_width, leg_height))
        # Right leg
        pygame.draw.rect(surface, primary_color,
                        (center_x + 5, leg_y, leg_width, leg_height))

        # Lower legs (skin)
        lower_leg_height = leg_height * 0.5
        pygame.draw.rect(surface, skin_color,
                        (center_x - leg_width - 5, ground_y - lower_leg_height,
                         leg_width, lower_leg_height))
        pygame.draw.rect(surface, skin_color,
                        (center_x + 5, ground_y - lower_leg_height,
                         leg_width, lower_leg_height))

        # Draw torso
        torso_y = leg_y - torso_height
        torso_rect = pygame.Rect(
            center_x - torso_width // 2,
            torso_y,
            torso_width,
            torso_height
        )
        pygame.draw.rect(surface, primary_color, torso_rect)

        # Torso detail (tank top lines)
        pygame.draw.line(surface, secondary_color,
                        (center_x - torso_width // 4, torso_y),
                        (center_x - torso_width // 4, torso_y + torso_height - 5), 2)
        pygame.draw.line(surface, secondary_color,
                        (center_x + torso_width // 4, torso_y),
                        (center_x + torso_width // 4, torso_y + torso_height - 5), 2)

        # Draw arms (skin)
        arm_width = width * 0.12
        arm_y = torso_y + 5

        # Arm direction based on facing
        arm_offset = 8 if facing_right else -8

        # Back arm (slightly behind)
        back_arm_x = center_x - torso_width // 2 - arm_width if facing_right else center_x + torso_width // 2
        pygame.draw.rect(surface, skin_color,
                        (back_arm_x, arm_y, arm_width, arm_length))

        # Front arm
        front_arm_x = center_x + torso_width // 2 if facing_right else center_x - torso_width // 2 - arm_width
        pygame.draw.rect(surface, skin_color,
                        (front_arm_x, arm_y, arm_width, arm_length))

        # Gloves
        glove_size = width * 0.15
        glove_color = RED if primary_color == RED or primary_color == DARK_RED else BLUE

        # Back glove (fist)
        back_glove_y = arm_y + arm_length - glove_size // 2
        pygame.draw.ellipse(surface, glove_color,
                           (back_arm_x - 2, back_glove_y, glove_size, glove_size))

        # Front glove
        front_glove_y = arm_y + arm_length - glove_size // 2
        pygame.draw.ellipse(surface, glove_color,
                           (front_arm_x - 2, front_glove_y, glove_size, glove_size))

        # Draw head
        head_y = torso_y - head_size
        head_rect = pygame.Rect(
            center_x - head_size // 2,
            head_y,
            head_size,
            head_size
        )
        pygame.draw.ellipse(surface, skin_color, head_rect)

        # Face features
        eye_y = head_y + head_size * 0.35
        eye_size = 3

        if facing_right:
            # Eyes
            pygame.draw.circle(surface, BLACK,
                             (int(center_x - 3), int(eye_y)), eye_size)
            pygame.draw.circle(surface, BLACK,
                             (int(center_x + 5), int(eye_y)), eye_size)
        else:
            pygame.draw.circle(surface, BLACK,
                             (int(center_x + 3), int(eye_y)), eye_size)
            pygame.draw.circle(surface, BLACK,
                             (int(center_x - 5), int(eye_y)), eye_size)

        return surface

    @staticmethod
    def create_punch_frame(base_surface: pygame.Surface,
                           primary_color: Tuple[int, int, int],
                           punch_type: str,
                           frame: int,
                           facing_right: bool) -> pygame.Surface:
        """Create punch animation frame"""
        surface = base_surface.copy()
        width, height = surface.get_size()
        center_x = width // 2

        # Punch extension based on type and frame
        max_extension = {
            'jab': 40,
            'cross': 55,
            'hook': 35,
            'uppercut': 30
        }.get(punch_type, 40)

        # Animation progress (0.0 to 1.0)
        progress = min(1.0, frame / 5.0)

        # Easing
        if frame < 3:
            # Extend
            extension = max_extension * (progress * 2)
        else:
            # Retract
            extension = max_extension * (1.0 - (progress - 0.5) * 2)

        extension = max(0, extension)

        # Draw extended arm
        arm_y = height * 0.4
        arm_width = width * 0.12
        glove_size = width * 0.18

        if punch_type == 'hook':
            # Hook curves around
            if facing_right:
                arm_x = center_x + width * 0.2 + extension * 0.7
                arm_end_y = arm_y - extension * 0.3
            else:
                arm_x = center_x - width * 0.2 - extension * 0.7 - arm_width
                arm_end_y = arm_y - extension * 0.3
        elif punch_type == 'uppercut':
            # Uppercut goes up
            if facing_right:
                arm_x = center_x + width * 0.15
                arm_end_y = arm_y - extension
            else:
                arm_x = center_x - width * 0.15 - arm_width
                arm_end_y = arm_y - extension
        else:
            # Jab/Cross straight
            if facing_right:
                arm_x = center_x + width * 0.2 + extension
            else:
                arm_x = center_x - width * 0.2 - extension - arm_width
            arm_end_y = arm_y

        # Draw extended arm
        pygame.draw.rect(surface, SKIN_TONE,
                        (arm_x, arm_end_y, extension + arm_width, arm_width))

        # Draw glove at end
        glove_color = RED if primary_color[0] > 150 else BLUE
        pygame.draw.ellipse(surface, glove_color,
                           (arm_x + extension - glove_size//4 if facing_right else arm_x - glove_size//2,
                            arm_end_y - glove_size//4,
                            glove_size, glove_size))

        return surface

    @staticmethod
    def create_block_frame(base_surface: pygame.Surface,
                           primary_color: Tuple[int, int, int]) -> pygame.Surface:
        """Create blocking pose"""
        surface = base_surface.copy()
        width, height = surface.get_size()
        center_x = width // 2

        # Draw arms in guard position
        arm_y = height * 0.35
        glove_size = width * 0.16
        glove_color = RED if primary_color[0] > 150 else BLUE

        # Left glove (covering face)
        pygame.draw.ellipse(surface, SKIN_TONE,
                           (center_x - glove_size - 5, arm_y - 10,
                            width * 0.12, height * 0.2))
        pygame.draw.ellipse(surface, glove_color,
                           (center_x - glove_size - 8, arm_y - 5,
                            glove_size, glove_size))

        # Right glove
        pygame.draw.ellipse(surface, SKIN_TONE,
                           (center_x + 5, arm_y - 10,
                            width * 0.12, height * 0.2))
        pygame.draw.ellipse(surface, glove_color,
                           (center_x + 8, arm_y - 5,
                            glove_size, glove_size))

        return surface

    @staticmethod
    def create_hit_frame(base_surface: pygame.Surface,
                         hit_type: str) -> pygame.Surface:
        """Create hit reaction frame"""
        surface = base_surface.copy()

        # Tilt/shift based on hit type
        if hit_type == 'light':
            # Slight tilt
            surface = pygame.transform.rotate(surface, -5)
        elif hit_type == 'heavy':
            # More tilt
            surface = pygame.transform.rotate(surface, -15)

        return surface


class FighterSprites:
    """
    Manage all sprites untuk satu fighter.
    """

    def __init__(self, primary_color: Tuple[int, int, int],
                 secondary_color: Tuple[int, int, int],
                 skin_color: Tuple[int, int, int] = SKIN_TONE):
        self.primary = primary_color
        self.secondary = secondary_color
        self.skin = skin_color

        # Cache surfaces
        self._surfaces: Dict[str, List[pygame.Surface]] = {}
        self._generate_all_sprites()

    def _generate_all_sprites(self):
        """Generate all sprite variations"""
        width, height = FIGHTER_WIDTH, FIGHTER_HEIGHT

        # Base idle (both directions)
        self._surfaces['idle_right'] = [
            SpriteGenerator.create_fighter_surface(
                width, height, self.primary, self.secondary,
                self.skin, facing_right=True
            )
        ]
        self._surfaces['idle_left'] = [
            SpriteGenerator.create_fighter_surface(
                width, height, self.primary, self.secondary,
                self.skin, facing_right=False
            )
        ]

        # Punch animations
        for punch in ['jab', 'cross', 'hook', 'uppercut']:
            for direction in ['right', 'left']:
                frames = []
                base = self._surfaces[f'idle_{direction}'][0]
                facing = direction == 'right'
                for frame in range(8):
                    punch_frame = SpriteGenerator.create_punch_frame(
                        base, self.primary, punch, frame, facing
                    )
                    frames.append(punch_frame)
                self._surfaces[f'{punch}_{direction}'] = frames

        # Block
        for direction in ['right', 'left']:
            base = self._surfaces[f'idle_{direction}'][0]
            block = SpriteGenerator.create_block_frame(base, self.primary)
            self._surfaces[f'block_{direction}'] = [block]

        # Hit reactions
        for direction in ['right', 'left']:
            base = self._surfaces[f'idle_{direction}'][0]
            for hit_type in ['light', 'heavy']:
                hit = SpriteGenerator.create_hit_frame(base, hit_type)
                self._surfaces[f'hit_{hit_type}_{direction}'] = [hit]

    def get_sprite(self, animation_state: AnimationState,
                   frame: int, facing_right: bool) -> pygame.Surface:
        """Get sprite untuk state dan frame tertentu"""
        direction = 'right' if facing_right else 'left'

        # Map animation state to sprite key
        state_map = {
            AnimationState.IDLE: f'idle_{direction}',
            AnimationState.JAB: f'jab_{direction}',
            AnimationState.CROSS: f'cross_{direction}',
            AnimationState.HOOK: f'hook_{direction}',
            AnimationState.UPPERCUT: f'uppercut_{direction}',
            AnimationState.BLOCK: f'block_{direction}',
            AnimationState.BLOCK_HIT: f'block_{direction}',
            AnimationState.HIT_LIGHT: f'hit_light_{direction}',
            AnimationState.HIT_HEAVY: f'hit_heavy_{direction}',
        }

        key = state_map.get(animation_state, f'idle_{direction}')
        frames = self._surfaces.get(key, self._surfaces[f'idle_{direction}'])

        # Get frame (loop if needed)
        frame_idx = frame % len(frames)
        return frames[frame_idx]


class RingSprites:
    """
    Generate ring/arena sprites.
    """

    @staticmethod
    def create_ring_surface(width: int, height: int) -> pygame.Surface:
        """Create boxing ring surface"""
        surface = pygame.Surface((width, height), pygame.SRCALPHA)

        # Ring dimensions
        ring_left = 100
        ring_right = width - 100
        ring_top = 150
        ring_bottom = 500
        ring_floor = 450

        # Floor/canvas
        canvas_color = (200, 180, 160)
        pygame.draw.rect(surface, canvas_color,
                        (ring_left, ring_top, ring_right - ring_left, ring_bottom - ring_top))

        # Ring apron
        apron_color = (100, 80, 60)
        pygame.draw.rect(surface, apron_color,
                        (ring_left - 20, ring_bottom - 30,
                         ring_right - ring_left + 40, 50))

        # Corner posts
        post_color = (60, 60, 60)
        post_size = 15
        posts = [
            (ring_left, ring_top),
            (ring_right - post_size, ring_top),
            (ring_left, ring_bottom - post_size - 30),
            (ring_right - post_size, ring_bottom - post_size - 30)
        ]
        for px, py in posts:
            pygame.draw.rect(surface, post_color,
                           (px, py, post_size, ring_bottom - ring_top))

        # Ropes (3 levels)
        rope_colors = [(200, 50, 50), (240, 240, 240), (50, 50, 200)]
        rope_heights = [ring_top + 30, ring_top + 70, ring_top + 110]

        for rope_y, rope_color in zip(rope_heights, rope_colors):
            # Top rope
            pygame.draw.line(surface, rope_color,
                           (ring_left + post_size, rope_y),
                           (ring_right - post_size, rope_y), 4)

        # Ring shadow
        shadow_color = (0, 0, 0, 50)
        shadow_surface = pygame.Surface((ring_right - ring_left, 30), pygame.SRCALPHA)
        shadow_surface.fill(shadow_color)
        surface.blit(shadow_surface, (ring_left, ring_bottom - 30))

        return surface


class BackgroundSprites:
    """
    Generate background/crowd sprites.
    """

    @staticmethod
    def create_crowd_surface(width: int, height: int) -> pygame.Surface:
        """Create crowd background"""
        surface = pygame.Surface((width, height))

        # Dark background
        surface.fill((20, 20, 30))

        # Crowd silhouettes
        import random
        random.seed(42)  # Consistent crowd

        crowd_y_start = 50
        crowd_y_end = 150

        for _ in range(200):
            x = random.randint(0, width)
            y = random.randint(crowd_y_start, crowd_y_end)

            # Head
            head_color = (40 + random.randint(0, 20),
                         40 + random.randint(0, 20),
                         50 + random.randint(0, 20))
            pygame.draw.circle(surface, head_color, (x, y), random.randint(8, 12))

            # Body
            body_color = tuple(max(0, c - 10) for c in head_color)
            pygame.draw.rect(surface, body_color,
                           (x - 8, y + 8, 16, random.randint(15, 25)))

        # Spotlights
        spotlight_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        spotlight_positions = [(width * 0.3, 0), (width * 0.7, 0)]

        for sx, sy in spotlight_positions:
            for radius in range(200, 50, -20):
                alpha = 5
                pygame.draw.circle(spotlight_surface, (255, 255, 200, alpha),
                                 (int(sx), int(sy + 100)), radius)

        surface.blit(spotlight_surface, (0, 0))

        return surface
