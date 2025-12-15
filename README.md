# Syntax Brawlers - LLM Arena Fighting Game

Two AI-controlled fighters battle in a boxing ring, with each LLM generating tactical decisions and trash talk based on the fight context.

## Features

- **Real LLM Integration**: OpenRouter (DeepSeek), Anthropic Claude, OpenAI GPT, Ollama
- **7 Combat Actions**: Jab, Cross, Hook, Uppercut, Block, Dodge, Clinch
- **4 AI Personalities**: The Destroyer, The Tactician, The Ghost, The Wildcard
- **Advanced Combat**: Combo system, counter attacks, critical hits, stagger
- **Visual Effects**: Particle effects, screen shake, damage popups
- **Professional GUI**: Health/stamina bars, AI thoughts display, round system

## Requirements

```bash
pip install pygame httpx numpy
```

## Setup

Set your LLM API key:

```bash
# OpenRouter (recommended - supports DeepSeek v3.2)
export OPENROUTER_API_KEY="your-key"

# Or Anthropic
export ANTHROPIC_API_KEY="your-key"

# Or OpenAI
export OPENAI_API_KEY="your-key"
```

## Run

```bash
python syntax_brawlers.py
```

## Controls

- **Mouse** - Menu navigation
- **ESC** - Pause / Menu
- **R** - Restart match
- **SPACE** - Skip text animation

## AI Personalities

| Personality | Style | Signature Move |
|-------------|-------|----------------|
| The Destroyer | Aggressive pressure | Hook |
| The Tactician | Strategic, analytical | Cross |
| The Ghost | Defensive, counter | Dodge |
| The Wildcard | Unpredictable chaos | Uppercut |

## License

MIT
