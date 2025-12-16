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
        distance = game_state.get('distance', 'medium')

        # Distance-specific advice
        if distance == 'far':
            distance_advice = "You are FAR - use JAB to MOVE FORWARD and close distance! Attacks also move you forward."
        elif distance == 'medium':
            distance_advice = "MEDIUM range - JAB or CROSS will hit and move you closer."
        elif distance == 'punch':
            distance_advice = "PUNCH range - all attacks can hit! Use combos: JAB->CROSS->HOOK"
        else:  # clinch
            distance_advice = "CLINCH range - UPPERCUT and HOOK do massive damage here!"

        return f"""Boxing AI - {personality} style. Pick ONE action.

STATE:
- My HP: {int(game_state.get('my_health', 100))}% | Stamina: {int(game_state.get('my_stamina', 100))}%
- Enemy HP: {int(game_state.get('opp_health', 100))}% | Stamina: {int(game_state.get('opp_stamina', 100))}%
- Distance: {distance} | Enemy doing: {game_state.get('opp_action', 'idle')}

ACTIONS (all attacks MOVE YOU FORWARD):
- JAB: Fast, 8 dmg, 8 stamina - BEST for closing distance
- CROSS: Medium, 20 dmg, 18 stamina - Good follow-up after JAB
- HOOK: Heavy, 32 dmg, 28 stamina - Best at close range
- UPPERCUT: Massive, 40 dmg, 35 stamina - Best at clinch
- BLOCK: Reduce damage 70%, 12 stamina - Use vs incoming attack
- DODGE: Evade attack, 15 stamina - MOVES YOU BACKWARD
- IDLE: Recover stamina, no movement

TIP: {distance_advice}

Reply ONLY with JSON:
{{"action":"JAB","reasoning":"why","trash_talk":"taunt","confidence":0.8}}"""

    def parse_response(self, response: str) -> LLMResponse:
        """Parse LLM response ke LLMResponse"""
        import json
        import re

        try:
            # Try multiple JSON extraction patterns
            # Pattern 1: Simple JSON object
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                action = data.get('action', 'IDLE').upper().strip()
                # Validate action
                valid_actions = ['JAB', 'CROSS', 'HOOK', 'UPPERCUT', 'BLOCK', 'DODGE', 'IDLE']
                if action not in valid_actions:
                    action = 'IDLE'
                return LLMResponse(
                    action=action,
                    reasoning=data.get('reasoning', '')[:100],
                    trash_talk=data.get('trash_talk', '')[:50],
                    confidence=min(1.0, max(0.0, float(data.get('confidence', 0.5)))),
                    raw_response=response
                )

            # Pattern 2: Try full response as JSON
            data = json.loads(response.strip())
            action = data.get('action', 'IDLE').upper().strip()
            valid_actions = ['JAB', 'CROSS', 'HOOK', 'UPPERCUT', 'BLOCK', 'DODGE', 'IDLE']
            if action not in valid_actions:
                action = 'IDLE'
            return LLMResponse(
                action=action,
                reasoning=data.get('reasoning', '')[:100],
                trash_talk=data.get('trash_talk', '')[:50],
                confidence=min(1.0, max(0.0, float(data.get('confidence', 0.5)))),
                raw_response=response
            )

        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            pass

        # NO FALLBACK - LLM only
        # Debug: print raw response when can't parse
        print(f"[Parser] LLM response invalid: {response[:150]}...")

        # Return IDLE with error - NO fallback action
        return LLMResponse(
            action='IDLE',
            reasoning="LLM response format invalid",
            trash_talk="",
            confidence=0.0,
            raw_response=response,
            error="LLM response could not be parsed"
        )
