"""
Combat Engine
=============
Main engine untuk mengelola pertarungan.
"""

from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
import sys
sys.path.insert(0, '..')

from config import (
    ActionType, HitZone, FightPhase,
    HIT_STUN_LIGHT, HIT_STUN_HEAVY, BLOCK_STUN,
    KNOCKBACK_FORCE, SHAKE_LIGHT, SHAKE_MEDIUM, SHAKE_HEAVY
)
from combat.actions import ActionResolver, ActionPriority
from combat.combo import ComboTracker
from combat.distance import DistanceManager


@dataclass
class HitEvent:
    """Event untuk hit yang terjadi"""
    attacker_id: int
    defender_id: int
    action: ActionType
    damage: float
    hit_zone: HitZone
    position: Tuple[float, float]
    is_crit: bool = False
    is_counter: bool = False
    is_blocked: bool = False
    combo_count: int = 0
    timestamp: float = 0


@dataclass
class CombatState:
    """State pertarungan saat ini"""
    hit_events: List[HitEvent] = field(default_factory=list)
    last_attacker: Optional[int] = None
    momentum: float = 0.5  # 0.0 = fighter2, 0.5 = neutral, 1.0 = fighter1
    clinch_active: bool = False
    clinch_timer: float = 0


class CombatEngine:
    """
    Engine utama untuk combat system.
    Mengelola hit detection, damage calculation, dan state combat.
    """

    def __init__(self):
        self.state = CombatState()
        self.combo_trackers = [ComboTracker(), ComboTracker()]
        self.distance_manager = DistanceManager()
        self.time_elapsed = 0.0

        # Hit buffer untuk mencegah double hits
        self._hit_buffer: Dict[int, float] = {}
        self._hit_buffer_duration = 0.1  # 100ms

    def reset(self):
        """Reset untuk round baru"""
        self.state = CombatState()
        self.combo_trackers = [ComboTracker(), ComboTracker()]
        self.time_elapsed = 0.0
        self._hit_buffer.clear()

    def update(self, dt: float, fighters: List) -> Optional[Dict[str, Any]]:
        """
        Update combat engine.
        Return dict dengan hasil combat jika ada hit, None jika tidak.
        """
        self.time_elapsed += dt

        if len(fighters) < 2:
            return None

        fighter1, fighter2 = fighters[0], fighters[1]

        # Update distance
        self.distance_manager.update(fighter1.x, fighter2.x)

        # Update combo trackers
        for tracker in self.combo_trackers:
            tracker.update(dt)

        # Update hit buffer
        self._update_hit_buffer(dt)

        # Check for hits from both fighters
        results = []

        # Fighter 1 attacking
        hit_info = fighter1.check_hit_against(fighter2)
        if hit_info:
            result = self._process_hit(hit_info, 0, 1, fighter1, fighter2)
            if result:
                results.append(result)

        # Fighter 2 attacking
        hit_info = fighter2.check_hit_against(fighter1)
        if hit_info:
            result = self._process_hit(hit_info, 1, 0, fighter2, fighter1)
            if result:
                results.append(result)

        # Return combined result if any hits
        if results:
            return self._combine_results(results)

        return None

    def _update_hit_buffer(self, dt: float):
        """Update hit buffer timers"""
        expired = []
        for key, timer in self._hit_buffer.items():
            self._hit_buffer[key] = timer - dt
            if self._hit_buffer[key] <= 0:
                expired.append(key)

        for key in expired:
            del self._hit_buffer[key]

    def _process_hit(self, hit_info: Dict, attacker_idx: int,
                     defender_idx: int, attacker, defender) -> Optional[Dict]:
        """Process single hit event"""
        # Check hit buffer
        buffer_key = (attacker_idx, self.time_elapsed)
        if attacker_idx in [k[0] for k in self._hit_buffer.keys()]:
            return None

        # Add to buffer
        self._hit_buffer[(attacker_idx, self.time_elapsed)] = self._hit_buffer_duration

        # Get damage and zone
        damage = hit_info['damage']
        hit_zone = hit_info['hit_zone']
        hit_pos = hit_info['hit_position']
        is_crit = hit_info['is_crit']
        is_counter = hit_info['is_counter']

        # Apply hit to defender
        damage_result = defender.receive_hit(
            damage, hit_zone, attacker.x,
            is_crit=is_crit, is_counter=is_counter
        )

        # Record hit for attacker
        attacker.stats.record_hit(int(damage_result.final_damage))

        # Update combo tracker
        self.combo_trackers[attacker_idx].add_hit(
            hit_info['action'], damage_result.final_damage
        )

        # Create hit event
        event = HitEvent(
            attacker_id=attacker_idx,
            defender_id=defender_idx,
            action=hit_info['action'],
            damage=damage_result.final_damage,
            hit_zone=hit_zone,
            position=hit_pos,
            is_crit=is_crit,
            is_counter=is_counter,
            is_blocked=damage_result.was_blocked,
            combo_count=self.combo_trackers[attacker_idx].current_count,
            timestamp=self.time_elapsed
        )
        self.state.hit_events.append(event)
        self.state.last_attacker = attacker_idx

        # Update momentum
        self._update_momentum(attacker_idx, damage_result.final_damage)

        # Determine screen effects
        shake_amount = SHAKE_LIGHT
        if damage_result.is_big_hit:
            shake_amount = SHAKE_HEAVY
        elif is_crit:
            shake_amount = SHAKE_MEDIUM

        # Build result
        return {
            'type': 'hit',
            'attacker': attacker_idx,
            'defender': defender_idx,
            'damage': damage_result.final_damage,
            'raw_damage': damage_result.raw_damage,
            'hit_zone': hit_zone.value,
            'hit_position': hit_pos,
            'is_crit': is_crit,
            'is_counter': is_counter,
            'is_blocked': damage_result.was_blocked,
            'combo_count': event.combo_count,
            'big_hit': damage_result.is_big_hit,
            'shake_amount': shake_amount,
            'knockdown': defender.stats.health <= 0 or damage_result.final_damage >= 40,
            'knocked_down': defender if damage_result.final_damage >= 40 else None
        }

    def _combine_results(self, results: List[Dict]) -> Dict:
        """Combine multiple hit results (untuk trades)"""
        if len(results) == 1:
            return results[0]

        # Trade occurred
        combined = {
            'type': 'trade',
            'hits': results,
            'big_hit': any(r['big_hit'] for r in results),
            'shake_amount': max(r['shake_amount'] for r in results),
            'knockdown': any(r.get('knockdown', False) for r in results)
        }

        # Find knocked down fighter if any
        for r in results:
            if r.get('knocked_down'):
                combined['knocked_down'] = r['knocked_down']
                break

        return combined

    def _update_momentum(self, attacker_idx: int, damage: float):
        """Update momentum berdasarkan hit"""
        # Momentum mengarah ke attacker
        momentum_shift = damage / 100.0  # Max shift 1.0 per 100 damage
        momentum_shift = min(momentum_shift, 0.2)  # Cap per hit

        if attacker_idx == 0:
            self.state.momentum = min(1.0, self.state.momentum + momentum_shift)
        else:
            self.state.momentum = max(0.0, self.state.momentum - momentum_shift)

    def get_range_info(self) -> Dict[str, Any]:
        """Get current range information"""
        return {
            'distance': self.distance_manager.distance,
            'zone': self.distance_manager.get_zone(),
            'in_punch_range': self.distance_manager.in_punch_range(),
            'optimal_range': self.distance_manager.get_optimal_attack_range()
        }

    def get_momentum(self) -> Tuple[float, str]:
        """
        Get momentum info.
        Return: (value, description)
        """
        m = self.state.momentum
        if m >= 0.7:
            return (m, "Fighter 1 dominating")
        elif m >= 0.55:
            return (m, "Fighter 1 advantage")
        elif m >= 0.45:
            return (m, "Even")
        elif m >= 0.3:
            return (m, "Fighter 2 advantage")
        else:
            return (m, "Fighter 2 dominating")

    def get_combo_info(self, fighter_idx: int) -> Dict[str, Any]:
        """Get combo info untuk fighter"""
        tracker = self.combo_trackers[fighter_idx]
        return {
            'count': tracker.current_count,
            'damage': tracker.total_damage,
            'active': tracker.is_active,
            'sequence': tracker.get_sequence_name()
        }

    def check_clinch(self, fighter1, fighter2) -> bool:
        """Check dan handle clinch"""
        distance = abs(fighter1.x - fighter2.x)

        # Auto-clinch jika terlalu dekat
        if distance < 40:
            if not self.state.clinch_active:
                self.state.clinch_active = True
                self.state.clinch_timer = 1.5  # 1.5 second clinch
            return True

        return False

    def update_clinch(self, dt: float) -> bool:
        """Update clinch state. Return True jika masih dalam clinch."""
        if self.state.clinch_active:
            self.state.clinch_timer -= dt
            if self.state.clinch_timer <= 0:
                self.state.clinch_active = False
                return False
            return True
        return False

    def get_recent_events(self, seconds: float = 1.0) -> List[HitEvent]:
        """Get hit events dalam X detik terakhir"""
        cutoff = self.time_elapsed - seconds
        return [e for e in self.state.hit_events if e.timestamp >= cutoff]

    def get_stats(self) -> Dict[str, Any]:
        """Get combat statistics"""
        total_hits = len(self.state.hit_events)
        f1_hits = len([e for e in self.state.hit_events if e.attacker_id == 0])
        f2_hits = total_hits - f1_hits

        f1_damage = sum(e.damage for e in self.state.hit_events if e.attacker_id == 0)
        f2_damage = sum(e.damage for e in self.state.hit_events if e.attacker_id == 1)

        return {
            'total_hits': total_hits,
            'fighter1_hits': f1_hits,
            'fighter2_hits': f2_hits,
            'fighter1_damage': f1_damage,
            'fighter2_damage': f2_damage,
            'momentum': self.state.momentum,
            'time_elapsed': self.time_elapsed
        }
