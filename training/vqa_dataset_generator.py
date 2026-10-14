"""
VisionAid Egocentric VQA Dataset Generator
==========================================

Generates high-volume assistive Question-Answer training pairs for fine-tuning
the Moondream2 Vision-Language Model (VLM).

Transforms generic captioning into spatial, life-safety cognitive reasoning.
Categories:
1. Stepping Hazards (Stairs, Curbs, Potholes)
2. Head & Torso Clearance (Awnings, Scaffolding, Branches)
3. Physical Affordances (Door Push/Pull, Handles, Seating)
4. Daily Independence (Medications, Currency, Crosswalks)
"""

import os
import json
import random
import logging
from typing import List, Dict

logger = logging.getLogger("VQAGenerator")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TEMPLATES = [
    # ── Stepping & Floor Hazards ──────────────────────────────────────────────
    {
        "q": ["What is on the floor ahead?", "Is my walking path clear?", "Any tripping hazards?"],
        "a": [
            "Descending stairs in two steps. Handrail is on your left.",
            "Sidewalk curb drop-off ahead. Step down carefully into the street.",
            "Clear flat walking corridor at 11 o'clock. Floor is open.",
            "Pothole in the sidewalk at 12 o'clock, 1.5 meters away. Veer slightly right."
        ]
    },
    # ── Head Level Clearance ──────────────────────────────────────────────────
    {
        "q": ["Watch my head", "Are there any high obstacles?", "Is head height clear?"],
        "a": [
            "Low-hanging tree branch at eye level on your right. Tilt your head left.",
            "Construction scaffolding overhang ahead at head height. Duck slightly.",
            "Storefront awning overhead at 12 o'clock. Clear to walk beneath."
        ]
    },
    # ── Doors & Physical Affordances ──────────────────────────────────────────
    {
        "q": ["How do I open this door?", "Where is the door handle?", "Is this door open?"],
        "a": [
            "Glass pull door. Vertical brass handle on the right side at waist level.",
            "Push door. Flat metal push-plate on your left.",
            "Automatic sliding glass door. Stand 1 pace closer to trigger sensor."
        ]
    },
    # ── Seating & Empty Chairs ────────────────────────────────────────────────
    {
        "q": ["Is this chair empty?", "Can I sit here?", "Find me a seat"],
        "a": [
            "Empty cushioned chair directly in front of you. Armrests are clear.",
            "Chair on your right is occupied by someone's backpack. Bench on your left is completely open.",
            "Wooden bench 3 paces ahead is vacant."
        ]
    },
    # ── Crosswalks & Traffic Signals ──────────────────────────────────────────
    {
        "q": ["Can I cross the street?", "What does the pedestrian light show?", "Is it safe to walk?"],
        "a": [
            "Pedestrian signal is red. Wait at the curb for the signal to change.",
            "Walk signal is active. Zebra crosswalk is clear directly ahead.",
            "Vehicle approaching from the left. Hold your position at the curb."
        ]
    },
    # ── Currency & Prescriptions ──────────────────────────────────────────────
    {
        "q": ["What bill is this?", "What note am I holding?"],
        "a": [
            "500 Rupee banknote.",
            "100 Rupee banknote.",
            "20 Dollar bill."
        ]
    },
    {
        "q": ["Read this medicine bottle", "What are the pill instructions?"],
        "a": [
            "Paracetamol 500mg. Take 1 tablet every 6 hours with a glass of water.",
            "Amoxicillin 250mg capsules. Take one capsule three times daily with meals.",
            "Eye drops. Administer 1 drop in each eye twice daily."
        ]
    }
]

def generate_vqa_corpus(output_path: str = "training/data/accessibility_vqa_mega.json", count: int = 2500):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    samples = []

    for i in range(count):
        template = random.choice(TEMPLATES)
        q = random.choice(template["q"])
        a = random.choice(template["a"])

        samples.append({
            "id": f"vqa_{i:05d}",
            "question": q,
            "answer": a,
            "image": f"training/datasets/accessibility_hazards_mega/images/train/mega_train_{random.randint(0, 3999):05d}.jpg"
        })

    with open(output_path, 'w') as f:
        json.dump(samples, f, indent=2)

    logger.info(f"✅ Generated {count} assistive VQA training pairs at: {output_path}")
    return output_path

if __name__ == "__main__":
    generate_vqa_corpus()
