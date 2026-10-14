"""
Scene Analyzer using Gemini Vision API.
"""

import asyncio
import io
import os
import time
from typing import Optional

import cv2
import numpy as np
from google import genai
from google.genai import types

class SceneAnalyzer:
    """
    Analyzes scenes for blind users using the Gemini Vision API.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the scene analyzer.

        Args:
            api_key: Optional Gemini API key. If not provided, it will be 
                     fetched from the GEMINI_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key is required.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = 'gemini-2.5-flash'
        self.last_call_time = 0.0
        self.min_interval = 2.0  # seconds between API calls to avoid rate limits

        self.system_prompts = {
            'scan': "You are an assistant for a blind person. Provide a quick scan of the environment. Focus ONLY on immediate obstacles and safety hazards. Use short sentences and spatial directions like 'on your left', 'ahead', 'behind you'. Keep it to 1-2 sentences.",
            'describe': "You are an assistant for a blind person. Describe the spatial layout of the scene, estimating distances to obstacles, people, and important objects. Mention their positions (left, right, ahead). Be concise and use short sentences suitable for speech synthesis.",
            'detailed': "You are an assistant for a blind person. Provide a rich, detailed description of the scene. Include colors, textures, lighting, spatial layout, distances, obstacles, people, and important objects. Describe the overall atmosphere while maintaining clarity and using spatial directions."
        }

    async def analyze_scene(self, frame: np.ndarray, mode: str = 'scan') -> str:
        """
        Analyzes the scene and returns a text description.

        Args:
            frame: Numpy array representing the image frame (BGR format).
            mode: Analysis mode ('scan', 'describe', 'detailed').

        Returns:
            A string describing the scene.
        """
        if mode not in self.system_prompts:
            mode = 'scan'

        # Rate limiting logic
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        if time_since_last_call < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last_call)

        try:
            # Convert numpy array to JPEG bytes
            success, buffer = cv2.imencode('.jpg', frame)
            if not success:
                return "Error: Failed to process the image frame."
            
            jpeg_bytes = buffer.tobytes()
            image_part = types.Part.from_bytes(data=jpeg_bytes, mime_type='image/jpeg')

            prompt = self.system_prompts[mode]
            
            self.last_call_time = time.time()
            
            # Use retry logic for API calls
            retries = 3
            for attempt in range(retries):
                try:
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=[prompt, image_part]
                    )
                    return response.text.strip()
                except Exception as e:
                    if attempt == retries - 1:
                        return f"Error analyzing scene: {str(e)}"
                    await asyncio.sleep(1 * (attempt + 1))
            
            return "Error: Failed to get a response after retries."
            
        except Exception as e:
            return f"Error: Unexpected failure during scene analysis: {str(e)}"
