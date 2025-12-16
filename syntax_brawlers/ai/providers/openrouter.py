"""
OpenRouter LLM Provider
=======================
Provider untuk OpenRouter API (supports DeepSeek, etc.)
"""

import httpx
import asyncio
import os
from typing import Dict, Any, Optional
import sys
sys.path.insert(0, '../..')

from config import LLM_TIMEOUT, LLM_MAX_RETRIES, LLM_DEFAULT_MODEL
from ai.providers.base import BaseLLMProvider, LLMResponse


class OpenRouterProvider(BaseLLMProvider):
    """
    LLM Provider menggunakan OpenRouter API.
    Supports berbagai model termasuk DeepSeek.
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str = "", model: str = ""):
        # Try environment variable if not provided
        if not api_key:
            api_key = os.environ.get('OPENROUTER_API_KEY', '')

        if not model:
            model = LLM_DEFAULT_MODEL

        super().__init__(api_key, model)

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/syntax-brawlers",
            "X-Title": "Syntax Brawlers"
        }

        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 500ms between requests

        # Caching
        self._response_cache: Dict[str, LLMResponse] = {}
        self._cache_ttl = 2.0  # Cache untuk 2 detik

    async def check_availability(self) -> bool:
        """Check apakah API available"""
        if not self.api_key:
            self.last_error = "No API key provided"
            self.is_available = False
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=5.0
                )

                if response.status_code == 200:
                    self.is_available = True
                    return True
                else:
                    self.last_error = f"API returned status {response.status_code}"
                    self.is_available = False
                    return False

        except Exception as e:
            self.last_error = str(e)
            self.is_available = False
            return False

    async def get_action(self, game_state: Dict[str, Any],
                         personality: str) -> LLMResponse:
        """Get action dari OpenRouter API"""
        if not self.api_key:
            return LLMResponse(
                action='IDLE',
                reasoning="No API key",
                trash_talk="",
                confidence=0,
                error="No API key configured"
            )

        # Check cache
        cache_key = self._make_cache_key(game_state, personality)
        if cache_key in self._response_cache:
            return self._response_cache[cache_key]

        # Rate limiting
        await self._rate_limit()

        # Build request
        prompt = self.build_prompt(game_state, personality)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a boxing AI with {personality} personality. Respond only in valid JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 200,
            "temperature": 0.7,
        }

        # Make request with retries
        for attempt in range(LLM_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.API_URL,
                        headers=self.headers,
                        json=payload,
                        timeout=LLM_TIMEOUT
                    )

                    if response.status_code == 200:
                        data = response.json()
                        content = data['choices'][0]['message']['content']
                        result = self.parse_response(content)

                        # Cache result
                        self._response_cache[cache_key] = result
                        self.is_available = True

                        return result

                    elif response.status_code == 401:
                        self.last_error = "Invalid API key"
                        return LLMResponse(
                            action='IDLE',
                            reasoning="Auth failed",
                            trash_talk="",
                            confidence=0,
                            error="Invalid API key"
                        )

                    elif response.status_code == 429:
                        # Rate limited, wait and retry
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue

                    else:
                        self.last_error = f"API error: {response.status_code}"

            except httpx.TimeoutException:
                self.last_error = "Request timed out"
                if attempt < LLM_MAX_RETRIES:
                    await asyncio.sleep(0.5)
                    continue

            except Exception as e:
                self.last_error = str(e)
                if attempt < LLM_MAX_RETRIES:
                    await asyncio.sleep(0.5)
                    continue

        # All retries failed
        return LLMResponse(
            action='IDLE',
            reasoning="API unavailable",
            trash_talk="",
            confidence=0,
            error=self.last_error
        )

    async def _rate_limit(self):
        """Enforce rate limiting"""
        import time
        now = time.time()
        elapsed = now - self._last_request_time

        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)

        self._last_request_time = time.time()

    def _make_cache_key(self, game_state: Dict[str, Any],
                        personality: str) -> str:
        """Create cache key dari game state"""
        # Simplify state untuk caching
        key_parts = [
            personality,
            str(int(game_state.get('my_health', 100) / 10)),  # Round to 10s
            str(int(game_state.get('opp_health', 100) / 10)),
            str(int(game_state.get('my_stamina', 100) / 20)),  # Round to 20s
            game_state.get('distance', 'medium'),
            game_state.get('opp_action', 'idle'),
        ]
        return '|'.join(key_parts)

    def set_api_key(self, api_key: str):
        """Set API key"""
        self.api_key = api_key
        self.headers["Authorization"] = f"Bearer {api_key}"

    def set_model(self, model: str):
        """Set model"""
        self.model = model

    def clear_cache(self):
        """Clear response cache"""
        self._response_cache.clear()

    def get_action_sync(self, game_state: Dict[str, Any],
                        personality: str) -> LLMResponse:
        """Synchronous version of get_action"""
        try:
            # Run async in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.get_action(game_state, personality))
            finally:
                loop.close()
        except Exception as e:
            return LLMResponse(
                action='JAB',  # Default action instead of IDLE
                reasoning=f"Sync error: {e}",
                trash_talk="",
                confidence=0.5,
                error=str(e)
            )

    def check_availability_sync(self) -> bool:
        """Synchronous version of check_availability"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.check_availability())
            finally:
                loop.close()
        except:
            return False


# Convenience function untuk quick setup
def create_openrouter_provider(api_key: str = "",
                               model: str = "deepseek/deepseek-chat") -> OpenRouterProvider:
    """Create OpenRouter provider dengan defaults"""
    return OpenRouterProvider(api_key=api_key, model=model)
