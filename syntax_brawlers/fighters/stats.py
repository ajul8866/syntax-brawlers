"""
Fighter Statistics System
=========================
Mengelola semua stats fighter: health, stamina, power, speed, defense.
"""

from dataclasses import dataclass, field
from typing import Optional
import sys
sys.path.insert(0, '..')

from config import (
    DEFAULT_MAX_HEALTH, DEFAULT_MAX_STAMINA,
    DEFAULT_POWER, DEFAULT_SPEED, DEFAULT_DEFENSE,
    STAMINA_REGEN_RATE, STAMINA_REGEN_IDLE_BONUS,
    EXHAUSTION_THRESHOLD, EXHAUSTION_DAMAGE_PENALTY,
    CRIT_MULTIPLIER, COUNTER_MULTIPLIER, BLOCK_REDUCTION
)


@dataclass
class FighterStats:
    """
    Stats dasar fighter.
    Modifiers adalah multiplier (1.0 = normal, 1.2 = 20% lebih tinggi)
    """
    # Modifiers
    power: float = DEFAULT_POWER       # Damage multiplier
    speed: float = DEFAULT_SPEED       # Attack/movement speed
    defense: float = DEFAULT_DEFENSE   # Damage reduction

    # Max values
    max_health: int = DEFAULT_MAX_HEALTH
    max_stamina: int = DEFAULT_MAX_STAMINA

    # Current values
    health: float = field(default=0, init=False)
    stamina: float = field(default=0, init=False)

    # State flags
    is_blocking: bool = field(default=False, init=False)
    is_exhausted: bool = field(default=False, init=False)
    is_stunned: bool = field(default=False, init=False)
    is_invulnerable: bool = field(default=False, init=False)

    # Timers
    stun_timer: float = field(default=0, init=False)
    invuln_timer: float = field(default=0, init=False)

    # Combat stats tracking
    total_damage_dealt: int = field(default=0, init=False)
    total_damage_taken: int = field(default=0, init=False)
    hits_landed: int = field(default=0, init=False)
    hits_taken: int = field(default=0, init=False)
    blocks_successful: int = field(default=0, init=False)
    dodges_successful: int = field(default=0, init=False)
    combo_count: int = field(default=0, init=False)
    max_combo: int = field(default=0, init=False)

    def __post_init__(self):
        """Initialize current values to max"""
        self.health = float(self.max_health)
        self.stamina = float(self.max_stamina)

    def reset(self):
        """Reset stats untuk round baru"""
        self.health = float(self.max_health)
        self.stamina = float(self.max_stamina)
        self.is_blocking = False
        self.is_exhausted = False
        self.is_stunned = False
        self.is_invulnerable = False
        self.stun_timer = 0
        self.invuln_timer = 0
        self.combo_count = 0

    def reset_match(self):
        """Reset semua stats untuk match baru"""
        self.reset()
        self.total_damage_dealt = 0
        self.total_damage_taken = 0
        self.hits_landed = 0
        self.hits_taken = 0
        self.blocks_successful = 0
        self.dodges_successful = 0
        self.max_combo = 0

    def update(self, dt: float, is_idle: bool = False):
        """Update stats per frame"""
        # Regen stamina
        regen_rate = STAMINA_REGEN_RATE
        if is_idle:
            regen_rate += STAMINA_REGEN_IDLE_BONUS

        self.stamina = min(self.max_stamina, self.stamina + regen_rate * dt)

        # Check exhaustion
        self.is_exhausted = self.stamina < EXHAUSTION_THRESHOLD

        # Update stun timer
        if self.stun_timer > 0:
            self.stun_timer -= dt
            if self.stun_timer <= 0:
                self.is_stunned = False

        # Update invuln timer
        if self.invuln_timer > 0:
            self.invuln_timer -= dt
            if self.invuln_timer <= 0:
                self.is_invulnerable = False

    def take_damage(self, base_damage: float, is_crit: bool = False,
                    is_counter: bool = False) -> float:
        """
        Terima damage dan return actual damage dealt.
        Memperhitungkan defense, blocking, dan modifiers.
        """
        if self.is_invulnerable:
            return 0

        damage = base_damage

        # Apply multipliers
        if is_crit:
            damage *= CRIT_MULTIPLIER
        if is_counter:
            damage *= COUNTER_MULTIPLIER

        # Defense reduction
        damage /= self.defense

        # Block reduction
        if self.is_blocking:
            damage *= (1 - BLOCK_REDUCTION)
            self.blocks_successful += 1

        # Apply damage
        actual_damage = min(damage, self.health)
        self.health -= actual_damage
        self.health = max(0, self.health)

        # Track stats
        self.total_damage_taken += int(actual_damage)
        self.hits_taken += 1

        # Reset combo when hit
        self.combo_count = 0

        return actual_damage

    def use_stamina(self, amount: float) -> bool:
        """
        Gunakan stamina. Return True jika cukup, False jika tidak.
        Jika exhausted, masih bisa attack tapi dengan penalty.
        """
        if self.stamina >= amount:
            self.stamina -= amount
            return True
        elif self.stamina > 0:
            # Use remaining stamina
            self.stamina = 0
            return True
        return False

    def apply_stun(self, duration: float):
        """Apply stun effect"""
        self.is_stunned = True
        self.stun_timer = max(self.stun_timer, duration)

    def apply_invulnerability(self, duration: float):
        """Apply invulnerability frames"""
        self.is_invulnerable = True
        self.invuln_timer = max(self.invuln_timer, duration)

    def record_hit(self, damage: int):
        """Record successful hit"""
        self.total_damage_dealt += damage
        self.hits_landed += 1
        self.combo_count += 1
        self.max_combo = max(self.max_combo, self.combo_count)

    def record_dodge(self):
        """Record successful dodge"""
        self.dodges_successful += 1

    def get_damage_modifier(self) -> float:
        """Get current damage modifier based on power and exhaustion"""
        modifier = self.power
        if self.is_exhausted:
            modifier *= EXHAUSTION_DAMAGE_PENALTY
        return modifier

    def get_speed_modifier(self) -> float:
        """Get current speed modifier"""
        modifier = self.speed
        if self.is_exhausted:
            modifier *= 0.8  # 20% slower when exhausted
        return modifier

    @property
    def health_percent(self) -> float:
        """Health sebagai persentase (0.0 - 1.0)"""
        return self.health / self.max_health

    @property
    def stamina_percent(self) -> float:
        """Stamina sebagai persentase (0.0 - 1.0)"""
        return self.stamina / self.max_stamina

    @property
    def is_alive(self) -> bool:
        """Cek apakah fighter masih hidup"""
        return self.health > 0

    @property
    def can_act(self) -> bool:
        """Cek apakah fighter bisa melakukan aksi"""
        return not self.is_stunned and self.is_alive


@dataclass
class DamageResult:
    """Hasil perhitungan damage"""
    raw_damage: float
    final_damage: float
    was_blocked: bool
    was_crit: bool
    was_counter: bool
    hit_zone: str = "body"

    @property
    def is_big_hit(self) -> bool:
        """Cek apakah ini big hit (untuk efek khusus)"""
        return self.final_damage >= 25 or self.was_crit
