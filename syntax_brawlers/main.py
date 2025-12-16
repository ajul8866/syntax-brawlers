#!/usr/bin/env python3
"""
SYNTAX BRAWLERS v2.0 - LLM Arena Fighting Game
==============================================
Entry point untuk game.

Jalankan: python main.py
"""

import asyncio
import sys
import os

# Tambahkan path untuk imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import GAME_TITLE


def main():
    """Entry point utama (synchronous)"""
    print(f"\n{'='*60}")
    print(f"  {GAME_TITLE}")
    print(f"{'='*60}\n")
    print("Memuat game...")

    # Import di sini untuk mencegah circular imports
    from core.game import Game

    # Buat dan jalankan game
    game = Game()

    # Cek apakah semua sistem sudah siap
    # Untuk sekarang, jalankan dengan sistem dasar
    try:
        game.run()
    except KeyboardInterrupt:
        print("\nGame dihentikan oleh user.")
    except Exception as e:
        print(f"\nError: {e}")
        raise


async def main_async():
    """Entry point utama dengan async support untuk LLM"""
    print(f"\n{'='*60}")
    print(f"  {GAME_TITLE}")
    print(f"{'='*60}\n")
    print("Memuat game (async mode)...")

    from core.game import AsyncGame

    game = AsyncGame()

    try:
        await game.run_async()
    except KeyboardInterrupt:
        print("\nGame dihentikan oleh user.")
    except Exception as e:
        print(f"\nError: {e}")
        raise


def run_with_full_systems():
    """
    Jalankan game dengan semua sistem lengkap.
    Ini akan dipanggil setelah semua modul selesai.
    """
    print(f"\n{'='*60}")
    print(f"  {GAME_TITLE}")
    print(f"{'='*60}\n")

    # Import semua sistem
    from core.game import AsyncGame
    from fighters.fighter import Fighter
    from fighters.stats import FighterStats
    from combat.engine import CombatEngine
    from graphics.renderer import Renderer
    from graphics.camera import Camera
    from graphics.particles import ParticleSystem
    from ui.manager import UIManager
    from audio.sound_manager import SoundManager
    from ai.controller import AIController
    from ai.providers.openrouter import OpenRouterProvider

    # Inisialisasi game
    game = AsyncGame()

    # Inisialisasi sistem
    renderer = Renderer()
    combat_engine = CombatEngine()
    camera = Camera()
    particle_system = ParticleSystem()
    ui_manager = UIManager()
    sound_manager = SoundManager()

    game.initialize_systems(
        renderer=renderer,
        combat_engine=combat_engine,
        camera=camera,
        particle_system=particle_system,
        ui_manager=ui_manager,
        sound_manager=sound_manager
    )

    # Buat fighters
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
    llm_provider = OpenRouterProvider()
    ai1 = AIController(fighter1, llm_provider, personality='aggressive')
    ai2 = AIController(fighter2, llm_provider, personality='defensive')
    game.set_ai_controllers(ai1, ai2)

    # Jalankan game async
    asyncio.run(game.run_async())


if __name__ == "__main__":
    # Parse argumen
    if len(sys.argv) > 1:
        if sys.argv[1] == '--async':
            asyncio.run(main_async())
        elif sys.argv[1] == '--full':
            run_with_full_systems()
        elif sys.argv[1] == '--help':
            print("Syntax Brawlers v2.0")
            print("\nUsage: python main.py [OPTIONS]")
            print("\nOptions:")
            print("  --async   Jalankan dengan async support")
            print("  --full    Jalankan dengan semua sistem (setelah lengkap)")
            print("  --help    Tampilkan bantuan ini")
        else:
            main()
    else:
        main()
