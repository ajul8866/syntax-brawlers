#!/usr/bin/env python3
"""
SYNTAX BRAWLERS v2.0 - LLM Arena Fighting Game
==============================================
Entry point untuk game.

Jalankan: python main.py
"""

import sys
import os

# Tambahkan path untuk imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    GAME_TITLE, GameState,
    FIGHTER1_START_X, FIGHTER2_START_X, FIGHTER_START_Y
)


def main():
    """Entry point utama"""
    print(f"\n{'='*60}")
    print(f"  {GAME_TITLE}")
    print(f"{'='*60}\n")
    print("Memuat game...")

    # Import semua sistem
    from core.game import Game
    from fighters.fighter import Fighter
    from fighters.stats import FighterStats
    from combat.engine import CombatEngine
    from graphics.renderer import Renderer
    from graphics.camera import Camera
    from graphics.particles import ParticleSystem
    from ui.manager import UIManager
    from audio.sound_manager import SoundManager
    from ai.controller import AIController
    from ai.fallback import FallbackAI

    print("Inisialisasi sistem...")

    # Buat game instance
    game = Game()

    # Inisialisasi semua sistem grafis dan audio
    renderer = Renderer()
    combat_engine = CombatEngine()
    camera = Camera()
    particle_system = ParticleSystem()
    ui_manager = UIManager()

    # Sound manager (opsional - mungkin gagal tanpa audio device)
    sound_manager = None
    if game.audio_available:
        try:
            sound_manager = SoundManager()
            print("Audio: OK")
        except Exception as e:
            print(f"Audio: Disabled ({e})")
    else:
        print("Audio: Disabled (no device)")

    # Register semua sistem ke game
    game.initialize_systems(
        renderer=renderer,
        combat_engine=combat_engine,
        camera=camera,
        particle_system=particle_system,
        ui_manager=ui_manager,
        sound_manager=sound_manager
    )

    # Buat fighters
    print("Membuat fighters...")
    fighter1 = Fighter(
        name="CLAUDE",
        stats=FighterStats(power=1.1, speed=0.9, defense=1.0),
        player_id=1,
        is_player_one=True
    )

    fighter2 = Fighter(
        name="GPT",
        stats=FighterStats(power=0.9, speed=1.1, defense=1.0),
        player_id=2,
        is_player_one=False
    )

    game.set_fighters(fighter1, fighter2)

    # Buat AI controllers dengan LLM
    print("Inisialisasi AI dengan LLM...")
    from ai.providers.openrouter import OpenRouterProvider

    # OpenRouter API - MUST set OPENROUTER_API_KEY environment variable
    api_key = os.environ.get('OPENROUTER_API_KEY', '').strip().strip('"').strip("'")
    if not api_key:
        print("=" * 60)
        print("ERROR: OPENROUTER_API_KEY not set!")
        print("Set environment variable sebelum jalankan:")
        print("  Windows: set OPENROUTER_API_KEY=sk-or-v1-xxx")
        print("  Linux:   export OPENROUTER_API_KEY=sk-or-v1-xxx")
        print("=" * 60)
    else:
        print(f"API Key loaded: {api_key[:15]}...{api_key[-4:]}")

    llm_provider = OpenRouterProvider(api_key=api_key)

    ai1 = AIController(fighter1, llm_provider=llm_provider, personality='aggressive')
    ai2 = AIController(fighter2, llm_provider=llm_provider, personality='defensive')
    game.set_ai_controllers(ai1, ai2)
    print(f"LLM Provider: OpenRouter (DeepSeek)")

    # Set initial state
    game.state_machine.transition_to(GameState.MAIN_MENU)

    print("\nGame siap! Tekan tombol untuk mulai...")
    print("ESC = Keluar | ENTER = Pilih | Arrow Keys = Navigasi\n")

    # Jalankan game loop
    try:
        game.run()
    except KeyboardInterrupt:
        print("\nGame dihentikan oleh user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Syntax Brawlers v2.0 - LLM Arena Fighting Game")
        print("\nUsage: python main.py")
        print("\nControls:")
        print("  Arrow Keys  - Navigate menu")
        print("  Enter       - Select")
        print("  Escape      - Pause / Back")
        print("  Space       - Start fight")
    else:
        main()
