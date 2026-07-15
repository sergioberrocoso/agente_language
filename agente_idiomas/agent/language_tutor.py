import json
from pathlib import Path

class LanguageTutorAgent:
    def __init__(self, language="English"):
        self.language = language
        self.core_vocab = []
        self.missions = []
        self.current_mission = None

    # -----------------------------
    # CARGA DE DATOS
    # -----------------------------
    def load_core_vocab(self, filepath: str):
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"El archivo de vocabulario no existe: {filepath}")

        with open(path, "r", encoding="utf-8") as f:
            self.core_vocab = json.load(f)

    def load_missions(self, filepath: str):
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"El archivo de misiones no existe: {filepath}")

        with open(path, "r", encoding="utf-8") as f:
            self.missions = json.load(f)

    # -----------------------------
    # SELECCIÓN DE MISIÓN
    # -----------------------------
    def select_mission(self, mission_id: str):
        for mission in self.missions:
            if mission["id"] == mission_id:
                self.current_mission = mission
                return mission
        raise ValueError(f"Misión no encontrada: {mission_id}")

    def get_mission_vocabulary(self):
        if not self.current_mission:
            raise ValueError("No hay misión seleccionada.")

        tags = self.current_mission.get("vocabulary_tags", [])
        filtered = [w for w in self.core_vocab if any(tag in w["tags"] for tag in tags)]
        return filtered

    # -----------------------------
    # INTELIGENCIA DE MISIÓN ABIERTA
    # -----------------------------
    def analyze_description(self, description: str):
        keywords = {
            "animals": ["dog", "cat", "park", "pet"],
            "actions": ["run", "eat", "walk", "play"],
            "food": ["restaurant", "eat", "menu", "food"],
            "travel": ["airport", "hotel", "flight", "travel"]
        }

        detected_tags = []

        for tag, words in keywords.items():
            if any(word in description.lower() for word in words):
                detected_tags.append(tag)

        return detected_tags

    def generate_dialogue(self, description: str, tags: list):
        if "animals" in tags:
            return [
                {"speaker": "Tutor", "text": "Do you have any pets?"},
                {"speaker": "Student", "text": "Yes, I have a dog."},
                {"speaker": "Tutor", "text": "Nice! What do you usually do with your dog in the park?"}
            ]

        if "food" in tags:
            return [
                {"speaker": "Tutor", "text": "What kind of food do you like?"},
                {"speaker": "Student", "text": "I love Italian food."},
                {"speaker": "Tutor", "text": "Great! Do you often go to restaurants?"}
            ]

        return [
            {"speaker": "Tutor", "text": f"Let's talk about: {description}"},
            {"speaker": "Student", "text": "Sure!"}
        ]

    def generate_exercises(self, tags: list):
        exercises = []

        if "animals" in tags:
            exercises.append({"type": "translate", "text": "Translate: My dog is very friendly"})
            exercises.append({"type": "fill_blank", "text": "I usually ____ my dog in the park"})

        if "actions" in tags:
            exercises.append({"type": "choose", "text": "Choose the correct verb: run / eat / sleep"})

        if not exercises:
            exercises.append({"type": "translate", "text": "Translate: I want to practice English"})

        return exercises

    def create_open_mission(self, description: str, mission_id: str):
        tags = self.analyze_description(description)

        new_mission = {
            "id": mission_id,
            "name": description,
            "goal": description,
            "vocabulary_tags": tags,
            "dialogues": self.generate_dialogue(description, tags),
            "exercises": self.generate_exercises(tags)
        }

        self.missions.append(new_mission)
        self.current_mission = new_mission
        return new_mission

    # -----------------------------
    # FLASHCARDS
    # -----------------------------
    def generate_flashcards(self):
        if not self.current_mission:
            raise ValueError("No hay misión seleccionada para generar flashcards.")

        vocab = self.get_mission_vocabulary()
        flashcards = []

        for item in vocab:
            word = item["word"]

            flashcards.append({
                "front": word,
                "back": {
                    "definition": f"Definition of '{word}' (placeholder)",
                    "example": f"Example sentence using '{word}' (placeholder)",
                    "translation": f"Traducción de '{word}' (placeholder)"
                }
            })

        return flashcards
