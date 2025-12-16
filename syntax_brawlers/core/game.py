"""
Main Game Engine for Syntax Brawlers v2.0
"""

import pygame
import asyncio
from typing import Optional, List, Dict, Any

import sys
sys.path.insert(0, '..')

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE,
    GameState, FightPhase, DEBUG_FRAMERATE,
    BLACK, WHITE
)
from core.state_machine import StateMachine
from core.input_handler import InputHandler


class Game:
    """
    Main game engine that coordinates all systems.
    """

    def __init__(self):
        # Initialize Pygame
        pygame.init()

        # Try to initialize audio (optional - may fail on servers)
        self.audio_available = False
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.audio_available = True
        except pygame.error as e:
            print(f"[Audio] Could not initialize mixer: {e}")

        # Display
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)

        # Clock
        self.clock = pygame.time.Clock()
        self.running = True
        self.dt = 0.0  # Delta time in seconds
        self.fps = 0
        self.frame_count = 0

        # Core systems
        self.state_machine = StateMachine()
        self.input_handler = InputHandler()

        # Systems (will be initialized later)
        self.fighters: List[Any] = []
        self.combat_engine = None
        self.renderer = None
        self.camera = None
        self.particle_system = None
        self.ui_manager = None
        self.sound_manager = None
        self.ai_controllers: List[Any] = []

        # Match state
        self.round_number = 1
        self.fighter1_rounds_won = 0
        self.fighter2_rounds_won = 0
        self.round_timer = 0.0

        # Initialize
        self._setup_state_handlers()

    def _setup_state_handlers(self):
        """Register handlers for each game state"""
        self.state_machine.register_handlers(
            GameState.MAIN_MENU,
            enter=self._enter_main_menu,
            update=self._update_main_menu
        )
        self.state_machine.register_handlers(
            GameState.CHARACTER_SELECT,
            enter=self._enter_character_select,
            update=self._update_character_select
        )
        self.state_machine.register_handlers(
            GameState.LLM_CONFIG,
            enter=self._enter_llm_config,
            update=self._update_llm_config
        )
        self.state_machine.register_handlers(
            GameState.PRE_FIGHT,
            enter=self._enter_pre_fight,
            update=self._update_pre_fight
        )
        self.state_machine.register_handlers(
            GameState.FIGHTING,
            enter=self._enter_fighting,
            update=self._update_fighting
        )
        self.state_machine.register_handlers(
            GameState.ROUND_END,
            enter=self._enter_round_end,
            update=self._update_round_end
        )
        self.state_machine.register_handlers(
            GameState.MATCH_END,
            enter=self._enter_match_end,
            update=self._update_match_end
        )
        self.state_machine.register_handlers(
            GameState.PAUSED,
            enter=self._enter_paused,
            update=self._update_paused
        )

    def initialize_systems(
        self,
        renderer,
        combat_engine,
        camera,
        particle_system,
        ui_manager,
        sound_manager
    ):
        """Initialize all game systems"""
        self.renderer = renderer
        self.combat_engine = combat_engine
        self.camera = camera
        self.particle_system = particle_system
        self.ui_manager = ui_manager
        self.sound_manager = sound_manager

    def set_fighters(self, fighter1, fighter2):
        """Set the two fighters"""
        self.fighters = [fighter1, fighter2]

    def set_ai_controllers(self, ai1, ai2):
        """Set AI controllers for fighters"""
        self.ai_controllers = [ai1, ai2]

    def run(self):
        """Main game loop"""
        while self.running:
            self.dt = self.clock.tick(FPS) / 1000.0
            self.fps = self.clock.get_fps()
            self.frame_count += 1

            # Handle events
            self._handle_events()

            # Check quit
            if self.input_handler.should_quit():
                self.running = False
                continue

            # Update
            self._update()

            # Render
            self._render()

            # Flip display
            pygame.display.flip()

        self._cleanup()

    def _handle_events(self):
        """Process pygame events"""
        self.input_handler.update()
        for event in pygame.event.get():
            self.input_handler.process_event(event)

    def _update(self):
        """Update game logic"""
        # Handle pause toggle
        if self.input_handler.is_action_just_pressed('pause'):
            if self.state_machine.is_state(GameState.FIGHTING):
                self.state_machine.transition_to(GameState.PAUSED)
            elif self.state_machine.is_state(GameState.PAUSED):
                self.state_machine.transition_to(GameState.FIGHTING)

        # Update state
        self.state_machine.update(self.dt)

        # Update particles (always, even when paused for nice effect)
        if self.particle_system:
            self.particle_system.update(self.dt)

    def _render(self):
        """Render current frame"""
        # Clear screen
        self.screen.fill(BLACK)

        if self.renderer:
            # Get camera transform
            offset_x, offset_y, zoom = (0, 0, 1.0)
            if self.camera:
                offset_x, offset_y = self.camera.get_offset()
                zoom = self.camera.zoom

            # Render game world
            self.renderer.render(
                self.screen,
                self.fighters,
                self.particle_system,
                offset_x, offset_y, zoom
            )

        # Render UI (always on top, no camera transform)
        if self.ui_manager:
            self.ui_manager.render(self.screen, self.state_machine.current_state)

        # Debug FPS
        if DEBUG_FRAMERATE:
            self._render_fps()

    def _render_fps(self):
        """Render FPS counter"""
        font = pygame.font.Font(None, 24)
        fps_text = font.render(f"FPS: {int(self.fps)}", True, WHITE)
        self.screen.blit(fps_text, (10, 10))

    def _cleanup(self):
        """Clean up resources"""
        if self.audio_available:
            pygame.mixer.quit()
        pygame.quit()

    # =========================================================================
    # STATE HANDLERS
    # =========================================================================

    def _enter_main_menu(self):
        """Enter main menu state"""
        if self.ui_manager:
            self.ui_manager.show_main_menu()
        if self.sound_manager:
            self.sound_manager.play_music('menu')

    def _update_main_menu(self, dt: float):
        """Update main menu"""
        if self.ui_manager:
            action = self.ui_manager.update_main_menu(self.input_handler)
            if action == 'start':
                self.state_machine.transition_to(GameState.CHARACTER_SELECT)
            elif action == 'settings':
                self.state_machine.transition_to(GameState.SETTINGS)
            elif action == 'quit':
                self.running = False

    def _enter_character_select(self):
        """Enter character select state"""
        if self.ui_manager:
            self.ui_manager.show_character_select()

    def _update_character_select(self, dt: float):
        """Update character select"""
        if self.ui_manager:
            result = self.ui_manager.update_character_select(self.input_handler)
            if result:
                # Characters selected, store and move to LLM config
                self.state_machine.set_data('fighter1_type', result[0])
                self.state_machine.set_data('fighter2_type', result[1])
                self.state_machine.transition_to(GameState.LLM_CONFIG)

    def _enter_llm_config(self):
        """Enter LLM configuration state"""
        if self.ui_manager:
            self.ui_manager.show_llm_config()

    def _update_llm_config(self, dt: float):
        """Update LLM configuration"""
        if self.ui_manager:
            result = self.ui_manager.update_llm_config(self.input_handler)
            if result:
                # LLM configured, move to pre-fight
                self.state_machine.set_data('llm_config', result)
                self.state_machine.transition_to(GameState.PRE_FIGHT)

    def _enter_pre_fight(self):
        """Enter pre-fight state (intro animations)"""
        # Reset match state
        self.round_number = 1
        self.fighter1_rounds_won = 0
        self.fighter2_rounds_won = 0

        # Initialize fighters at starting positions
        if self.fighters:
            for fighter in self.fighters:
                fighter.reset_round()

        # Start intro
        self.state_machine.set_fight_phase(FightPhase.INTRO)
        if self.sound_manager:
            self.sound_manager.play_music('fight')

        # Intro timer
        self._intro_timer = 3.0

    def _update_pre_fight(self, dt: float):
        """Update pre-fight intro"""
        self._intro_timer -= dt
        if self._intro_timer <= 0:
            self.state_machine.transition_to(GameState.FIGHTING)

    def _enter_fighting(self):
        """Enter fighting state"""
        self.state_machine.set_fight_phase(FightPhase.READY)
        self.round_timer = 180.0  # 3 minute round

        # Brief ready phase
        self._ready_timer = 1.5

    def _update_fighting(self, dt: float):
        """Update active fighting"""
        fight_phase = self.state_machine.fight_phase

        if fight_phase == FightPhase.READY:
            self._ready_timer -= dt
            if self._ready_timer <= 0:
                self.state_machine.set_fight_phase(FightPhase.ACTIVE)
                if self.sound_manager:
                    self.sound_manager.play_sfx('bell')

        elif fight_phase == FightPhase.ACTIVE:
            # Update round timer
            self.round_timer -= dt

            # Update AI controllers
            for i, ai in enumerate(self.ai_controllers):
                if ai:
                    # Update AI cooldowns
                    ai.update(dt)

                    if self.fighters:
                        action = ai.get_action(
                            self.fighters[i],
                            self.fighters[1 - i],
                            self.round_timer
                        )
                        if action:
                            self.fighters[i].execute_action(action)

            # Update fighters - pass opponent for proper facing
            if len(self.fighters) >= 2:
                self.fighters[0].update(dt, self.fighters[1])
                self.fighters[1].update(dt, self.fighters[0])

            # Update combat
            if self.combat_engine:
                result = self.combat_engine.update(dt, self.fighters)
                if result:
                    self._handle_combat_result(result)

            # Update camera
            if self.camera and self.fighters:
                self.camera.update(dt, self.fighters[0], self.fighters[1])

            # Check round end conditions
            self._check_round_end()

        elif fight_phase == FightPhase.HIT_FREEZE:
            # Brief pause on big hits
            self._hit_freeze_timer -= dt
            if self._hit_freeze_timer <= 0:
                self.state_machine.set_fight_phase(FightPhase.ACTIVE)

        elif fight_phase == FightPhase.KNOCKDOWN:
            # Handle knockdown/count
            self._knockdown_timer -= dt
            if self._knockdown_timer <= 0:
                self._handle_knockdown_end()

        elif fight_phase == FightPhase.KO:
            # KO celebration
            self._ko_timer -= dt
            if self._ko_timer <= 0:
                self.state_machine.transition_to(GameState.ROUND_END)

    def _handle_combat_result(self, result: Dict):
        """Handle combat result from engine"""
        if result.get('big_hit'):
            # Trigger hit freeze
            self._hit_freeze_timer = 0.05
            self.state_machine.set_fight_phase(FightPhase.HIT_FREEZE)

            # Camera shake
            if self.camera:
                self.camera.shake(result.get('shake_amount', 6))

            # Spawn particles
            if self.particle_system:
                self.particle_system.spawn_hit_effect(
                    result.get('hit_position', (640, 360)),
                    result.get('damage', 10)
                )

        if result.get('knockdown'):
            self._knockdown_timer = 10.0  # 10-count
            self._knocked_down_fighter = result.get('knocked_down')
            self.state_machine.set_fight_phase(FightPhase.KNOCKDOWN)

    def _check_round_end(self):
        """Check if round should end"""
        # Time up
        if self.round_timer <= 0:
            self.state_machine.transition_to(GameState.ROUND_END)
            return

        # KO
        for i, fighter in enumerate(self.fighters):
            if fighter.stats.health <= 0:
                self._ko_timer = 3.0
                self._winner = 1 - i
                self.state_machine.set_fight_phase(FightPhase.KO)
                return

    def _handle_knockdown_end(self):
        """Handle end of knockdown"""
        # Fighter gets up or KO
        if hasattr(self, '_knocked_down_fighter') and self._knocked_down_fighter:
            fighter = self._knocked_down_fighter
            if fighter.stats.health > 20:  # Can get up
                fighter.get_up()
                self.state_machine.set_fight_phase(FightPhase.ACTIVE)
            else:
                # KO
                self._ko_timer = 3.0
                self._winner = 0 if fighter == self.fighters[1] else 1
                self.state_machine.set_fight_phase(FightPhase.KO)

    def _enter_round_end(self):
        """Enter round end state"""
        # Determine round winner
        if hasattr(self, '_winner'):
            winner = self._winner
        else:
            # Compare health
            h1 = self.fighters[0].stats.health if self.fighters else 0
            h2 = self.fighters[1].stats.health if self.fighters else 0
            winner = 0 if h1 >= h2 else 1

        if winner == 0:
            self.fighter1_rounds_won += 1
        else:
            self.fighter2_rounds_won += 1

        if self.ui_manager:
            self.ui_manager.show_round_result(winner, self.round_number)

        self._round_end_timer = 3.0

    def _update_round_end(self, dt: float):
        """Update round end"""
        self._round_end_timer -= dt
        if self._round_end_timer <= 0:
            # Check for match end
            if self.fighter1_rounds_won >= 2 or self.fighter2_rounds_won >= 2:
                self.state_machine.transition_to(GameState.MATCH_END)
            else:
                # Next round
                self.round_number += 1
                for fighter in self.fighters:
                    fighter.reset_round()
                self.state_machine.transition_to(GameState.PRE_FIGHT)

    def _enter_match_end(self):
        """Enter match end state"""
        winner = 0 if self.fighter1_rounds_won > self.fighter2_rounds_won else 1
        if self.ui_manager:
            self.ui_manager.show_match_result(winner)
        if self.sound_manager:
            self.sound_manager.play_sfx('victory')

        # Set winner animation
        if self.fighters:
            self.fighters[winner].set_animation('victory')
            self.fighters[1 - winner].set_animation('defeat')

    def _update_match_end(self, dt: float):
        """Update match end"""
        # Wait for input to return to menu
        if self.input_handler.is_action_just_pressed('confirm'):
            self.state_machine.transition_to(GameState.MAIN_MENU)
        elif self.input_handler.is_action_just_pressed('restart'):
            self.state_machine.transition_to(GameState.PRE_FIGHT)

    def _enter_paused(self):
        """Enter paused state"""
        if self.ui_manager:
            self.ui_manager.show_pause_menu()

    def _update_paused(self, dt: float):
        """Update paused state"""
        if self.ui_manager:
            action = self.ui_manager.update_pause_menu(self.input_handler)
            if action == 'resume':
                self.state_machine.transition_to(GameState.FIGHTING)
            elif action == 'restart':
                self.state_machine.transition_to(GameState.PRE_FIGHT)
            elif action == 'quit':
                self.state_machine.transition_to(GameState.MAIN_MENU)


# Async wrapper for LLM calls
class AsyncGame(Game):
    """Game with async support for LLM API calls"""

    def __init__(self):
        super().__init__()
        self._pending_ai_tasks: List[asyncio.Task] = []

    async def run_async(self):
        """Async main game loop"""
        loop = asyncio.get_event_loop()

        while self.running:
            self.dt = self.clock.tick(FPS) / 1000.0
            self.fps = self.clock.get_fps()
            self.frame_count += 1

            # Handle events
            self._handle_events()

            # Check quit
            if self.input_handler.should_quit():
                self.running = False
                continue

            # Update (with async AI)
            await self._update_async()

            # Render
            self._render()

            # Flip display
            pygame.display.flip()

            # Yield to event loop
            await asyncio.sleep(0)

        self._cleanup()

    async def _update_async(self):
        """Update with async AI calls"""
        # Handle pause toggle
        if self.input_handler.is_action_just_pressed('pause'):
            if self.state_machine.is_state(GameState.FIGHTING):
                self.state_machine.transition_to(GameState.PAUSED)
            elif self.state_machine.is_state(GameState.PAUSED):
                self.state_machine.transition_to(GameState.FIGHTING)

        # Update state
        if self.state_machine.current_state == GameState.FIGHTING:
            await self._update_fighting_async(self.dt)
        else:
            self.state_machine.update(self.dt)

        # Update particles
        if self.particle_system:
            self.particle_system.update(self.dt)

    async def _update_fighting_async(self, dt: float):
        """Async fighting update for LLM calls"""
        fight_phase = self.state_machine.fight_phase

        if fight_phase == FightPhase.READY:
            if hasattr(self, '_ready_timer'):
                self._ready_timer -= dt
                if self._ready_timer <= 0:
                    self.state_machine.set_fight_phase(FightPhase.ACTIVE)
                    if self.sound_manager:
                        self.sound_manager.play_sfx('bell')

        elif fight_phase == FightPhase.ACTIVE:
            # Update round timer
            self.round_timer -= dt

            # Async AI decisions
            for i, ai in enumerate(self.ai_controllers):
                if ai and self.fighters:
                    # Non-blocking AI call
                    action = await ai.get_action_async(
                        self.fighters[i],
                        self.fighters[1 - i],
                        self.round_timer
                    )
                    if action:
                        self.fighters[i].execute_action(action)

            # Update fighters
            for fighter in self.fighters:
                fighter.update(dt)

            # Update combat
            if self.combat_engine:
                result = self.combat_engine.update(dt, self.fighters)
                if result:
                    self._handle_combat_result(result)

            # Update camera
            if self.camera and self.fighters:
                self.camera.update(dt, self.fighters[0], self.fighters[1])

            # Check round end conditions
            self._check_round_end()

        elif fight_phase == FightPhase.HIT_FREEZE:
            if hasattr(self, '_hit_freeze_timer'):
                self._hit_freeze_timer -= dt
                if self._hit_freeze_timer <= 0:
                    self.state_machine.set_fight_phase(FightPhase.ACTIVE)

        elif fight_phase == FightPhase.KNOCKDOWN:
            if hasattr(self, '_knockdown_timer'):
                self._knockdown_timer -= dt
                if self._knockdown_timer <= 0:
                    self._handle_knockdown_end()

        elif fight_phase == FightPhase.KO:
            if hasattr(self, '_ko_timer'):
                self._ko_timer -= dt
                if self._ko_timer <= 0:
                    self.state_machine.transition_to(GameState.ROUND_END)
