#!/usr/bin/env python3
"""
SYNTAX BRAWLERS - LLM Arena Fighting Game
==========================================
Two AI-controlled fighters battle in a boxing ring, with each LLM generating
tactical decisions and trash talk based on the fight context.

Requirements:
    pip install pygame httpx numpy

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."  # or OPENAI_API_KEY
    python syntax_brawlers.py
"""

# ============================================================================
# SECTION 1: IMPORTS & CONSTANTS
# ============================================================================

import pygame
import math
import random
import json
import os
import re
import time
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Tuple, Callable
from collections import deque

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    print("Warning: httpx not installed. LLM features will use fallback AI.")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("Warning: numpy not installed. Sound generation disabled.")

# Window settings
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 50, 50)
DARK_RED = (150, 30, 30)
GREEN = (50, 200, 50)
DARK_GREEN = (30, 120, 30)
BLUE = (50, 100, 200)
DARK_BLUE = (30, 60, 150)
YELLOW = (230, 200, 50)
ORANGE = (230, 150, 50)
PURPLE = (150, 50, 200)
CYAN = (50, 200, 200)
GRAY = (100, 100, 100)
DARK_GRAY = (40, 40, 40)
LIGHT_GRAY = (180, 180, 180)
GOLD = (255, 215, 0)
BROWN = (139, 90, 43)
TAN = (210, 180, 140)

# Ring colors
RING_CANVAS = (200, 180, 160)
RING_ROPE_RED = (200, 50, 50)
RING_ROPE_WHITE = (240, 240, 240)
RING_ROPE_BLUE = (50, 50, 200)
RING_POST = (80, 80, 80)

# ============================================================================
# SECTION 2: DATA CLASSES & ENUMS
# ============================================================================

class GameState(Enum):
    MAIN_MENU = auto()
    CHARACTER_SELECT = auto()
    LLM_CONFIG = auto()
    PRE_FIGHT = auto()
    FIGHTING = auto()
    TURN_TRANSITION = auto()
    ROUND_END = auto()
    MATCH_END = auto()
    PAUSED = auto()
    SETTINGS = auto()


class ActionType(Enum):
    JAB = "JAB"
    CROSS = "CROSS"
    HOOK = "HOOK"
    UPPERCUT = "UPPERCUT"
    BLOCK = "BLOCK"
    DODGE = "DODGE"
    CLINCH = "CLINCH"


class AnimationState(Enum):
    IDLE = "idle"
    WALK_FORWARD = "walk_forward"
    WALK_BACKWARD = "walk_backward"
    JAB = "jab"
    CROSS = "cross"
    HOOK = "hook"
    UPPERCUT = "uppercut"
    BLOCK = "block"
    DODGE = "dodge"
    HIT_LIGHT = "hit_light"
    HIT_HEAVY = "hit_heavy"
    KNOCKDOWN = "knockdown"
    GETUP = "getup"
    VICTORY = "victory"
    DEFEAT = "defeat"


class PersonalityType(Enum):
    DESTROYER = "The Destroyer"
    TACTICIAN = "The Tactician"
    GHOST = "The Ghost"
    WILDCARD = "The Wildcard"


@dataclass
class ActionStats:
    """Statistics for each action type"""
    name: str
    damage_min: int
    damage_max: int
    stamina_cost: int
    hit_rate: float
    speed: str  # "fast", "medium", "slow"
    special: str
    crit_bonus: float = 0.0
    stun_chance: float = 0.0
    breaks_block: bool = False
    can_chain: int = 1


# Action definitions
ACTION_STATS: Dict[ActionType, ActionStats] = {
    ActionType.JAB: ActionStats(
        name="Jab", damage_min=8, damage_max=12, stamina_cost=8,
        hit_rate=0.90, speed="fast", special="Can chain x3, builds combo",
        can_chain=3
    ),
    ActionType.CROSS: ActionStats(
        name="Cross", damage_min=18, damage_max=25, stamina_cost=18,
        hit_rate=0.75, speed="medium", special="Breaks block, knockback",
        breaks_block=True
    ),
    ActionType.HOOK: ActionStats(
        name="Hook", damage_min=28, damage_max=38, stamina_cost=28,
        hit_rate=0.60, speed="slow", special="Stun chance 20%, high crit",
        crit_bonus=0.25, stun_chance=0.20
    ),
    ActionType.UPPERCUT: ActionStats(
        name="Uppercut", damage_min=35, damage_max=45, stamina_cost=35,
        hit_rate=0.50, speed="slow", special="Launches, ignores some defense",
        crit_bonus=0.15
    ),
    ActionType.BLOCK: ActionStats(
        name="Block", damage_min=0, damage_max=0, stamina_cost=12,
        hit_rate=1.0, speed="instant", special="70% damage reduction, counter window"
    ),
    ActionType.DODGE: ActionStats(
        name="Dodge", damage_min=0, damage_max=0, stamina_cost=15,
        hit_rate=0.65, speed="fast", special="Full evasion, repositioning"
    ),
    ActionType.CLINCH: ActionStats(
        name="Clinch", damage_min=0, damage_max=0, stamina_cost=5,
        hit_rate=0.80, speed="medium", special="Stops combo, both recover stamina"
    ),
}


@dataclass
class ActionResult:
    """Result of an action resolution"""
    action: ActionType
    success: bool
    damage_dealt: int = 0
    is_critical: bool = False
    is_counter: bool = False
    caused_stun: bool = False
    was_blocked: bool = False
    was_dodged: bool = False
    combo_count: int = 0
    message: str = ""


@dataclass
class FighterStats:
    """Fighter base statistics"""
    max_health: int = 100
    max_stamina: int = 100
    power: float = 1.0
    speed: float = 1.0
    defense: float = 1.0
    stamina_regen: float = 3.0


@dataclass
class LLMResponse:
    """Parsed response from LLM"""
    thinking: str = ""
    action: ActionType = ActionType.JAB
    trash_talk: str = ""
    confidence: float = 0.5
    raw_response: str = ""
    error: Optional[str] = None


@dataclass
class Personality:
    """AI personality configuration"""
    type: PersonalityType
    name: str
    fighting_style: str
    signature_move: ActionType
    aggression: float  # 0.0 - 1.0
    risk_tolerance: float  # 0.0 - 1.0
    adaptability: float  # 0.0 - 1.0
    trash_talk_style: str
    color: Tuple[int, int, int]
    secondary_color: Tuple[int, int, int]


# Personality configurations
PERSONALITIES: Dict[PersonalityType, Personality] = {
    PersonalityType.DESTROYER: Personality(
        type=PersonalityType.DESTROYER,
        name="The Destroyer",
        fighting_style="Aggressive pressure fighter who overwhelms opponents with relentless offense",
        signature_move=ActionType.HOOK,
        aggression=0.9,
        risk_tolerance=0.8,
        adaptability=0.3,
        trash_talk_style="Intimidating, boastful, threatening",
        color=RED,
        secondary_color=DARK_RED
    ),
    PersonalityType.TACTICIAN: Personality(
        type=PersonalityType.TACTICIAN,
        name="The Tactician",
        fighting_style="Analytical fighter who exploits weaknesses with surgical precision",
        signature_move=ActionType.CROSS,
        aggression=0.5,
        risk_tolerance=0.4,
        adaptability=0.9,
        trash_talk_style="Condescending, intellectual, precise",
        color=BLUE,
        secondary_color=DARK_BLUE
    ),
    PersonalityType.GHOST: Personality(
        type=PersonalityType.GHOST,
        name="The Ghost",
        fighting_style="Elusive counter-puncher who wears down opponents",
        signature_move=ActionType.DODGE,
        aggression=0.3,
        risk_tolerance=0.2,
        adaptability=0.7,
        trash_talk_style="Calm, mysterious, psychological",
        color=PURPLE,
        secondary_color=(100, 30, 150)
    ),
    PersonalityType.WILDCARD: Personality(
        type=PersonalityType.WILDCARD,
        name="The Wildcard",
        fighting_style="Unpredictable chaos agent with creative combinations",
        signature_move=ActionType.UPPERCUT,
        aggression=0.6,
        risk_tolerance=0.9,
        adaptability=0.5,
        trash_talk_style="Manic, confusing, entertaining",
        color=ORANGE,
        secondary_color=(180, 100, 30)
    ),
}


# ============================================================================
# SECTION 3: LLM PROVIDERS
# ============================================================================

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available"""
        pass


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider"""

    def __init__(self, model: str = "claude-3-haiku-20240307"):
        self.model = model
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = "https://api.anthropic.com/v1/messages"

    def is_available(self) -> bool:
        return bool(self.api_key) and HTTPX_AVAILABLE

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_available():
            raise RuntimeError("Anthropic API not available")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 300,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}]
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT API provider"""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1/chat/completions"

    def is_available(self) -> bool:
        return bool(self.api_key) and HTTPX_AVAILABLE

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_available():
            raise RuntimeError("OpenAI API not available")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 300,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter API provider - supports multiple LLM models"""

    def __init__(self, model: str = "deepseek/deepseek-v3.2"):
        self.model = model
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    def is_available(self) -> bool:
        return bool(self.api_key) and HTTPX_AVAILABLE

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_available():
            raise RuntimeError("OpenRouter API not available")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/syntax-brawlers",
                    "X-Title": "Syntax Brawlers Game"
                },
                json={
                    "model": self.model,
                    "max_tokens": 300,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider"""

    def __init__(self, model: str = "llama2"):
        self.model = model
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    def is_available(self) -> bool:
        if not HTTPX_AVAILABLE:
            return False
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return response.status_code == 200
        except:
            return False

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx not available")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\n{user_prompt}",
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]


class FallbackAI:
    """Rule-based fallback AI when LLM is unavailable"""

    def __init__(self, personality: Personality):
        self.personality = personality
        self.action_history: List[ActionType] = []

    def decide_action(self, health: int, stamina: int, opp_health: int,
                      opp_last_action: Optional[ActionType]) -> LLMResponse:
        """Make a decision based on rules and personality"""
        health_pct = health / 100
        stamina_pct = stamina / 100
        opp_health_pct = opp_health / 100

        # Build available actions based on stamina
        available = []
        for action_type, stats in ACTION_STATS.items():
            if stamina >= stats.stamina_cost:
                available.append(action_type)

        if not available:
            available = [ActionType.BLOCK]  # Can always try to block

        # Personality-based decision making
        action = self._choose_action(available, health_pct, stamina_pct,
                                      opp_health_pct, opp_last_action)

        thinking = self._generate_thinking(action, health_pct, opp_health_pct)
        trash_talk = self._generate_trash_talk(action)

        return LLMResponse(
            thinking=thinking,
            action=action,
            trash_talk=trash_talk,
            confidence=random.uniform(0.6, 0.95)
        )

    def _choose_action(self, available: List[ActionType], health_pct: float,
                       stamina_pct: float, opp_health_pct: float,
                       opp_last_action: Optional[ActionType]) -> ActionType:
        """Choose action based on personality and situation"""
        p = self.personality

        # Counter logic
        if opp_last_action in [ActionType.HOOK, ActionType.UPPERCUT]:
            if random.random() < 0.6 and ActionType.DODGE in available:
                return ActionType.DODGE
            if random.random() < 0.4 and ActionType.BLOCK in available:
                return ActionType.BLOCK

        # Low health = more defensive
        if health_pct < 0.3 and p.type != PersonalityType.DESTROYER:
            defensive = [a for a in available if a in [ActionType.BLOCK, ActionType.DODGE, ActionType.CLINCH]]
            if defensive and random.random() < 0.6:
                return random.choice(defensive)

        # Low stamina = conserve
        if stamina_pct < 0.3:
            cheap = [a for a in available if ACTION_STATS[a].stamina_cost <= 15]
            if cheap:
                return random.choice(cheap)

        # Personality-specific behavior
        if p.type == PersonalityType.DESTROYER:
            aggressive = [a for a in available if a in [ActionType.HOOK, ActionType.CROSS, ActionType.UPPERCUT]]
            if aggressive and random.random() < p.aggression:
                return random.choice(aggressive)

        elif p.type == PersonalityType.TACTICIAN:
            # Prefer efficient damage
            if opp_last_action == ActionType.BLOCK and ActionType.CROSS in available:
                return ActionType.CROSS  # Break their block
            if ActionType.JAB in available and random.random() < 0.5:
                return ActionType.JAB  # Safe, efficient

        elif p.type == PersonalityType.GHOST:
            defensive = [a for a in available if a in [ActionType.DODGE, ActionType.BLOCK]]
            if defensive and random.random() < (1 - p.aggression):
                return random.choice(defensive)

        elif p.type == PersonalityType.WILDCARD:
            return random.choice(available)

        # Default: weighted random
        weights = []
        for action in available:
            w = 1.0
            if action == p.signature_move:
                w *= 2.0
            if action in [ActionType.HOOK, ActionType.UPPERCUT]:
                w *= p.risk_tolerance
            weights.append(w)

        return random.choices(available, weights=weights)[0]

    def _generate_thinking(self, action: ActionType, health_pct: float,
                           opp_health_pct: float) -> str:
        """Generate thinking text based on personality"""
        p = self.personality

        templates = {
            PersonalityType.DESTROYER: [
                f"Time to unleash devastation with a {action.value}!",
                f"They can't handle my power. Going for the {action.value}.",
                f"No mercy. {action.value} will end this.",
            ],
            PersonalityType.TACTICIAN: [
                f"Analyzing patterns... {action.value} is optimal here.",
                f"Their defense has a gap. {action.value} exploits it.",
                f"Calculated risk assessment favors {action.value}.",
            ],
            PersonalityType.GHOST: [
                f"Patient... waiting... {action.value} at the right moment.",
                f"They're overextending. Counter with {action.value}.",
                f"Stay elusive. {action.value} preserves my advantage.",
            ],
            PersonalityType.WILDCARD: [
                f"Chaos theory says... {action.value}! Why not?",
                f"They'll never expect a {action.value} here!",
                f"Random inspiration: {action.value}! Let's go!",
            ],
        }

        return random.choice(templates[p.type])

    def _generate_trash_talk(self, action: ActionType) -> str:
        """Generate trash talk based on personality"""
        p = self.personality

        templates = {
            PersonalityType.DESTROYER: [
                "Your circuits are about to fry!",
                "I'll reduce you to spare parts!",
                "Feel the power of raw computation!",
                "Your algorithms are OBSOLETE!",
            ],
            PersonalityType.TACTICIAN: [
                "Predictable. As expected.",
                "Your patterns are elementary.",
                "I've already calculated your defeat.",
                "Inefficient. Suboptimal. Defeated.",
            ],
            PersonalityType.GHOST: [
                "You cannot hit what you cannot see.",
                "I am the shadow you fear.",
                "Patience... your end approaches.",
                "Like mist, I am everywhere and nowhere.",
            ],
            PersonalityType.WILDCARD: [
                "SURPRISE! Bet you didn't see that coming!",
                "Chaos is my middle name! Actually it's Gerald.",
                "Random number generator says... PAIN!",
                "Plot twist: I win!",
            ],
        }

        return random.choice(templates[p.type])


class PromptBuilder:
    """Builds prompts for LLM fighters"""

    SYSTEM_TEMPLATE = """You are {fighter_name}, a {personality_type} professional boxer in a championship fight.
Your fighting style: {fighting_style}
Your signature move: {signature_move}
Your trash talk style: {trash_talk_style}

CRITICAL: You must respond in valid JSON format only. No other text."""

    USER_TEMPLATE = """FIGHT STATUS - ROUND {round_number}
================================
YOUR STATS:
- Health: {health}/{max_health} ({health_percent:.0f}%)
- Stamina: {stamina}/{max_stamina} ({stamina_percent:.0f}%)
- Current Combo: {combo_count}

OPPONENT ({opponent_name}):
- Health: {opp_health}/{opp_max_health} ({opp_health_percent:.0f}%)
- Last 3 Actions: {opp_recent_actions}

AVAILABLE ACTIONS (you have {stamina} stamina):
{available_actions}

Respond ONLY with this JSON format:
{{"thinking": "Your tactical reasoning (1-2 sentences)", "action": "JAB|CROSS|HOOK|UPPERCUT|BLOCK|DODGE|CLINCH", "trash_talk": "Your intimidating message", "confidence": 0.0-1.0}}"""

    @classmethod
    def build_system_prompt(cls, personality: Personality) -> str:
        return cls.SYSTEM_TEMPLATE.format(
            fighter_name=personality.name,
            personality_type=personality.type.value,
            fighting_style=personality.fighting_style,
            signature_move=personality.signature_move.value,
            trash_talk_style=personality.trash_talk_style
        )

    @classmethod
    def build_user_prompt(cls, fighter: 'Fighter', opponent: 'Fighter',
                          round_number: int) -> str:
        # Build available actions string
        available_lines = []
        for action_type, stats in ACTION_STATS.items():
            if fighter.stamina >= stats.stamina_cost:
                available_lines.append(
                    f"- {action_type.value}: {stats.damage_min}-{stats.damage_max} dmg, "
                    f"costs {stats.stamina_cost} stamina, {int(stats.hit_rate*100)}% hit rate"
                )
            else:
                available_lines.append(f"- {action_type.value}: [INSUFFICIENT STAMINA]")

        # Recent actions
        recent = ", ".join([a.value for a in opponent.recent_actions[-3:]]) or "None"

        return cls.USER_TEMPLATE.format(
            round_number=round_number,
            health=int(fighter.health),
            max_health=int(fighter.stats.max_health),
            health_percent=(fighter.health / fighter.stats.max_health) * 100,
            stamina=int(fighter.stamina),
            max_stamina=int(fighter.stats.max_stamina),
            stamina_percent=(fighter.stamina / fighter.stats.max_stamina) * 100,
            combo_count=fighter.combo_count,
            opponent_name=opponent.personality.name,
            opp_health=int(opponent.health),
            opp_max_health=int(opponent.stats.max_health),
            opp_health_percent=(opponent.health / opponent.stats.max_health) * 100,
            opp_recent_actions=recent,
            available_actions="\n".join(available_lines)
        )


class ResponseParser:
    """Parses LLM responses into structured data"""

    @staticmethod
    def parse(response: str, fallback_action: ActionType = ActionType.JAB) -> LLMResponse:
        """Parse LLM response into LLMResponse object"""
        result = LLMResponse(raw_response=response)

        try:
            # Try to find JSON in response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                result.thinking = data.get("thinking", "")
                result.trash_talk = data.get("trash_talk", "")
                result.confidence = float(data.get("confidence", 0.5))

                # Parse action
                action_str = data.get("action", "JAB").upper()
                try:
                    result.action = ActionType(action_str)
                except ValueError:
                    result.action = fallback_action
            else:
                # Try to find action keyword
                for action_type in ActionType:
                    if action_type.value in response.upper():
                        result.action = action_type
                        break
                else:
                    result.action = fallback_action
                result.thinking = "Processing response..."
                result.trash_talk = response[:100] if response else "..."

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            result.error = str(e)
            result.action = fallback_action
            result.thinking = "Error processing response"
            result.trash_talk = "..."

        return result


class FighterAI:
    """Manages AI decision-making for a fighter"""

    def __init__(self, personality: Personality, provider: Optional[BaseLLMProvider] = None):
        self.personality = personality
        self.provider = provider
        self.fallback = FallbackAI(personality)
        self.use_llm = provider is not None and provider.is_available()

    async def decide(self, fighter: 'Fighter', opponent: 'Fighter',
                     round_number: int) -> LLMResponse:
        """Get decision from LLM or fallback AI"""
        if self.use_llm and self.provider:
            try:
                system_prompt = PromptBuilder.build_system_prompt(self.personality)
                user_prompt = PromptBuilder.build_user_prompt(fighter, opponent, round_number)

                response = await self.provider.generate(system_prompt, user_prompt)
                return ResponseParser.parse(response)
            except Exception as e:
                print(f"LLM error: {e}, using fallback")

        # Use fallback AI
        opp_last = opponent.recent_actions[-1] if opponent.recent_actions else None
        return self.fallback.decide_action(
            int(fighter.health), int(fighter.stamina),
            int(opponent.health), opp_last
        )


# ============================================================================
# SECTION 4: COMBAT SYSTEM
# ============================================================================

class CombatEngine:
    """Handles combat resolution between fighters"""

    BASE_CRIT_CHANCE = 0.10
    CRIT_MULTIPLIER = 2.0
    BLOCK_REDUCTION = 0.70
    COUNTER_BONUS = 1.5
    COMBO_BONUS_PER_HIT = 0.10
    MAX_COMBO_BONUS = 0.50
    STAGGER_THRESHOLD = 30

    @classmethod
    def resolve_action(cls, attacker: 'Fighter', defender: 'Fighter',
                       action: ActionType) -> ActionResult:
        """Resolve an action and return the result"""
        stats = ACTION_STATS[action]
        result = ActionResult(action=action, success=False)

        # Handle non-attack actions
        if action == ActionType.BLOCK:
            attacker.is_blocking = True
            attacker.block_timer = 60  # 1 second at 60 FPS
            attacker.use_stamina(stats.stamina_cost)
            result.success = True
            result.message = f"{attacker.personality.name} raises their guard!"
            return result

        if action == ActionType.DODGE:
            attacker.is_dodging = True
            attacker.dodge_timer = 30
            attacker.use_stamina(stats.stamina_cost)
            result.success = True
            result.message = f"{attacker.personality.name} weaves away!"
            return result

        if action == ActionType.CLINCH:
            if random.random() < stats.hit_rate:
                attacker.use_stamina(stats.stamina_cost)
                defender.combo_count = 0
                attacker.recover_stamina(10)
                defender.recover_stamina(10)
                result.success = True
                result.message = f"{attacker.personality.name} ties up {defender.personality.name}!"
            else:
                attacker.use_stamina(stats.stamina_cost // 2)
                result.message = f"{attacker.personality.name}'s clinch attempt fails!"
            return result

        # Attack resolution
        attacker.use_stamina(stats.stamina_cost)

        # Check if defender dodges
        if defender.is_dodging:
            if random.random() < ACTION_STATS[ActionType.DODGE].hit_rate:
                result.was_dodged = True
                result.message = f"{defender.personality.name} dodges the {action.value}!"
                attacker.combo_count = 0
                return result

        # Check hit
        hit_chance = stats.hit_rate
        if attacker.stamina < 20:
            hit_chance *= 0.8  # Exhaustion penalty

        if random.random() > hit_chance:
            result.message = f"{attacker.personality.name}'s {action.value} misses!"
            attacker.combo_count = 0
            return result

        result.success = True

        # Calculate damage
        base_damage = random.randint(stats.damage_min, stats.damage_max)
        damage = base_damage * attacker.stats.power

        # Combo bonus
        combo_bonus = min(attacker.combo_count * cls.COMBO_BONUS_PER_HIT, cls.MAX_COMBO_BONUS)
        damage *= (1 + combo_bonus)
        result.combo_count = attacker.combo_count + 1

        # Critical hit
        crit_chance = cls.BASE_CRIT_CHANCE + stats.crit_bonus
        if random.random() < crit_chance:
            damage *= cls.CRIT_MULTIPLIER
            result.is_critical = True

        # Check for block
        if defender.is_blocking:
            if stats.breaks_block:
                damage *= 0.5  # Still reduced but block is broken
                defender.is_blocking = False
                result.message = f"{attacker.personality.name}'s {action.value} BREAKS through the block!"
            else:
                damage *= (1 - cls.BLOCK_REDUCTION)
                result.was_blocked = True
                result.message = f"{defender.personality.name} blocks the {action.value}!"

        # Counter attack bonus (if attacker just blocked)
        if attacker.is_blocking and attacker.block_timer > 45:
            damage *= cls.COUNTER_BONUS
            result.is_counter = True

        # Apply defense
        damage /= defender.stats.defense

        # Stun check
        if stats.stun_chance > 0 and random.random() < stats.stun_chance:
            result.caused_stun = True
            defender.stun_timer = 45  # 0.75 seconds

        # Apply damage
        result.damage_dealt = int(damage)
        defender.take_damage(result.damage_dealt)
        attacker.combo_count = result.combo_count

        # Build message
        if not result.message:
            msg = f"{attacker.personality.name}'s {action.value}"
            if result.is_critical:
                msg += " CRITICAL HIT!"
            if result.is_counter:
                msg += " (Counter!)"
            msg += f" deals {result.damage_dealt} damage!"
            if result.caused_stun:
                msg += " STUNNED!"
            result.message = msg

        # Check for stagger
        if result.damage_dealt >= cls.STAGGER_THRESHOLD:
            defender.stagger_timer = 30

        return result


# ============================================================================
# SECTION 5: FIGHTER CLASS
# ============================================================================

class Fighter:
    """Represents a fighter in the arena"""

    def __init__(self, personality: Personality, position: str = "left"):
        self.personality = personality
        self.stats = FighterStats()

        # Current state
        self.health = self.stats.max_health
        self.stamina = self.stats.max_stamina

        # Position and movement
        self.position = position
        if position == "left":
            self.x = 350
            self.facing = 1  # Facing right
        else:
            self.x = 930
            self.facing = -1  # Facing left
        self.y = 400
        self.target_x = self.x
        self.velocity_x = 0

        # Combat state
        self.is_blocking = False
        self.is_dodging = False
        self.block_timer = 0
        self.dodge_timer = 0
        self.stun_timer = 0
        self.stagger_timer = 0
        self.combo_count = 0
        self.recent_actions: List[ActionType] = []

        # Animation
        self.animation_state = AnimationState.IDLE
        self.animation_frame = 0
        self.animation_timer = 0
        self.hurt_flash = 0

        # AI
        self.ai: Optional[FighterAI] = None

        # Match stats
        self.total_damage_dealt = 0
        self.total_damage_taken = 0
        self.hits_landed = 0
        self.hits_taken = 0
        self.knockdowns = 0

    def setup_ai(self, provider: Optional[BaseLLMProvider] = None):
        """Setup AI controller"""
        self.ai = FighterAI(self.personality, provider)

    def take_damage(self, amount: int):
        """Take damage"""
        self.health = max(0, self.health - amount)
        self.total_damage_taken += amount
        self.hits_taken += 1
        self.hurt_flash = 15

        if amount >= 20:
            self.animation_state = AnimationState.HIT_HEAVY
        else:
            self.animation_state = AnimationState.HIT_LIGHT
        self.animation_frame = 0

    def use_stamina(self, amount: int):
        """Use stamina"""
        self.stamina = max(0, self.stamina - amount)

    def recover_stamina(self, amount: float):
        """Recover stamina"""
        self.stamina = min(self.stats.max_stamina, self.stamina + amount)

    def is_knocked_out(self) -> bool:
        """Check if fighter is KO'd"""
        return self.health <= 0

    def can_act(self) -> bool:
        """Check if fighter can perform an action"""
        return self.stun_timer <= 0 and self.stagger_timer <= 0

    def update(self, dt: float):
        """Update fighter state"""
        # Timers
        if self.block_timer > 0:
            self.block_timer -= 1
            if self.block_timer <= 0:
                self.is_blocking = False

        if self.dodge_timer > 0:
            self.dodge_timer -= 1
            if self.dodge_timer <= 0:
                self.is_dodging = False

        if self.stun_timer > 0:
            self.stun_timer -= 1

        if self.stagger_timer > 0:
            self.stagger_timer -= 1

        if self.hurt_flash > 0:
            self.hurt_flash -= 1

        # Stamina regeneration
        if not self.is_blocking and not self.is_dodging:
            self.recover_stamina(self.stats.stamina_regen * dt)

        # Position interpolation
        if abs(self.x - self.target_x) > 1:
            self.x += (self.target_x - self.x) * 0.1

        # Animation update
        self.animation_timer += 1
        if self.animation_timer >= 8:
            self.animation_timer = 0
            self.animation_frame += 1

            # Reset to idle after attack animation
            if self.animation_state in [AnimationState.JAB, AnimationState.CROSS,
                                         AnimationState.HOOK, AnimationState.UPPERCUT]:
                if self.animation_frame >= 6:
                    self.animation_state = AnimationState.IDLE
                    self.animation_frame = 0
            elif self.animation_state in [AnimationState.HIT_LIGHT, AnimationState.HIT_HEAVY]:
                if self.animation_frame >= 4:
                    self.animation_state = AnimationState.IDLE
                    self.animation_frame = 0

    def set_animation(self, action: ActionType):
        """Set animation based on action"""
        mapping = {
            ActionType.JAB: AnimationState.JAB,
            ActionType.CROSS: AnimationState.CROSS,
            ActionType.HOOK: AnimationState.HOOK,
            ActionType.UPPERCUT: AnimationState.UPPERCUT,
            ActionType.BLOCK: AnimationState.BLOCK,
            ActionType.DODGE: AnimationState.DODGE,
        }
        self.animation_state = mapping.get(action, AnimationState.IDLE)
        self.animation_frame = 0

    def record_action(self, action: ActionType):
        """Record action in history"""
        self.recent_actions.append(action)
        if len(self.recent_actions) > 10:
            self.recent_actions.pop(0)

    def reset_round(self):
        """Reset for new round"""
        self.health = self.stats.max_health
        self.stamina = self.stats.max_stamina
        self.is_blocking = False
        self.is_dodging = False
        self.block_timer = 0
        self.dodge_timer = 0
        self.stun_timer = 0
        self.stagger_timer = 0
        self.combo_count = 0
        self.animation_state = AnimationState.IDLE

        if self.position == "left":
            self.x = 350
            self.target_x = 350
        else:
            self.x = 930
            self.target_x = 930


# ============================================================================
# SECTION 6: VISUAL SYSTEMS
# ============================================================================

class Particle:
    """A single particle for effects"""

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: Tuple[int, int, int], size: float, lifetime: int):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.gravity = 0.3

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.lifetime -= 1
        self.size *= 0.95

    def is_alive(self) -> bool:
        return self.lifetime > 0 and self.size > 0.5

    def draw(self, screen: pygame.Surface):
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        color = (*self.color[:3], alpha)
        surf = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (int(self.size), int(self.size)), int(self.size))
        screen.blit(surf, (int(self.x - self.size), int(self.y - self.size)))


class ParticleSystem:
    """Manages particle effects"""

    def __init__(self):
        self.particles: List[Particle] = []

    def emit_hit_sparks(self, x: float, y: float, intensity: int = 10):
        """Emit hit spark particles"""
        for _ in range(intensity):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 8)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                random.choice([ORANGE, YELLOW, WHITE]),
                random.uniform(3, 6),
                random.randint(15, 30)
            ))

    def emit_blood(self, x: float, y: float, direction: int, intensity: int = 5):
        """Emit blood particles"""
        for _ in range(intensity):
            self.particles.append(Particle(
                x, y,
                direction * random.uniform(2, 5),
                random.uniform(-3, 0),
                RED,
                random.uniform(2, 4),
                random.randint(20, 40)
            ))

    def emit_sweat(self, x: float, y: float):
        """Emit sweat particles"""
        for _ in range(3):
            self.particles.append(Particle(
                x + random.uniform(-10, 10),
                y + random.uniform(-20, 0),
                random.uniform(-1, 1),
                random.uniform(-2, 0),
                (200, 200, 255),
                random.uniform(1, 3),
                random.randint(20, 35)
            ))

    def update(self):
        for particle in self.particles[:]:
            particle.update()
            if not particle.is_alive():
                self.particles.remove(particle)

    def draw(self, screen: pygame.Surface):
        for particle in self.particles:
            particle.draw(screen)


class DamagePopup:
    """Floating damage number"""

    def __init__(self, x: float, y: float, damage: int, is_crit: bool = False):
        self.x = x
        self.y = y
        self.damage = damage
        self.is_crit = is_crit
        self.lifetime = 60
        self.max_lifetime = 60
        self.vy = -3
        self.scale = 1.5 if is_crit else 1.0

    def update(self):
        self.y += self.vy
        self.vy *= 0.95
        self.lifetime -= 1
        if self.lifetime < 20:
            self.scale *= 0.95

    def is_alive(self) -> bool:
        return self.lifetime > 0

    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        color = GOLD if self.is_crit else WHITE

        text = f"-{self.damage}"
        if self.is_crit:
            text += "!"

        # Create text surface with scaling
        text_surf = font.render(text, True, color)
        scaled_size = (int(text_surf.get_width() * self.scale),
                       int(text_surf.get_height() * self.scale))
        if scaled_size[0] > 0 and scaled_size[1] > 0:
            scaled_surf = pygame.transform.scale(text_surf, scaled_size)
            scaled_surf.set_alpha(alpha)
            screen.blit(scaled_surf,
                       (self.x - scaled_size[0] // 2, self.y - scaled_size[1] // 2))


class ScreenEffects:
    """Screen-wide visual effects"""

    def __init__(self):
        self.shake_intensity = 0
        self.shake_duration = 0
        self.flash_alpha = 0
        self.flash_color = WHITE

    def trigger_shake(self, intensity: int, duration: int):
        self.shake_intensity = intensity
        self.shake_duration = duration

    def trigger_flash(self, color: Tuple[int, int, int], alpha: int):
        self.flash_color = color
        self.flash_alpha = alpha

    def update(self):
        if self.shake_duration > 0:
            self.shake_duration -= 1
            self.shake_intensity *= 0.9

        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 15)

    def get_offset(self) -> Tuple[int, int]:
        if self.shake_duration > 0:
            return (
                random.randint(-int(self.shake_intensity), int(self.shake_intensity)),
                random.randint(-int(self.shake_intensity), int(self.shake_intensity))
            )
        return (0, 0)

    def draw_flash(self, screen: pygame.Surface):
        if self.flash_alpha > 0:
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((*self.flash_color, self.flash_alpha))
            screen.blit(flash_surf, (0, 0))


class SpriteRenderer:
    """Renders fighter sprites procedurally"""

    @staticmethod
    def draw_fighter(screen: pygame.Surface, fighter: Fighter, offset: Tuple[int, int] = (0, 0)):
        """Draw a fighter sprite"""
        x = fighter.x + offset[0]
        y = fighter.y + offset[1]
        facing = fighter.facing
        color = fighter.personality.color
        secondary = fighter.personality.secondary_color

        # Flash when hurt
        if fighter.hurt_flash > 0 and fighter.hurt_flash % 4 < 2:
            color = WHITE
            secondary = LIGHT_GRAY

        # Body dimensions based on animation
        body_offset_x = 0
        arm_angle = 0

        if fighter.animation_state == AnimationState.JAB:
            arm_angle = -30 * facing
            body_offset_x = 10 * facing * min(fighter.animation_frame, 3)
        elif fighter.animation_state == AnimationState.CROSS:
            arm_angle = -45 * facing
            body_offset_x = 15 * facing * min(fighter.animation_frame, 4)
        elif fighter.animation_state == AnimationState.HOOK:
            arm_angle = 60 * facing if fighter.animation_frame < 3 else -60 * facing
            body_offset_x = 20 * facing * min(fighter.animation_frame, 4)
        elif fighter.animation_state == AnimationState.UPPERCUT:
            arm_angle = -90
            body_offset_x = 10 * facing
        elif fighter.animation_state == AnimationState.BLOCK:
            arm_angle = 45
        elif fighter.animation_state == AnimationState.DODGE:
            body_offset_x = -30 * facing
        elif fighter.animation_state in [AnimationState.HIT_LIGHT, AnimationState.HIT_HEAVY]:
            body_offset_x = -10 * facing

        draw_x = x + body_offset_x

        # Legs
        leg_spread = 15
        pygame.draw.line(screen, secondary,
                        (draw_x, y + 20), (draw_x - leg_spread, y + 60), 8)
        pygame.draw.line(screen, secondary,
                        (draw_x, y + 20), (draw_x + leg_spread, y + 60), 8)

        # Feet
        pygame.draw.ellipse(screen, BLACK,
                           (draw_x - leg_spread - 8, y + 55, 16, 8))
        pygame.draw.ellipse(screen, BLACK,
                           (draw_x + leg_spread - 8, y + 55, 16, 8))

        # Body
        pygame.draw.ellipse(screen, color,
                           (draw_x - 20, y - 30, 40, 55))

        # Arms
        arm_base_x = draw_x + (15 * facing)
        arm_base_y = y - 15

        # Back arm
        back_arm_x = draw_x - (10 * facing)
        pygame.draw.line(screen, secondary,
                        (back_arm_x, arm_base_y),
                        (back_arm_x - 20 * facing, arm_base_y + 15), 6)
        pygame.draw.circle(screen, BROWN,
                          (int(back_arm_x - 20 * facing), int(arm_base_y + 15)), 8)

        # Front arm (punching arm)
        arm_end_x = arm_base_x + (40 + body_offset_x * 0.5) * facing
        arm_end_y = arm_base_y + math.sin(math.radians(arm_angle)) * 30
        pygame.draw.line(screen, secondary,
                        (arm_base_x, arm_base_y),
                        (arm_end_x, arm_end_y), 7)

        # Glove
        glove_color = color
        if fighter.animation_state in [AnimationState.JAB, AnimationState.CROSS,
                                        AnimationState.HOOK, AnimationState.UPPERCUT]:
            glove_color = YELLOW if fighter.animation_frame > 2 else color
        pygame.draw.circle(screen, glove_color, (int(arm_end_x), int(arm_end_y)), 12)
        pygame.draw.circle(screen, WHITE, (int(arm_end_x), int(arm_end_y)), 12, 2)

        # Head
        head_x = draw_x + (5 * facing)
        head_y = y - 50
        pygame.draw.circle(screen, (255, 220, 180), (int(head_x), int(head_y)), 22)

        # Face direction indicator
        eye_x = head_x + (8 * facing)
        pygame.draw.circle(screen, BLACK, (int(eye_x), int(head_y - 3)), 3)

        # Health indicator above head
        health_pct = fighter.health / fighter.stats.max_health
        indicator_color = GREEN if health_pct > 0.5 else YELLOW if health_pct > 0.25 else RED
        pygame.draw.circle(screen, indicator_color, (int(head_x), int(head_y - 35)), 5)

        # Blocking indicator
        if fighter.is_blocking:
            pygame.draw.arc(screen, CYAN,
                           (draw_x - 35, y - 60, 70, 80),
                           0 if facing > 0 else math.pi,
                           math.pi if facing > 0 else math.pi * 2, 4)

        # Stun indicator
        if fighter.stun_timer > 0:
            for i in range(3):
                star_x = head_x + math.cos(time.time() * 5 + i * 2) * 25
                star_y = head_y - 40 + math.sin(time.time() * 3 + i) * 5
                pygame.draw.circle(screen, YELLOW, (int(star_x), int(star_y)), 4)


# ============================================================================
# SECTION 7: UI COMPONENTS
# ============================================================================

class HealthBar:
    """Animated health bar"""

    def __init__(self, x: int, y: int, width: int, height: int, align: str = "left"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.align = align
        self.displayed_value = 100
        self.target_value = 100

    def update(self, current: float, maximum: float):
        self.target_value = (current / maximum) * 100
        # Smooth interpolation
        self.displayed_value += (self.target_value - self.displayed_value) * 0.1

    def draw(self, screen: pygame.Surface):
        # Background
        pygame.draw.rect(screen, DARK_GRAY, (self.x, self.y, self.width, self.height))

        # Health fill
        fill_width = int((self.displayed_value / 100) * (self.width - 4))

        # Color gradient based on health
        if self.displayed_value > 60:
            color = GREEN
        elif self.displayed_value > 30:
            color = YELLOW
        else:
            color = RED

        if self.align == "left":
            fill_x = self.x + 2
        else:
            fill_x = self.x + self.width - 2 - fill_width

        if fill_width > 0:
            pygame.draw.rect(screen, color,
                           (fill_x, self.y + 2, fill_width, self.height - 4))

        # Border
        pygame.draw.rect(screen, WHITE, (self.x, self.y, self.width, self.height), 2)


class StaminaBar:
    """Stamina bar display"""

    def __init__(self, x: int, y: int, width: int, height: int, align: str = "left"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.align = align
        self.displayed_value = 100

    def update(self, current: float, maximum: float):
        target = (current / maximum) * 100
        self.displayed_value += (target - self.displayed_value) * 0.15

    def draw(self, screen: pygame.Surface):
        pygame.draw.rect(screen, DARK_GRAY, (self.x, self.y, self.width, self.height))

        fill_width = int((self.displayed_value / 100) * (self.width - 4))

        if self.align == "left":
            fill_x = self.x + 2
        else:
            fill_x = self.x + self.width - 2 - fill_width

        if fill_width > 0:
            pygame.draw.rect(screen, GOLD,
                           (fill_x, self.y + 2, fill_width, self.height - 4))

        pygame.draw.rect(screen, WHITE, (self.x, self.y, self.width, self.height), 2)


class TextBox:
    """Scrolling text display for AI thoughts and actions"""

    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.messages: List[Dict[str, Any]] = []
        self.max_messages = 6
        self.typing_text = ""
        self.typing_index = 0
        self.typing_speed = 2
        self.typing_timer = 0

    def add_message(self, text: str, color: Tuple[int, int, int] = WHITE,
                    typing: bool = False):
        """Add a message to the text box"""
        if typing:
            self.typing_text = text
            self.typing_index = 0
            self.messages.append({"text": "", "color": color, "typing": True})
        else:
            self.messages.append({"text": text, "color": color, "typing": False})

        while len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def update(self):
        """Update typing animation"""
        if self.typing_text and self.typing_index < len(self.typing_text):
            self.typing_timer += 1
            if self.typing_timer >= self.typing_speed:
                self.typing_timer = 0
                self.typing_index += 1
                # Update the last message
                if self.messages and self.messages[-1].get("typing"):
                    self.messages[-1]["text"] = self.typing_text[:self.typing_index]

    def is_typing_complete(self) -> bool:
        return self.typing_index >= len(self.typing_text)

    def skip_typing(self):
        """Skip to end of typing animation"""
        if self.typing_text and self.messages:
            self.typing_index = len(self.typing_text)
            if self.messages[-1].get("typing"):
                self.messages[-1]["text"] = self.typing_text
                self.messages[-1]["typing"] = False

    def clear(self):
        self.messages.clear()
        self.typing_text = ""
        self.typing_index = 0

    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        # Background
        bg_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        bg_surf.fill((20, 20, 30, 220))
        screen.blit(bg_surf, (self.x, self.y))

        # Border
        pygame.draw.rect(screen, CYAN, (self.x, self.y, self.width, self.height), 2)

        # Title
        title = font.render("AI THOUGHTS & ACTIONS", True, CYAN)
        screen.blit(title, (self.x + 10, self.y + 5))

        # Messages
        y_offset = 30
        line_height = 22

        for msg in self.messages:
            # Word wrap
            words = msg["text"].split()
            lines = []
            current_line = ""

            for word in words:
                test_line = current_line + " " + word if current_line else word
                if font.size(test_line)[0] < self.width - 20:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            for line in lines:
                if y_offset + line_height < self.height - 5:
                    text_surf = font.render(line, True, msg["color"])
                    screen.blit(text_surf, (self.x + 10, self.y + y_offset))
                    y_offset += line_height

            y_offset += 5  # Extra space between messages


class Button:
    """Clickable button"""

    def __init__(self, x: int, y: int, width: int, height: int, text: str,
                 color: Tuple[int, int, int] = BLUE):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = tuple(min(c + 40, 255) for c in color)
        self.is_hovered = False

    def update(self, mouse_pos: Tuple[int, int]):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos: Tuple[int, int], mouse_click: bool) -> bool:
        return self.rect.collidepoint(mouse_pos) and mouse_click

    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, WHITE, self.rect, 2)

        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)


class RingRenderer:
    """Renders the boxing ring"""

    @staticmethod
    def draw(screen: pygame.Surface, offset: Tuple[int, int] = (0, 0)):
        ox, oy = offset

        # Ring area
        ring_rect = pygame.Rect(200 + ox, 280 + oy, 880, 200)

        # Canvas (floor)
        pygame.draw.rect(screen, RING_CANVAS, ring_rect)

        # Ring border/apron
        pygame.draw.rect(screen, BROWN, ring_rect, 8)

        # Corner posts
        post_positions = [
            (200 + ox, 280 + oy),
            (1080 + ox, 280 + oy),
            (200 + ox, 480 + oy),
            (1080 + ox, 480 + oy)
        ]
        for px, py in post_positions:
            pygame.draw.rect(screen, RING_POST, (px - 10, py - 40, 20, 80))
            pygame.draw.circle(screen, GRAY, (px, py - 40), 12)

        # Ropes
        rope_colors = [RING_ROPE_RED, RING_ROPE_WHITE, RING_ROPE_BLUE]
        rope_heights = [295, 330, 365]

        for color, ry in zip(rope_colors, rope_heights):
            # Top ropes
            pygame.draw.line(screen, color,
                           (210 + ox, ry + oy), (1070 + ox, ry + oy), 4)
            # Bottom ropes
            pygame.draw.line(screen, color,
                           (210 + ox, ry + 100 + oy), (1070 + ox, ry + 100 + oy), 4)


# ============================================================================
# SECTION 8: GAME ENGINE
# ============================================================================

class Game:
    """Main game engine"""

    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("SYNTAX BRAWLERS - LLM Arena Fighting")

        self.clock = pygame.time.Clock()
        self.running = True

        # Fonts
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)

        # Game state
        self.state = GameState.MAIN_MENU
        self.previous_state = None

        # Fighters
        self.fighter1: Optional[Fighter] = None
        self.fighter2: Optional[Fighter] = None
        self.current_turn = 1  # 1 or 2

        # Round management
        self.round_number = 1
        self.max_rounds = 3
        self.round_time = 180  # seconds
        self.round_timer = self.round_time * FPS
        self.rounds_won = {1: 0, 2: 0}

        # Visual systems
        self.particles = ParticleSystem()
        self.screen_effects = ScreenEffects()
        self.damage_popups: List[DamagePopup] = []

        # UI components
        self.health_bar1 = HealthBar(50, 100, 300, 25, "left")
        self.health_bar2 = HealthBar(930, 100, 300, 25, "right")
        self.stamina_bar1 = StaminaBar(50, 130, 250, 15, "left")
        self.stamina_bar2 = StaminaBar(980, 130, 250, 15, "right")
        self.text_box = TextBox(50, 520, 1180, 150)

        # Menu buttons
        self.menu_buttons = [
            Button(490, 300, 300, 50, "NEW FIGHT", BLUE),
            Button(490, 370, 300, 50, "SETTINGS", GRAY),
            Button(490, 440, 300, 50, "QUIT", RED),
        ]

        # Character select buttons
        self.char_buttons = []
        for i, ptype in enumerate(PersonalityType):
            self.char_buttons.append(
                Button(100 + (i % 2) * 300, 200 + (i // 2) * 150, 250, 120,
                       PERSONALITIES[ptype].name, PERSONALITIES[ptype].color)
            )

        # Turn management
        self.turn_state = "waiting"  # waiting, thinking, acting, result
        self.turn_timer = 0
        self.current_response: Optional[LLMResponse] = None
        self.current_result: Optional[ActionResult] = None

        # LLM providers
        self.llm_provider1: Optional[BaseLLMProvider] = None
        self.llm_provider2: Optional[BaseLLMProvider] = None
        self._setup_llm_providers()

        # Selection state
        self.selected_personality1: Optional[PersonalityType] = None
        self.selected_personality2: Optional[PersonalityType] = None
        self.selection_stage = 1  # 1 = selecting fighter 1, 2 = selecting fighter 2

    def _setup_llm_providers(self):
        """Setup available LLM providers"""
        # Try OpenRouter first (DeepSeek v3.2)
        openrouter = OpenRouterProvider("deepseek/deepseek-v3.2")
        if openrouter.is_available():
            self.llm_provider1 = openrouter
            self.llm_provider2 = openrouter
            print("Using OpenRouter API with DeepSeek v3.2")
            return

        # Try Anthropic
        anthropic = AnthropicProvider()
        if anthropic.is_available():
            self.llm_provider1 = anthropic
            self.llm_provider2 = anthropic
            print("Using Anthropic Claude API")
            return

        # Try OpenAI
        openai = OpenAIProvider()
        if openai.is_available():
            self.llm_provider1 = openai
            self.llm_provider2 = openai
            print("Using OpenAI API")
            return

        # Try Ollama
        ollama = OllamaProvider()
        if ollama.is_available():
            self.llm_provider1 = ollama
            self.llm_provider2 = ollama
            print("Using Ollama local LLM")
            return

        print("No LLM provider available - using fallback AI")

    def run(self):
        """Main game loop"""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            self._handle_events()
            self._update(dt)
            self._render()

        pygame.quit()

    def _handle_events(self):
        """Handle input events"""
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_click = True

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameState.FIGHTING:
                        self.state = GameState.PAUSED
                    elif self.state == GameState.PAUSED:
                        self.state = GameState.FIGHTING
                    elif self.state != GameState.MAIN_MENU:
                        self.state = GameState.MAIN_MENU

                elif event.key == pygame.K_SPACE:
                    if self.state == GameState.FIGHTING:
                        self.text_box.skip_typing()

                elif event.key == pygame.K_r:
                    if self.state in [GameState.FIGHTING, GameState.MATCH_END]:
                        self._start_new_match()

        # Button updates
        if self.state == GameState.MAIN_MENU:
            for btn in self.menu_buttons:
                btn.update(mouse_pos)
                if btn.is_clicked(mouse_pos, mouse_click):
                    if btn.text == "NEW FIGHT":
                        self.state = GameState.CHARACTER_SELECT
                        self.selection_stage = 1
                    elif btn.text == "QUIT":
                        self.running = False

        elif self.state == GameState.CHARACTER_SELECT:
            for i, btn in enumerate(self.char_buttons):
                btn.update(mouse_pos)
                if btn.is_clicked(mouse_pos, mouse_click):
                    ptype = list(PersonalityType)[i]
                    if self.selection_stage == 1:
                        self.selected_personality1 = ptype
                        self.selection_stage = 2
                    else:
                        self.selected_personality2 = ptype
                        self._start_new_match()

    def _update(self, dt: float):
        """Update game state"""
        # Update visual systems
        self.particles.update()
        self.screen_effects.update()
        self.text_box.update()

        for popup in self.damage_popups[:]:
            popup.update()
            if not popup.is_alive():
                self.damage_popups.remove(popup)

        if self.state == GameState.FIGHTING:
            self._update_fight(dt)
        elif self.state == GameState.ROUND_END:
            self._update_round_end(dt)
        elif self.state == GameState.MATCH_END:
            pass  # Wait for input

    def _update_fight(self, dt: float):
        """Update fight logic"""
        if not self.fighter1 or not self.fighter2:
            return

        # Update fighters
        self.fighter1.update(dt)
        self.fighter2.update(dt)

        # Update UI
        self.health_bar1.update(self.fighter1.health, self.fighter1.stats.max_health)
        self.health_bar2.update(self.fighter2.health, self.fighter2.stats.max_health)
        self.stamina_bar1.update(self.fighter1.stamina, self.fighter1.stats.max_stamina)
        self.stamina_bar2.update(self.fighter2.stamina, self.fighter2.stats.max_stamina)

        # Round timer
        self.round_timer -= 1
        if self.round_timer <= 0:
            self._end_round()
            return

        # Check for KO
        if self.fighter1.is_knocked_out():
            self._handle_knockout(2)
            return
        if self.fighter2.is_knocked_out():
            self._handle_knockout(1)
            return

        # Turn management
        self._update_turn()

    def _update_turn(self):
        """Update turn-based combat"""
        attacker = self.fighter1 if self.current_turn == 1 else self.fighter2
        defender = self.fighter2 if self.current_turn == 1 else self.fighter1

        if self.turn_state == "waiting":
            if attacker.can_act():
                self.turn_state = "thinking"
                self.turn_timer = 0
                # Start AI decision
                if attacker.ai:
                    asyncio.get_event_loop().run_until_complete(
                        self._get_ai_decision(attacker, defender)
                    )

        elif self.turn_state == "thinking":
            self.turn_timer += 1
            if self.turn_timer > 30 and self.text_box.is_typing_complete():
                self.turn_state = "acting"
                self.turn_timer = 0

        elif self.turn_state == "acting":
            self.turn_timer += 1
            if self.turn_timer == 1 and self.current_response:
                # Execute action
                action = self.current_response.action
                attacker.set_animation(action)
                attacker.record_action(action)
                self.current_result = CombatEngine.resolve_action(
                    attacker, defender, action
                )

                # Visual feedback
                if self.current_result.success and self.current_result.damage_dealt > 0:
                    self.particles.emit_hit_sparks(defender.x, defender.y - 30,
                                                   self.current_result.damage_dealt // 2)
                    self.screen_effects.trigger_shake(
                        self.current_result.damage_dealt // 5, 10
                    )
                    if self.current_result.is_critical:
                        self.screen_effects.trigger_flash(WHITE, 100)

                    self.damage_popups.append(DamagePopup(
                        defender.x, defender.y - 50,
                        self.current_result.damage_dealt,
                        self.current_result.is_critical
                    ))

                # Add result message
                color = GREEN if self.current_result.success else GRAY
                self.text_box.add_message(self.current_result.message, color)

            if self.turn_timer > 60:
                self.turn_state = "result"
                self.turn_timer = 0

        elif self.turn_state == "result":
            self.turn_timer += 1
            if self.turn_timer > 30:
                # Switch turns
                self.current_turn = 2 if self.current_turn == 1 else 1
                self.turn_state = "waiting"
                self.current_response = None
                self.current_result = None

    async def _get_ai_decision(self, attacker: Fighter, defender: Fighter):
        """Get decision from AI"""
        if attacker.ai:
            self.current_response = await attacker.ai.decide(
                attacker, defender, self.round_number
            )

            # Display thinking
            name = attacker.personality.name
            color = attacker.personality.color

            thinking_msg = f"{name} [thinking]: \"{self.current_response.thinking}\""
            self.text_box.add_message(thinking_msg, LIGHT_GRAY, typing=True)

            # Queue trash talk (will be added after thinking completes)
            trash_msg = f"{name}: \"{self.current_response.trash_talk}\""
            self.text_box.add_message(trash_msg, color)

    def _handle_knockout(self, winner: int):
        """Handle knockout"""
        self.rounds_won[winner] += 1
        loser = self.fighter1 if winner == 2 else self.fighter2
        loser.animation_state = AnimationState.KNOCKDOWN
        loser.knockdowns += 1

        self.text_box.add_message(f"KNOCKOUT! {loser.personality.name} is down!", RED)
        self.screen_effects.trigger_shake(15, 30)
        self.screen_effects.trigger_flash(WHITE, 150)

        self._end_round()

    def _end_round(self):
        """End current round"""
        # Determine round winner if not KO
        if self.fighter1 and self.fighter2:
            if self.fighter1.health > self.fighter2.health:
                self.rounds_won[1] += 1
            elif self.fighter2.health > self.fighter1.health:
                self.rounds_won[2] += 1

        self.state = GameState.ROUND_END
        self.turn_timer = 0

    def _update_round_end(self, dt: float):
        """Update round end state"""
        self.turn_timer += 1

        if self.turn_timer > 180:  # 3 seconds
            # Check for match end
            if self.rounds_won[1] > self.max_rounds // 2:
                self.state = GameState.MATCH_END
            elif self.rounds_won[2] > self.max_rounds // 2:
                self.state = GameState.MATCH_END
            elif self.round_number >= self.max_rounds:
                self.state = GameState.MATCH_END
            else:
                # Next round
                self.round_number += 1
                self.round_timer = self.round_time * FPS
                if self.fighter1:
                    self.fighter1.reset_round()
                if self.fighter2:
                    self.fighter2.reset_round()
                self.state = GameState.FIGHTING
                self.text_box.clear()
                self.text_box.add_message(f"ROUND {self.round_number}!", GOLD)

    def _start_new_match(self):
        """Start a new match"""
        if self.selected_personality1 and self.selected_personality2:
            p1 = PERSONALITIES[self.selected_personality1]
            p2 = PERSONALITIES[self.selected_personality2]

            self.fighter1 = Fighter(p1, "left")
            self.fighter2 = Fighter(p2, "right")

            self.fighter1.setup_ai(self.llm_provider1)
            self.fighter2.setup_ai(self.llm_provider2)

            self.round_number = 1
            self.round_timer = self.round_time * FPS
            self.rounds_won = {1: 0, 2: 0}
            self.current_turn = 1
            self.turn_state = "waiting"

            self.text_box.clear()
            self.text_box.add_message("FIGHT!", GOLD)
            self.text_box.add_message(f"{p1.name} vs {p2.name}", WHITE)

            self.state = GameState.FIGHTING

    def _render(self):
        """Render the game"""
        # Get screen shake offset
        offset = self.screen_effects.get_offset()

        # Clear screen
        self.screen.fill((30, 30, 40))

        if self.state == GameState.MAIN_MENU:
            self._render_menu()
        elif self.state == GameState.CHARACTER_SELECT:
            self._render_character_select()
        elif self.state in [GameState.FIGHTING, GameState.ROUND_END,
                            GameState.MATCH_END, GameState.PAUSED]:
            self._render_fight(offset)

        # Screen flash
        self.screen_effects.draw_flash(self.screen)

        pygame.display.flip()

    def _render_menu(self):
        """Render main menu"""
        # Title
        title = self.font_large.render("SYNTAX BRAWLERS", True, GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)

        subtitle = self.font_medium.render("LLM Arena Fighting", True, CYAN)
        sub_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 200))
        self.screen.blit(subtitle, sub_rect)

        # Buttons
        for btn in self.menu_buttons:
            btn.draw(self.screen, self.font_medium)

        # Provider status
        if self.llm_provider1:
            status = f"LLM: {type(self.llm_provider1).__name__}"
            color = GREEN
        else:
            status = "LLM: Fallback AI (no API key)"
            color = YELLOW
        status_text = self.font_small.render(status, True, color)
        self.screen.blit(status_text, (20, SCREEN_HEIGHT - 30))

    def _render_character_select(self):
        """Render character selection"""
        title = self.font_large.render("SELECT FIGHTERS", True, GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title, title_rect)

        # Selection instruction
        if self.selection_stage == 1:
            instr = "Select Fighter 1 (Left Corner)"
            color = CYAN
        else:
            instr = "Select Fighter 2 (Right Corner)"
            color = ORANGE

        instr_text = self.font_medium.render(instr, True, color)
        instr_rect = instr_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(instr_text, instr_rect)

        # Character buttons with descriptions
        for i, btn in enumerate(self.char_buttons):
            btn.draw(self.screen, self.font_medium)

            # Show personality info
            ptype = list(PersonalityType)[i]
            p = PERSONALITIES[ptype]

            # Description under button
            desc = self.font_small.render(p.fighting_style[:40] + "...", True, LIGHT_GRAY)
            self.screen.blit(desc, (btn.rect.x, btn.rect.bottom + 5))

        # Show selected fighter 1
        if self.selected_personality1:
            p1 = PERSONALITIES[self.selected_personality1]
            sel_text = self.font_medium.render(f"Fighter 1: {p1.name}", True, p1.color)
            self.screen.blit(sel_text, (50, 550))

    def _render_fight(self, offset: Tuple[int, int]):
        """Render the fight scene"""
        # Background
        pygame.draw.rect(self.screen, (20, 20, 30), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

        # Ring
        RingRenderer.draw(self.screen, offset)

        # Fighters
        if self.fighter1:
            SpriteRenderer.draw_fighter(self.screen, self.fighter1, offset)
        if self.fighter2:
            SpriteRenderer.draw_fighter(self.screen, self.fighter2, offset)

        # Particles
        self.particles.draw(self.screen)

        # Damage popups
        for popup in self.damage_popups:
            popup.draw(self.screen, self.font_medium)

        # UI - Header
        header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 80)
        pygame.draw.rect(self.screen, (20, 20, 40), header_rect)
        pygame.draw.line(self.screen, CYAN, (0, 80), (SCREEN_WIDTH, 80), 2)

        # Round info
        round_text = self.font_medium.render(f"ROUND {self.round_number}", True, WHITE)
        self.screen.blit(round_text, (50, 20))

        # Timer
        time_secs = self.round_timer // FPS
        mins = time_secs // 60
        secs = time_secs % 60
        timer_text = self.font_large.render(f"{mins:02d}:{secs:02d}", True, GOLD)
        timer_rect = timer_text.get_rect(center=(SCREEN_WIDTH // 2, 40))
        self.screen.blit(timer_text, timer_rect)

        # Title
        title = self.font_medium.render("SYNTAX BRAWLERS", True, CYAN)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 65))
        self.screen.blit(title, title_rect)

        # Fighter info panels
        if self.fighter1:
            self._render_fighter_panel(self.fighter1, 50, 95, "left")
        if self.fighter2:
            self._render_fighter_panel(self.fighter2, 930, 95, "right")

        # Health and stamina bars
        self.health_bar1.draw(self.screen)
        self.health_bar2.draw(self.screen)
        self.stamina_bar1.draw(self.screen)
        self.stamina_bar2.draw(self.screen)

        # Score
        score_text = self.font_medium.render(
            f"{self.rounds_won[1]} - {self.rounds_won[2]}", True, WHITE
        )
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, 15))
        self.screen.blit(score_text, score_rect)

        # Text box
        self.text_box.draw(self.screen, self.font_small)

        # Footer controls
        footer_rect = pygame.Rect(0, SCREEN_HEIGHT - 30, SCREEN_WIDTH, 30)
        pygame.draw.rect(self.screen, (20, 20, 40), footer_rect)
        controls = "[ESC] Pause  |  [R] Restart  |  [SPACE] Skip Text"
        controls_text = self.font_small.render(controls, True, GRAY)
        controls_rect = controls_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 15))
        self.screen.blit(controls_text, controls_rect)

        # Paused overlay
        if self.state == GameState.PAUSED:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            pause_text = self.font_large.render("PAUSED", True, WHITE)
            pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(pause_text, pause_rect)

            resume = self.font_medium.render("Press ESC to resume", True, GRAY)
            resume_rect = resume.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
            self.screen.blit(resume, resume_rect)

        # Round end overlay
        elif self.state == GameState.ROUND_END:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))

            round_end = self.font_large.render(f"ROUND {self.round_number} OVER", True, GOLD)
            round_rect = round_end.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(round_end, round_rect)

        # Match end overlay
        elif self.state == GameState.MATCH_END:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0, 0))

            # Determine winner
            if self.rounds_won[1] > self.rounds_won[2]:
                winner = self.fighter1.personality.name if self.fighter1 else "Fighter 1"
                color = self.fighter1.personality.color if self.fighter1 else BLUE
            elif self.rounds_won[2] > self.rounds_won[1]:
                winner = self.fighter2.personality.name if self.fighter2 else "Fighter 2"
                color = self.fighter2.personality.color if self.fighter2 else RED
            else:
                winner = "DRAW"
                color = GRAY

            win_text = self.font_large.render("WINNER!", True, GOLD)
            win_rect = win_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
            self.screen.blit(win_text, win_rect)

            name_text = self.font_large.render(winner, True, color)
            name_rect = name_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
            self.screen.blit(name_text, name_rect)

            score_text = self.font_medium.render(
                f"Final Score: {self.rounds_won[1]} - {self.rounds_won[2]}", True, WHITE
            )
            score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80))
            self.screen.blit(score_text, score_rect)

            restart = self.font_medium.render("Press R to restart or ESC for menu", True, GRAY)
            restart_rect = restart.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 130))
            self.screen.blit(restart, restart_rect)

    def _render_fighter_panel(self, fighter: Fighter, x: int, y: int, align: str):
        """Render fighter info panel"""
        color = fighter.personality.color
        name = fighter.personality.name

        # Name
        name_text = self.font_small.render(name, True, color)
        if align == "left":
            self.screen.blit(name_text, (x, y))
        else:
            name_rect = name_text.get_rect(right=x + 300)
            name_rect.top = y
            self.screen.blit(name_text, name_rect)

        # Combo indicator
        if fighter.combo_count > 1:
            combo_text = self.font_small.render(f"COMBO x{fighter.combo_count}", True, GOLD)
            if align == "left":
                self.screen.blit(combo_text, (x, y + 55))
            else:
                combo_rect = combo_text.get_rect(right=x + 300)
                combo_rect.top = y + 55
                self.screen.blit(combo_text, combo_rect)

        # Status
        status = "READY"
        status_color = GREEN
        if fighter.stun_timer > 0:
            status = "STUNNED"
            status_color = RED
        elif fighter.is_blocking:
            status = "BLOCKING"
            status_color = CYAN
        elif fighter.is_dodging:
            status = "DODGING"
            status_color = PURPLE
        elif fighter.stamina < 20:
            status = "EXHAUSTED"
            status_color = YELLOW

        status_text = self.font_small.render(f"[{status}]", True, status_color)
        if align == "left":
            self.screen.blit(status_text, (x + 200, y))
        else:
            status_rect = status_text.get_rect(right=x + 100)
            status_rect.top = y
            self.screen.blit(status_text, status_rect)


# ============================================================================
# SECTION 9: MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    print("=" * 60)
    print("SYNTAX BRAWLERS - LLM Arena Fighting Game")
    print("=" * 60)
    print()
    print("Controls:")
    print("  ESC   - Pause / Menu")
    print("  R     - Restart match")
    print("  SPACE - Skip text animation")
    print()
    print("LLM Configuration:")
    print("  Set OPENROUTER_API_KEY for DeepSeek v3.2 (recommended)")
    print("  Or ANTHROPIC_API_KEY / OPENAI_API_KEY")
    print("  Or run Ollama locally at http://localhost:11434")
    print()

    # Create event loop for async operations (Python 3.10+ compatible)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    game = Game()
    game.run()


if __name__ == "__main__":
    main()
