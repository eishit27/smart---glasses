"""OCR / Text Reading module with multiple backends.

Backends:
1. EasyOCR (primary) — Fast, accurate, works offline, 80+ languages
2. Gemini Vision (enrichment) — Understands context (is it a menu? a sign? medicine?)
3. pytesseract (legacy fallback) — Last resort

The strategy: EasyOCR extracts the raw text quickly and offline.
If Gemini is available, it adds context ('This appears to be a restaurant
menu. The vegetarian options are...').
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
import numpy as np
import easyocr
import pytesseract
import torch
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class OCRReader:
    def __init__(self, api_key: Optional[str] = None, languages: List[str] = None):
        """Initializes EasyOCR reader and optional Gemini client."""
        if languages is None:
            languages = ['en']
        self.languages = languages
        self.api_key = api_key
        
        # Initialize EasyOCR
        self.reader = easyocr.Reader(self.languages, gpu=torch.cuda.is_available())
        
        # Initialize Gemini if API key is provided
        self.gemini_client = None
        if self.api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def read_text(self, frame: np.ndarray, use_context: bool = True) -> Dict[str, Any]:
        """
        Reads text from the frame using EasyOCR and optionally enriches it with Gemini.
        Falls back to pytesseract and then Gemini if local models fail.
        """
        # Step 1: Run local extraction
        try:
            local_result = await self.read_text_offline(frame)
            text = local_result.get("text", "")
            confidence = local_result.get("confidence", 0.0)
            backend = local_result.get("backend", "unknown")
        except Exception as e:
            logger.warning(f"Local OCR failed: {e}. Trying Gemini as fallback if available.")
            text = ""
            confidence = 0.0
            backend = "failed"
            
        # Step 2: Context enrichment or fallback via Gemini
        context = ""
        if use_context and self.gemini_client:
            try:
                prompt = f'Here is text extracted from an image: "{text}". What type of text is this (sign, menu, label, book, etc.)? Provide a brief, useful summary for a blind person.'
                if not text:
                    prompt = "Extract any text from this image and provide a brief, useful summary of what type of text it is (sign, menu, label, book, etc.) for a blind person."
                
                # Convert frame to PIL image or bytes for Gemini
                from PIL import Image
                img = Image.fromarray(frame)
                
                def _call_gemini():
                    # Synchronous call to Gemini SDK
                    response = self.gemini_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[img, prompt],
                        config=types.GenerateContentConfig(
                            temperature=0.3
                        )
                    )
                    return response.text
                    
                context = await asyncio.get_event_loop().run_in_executor(self.executor, _call_gemini)
                if not text:
                    text = context  # If we completely failed local OCR, use Gemini's text
                    backend = "gemini_fallback"
                    confidence = 0.8 # Arbitrary confidence for Gemini
            except Exception as e:
                logger.error(f"Gemini context generation failed: {e}")
                
        return {
            "text": text.strip() if text else "",
            "context": context.strip() if context else "",
            "confidence": confidence,
            "backend": backend
        }

    async def read_text_offline(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Extracts text from the image using only local models (EasyOCR, fallback pytesseract).
        """
        try:
            # Run EasyOCR
            def _run_easyocr():
                return self.reader.readtext(frame)
                
            results = await asyncio.get_event_loop().run_in_executor(self.executor, _run_easyocr)
            
            # Filter low confidence and sort
            valid_results = [r for r in results if r[2] >= 0.3]
            
            # Sort top-to-bottom, then left-to-right
            # r[0] is bbox: [[top_left, top_right, bottom_right, bottom_left]]
            valid_results.sort(key=lambda x: (x[0][0][1], x[0][0][0]))
            
            texts = [r[1] for r in valid_results]
            confidences = [r[2] for r in valid_results]
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                "text": " ".join(texts),
                "confidence": avg_confidence,
                "backend": "easyocr"
            }
        except Exception as e:
            logger.warning(f"EasyOCR failed: {e}. Falling back to pytesseract.")
            
            def _run_pytesseract():
                # Get data with confidences
                data = pytesseract.image_to_data(frame, output_type=pytesseract.Output.DICT)
                texts = []
                confs = []
                for i in range(len(data['text'])):
                    if float(data['conf'][i]) >= 30.0:  # pytesseract confidence is 0-100
                        txt = data['text'][i].strip()
                        if txt:
                            texts.append(txt)
                            confs.append(float(data['conf'][i]) / 100.0)
                return texts, confs
                
            texts, confs = await asyncio.get_event_loop().run_in_executor(self.executor, _run_pytesseract)
            avg_conf = sum(confs) / len(confs) if confs else 0.0
            
            return {
                "text": " ".join(texts),
                "confidence": avg_conf,
                "backend": "pytesseract"
            }
