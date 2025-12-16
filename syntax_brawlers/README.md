# Syntax Brawlers v2.0 - LLM Arena Fighting Game

A fighting game where AI fighters powered by LLMs (Large Language Models) battle each other in real-time combat.

## Features

- **LLM-Powered AI**: Fighters make decisions using DeepSeek via OpenRouter API
- **Procedural Graphics**: All sprites and effects generated with code (no external assets needed)
- **Real-time Combat**: Hitbox/hurtbox collision system with proper attack ranges
- **Particle Effects**: Hit sparks, blood effects, and visual feedback
- **Camera System**: Dynamic camera with shake, zoom, and follow
- **Procedural Audio**: Sound effects generated programmatically
- **Modular Architecture**: 39 files organized into 8 modules

## Requirements

- Python 3.8+
- Pygame 2.5+
- httpx (for async API calls)
- numpy

## Installation

```bash
cd syntax_brawlers
pip install -r requirements.txt
```

## Running the Game

```bash
python main.py
```

## Configuration

Set your OpenRouter API key in the game or as environment variable:
```bash
export OPENROUTER_API_KEY="your-api-key"
```

## Project Structure

```
syntax_brawlers/
├── main.py              # Entry point
├── config.py            # Game constants & settings
├── core/                # Core engine (game loop, state machine, input)
├── fighters/            # Fighter system (stats, hitbox, movement)
├── combat/              # Combat system (actions, combos, distance)
├── graphics/            # Graphics (renderer, sprites, particles, camera)
├── ai/                  # AI system (LLM providers, fallback, personality)
├── ui/                  # UI system (HUD, menus, text displays)
└── audio/               # Audio system (sound manager, procedural SFX)
```

## Controls

- **Arrow Keys**: Navigate menus
- **Enter**: Confirm selection
- **Escape**: Pause / Back
- **Space**: Start fight

## License

MIT License
