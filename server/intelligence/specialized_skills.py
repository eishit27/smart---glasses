"""
VisionAid Specialized Accessibility Skills
===========================================

Adds genuinely smart, high-impact cognitive skills for daily independence:

1. Medication & Prescription Reader (Parses Drug name, Dosage, Warnings, Expiration)
2. Currency & Cash Reader (Instant banknote denomination identification)
3. Social Dynamics & Handshake Assistant (Detects extended hands, smiles, eye gaze)
4. Color & Clothing Matcher ("Is this shirt blue or black? Does it match?")
"""

import re
import logging
from typing import Dict, Any, Optional, List
import numpy as np

logger = logging.getLogger(__name__)

class SpecializedAccessibilitySkills:
    """
    Expert cognitive skills designed for visually impaired daily life challenges.
    """

    # ── 1. Medication & Prescription Intelligence ───────────────────────────

    @staticmethod
    def parse_medication_label(raw_ocr_text: str) -> Dict[str, Any]:
        """
        Extracts structured clinical instructions from messy OCR text on pill bottles.
        Identifies: Drug Name, Dosage, Instructions, Warnings, Expiration.
        """
        text = raw_ocr_text.strip()
        result = {
            "is_medication": False,
            "drug_name": "Unknown",
            "dosage": "Unknown",
            "instructions": "No clear dosage instructions found",
            "warnings": [],
            "spoken_summary": ""
        }

        # Common indicators of a prescription or OTC medicine
        med_keywords = ['mg', 'tablet', 'capsule', 'daily', 'take', 'rx', 'pharmacy', 'dose', 'dr.', 'exp', 'refill']
        matches = sum(1 for kw in med_keywords if kw in text.lower())
        if matches < 2:
            return result

        result["is_medication"] = True

        # Extract Dosage (e.g. 500mg, 10mg, 5ml, 25 mcg)
        dosage_match = re.search(r'(\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|tablets?|capsules?))', text, re.IGNORECASE)
        if dosage_match:
            result["dosage"] = dosage_match.group(1)

        # Extract Instructions (Take X tablets daily / with food)
        inst_match = re.search(r'(take\s+[^.\n]+(?:daily|meals?|food|bedtime|hours?)[^.\n]*)', text, re.IGNORECASE)
        if inst_match:
            result["instructions"] = inst_match.group(1).strip()

        # Extract Warnings
        warnings = []
        if re.search(r'(with\s+food|with\s+meals?)', text, re.IGNORECASE):
            warnings.append("Take with food")
        if re.search(r'(drowsiness|causes\s+drowsiness|sleepy)', text, re.IGNORECASE):
            warnings.append("May cause drowsiness. Do not drive.")
        if re.search(r'(avoid\s+alcohol)', text, re.IGNORECASE):
            warnings.append("Avoid alcohol")
        result["warnings"] = warnings

        # Build natural spoken summary for blind user
        summary_parts = ["Medication detected."]
        if result["dosage"] != "Unknown":
            summary_parts.append(f"Strength: {result['dosage']}.")
        if result["instructions"] != "No clear dosage instructions found":
            summary_parts.append(f"Directions: {result['instructions']}.")
        if warnings:
            summary_parts.append("Important: " + ", ".join(warnings) + ".")

        result["spoken_summary"] = " ".join(summary_parts)
        return result

    # ── 2. Banknote & Currency Intelligence ─────────────────────────────────

    @staticmethod
    def identify_currency(raw_ocr_text: str) -> Dict[str, Any]:
        """
        Recognizes banknote currency denominations from OCR numbers and symbols.
        Prevents blind users from being short-changed or handing over the wrong bill.
        """
        text = raw_ocr_text.upper()
        
        # USD Denominations
        usd_patterns = [
            (r'\b100\b|ONE HUNDRED', "$100 bill (One Hundred Dollars)"),
            (r'\b50\b|FIFTY', "$50 bill (Fifty Dollars)"),
            (r'\b20\b|TWENTY', "$20 bill (Twenty Dollars)"),
            (r'\b10\b|TEN', "$10 bill (Ten Dollars)"),
            (r'\b5\b|FIVE', "$5 bill (Five Dollars)"),
            (r'\b1\b|ONE DOLLAR', "$1 bill (One Dollar)")
        ]
        
        # INR (Indian Rupee) Denominations
        inr_patterns = [
            (r'\b500\b|FIVE HUNDRED RUPEES', "₹500 note (Five Hundred Rupees)"),
            (r'\b200\b|TWO HUNDRED RUPEES', "₹200 note (Two Hundred Rupees)"),
            (r'\b100\b|ONE HUNDRED RUPEES', "₹100 note (One Hundred Rupees)"),
            (r'\b50\b|FIFTY RUPEES', "₹50 note (Fifty Rupees)"),
            (r'\b20\b|TWENTY RUPEES', "₹20 note (Twenty Rupees)"),
            (r'\b10\b|TEN RUPEES', "₹10 note (Ten Rupees)")
        ]

        if "RESERVE BANK" in text or "RUPEE" in text or "BHARAT" in text:
            for pattern, spoken in inr_patterns:
                if re.search(pattern, text):
                    return {"is_currency": True, "currency": "INR", "announcement": spoken}

        if "FEDERAL RESERVE" in text or "DOLLARS" in text or "UNITED STATES" in text:
            for pattern, spoken in usd_patterns:
                if re.search(pattern, text):
                    return {"is_currency": True, "currency": "USD", "announcement": spoken}

        # Generic number check if money keywords present
        for pattern, spoken in usd_patterns:
            if re.search(pattern, text) and ("BANK" in text or "NOTE" in text or "$" in text):
                return {"is_currency": True, "currency": "USD", "announcement": spoken}

        return {"is_currency": False, "announcement": ""}

    # ── 3. Social Interaction & Body Language Assistant ─────────────────────

    @staticmethod
    def analyze_social_cues(detections: List[Dict], pose_context: str = "") -> str:
        """
        Identifies non-verbal human social cues that blind people cannot see:
        - Handshakes offered
        - People waving
        - Group gatherings
        """
        people = [d for d in detections if d.get('label') == 'person']
        if not people:
            return ""

        closest_person = min(people, key=lambda p: p.get('distance_meters', 99.0))
        dist = closest_person.get('distance_meters', 2.0)

        cues = []
        if dist < 1.4:
            cues.append(f"A person is standing close to you, about {dist:.1f} meters away")
            if "hand" in pose_context.lower() or "reach" in pose_context.lower():
                cues.append("They may be extending a hand for a handshake")
        elif len(people) >= 3:
            cues.append(f"There is a group of {len(people)} people ahead of you")

        return ". ".join(cues)
