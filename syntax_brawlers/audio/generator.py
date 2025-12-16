"""
Sound Generator
===============
Procedural sound generation untuk fighting game.
Tidak perlu file audio eksternal.
"""

import pygame
import numpy as np
import math
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import sys
sys.path.insert(0, '..')

from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS


class WaveType(Enum):
    """Jenis gelombang untuk sound synthesis"""
    SINE = "sine"
    SQUARE = "square"
    SAWTOOTH = "sawtooth"
    TRIANGLE = "triangle"
    NOISE = "noise"


@dataclass
class SoundParams:
    """Parameter untuk sound generation"""
    frequency: float = 440.0
    duration: float = 0.2
    volume: float = 0.5
    wave_type: WaveType = WaveType.SINE

    # Envelope (ADSR)
    attack: float = 0.01
    decay: float = 0.05
    sustain: float = 0.7
    release: float = 0.1

    # Effects
    pitch_bend: float = 0.0  # Semitones per second
    vibrato_freq: float = 0.0
    vibrato_depth: float = 0.0
    noise_mix: float = 0.0


class SoundGenerator:
    """
    Generator untuk procedural sound effects.
    """

    def __init__(self, sample_rate: int = AUDIO_SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._cache = {}

    def generate(self, params: SoundParams) -> pygame.mixer.Sound:
        """Generate sound dari parameters"""
        # Check cache
        cache_key = self._make_cache_key(params)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Generate samples
        num_samples = int(params.duration * self.sample_rate)
        t = np.linspace(0, params.duration, num_samples, dtype=np.float32)

        # Frequency with pitch bend
        freq = params.frequency
        if params.pitch_bend != 0:
            # Pitch bend dalam semitones
            freq = freq * np.power(2, params.pitch_bend * t / 12)

        # Vibrato
        if params.vibrato_freq > 0 and params.vibrato_depth > 0:
            vibrato = params.vibrato_depth * np.sin(2 * np.pi * params.vibrato_freq * t)
            freq = freq * np.power(2, vibrato / 12)

        # Generate waveform
        if isinstance(freq, np.ndarray):
            phase = np.cumsum(freq / self.sample_rate) * 2 * np.pi
        else:
            phase = 2 * np.pi * freq * t

        samples = self._generate_wave(phase, params.wave_type)

        # Add noise
        if params.noise_mix > 0:
            noise = np.random.uniform(-1, 1, num_samples).astype(np.float32)
            samples = samples * (1 - params.noise_mix) + noise * params.noise_mix

        # Apply envelope
        envelope = self._generate_envelope(params, num_samples)
        samples = samples * envelope

        # Apply volume
        samples = samples * params.volume

        # Clip
        samples = np.clip(samples, -1, 1)

        # Convert to 16-bit
        samples_int = (samples * 32767).astype(np.int16)

        # Create stereo
        if AUDIO_CHANNELS == 2:
            stereo = np.column_stack((samples_int, samples_int))
            sound = pygame.sndarray.make_sound(stereo)
        else:
            sound = pygame.sndarray.make_sound(samples_int)

        # Cache
        self._cache[cache_key] = sound
        return sound

    def _generate_wave(self, phase: np.ndarray, wave_type: WaveType) -> np.ndarray:
        """Generate waveform"""
        if wave_type == WaveType.SINE:
            return np.sin(phase)

        elif wave_type == WaveType.SQUARE:
            return np.sign(np.sin(phase))

        elif wave_type == WaveType.SAWTOOTH:
            return 2 * (phase / (2 * np.pi) % 1) - 1

        elif wave_type == WaveType.TRIANGLE:
            return 2 * np.abs(2 * (phase / (2 * np.pi) % 1) - 1) - 1

        elif wave_type == WaveType.NOISE:
            return np.random.uniform(-1, 1, len(phase)).astype(np.float32)

        return np.zeros_like(phase)

    def _generate_envelope(self, params: SoundParams, num_samples: int) -> np.ndarray:
        """Generate ADSR envelope"""
        envelope = np.zeros(num_samples, dtype=np.float32)

        attack_samples = int(params.attack * self.sample_rate)
        decay_samples = int(params.decay * self.sample_rate)
        release_samples = int(params.release * self.sample_rate)
        sustain_samples = num_samples - attack_samples - decay_samples - release_samples

        if sustain_samples < 0:
            # Adjust jika duration terlalu pendek
            total = attack_samples + decay_samples + release_samples
            ratio = num_samples / total if total > 0 else 1
            attack_samples = int(attack_samples * ratio)
            decay_samples = int(decay_samples * ratio)
            release_samples = num_samples - attack_samples - decay_samples
            sustain_samples = 0

        idx = 0

        # Attack
        if attack_samples > 0:
            envelope[idx:idx+attack_samples] = np.linspace(0, 1, attack_samples)
            idx += attack_samples

        # Decay
        if decay_samples > 0:
            envelope[idx:idx+decay_samples] = np.linspace(1, params.sustain, decay_samples)
            idx += decay_samples

        # Sustain
        if sustain_samples > 0:
            envelope[idx:idx+sustain_samples] = params.sustain
            idx += sustain_samples

        # Release
        if release_samples > 0:
            start_val = envelope[idx-1] if idx > 0 else params.sustain
            envelope[idx:] = np.linspace(start_val, 0, len(envelope) - idx)

        return envelope

    def _make_cache_key(self, params: SoundParams) -> str:
        """Create cache key dari params"""
        return f"{params.frequency}_{params.duration}_{params.volume}_{params.wave_type.value}"

    def clear_cache(self):
        """Clear sound cache"""
        self._cache.clear()


class ProceduralSFX:
    """
    Pre-defined sound effects untuk fighting game.
    """

    def __init__(self):
        self.generator = SoundGenerator()
        self._sounds = {}
        self._generate_all()

    def _generate_all(self):
        """Generate semua sound effects"""
        # Punch sounds
        self._sounds['punch_light'] = self._generate_punch_light()
        self._sounds['punch_medium'] = self._generate_punch_medium()
        self._sounds['punch_heavy'] = self._generate_punch_heavy()

        # Kick sounds
        self._sounds['kick_light'] = self._generate_kick_light()
        self._sounds['kick_medium'] = self._generate_kick_medium()
        self._sounds['kick_heavy'] = self._generate_kick_heavy()

        # Special sounds
        self._sounds['special'] = self._generate_special()
        self._sounds['super'] = self._generate_super()

        # Block and hit
        self._sounds['block'] = self._generate_block()
        self._sounds['hit_blocked'] = self._generate_hit_blocked()

        # Movement
        self._sounds['whoosh'] = self._generate_whoosh()
        self._sounds['dash'] = self._generate_dash()
        self._sounds['jump'] = self._generate_jump()
        self._sounds['land'] = self._generate_land()

        # Impact
        self._sounds['impact_light'] = self._generate_impact_light()
        self._sounds['impact_heavy'] = self._generate_impact_heavy()
        self._sounds['ko'] = self._generate_ko()

        # UI sounds
        self._sounds['menu_select'] = self._generate_menu_select()
        self._sounds['menu_move'] = self._generate_menu_move()
        self._sounds['round_start'] = self._generate_round_start()
        self._sounds['fight'] = self._generate_fight()

    def get(self, name: str) -> Optional[pygame.mixer.Sound]:
        """Get sound by name"""
        return self._sounds.get(name)

    def _generate_punch_light(self) -> pygame.mixer.Sound:
        """Light punch - quick, snappy"""
        params = SoundParams(
            frequency=200,
            duration=0.08,
            volume=0.4,
            wave_type=WaveType.NOISE,
            attack=0.001,
            decay=0.02,
            sustain=0.3,
            release=0.05,
            pitch_bend=-50
        )
        return self.generator.generate(params)

    def _generate_punch_medium(self) -> pygame.mixer.Sound:
        """Medium punch - more impact"""
        params = SoundParams(
            frequency=150,
            duration=0.12,
            volume=0.5,
            wave_type=WaveType.NOISE,
            attack=0.001,
            decay=0.03,
            sustain=0.4,
            release=0.08,
            pitch_bend=-40
        )
        return self.generator.generate(params)

    def _generate_punch_heavy(self) -> pygame.mixer.Sound:
        """Heavy punch - deep, powerful"""
        params = SoundParams(
            frequency=100,
            duration=0.18,
            volume=0.6,
            wave_type=WaveType.NOISE,
            attack=0.001,
            decay=0.04,
            sustain=0.5,
            release=0.12,
            pitch_bend=-30,
            noise_mix=0.3
        )
        return self.generator.generate(params)

    def _generate_kick_light(self) -> pygame.mixer.Sound:
        """Light kick - sharper than punch"""
        params = SoundParams(
            frequency=250,
            duration=0.1,
            volume=0.4,
            wave_type=WaveType.NOISE,
            attack=0.001,
            decay=0.03,
            sustain=0.3,
            release=0.06,
            pitch_bend=-60
        )
        return self.generator.generate(params)

    def _generate_kick_medium(self) -> pygame.mixer.Sound:
        """Medium kick"""
        params = SoundParams(
            frequency=180,
            duration=0.14,
            volume=0.5,
            wave_type=WaveType.NOISE,
            attack=0.001,
            decay=0.04,
            sustain=0.4,
            release=0.09,
            pitch_bend=-50
        )
        return self.generator.generate(params)

    def _generate_kick_heavy(self) -> pygame.mixer.Sound:
        """Heavy kick - thunderous"""
        params = SoundParams(
            frequency=120,
            duration=0.2,
            volume=0.65,
            wave_type=WaveType.NOISE,
            attack=0.001,
            decay=0.05,
            sustain=0.5,
            release=0.13,
            pitch_bend=-40,
            noise_mix=0.4
        )
        return self.generator.generate(params)

    def _generate_special(self) -> pygame.mixer.Sound:
        """Special move - dramatic"""
        params = SoundParams(
            frequency=300,
            duration=0.3,
            volume=0.6,
            wave_type=WaveType.SAWTOOTH,
            attack=0.01,
            decay=0.05,
            sustain=0.6,
            release=0.2,
            pitch_bend=20,
            vibrato_freq=10,
            vibrato_depth=2,
            noise_mix=0.2
        )
        return self.generator.generate(params)

    def _generate_super(self) -> pygame.mixer.Sound:
        """Super move - epic"""
        params = SoundParams(
            frequency=200,
            duration=0.5,
            volume=0.7,
            wave_type=WaveType.SAWTOOTH,
            attack=0.02,
            decay=0.08,
            sustain=0.7,
            release=0.3,
            pitch_bend=30,
            vibrato_freq=15,
            vibrato_depth=3,
            noise_mix=0.25
        )
        return self.generator.generate(params)

    def _generate_block(self) -> pygame.mixer.Sound:
        """Block - metallic clang"""
        params = SoundParams(
            frequency=400,
            duration=0.1,
            volume=0.45,
            wave_type=WaveType.SQUARE,
            attack=0.001,
            decay=0.02,
            sustain=0.2,
            release=0.07,
            pitch_bend=-80
        )
        return self.generator.generate(params)

    def _generate_hit_blocked(self) -> pygame.mixer.Sound:
        """Hit blocked - dull thud"""
        params = SoundParams(
            frequency=150,
            duration=0.08,
            volume=0.35,
            wave_type=WaveType.NOISE,
            attack=0.001,
            decay=0.02,
            sustain=0.2,
            release=0.05,
            pitch_bend=-30
        )
        return self.generator.generate(params)

    def _generate_whoosh(self) -> pygame.mixer.Sound:
        """Whoosh - movement"""
        params = SoundParams(
            frequency=800,
            duration=0.15,
            volume=0.25,
            wave_type=WaveType.NOISE,
            attack=0.01,
            decay=0.03,
            sustain=0.3,
            release=0.11,
            pitch_bend=-100
        )
        return self.generator.generate(params)

    def _generate_dash(self) -> pygame.mixer.Sound:
        """Dash - quick movement"""
        params = SoundParams(
            frequency=600,
            duration=0.12,
            volume=0.3,
            wave_type=WaveType.NOISE,
            attack=0.005,
            decay=0.02,
            sustain=0.25,
            release=0.09,
            pitch_bend=-80
        )
        return self.generator.generate(params)

    def _generate_jump(self) -> pygame.mixer.Sound:
        """Jump - upward whoosh"""
        params = SoundParams(
            frequency=300,
            duration=0.15,
            volume=0.3,
            wave_type=WaveType.NOISE,
            attack=0.01,
            decay=0.03,
            sustain=0.3,
            release=0.11,
            pitch_bend=50
        )
        return self.generator.generate(params)

    def _generate_land(self) -> pygame.mixer.Sound:
        """Land - thump"""
        params = SoundParams(
            frequency=80,
            duration=0.1,
            volume=0.35,
            wave_type=WaveType.NOISE,
            attack=0.001,
            decay=0.02,
            sustain=0.3,
            release=0.07,
            pitch_bend=-20
        )
        return self.generator.generate(params)

    def _generate_impact_light(self) -> pygame.mixer.Sound:
        """Light impact"""
        params = SoundParams(
            frequency=180,
            duration=0.1,
            volume=0.4,
            wave_type=WaveType.NOISE,
            attack=0.001,
            decay=0.02,
            sustain=0.3,
            release=0.07,
            pitch_bend=-40
        )
        return self.generator.generate(params)

    def _generate_impact_heavy(self) -> pygame.mixer.Sound:
        """Heavy impact - screen shake worthy"""
        params = SoundParams(
            frequency=80,
            duration=0.25,
            volume=0.7,
            wave_type=WaveType.NOISE,
            attack=0.001,
            decay=0.05,
            sustain=0.5,
            release=0.19,
            pitch_bend=-20,
            noise_mix=0.5
        )
        return self.generator.generate(params)

    def _generate_ko(self) -> pygame.mixer.Sound:
        """KO - dramatic ending"""
        params = SoundParams(
            frequency=150,
            duration=0.6,
            volume=0.8,
            wave_type=WaveType.SAWTOOTH,
            attack=0.01,
            decay=0.1,
            sustain=0.6,
            release=0.4,
            pitch_bend=-30,
            vibrato_freq=5,
            vibrato_depth=2,
            noise_mix=0.3
        )
        return self.generator.generate(params)

    def _generate_menu_select(self) -> pygame.mixer.Sound:
        """Menu select - confirmation"""
        params = SoundParams(
            frequency=600,
            duration=0.1,
            volume=0.4,
            wave_type=WaveType.SINE,
            attack=0.005,
            decay=0.02,
            sustain=0.5,
            release=0.07,
            pitch_bend=20
        )
        return self.generator.generate(params)

    def _generate_menu_move(self) -> pygame.mixer.Sound:
        """Menu move - navigation"""
        params = SoundParams(
            frequency=400,
            duration=0.05,
            volume=0.3,
            wave_type=WaveType.SINE,
            attack=0.005,
            decay=0.01,
            sustain=0.4,
            release=0.035
        )
        return self.generator.generate(params)

    def _generate_round_start(self) -> pygame.mixer.Sound:
        """Round start announcement"""
        params = SoundParams(
            frequency=250,
            duration=0.4,
            volume=0.6,
            wave_type=WaveType.SAWTOOTH,
            attack=0.02,
            decay=0.05,
            sustain=0.6,
            release=0.3,
            pitch_bend=15,
            vibrato_freq=8,
            vibrato_depth=1
        )
        return self.generator.generate(params)

    def _generate_fight(self) -> pygame.mixer.Sound:
        """FIGHT! announcement"""
        params = SoundParams(
            frequency=350,
            duration=0.3,
            volume=0.7,
            wave_type=WaveType.SAWTOOTH,
            attack=0.01,
            decay=0.04,
            sustain=0.7,
            release=0.2,
            pitch_bend=25,
            vibrato_freq=12,
            vibrato_depth=1.5,
            noise_mix=0.1
        )
        return self.generator.generate(params)


# Mapping action ke sound
ACTION_SOUNDS = {
    'jab': 'punch_light',
    'cross': 'punch_medium',
    'hook': 'punch_medium',
    'uppercut': 'punch_heavy',
    'front_kick': 'kick_light',
    'roundhouse': 'kick_medium',
    'low_kick': 'kick_light',
    'sweep': 'kick_heavy',
    'grab': 'impact_light',
    'throw': 'impact_heavy',
    'special': 'special',
    'super': 'super',
    'block': 'block',
    'dodge': 'whoosh',
    'advance': 'whoosh',
    'retreat': 'whoosh',
}
