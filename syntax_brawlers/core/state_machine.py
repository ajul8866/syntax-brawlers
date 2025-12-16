"""
State Machine for game flow management
"""

from typing import Dict, Optional, Callable, Any
from config import GameState, FightPhase


class StateMachine:
    """
    Manages game states and transitions.
    Supports nested states (e.g., FIGHTING -> FightPhase.ACTIVE)
    """

    def __init__(self):
        self.current_state: GameState = GameState.MAIN_MENU
        self.previous_state: Optional[GameState] = None
        self.fight_phase: FightPhase = FightPhase.INTRO

        # State handlers
        self._enter_handlers: Dict[GameState, Callable] = {}
        self._exit_handlers: Dict[GameState, Callable] = {}
        self._update_handlers: Dict[GameState, Callable] = {}

        # Transition locks
        self._transition_locked = False
        self._pending_transition: Optional[GameState] = None

        # State data (for passing data between states)
        self.state_data: Dict[str, Any] = {}

    def register_handlers(
        self,
        state: GameState,
        enter: Optional[Callable] = None,
        exit_handler: Optional[Callable] = None,
        update: Optional[Callable] = None
    ):
        """Register handlers for a state"""
        if enter:
            self._enter_handlers[state] = enter
        if exit_handler:
            self._exit_handlers[state] = exit_handler
        if update:
            self._update_handlers[state] = update

    def transition_to(self, new_state: GameState, **kwargs):
        """
        Transition to a new state.
        Calls exit handler on current state, then enter handler on new state.
        """
        if self._transition_locked:
            self._pending_transition = new_state
            return

        if new_state == self.current_state:
            return

        # Store data for new state
        self.state_data.update(kwargs)

        # Exit current state
        if self.current_state in self._exit_handlers:
            self._exit_handlers[self.current_state]()

        # Update state
        self.previous_state = self.current_state
        self.current_state = new_state

        # Reset fight phase when entering fight
        if new_state == GameState.FIGHTING:
            self.fight_phase = FightPhase.INTRO

        # Enter new state
        if new_state in self._enter_handlers:
            self._enter_handlers[new_state]()

    def set_fight_phase(self, phase: FightPhase):
        """Set the current fight phase (sub-state of FIGHTING)"""
        if self.current_state == GameState.FIGHTING:
            self.fight_phase = phase

    def update(self, dt: float):
        """Update current state"""
        if self.current_state in self._update_handlers:
            self._update_handlers[self.current_state](dt)

        # Process pending transition
        if self._pending_transition and not self._transition_locked:
            pending = self._pending_transition
            self._pending_transition = None
            self.transition_to(pending)

    def lock_transition(self):
        """Prevent state transitions (e.g., during animations)"""
        self._transition_locked = True

    def unlock_transition(self):
        """Allow state transitions again"""
        self._transition_locked = False

    def go_back(self):
        """Return to previous state"""
        if self.previous_state:
            self.transition_to(self.previous_state)

    def is_state(self, state: GameState) -> bool:
        """Check if current state matches"""
        return self.current_state == state

    def is_fight_phase(self, phase: FightPhase) -> bool:
        """Check if current fight phase matches"""
        return self.current_state == GameState.FIGHTING and self.fight_phase == phase

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get state data"""
        return self.state_data.get(key, default)

    def set_data(self, key: str, value: Any):
        """Set state data"""
        self.state_data[key] = value

    def clear_data(self):
        """Clear all state data"""
        self.state_data.clear()
