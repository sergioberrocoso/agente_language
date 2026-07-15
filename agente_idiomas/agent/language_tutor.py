from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Corrector de gramática mejorado (reglas sin LLM)
#
# Cada entrada de corrección incluye:
#   - original    : fragmento tal como aparece en el texto
#   - suggested   : forma corregida
#   - position    : índice de carácter en el texto original
#   - rule        : nombre de la regla aplicada
#   - explanation : descripción breve del error
#   - why         : explicación pedagógica del porqué
#   - better_example : oración de ejemplo correcta
# ---------------------------------------------------------------------------

# Contracciones escritas sin apóstrofe
# Cada tupla: (patrón, sugerencia, explicación, por-qué, ejemplo)
_CONTRACTION_RULES: list[tuple[str, str, str, str, str]] = [
    (r"\bdont\b",    "don't",    "Missing apostrophe in 'don't'",
     "Contractions require an apostrophe to replace omitted letters (do + not = don't).",
     "I don't like cold weather."),
    (r"\bcant\b",    "can't",    "Missing apostrophe in 'can't'",
     "The contraction 'can't' stands for 'cannot'. The apostrophe marks the missing letters.",
     "She can't come to the party."),
    (r"\bwont\b",    "won't",    "Missing apostrophe in 'won't'",
     "'Won't' is the contraction of 'will not'. It has an irregular spelling change.",
     "He won't be here tomorrow."),
    (r"\bcouldnt\b", "couldn't", "Missing apostrophe in 'couldn't'",
     "'Couldn't' = 'could not'. Always add an apostrophe before the final 't'.",
     "I couldn't sleep last night."),
    (r"\bwouldnt\b", "wouldn't", "Missing apostrophe in 'wouldn't'",
     "'Wouldn't' = 'would not'. The apostrophe replaces the missing 'o'.",
     "They wouldn't agree with us."),
    (r"\bshouldnt\b","shouldn't","Missing apostrophe in 'shouldn't'",
     "'Shouldn't' = 'should not'. Use an apostrophe before 't'.",
     "You shouldn't eat so much sugar."),
    (r"\bisnt\b",    "isn't",    "Missing apostrophe in 'isn't'",
     "'Isn't' = 'is not'. The apostrophe replaces the 'o' in 'not'.",
     "That isn't the right answer."),
    (r"\barent\b",   "aren't",   "Missing apostrophe in 'aren't'",
     "'Aren't' = 'are not'. The apostrophe marks the missing 'o'.",
     "We aren't ready yet."),
    (r"\bwasnt\b",   "wasn't",   "Missing apostrophe in 'wasn't'",
     "'Wasn't' = 'was not'. The apostrophe replaces the 'o' in 'not'.",
     "It wasn't a good idea."),
    (r"\bwerent\b",  "weren't",  "Missing apostrophe in 'weren't'",
     "'Weren't' = 'were not'. Add an apostrophe before 't'.",
     "They weren't at home."),
    (r"\bhasnt\b",   "hasn't",   "Missing apostrophe in 'hasn't'",
     "'Hasn't' = 'has not'. The apostrophe replaces the 'o' in 'not'.",
     "She hasn't finished yet."),
    (r"\bhavent\b",  "haven't",  "Missing apostrophe in 'haven't'",
     "'Haven't' = 'have not'. The apostrophe marks the missing 'o'.",
     "I haven't seen that film."),
    (r"\bhadnt\b",   "hadn't",   "Missing apostrophe in 'hadn't'",
     "'Hadn't' = 'had not'. Add the apostrophe before 't'.",
     "We hadn't met before."),
    (r"\bdidnt\b",   "didn't",   "Missing apostrophe in 'didn't'",
     "'Didn't' = 'did not'. The apostrophe replaces the 'o' in 'not'.",
     "I didn't understand the question."),
    (r"\bdoesnt\b",  "doesn't",  "Missing apostrophe in 'doesn't'",
     "'Doesn't' = 'does not'. The apostrophe replaces the 'o' in 'not'.",
     "He doesn't know the answer."),
    (r"\bthats\b",   "that's",   "Missing apostrophe in 'that's'",
     "'That's' = 'that is' or 'that has'. The apostrophe replaces the omitted letters.",
     "That's a great idea!"),
    (r"\bweve\b",    "we've",    "Missing apostrophe in 'we've'",
     "'We've' = 'we have'. The apostrophe replaces 'ha' from 'have'.",
     "We've been waiting for an hour."),
    (r"\btheyre\b",  "they're",  "Missing apostrophe in 'they're'",
     "'They're' = 'they are'. Do not confuse with 'their' (possessive) or 'there' (place).",
     "They're going to the cinema."),
    (r"\btheyve\b",  "they've",  "Missing apostrophe in 'they've'",
     "'They've' = 'they have'. The apostrophe replaces 'ha'.",
     "They've already left."),
    (r"\byoure\b",   "you're",   "Missing apostrophe in 'you're'",
     "'You're' = 'you are'. Do not confuse with 'your' (possessive).",
     "You're doing very well!"),
    (r"\byouve\b",   "you've",   "Missing apostrophe in 'you've'",
     "'You've' = 'you have'. The apostrophe replaces 'ha'.",
     "You've made great progress."),
    (r"\bim\b",      "I'm",      "Missing apostrophe in 'I'm'",
     "'I'm' = 'I am'. The apostrophe replaces 'a'. Also note 'I' is always capitalised.",
     "I'm learning English every day."),
    (r"\bive\b",     "I've",     "Missing apostrophe in 'I've'",
     "'I've' = 'I have'. The apostrophe replaces 'ha'. 'I' is always capitalised.",
     "I've finished my homework."),
    (r"\bill\b",     "I'll",     "Missing apostrophe in 'I'll'",
     "'I'll' = 'I will'. The apostrophe replaces 'wi'. 'I' is always capitalised.",
     "I'll call you tomorrow."),
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
    "open", "close", "stop", "begin", "finish", "continue", "enjoy",
    "prefer", "decide", "plan", "suggest", "explain", "describe",
]

# Irregulares: base → 3.ª persona
_IRREGULAR_3SG: dict[str, str] = {
    "go": "goes",
    "do": "does",
    "have": "has",
    "be": "is",
}

# Reglas de "ser/estar" con explicación pedagógica completa
# Cada tupla: (patrón, sugerencia, explicación, por-qué, ejemplo)
_BE_RULES: list[tuple[str, str, str, str, str]] = [
    (r"\bI\s+are\b",    "I am",     "Subject-verb agreement: use 'am' with 'I'",
     "The verb 'to be' with the subject 'I' is always 'am' (present) or 'was' (past).",
     "I am a student."),
    (r"\bI\s+is\b",     "I am",     "Subject-verb agreement: use 'am' with 'I'",
     "'Is' is used for he/she/it — not for 'I'. With 'I' always use 'am'.",
     "I am happy today."),
    (r"\byou\s+am\b",   "you are",  "Subject-verb agreement: use 'are' with 'you'",
     "'Am' is only used with 'I'. For 'you', always use 'are'.",
     "You are very kind."),
    (r"\byou\s+is\b",   "you are",  "Subject-verb agreement: use 'are' with 'you'",
     "'Is' is used for he/she/it — not for 'you'. Use 'are' with 'you'.",
     "You are doing well."),
    (r"\bhe\s+am\b",    "he is",    "Subject-verb agreement: use 'is' with 'he'",
     "'Am' is only for 'I'. Third-person singular (he/she/it) requires 'is'.",
     "He is my best friend."),
    (r"\bhe\s+are\b",   "he is",    "Subject-verb agreement: use 'is' with 'he'",
     "'Are' is for you/we/they. Third-person singular (he/she/it) requires 'is'.",
     "He is at school."),
    (r"\bshe\s+am\b",   "she is",   "Subject-verb agreement: use 'is' with 'she'",
     "'Am' is only for 'I'. Use 'is' with she/he/it.",
     "She is a doctor."),
    (r"\bshe\s+are\b",  "she is",   "Subject-verb agreement: use 'is' with 'she'",
     "'Are' is for you/we/they. Use 'is' with she/he/it.",
     "She is very talented."),
    (r"\bit\s+am\b",    "it is",    "Subject-verb agreement: use 'is' with 'it'",
     "'Am' is only for 'I'. Use 'is' with she/he/it.",
     "It is a beautiful day."),
    (r"\bit\s+are\b",   "it is",    "Subject-verb agreement: use 'is' with 'it'",
     "'Are' is for you/we/they. Use 'is' with she/he/it.",
     "It is raining outside."),
    (r"\bwe\s+am\b",    "we are",   "Subject-verb agreement: use 'are' with 'we'",
     "'Am' is only for 'I'. For 'we', use 'are'.",
     "We are ready to go."),
    (r"\bwe\s+is\b",    "we are",   "Subject-verb agreement: use 'are' with 'we'",
     "'Is' is for he/she/it. For 'we', use 'are'.",
     "We are from Spain."),
    (r"\bthey\s+am\b",  "they are", "Subject-verb agreement: use 'are' with 'they'",
     "'Am' is only for 'I'. For 'they', use 'are'.",
     "They are good students."),
    (r"\bthey\s+is\b",  "they are", "Subject-verb agreement: use 'are' with 'they'",
     "'Is' is for he/she/it. For 'they', use 'are'.",
     "They are waiting outside."),
]

# Doble negación
_DOUBLE_NEGATIVE_RULES: list[tuple[str, str, str, str, str]] = [
    (r"\bdon't\s+know\s+nothing\b",   "don't know anything",
     "Double negative: use 'anything' instead of 'nothing' with 'don't'",
     "In standard English, two negatives cancel each other out. Use 'don't know anything' or 'know nothing'.",
     "I don't know anything about that."),
    (r"\bdidn't\s+do\s+nothing\b",    "didn't do anything",
     "Double negative: use 'anything' instead of 'nothing' with 'didn't'",
     "Double negatives are non-standard. Use 'didn't do anything' or 'did nothing'.",
     "She didn't do anything wrong."),
    (r"\bcan't\s+do\s+nothing\b",     "can't do anything",
     "Double negative: use 'anything' with 'can't'",
     "Two negatives in one clause create a double negative. Use 'anything' instead.",
     "He can't do anything to help."),
    (r"\bnever\s+said\s+nothing\b",   "never said anything",
     "Double negative: use 'anything' instead of 'nothing' with 'never'",
     "'Never' is already negative. Use 'never said anything'.",
     "She never said anything about it."),
    (r"\bain't\s+got\s+no\b",         "haven't got any",
     "Double negative: avoid 'ain't ... no'",
     "'Ain't' is informal and combining it with 'no' creates a double negative. Use 'haven't got any'.",
     "I haven't got any money."),
]

# Preposiciones incorrectas frecuentes
_PREPOSITION_RULES: list[tuple[str, str, str, str, str]] = [
    (r"\binterested\s+on\b",     "interested in",
     "Wrong preposition: use 'interested in' not 'interested on'",
     "The adjective 'interested' is always followed by the preposition 'in'.",
     "I am interested in learning new languages."),
    (r"\bgood\s+in\b",           "good at",
     "Wrong preposition: use 'good at' not 'good in'",
     "To express skill or ability, use 'good at'. 'Good in' is used for context (e.g. 'good in bed').",
     "She is very good at maths."),
    (r"\bmarried\s+with\b",      "married to",
     "Wrong preposition: use 'married to' not 'married with'",
     "In English, you are 'married to' someone, not 'married with'.",
     "He is married to a teacher."),
    (r"\bdepend\s+of\b",         "depend on",
     "Wrong preposition: use 'depend on' not 'depend of'",
     "The verb 'depend' always takes the preposition 'on'.",
     "It depends on the weather."),
    (r"\barrived\s+to\b",        "arrived at/in",
     "Wrong preposition after 'arrived': use 'at' (small place) or 'in' (city/country)",
     "Use 'arrived at' for specific places (station, school) and 'arrived in' for cities/countries.",
     "We arrived at the airport. / We arrived in London."),
    (r"\blisten\s+music\b",      "listen to music",
     "Missing preposition: use 'listen to music'",
     "The verb 'listen' requires the preposition 'to' before its object.",
     "I love to listen to music in the evening."),
    (r"\bdream\s+with\b",        "dream about/of",
     "Wrong preposition: use 'dream about' or 'dream of'",
     "In English you 'dream about' or 'dream of' something, never 'dream with'.",
     "I dream about travelling the world."),
]

# Confusión modal + infinitivo (would/could/should + of → have)
_MODAL_PERFECTIVE_RULES: list[tuple[str, str, str, str, str]] = [
    (r"\bwould\s+of\b",   "would have",
     "Wrong form: use 'would have' not 'would of'",
     "'Would have' is the correct form. 'Would of' is a phonetic spelling error — 'have' sounds like 'of' in spoken English.",
     "I would have helped you if I had known."),
    (r"\bcould\s+of\b",   "could have",
     "Wrong form: use 'could have' not 'could of'",
     "'Could have' is the correct form. 'Of' cannot follow modal verbs.",
     "She could have passed the exam with more practice."),
    (r"\bshould\s+of\b",  "should have",
     "Wrong form: use 'should have' not 'should of'",
     "'Should have' is the correct form. This is a very common phonetic spelling mistake.",
     "You should have called me earlier."),
    (r"\bmight\s+of\b",   "might have",
     "Wrong form: use 'might have' not 'might of'",
     "'Might have' is the correct form — 'of' cannot follow modal verbs.",
     "It might have been an accident."),
    (r"\bmust\s+of\b",    "must have",
     "Wrong form: use 'must have' not 'must of'",
     "'Must have' expresses deduction about the past. 'Must of' is not standard English.",
     "She must have forgotten about the meeting."),
]

# Artículo "a" vs "an"
_VOWEL_SOUNDS = re.compile(
    r"\ba\s+([aeiouAEIOU]\w*)", re.IGNORECASE
)
_CONSONANT_AN = re.compile(
    r"\ban\s+([^aeiouAEIOU\s]\w*)", re.IGNORECASE
)

# Palabras "silent-h" que siempre llevan "an"
_SILENT_H_WORDS = {"hour", "honest", "honour", "honor", "heir", "herb"}
# Siglas y palabras que suenan con vocal aunque empiecen por consonante
_VOWEL_SOUND_WORDS = {"fbi", "nba", "nfl", "nsa", "mba", "ngo", "mp", "nhs"}


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
    """Aplica reglas gramaticales y devuelve la lista de correcciones.

    Cada corrección incluye los campos estándar (original, suggested,
    position, rule, explanation) más dos campos pedagógicos opcionales:
        - ``why``            : explicación del porqué es un error
        - ``better_example`` : oración de ejemplo correcta
    """
    corrections: list[dict] = []

    # 1. Contracciones
    for pattern, suggestion, explanation, why, better_example in _CONTRACTION_RULES:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            corrections.append({
                "original": m.group(0),
                "suggested": suggestion,
                "position": m.start(),
                "rule": "contraction",
                "explanation": explanation,
                "why": why,
                "better_example": better_example,
            })

    # 2. Concordancia be
    for pattern, suggestion, explanation, why, better_example in _BE_RULES:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            corrections.append({
                "original": m.group(0),
                "suggested": suggestion,
                "position": m.start(),
                "rule": "subject_verb_be",
                "explanation": explanation,
                "why": why,
                "better_example": better_example,
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
                    "why": (
                        f"In the simple present tense, verbs after he/she/it must "
                        f"take the third-person singular form (add -s or -es). "
                        f"'{verb}' → '{corrected_v}' with '{subj}'."
                    ),
                    "better_example": f"{subj.capitalize()} {corrected_v} to school every day.",
                })

    # 4. Doble negación
    for pattern, suggestion, explanation, why, better_example in _DOUBLE_NEGATIVE_RULES:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            corrections.append({
                "original": m.group(0),
                "suggested": suggestion,
                "position": m.start(),
                "rule": "double_negative",
                "explanation": explanation,
                "why": why,
                "better_example": better_example,
            })

    # 5. Preposiciones incorrectas
    for pattern, suggestion, explanation, why, better_example in _PREPOSITION_RULES:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            corrections.append({
                "original": m.group(0),
                "suggested": suggestion,
                "position": m.start(),
                "rule": "wrong_preposition",
                "explanation": explanation,
                "why": why,
                "better_example": better_example,
            })

    # 6. Modal + "of" (debería ser "have")
    for pattern, suggestion, explanation, why, better_example in _MODAL_PERFECTIVE_RULES:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            corrections.append({
                "original": m.group(0),
                "suggested": suggestion,
                "position": m.start(),
                "rule": "modal_perfective",
                "explanation": explanation,
                "why": why,
                "better_example": better_example,
            })

    # 7. Artículo "a" antes de vocal (excluyendo palabras silent-h)
    for m in _VOWEL_SOUNDS.finditer(text):
        following_word = m.group(1).lower()
        if following_word in _SILENT_H_WORDS:
            continue  # "an hour" es correcto — no tocar
        corrections.append({
            "original": m.group(0),
            "suggested": "an " + m.group(1),
            "position": m.start(),
            "rule": "article_a_an",
            "explanation": "Use 'an' before words starting with a vowel sound",
            "why": (
                "The article 'an' is used instead of 'a' when the next word "
                "begins with a vowel sound. This makes pronunciation smoother."
            ),
            "better_example": f"She is an {m.group(1)} expert.",
        })

    # 8. Artículo "an" antes de consonante
    for m in _CONSONANT_AN.finditer(text):
        following_word = m.group(1).lower()
        if following_word in _SILENT_H_WORDS or following_word in _VOWEL_SOUND_WORDS:
            continue  # "an hour", "an FBI agent" son correctos
        corrections.append({
            "original": m.group(0),
            "suggested": "a " + m.group(1),
            "position": m.start(),
            "rule": "article_a_an",
            "explanation": "Use 'a' before words starting with a consonant sound",
            "why": (
                "The article 'a' is used before words that begin with a consonant "
                "sound. 'An' is only used before vowel sounds."
            ),
            "better_example": f"I need a {m.group(1)} to complete this task.",
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

    def generate_exercises(
        self,
        tags: list[str],
        difficulty: str = "beginner",
    ) -> list[dict]:
        """Genera ejercicios variados y con diferentes niveles de dificultad.

        Args:
            tags:       Lista de tags temáticos.
            difficulty: ``"beginner"`` | ``"intermediate"`` | ``"advanced"``

        Tipos de ejercicio disponibles:
            fill_blank     — completar huecos
            multiple_choice — elegir la opción correcta
            translate      — traducir al inglés
            reorder        — ordenar palabras para formar una oración
            error_correct  — encontrar y corregir el error gramatical
            match          — emparejar palabra con definición
        """
        exercises: list[dict] = []

        # ----------------------------------------------------------------
        # ANIMALES
        # ----------------------------------------------------------------
        if "animals" in tags:
            exercises.append({
                "type": "fill_blank",
                "text": "I usually ___ my dog in the park.",
                "blanks": ["walk"],
                "hint": "Use a verb for taking a dog outside",
                "difficulty": "beginner",
                "feedback": "The verb 'walk' is used when you take your dog out.",
            })
            exercises.append({
                "type": "multiple_choice",
                "text": "Which animal makes a good house pet?",
                "options": ["dog", "lion", "elephant", "shark"],
                "answer": "dog",
                "difficulty": "beginner",
                "feedback": "Dogs, cats, and rabbits are common house pets.",
            })
            exercises.append({
                "type": "translate",
                "text": "My dog is very friendly.",
                "difficulty": "beginner",
                "feedback": "Mi perro es muy amigable.",
            })
            exercises.append({
                "type": "reorder",
                "text": "in / lives / a / The / cat / house",
                "answer": "The cat lives in a house.",
                "difficulty": "intermediate",
                "feedback": "Word order in English: Subject + Verb + Prepositional phrase.",
            })
            exercises.append({
                "type": "error_correct",
                "text": "The dog runned away very fast.",
                "answer": "The dog ran away very fast.",
                "difficulty": "intermediate",
                "feedback": "'Run' is irregular: run → ran (past simple).",
            })
            exercises.append({
                "type": "match",
                "text": "Match each animal to its description",
                "pairs": [
                    {"word": "dog",   "definition": "Loyal pet that barks"},
                    {"word": "cat",   "definition": "Independent pet that meows"},
                    {"word": "bird",  "definition": "Animal with wings that can sing"},
                    {"word": "fish",  "definition": "Silent animal that lives in water"},
                ],
                "difficulty": "beginner",
                "feedback": "Each animal has unique characteristics that define it.",
            })
            if difficulty in ("intermediate", "advanced"):
                exercises.append({
                    "type": "fill_blank",
                    "text": "Wild animals should not be kept in ___; they belong in their natural ___.",
                    "blanks": ["captivity", "habitat"],
                    "hint": "Think about zoo ethics and nature",
                    "difficulty": "advanced",
                    "feedback": "'Captivity' = being confined. 'Habitat' = natural environment.",
                })

        # ----------------------------------------------------------------
        # COMIDA
        # ----------------------------------------------------------------
        if "food" in tags:
            exercises.append({
                "type": "fill_blank",
                "text": "I ___ a lot of fruit every day.",
                "blanks": ["eat"],
                "hint": "Verb for consuming food",
                "difficulty": "beginner",
                "feedback": "The verb 'eat' means to consume food.",
            })
            exercises.append({
                "type": "multiple_choice",
                "text": "What do you call the midday meal?",
                "options": ["breakfast", "lunch", "dinner", "snack"],
                "answer": "lunch",
                "difficulty": "beginner",
                "feedback": "Breakfast = morning, lunch = midday, dinner = evening.",
            })
            exercises.append({
                "type": "reorder",
                "text": "morning / every / I / eat / toast / the / in",
                "answer": "I eat toast in the morning every day.",
                "difficulty": "intermediate",
                "feedback": "Time expressions often go at the end of the sentence.",
            })
            exercises.append({
                "type": "error_correct",
                "text": "She don't like vegetables.",
                "answer": "She doesn't like vegetables.",
                "difficulty": "beginner",
                "feedback": "With he/she/it in negatives, use 'doesn't' not 'don't'.",
            })
            if difficulty in ("intermediate", "advanced"):
                exercises.append({
                    "type": "fill_blank",
                    "text": "The chef ___ the vegetables before adding them to the ___.",
                    "blanks": ["chopped", "pan"],
                    "hint": "Cooking actions and kitchen tools",
                    "difficulty": "intermediate",
                    "feedback": "'Chop' = to cut into pieces. A 'pan' is used for frying.",
                })
            if difficulty == "advanced":
                exercises.append({
                    "type": "translate",
                    "text": "El restaurante es famoso por su exquisita cocina mediterránea.",
                    "difficulty": "advanced",
                    "feedback": "The restaurant is famous for its exquisite Mediterranean cuisine.",
                })

        # ----------------------------------------------------------------
        # VIAJES
        # ----------------------------------------------------------------
        if "travel" in tags:
            exercises.append({
                "type": "fill_blank",
                "text": "You need a ___ to enter another country.",
                "blanks": ["passport"],
                "hint": "Official travel document",
                "difficulty": "beginner",
                "feedback": "A passport is the official document for international travel.",
            })
            exercises.append({
                "type": "translate",
                "text": "The flight departs at 10 am.",
                "difficulty": "beginner",
                "feedback": "El vuelo sale a las 10 de la mañana.",
            })
            exercises.append({
                "type": "multiple_choice",
                "text": "Where do you check in for a flight?",
                "options": ["train station", "airport", "bus stop", "hotel"],
                "answer": "airport",
                "difficulty": "beginner",
                "feedback": "You check in for flights at the airport.",
            })
            exercises.append({
                "type": "reorder",
                "text": "in / We / hotel / the / checked / yesterday",
                "answer": "We checked in the hotel yesterday.",
                "difficulty": "intermediate",
                "feedback": "'Check in' means to register your arrival at a hotel or airport.",
            })
            exercises.append({
                "type": "error_correct",
                "text": "I arrived to the airport two hours ago.",
                "answer": "I arrived at the airport two hours ago.",
                "difficulty": "intermediate",
                "feedback": "Use 'arrive at' for specific places, 'arrive in' for cities/countries.",
            })
            if difficulty == "advanced":
                exercises.append({
                    "type": "fill_blank",
                    "text": "After clearing ___, we proceeded to the departure ___.",
                    "blanks": ["customs", "lounge"],
                    "hint": "Airport areas and procedures",
                    "difficulty": "advanced",
                    "feedback": "'Customs' = document/goods inspection. 'Departure lounge' = waiting area.",
                })

        # ----------------------------------------------------------------
        # TRABAJO
        # ----------------------------------------------------------------
        if "work" in tags:
            exercises.append({
                "type": "fill_blank",
                "text": "I have an important ___ with my boss tomorrow.",
                "blanks": ["meeting"],
                "hint": "A scheduled professional gathering",
                "difficulty": "beginner",
                "feedback": "A 'meeting' is a planned gathering of people at work.",
            })
            exercises.append({
                "type": "multiple_choice",
                "text": "What do you call the money you earn at work?",
                "options": ["salary", "price", "cost", "fee"],
                "answer": "salary",
                "difficulty": "beginner",
                "feedback": "A 'salary' is the fixed regular payment from an employer.",
            })
            exercises.append({
                "type": "error_correct",
                "text": "She work in a bank and she love her job.",
                "answer": "She works in a bank and she loves her job.",
                "difficulty": "beginner",
                "feedback": "With he/she/it in present simple, add -s to the verb.",
            })
            if difficulty in ("intermediate", "advanced"):
                exercises.append({
                    "type": "reorder",
                    "text": "apply / I / a / for / decided / promotion / to",
                    "answer": "I decided to apply for a promotion.",
                    "difficulty": "intermediate",
                    "feedback": "'Apply for' is used for jobs, promotions, or grants.",
                })
                exercises.append({
                    "type": "fill_blank",
                    "text": "The company offered her an excellent ___ package including health insurance.",
                    "blanks": ["benefits"],
                    "hint": "Additional compensation beyond base salary",
                    "difficulty": "intermediate",
                    "feedback": "'Benefits' = extras like insurance, holidays, or bonuses.",
                })

        # ----------------------------------------------------------------
        # ESCUELA
        # ----------------------------------------------------------------
        if "school" in tags:
            exercises.append({
                "type": "fill_blank",
                "text": "The ___ explained the lesson clearly to the students.",
                "blanks": ["teacher"],
                "hint": "The person who teaches",
                "difficulty": "beginner",
                "feedback": "A 'teacher' is the person who instructs students.",
            })
            exercises.append({
                "type": "multiple_choice",
                "text": "What do you call the test at the end of a school term?",
                "options": ["homework", "essay", "exam", "project"],
                "answer": "exam",
                "difficulty": "beginner",
                "feedback": "An 'exam' is a formal test to evaluate knowledge.",
            })
            exercises.append({
                "type": "error_correct",
                "text": "I didn't studied for the exam last night.",
                "answer": "I didn't study for the exam last night.",
                "difficulty": "intermediate",
                "feedback": "After 'didn't', always use the base form of the verb (not past tense).",
            })

        # ----------------------------------------------------------------
        # TECNOLOGÍA
        # ----------------------------------------------------------------
        if "technology" in tags:
            exercises.append({
                "type": "fill_blank",
                "text": "I use my ___ to browse the internet.",
                "blanks": ["computer"],
                "hint": "Electronic device for computing",
                "difficulty": "beginner",
                "feedback": "A 'computer' is the main device for accessing the internet.",
            })
            exercises.append({
                "type": "multiple_choice",
                "text": "Which of these is a social media platform?",
                "options": ["spreadsheet", "database", "Instagram", "compiler"],
                "answer": "Instagram",
                "difficulty": "beginner",
                "feedback": "Instagram, Facebook, and Twitter are social media platforms.",
            })
            exercises.append({
                "type": "error_correct",
                "text": "Can you send me the file per email?",
                "answer": "Can you send me the file by email?",
                "difficulty": "intermediate",
                "feedback": "Use 'by email', 'by phone', 'by post' — not 'per'.",
            })

        # ----------------------------------------------------------------
        # EMOCIONES
        # ----------------------------------------------------------------
        if "emotions" in tags:
            exercises.append({
                "type": "multiple_choice",
                "text": "If you feel very happy, you could say you feel…",
                "options": ["miserable", "elated", "bored", "nervous"],
                "answer": "elated",
                "difficulty": "intermediate",
                "feedback": "'Elated' means extremely happy and excited.",
            })
            exercises.append({
                "type": "match",
                "text": "Match each emotion to its description",
                "pairs": [
                    {"word": "anxious",  "definition": "Worried about uncertain future events"},
                    {"word": "content",  "definition": "Quietly satisfied and at peace"},
                    {"word": "furious",  "definition": "Extremely angry"},
                    {"word": "nostalgic","definition": "Longing for the past"},
                ],
                "difficulty": "advanced",
                "feedback": "English has a rich vocabulary for nuanced emotions.",
            })

        # ----------------------------------------------------------------
        # CLIMA
        # ----------------------------------------------------------------
        if "weather" in tags:
            exercises.append({
                "type": "fill_blank",
                "text": "It's ___ outside, so don't forget your umbrella.",
                "blanks": ["raining"],
                "hint": "Water falling from the sky",
                "difficulty": "beginner",
                "feedback": "'It's raining' uses the present continuous for current weather.",
            })
            exercises.append({
                "type": "error_correct",
                "text": "Yesterday was so heat that we stayed inside.",
                "answer": "Yesterday was so hot that we stayed inside.",
                "difficulty": "beginner",
                "feedback": "'Hot' is the adjective (not 'heat'). Heat is a noun.",
            })

        # ----------------------------------------------------------------
        # Ejercicio de gramática genérico (siempre se incluye)
        # ----------------------------------------------------------------
        exercises.append({
            "type": "error_correct",
            "text": "He don't understand the question.",
            "answer": "He doesn't understand the question.",
            "difficulty": "beginner",
            "feedback": "With he/she/it use 'doesn't' for negation in the present simple.",
        })

        # Fallback si no hay ejercicios temáticos
        if len(exercises) == 1:
            exercises.insert(0, {
                "type": "translate",
                "text": "I want to practise English every day.",
                "difficulty": "beginner",
                "feedback": "Quiero practicar inglés todos los días.",
            })

        # Filtrar por dificultad si se pide
        level_order = {"beginner": 0, "intermediate": 1, "advanced": 2}
        requested_level = level_order.get(difficulty, 0)
        filtered = [
            e for e in exercises
            if level_order.get(e.get("difficulty", "beginner"), 0) <= requested_level
        ]
        return filtered if filtered else exercises

    def create_open_mission(
        self,
        description: str,
        mission_id: str,
        difficulty: str = "beginner",
    ) -> dict:
        tags = self.analyze_description(description)
        new_mission = {
            "id":              mission_id,
            "name":            description,
            "goal":            description,
            "vocabulary_tags": tags,
            "dialogues":       self.generate_dialogue(description, tags),
            "exercises":       self.generate_exercises(tags, difficulty=difficulty),
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
