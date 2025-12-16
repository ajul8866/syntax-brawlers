"""
Text Box System
===============
Untuk menampilkan trash talk dan messages.
"""

import pygame
from typing import List, Optional, Tuple
from dataclasses import dataclass
import sys
sys.path.insert(0, '..')

from config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, BLACK, GRAY, RED, BLUE


@dataclass
class TextMessage:
    """Single text message"""
    text: str
    speaker: str
    color: Tuple[int, int, int]
    duration: float
    timer: float = 0
    alpha: float = 1.0


class TextBox:
    """
    Simple text box untuk single message.
    """

    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        self.text = ""
        self.font = None
        self.bg_color = (20, 20, 30, 200)
        self.text_color = WHITE
        self.border_color = GRAY

        self._init_font()

    def _init_font(self):
        self.font = pygame.font.Font(None, 24)

    def set_text(self, text: str, color: Tuple[int, int, int] = WHITE):
        self.text = text
        self.text_color = color

    def render(self, surface: pygame.Surface):
        if not self.text:
            return

        if self.font is None:
            self._init_font()

        # Background
        bg_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        bg_surface.fill(self.bg_color)
        surface.blit(bg_surface, (self.x, self.y))

        # Border
        pygame.draw.rect(surface, self.border_color,
                        (self.x, self.y, self.width, self.height), 2)

        # Text (word wrap)
        words = self.text.split(' ')
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            if self.font.size(test_line)[0] <= self.width - 20:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        # Render lines
        y_offset = 10
        for line in lines[:3]:  # Max 3 lines
            text_surface = self.font.render(line, True, self.text_color)
            surface.blit(text_surface, (self.x + 10, self.y + y_offset))
            y_offset += 25


class TrashTalkDisplay:
    """
    Display untuk trash talk dari kedua fighter.
    Shows messages yang muncul dan fade out.
    """

    def __init__(self):
        # Position
        self.y_base = SCREEN_HEIGHT - 150

        # Messages
        self.messages: List[TextMessage] = []
        self.max_messages = 3

        # Font
        self.font = None
        self.speaker_font = None
        self._init_fonts()

        # Animation
        self.message_duration = 3.0
        self.fade_duration = 0.5

    def _init_fonts(self):
        self.font = pygame.font.Font(None, 28)
        self.speaker_font = pygame.font.Font(None, 22)

    def add_message(self, text: str, speaker: str,
                    color: Tuple[int, int, int] = WHITE):
        """Add new trash talk message"""
        if not text:
            return

        # Remove oldest if at max
        while len(self.messages) >= self.max_messages:
            self.messages.pop(0)

        self.messages.append(TextMessage(
            text=text,
            speaker=speaker,
            color=color,
            duration=self.message_duration
        ))

    def update(self, dt: float):
        """Update message timers"""
        for msg in self.messages[:]:
            msg.timer += dt

            # Calculate alpha for fade out
            if msg.timer > msg.duration - self.fade_duration:
                fade_progress = (msg.timer - (msg.duration - self.fade_duration)) / self.fade_duration
                msg.alpha = 1.0 - fade_progress

            # Remove expired
            if msg.timer >= msg.duration:
                self.messages.remove(msg)

    def render(self, surface: pygame.Surface):
        """Render all active messages"""
        if self.font is None:
            self._init_fonts()

        # Background panel
        if self.messages:
            panel_height = len(self.messages) * 45 + 20
            panel_y = self.y_base - 10

            panel = pygame.Surface((SCREEN_WIDTH - 100, panel_height), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 150))
            surface.blit(panel, (50, panel_y))

            pygame.draw.rect(surface, GRAY,
                           (50, panel_y, SCREEN_WIDTH - 100, panel_height), 1)

        # Render messages
        y_offset = 0
        for msg in self.messages:
            alpha = int(255 * msg.alpha)

            # Speaker name
            speaker_text = self.speaker_font.render(f"[{msg.speaker}]", True, msg.color)
            speaker_text.set_alpha(alpha)

            # Message text
            msg_text = self.font.render(msg.text, True, WHITE)
            msg_text.set_alpha(alpha)

            # Position
            y = self.y_base + y_offset

            # Determine side based on speaker color
            if msg.color == RED or msg.color[0] > 150:
                # Left side (fighter 1)
                surface.blit(speaker_text, (60, y))
                surface.blit(msg_text, (60 + speaker_text.get_width() + 10, y))
            else:
                # Right side (fighter 2)
                total_width = speaker_text.get_width() + msg_text.get_width() + 10
                x = SCREEN_WIDTH - 60 - total_width
                surface.blit(speaker_text, (x, y))
                surface.blit(msg_text, (x + speaker_text.get_width() + 10, y))

            y_offset += 40

    def clear(self):
        """Clear all messages"""
        self.messages.clear()


class AnnouncerText:
    """
    Large announcer text untuk ROUND START, KO, etc.
    """

    def __init__(self):
        self.text = ""
        self.subtitle = ""
        self.timer = 0.0
        self.duration = 2.0
        self.is_active = False

        # Animation
        self.scale = 1.0
        self.alpha = 255

        # Fonts
        self.main_font = None
        self.sub_font = None
        self._init_fonts()

    def _init_fonts(self):
        self.main_font = pygame.font.Font(None, 96)
        self.sub_font = pygame.font.Font(None, 36)

    def show(self, text: str, subtitle: str = "", duration: float = 2.0):
        """Show announcer text"""
        self.text = text
        self.subtitle = subtitle
        self.duration = duration
        self.timer = 0
        self.is_active = True
        self.scale = 0.5
        self.alpha = 255

    def update(self, dt: float):
        """Update animation"""
        if not self.is_active:
            return

        self.timer += dt

        # Scale animation (pop in)
        if self.timer < 0.2:
            self.scale = 0.5 + (self.timer / 0.2) * 0.7  # 0.5 -> 1.2
        elif self.timer < 0.3:
            self.scale = 1.2 - ((self.timer - 0.2) / 0.1) * 0.2  # 1.2 -> 1.0
        else:
            self.scale = 1.0

        # Fade out
        if self.timer > self.duration - 0.5:
            fade_progress = (self.timer - (self.duration - 0.5)) / 0.5
            self.alpha = int(255 * (1 - fade_progress))

        # End
        if self.timer >= self.duration:
            self.is_active = False

    def render(self, surface: pygame.Surface):
        """Render announcer text"""
        if not self.is_active:
            return

        if self.main_font is None:
            self._init_fonts()

        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2 - 50

        # Main text
        main_surface = self.main_font.render(self.text, True, WHITE)

        # Scale
        if self.scale != 1.0:
            new_size = (int(main_surface.get_width() * self.scale),
                       int(main_surface.get_height() * self.scale))
            main_surface = pygame.transform.scale(main_surface, new_size)

        main_surface.set_alpha(self.alpha)

        # Position
        main_rect = main_surface.get_rect(center=(center_x, center_y))
        surface.blit(main_surface, main_rect)

        # Subtitle
        if self.subtitle:
            sub_surface = self.sub_font.render(self.subtitle, True, GRAY)
            sub_surface.set_alpha(self.alpha)
            sub_rect = sub_surface.get_rect(center=(center_x, center_y + 60))
            surface.blit(sub_surface, sub_rect)
