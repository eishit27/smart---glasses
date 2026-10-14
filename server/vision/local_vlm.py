"""
Local Vision-Language Model (VLM) Module
=========================================

Uses Moondream2 (vikhyatk/moondream2) — a lightweight 1.86B parameter VLM
optimized to run directly on consumer laptops, mini-PCs, and mobile edge chips.

Provides:
- 100% OFFLINE natural-language scene descriptions (NO internet, NO API keys)
- Visual Question Answering (VQA) for blind users:
  - "Is the traffic light red or green?"
  - "What is the person in front of me holding?"
  - "Is the door open or closed?"
"""

import asyncio
import logging
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

class LocalVLM:
    """
    On-device Vision-Language Model for offline scene comprehension.
    """

    def __init__(self, model_id: str = "vikhyatk/moondream2", device: str = "auto"):
        self.model_id = model_id
        self.device = device
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.model = None
        self.tokenizer = None
        self._initialized = False

    def _lazy_init(self):
        """Initializes the model in background thread upon first request."""
        if self._initialized:
            return

        import torch
        if self.device == "auto":
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"

        logger.info(f"Loading local VLM ({self.model_id}) on {self.device}...")
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision="2024-08-26")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                trust_remote_code=True,
                revision="2024-08-26",
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32
            ).to(self.device)
            self._initialized = True
            logger.info("Local VLM (Moondream2) loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load Moondream2 ({e}). Offline scene captioning will use YOLO summaries.")
            self.model = None
            self._initialized = True

    def _caption_sync(self, pil_image: Image.Image) -> str:
        """Generates a scene description synchronously."""
        self._lazy_init()
        if not self.model or not self.tokenizer:
            return ""

        try:
            image_embeds = self.model.encode_image(pil_image)
            prompt = (
                "You are the sensory visual cortex for a blind person walking. "
                "Prioritize: 1. Stepping hazards (curbs, drop-offs, stairs, puddles). "
                "2. Head/torso obstacles (branches, glass, poles). "
                "3. Clear walking path. "
                "4. People interacting with user. "
                "Respond in 1-2 calm, concise sentences with clock directions (e.g., 'at 11 o'clock')."
            )
            caption = self.model.answer_question(image_embeds, prompt, self.tokenizer)
            return caption.strip()
        except Exception as e:
            logger.error(f"Error in local VLM captioning: {e}")
            return ""

    def _vqa_sync(self, pil_image: Image.Image, question: str) -> str:
        """Answers a specific visual question synchronously."""
        self._lazy_init()
        if not self.model or not self.tokenizer:
            return ""

        try:
            image_embeds = self.model.encode_image(pil_image)
            guided_question = (
                f"Context: The user is blind and navigating. Question: {question}. "
                "Give a direct, factual answer focusing on physical orientation and safety."
            )
            answer = self.model.answer_question(image_embeds, guided_question, self.tokenizer)
            return answer.strip()
        except Exception as e:
            logger.error(f"Error in local VLM VQA: {e}")
            return ""

    async def describe_scene(self, frame: np.ndarray) -> str:
        """
        Asynchronously generates a rich scene description from an image frame.
        """
        # Convert BGR (OpenCV) to RGB (PIL)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._caption_sync, pil_img)

    async def answer_question(self, frame: np.ndarray, question: str) -> str:
        """
        Asynchronously answers a specific question about the camera frame.
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._vqa_sync, pil_img, question)

    @property
    def is_available(self) -> bool:
        """Returns True if the local model loaded successfully."""
        return self.model is not None
