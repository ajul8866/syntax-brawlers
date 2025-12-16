"""
Input handling for keyboard and mouse
"""

import pygame
from typing import Dict, Set, Tuple, Callable, Optional
from dataclasses import dataclass, field


@dataclass
class InputState:
    """Current state of all inputs"""
    # Keyboard
    keys_pressed: Set[int] = field(default_factory=set)
    keys_just_pressed: Set[int] = field(default_factory=set)
    keys_just_released: Set[int] = field(default_factory=set)

    # Mouse
    mouse_pos: Tuple[int, int] = (0, 0)
    mouse_buttons: Tuple[bool, bool, bool] = (False, False, False)
    mouse_just_clicked: Tuple[bool, bool, bool] = (False, False, False)
    mouse_just_released: Tuple[bool, bool, bool] = (False, False, False)

    # Special
    quit_requested: bool = False


class InputHandler:
    """
    Centralized input handling.
    Tracks current state, just-pressed, and just-released for all inputs.
    """

    def __init__(self):
        self.state = InputState()
        self._prev_keys: Set[int] = set()
        self._prev_mouse: Tuple[bool, bool, bool] = (False, False, False)

        # Key bindings (action -> key)
        self.bindings: Dict[str, int] = {
            'pause': pygame.K_ESCAPE,
            'confirm': pygame.K_RETURN,
            'cancel': pygame.K_ESCAPE,
            'restart': pygame.K_r,
            'skip': pygame.K_SPACE,
            'debug': pygame.K_F1,
            'fullscreen': pygame.K_F11,
        }

        # Callbacks
        self._key_callbacks: Dict[int, Callable] = {}

    def update(self):
        """
        Update input state. Call once per frame before processing events.
        """
        # Store previous state
        self._prev_keys = self.state.keys_pressed.copy()
        self._prev_mouse = self.state.mouse_buttons

        # Reset just-pressed/released
        self.state.keys_just_pressed.clear()
        self.state.keys_just_released.clear()
        self.state.mouse_just_clicked = (False, False, False)
        self.state.mouse_just_released = (False, False, False)
        self.state.quit_requested = False

    def process_event(self, event: pygame.event.Event):
        """Process a single pygame event"""
        if event.type == pygame.QUIT:
            self.state.quit_requested = True

        elif event.type == pygame.KEYDOWN:
            self.state.keys_pressed.add(event.key)
            if event.key not in self._prev_keys:
                self.state.keys_just_pressed.add(event.key)
                # Trigger callback if exists
                if event.key in self._key_callbacks:
                    self._key_callbacks[event.key]()

        elif event.type == pygame.KEYUP:
            self.state.keys_pressed.discard(event.key)
            self.state.keys_just_released.add(event.key)

        elif event.type == pygame.MOUSEMOTION:
            self.state.mouse_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONDOWN:
            buttons = list(self.state.mouse_buttons)
            just_clicked = list(self.state.mouse_just_clicked)
            if event.button <= 3:
                buttons[event.button - 1] = True
                just_clicked[event.button - 1] = True
            self.state.mouse_buttons = tuple(buttons)
            self.state.mouse_just_clicked = tuple(just_clicked)

        elif event.type == pygame.MOUSEBUTTONUP:
            buttons = list(self.state.mouse_buttons)
            just_released = list(self.state.mouse_just_released)
            if event.button <= 3:
                buttons[event.button - 1] = False
                just_released[event.button - 1] = True
            self.state.mouse_buttons = tuple(buttons)
            self.state.mouse_just_released = tuple(just_released)

    def is_key_pressed(self, key: int) -> bool:
        """Check if key is currently held down"""
        return key in self.state.keys_pressed

    def is_key_just_pressed(self, key: int) -> bool:
        """Check if key was just pressed this frame"""
        return key in self.state.keys_just_pressed

    def is_key_just_released(self, key: int) -> bool:
        """Check if key was just released this frame"""
        return key in self.state.keys_just_released

    def is_action_pressed(self, action: str) -> bool:
        """Check if bound action key is pressed"""
        if action in self.bindings:
            return self.is_key_pressed(self.bindings[action])
        return False

    def is_action_just_pressed(self, action: str) -> bool:
        """Check if bound action key was just pressed"""
        if action in self.bindings:
            return self.is_key_just_pressed(self.bindings[action])
        return False

    def is_mouse_clicked(self, button: int = 0) -> bool:
        """Check if mouse button was just clicked (0=left, 1=middle, 2=right)"""
        if 0 <= button < 3:
            return self.state.mouse_just_clicked[button]
        return False

    def is_mouse_held(self, button: int = 0) -> bool:
        """Check if mouse button is held down"""
        if 0 <= button < 3:
            return self.state.mouse_buttons[button]
        return False

    def get_mouse_pos(self) -> Tuple[int, int]:
        """Get current mouse position"""
        return self.state.mouse_pos

    def register_key_callback(self, key: int, callback: Callable):
        """Register a callback for when a key is pressed"""
        self._key_callbacks[key] = callback

    def unregister_key_callback(self, key: int):
        """Remove a key callback"""
        self._key_callbacks.pop(key, None)

    def set_binding(self, action: str, key: int):
        """Change a key binding"""
        self.bindings[action] = key

    def should_quit(self) -> bool:
        """Check if quit was requested"""
        return self.state.quit_requested
