"""
AI Personality System
=====================
Definisi personality dan behavior patterns untuk AI fighters.
"""

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import random
import sys
sys.path.insert(0, '..')

from config import PersonalityType, ActionType


@dataclass
class PersonalityTraits:
    """Traits untuk personality"""
    aggression: float      # 0.0 - 1.0 (tendency to attack)
    patience: float        # 0.0 - 1.0 (willingness to wait)
    risk_tolerance: float  # 0.0 - 1.0 (willingness to take risks)
    adaptability: float    # 0.0 - 1.0 (ability to change tactics)
    trash_talk_freq: float # 0.0 - 1.0 (how often to trash talk)

    # Action preferences (weights)
    jab_weight: float = 1.0
    cross_weight: float = 1.0
    hook_weight: float = 1.0
    uppercut_weight: float = 1.0
    block_weight: float = 1.0
    dodge_weight: float = 1.0


# Predefined personalities
PERSONALITIES: Dict[str, PersonalityTraits] = {
    # The Destroyer - Aggressive, high damage
    'destroyer': PersonalityTraits(
        aggression=0.9,
        patience=0.2,
        risk_tolerance=0.8,
        adaptability=0.4,
        trash_talk_freq=0.9,
        jab_weight=0.6,
        cross_weight=1.2,
        hook_weight=1.5,
        uppercut_weight=1.3,
        block_weight=0.3,
        dodge_weight=0.4
    ),

    # The Tactician - Calculated, efficient
    'tactician': PersonalityTraits(
        aggression=0.5,
        patience=0.8,
        risk_tolerance=0.3,
        adaptability=0.9,
        trash_talk_freq=0.3,
        jab_weight=1.4,
        cross_weight=1.1,
        hook_weight=0.7,
        uppercut_weight=0.5,
        block_weight=1.2,
        dodge_weight=1.0
    ),

    # The Ghost - Evasive, counter-focused
    'ghost': PersonalityTraits(
        aggression=0.3,
        patience=0.9,
        risk_tolerance=0.2,
        adaptability=0.7,
        trash_talk_freq=0.5,
        jab_weight=1.2,
        cross_weight=0.8,
        hook_weight=0.6,
        uppercut_weight=0.9,
        block_weight=0.8,
        dodge_weight=1.5
    ),

    # The Wildcard - Unpredictable
    'wildcard': PersonalityTraits(
        aggression=0.6,
        patience=0.5,
        risk_tolerance=0.9,
        adaptability=0.3,
        trash_talk_freq=1.0,
        jab_weight=1.0,
        cross_weight=1.0,
        hook_weight=1.2,
        uppercut_weight=1.3,
        block_weight=0.8,
        dodge_weight=1.0
    ),

    # Balanced - Default
    'balanced': PersonalityTraits(
        aggression=0.5,
        patience=0.5,
        risk_tolerance=0.5,
        adaptability=0.5,
        trash_talk_freq=0.5,
        jab_weight=1.0,
        cross_weight=1.0,
        hook_weight=1.0,
        uppercut_weight=1.0,
        block_weight=1.0,
        dodge_weight=1.0
    ),

    # Aggressive - For AI that tends to attack
    'aggressive': PersonalityTraits(
        aggression=0.8,
        patience=0.3,
        risk_tolerance=0.7,
        adaptability=0.5,
        trash_talk_freq=0.7,
        jab_weight=0.8,
        cross_weight=1.3,
        hook_weight=1.4,
        uppercut_weight=1.2,
        block_weight=0.4,
        dodge_weight=0.5
    ),

    # Defensive - For AI that tends to block/dodge
    'defensive': PersonalityTraits(
        aggression=0.3,
        patience=0.8,
        risk_tolerance=0.2,
        adaptability=0.6,
        trash_talk_freq=0.4,
        jab_weight=1.3,
        cross_weight=0.8,
        hook_weight=0.6,
        uppercut_weight=0.7,
        block_weight=1.4,
        dodge_weight=1.3
    ),
}

# Trash talk templates per personality
TRASH_TALK: Dict[str, List[str]] = {
    'destroyer': [
        "Feel the pain!",
        "You're going DOWN!",
        "Is that all you got?",
        "Too slow!",
        "BOOM! Did that hurt?",
        "I'm just getting started!",
        "You call that a punch?",
        "Stay down!",
    ],
    'tactician': [
        "Predictable.",
        "I see your pattern.",
        "Calculate that.",
        "As expected.",
        "Your move was... obvious.",
        "Efficiency wins.",
        "Think faster.",
        "Strategic error.",
    ],
    'ghost': [
        "Can't touch this.",
        "I'm not even here.",
        "Like shadow...",
        "Too slow to catch me.",
        "Now you see me...",
        "Missed again.",
        "Float like a butterfly...",
        "Patience...",
    ],
    'wildcard': [
        "SURPRISE!",
        "Bet you didn't see that coming!",
        "YOLO!",
        "What's next? Even I don't know!",
        "Chaos is my friend!",
        "Random? Or genius?",
        "WILDCARD BABY!",
        "Expect the unexpected!",
    ],
    'balanced': [
        "Good fight.",
        "Nice try.",
        "Keep it up.",
        "Not bad.",
        "Interesting move.",
        "Let's go!",
        "Show me what you got.",
        "Round two!",
    ],
    'aggressive': [
        "ATTACK!",
        "No mercy!",
        "Coming at you!",
        "Can't stop this!",
        "Take THIS!",
        "Non-stop assault!",
        "Keep your guard up!",
        "Pressure!",
    ],
    'defensive': [
        "Nice try.",
        "Blocked.",
        "Saw that coming.",
        "Patience pays off.",
        "Your turn.",
        "Counter time.",
        "Wait for it...",
        "Defense wins.",
    ],
}


class PersonalityManager:
    """
    Manages personality-based decision making.
    """

    def __init__(self, personality_name: str = 'balanced'):
        self.personality_name = personality_name.lower()
        self.traits = PERSONALITIES.get(self.personality_name,
                                         PERSONALITIES['balanced'])

        # State tracking untuk adaptability
        self._damage_taken = 0
        self._damage_dealt = 0
        self._blocks_successful = 0
        self._hits_landed = 0
        self._mode = 'normal'  # normal, aggressive, defensive, desperate

    def get_action_weights(self, game_state: Dict[str, Any]) -> Dict[ActionType, float]:
        """Get action weights berdasarkan personality dan game state"""
        weights = {
            ActionType.JAB: self.traits.jab_weight,
            ActionType.CROSS: self.traits.cross_weight,
            ActionType.HOOK: self.traits.hook_weight,
            ActionType.UPPERCUT: self.traits.uppercut_weight,
            ActionType.BLOCK: self.traits.block_weight,
            ActionType.DODGE: self.traits.dodge_weight,
            ActionType.IDLE: 0.2,
        }

        # Adjust based on health
        my_health = game_state.get('my_health', 100)
        opp_health = game_state.get('opp_health', 100)

        if my_health < 30:
            # Desperate - more aggressive or defensive based on personality
            if self.traits.aggression > 0.6:
                weights[ActionType.HOOK] *= 1.5
                weights[ActionType.UPPERCUT] *= 1.5
            else:
                weights[ActionType.BLOCK] *= 1.5
                weights[ActionType.DODGE] *= 1.5

        if opp_health < 30:
            # Go for the kill
            weights[ActionType.CROSS] *= 1.3
            weights[ActionType.HOOK] *= 1.3
            weights[ActionType.UPPERCUT] *= 1.4

        # Adjust based on stamina
        my_stamina = game_state.get('my_stamina', 100)
        if my_stamina < 30:
            # Low stamina - prefer low cost actions
            weights[ActionType.JAB] *= 1.5
            weights[ActionType.HOOK] *= 0.5
            weights[ActionType.UPPERCUT] *= 0.3
            weights[ActionType.IDLE] *= 2.0

        # Adjust based on distance
        distance = game_state.get('distance', 'medium')
        if distance == 'far':
            weights[ActionType.IDLE] *= 1.5  # Close distance first
            weights[ActionType.UPPERCUT] *= 0.3
        elif distance == 'clinch':
            weights[ActionType.UPPERCUT] *= 1.5
            weights[ActionType.HOOK] *= 1.3
            weights[ActionType.DODGE] *= 0.5

        # Adjust based on opponent action
        opp_action = game_state.get('opp_action', 'idle')
        if opp_action in ['JAB', 'CROSS', 'HOOK', 'UPPERCUT']:
            # Opponent attacking
            if self.traits.patience > 0.6:
                weights[ActionType.BLOCK] *= 1.5
                weights[ActionType.DODGE] *= 1.3
            else:
                # Counter attack
                weights[ActionType.JAB] *= 1.3

        return weights

    def choose_action(self, game_state: Dict[str, Any]) -> ActionType:
        """Choose action berdasarkan weights"""
        weights = self.get_action_weights(game_state)

        # Filter by stamina
        stamina = game_state.get('my_stamina', 100)
        from config import ACTION_DATA
        valid_actions = {}

        for action, weight in weights.items():
            action_data = ACTION_DATA.get(action)
            if action_data and stamina >= action_data.stamina_cost * 0.5:
                valid_actions[action] = weight

        if not valid_actions:
            return ActionType.IDLE

        # Weighted random choice
        total = sum(valid_actions.values())
        r = random.random() * total
        cumulative = 0

        for action, weight in valid_actions.items():
            cumulative += weight
            if r <= cumulative:
                return action

        return ActionType.IDLE

    def get_trash_talk(self, event: str = 'general') -> str:
        """Get trash talk line"""
        if random.random() > self.traits.trash_talk_freq:
            return ""

        lines = TRASH_TALK.get(self.personality_name,
                               TRASH_TALK['balanced'])
        return random.choice(lines)

    def update_state(self, event: str, value: Any = None):
        """Update internal state untuk adaptability"""
        if event == 'damage_taken':
            self._damage_taken += value or 0
        elif event == 'damage_dealt':
            self._damage_dealt += value or 0
        elif event == 'block_success':
            self._blocks_successful += 1
        elif event == 'hit_landed':
            self._hits_landed += 1

        # Update mode based on performance
        self._update_mode()

    def _update_mode(self):
        """Update tactical mode based on performance"""
        if self.traits.adaptability < 0.3:
            return  # Low adaptability = stick to default

        # Calculate performance
        total_exchanges = self._hits_landed + self._blocks_successful
        if total_exchanges < 5:
            return  # Not enough data

        hit_ratio = self._hits_landed / max(1, total_exchanges)
        damage_ratio = self._damage_dealt / max(1, self._damage_dealt + self._damage_taken)

        if damage_ratio > 0.7:
            self._mode = 'aggressive'  # Winning - press advantage
        elif damage_ratio < 0.3:
            self._mode = 'defensive'  # Losing - be careful
        else:
            self._mode = 'normal'

    def get_description(self) -> str:
        """Get personality description for LLM prompt"""
        descs = {
            'destroyer': "Aggressive and powerful. Prefer heavy attacks. Go for the knockout.",
            'tactician': "Calculated and efficient. Use jabs to set up bigger punches. Be patient.",
            'ghost': "Evasive and counter-focused. Dodge attacks and strike when they miss.",
            'wildcard': "Unpredictable and chaotic. Mix up attacks randomly. Keep them guessing.",
            'balanced': "Well-rounded fighter. Adapt to the situation. Balance offense and defense.",
            'aggressive': "Relentless attacker. Keep pressure on. Don't let them breathe.",
            'defensive': "Patient defender. Wait for openings. Counter-attack effectively.",
        }
        return descs.get(self.personality_name, descs['balanced'])

    def reset(self):
        """Reset state untuk match baru"""
        self._damage_taken = 0
        self._damage_dealt = 0
        self._blocks_successful = 0
        self._hits_landed = 0
        self._mode = 'normal'
