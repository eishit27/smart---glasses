"""
VisionAid SOTA Foundation Vision-Language Model (VLM) Engine
============================================================

Upgrades the cognitive reasoning brain to the highest-performing open-source
multimodal models in the world:

1. Qwen2.5-VL (3B / 7B) — Undisputed #1 Open-Source VLM:
   - Pixel-accurate visual spatial grounding (predicts exact bounding boxes for questions).
   - Reads tiny text, medicine bottles, expiration dates, and complex urban signs.
   - Dynamic resolution processing (preserves fine visual details).
2. Microsoft Florence-2-Large (0.77B):
   - Ultra-fast (sub-100ms) dense captioning and open-vocabulary grounding.
   - Pre-trained on 5.4 Billion annotations across 126 Million real-world images.
3. Fallback: Moondream2 (1.86B) for ultra-low memory devices.
"""

import os
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, List
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

class SOTAVisionLanguageEngine:
    """
    World-class multimodal reasoning engine utilizing Qwen2.5-VL and Florence-2.
    """

    def __init__(
        self,
        primary_model: str = "Qwen/Qwen2.5-VL-3B-Instruct",
        fast_model: str = "microsoft/Florence-2-large",
        device: str = "auto"
    ):
        self.primary_model_id = primary_model
        self.fast_model_id = fast_model
        self.device = device
        self._executor = ThreadPoolExecutor(max_workers=1)

        self.model = None
        self.processor = None
        self.active_backend = "none"
        self._initialized = False

    def _lazy_init(self):
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

        logger.info(f"Initializing World-Class VLM on {self.device}...")

        # ── Tier 1: Try Loading Qwen2.5-VL ─────────────────────────────────
        try:
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
            logger.info(f"Loading SOTA Qwen2.5-VL ({self.primary_model_id})...")
            self.processor = AutoProcessor.from_pretrained(self.primary_model_id)
            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                self.primary_model_id,
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                device_map=self.device
            )
            self.active_backend = "qwen2.5-vl"
            self._initialized = True
            logger.info("✅ Qwen2.5-VL loaded successfully (Tier 1 SOTA Multimodal Brain).")
            return
        except Exception as e:
            logger.warning(f"Could not initialize Qwen2.5-VL ({e}). Trying Florence-2...")

        # ── Tier 2: Try Loading Microsoft Florence-2 ───────────────────────
        try:
            from transformers import AutoProcessor, AutoModelForCausalLM
            logger.info(f"Loading Microsoft Florence-2-Large ({self.fast_model_id})...")
            self.processor = AutoProcessor.from_pretrained(self.fast_model_id, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.fast_model_id,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32
            ).to(self.device)
            self.active_backend = "florence-2"
            self._initialized = True
            logger.info("✅ Microsoft Florence-2-Large loaded successfully (Sub-100ms Grounding).")
            return
        except Exception as e:
            logger.warning(f"Could not load Florence-2 ({e}). Falling back to Moondream2.")

        # ── Tier 3: Fallback to Moondream2 ─────────────────────────────────
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            logger.info("Loading Moondream2 (Fallback VLM)...")
            tokenizer = AutoTokenizer.from_pretrained("vikhyatk/moondream2", revision="2024-08-26")
            model = AutoModelForCausalLM.from_pretrained(
                "vikhyatk/moondream2",
                trust_remote_code=True,
                revision="2024-08-26",
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32
            ).to(self.device)
            self.model = model
            self.processor = tokenizer
            self.active_backend = "moondream2"
            self._initialized = True
            logger.info("✅ Moondream2 loaded successfully.")
        except Exception as e:
            logger.error(f"All VLM models failed to initialize: {e}")
            self.model = None
            self._initialized = True

    def _sync_reasoning(self, pil_image: Image.Image, prompt: str) -> str:
        self._lazy_init()
        if self.model is None:
            return ""

        try:
            # 1. Qwen2.5-VL Execution
            if self.active_backend == "qwen2.5-vl":
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": pil_image},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ]
                text_prompt = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                inputs = self.processor(text=[text_prompt], images=[pil_image], padding=True, return_tensors="pt").to(self.device)
                generated_ids = self.model.generate(**inputs, max_new_tokens=128)
                output_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
                return output_text.strip()

            # 2. Florence-2 Execution
            elif self.active_backend == "florence-2":
                task_prompt = "<MORE_DETAILED_CAPTION>" if "describe" in prompt.lower() else prompt
                inputs = self.processor(text=task_prompt, images=pil_image, return_tensors="pt").to(self.device)
                generated_ids = self.model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=128,
                    num_beams=3
                )
                generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
                parsed = self.processor.post_process_generation(generated_text, task=task_prompt, image_size=(pil_image.width, pil_image.height))
                return str(parsed.get(task_prompt, generated_text)).strip()

            # 3. Moondream2 Execution
            elif self.active_backend == "moondream2":
                image_embeds = self.model.encode_image(pil_image)
                answer = self.model.answer_question(image_embeds, prompt, self.processor)
                return answer.strip()

        except Exception as e:
            logger.error(f"Error during VLM inference ({self.active_backend}): {e}")
            return ""

    async def answer_visual_query(self, frame: np.ndarray, question: str) -> str:
        """
        Asynchronously reasons over an image frame with SOTA multimodal intelligence.
        """
        import cv2
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)

        # Egocentric assistive prompt tuning
        system_grounded_prompt = (
            f"You are the visual cortex for a blind person. Context: The user is walking. "
            f"Question: {question}. "
            "Give a direct, calm, actionable answer. State clock directions (e.g. 'at 11 o'clock') and physical distances."
        )

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._sync_reasoning, pil_img, system_grounded_prompt)

    async def describe_scene(self, frame: np.ndarray) -> str:
        """
        Generates a concise, safety-first scene description.
        """
        import cv2
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)

        prompt = (
            "Describe this scene for a blind person walking. Prioritize in order: "
            "1. Stepping hazards (curbs, drop-offs, stairs). "
            "2. Head/torso obstacles (branches, glass, poles). "
            "3. Clear walking path. "
            "Respond in 1-2 calm, concise sentences with clock directions. No filler words."
        )

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._sync_reasoning, pil_img, prompt)

    async def answer_question(self, frame: np.ndarray, question: str) -> str:
        """Alias for answer_visual_query for drop-in compatibility."""
        return await self.answer_visual_query(frame, question)
