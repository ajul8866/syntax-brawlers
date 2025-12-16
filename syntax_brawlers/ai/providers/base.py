"""
Base LLM Provider
=================
Abstract base class untuk semua LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response dari LLM"""
    action: str
    reasoning: str
    trash_talk: str
    confidence: float
    raw_response: str = ""
    error: Optional[str] = None


class BaseLLMProvider(ABC):
    """
    Base class untuk LLM providers.
    """

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key
        self.model = model
        self.is_available = False
        self.last_error: Optional[str] = None

    @abstractmethod
    async def get_action(self, game_state: Dict[str, Any],
                         personality: str) -> LLMResponse:
        """
        Get action dari LLM berdasarkan game state.
        Return LLMResponse dengan action decision.
        """
        pass

    @abstractmethod
    async def check_availability(self) -> bool:
        """Check apakah provider available"""
        pass

    def build_prompt(self, game_state: Dict[str, Any],
                     personality: str) -> str:
        """Build prompt untuk LLM"""
        return f"""You are an AI boxer in a fighting game with personality: {personality}

Current Game State:
- Your Health: {game_state.get('my_health', 100)}%
- Your Stamina: {game_state.get('my_stamina', 100)}%
- Opponent Health: {game_state.get('opp_health', 100)}%
- Opponent Stamina: {game_state.get('opp_stamina', 100)}%
- Distance: {game_state.get('distance', 'medium')} ({game_state.get('distance_px', 200)}px)
- Opponent Action: {game_state.get('opp_action', 'idle')}
- Your Last Action: {game_state.get('my_last_action', 'none')}
- Combo Count: {game_state.get('combo_count', 0)}
- Round Time Remaining: {game_state.get('round_time', 180)}s
- Can Act: {game_state.get('can_act', True)}

Available Actions:
- JAB: Quick punch, low damage (8-12), high accuracy (90%), low stamina (8)
- CROSS: Strong straight, medium damage (18-25), medium accuracy (75%), medium stamina (18)
- HOOK: Wide swing, high damage (28-38), low accuracy (60%), high stamina (28)
- UPPERCUT: Rising punch, very high damage (35-45), low accuracy (50%), very high stamina (35)
- BLOCK: Reduce incoming damage by 70%, costs stamina (12)
- DODGE: Evade attack and create distance, costs stamina (15)
- IDLE: Wait and recover stamina

Respond in this exact JSON format:
{{"action": "JAB/CROSS/HOOK/UPPERCUT/BLOCK/DODGE/IDLE", "reasoning": "brief tactical reasoning", "trash_talk": "short taunt or comment", "confidence": 0.0-1.0}}

Choose wisely based on distance, stamina, and your personality. Be strategic!"""

    def parse_response(self, response: str) -> LLMResponse:
        """Parse LLM response ke LLMResponse"""
        import json
        import re

        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return LLMResponse(
                    action=data.get('action', 'IDLE').upper(),
                    reasoning=data.get('reasoning', ''),
                    trash_talk=data.get('trash_talk', ''),
                    confidence=float(data.get('confidence', 0.5)),
                    raw_response=response
                )
        except (json.JSONDecodeError, ValueError) as e:
            pass

        # Fallback: try to find action in text
        actions = ['JAB', 'CROSS', 'HOOK', 'UPPERCUT', 'BLOCK', 'DODGE', 'IDLE']
        for action in actions:
            if action in response.upper():
                return LLMResponse(
                    action=action,
                    reasoning="Parsed from text",
                    trash_talk="",
                    confidence=0.3,
                    raw_response=response
                )

        # Default to IDLE
        return LLMResponse(
            action='IDLE',
            reasoning="Could not parse response",
            trash_talk="",
            confidence=0.1,
            raw_response=response,
            error="Failed to parse LLM response"
        )
