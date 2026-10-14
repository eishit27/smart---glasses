"""
Voice command processing module.
Interprets spoken requests and maps them to system commands.
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class CommandType(Enum):
    """Supported voice commands."""
    DESCRIBE_SCENE = auto()
    READ_TEXT = auto()
    IDENTIFY_PERSON = auto()
    NAVIGATE = auto()
    RECORD_VIDEO = auto()
    TAKE_PHOTO = auto()
    STOP_RECORDING = auto()
    HELP = auto()
    BATTERY_STATUS = auto()
    CONVERSATIONAL_QUERY = auto()  # Open-ended Alexa-style visual conversational AI
    UNKNOWN = auto()

@dataclass
class Command:
    """Represents a parsed command with optional parameters."""
    type: CommandType
    parameters: Dict[str, str]
    original_text: str
    clean_query: str = ""

class VoiceCommandHandler:
    """Processes natural language text into actionable commands or open-ended visual queries."""

    WAKE_WORDS = ["hey vision", "vision aid", "hey glasses", "ok vision", "vision"]

    def __init__(self):
        """Initialize the voice command handler with keyword mappings."""
        self._intent_map = {
            CommandType.DESCRIBE_SCENE: ["describe", "what do you see", "what's around me", "look around", "scan scene"],
            CommandType.READ_TEXT: ["read text", "read this", "what does it say", "read the sign", "read menu"],
            CommandType.IDENTIFY_PERSON: ["who is this", "identify person", "whose face", "who is around me"],
            CommandType.NAVIGATE: ["navigate", "guide me", "directions", "take me to"],
            CommandType.RECORD_VIDEO: ["start recording", "record video"],
            CommandType.TAKE_PHOTO: ["take photo", "capture photo", "snap picture"],
            CommandType.STOP_RECORDING: ["stop recording", "stop video"],
            CommandType.HELP: ["help", "what can you do", "commands"],
            CommandType.BATTERY_STATUS: ["battery", "power level", "how much battery"]
        }

    def strip_wake_word(self, text: str) -> str:
        """Removes introductory wake words like 'Hey Vision' from the sentence."""
        cleaned = text.strip()
        cleaned_lower = cleaned.lower()
        for wake in self.WAKE_WORDS:
            if cleaned_lower.startswith(wake):
                cleaned = cleaned[len(wake):].lstrip(" ,:.-?!")
                break
        return cleaned

    def process_command(self, text: str) -> Command:
        """
        Process transcribed text and identify either a system action or an open-ended
        Alexa-like conversational visual query.
        """
        if not text or not text.strip():
            return Command(CommandType.UNKNOWN, {}, "", "")

        # 1. Clean wake word
        clean_text = self.strip_wake_word(text)
        if not clean_text:
            # User just said "Hey Vision"
            return Command(CommandType.HELP, {}, text, "help")

        text_lower = clean_text.lower()
        logger.debug(f"Processing clean voice query: '{clean_text}'")

        # 2. Check for exact operational shortcut commands
        for cmd_type, keywords in self._intent_map.items():
            for keyword in keywords:
                # Match if keyword is exact or prominent command
                if text_lower == keyword or text_lower.startswith(keyword + " "):
                    params = {}
                    if cmd_type == CommandType.NAVIGATE and "to" in text_lower:
                        parts = text_lower.split("to", 1)
                        if len(parts) > 1:
                            params["target"] = parts[1].strip()

                    return Command(type=cmd_type, parameters=params, original_text=text, clean_query=clean_text)

        # 3. Conversational / Alexa-like Visual Q&A
        # E.g.: "What am I holding?", "Where did I put my keys?", "Is this milk expired?", "Is anyone smiling?"
        return Command(
            type=CommandType.CONVERSATIONAL_QUERY,
            parameters={"query": clean_text},
            original_text=text,
            clean_query=clean_text
        )
