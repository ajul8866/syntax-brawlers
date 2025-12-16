"""
Action System
=============
Validasi dan resolusi aksi combat.
"""

from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import random
import sys
sys.path.insert(0, '..')

from config import ActionType, ACTION_DATA, ActionData, HitZone


@dataclass
class ActionResult:
    """Hasil eksekusi aksi"""
    success: bool
    action_type: ActionType
    damage: float = 0
    stamina_used: float = 0
    hit: bool = False
    blocked: bool = False
    dodged: bool = False
    crit: bool = False
    counter: bool = False
    hit_zone: Optional[HitZone] = None
    message: str = ""


class ActionValidator:
    """
    Validasi apakah aksi bisa dilakukan.
    """

    @staticmethod
    def can_execute(action_type: ActionType, stamina: float,
                    is_stunned: bool, is_blocking: bool,
                    current_action: Optional[ActionType] = None) -> Tuple[bool, str]:
        """
        Cek apakah aksi bisa dilakukan.
        Return (can_execute, reason)
        """
        action_data = ACTION_DATA.get(action_type)

        if action_data is None:
            return False, "Invalid action"

        if is_stunned:
            return False, "Stunned"

        if stamina < action_data.stamina_cost * 0.5:  # Need at least 50% stamina cost
            return False, "Not enough stamina"

        # Can't attack while blocking
        if is_blocking and action_type in (ActionType.JAB, ActionType.CROSS,
                                           ActionType.HOOK, ActionType.UPPERCUT):
            return False, "Can't attack while blocking"

        # Check chain restrictions
        if current_action:
            current_data = ACTION_DATA.get(current_action)
            if current_data:
                # Some actions can't be chained
                if action_type == ActionType.BLOCK and current_action != ActionType.IDLE:
                    return False, "Can't block during attack"

        return True, "OK"

    @staticmethod
    def get_valid_actions(stamina: float, is_stunned: bool,
                         distance: float) -> List[ActionType]:
        """Dapatkan list aksi yang valid berdasarkan kondisi saat ini"""
        valid = []

        if is_stunned:
            return [ActionType.IDLE]

        for action_type in ActionType:
            if action_type == ActionType.IDLE:
                valid.append(action_type)
                continue

            action_data = ACTION_DATA.get(action_type)
            if action_data is None:
                continue

            # Check stamina
            if stamina < action_data.stamina_cost * 0.5:
                continue

            # Check range for attacks
            if action_type in (ActionType.JAB, ActionType.CROSS,
                              ActionType.HOOK, ActionType.UPPERCUT):
                if distance > action_data.range * 1.5:
                    continue  # Too far

            valid.append(action_type)

        return valid


class ActionResolver:
    """
    Resolve outcome ketika dua aksi bertemu.
    """

    @staticmethod
    def resolve_clash(attacker_action: ActionType, defender_action: ActionType,
                      distance: float, attacker_stats: Dict,
                      defender_stats: Dict) -> Dict[str, Any]:
        """
        Resolve clash antara dua aksi.
        Return dict dengan hasil untuk kedua pihak.
        """
        result = {
            'attacker': {
                'hit': False, 'blocked': False, 'dodged': False,
                'damage_dealt': 0, 'damage_taken': 0
            },
            'defender': {
                'hit': False, 'blocked': False, 'dodged': False,
                'damage_dealt': 0, 'damage_taken': 0
            },
            'trade': False,  # Both hit
            'clash_type': 'none'
        }

        att_data = ACTION_DATA.get(attacker_action)
        def_data = ACTION_DATA.get(defender_action)

        if att_data is None:
            return result

        # Attacker attacking
        if attacker_action in (ActionType.JAB, ActionType.CROSS,
                               ActionType.HOOK, ActionType.UPPERCUT):

            # Check if in range
            if distance > att_data.range:
                result['clash_type'] = 'whiff'
                return result

            # Calculate base damage
            damage = random.randint(att_data.damage_min, att_data.damage_max)
            damage *= attacker_stats.get('power', 1.0)

            # Defender response
            if defender_action == ActionType.BLOCK:
                # Blocked
                result['attacker']['blocked'] = True
                result['defender']['blocked'] = True
                result['clash_type'] = 'block'

                # Chip damage through block (30%)
                chip = damage * 0.3
                result['defender']['damage_taken'] = chip

                # Block breaks on heavy attacks
                if att_data.breaks_block and random.random() < 0.4:
                    result['clash_type'] = 'block_break'
                    result['defender']['damage_taken'] = damage * 0.5

            elif defender_action == ActionType.DODGE:
                # Check dodge success
                dodge_rate = def_data.hit_rate if def_data else 0.7
                if random.random() < dodge_rate:
                    result['attacker']['dodged'] = True
                    result['defender']['dodged'] = True
                    result['clash_type'] = 'dodge'
                else:
                    # Dodge failed, full damage
                    result['attacker']['hit'] = True
                    result['defender']['damage_taken'] = damage
                    result['clash_type'] = 'hit'

            elif defender_action in (ActionType.JAB, ActionType.CROSS,
                                     ActionType.HOOK, ActionType.UPPERCUT):
                # Trade! Both can hit
                result['trade'] = True
                result['clash_type'] = 'trade'

                # Attacker hits (faster attack wins priority)
                att_speed = att_data.startup_frames
                def_speed = def_data.startup_frames if def_data else 99

                if att_speed <= def_speed:
                    result['attacker']['hit'] = True
                    result['defender']['damage_taken'] = damage

                if def_data and def_speed <= att_speed:
                    def_damage = random.randint(def_data.damage_min, def_data.damage_max)
                    def_damage *= defender_stats.get('power', 1.0)
                    result['defender']['hit'] = True
                    result['attacker']['damage_taken'] = def_damage

            else:
                # Defender idle or other - clean hit
                result['attacker']['hit'] = True
                result['defender']['damage_taken'] = damage
                result['clash_type'] = 'hit'

                # Check crit
                if random.random() < att_data.crit_bonus:
                    result['defender']['damage_taken'] *= 2.0
                    result['attacker']['crit'] = True

        return result

    @staticmethod
    def calculate_damage(action_type: ActionType, attacker_power: float,
                         defender_defense: float, is_crit: bool = False,
                         is_counter: bool = False,
                         hit_zone: HitZone = HitZone.BODY) -> float:
        """Calculate final damage untuk serangan"""
        action_data = ACTION_DATA.get(action_type)
        if action_data is None:
            return 0

        # Base damage
        damage = random.randint(action_data.damage_min, action_data.damage_max)

        # Apply attacker power
        damage *= attacker_power

        # Apply defender defense
        damage /= defender_defense

        # Zone modifier
        zone_mult = {
            HitZone.HEAD: 1.5,
            HitZone.BODY: 1.0,
            HitZone.LEGS: 0.8
        }.get(hit_zone, 1.0)
        damage *= zone_mult

        # Crit bonus
        if is_crit:
            damage *= 2.0

        # Counter bonus (hitting during opponent startup)
        if is_counter:
            damage *= 1.5

        return damage


class ActionPriority:
    """
    Sistem prioritas untuk resolve aksi yang simultaneous.
    """

    # Priority rankings (lower = higher priority)
    PRIORITY = {
        ActionType.JAB: 1,       # Fastest
        ActionType.CROSS: 2,
        ActionType.HOOK: 3,
        ActionType.UPPERCUT: 4,
        ActionType.BLOCK: 0,    # Instant
        ActionType.DODGE: 1,
        ActionType.CLINCH: 3,
        ActionType.IDLE: 99,
    }

    @classmethod
    def compare(cls, action1: ActionType, action2: ActionType) -> int:
        """
        Compare priority dua aksi.
        Return: -1 jika action1 lebih cepat, 1 jika action2, 0 jika sama
        """
        p1 = cls.PRIORITY.get(action1, 99)
        p2 = cls.PRIORITY.get(action2, 99)

        if p1 < p2:
            return -1
        elif p1 > p2:
            return 1
        return 0

    @classmethod
    def get_winner(cls, action1: ActionType, action2: ActionType,
                   startup1: int, startup2: int) -> Optional[int]:
        """
        Tentukan siapa yang menang clash.
        Return: 1 jika action1 menang, 2 jika action2, None jika trade
        """
        # Compare startup frames first
        if startup1 < startup2:
            return 1
        elif startup2 < startup1:
            return 2

        # Same startup, compare priority
        priority_cmp = cls.compare(action1, action2)
        if priority_cmp < 0:
            return 1
        elif priority_cmp > 0:
            return 2

        # True trade - both hit
        return None
