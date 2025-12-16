"""
Fallback AI System
==================
AI lokal yang digunakan ketika LLM tidak tersedia.
Berbasis rule dan weighted random.
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import sys
sys.path.insert(0, '..')

from config import ActionType, ACTION_DATA
from ai.personality import PersonalityManager, TRASH_TALK


@dataclass
class FallbackDecision:
    """Decision dari fallback AI"""
    action: ActionType
    reasoning: str
    trash_talk: str
    confidence: float


class FallbackAI:
    """
    Fallback AI menggunakan rule-based decision making.
    Digunakan ketika LLM tidak tersedia atau timeout.
    """

    def __init__(self, personality: str = 'balanced'):
        self.personality = PersonalityManager(personality)
        self._last_action: Optional[ActionType] = None
        self._consecutive_same = 0
        self._combo_sequence: list = []

    def get_action(self, game_state: Dict[str, Any]) -> FallbackDecision:
        """Get action berdasarkan game state"""
        # Extract state
        my_health = game_state.get('my_health', 100)
        my_stamina = game_state.get('my_stamina', 100)
        opp_health = game_state.get('opp_health', 100)
        opp_stamina = game_state.get('opp_stamina', 100)
        distance = game_state.get('distance', 'medium')
        distance_px = game_state.get('distance_px', 200)
        opp_action = game_state.get('opp_action', 'idle')
        can_act = game_state.get('can_act', True)

        if not can_act:
            return FallbackDecision(
                action=ActionType.IDLE,
                reasoning="Cannot act",
                trash_talk="",
                confidence=1.0
            )

        # Decision logic
        action, reasoning, confidence = self._decide_action(
            my_health, my_stamina, opp_health, opp_stamina,
            distance, distance_px, opp_action
        )

        # Prevent repetition
        if action == self._last_action:
            self._consecutive_same += 1
            if self._consecutive_same > 3:
                # Force variety
                action = self._get_alternative_action(action, my_stamina)
                reasoning = "Mixing it up"
                confidence *= 0.8
        else:
            self._consecutive_same = 0

        self._last_action = action

        # Get trash talk (deterministic - every 5th decision)
        trash_talk = ""
        if self._consecutive_same == 0:  # First action of new type
            trash_talk = self.personality.get_trash_talk()

        return FallbackDecision(
            action=action,
            reasoning=reasoning,
            trash_talk=trash_talk,
            confidence=confidence
        )

    def _decide_action(self, my_health: float, my_stamina: float,
                       opp_health: float, opp_stamina: float,
                       distance: str, distance_px: float,
                       opp_action: str) -> Tuple[ActionType, str, float]:
        """Core decision logic"""

        # CRITICAL: Opponent attacking
        if opp_action in ['JAB', 'CROSS', 'HOOK', 'UPPERCUT']:
            return self._respond_to_attack(opp_action, my_stamina, distance)

        # DESPERATE: Very low health
        if my_health < 20:
            return self._desperate_mode(my_stamina, opp_health, distance)

        # FINISH: Opponent low health
        if opp_health < 20 and distance in ['punch', 'clinch']:
            return self._finish_mode(my_stamina)

        # RECOVER: Low stamina
        if my_stamina < 20:
            return (ActionType.IDLE, "Recovering stamina", 0.9)

        # DISTANCE BASED
        if distance == 'far':
            # Agresif maju, atau jab untuk approach
            if my_stamina >= 8 and random.random() < 0.7:
                return (ActionType.JAB, "Approaching with jab", 0.7)
            return (ActionType.JAB, "Closing distance", 0.6)

        if distance == 'clinch':
            return self._clinch_action(my_stamina)

        if distance == 'punch':
            return self._punch_range_action(my_stamina, opp_stamina)

        if distance == 'medium':
            return self._medium_range_action(my_stamina)

        # DEFAULT
        return self._default_action(my_stamina)

    def _respond_to_attack(self, opp_action: str, stamina: float,
                           distance: str) -> Tuple[ActionType, str, float]:
        """Respond to incoming attack - deterministic"""
        # Heavy attack - dodge if possible
        if opp_action in ['HOOK', 'UPPERCUT']:
            if stamina >= 15:
                return (ActionType.DODGE, "Evading heavy attack", 0.8)
            elif stamina >= 12:
                return (ActionType.BLOCK, "Blocking heavy attack", 0.85)

        # Light attack - counter with jab
        if stamina >= 8 and self.personality.traits.aggression > 0.5:
            return (ActionType.JAB, "Counter jab", 0.7)

        # Default: block
        if stamina >= 12:
            return (ActionType.BLOCK, "Blocking", 0.8)

        return (ActionType.JAB, "Trading", 0.5)

    def _desperate_mode(self, stamina: float, opp_health: float,
                        distance: str) -> Tuple[ActionType, str, float]:
        """Actions when very low health"""
        # If can finish, go for it
        if opp_health < 30 and distance in ['punch', 'clinch']:
            if stamina >= 35:
                return (ActionType.UPPERCUT, "Desperate uppercut!", 0.6)
            if stamina >= 28:
                return (ActionType.HOOK, "Desperate hook!", 0.6)

        # Otherwise play safe
        if stamina >= 15:
            return (ActionType.DODGE, "Survival dodge", 0.7)
        if stamina >= 12:
            return (ActionType.BLOCK, "Survival block", 0.7)

        return (ActionType.IDLE, "Desperate recovery", 0.5)

    def _finish_mode(self, stamina: float) -> Tuple[ActionType, str, float]:
        """Actions to finish low health opponent"""
        if stamina >= 35:
            return (ActionType.UPPERCUT, "Finish with uppercut!", 0.8)
        if stamina >= 28:
            return (ActionType.HOOK, "Finish with hook!", 0.8)
        if stamina >= 18:
            return (ActionType.CROSS, "Finish with cross!", 0.8)
        if stamina >= 8:
            return (ActionType.JAB, "Finish with jab!", 0.8)

        return (ActionType.IDLE, "Waiting to finish", 0.6)

    def _clinch_action(self, stamina: float) -> Tuple[ActionType, str, float]:
        """Action in clinch range - deterministic"""
        # Prioritas: uppercut > hook > jab berdasarkan stamina
        if stamina >= 35:
            return (ActionType.UPPERCUT, "Clinch uppercut", 0.7)
        if stamina >= 28:
            return (ActionType.HOOK, "Short hook", 0.75)
        if stamina >= 8:
            return (ActionType.JAB, "Body jab", 0.8)

        return (ActionType.JAB, "Quick jab", 0.6)

    def _punch_range_action(self, my_stamina: float,
                            opp_stamina: float) -> Tuple[ActionType, str, float]:
        """Action in punch range - deterministic combo system"""
        # Combo logic: JAB -> CROSS -> HOOK
        if self._last_action == ActionType.JAB and my_stamina >= 18:
            self._combo_sequence.append(ActionType.CROSS)
            return (ActionType.CROSS, "Jab-Cross combo", 0.8)

        if self._last_action == ActionType.CROSS and my_stamina >= 28:
            self._combo_sequence.append(ActionType.HOOK)
            return (ActionType.HOOK, "Combo finisher", 0.75)

        # Start combo with jab
        if my_stamina >= 8:
            return (ActionType.JAB, "Starting combo", 0.7)

        return (ActionType.JAB, "In range attack", 0.7)

    def _medium_range_action(self, stamina: float) -> Tuple[ActionType, str, float]:
        """Action in medium range - deterministic"""
        if stamina >= 8:
            return (ActionType.JAB, "Range finder jab", 0.75)

        return (ActionType.JAB, "Closing in", 0.6)

    def _default_action(self, stamina: float) -> Tuple[ActionType, str, float]:
        """Default action"""
        action = self.personality.choose_action({'my_stamina': stamina})
        return (action, "Standard play", 0.6)

    def _get_alternative_action(self, current: ActionType,
                                 stamina: float) -> ActionType:
        """Get different action to avoid repetition - deterministic"""
        # Cycle through actions: JAB -> CROSS -> HOOK -> JAB
        cycle = {
            ActionType.JAB: ActionType.CROSS,
            ActionType.CROSS: ActionType.HOOK,
            ActionType.HOOK: ActionType.JAB,
            ActionType.BLOCK: ActionType.JAB,
            ActionType.DODGE: ActionType.JAB,
            ActionType.IDLE: ActionType.JAB,
        }

        next_action = cycle.get(current, ActionType.JAB)

        # Check stamina
        action_data = ACTION_DATA.get(next_action)
        if action_data and stamina >= action_data.stamina_cost:
            return next_action

        # Default to jab (lowest cost)
        return ActionType.JAB

    def reset(self):
        """Reset state"""
        self._last_action = None
        self._consecutive_same = 0
        self._combo_sequence.clear()
        self.personality.reset()


def create_fallback_ai(personality: str = 'balanced') -> FallbackAI:
    """Factory function untuk FallbackAI"""
    return FallbackAI(personality)
