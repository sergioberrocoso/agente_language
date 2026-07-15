from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Corrector de gramática básico (reglas sin LLM)
# ---------------------------------------------------------------------------

# Contracciones escritas sin apóstrofe
_CONTRACTION_RULES: list[tuple[str, str, str]] = [
    (r"\bdont\b",      "don't",   "Missing apostrophe in contraction"),
    (r"\bcant\b",      "can't",   "Missing apostrophe in contraction"),
    (r"\bwont\b",      "won't",   "Missing apostrophe in contraction"),
    (r"\bcouldnt\b",   "couldn't","Missing apostrophe in contraction"),
    (r"\bwouldnt\b",   "wouldn't","Missing apostrophe in contraction"),
    (r"\bshouldnt\b",  "shouldn't","Missing apostrophe in contraction"),
    (r"\bisnt\b",      "isn't",   "Missing apostrophe in contraction"),
    (r"\barent\b",     "aren't",  "Missing apostrophe in contraction"),
    (r"\bwasnt\b",     "wasn't",  "Missing apostrophe in contraction"),
    (r"\bwerent\b",    "weren't", "Missing apostrophe in contraction"),
    (r"\bhasnt\b",     "hasn't",  "Missing apostrophe in contraction"),
    (r"\bhavent\b",    "haven't", "Missing apostrophe in contraction"),
    (r"\bhadnt\b",     "hadn't",  "Missing apostrophe in contraction"),
    (r"\bdidnt\b",     "didn't",  "Missing apostrophe in contraction"),
    (r"\bdoesnt\b",    "doesn't", "Missing apostrophe in contraction"),
    (r"\bthats\b",     "that's",  "Missing apostrophe in contraction"),
    (r"\bweve\b",      "we've",   "Missing apostrophe in contraction"),
    (r"\btheyre\b",    "they're", "Missing apostrophe in contraction"),
    (r"\btheyve\b",    "they've", "Missing apostrophe in contraction"),
    (r"\byoure\b",     "you're",  "Missing apostrophe in contraction"),
    (r"\byouve\b",     "you've",  "Missing apostrophe in contraction"),
    (r"\bim\b",        "I'm",     "Missing apostrophe in contraction"),
    (r"\bive\b",       "I've",    "Missing apostrophe in contraction"),
    (r"\bill\b",       "I'll",    "Missing apostrophe in contraction"),
    # Note: "I'd" is excluded — "id" collides too often with other words
]

# Concordancia sujeto-verbo (3.ª persona singular, presente simple)
_THIRD_PERSON_VERBS: list[str] = [
    "go", "have", "do", "want", "like", "come", "work", "live", "speak",
    "run", "eat", "drink", "sleep", "read", "write", "play", "study",
    "watch", "teach", "know", "think", "feel", "need", "help", "walk",
    "talk", "make", "take", "find", "give", "use", "start", "show",
    "ask", "love", "say", "tell", "follow", "happen", "seem", "stay",
    "try", "keep", "put", "get", "bring", "carry", "turn", "hold",
    "wait", "choose", "look", "stand", "sit", "call", "visit", "buy",
    "sell", "pay", "send", "receive", "understand", "remember", "forget",
    "learn", "hear", "see", "meet", "mean", "matter", "last", "change",
]

# Irregulares: base → 3.ª persona
_IRREGULAR_3SG: dict[str, str] = {
    "go": "goes",
    "do": "does",
    "have": "has",
    "be": "is",
}

# Reglas de "ser/estar"
_BE_RULES: list[tuple[str, str, str]] = [
    (r"\bI\s+are\b",    "I am",    "Subject-verb agreement: use 'am' with 'I'"),
    (r"\bI\s+is\b",     "I am",    "Subject-verb agreement: use 'am' with 'I'"),
    (r"\byou\s+am\b",   "you are", "Subject-verb agreement: use 'are' with 'you'"),
    (r"\byou\s+is\b",   "you are", "Subject-verb agreement: use 'are' with 'you'"),
    (r"\bhe\s+am\b",    "he is",   "Subject-verb agreement: use 'is' with 'he'"),
    (r"\bhe\s+are\b",   "he is",   "Subject-verb agreement: use 'is' with 'he'"),
    (r"\bshe\s+am\b",   "she is",  "Subject-verb agreement: use 'is' with 'she'"),
    (r"\bshe\s+are\b",  "she is",  "Subject-verb agreement: use 'is' with 'she'"),
    (r"\bit\s+am\b",    "it is",   "Subject-verb agreement: use 'is' with 'it'"),
    (r"\bit\s+are\b",   "it is",   "Subject-verb agreement: use 'is' with 'it'"),
    (r"\bwe\s+am\b",    "we are",  "Subject-verb agreement: use 'are' with 'we'"),
    (r"\bwe\s+is\b",    "we are",  "Subject-verb agreement: use 'are' with 'we'"),
    (r"\bthey\s+am\b",  "they are","Subject-verb agreement: use 'are' with 'they'"),
    (r"\bthey\s+is\b",  "they are","Subject-verb agreement: use 'are' with 'they'"),
]

# Artículo "a" vs "an"
_VOWEL_SOUNDS = re.compile(
    r"\ba\s+([aeiouAEIOU]\w*)", re.IGNORECASE
)
_CONSONANT_AN = re.compile(
    r"\ban\s+([^aeiouAEIOU\s]\w*)", re.IGNORECASE
)


def _make_3sg(verb: str) -> str:
    """Devuelve la forma de 3.ª persona singular del presente."""
    if verb in _IRREGULAR_3SG:
        return _IRREGULAR_3SG[verb]
    if verb.endswith(("s", "sh", "ch", "x", "z", "o")):
        return verb + "es"
    if len(verb) >= 2 and verb.endswith("y") and verb[-2] not in "aeiou":
        return verb[:-1] + "ies"
    return verb + "s"


def _correct_text(text: str) -> list[dict]:
    """Aplica reglas gramaticales y devuelve la lista de correcciones."""
    corrections: list[dict] = []

    # 1. Contracciones
    for pattern, suggestion, explanation in _CONTRACTION_RULES:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            corrections.append({
                "original": m.group(0),
                "suggested": suggestion,
                "position": m.start(),
                "rule": "contraction",
                "explanation": explanation,
            })

    # 2. Concordancia be
    for pattern, suggestion, explanation in _BE_RULES:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            corrections.append({
                "original": m.group(0),
                "suggested": suggestion,
                "position": m.start(),
                "rule": "subject_verb_be",
                "explanation": explanation,
            })

    # 3. Concordancia 3.ª persona (he/she/it + base verb)
    for verb in _THIRD_PERSON_VERBS:
        pat = rf"\b(he|she|it)\s+({re.escape(verb)})\b"
        for m in re.finditer(pat, text, re.IGNORECASE):
            subj = m.group(1)
            v = m.group(2)
            if v.lower() == verb:  # está en base form (no conjugada)
                corrected_v = _make_3sg(verb)
                corrections.append({
                    "original": m.group(0),
                    "suggested": f"{subj} {corrected_v}",
                    "position": m.start(),
                    "rule": "third_person_singular",
                    "explanation": (
                        f"Subject-verb agreement: '{subj}' requires "
                        f"third-person singular form '{corrected_v}'"
                    ),
                })

    # 4. Artículo "a" antes de vocal
    for m in _VOWEL_SOUNDS.finditer(text):
        corrections.append({
            "original": m.group(0),
            "suggested": "an " + m.group(1),
            "position": m.start(),
            "rule": "article_a_an",
            "explanation": "Use 'an' before words starting with a vowel sound",
        })

    # 5. Artículo "an" antes de consonante
    for m in _CONSONANT_AN.finditer(text):
        corrections.append({
            "original": m.group(0),
            "suggested": "a " + m.group(1),
            "position": m.start(),
            "rule": "article_a_an",
            "explanation": "Use 'a' before words starting with a consonant sound",
        })

    # Eliminar duplicados por posición (prioridad: la primera regla detectada)
    seen: set[int] = set()
    unique: list[dict] = []
    for c in sorted(corrections, key=lambda x: x["position"]):
        if c["position"] not in seen:
            seen.add(c["position"])
            unique.append(c)

    return unique


# ---------------------------------------------------------------------------
# Respuestas conversacionales del tutor (sin LLM)
# ---------------------------------------------------------------------------
_GREETING_RESPONSES = [
    "Hello! I'm your English tutor. What would you like to practice today?",
    "Hi there! Ready to practise your English? Tell me what you'd like to work on.",
    "Good to see you! What topic shall we explore today?",
]

_ENCOURAGEMENT = [
    "Great job! Keep going.",
    "Well done! That was good.",
    "Nice work! You're making progress.",
    "Excellent! You're getting better.",
]

_CORRECTION_INTRO = [
    "Almost! A small correction: ",
    "Good try! Just a small fix: ",
    "Nearly there! One thing to note: ",
]

_FILL_BLANK_PROMPT = "Now let's practise! Fill in the blank: "

# Respuestas por tag de misión
_TOPIC_RESPONSES: dict[str, list[str]] = {
    "animals": [
        "Interesting! What's your favourite animal?",
        "Do you have any pets at home?",
        "Tell me more about animals you like.",
    ],
    "food": [
        "What kind of food do you enjoy most?",
        "Do you like cooking? What do you usually make?",
        "Describe a meal you really enjoyed recently.",
    ],
    "travel": [
        "Where would you like to travel?",
        "Have you visited any interesting places recently?",
        "What do you usually pack when you travel?",
    ],
    "work": [
        "What do you do for work?",
        "Describe a typical day at your job.",
        "What skills are important in your profession?",
    ],
    "school": [
        "What subjects did you study?",
        "What was your favourite class at school?",
        "How do you usually prepare for exams?",
    ],
    "weather": [
        "What's the weather like where you live?",
        "Do you prefer hot or cold weather?",
        "How does the weather affect your mood?",
    ],
}

_DEFAULT_RESPONSES = [
    "That's interesting! Can you tell me more?",
    "Good! Now let me ask you something related.",
    "I see. How would you describe that in more detail?",
]


# ---------------------------------------------------------------------------
# LanguageTutorAgent
# ---------------------------------------------------------------------------
class LanguageTutorAgent:
    def __init__(self, language: str = "English"):
        self.language = language
        self.core_vocab: list[dict] = []
        self.missions: list[dict] = []
        self.current_mission: Optional[dict] = None

    # ------------------------------------------------------------------
    # CARGA DE DATOS
    # ------------------------------------------------------------------
    def load_core_vocab(self, filepath: str) -> None:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"El archivo de vocabulario no existe: {filepath}")
        with open(path, "r", encoding="utf-8") as f:
            self.core_vocab = json.load(f)

    def load_missions(self, filepath: str) -> None:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"El archivo de misiones no existe: {filepath}")
        with open(path, "r", encoding="utf-8") as f:
            self.missions = json.load(f)

    # ------------------------------------------------------------------
    # SELECCIÓN DE MISIÓN
    # ------------------------------------------------------------------
    def select_mission(self, mission_id: str) -> dict:
        for mission in self.missions:
            if mission["id"] == mission_id:
                self.current_mission = mission
                return mission
        raise ValueError(f"Misión no encontrada: {mission_id}")

    def get_mission_vocabulary(self) -> list[dict]:
        if not self.current_mission:
            raise ValueError("No hay misión seleccionada.")
        tags = self.current_mission.get("vocabulary_tags", [])
        return [w for w in self.core_vocab if any(tag in w.get("tags", []) for tag in tags)]

    # ------------------------------------------------------------------
    # CORRECCIÓN DE TEXTO
    # ------------------------------------------------------------------
    def correct_text(self, text: str) -> list[dict]:
        """Analiza *text* y devuelve una lista de correcciones gramaticales.

        Cada corrección tiene:
            - ``original``:    fragmento tal como aparece en el texto
            - ``suggested``:   forma corregida
            - ``position``:    índice de carácter en el texto original
            - ``rule``:        nombre de la regla aplicada
            - ``explanation``: mensaje explicativo en inglés
        """
        return _correct_text(text)

    def apply_corrections(self, text: str) -> str:
        """Devuelve una versión corregida del texto aplicando las reglas."""
        corrections = self.correct_text(text)
        # Aplicar de derecha a izquierda para no alterar posiciones
        result = text
        for c in sorted(corrections, key=lambda x: x["position"], reverse=True):
            start = c["position"]
            end = start + len(c["original"])
            result = result[:start] + c["suggested"] + result[end:]
        return result

    # ------------------------------------------------------------------
    # EJERCICIOS DE RELLENO (fill-in-the-blank)
    # ------------------------------------------------------------------
    def generate_fill_blank(self, sentence: str) -> dict:
        """Genera un ejercicio de completar huecos a partir de una oración.

        Busca en la oración palabras presentes en el vocabulario de la
        misión activa (o en ``core_vocab``) y las sustituye por ``___``.
        Devuelve un dict con:
            - ``exercise``: oración con hueco(s)
            - ``blanks``:   lista de palabras retiradas
            - ``original``: oración original
        """
        vocab_words = self.get_mission_vocabulary() if self.current_mission else self.core_vocab
        target_words = [w["word"] for w in vocab_words]

        blanked = sentence
        found_blanks: list[str] = []

        for word in target_words:
            pat = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
            if pat.search(sentence):
                blanked = pat.sub("___", blanked)
                found_blanks.append(word)

        if not found_blanks:
            # Si no hay vocab coincidente, blanquear el primer verbo/sustantivo
            words_in_sentence = sentence.split()
            stop_words = {"the", "a", "an", "is", "are", "was", "were",
                          "i", "you", "he", "she", "it", "we", "they",
                          "in", "on", "at", "to", "for", "of", "and", "but"}
            for w in words_in_sentence:
                clean = w.strip(".,!?;:")
                if clean.lower() not in stop_words and len(clean) > 2:
                    pat = re.compile(r"\b" + re.escape(clean) + r"\b", re.IGNORECASE)
                    blanked = pat.sub("___", blanked, count=1)
                    found_blanks.append(clean)
                    break

        return {"original": sentence, "exercise": blanked, "blanks": found_blanks}

    # ------------------------------------------------------------------
    # CONVERSACIÓN
    # ------------------------------------------------------------------
    def chat(self, user_message: str, history: Optional[list[dict]] = None) -> dict:
        """Procesa un mensaje del alumno y devuelve la respuesta del tutor.

        *history* es una lista de dicts ``{"role": "student"|"tutor", "text": ...}``.
        Devuelve un dict con:
            - ``response``:    texto del tutor
            - ``corrections``: lista de correcciones (puede estar vacía)
            - ``exercise``:    ejercicio de relleno opcional (puede ser None)
            - ``turn``:        número de turno de la conversación
        """
        history = history or []
        turn = len(history) + 1

        corrections = self.correct_text(user_message)

        # Construir respuesta según el turno y la misión activa
        response_text = self._build_response(user_message, history, turn, corrections)

        # Cada ~3 turnos generar un ejercicio de relleno desde los diálogos
        exercise = None
        if turn % 3 == 0 and self.current_mission:
            dialogues = self.current_mission.get("dialogues", [])
            if dialogues:
                # Tomar una línea de diálogo del tutor para ejercicio
                tutor_lines = [d["text"] for d in dialogues if d.get("speaker") == "Tutor"]
                if tutor_lines:
                    sentence = tutor_lines[(turn // 3 - 1) % len(tutor_lines)]
                    exercise = self.generate_fill_blank(sentence)

        return {
            "response": response_text,
            "corrections": corrections,
            "exercise": exercise,
            "turn": turn,
        }

    def _build_response(
        self,
        user_message: str,
        history: list[dict],
        turn: int,
        corrections: list[dict],
    ) -> str:
        parts: list[str] = []

        # Primer turno: saludo
        if turn == 1:
            return _GREETING_RESPONSES[0]

        # Si hay correcciones, mencionarlas brevemente
        if corrections:
            first = corrections[0]
            intro = _CORRECTION_INTRO[turn % len(_CORRECTION_INTRO)]
            parts.append(
                f"{intro}'{first['original']}' → '{first['suggested']}'. "
                f"({first['explanation']})"
            )

        # Respuesta temática según la misión actual
        if self.current_mission:
            tags = self.current_mission.get("vocabulary_tags", [])
            for tag in tags:
                if tag in _TOPIC_RESPONSES:
                    responses = _TOPIC_RESPONSES[tag]
                    parts.append(responses[turn % len(responses)])
                    break
            else:
                parts.append(_DEFAULT_RESPONSES[turn % len(_DEFAULT_RESPONSES)])
        else:
            parts.append(_DEFAULT_RESPONSES[turn % len(_DEFAULT_RESPONSES)])

        # Estímulo positivo cada 4 turnos
        if turn % 4 == 0:
            parts.append(_ENCOURAGEMENT[turn % len(_ENCOURAGEMENT)])

        return " ".join(parts)

    # ------------------------------------------------------------------
    # MISIONES
    # ------------------------------------------------------------------
    def analyze_description(self, description: str) -> list[str]:
        keywords: dict[str, list[str]] = {
            "animals":    ["dog", "cat", "park", "pet", "animal", "bird", "horse"],
            "actions":    ["run", "eat", "walk", "play", "do", "make"],
            "food":       ["restaurant", "eat", "menu", "food", "cook", "recipe"],
            "travel":     ["airport", "hotel", "flight", "travel", "trip", "visit"],
            "work":       ["job", "office", "work", "company", "career", "business"],
            "school":     ["school", "study", "class", "exam", "learn", "university"],
            "weather":    ["weather", "rain", "snow", "sun", "temperature"],
            "technology": ["computer", "phone", "internet", "app", "software"],
            "home":       ["house", "home", "room", "kitchen", "garden"],
            "emotions":   ["feel", "happy", "sad", "emotion", "love", "afraid"],
        }
        detected: list[str] = []
        for tag, words in keywords.items():
            if any(word in description.lower() for word in words):
                detected.append(tag)
        return detected

    def generate_dialogue(self, description: str, tags: list[str]) -> list[dict]:
        if "animals" in tags:
            return [
                {"speaker": "Tutor",   "text": "Do you have any pets?"},
                {"speaker": "Student", "text": "Yes, I have a dog."},
                {"speaker": "Tutor",   "text": "What do you usually do with your dog in the park?"},
                {"speaker": "Student", "text": "I walk and play with him every morning."},
            ]
        if "food" in tags:
            return [
                {"speaker": "Tutor",   "text": "What kind of food do you like?"},
                {"speaker": "Student", "text": "I love Italian food."},
                {"speaker": "Tutor",   "text": "Do you often go to restaurants?"},
                {"speaker": "Student", "text": "Yes, I go out for dinner once a week."},
            ]
        if "travel" in tags:
            return [
                {"speaker": "Tutor",   "text": "Where would you like to travel next?"},
                {"speaker": "Student", "text": "I want to visit Japan."},
                {"speaker": "Tutor",   "text": "Great choice! Have you bought your ticket yet?"},
                {"speaker": "Student", "text": "Not yet, I'm still planning."},
            ]
        if "work" in tags:
            return [
                {"speaker": "Tutor",   "text": "What do you do for work?"},
                {"speaker": "Student", "text": "I work in a software company."},
                {"speaker": "Tutor",   "text": "Interesting! What are your main responsibilities?"},
                {"speaker": "Student", "text": "I develop mobile applications."},
            ]
        return [
            {"speaker": "Tutor",   "text": f"Let's talk about: {description}"},
            {"speaker": "Student", "text": "Sure!"},
            {"speaker": "Tutor",   "text": "Great! Can you describe it in more detail?"},
        ]

    def generate_exercises(self, tags: list[str]) -> list[dict]:
        exercises: list[dict] = []

        if "animals" in tags:
            exercises.append({
                "type": "fill_blank",
                "text":   "I usually ___ my dog in the park.",
                "blanks": ["walk"],
                "hint":   "Use a verb for taking a dog outside",
            })
            exercises.append({
                "type": "translate",
                "text":   "My dog is very friendly.",
            })
            exercises.append({
                "type": "multiple_choice",
                "text":   "Which animal makes a good house pet?",
                "options": ["dog", "lion", "elephant", "shark"],
                "answer": "dog",
            })

        if "food" in tags:
            exercises.append({
                "type": "fill_blank",
                "text":   "I ___ a lot of fruit every day.",
                "blanks": ["eat"],
                "hint":   "Verb for consuming food",
            })
            exercises.append({
                "type": "multiple_choice",
                "text":   "What do you call the midday meal?",
                "options": ["breakfast", "lunch", "dinner", "snack"],
                "answer": "lunch",
            })

        if "travel" in tags:
            exercises.append({
                "type": "fill_blank",
                "text":   "You need a ___ to enter another country.",
                "blanks": ["passport"],
                "hint":   "Official travel document",
            })
            exercises.append({
                "type": "translate",
                "text":   "The flight departs at 10 am.",
            })

        if "work" in tags:
            exercises.append({
                "type": "fill_blank",
                "text":   "I have an important ___ with my boss tomorrow.",
                "blanks": ["meeting"],
                "hint":   "A scheduled professional gathering",
            })

        if not exercises:
            exercises.append({
                "type": "translate",
                "text":   "I want to practise English every day.",
            })

        return exercises

    def create_open_mission(self, description: str, mission_id: str) -> dict:
        tags = self.analyze_description(description)
        new_mission = {
            "id":              mission_id,
            "name":            description,
            "goal":            description,
            "vocabulary_tags": tags,
            "dialogues":       self.generate_dialogue(description, tags),
            "exercises":       self.generate_exercises(tags),
        }
        self.missions.append(new_mission)
        self.current_mission = new_mission
        return new_mission

    # ------------------------------------------------------------------
    # FLASHCARDS
    # ------------------------------------------------------------------
    def generate_flashcards(self) -> list[dict]:
        if not self.current_mission:
            raise ValueError("No hay misión seleccionada para generar flashcards.")

        vocab = self.get_mission_vocabulary()
        flashcards: list[dict] = []

        for item in vocab:
            word = item["word"]
            flashcards.append({
                "front": word,
                "back": {
                    "definition":  item.get("definition",  f"Definition of '{word}'"),
                    "example":     item.get("example",     f"I use the word '{word}' in a sentence."),
                    "translation": item.get("translation", f"Traducción de '{word}'"),
                },
            })

        return flashcards
