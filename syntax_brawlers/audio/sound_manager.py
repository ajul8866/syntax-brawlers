"""
Sound Manager
=============
Mengelola semua audio dalam game.
"""

import pygame
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import sys
sys.path.insert(0, '..')

from config import (
    AUDIO_ENABLED, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
    AUDIO_BUFFER_SIZE, MASTER_VOLUME, SFX_VOLUME, MUSIC_VOLUME
)
from audio.generator import ProceduralSFX, ACTION_SOUNDS


class SoundChannel(Enum):
    """Channel untuk different sound types"""
    MASTER = "master"
    SFX = "sfx"
    MUSIC = "music"
    VOICE = "voice"
    UI = "ui"


@dataclass
class ChannelConfig:
    """Konfigurasi untuk sound channel"""
    volume: float = 1.0
    muted: bool = False
    channel_count: int = 4


class SoundManager:
    """
    Manager untuk semua audio dalam game.
    Menggunakan procedural sound generation.
    """

    def __init__(self):
        self.enabled = AUDIO_ENABLED
        self.initialized = False

        # Volume settings
        self.volumes: Dict[SoundChannel, float] = {
            SoundChannel.MASTER: MASTER_VOLUME,
            SoundChannel.SFX: SFX_VOLUME,
            SoundChannel.MUSIC: MUSIC_VOLUME,
            SoundChannel.VOICE: 0.8,
            SoundChannel.UI: 0.7,
        }

        # Mute states
        self.muted: Dict[SoundChannel, bool] = {
            channel: False for channel in SoundChannel
        }

        # Pygame channels
        self._channels: Dict[SoundChannel, List[pygame.mixer.Channel]] = {}
        self._channel_index: Dict[SoundChannel, int] = {}

        # Sound effects
        self._sfx: Optional[ProceduralSFX] = None

        # Currently playing
        self._playing: Dict[str, pygame.mixer.Channel] = {}

        if self.enabled:
            self._init_audio()

    def _init_audio(self):
        """Initialize pygame audio"""
        try:
            # Only init if not already initialized
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(
                    frequency=AUDIO_SAMPLE_RATE,
                    size=-16,
                    channels=AUDIO_CHANNELS,
                    buffer=AUDIO_BUFFER_SIZE
                )
                pygame.mixer.init()

            # Allocate channels
            total_channels = 16
            pygame.mixer.set_num_channels(total_channels)

            # Assign channels to types
            channel_allocation = {
                SoundChannel.SFX: 8,
                SoundChannel.UI: 2,
                SoundChannel.VOICE: 2,
                SoundChannel.MUSIC: 2,
            }

            idx = 0
            for channel_type, count in channel_allocation.items():
                self._channels[channel_type] = []
                self._channel_index[channel_type] = 0
                for i in range(count):
                    if idx < total_channels:
                        self._channels[channel_type].append(
                            pygame.mixer.Channel(idx)
                        )
                        idx += 1

            # Generate procedural sounds
            self._sfx = ProceduralSFX()

            self.initialized = True
            print("[Audio] Sound manager initialized")

        except Exception as e:
            print(f"[Audio] Failed to initialize: {e}")
            self.enabled = False
            self.initialized = False

    def play(
        self,
        sound_name: str,
        channel_type: SoundChannel = SoundChannel.SFX,
        volume: float = 1.0,
        loops: int = 0,
        fade_ms: int = 0
    ) -> Optional[pygame.mixer.Channel]:
        """
        Play a sound effect.

        Args:
            sound_name: Nama sound dari ProceduralSFX
            channel_type: Tipe channel
            volume: Volume multiplier (0.0 - 1.0)
            loops: Jumlah loop (-1 untuk infinite)
            fade_ms: Fade in duration

        Returns:
            Channel yang digunakan atau None
        """
        if not self.enabled or not self.initialized:
            return None

        if self._is_muted(channel_type):
            return None

        # Get sound
        sound = self._sfx.get(sound_name)
        if not sound:
            return None

        # Get channel
        channel = self._get_channel(channel_type)
        if not channel:
            return None

        # Calculate final volume
        final_volume = self._calculate_volume(channel_type, volume)
        sound.set_volume(final_volume)

        # Play
        if fade_ms > 0:
            channel.play(sound, loops=loops, fade_ms=fade_ms)
        else:
            channel.play(sound, loops=loops)

        # Track playing
        self._playing[sound_name] = channel

        return channel

    def play_action(
        self,
        action_name: str,
        volume: float = 1.0
    ) -> Optional[pygame.mixer.Channel]:
        """
        Play sound untuk combat action.

        Args:
            action_name: Nama action (jab, cross, etc.)
            volume: Volume multiplier

        Returns:
            Channel atau None
        """
        sound_name = ACTION_SOUNDS.get(action_name.lower())
        if sound_name:
            return self.play(sound_name, SoundChannel.SFX, volume)
        return None

    def play_hit(self, damage: float) -> Optional[pygame.mixer.Channel]:
        """Play hit sound berdasarkan damage"""
        if damage >= 20:
            return self.play('impact_heavy', SoundChannel.SFX, 1.0)
        elif damage >= 10:
            return self.play('punch_heavy', SoundChannel.SFX, 0.8)
        else:
            return self.play('impact_light', SoundChannel.SFX, 0.6)

    def play_block(self) -> Optional[pygame.mixer.Channel]:
        """Play block sound"""
        return self.play('block', SoundChannel.SFX, 0.8)

    def play_ko(self) -> Optional[pygame.mixer.Channel]:
        """Play KO sound"""
        return self.play('ko', SoundChannel.SFX, 1.0)

    def play_ui(self, sound_name: str) -> Optional[pygame.mixer.Channel]:
        """Play UI sound"""
        return self.play(sound_name, SoundChannel.UI, 1.0)

    def play_announcer(self, announcement: str) -> Optional[pygame.mixer.Channel]:
        """Play announcer sound"""
        sound_map = {
            'round': 'round_start',
            'fight': 'fight',
            'ko': 'ko',
        }
        sound_name = sound_map.get(announcement.lower())
        if sound_name:
            return self.play(sound_name, SoundChannel.VOICE, 1.0)
        return None

    def stop(self, sound_name: str, fade_ms: int = 0):
        """Stop specific sound"""
        if sound_name in self._playing:
            channel = self._playing[sound_name]
            if fade_ms > 0:
                channel.fadeout(fade_ms)
            else:
                channel.stop()
            del self._playing[sound_name]

    def stop_all(self, channel_type: Optional[SoundChannel] = None, fade_ms: int = 0):
        """Stop all sounds atau sounds di channel tertentu"""
        if channel_type:
            channels = self._channels.get(channel_type, [])
            for channel in channels:
                if fade_ms > 0:
                    channel.fadeout(fade_ms)
                else:
                    channel.stop()
        else:
            if fade_ms > 0:
                pygame.mixer.fadeout(fade_ms)
            else:
                pygame.mixer.stop()

        self._playing.clear()

    def pause(self, channel_type: Optional[SoundChannel] = None):
        """Pause sounds"""
        if channel_type:
            channels = self._channels.get(channel_type, [])
            for channel in channels:
                channel.pause()
        else:
            pygame.mixer.pause()

    def unpause(self, channel_type: Optional[SoundChannel] = None):
        """Unpause sounds"""
        if channel_type:
            channels = self._channels.get(channel_type, [])
            for channel in channels:
                channel.unpause()
        else:
            pygame.mixer.unpause()

    def set_volume(self, channel_type: SoundChannel, volume: float):
        """Set volume untuk channel type"""
        self.volumes[channel_type] = max(0.0, min(1.0, volume))

    def get_volume(self, channel_type: SoundChannel) -> float:
        """Get volume untuk channel type"""
        return self.volumes.get(channel_type, 1.0)

    def set_master_volume(self, volume: float):
        """Set master volume"""
        self.set_volume(SoundChannel.MASTER, volume)

    def mute(self, channel_type: SoundChannel):
        """Mute channel type"""
        self.muted[channel_type] = True

    def unmute(self, channel_type: SoundChannel):
        """Unmute channel type"""
        self.muted[channel_type] = False

    def toggle_mute(self, channel_type: SoundChannel) -> bool:
        """Toggle mute state, return new state"""
        self.muted[channel_type] = not self.muted[channel_type]
        return self.muted[channel_type]

    def mute_all(self):
        """Mute semua channels"""
        self.muted[SoundChannel.MASTER] = True

    def unmute_all(self):
        """Unmute semua channels"""
        self.muted[SoundChannel.MASTER] = False

    def _get_channel(self, channel_type: SoundChannel) -> Optional[pygame.mixer.Channel]:
        """Get next available channel"""
        channels = self._channels.get(channel_type, [])
        if not channels:
            return None

        # Round-robin selection
        idx = self._channel_index.get(channel_type, 0)
        channel = channels[idx % len(channels)]
        self._channel_index[channel_type] = idx + 1

        return channel

    def _calculate_volume(self, channel_type: SoundChannel, volume: float) -> float:
        """Calculate final volume dengan master"""
        master = self.volumes.get(SoundChannel.MASTER, 1.0)
        channel_vol = self.volumes.get(channel_type, 1.0)
        return master * channel_vol * volume

    def _is_muted(self, channel_type: SoundChannel) -> bool:
        """Check if channel is muted"""
        if self.muted.get(SoundChannel.MASTER, False):
            return True
        return self.muted.get(channel_type, False)

    def is_playing(self, sound_name: str) -> bool:
        """Check if sound sedang playing"""
        if sound_name in self._playing:
            return self._playing[sound_name].get_busy()
        return False

    def get_busy_channels(self, channel_type: SoundChannel) -> int:
        """Get jumlah channel yang busy"""
        channels = self._channels.get(channel_type, [])
        return sum(1 for ch in channels if ch.get_busy())

    def cleanup(self):
        """Cleanup audio resources"""
        if self.initialized:
            self.stop_all()
            pygame.mixer.quit()
            self.initialized = False
            print("[Audio] Sound manager cleaned up")


# Global sound manager instance
_sound_manager: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    """Get atau create global sound manager"""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager


def play_sfx(sound_name: str, volume: float = 1.0) -> Optional[pygame.mixer.Channel]:
    """Shortcut untuk play SFX"""
    return get_sound_manager().play(sound_name, SoundChannel.SFX, volume)


def play_action_sound(action_name: str) -> Optional[pygame.mixer.Channel]:
    """Shortcut untuk play action sound"""
    return get_sound_manager().play_action(action_name)


def play_ui_sound(sound_name: str) -> Optional[pygame.mixer.Channel]:
    """Shortcut untuk play UI sound"""
    return get_sound_manager().play_ui(sound_name)
