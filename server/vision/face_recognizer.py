"""
Face recognition module for the VisionAid project.
"""

import asyncio
import os
import pickle
from typing import List, Dict, Any, Tuple

import cv2
import numpy as np
import face_recognition

class FaceRecognizer:
    """
    Recognizes faces and manages a database of known faces.
    """

    def __init__(self, db_path: str = "known_faces.pkl"):
        """
        Initializes the face recognizer.

        Args:
            db_path: Path to the file where known faces are saved.
        """
        self.db_path = db_path
        self.known_face_encodings: List[np.ndarray] = []
        self.known_face_names: List[str] = []
        self._load_db()

    def _load_db(self) -> None:
        """Loads the face database from disk."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "rb") as f:
                    data = pickle.load(f)
                    self.known_face_encodings = data.get("encodings", [])
                    self.known_face_names = data.get("names", [])
            except Exception as e:
                print(f"Error loading face database: {e}")

    def _save_db(self) -> None:
        """Saves the face database to disk."""
        try:
            with open(self.db_path, "wb") as f:
                pickle.dump({
                    "encodings": self.known_face_encodings,
                    "names": self.known_face_names
                }, f)
        except Exception as e:
            print(f"Error saving face database: {e}")

    def register_face(self, name: str, frame: np.ndarray) -> bool:
        """
        Registers a new face in the database.

        Args:
            name: Name of the person.
            frame: Image containing the person's face.

        Returns:
            True if registration was successful, False otherwise.
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        if not face_locations:
            return False
            
        # Get encoding of the largest face if multiple are present
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        if face_encodings:
            self.known_face_encodings.append(face_encodings[0])
            self.known_face_names.append(name)
            self._save_db()
            return True
            
        return False

    def remove_face(self, name: str) -> bool:
        """
        Removes a face from the database.

        Args:
            name: Name of the person to remove.

        Returns:
            True if removed successfully, False if name not found.
        """
        if name in self.known_face_names:
            index = self.known_face_names.index(name)
            self.known_face_names.pop(index)
            self.known_face_encodings.pop(index)
            self._save_db()
            return True
        return False

    def list_known_faces(self) -> List[str]:
        """
        Returns a list of all registered faces.
        """
        return self.known_face_names.copy()

    async def identify_faces(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Identifies faces in the given frame.

        Args:
            frame: Numpy array representing the image frame (BGR format).

        Returns:
            List of dictionaries containing name, location, and confidence.
            Location is 'left', 'center', or 'right' for spatial audio cues.
        """
        # Run synchronous face_recognition tasks in a threadpool or fast enough inline
        # In actual practice, it might be better to offload to executor
        # but inline is fine for this async wrapper
        results = []
        
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame)
        if not face_locations:
            return results
            
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        frame_width = small_frame.shape[1]
        
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            name = "unknown"
            confidence = "low"
            
            if self.known_face_encodings:
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                best_match_index = int(np.argmin(face_distances))
                
                if face_distances[best_match_index] < 0.6:  # Threshold for recognition
                    name = self.known_face_names[best_match_index]
                    confidence = "high" if face_distances[best_match_index] < 0.4 else "medium"
            
            # Determine spatial location
            center_x = (left + right) / 2
            if center_x < frame_width / 3:
                spatial_location = "left"
            elif center_x > 2 * frame_width / 3:
                spatial_location = "right"
            else:
                spatial_location = "center"
                
            results.append({
                "name": name,
                "location": spatial_location,
                "confidence": confidence
            })
            
        return results
