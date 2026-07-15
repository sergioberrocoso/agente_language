# agente_language

Agente educativo para practicar idiomas con:

- selección de misiones predefinidas
- creación de misiones abiertas con nivel de dificultad
- **corrección gramatical mejorada** (contracciones, concordancia, doble negación, preposiciones, modales)
- conversación interactiva con feedback y ejercicios
- **ejercicios más completos** (fill-blank, multiple-choice, reorder, error_correct, match — por nivel)
- base de datos SQLite de vocabulario (NGSL, 2800+ palabras)
- generación y exportación de flashcards a formato Anki
- **conversaciones por voz** (STT + TTS, con degradación elegante a texto)
- **importación de CSV de vocabulario** (con deduplicación y trazabilidad)
- **persistencia de progreso de usuario** (historial, preferencias, estado de flashcards)

## Arquitectura

```
agente_idiomas/
├── requirements.txt
├── main.py                       # Demo standalone
├── api_server.py                 # Arranca el servidor FastAPI
├── agent/
│   └── language_tutor.py         # Núcleo: corrección mejorada, conversación, ejercicios por nivel
├── api/
│   ├── app.py                    # Aplicación FastAPI (v0.2.0)
│   ├── deps.py                   # Inyección de dependencias (singletons)
│   ├── schemas.py                # Modelos Pydantic (incluye nuevos modelos)
│   └── routes/
│       ├── missions.py           # /missions (con difficulty)
│       ├── vocabulary.py         # /vocabulary
│       ├── chat.py               # /chat  /correct
│       ├── flashcards.py         # /flashcards/export  /flashcards/import-csv
│       ├── voice.py              # /voice (STT/TTS + text fallback)
│       └── progress.py           # /progress (historial, preferencias, flashcard states)
├── db/
│   ├── vocabulary_db.py          # SQLite + carga NGSL CSV
│   ├── user_db.py                # Usuarios (auth)
│   └── user_progress_db.py       # Progreso de usuario (persistencia)
├── voice/
│   ├── config.py                 # VoiceConfig (idioma, backends, etc.)
│   ├── speech_to_text.py         # STT con degradación elegante
│   ├── text_to_speech.py         # TTS (pyttsx3 / gTTS) con degradación elegante
│   └── voice_conversation.py     # Flujo completo de conversación por voz
├── flashcards/
│   ├── anki_export.py            # Exportación TSV/JSON para Anki
│   └── csv_import.py             # Parser y validador de CSV de vocabulario
├── data/
│   ├── core_vocab_500.json       # Vocabulario categorizado con definiciones
│   ├── missions.json             # Misiones con diálogos y ejercicios
│   └── NGSL_1.2_lemmatized_for_teaching.csv
└── tests/
    ├── test_language_tutor.py
    ├── test_vocabulary_db.py
    ├── test_api.py
    ├── test_user_progress_db.py   # Nuevos: persistencia
    ├── test_csv_import.py         # Nuevos: importación CSV
    ├── test_grammar_and_exercises.py  # Nuevos: gramática y ejercicios
    └── test_new_features_api.py   # Nuevos: API voz, progreso, CSV
```

## Requisitos

- Python 3.10+
- Dependencias listadas en `requirements.txt`

```bash
cd agente_idiomas
pip install -r requirements.txt
```

### Dependencias opcionales para voz

Para activar el módulo de voz es necesario instalar dependencias adicionales:

```bash
# TTS offline (recomendado para entornos sin conexión)
pip install pyttsx3

# TTS online (Google Text-to-Speech)
pip install gtts

# STT (micrófono + reconocimiento de voz)
pip install SpeechRecognition pyaudio
```

Si estas dependencias no están instaladas, el módulo de voz opera en **modo texto** (fallback) sin lanzar errores.

## Arrancar el servidor API

```bash
cd agente_idiomas
python3 api_server.py
```

El servidor arranca en `http://localhost:8000`.  
Documentación interactiva disponible en `http://localhost:8000/docs`.

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `USER_DB_PATH` | `data/users.db` | Ruta a la BD SQLite de usuarios |
| `USER_PROGRESS_DB_PATH` | `data/user_progress.db` | Ruta a la BD de progreso de usuario |
| `JWT_SECRET` | requerido | Secreto para firmar tokens JWT |
| `JWT_EXPIRE_MINUTES` | `60` | Expiración del token en minutos |

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del servidor |
| GET | `/missions` | Lista de misiones |
| POST | `/missions` | Crear misión abierta (con `difficulty`) |
| GET | `/missions/{id}` | Detalle de misión |
| GET | `/missions/{id}/vocabulary` | Vocabulario de la misión |
| GET | `/missions/{id}/exercises` | Ejercicios de la misión |
| GET | `/missions/{id}/flashcards` | Flashcards de la misión |
| POST | `/chat` | Conversar con el tutor |
| POST | `/correct` | Corregir un texto (con `why` y `better_example`) |
| GET | `/vocabulary/search?q=` | Buscar en base NGSL |
| GET | `/vocabulary/by-tag?tags=` | Filtrar vocab por categoría |
| GET | `/vocabulary/top` | Palabras más frecuentes |
| POST | `/flashcards/export` | Exportar a TSV para Anki |
| **POST** | **`/flashcards/import-csv`** | **Importar vocabulario desde CSV** |
| **GET** | **`/voice/capabilities`** | **Capacidades STT/TTS disponibles** |
| **POST** | **`/voice/config`** | **Configurar idioma y backends de voz** |
| **POST** | **`/voice/turn/text`** | **Turno de conversación por voz (texto → TTS)** |
| **POST** | **`/voice/session/reset`** | **Reiniciar sesión de voz** |
| **GET** | **`/progress/{user_id}`** | **Resumen de progreso del usuario** |
| **GET/POST** | **`/progress/{user_id}/exercises`** | **Historial y registro de ejercicios** |
| **GET/POST** | **`/progress/{user_id}/conversation`** | **Historial de conversación** |
| **GET/POST** | **`/progress/{user_id}/preferences`** | **Preferencias de usuario** |
| **GET/POST** | **`/progress/{user_id}/flashcards`** | **Estado de flashcards** |

---

## 1. Persistencia de datos de usuario

El módulo `db/user_progress_db.py` persiste en SQLite:

- **Preferencias** (idioma, voz activada, tema, etc.)
- **Historial de ejercicios** (tipo, respuesta, correcto/incorrecto)
- **Historial de conversaciones** (turnos con correcciones)
- **Estado de flashcards** (conocida/desconocida + contador de revisiones)

### Uso desde Python

```python
from db.user_progress_db import UserProgressDB

db = UserProgressDB("data/user_progress.db")

# Guardar preferencia
db.set_preference(user_id=1, key="voice_enabled", value=True)

# Registrar ejercicio
db.record_exercise(
    user_id=1,
    exercise_type="fill_blank",
    prompt="I ___ a dog.",
    user_answer="have",
    correct=True,
    mission_id="mission_001",
)

# Resumen de progreso
summary = db.get_progress_summary(user_id=1)
# {"user_id": 1, "exercises": {"total": 1, "accuracy": 1.0}, ...}
```

### Uso desde la API

```bash
# Resumen de progreso
curl http://localhost:8000/progress/1

# Guardar preferencia
curl -X POST http://localhost:8000/progress/1/preferences \
  -H "Content-Type: application/json" \
  -d '{"key": "voice_enabled", "value": true}'

# Marcar flashcard como conocida
curl -X POST http://localhost:8000/progress/1/flashcards \
  -H "Content-Type: application/json" \
  -d '{"word": "dog", "known": true}'

# Ver flashcards pendientes de repasar
curl http://localhost:8000/progress/1/flashcards/unknown
```

### Diseño / versionado

La tabla `schema_version` registra la versión del esquema. Para añadir una migración:

```python
migrations: dict[int, str] = {
    2: "ALTER TABLE preferences ADD COLUMN notes TEXT;",
}
```

---

## 2. Correcciones gramaticales mejoradas

El corrector detecta:

| Regla | Ejemplo incorrecto | Corrección |
|-------|--------------------|------------|
| `contraction` | `I dont know` | `I don't know` |
| `subject_verb_be` | `She are happy` | `She is happy` |
| `third_person_singular` | `He go to school` | `He goes to school` |
| `double_negative` | `I don't know nothing` | `I don't know anything` |
| `wrong_preposition` | `interested on` | `interested in` |
| `modal_perfective` | `I would of helped` | `I would have helped` |
| `article_a_an` | `a engineer` | `an engineer` |

Cada corrección incluye tres campos explicativos:

```json
{
  "original": "He go",
  "suggested": "He goes",
  "position": 0,
  "rule": "third_person_singular",
  "explanation": "Subject-verb agreement: 'he' requires third-person singular form 'goes'",
  "why": "In the simple present tense, verbs after he/she/it must take the third-person singular form...",
  "better_example": "He goes to school every day."
}
```

### Ejemplo

```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "I would of helped you and she dont know nothing"}'
```

---

## 3. Conversaciones por voz

### Verificar capacidades

```bash
curl http://localhost:8000/voice/capabilities
```

Respuesta (sin dependencias instaladas):

```json
{
  "stt": {"available": false, "backend": "none"},
  "tts": {"available": false, "pyttsx3": false, "gtts": false}
}
```

### Configurar voz

```bash
curl -X POST http://localhost:8000/voice/config \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "language": "en-US", "tts_backend": "pyttsx3", "tts_rate": 150}'
```

### Turno de conversación con voz (API)

```bash
# Sin TTS real (speak_response=false, por defecto en la API)
curl -X POST http://localhost:8000/voice/turn/text \
  -H "Content-Type: application/json" \
  -d '{"text": "I dont know how to say this", "speak_response": false}'
```

### Uso programático completo

```python
from voice.config import VoiceConfig
from voice.voice_conversation import VoiceConversation
from agent.language_tutor import LanguageTutorAgent

agent = LanguageTutorAgent("English")
config = VoiceConfig(enabled=True, language="en-US", tts_backend="pyttsx3")
vc = VoiceConversation(agent, config)

# Turno por voz (escucha micrófono → procesa → habla respuesta)
result = vc.voice_turn()
if result["fallback_to_text"]:
    user_input = input("Escribe tu mensaje: ")
    result = vc.text_turn(user_input)

print("Tutor:", result["response"])
```

### Degradación elegante

Si STT/TTS no están disponibles, el módulo devuelve `fallback_to_text: true` y la aplicación puede mostrar el texto en pantalla o pedir input escrito al usuario.

---

## 4. Ejercicios más completos

Los ejercicios ahora incluyen:

- **Tipos**: `fill_blank`, `multiple_choice`, `translate`, `reorder`, `error_correct`, `match`
- **Niveles**: `beginner`, `intermediate`, `advanced`
- **Campos enriquecidos**: `feedback` (explicación pedagógica), `difficulty`, `pairs` (para match)
- **Más temas**: animals, food, travel, work, school, technology, emotions, weather

### Crear misión con nivel de dificultad

```bash
curl -X POST http://localhost:8000/missions \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Let me practice travel vocabulary",
    "mission_id": "travel_advanced",
    "difficulty": "advanced"
  }'
```

### Ejercicios disponibles por tipo

| Tipo | Descripción |
|------|-------------|
| `fill_blank` | Completar huecos |
| `multiple_choice` | Elegir la respuesta correcta entre opciones |
| `translate` | Traducir la frase |
| `reorder` | Ordenar palabras para formar una oración |
| `error_correct` | Encontrar y corregir el error gramatical |
| `match` | Emparejar palabra con su definición |

---

## 5. Importación de CSV de vocabulario

### Formato del CSV

Columnas **obligatorias**: `word`, `translation`  
Columnas **opcionales**: `definition`, `example`, `tags` (separadas por comas), `difficulty`

```csv
word,translation,definition,example,tags,difficulty
apple,manzana,A round red fruit,I eat an apple every day,food,beginner
passport,pasaporte,Official travel document,I need my passport,travel,beginner
elated,eufórico,Extremely happy,She felt elated after the news,emotions,advanced
```

### Importar desde la API

```bash
curl -X POST http://localhost:8000/flashcards/import-csv \
  -F "file=@mi_vocabulario.csv"
```

Respuesta:

```json
{
  "imported": 15,
  "skipped_duplicates": 3,
  "errors": [],
  "source": "mi_vocabulario.csv",
  "imported_at": "2024-01-15T10:30:00+00:00"
}
```

### Opciones

```bash
# Omitir deduplicación (permite duplicados)
curl -X POST "http://localhost:8000/flashcards/import-csv?skip_duplicates=false" \
  -F "file=@mi_vocabulario.csv"
```

### Uso desde Python

```python
from flashcards.csv_import import VocabularyCSVImporter

importer = VocabularyCSVImporter()

# Desde archivo
result = importer.import_from_file(
    "mi_vocabulario.csv",
    existing_words={"apple", "run"},  # palabras ya existentes
    source_label="mi_vocabulario.csv",
)

# Desde string
csv_content = "word,translation\napple,manzana\nrun,correr\n"
result = importer.import_from_string(csv_content)

print(f"Importadas: {result['imported']}, Duplicadas: {result['skipped_duplicates']}")
```

### Integración con flashcards

Las palabras importadas se añaden automáticamente a `agent.core_vocab` y quedan disponibles para:
- Generación de flashcards en misiones
- Ejercicios de la misión activa
- Estado de revisión en `/progress/{user_id}/flashcards`

---

## Ejemplo: conversación con corrección

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "He go to school every day", "mission_id": "mission_001"}'
```

Respuesta:
```json
{
  "response": "Almost! A small correction: 'He go' → 'He goes'. ...",
  "corrections": [
    {
      "original": "He go",
      "suggested": "He goes",
      "position": 0,
      "rule": "third_person_singular",
      "explanation": "Subject-verb agreement: 'He' requires third-person singular form 'goes'",
      "why": "In the simple present tense, verbs after he/she/it must take the third-person singular form...",
      "better_example": "He goes to school every day."
    }
  ],
  "exercise": null,
  "turn": 2
}
```

### Ejemplo: corrección de texto

```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "I dont have a dog and she dont like cats"}'
```

### Ejemplo: buscar vocabulario

```bash
curl "http://localhost:8000/vocabulary/search?q=travel&limit=5"
curl "http://localhost:8000/vocabulary/by-tag?tags=animals&tags=food"
```

## Ejecutar demo (sin servidor)

```bash
cd agente_idiomas
python3 main.py
```

## Exportar flashcards a Anki (TSV)

### Desde la API

```bash
curl -X POST http://localhost:8000/flashcards/export \
  -H "Content-Type: application/json" \
  -d '{
    "flashcards": [{"front": "dog", "back": {"definition": "A pet", "example": "I have a dog.", "translation": "perro"}}],
    "output_path": "exports/my_deck.tsv"
  }'
```

### Desde Python

```python
from flashcards.anki_export import export_flashcards_to_tsv

export_flashcards_to_tsv([
    {"front": "dog", "back": {"definition": "A pet", "example": "I have a dog.", "translation": "perro"}}
], "exports/my_deck.tsv")
```

## Ejecutar tests

```bash
cd agente_idiomas
python3 -m unittest discover -s tests -p "test_*.py"
```

## Decisiones de diseño

1. **Persistencia**: SQLite con tabla `schema_version` para migraciones futuras. `user_id=0` como usuario anónimo por defecto cuando no hay autenticación.

2. **Gramática**: El corrector es puramente basado en reglas (sin LLM) para ser rápido y predecible. Los nuevos campos `why` y `better_example` son opcionales (backward-compatible).

3. **Voz**: Las dependencias STT/TTS son opcionales — si no están instaladas, el módulo devuelve `fallback_to_text: true` en lugar de lanzar excepciones. La API expone la conversación por voz via texto (`/voice/turn/text`) ya que los servidores no tienen altavoces/micrófono.

4. **Ejercicios**: Los nuevos campos `difficulty` y `feedback` son opcionales en el schema para mantener compatibilidad con misiones predefinidas en `missions.json`.

5. **CSV**: La deduplicación es insensible a mayúsculas. Las entradas importadas se añaden a `core_vocab` en memoria; para persistencia entre reinicios es necesario exportarlas o usar una BD externa.

## Limitaciones conocidas

- El módulo de voz requiere micrófono físico para captura de audio en tiempo real.
- La corrección gramatical es basada en reglas (sin modelo de lenguaje); no detecta errores contextuales complejos.
- Las misiones importadas por CSV se pierden al reiniciar el servidor (sólo persisten en `user_progress.db`, no en `core_vocab`). Una futura mejora sería persistirlas en la BD de vocabulario.
- El módulo de voz comparte una única sesión global; en producción se debería gestionar por usuario/sesión.

