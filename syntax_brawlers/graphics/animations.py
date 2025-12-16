"""
Animation System
================
Keyframe animation dengan easing functions.
"""

import pygame
import math
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import sys
sys.path.insert(0, '..')

from config import AnimationState, EasingType, ANIMATION_FPS


@dataclass
class Keyframe:
    """Single keyframe dalam animation"""
    frame: int
    x_offset: float = 0
    y_offset: float = 0
    rotation: float = 0
    scale_x: float = 1.0
    scale_y: float = 1.0
    alpha: float = 1.0
    easing: EasingType = EasingType.LINEAR


@dataclass
class AnimationData:
    """Data untuk satu animation"""
    name: str
    keyframes: List[Keyframe]
    loop: bool = False
    duration_frames: int = 10
    on_complete: Optional[str] = None  # Next animation to play


class EasingFunctions:
    """Collection of easing functions"""

    @staticmethod
    def linear(t: float) -> float:
        return t

    @staticmethod
    def ease_in(t: float) -> float:
        return t * t

    @staticmethod
    def ease_out(t: float) -> float:
        return 1 - (1 - t) ** 2

    @staticmethod
    def ease_in_out(t: float) -> float:
        if t < 0.5:
            return 2 * t * t
        return 1 - (-2 * t + 2) ** 2 / 2

    @staticmethod
    def ease_out_back(t: float) -> float:
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)

    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        if t < 0.5:
            return 4 * t * t * t
        return 1 - pow(-2 * t + 2, 3) / 2

    @staticmethod
    def bounce(t: float) -> float:
        if t < 1 / 2.75:
            return 7.5625 * t * t
        elif t < 2 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t -= 2.25 / 2.75
            return 7.5625 * t * t + 0.9375
        else:
            t -= 2.625 / 2.75
            return 7.5625 * t * t + 0.984375

    @staticmethod
    def get_function(easing_type: EasingType) -> Callable[[float], float]:
        """Get easing function by type"""
        mapping = {
            EasingType.LINEAR: EasingFunctions.linear,
            EasingType.EASE_IN: EasingFunctions.ease_in,
            EasingType.EASE_OUT: EasingFunctions.ease_out,
            EasingType.EASE_IN_OUT: EasingFunctions.ease_in_out,
            EasingType.EASE_OUT_BACK: EasingFunctions.ease_out_back,
            EasingType.EASE_IN_OUT_CUBIC: EasingFunctions.ease_in_out_cubic,
            EasingType.BOUNCE: EasingFunctions.bounce,
        }
        return mapping.get(easing_type, EasingFunctions.linear)


class KeyframeAnimation:
    """
    Handles keyframe-based animation.
    """

    def __init__(self, animation_data: AnimationData):
        self.data = animation_data
        self.current_frame = 0
        self.is_playing = False
        self.is_complete = False

        # Cached interpolated values
        self._cached_values: Dict[str, float] = {}

    def play(self):
        """Start playing animation"""
        self.current_frame = 0
        self.is_playing = True
        self.is_complete = False

    def stop(self):
        """Stop animation"""
        self.is_playing = False

    def reset(self):
        """Reset to beginning"""
        self.current_frame = 0
        self.is_complete = False

    def update(self) -> bool:
        """
        Advance one frame.
        Return True if still playing.
        """
        if not self.is_playing:
            return False

        self.current_frame += 1

        if self.current_frame >= self.data.duration_frames:
            if self.data.loop:
                self.current_frame = 0
            else:
                self.is_playing = False
                self.is_complete = True
                return False

        self._interpolate()
        return True

    def _interpolate(self):
        """Interpolate values between keyframes"""
        if not self.data.keyframes:
            return

        # Find surrounding keyframes
        prev_kf = self.data.keyframes[0]
        next_kf = self.data.keyframes[-1]

        for i, kf in enumerate(self.data.keyframes):
            if kf.frame <= self.current_frame:
                prev_kf = kf
            if kf.frame >= self.current_frame:
                next_kf = kf
                break

        # Calculate interpolation factor
        if prev_kf.frame == next_kf.frame:
            t = 1.0
        else:
            t = (self.current_frame - prev_kf.frame) / (next_kf.frame - prev_kf.frame)

        # Apply easing
        easing_func = EasingFunctions.get_function(next_kf.easing)
        t = easing_func(t)

        # Interpolate all values
        self._cached_values = {
            'x_offset': self._lerp(prev_kf.x_offset, next_kf.x_offset, t),
            'y_offset': self._lerp(prev_kf.y_offset, next_kf.y_offset, t),
            'rotation': self._lerp(prev_kf.rotation, next_kf.rotation, t),
            'scale_x': self._lerp(prev_kf.scale_x, next_kf.scale_x, t),
            'scale_y': self._lerp(prev_kf.scale_y, next_kf.scale_y, t),
            'alpha': self._lerp(prev_kf.alpha, next_kf.alpha, t),
        }

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        """Linear interpolation"""
        return a + (b - a) * t

    def get_transform(self) -> Dict[str, float]:
        """Get current transform values"""
        return self._cached_values.copy()

    @property
    def progress(self) -> float:
        """Get animation progress (0.0 - 1.0)"""
        return self.current_frame / max(1, self.data.duration_frames)


class AnimationController:
    """
    Controls animations untuk satu entity.
    """

    def __init__(self):
        self.animations: Dict[str, AnimationData] = {}
        self.current_animation: Optional[KeyframeAnimation] = None
        self.current_name: str = ""
        self.animation_timer: float = 0
        self.frame_duration: float = 1.0 / ANIMATION_FPS

        # Callbacks
        self._on_complete: Optional[Callable[[str], None]] = None

        # Create default animations
        self._create_default_animations()

    def _create_default_animations(self):
        """Create default fighter animations"""
        # Idle (subtle bobbing)
        self.animations['idle'] = AnimationData(
            name='idle',
            keyframes=[
                Keyframe(0, y_offset=0),
                Keyframe(15, y_offset=-3, easing=EasingType.EASE_IN_OUT),
                Keyframe(30, y_offset=0, easing=EasingType.EASE_IN_OUT),
            ],
            loop=True,
            duration_frames=30
        )

        # Jab
        self.animations['jab'] = AnimationData(
            name='jab',
            keyframes=[
                Keyframe(0, x_offset=0),
                Keyframe(3, x_offset=30, easing=EasingType.EASE_OUT),
                Keyframe(6, x_offset=35, easing=EasingType.LINEAR),
                Keyframe(9, x_offset=0, easing=EasingType.EASE_IN),
            ],
            loop=False,
            duration_frames=9,
            on_complete='idle'
        )

        # Cross
        self.animations['cross'] = AnimationData(
            name='cross',
            keyframes=[
                Keyframe(0, x_offset=0, rotation=0),
                Keyframe(5, x_offset=45, rotation=-5, easing=EasingType.EASE_OUT),
                Keyframe(8, x_offset=50, rotation=-8, easing=EasingType.LINEAR),
                Keyframe(14, x_offset=0, rotation=0, easing=EasingType.EASE_IN_OUT),
            ],
            loop=False,
            duration_frames=14,
            on_complete='idle'
        )

        # Hook
        self.animations['hook'] = AnimationData(
            name='hook',
            keyframes=[
                Keyframe(0, x_offset=0, rotation=0),
                Keyframe(4, x_offset=-10, rotation=15, easing=EasingType.EASE_IN),
                Keyframe(7, x_offset=25, rotation=-20, easing=EasingType.EASE_OUT_BACK),
                Keyframe(10, x_offset=30, rotation=-25, easing=EasingType.LINEAR),
                Keyframe(18, x_offset=0, rotation=0, easing=EasingType.EASE_IN_OUT),
            ],
            loop=False,
            duration_frames=18,
            on_complete='idle'
        )

        # Uppercut
        self.animations['uppercut'] = AnimationData(
            name='uppercut',
            keyframes=[
                Keyframe(0, x_offset=0, y_offset=0),
                Keyframe(5, x_offset=5, y_offset=10, easing=EasingType.EASE_IN),
                Keyframe(9, x_offset=20, y_offset=-30, easing=EasingType.EASE_OUT_BACK),
                Keyframe(13, x_offset=25, y_offset=-35, easing=EasingType.LINEAR),
                Keyframe(23, x_offset=0, y_offset=0, easing=EasingType.EASE_IN_OUT),
            ],
            loop=False,
            duration_frames=23,
            on_complete='idle'
        )

        # Block
        self.animations['block'] = AnimationData(
            name='block',
            keyframes=[
                Keyframe(0, y_offset=0, scale_x=1.0),
                Keyframe(2, y_offset=-5, scale_x=0.95, easing=EasingType.EASE_OUT),
            ],
            loop=False,
            duration_frames=30
        )

        # Block hit (when taking damage while blocking)
        self.animations['block_hit'] = AnimationData(
            name='block_hit',
            keyframes=[
                Keyframe(0, x_offset=0),
                Keyframe(2, x_offset=-15, easing=EasingType.EASE_OUT),
                Keyframe(8, x_offset=0, easing=EasingType.EASE_IN_OUT),
            ],
            loop=False,
            duration_frames=8,
            on_complete='block'
        )

        # Dodge
        self.animations['dodge'] = AnimationData(
            name='dodge',
            keyframes=[
                Keyframe(0, x_offset=0, y_offset=0),
                Keyframe(3, x_offset=-20, y_offset=-10, easing=EasingType.EASE_OUT),
                Keyframe(8, x_offset=-40, y_offset=0, easing=EasingType.EASE_IN_OUT),
                Keyframe(16, x_offset=0, y_offset=0, easing=EasingType.EASE_IN),
            ],
            loop=False,
            duration_frames=16,
            on_complete='idle'
        )

        # Hit light
        self.animations['hit_light'] = AnimationData(
            name='hit_light',
            keyframes=[
                Keyframe(0, x_offset=0, rotation=0),
                Keyframe(2, x_offset=-20, rotation=-10, easing=EasingType.EASE_OUT),
                Keyframe(8, x_offset=0, rotation=0, easing=EasingType.EASE_IN_OUT),
            ],
            loop=False,
            duration_frames=8,
            on_complete='idle'
        )

        # Hit heavy
        self.animations['hit_heavy'] = AnimationData(
            name='hit_heavy',
            keyframes=[
                Keyframe(0, x_offset=0, rotation=0),
                Keyframe(3, x_offset=-40, rotation=-20, easing=EasingType.EASE_OUT),
                Keyframe(12, x_offset=0, rotation=0, easing=EasingType.BOUNCE),
            ],
            loop=False,
            duration_frames=12,
            on_complete='idle'
        )

        # Stagger
        self.animations['stagger'] = AnimationData(
            name='stagger',
            keyframes=[
                Keyframe(0, x_offset=0),
                Keyframe(5, x_offset=-30, easing=EasingType.EASE_OUT),
                Keyframe(15, x_offset=-20, easing=EasingType.EASE_IN_OUT),
                Keyframe(25, x_offset=-30, easing=EasingType.EASE_IN_OUT),
                Keyframe(35, x_offset=0, easing=EasingType.EASE_IN),
            ],
            loop=False,
            duration_frames=35,
            on_complete='idle'
        )

        # Knockdown
        self.animations['knockdown'] = AnimationData(
            name='knockdown',
            keyframes=[
                Keyframe(0, rotation=0, y_offset=0),
                Keyframe(8, rotation=-45, y_offset=20, easing=EasingType.EASE_OUT),
                Keyframe(15, rotation=-90, y_offset=60, easing=EasingType.BOUNCE),
            ],
            loop=False,
            duration_frames=60
        )

        # Get up
        self.animations['getup'] = AnimationData(
            name='getup',
            keyframes=[
                Keyframe(0, rotation=-90, y_offset=60),
                Keyframe(15, rotation=-45, y_offset=40, easing=EasingType.EASE_IN),
                Keyframe(25, rotation=-20, y_offset=20, easing=EasingType.EASE_IN_OUT),
                Keyframe(35, rotation=0, y_offset=0, easing=EasingType.EASE_OUT),
            ],
            loop=False,
            duration_frames=35,
            on_complete='idle'
        )

        # Victory
        self.animations['victory'] = AnimationData(
            name='victory',
            keyframes=[
                Keyframe(0, y_offset=0),
                Keyframe(10, y_offset=-20, easing=EasingType.EASE_OUT),
                Keyframe(20, y_offset=0, easing=EasingType.BOUNCE),
                Keyframe(30, y_offset=-15, easing=EasingType.EASE_OUT),
                Keyframe(40, y_offset=0, easing=EasingType.EASE_IN),
            ],
            loop=True,
            duration_frames=40
        )

        # Defeat
        self.animations['defeat'] = AnimationData(
            name='defeat',
            keyframes=[
                Keyframe(0, rotation=0),
                Keyframe(30, rotation=-90, y_offset=60, easing=EasingType.EASE_IN_OUT),
            ],
            loop=False,
            duration_frames=60
        )

    def play(self, name: str):
        """Play animation by name"""
        if name not in self.animations:
            name = 'idle'

        if self.current_name == name and self.current_animation:
            if self.current_animation.is_playing:
                return  # Already playing

        self.current_name = name
        self.current_animation = KeyframeAnimation(self.animations[name])
        self.current_animation.play()

    def update(self, dt: float):
        """Update current animation"""
        if self.current_animation is None:
            return

        self.animation_timer += dt
        if self.animation_timer >= self.frame_duration:
            self.animation_timer = 0
            still_playing = self.current_animation.update()

            if not still_playing and self.current_animation.is_complete:
                # Check for next animation
                data = self.animations.get(self.current_name)
                if data and data.on_complete:
                    self.play(data.on_complete)

                # Callback
                if self._on_complete:
                    self._on_complete(self.current_name)

    def get_transform(self) -> Dict[str, float]:
        """Get current transform"""
        if self.current_animation:
            return self.current_animation.get_transform()
        return {}

    def on_complete(self, callback: Callable[[str], None]):
        """Set completion callback"""
        self._on_complete = callback

    @property
    def is_playing(self) -> bool:
        return self.current_animation is not None and self.current_animation.is_playing
