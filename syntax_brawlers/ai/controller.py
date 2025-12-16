"""
AI Controller
=============
Main controller yang mengintegrasikan LLM dan Fallback AI.
"""

import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
import sys
sys.path.insert(0, '..')

from config import ActionType, LLM_TIMEOUT
from ai.providers.base import BaseLLMProvider, LLMResponse
from ai.personality import PersonalityManager


@dataclass
class AIDecision:
    """Final AI decision"""
    action: ActionType
    reasoning: str
    trash_talk: str
    confidence: float
    source: str  # 'llm' or 'fallback'


class AIController:
    """
    Controller utama untuk AI fighter.
    Menggunakan LLM jika tersedia, fallback jika tidak.
    """

    def __init__(self, fighter, llm_provider: Optional[BaseLLMProvider] = None,
                 personality: str = 'balanced'):
        self.fighter = fighter
        self.llm_provider = llm_provider
        self.personality_name = personality
        self.personality = PersonalityManager(personality)

        # State
        self._pending_decision: Optional[AIDecision] = None
        self._decision_cooldown = 0.0
        self._min_decision_interval = 0.5  # 500ms between LLM calls

        # LLM state
        self._last_llm_response: Optional[LLMResponse] = None
        self._llm_available = False
        self._llm_check_cooldown = 0.0

        # Stats
        self.decisions_made = 0
        self.llm_decisions = 0

    async def initialize(self):
        """Initialize controller (check LLM availability)"""
        if self.llm_provider:
            self._llm_available = await self.llm_provider.check_availability()

    def get_action(self, fighter, opponent, round_time: float) -> Optional[ActionType]:
        """
        Synchronous action getter - ONLY uses LLM, no fallback.
        """
        if not fighter.can_act:
            return None

        if self._decision_cooldown > 0:
            return None

        # Build game state
        game_state = self._build_game_state(fighter, opponent, round_time)

        # ONLY use LLM - no fallback
        if self.llm_provider and hasattr(self.llm_provider, 'get_action_sync'):
            try:
                response = self.llm_provider.get_action_sync(
                    game_state,
                    self.personality.get_description()
                )

                self._decision_cooldown = self._min_decision_interval
                self.decisions_made += 1
                self.llm_decisions += 1

                if response:
                    self._last_llm_response = response
                    action = self._convert_action_string(response.action)
                    print(f"[{fighter.name}] LLM: {response.action} - {response.reasoning}")
                    return action

            except Exception as e:
                print(f"[{fighter.name}] LLM Error: {e}")
                self._decision_cooldown = 0.5  # Wait before retry

        return None  # No action if LLM fails - NO FALLBACK

    async def get_action_async(self, fighter, opponent,
                               round_time: float) -> Optional[ActionType]:
        """
        Async action getter - ONLY uses LLM, no fallback.
        """
        if not fighter.can_act:
            return None

        if self._decision_cooldown > 0:
            self._decision_cooldown -= 0.016  # Approximate frame time
            return None

        # Build game state
        game_state = self._build_game_state(fighter, opponent, round_time)

        # ONLY use LLM - no fallback
        if self.llm_provider:
            try:
                response = await asyncio.wait_for(
                    self.llm_provider.get_action(game_state,
                                                 self.personality.get_description()),
                    timeout=LLM_TIMEOUT
                )

                self._decision_cooldown = self._min_decision_interval
                self.decisions_made += 1
                self.llm_decisions += 1

                if response:
                    self._last_llm_response = response
                    action = self._convert_action_string(response.action)
                    print(f"[{fighter.name}] LLM: {response.action} - {response.reasoning}")
                    return action

            except asyncio.TimeoutError:
                print(f"[{fighter.name}] LLM Timeout - retrying...")
                self._decision_cooldown = 0.5

            except Exception as e:
                print(f"[{fighter.name}] LLM Error: {e}")
                self._decision_cooldown = 0.5

        return None  # No action if LLM fails - NO FALLBACK

    def _build_game_state(self, fighter, opponent, round_time: float) -> Dict[str, Any]:
        """Build game state dict untuk AI"""
        # Calculate distance
        distance_px = abs(fighter.x - opponent.x)

        if distance_px < 60:
            distance = 'clinch'
        elif distance_px < 140:
            distance = 'punch'
        elif distance_px < 200:
            distance = 'medium'
        else:
            distance = 'far'

        # Get opponent action
        opp_action = 'idle'
        if hasattr(opponent, 'current_action') and opponent.current_action:
            opp_action = opponent.current_action.action_type.value

        # Get last action
        my_last = 'none'
        if hasattr(fighter, 'last_action') and fighter.last_action:
            my_last = fighter.last_action.value

        return {
            'my_health': fighter.health_percent * 100,
            'my_stamina': fighter.stamina_percent * 100,
            'opp_health': opponent.health_percent * 100,
            'opp_stamina': opponent.stamina_percent * 100,
            'distance': distance,
            'distance_px': distance_px,
            'opp_action': opp_action,
            'my_last_action': my_last,
            'combo_count': fighter.stats.combo_count,
            'round_time': round_time,
            'can_act': fighter.can_act,
            'my_position': fighter.x,
            'opp_position': opponent.x,
        }

    def _convert_action(self, action: ActionType) -> ActionType:
        """Convert fallback action to ActionType"""
        return action

    def _convert_action_string(self, action_str: str) -> ActionType:
        """Convert string action to ActionType"""
        mapping = {
            'JAB': ActionType.JAB,
            'CROSS': ActionType.CROSS,
            'HOOK': ActionType.HOOK,
            'UPPERCUT': ActionType.UPPERCUT,
            'BLOCK': ActionType.BLOCK,
            'DODGE': ActionType.DODGE,
            'IDLE': ActionType.IDLE,
        }
        return mapping.get(action_str.upper(), ActionType.IDLE)

    def update(self, dt: float):
        """Update controller state"""
        if self._decision_cooldown > 0:
            self._decision_cooldown -= dt

        if self._llm_check_cooldown > 0:
            self._llm_check_cooldown -= dt
            if self._llm_check_cooldown <= 0 and self.llm_provider:
                # Re-check LLM availability
                asyncio.create_task(self._recheck_llm())

    async def _recheck_llm(self):
        """Re-check LLM availability"""
        if self.llm_provider:
            self._llm_available = await self.llm_provider.check_availability()

    def get_last_trash_talk(self) -> str:
        """Get last trash talk"""
        if self._last_llm_response and self._last_llm_response.trash_talk:
            return self._last_llm_response.trash_talk
        return self.personality.get_trash_talk()

    def get_last_reasoning(self) -> str:
        """Get last reasoning"""
        if self._last_llm_response:
            return self._last_llm_response.reasoning
        return ""

    def reset(self):
        """Reset untuk round/match baru"""
        self._pending_decision = None
        self._decision_cooldown = 0
        self.personality.reset()

    def get_stats(self) -> Dict[str, Any]:
        """Get AI stats"""
        return {
            'decisions_made': self.decisions_made,
            'llm_decisions': self.llm_decisions,
            'personality': self.personality_name,
        }

    def set_llm_provider(self, provider: BaseLLMProvider):
        """Set LLM provider"""
        self.llm_provider = provider
        self._llm_available = False
        asyncio.create_task(self.initialize())
