"""
Particle System
===============
Efek partikel untuk hit impacts, sparks, dll.
"""

import pygame
import random
import math
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
import sys
sys.path.insert(0, '..')

from config import (
    MAX_PARTICLES, PARTICLE_GRAVITY,
    WHITE, YELLOW, ORANGE, RED, BRIGHT_RED
)


@dataclass
class Particle:
    """Single particle"""
    x: float
    y: float
    vx: float
    vy: float
    size: float
    color: Tuple[int, int, int]
    lifetime: float
    max_lifetime: float
    gravity: float = PARTICLE_GRAVITY
    fade: bool = True
    shrink: bool = True
    shape: str = "circle"  # circle, square, star

    def update(self, dt: float) -> bool:
        """
        Update particle.
        Return True if still alive.
        """
        self.lifetime -= dt
        if self.lifetime <= 0:
            return False

        # Apply velocity
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Apply gravity
        self.vy += self.gravity * dt

        # Shrink
        if self.shrink:
            life_ratio = self.lifetime / self.max_lifetime
            self.size *= 0.95 + 0.05 * life_ratio

        return True

    def get_alpha(self) -> int:
        """Get current alpha based on lifetime"""
        if not self.fade:
            return 255
        life_ratio = self.lifetime / self.max_lifetime
        return int(255 * life_ratio)


class ParticleEmitter:
    """Emitter untuk spawn particles"""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.particles: List[Particle] = []
        self.active = True

    def emit(self, count: int, config: dict):
        """Emit particles dengan config"""
        for _ in range(count):
            # Randomize values within ranges
            angle = random.uniform(
                config.get('angle_min', 0),
                config.get('angle_max', 360)
            )
            speed = random.uniform(
                config.get('speed_min', 50),
                config.get('speed_max', 150)
            )

            rad = math.radians(angle)
            vx = math.cos(rad) * speed
            vy = math.sin(rad) * speed

            size = random.uniform(
                config.get('size_min', 3),
                config.get('size_max', 8)
            )

            lifetime = random.uniform(
                config.get('lifetime_min', 0.3),
                config.get('lifetime_max', 0.8)
            )

            color = random.choice(config.get('colors', [WHITE]))

            particle = Particle(
                x=self.x + random.uniform(-5, 5),
                y=self.y + random.uniform(-5, 5),
                vx=vx,
                vy=vy,
                size=size,
                color=color,
                lifetime=lifetime,
                max_lifetime=lifetime,
                gravity=config.get('gravity', PARTICLE_GRAVITY),
                fade=config.get('fade', True),
                shrink=config.get('shrink', True),
                shape=config.get('shape', 'circle')
            )
            self.particles.append(particle)

    def update(self, dt: float):
        """Update all particles"""
        self.particles = [p for p in self.particles if p.update(dt)]


class ParticleSystem:
    """
    Manages all particles dalam game.
    """

    def __init__(self):
        self.emitters: List[ParticleEmitter] = []
        self._particle_pool: List[Particle] = []

    def update(self, dt: float):
        """Update all emitters dan particles"""
        # Update emitters
        for emitter in self.emitters:
            emitter.update(dt)

        # Remove empty emitters
        self.emitters = [e for e in self.emitters if e.particles or e.active]

        # Count total particles
        total = sum(len(e.particles) for e in self.emitters)
        if total > MAX_PARTICLES:
            self._cull_particles(total - MAX_PARTICLES)

    def _cull_particles(self, count: int):
        """Remove oldest particles"""
        removed = 0
        for emitter in self.emitters:
            while emitter.particles and removed < count:
                emitter.particles.pop(0)
                removed += 1

    def spawn_hit_effect(self, position: Tuple[float, float],
                         damage: float, is_crit: bool = False):
        """Spawn hit impact particles"""
        emitter = ParticleEmitter(position[0], position[1])

        # Scale dengan damage
        count = int(10 + damage * 0.5)
        if is_crit:
            count *= 2

        # Config based on damage
        if damage >= 30:  # Heavy hit
            config = {
                'angle_min': 160, 'angle_max': 200,
                'speed_min': 150, 'speed_max': 350,
                'size_min': 5, 'size_max': 15,
                'lifetime_min': 0.4, 'lifetime_max': 1.0,
                'colors': [BRIGHT_RED, ORANGE, YELLOW, WHITE],
                'gravity': PARTICLE_GRAVITY * 0.5,
                'shape': 'star' if is_crit else 'circle'
            }
        elif damage >= 15:  # Medium hit
            config = {
                'angle_min': 150, 'angle_max': 210,
                'speed_min': 100, 'speed_max': 250,
                'size_min': 4, 'size_max': 10,
                'lifetime_min': 0.3, 'lifetime_max': 0.7,
                'colors': [YELLOW, ORANGE, WHITE],
                'gravity': PARTICLE_GRAVITY
            }
        else:  # Light hit
            config = {
                'angle_min': 140, 'angle_max': 220,
                'speed_min': 50, 'speed_max': 150,
                'size_min': 2, 'size_max': 6,
                'lifetime_min': 0.2, 'lifetime_max': 0.5,
                'colors': [WHITE, YELLOW],
                'gravity': PARTICLE_GRAVITY * 1.5
            }

        emitter.emit(count, config)
        emitter.active = False
        self.emitters.append(emitter)

    def spawn_block_effect(self, position: Tuple[float, float]):
        """Spawn block spark effect"""
        emitter = ParticleEmitter(position[0], position[1])

        config = {
            'angle_min': 0, 'angle_max': 360,
            'speed_min': 80, 'speed_max': 200,
            'size_min': 2, 'size_max': 5,
            'lifetime_min': 0.2, 'lifetime_max': 0.4,
            'colors': [(100, 150, 255), (150, 200, 255), WHITE],
            'gravity': 0,
            'shape': 'square'
        }

        emitter.emit(15, config)
        emitter.active = False
        self.emitters.append(emitter)

    def spawn_dust(self, position: Tuple[float, float],
                   direction: int = 0):
        """Spawn dust particles (for movement)"""
        emitter = ParticleEmitter(position[0], position[1])

        angle_center = 90 if direction >= 0 else -90

        config = {
            'angle_min': angle_center - 30,
            'angle_max': angle_center + 30,
            'speed_min': 30, 'speed_max': 80,
            'size_min': 3, 'size_max': 8,
            'lifetime_min': 0.3, 'lifetime_max': 0.6,
            'colors': [(150, 140, 130), (180, 170, 160), (200, 190, 180)],
            'gravity': -50,  # Float up
            'fade': True,
            'shrink': True
        }

        emitter.emit(5, config)
        emitter.active = False
        self.emitters.append(emitter)

    def spawn_sweat(self, position: Tuple[float, float]):
        """Spawn sweat droplets"""
        emitter = ParticleEmitter(position[0], position[1])

        config = {
            'angle_min': -45, 'angle_max': 45,
            'speed_min': 100, 'speed_max': 200,
            'size_min': 2, 'size_max': 4,
            'lifetime_min': 0.5, 'lifetime_max': 1.0,
            'colors': [(200, 220, 255), (180, 200, 240)],
            'gravity': PARTICLE_GRAVITY * 2,
            'shape': 'circle'
        }

        emitter.emit(3, config)
        emitter.active = False
        self.emitters.append(emitter)

    def spawn_ko_effect(self, position: Tuple[float, float]):
        """Spawn KO explosion effect"""
        emitter = ParticleEmitter(position[0], position[1])

        config = {
            'angle_min': 0, 'angle_max': 360,
            'speed_min': 200, 'speed_max': 500,
            'size_min': 8, 'size_max': 20,
            'lifetime_min': 0.8, 'lifetime_max': 1.5,
            'colors': [BRIGHT_RED, ORANGE, YELLOW, WHITE],
            'gravity': PARTICLE_GRAVITY * 0.3,
            'shape': 'star'
        }

        emitter.emit(50, config)
        emitter.active = False
        self.emitters.append(emitter)

    def render(self, surface: pygame.Surface,
               offset_x: float = 0, offset_y: float = 0):
        """Render all particles"""
        for emitter in self.emitters:
            for particle in emitter.particles:
                self._render_particle(surface, particle, offset_x, offset_y)

    def _render_particle(self, surface: pygame.Surface, particle: Particle,
                         offset_x: float, offset_y: float):
        """Render single particle"""
        x = int(particle.x + offset_x)
        y = int(particle.y + offset_y)
        size = max(1, int(particle.size))
        alpha = particle.get_alpha()

        # Create color with alpha
        color = (*particle.color, alpha)

        if particle.shape == 'circle':
            # Draw with alpha
            temp_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(temp_surface, color, (size, size), size)
            surface.blit(temp_surface, (x - size, y - size))

        elif particle.shape == 'square':
            temp_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            temp_surface.fill(color)
            surface.blit(temp_surface, (x - size // 2, y - size // 2))

        elif particle.shape == 'star':
            self._draw_star(surface, x, y, size, color)

    def _draw_star(self, surface: pygame.Surface, x: int, y: int,
                   size: int, color: Tuple):
        """Draw star shape"""
        points = []
        for i in range(5):
            # Outer point
            angle = math.radians(i * 72 - 90)
            px = x + math.cos(angle) * size
            py = y + math.sin(angle) * size
            points.append((px, py))

            # Inner point
            angle = math.radians(i * 72 + 36 - 90)
            px = x + math.cos(angle) * (size * 0.4)
            py = y + math.sin(angle) * (size * 0.4)
            points.append((px, py))

        if len(points) >= 3:
            temp_surface = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
            adjusted_points = [(p[0] - x + size * 1.5, p[1] - y + size * 1.5) for p in points]
            pygame.draw.polygon(temp_surface, color, adjusted_points)
            surface.blit(temp_surface, (x - size * 1.5, y - size * 1.5))

    def clear(self):
        """Clear all particles"""
        self.emitters.clear()

    @property
    def particle_count(self) -> int:
        """Get total particle count"""
        return sum(len(e.particles) for e in self.emitters)
