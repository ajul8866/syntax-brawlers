"""
Fighter Class
=============
Main fighter entity yang mengintegrasikan semua sistem.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum, auto
import sys
sys.path.insert(0, '..')

from config import (
    ActionType, AnimationState, ACTION_DATA, HitZone,
    FIGHTER1_START_X, FIGHTER2_START_X, FIGHTER_START_Y,
    FIGHTER_WIDTH, FIGHTER_HEIGHT,
    KNOCKBACK_FORCE, HIT_STUN_LIGHT, HIT_STUN_HEAVY,
    BLOCK_STUN, STAGGER_DURATION
)
from fighters.stats import FighterStats, DamageResult
from fighters.hitbox import (
    Hitbox, HurtboxManager, AttackHitboxes, check_collision
)
from fighters.movement import MovementController, MovementState


class ActionPhase(Enum):
    """Phase dalam satu aksi"""
    NONE = auto()
    STARTUP = auto()    # Sebelum hitbox aktif
    ACTIVE = auto()     # Hitbox aktif
    RECOVERY = auto()   # Setelah hitbox tidak aktif


@dataclass
class ActiveAction:
    """Data untuk aksi yang sedang berlangsung"""
    action_type: ActionType
    phase: ActionPhase = ActionPhase.NONE
    frame: int = 0
    total_frames: int = 0
    hitbox: Optional[Hitbox] = None
    has_hit: bool = False  # Sudah hit musuh?

    # Phase frame counts
    startup_frames: int = 0
    active_frames: int = 0
    recovery_frames: int = 0


class Fighter:
    """
    Main fighter class.
    Mengintegrasikan stats, movement, hitbox, dan animation.
    """

    def __init__(self, name: str, stats: FighterStats,
                 player_id: int, is_player_one: bool = True):
        self.name = name
        self.player_id = player_id
        self.is_player_one = is_player_one

        # Core systems
        self.stats = stats
        self.movement = MovementController()
        self.hurtbox_manager = HurtboxManager()

        # Position
        start_x = FIGHTER1_START_X if is_player_one else FIGHTER2_START_X
        self.movement.set_position(start_x, FIGHTER_START_Y)
        self.movement.facing_right = not is_player_one  # Face opponent

        # Action state
        self.current_action: Optional[ActiveAction] = None
        self.action_queue: List[ActionType] = []  # Untuk combo chaining
        self.last_action: Optional[ActionType] = None
        self.combo_window: float = 0  # Waktu tersisa untuk chain combo

        # Animation
        self.animation_state = AnimationState.IDLE
        self.animation_frame = 0
        self.animation_timer = 0.0

        # Visual state
        self.flash_timer = 0.0  # Flash putih saat hit
        self.shake_offset = (0, 0)  # Shake saat impact

        # Callbacks
        self._on_hit_callback: Optional[Callable] = None
        self._on_block_callback: Optional[Callable] = None
        self._on_dodge_callback: Optional[Callable] = None

    # Position properties untuk kemudahan akses
    @property
    def x(self) -> float:
        return self.movement.x

    @x.setter
    def x(self, value: float):
        self.movement.x = value

    @property
    def y(self) -> float:
        return self.movement.y

    @y.setter
    def y(self, value: float):
        self.movement.y = value

    def update(self, dt: float, opponent: Optional['Fighter'] = None):
        """Update fighter per frame"""
        # Update movement
        opponent_x = opponent.movement.x if opponent else None
        self.movement.update(dt, opponent_x)

        # Update stats
        is_idle = self.current_action is None
        self.stats.update(dt, is_idle)

        # Update current action
        self._update_action(dt)

        # Update animation
        self._update_animation(dt)

        # Update visual effects
        if self.flash_timer > 0:
            self.flash_timer -= dt

        # Update combo window
        if self.combo_window > 0:
            self.combo_window -= dt
            if self.combo_window <= 0:
                self.stats.combo_count = 0

    def _update_action(self, dt: float):
        """Update aksi yang sedang berlangsung"""
        if self.current_action is None:
            return

        action = self.current_action
        action_data = ACTION_DATA.get(action.action_type)

        if action_data is None:
            self.current_action = None
            return

        # Calculate frame duration (60 FPS animation)
        frame_duration = 1.0 / 60.0 / self.stats.get_speed_modifier()

        # Advance frame
        action.frame += 1

        # Determine current phase
        if action.frame <= action.startup_frames:
            action.phase = ActionPhase.STARTUP
            if action.hitbox:
                action.hitbox.is_active = False

        elif action.frame <= action.startup_frames + action.active_frames:
            action.phase = ActionPhase.ACTIVE
            if action.hitbox:
                action.hitbox.is_active = True

        elif action.frame <= action.total_frames:
            action.phase = ActionPhase.RECOVERY
            if action.hitbox:
                action.hitbox.is_active = False

        else:
            # Action complete
            self._complete_action()

    def _complete_action(self):
        """Selesaikan aksi saat ini"""
        if self.current_action:
            self.last_action = self.current_action.action_type
            self.combo_window = 0.3  # 300ms untuk chain

        self.current_action = None
        self.animation_state = AnimationState.IDLE
        self.hurtbox_manager.set_state('idle')

        # Process action queue
        if self.action_queue:
            next_action = self.action_queue.pop(0)
            self.execute_action(next_action)

    def execute_action(self, action_type: ActionType) -> bool:
        """
        Execute combat action.
        Return True jika berhasil memulai aksi.
        """
        # Check if can act
        if not self.stats.can_act:
            return False

        # If already in action, try to queue
        if self.current_action is not None:
            # Can chain during recovery
            if (self.current_action.phase == ActionPhase.RECOVERY and
                len(self.action_queue) < 2):
                action_data = ACTION_DATA.get(action_type)
                if action_data and action_data.can_chain > 1:
                    self.action_queue.append(action_type)
                    return True
            return False

        # Get action data
        action_data = ACTION_DATA.get(action_type)
        if action_data is None:
            return False

        # Check stamina
        if not self.stats.use_stamina(action_data.stamina_cost):
            return False

        # Create active action
        self.current_action = ActiveAction(
            action_type=action_type,
            phase=ActionPhase.STARTUP,
            frame=0,
            startup_frames=action_data.startup_frames,
            active_frames=action_data.active_frames,
            recovery_frames=action_data.recovery_frames,
            total_frames=(action_data.startup_frames +
                         action_data.active_frames +
                         action_data.recovery_frames)
        )

        # Create hitbox if attack
        if action_type in (ActionType.JAB, ActionType.CROSS,
                          ActionType.HOOK, ActionType.UPPERCUT):
            self.current_action.hitbox = self._create_hitbox(action_type)
            self.hurtbox_manager.set_state('attacking')

            # Advance during attack
            self.movement.advance(action_data.move_distance)

        elif action_type == ActionType.BLOCK:
            self.stats.is_blocking = True
            self.hurtbox_manager.set_state('blocking')

        elif action_type == ActionType.DODGE:
            self.hurtbox_manager.set_state('crouching')
            self.movement.retreat(abs(action_data.move_distance))

        # Set animation
        self._set_animation_for_action(action_type)

        return True

    def _create_hitbox(self, action_type: ActionType) -> Hitbox:
        """Create hitbox untuk tipe serangan"""
        facing = self.movement.facing_right

        if action_type == ActionType.JAB:
            return AttackHitboxes.create_jab(facing)
        elif action_type == ActionType.CROSS:
            return AttackHitboxes.create_cross(facing)
        elif action_type == ActionType.HOOK:
            return AttackHitboxes.create_hook(facing)
        elif action_type == ActionType.UPPERCUT:
            return AttackHitboxes.create_uppercut(facing)

        return Hitbox(0, 0, 0, 0)

    def _set_animation_for_action(self, action_type: ActionType):
        """Set animation state berdasarkan action"""
        anim_map = {
            ActionType.JAB: AnimationState.JAB,
            ActionType.CROSS: AnimationState.CROSS,
            ActionType.HOOK: AnimationState.HOOK,
            ActionType.UPPERCUT: AnimationState.UPPERCUT,
            ActionType.BLOCK: AnimationState.BLOCK,
            ActionType.DODGE: AnimationState.DODGE,
        }
        self.animation_state = anim_map.get(action_type, AnimationState.IDLE)
        self.animation_frame = 0
        self.animation_timer = 0

    def _update_animation(self, dt: float):
        """Update animation frame"""
        self.animation_timer += dt

        # 30 FPS animation
        if self.animation_timer >= 1/30:
            self.animation_timer = 0
            self.animation_frame += 1

    def receive_hit(self, damage: float, hit_zone: HitZone,
                    attacker_x: float, is_crit: bool = False,
                    is_counter: bool = False) -> DamageResult:
        """
        Terima serangan dari lawan.
        Return DamageResult dengan info detail.
        """
        # Apply zone multiplier
        zone_mult = {
            HitZone.HEAD: 1.5,
            HitZone.BODY: 1.0,
            HitZone.LEGS: 0.8
        }.get(hit_zone, 1.0)

        raw_damage = damage * zone_mult

        # Take damage through stats
        final_damage = self.stats.take_damage(raw_damage, is_crit, is_counter)

        # Create result
        result = DamageResult(
            raw_damage=raw_damage,
            final_damage=final_damage,
            was_blocked=self.stats.is_blocking,
            was_crit=is_crit,
            was_counter=is_counter,
            hit_zone=hit_zone.value
        )

        # Apply effects based on damage
        if final_damage > 0:
            # Flash effect
            self.flash_timer = 0.1

            # Knockback
            from_right = attacker_x > self.movement.x
            knockback = KNOCKBACK_FORCE
            if is_crit:
                knockback *= 1.5
            if result.was_blocked:
                knockback *= 0.3
            self.movement.apply_knockback(knockback, from_right)

            # Stun
            if self.stats.is_blocking:
                self.stats.apply_stun(BLOCK_STUN)
                self.animation_state = AnimationState.BLOCK_HIT
            elif is_crit or final_damage >= 30:
                self.stats.apply_stun(HIT_STUN_HEAVY)
                self.animation_state = AnimationState.HIT_HEAVY
            else:
                self.stats.apply_stun(HIT_STUN_LIGHT)
                self.animation_state = AnimationState.HIT_LIGHT

            # Cancel current action
            if self.current_action and not self.stats.is_blocking:
                self.current_action = None

            # Callback
            if self._on_hit_callback:
                self._on_hit_callback(result)

        return result

    def dodge_success(self):
        """Called when successfully dodged an attack"""
        self.stats.record_dodge()
        if self._on_dodge_callback:
            self._on_dodge_callback()

    def check_hit_against(self, opponent: 'Fighter') -> Optional[Dict[str, Any]]:
        """
        Cek apakah serangan saat ini mengenai lawan.
        Return hit info dict atau None.
        """
        if self.current_action is None:
            return None

        if self.current_action.hitbox is None:
            return None

        if not self.current_action.hitbox.is_active:
            return None

        if self.current_action.has_hit:
            return None  # Already hit this attack

        # Check collision
        result = check_collision(
            self.current_action.hitbox,
            opponent.hurtbox_manager,
            self.movement.get_position(),
            self.movement.facing_right,
            opponent.movement.get_position(),
            opponent.movement.facing_right
        )

        if result:
            zone, mult, hit_pos = result
            self.current_action.has_hit = True

            # Get damage
            action_data = ACTION_DATA.get(self.current_action.action_type)
            if action_data:
                import random
                base_damage = random.randint(action_data.damage_min,
                                            action_data.damage_max)
                base_damage *= self.stats.get_damage_modifier()
                base_damage *= mult

                # Check crit
                is_crit = random.random() < action_data.crit_bonus

                # Check counter (opponent was attacking)
                is_counter = (opponent.current_action is not None and
                             opponent.current_action.phase == ActionPhase.STARTUP)

                return {
                    'damage': base_damage,
                    'hit_zone': zone,
                    'hit_position': hit_pos,
                    'is_crit': is_crit,
                    'is_counter': is_counter,
                    'action': self.current_action.action_type,
                    'attacker': self,
                    'defender': opponent
                }

        return None

    def reset_round(self):
        """Reset untuk round baru"""
        # Reset position
        start_x = FIGHTER1_START_X if self.is_player_one else FIGHTER2_START_X
        self.movement.set_position(start_x, FIGHTER_START_Y)
        self.movement.facing_right = not self.is_player_one
        self.movement.state = MovementState.IDLE
        self.movement.knockback_velocity = 0

        # Reset stats
        self.stats.reset()

        # Reset action
        self.current_action = None
        self.action_queue.clear()
        self.last_action = None
        self.combo_window = 0

        # Reset animation
        self.animation_state = AnimationState.IDLE
        self.animation_frame = 0

        # Reset hurtbox
        self.hurtbox_manager.set_state('idle')

    def reset_match(self):
        """Reset untuk match baru"""
        self.reset_round()
        self.stats.reset_match()

    def set_animation(self, anim_name: str):
        """Set animation state by name"""
        try:
            self.animation_state = AnimationState(anim_name)
        except ValueError:
            self.animation_state = AnimationState.IDLE

    def get_up(self):
        """Bangun dari knockdown"""
        self.movement.get_up()
        self.animation_state = AnimationState.GETUP

    # Callbacks
    def on_hit(self, callback: Callable):
        """Register callback untuk saat terkena hit"""
        self._on_hit_callback = callback

    def on_block(self, callback: Callable):
        """Register callback untuk saat block berhasil"""
        self._on_block_callback = callback

    def on_dodge(self, callback: Callable):
        """Register callback untuk saat dodge berhasil"""
        self._on_dodge_callback = callback

    # Properties
    @property
    def x(self) -> float:
        return self.movement.x

    @property
    def y(self) -> float:
        return self.movement.y

    @property
    def position(self):
        return self.movement.get_position()

    @property
    def facing_right(self) -> bool:
        return self.movement.facing_right

    @property
    def is_attacking(self) -> bool:
        return (self.current_action is not None and
                self.current_action.action_type in
                (ActionType.JAB, ActionType.CROSS,
                 ActionType.HOOK, ActionType.UPPERCUT))

    @property
    def is_blocking(self) -> bool:
        return self.stats.is_blocking

    @property
    def is_stunned(self) -> bool:
        return self.stats.is_stunned

    @property
    def health_percent(self) -> float:
        return self.stats.health_percent

    @property
    def stamina_percent(self) -> float:
        return self.stats.stamina_percent

    @property
    def can_act(self) -> bool:
        return self.stats.can_act and self.current_action is None

    def get_state_info(self) -> Dict[str, Any]:
        """Get current state untuk AI/debug"""
        return {
            'name': self.name,
            'health': self.stats.health,
            'health_pct': self.health_percent,
            'stamina': self.stats.stamina,
            'stamina_pct': self.stamina_percent,
            'x': self.x,
            'y': self.y,
            'facing_right': self.facing_right,
            'is_attacking': self.is_attacking,
            'is_blocking': self.is_blocking,
            'is_stunned': self.is_stunned,
            'can_act': self.can_act,
            'current_action': self.current_action.action_type.value if self.current_action else None,
            'combo_count': self.stats.combo_count,
        }
