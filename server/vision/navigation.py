"""
Navigation assistance module using Gemini Vision API.
"""

import asyncio
import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

import cv2
import numpy as np
from google import genai
from google.genai import types

@dataclass
class Obstacle:
    type: str
    direction: str  # left, center, right
    distance_estimate: str  # near, medium, far

@dataclass
class NavigationResult:
    obstacles: List[Obstacle]
    path_clear: bool
    warnings: List[str]  # critical alerts
    suggestions: List[str]  # info/guidance
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class NavigationAssistant:
    """
    Analyzes frames for navigation and obstacle avoidance using Gemini Vision.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the navigation assistant.

        Args:
            api_key: Optional Gemini API key.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key is required.")
            
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = 'gemini-2.5-flash'
        
        self.system_prompt = (
            "You are an expert navigation assistant for a blind person. Analyze the image and "
            "provide structured navigation cues in JSON format with the following keys:\n"
            "1. 'obstacles': A list of objects where each object has 'type' (e.g. chair, pole), "
            "'direction' ('left', 'center', 'right'), and 'distance_estimate' ('near', 'medium', 'far').\n"
            "2. 'path_clear': A boolean indicating if the immediate forward path is clear.\n"
            "3. 'warnings': A list of strings for urgent/critical hazards like stairs ahead, curbs, "
            "approaching vehicles, or tripping hazards. Keep them brief.\n"
            "4. 'suggestions': A list of strings for helpful guidance (e.g., 'path clear on your right').\n"
            "Focus especially on obstacles, path clearance, stairs, curbs, doors, and crosswalks. "
            "Ensure the output is valid JSON."
        )

    async def analyze_navigation(self, frame: np.ndarray) -> NavigationResult:
        """
        Analyzes the frame for navigation assistance.

        Args:
            frame: Numpy array representing the image frame (BGR format).

        Returns:
            NavigationResult containing structured navigation cues.
        """
        default_result = NavigationResult(
            obstacles=[],
            path_clear=False,
            warnings=["Unable to analyze environment. Proceed with caution."],
            suggestions=[]
        )

        try:
            success, buffer = cv2.imencode('.jpg', frame)
            if not success:
                return default_result
                
            jpeg_bytes = buffer.tobytes()
            image_part = types.Part.from_bytes(data=jpeg_bytes, mime_type='image/jpeg')

            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=[self.system_prompt, image_part]
            )
            
            response_text = response.text.strip()
            # Clean up markdown JSON block if present
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            data = json.loads(response_text)
            
            # Parse obstacles
            obstacles = []
            for obs_data in data.get("obstacles", []):
                try:
                    obstacles.append(Obstacle(
                        type=obs_data.get("type", "unknown"),
                        direction=obs_data.get("direction", "center"),
                        distance_estimate=obs_data.get("distance_estimate", "unknown")
                    ))
                except Exception:
                    pass
                    
            return NavigationResult(
                obstacles=obstacles,
                path_clear=data.get("path_clear", False),
                warnings=data.get("warnings", []),
                suggestions=data.get("suggestions", [])
            )
            
        except Exception as e:
            return NavigationResult(
                obstacles=[],
                path_clear=False,
                warnings=[f"Navigation analysis failed: {str(e)}"],
                suggestions=[]
            )
