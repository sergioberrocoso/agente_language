# agente_language

Agente educativo para practicar idiomas con:

- selección de misiones predefinidas
- creación de misiones abiertas a partir de descripciones naturales
- corrección gramatical basada en reglas (contracciones, concordancia sujeto-verbo, artículos)
- conversación interactiva con feedback y ejercicios
- generación de ejercicios fill-in-the-blank
- base de datos SQLite de vocabulario (NGSL, 2800+ palabras)
- generación y exportación de flashcards a formato Anki

## Arquitectura

```
agente_idiomas/
├── requirements.txt
├── main.py                   # Demo standalone
├── api_server.py             # Arranca el servidor FastAPI
├── agent/
│   └── language_tutor.py     # Núcleo del agente (corrección, conversación, ejercicios)
├── api/
│   ├── app.py                # Aplicación FastAPI
│   ├── deps.py               # Inyección de dependencias (singleton agente + BD)
│   ├── schemas.py            # Modelos Pydantic
│   └── routes/
│       ├── missions.py       # /missions
│       ├── vocabulary.py     # /vocabulary
│       ├── chat.py           # /chat  /correct
│       └── flashcards.py     # /flashcards/export
├── db/
│   └── vocabulary_db.py      # SQLite + carga NGSL CSV
├── data/
│   ├── core_vocab_500.json   # Vocabulario categorizado con definiciones
│   ├── missions.json         # 5 misiones con diálogos y ejercicios
│   └── NGSL_1.2_lemmatized_for_teaching.csv
├── flashcards/
│   └── anki_export.py        # Exportación TSV/JSON para Anki
└── tests/
    ├── test_language_tutor.py
    ├── test_vocabulary_db.py
    └── test_api.py
```

## Requisitos

- Python 3.10+
- Dependencias listadas en `requirements.txt`

```bash
cd agente_idiomas
pip install -r requirements.txt
```

## Arrancar el servidor API

```bash
cd agente_idiomas
python3 api_server.py
```

El servidor arranca en `http://localhost:8000`.
Documentación interactiva disponible en `http://localhost:8000/docs`.

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del servidor |
| GET | `/missions` | Lista de misiones |
| POST | `/missions` | Crear misión abierta |
| GET | `/missions/{id}` | Detalle de misión |
| GET | `/missions/{id}/vocabulary` | Vocabulario de la misión |
| GET | `/missions/{id}/exercises` | Ejercicios de la misión |
| GET | `/missions/{id}/flashcards` | Flashcards de la misión |
| POST | `/chat` | Conversar con el tutor |
| POST | `/correct` | Corregir un texto |
| GET | `/vocabulary/search?q=` | Buscar en base NGSL |
| GET | `/vocabulary/by-tag?tags=` | Filtrar vocab por categoría |
| GET | `/vocabulary/top` | Palabras más frecuentes |
| POST | `/flashcards/export` | Exportar a TSV para Anki |

### Ejemplo: conversación con corrección

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
      "explanation": "Subject-verb agreement: 'He' requires third-person singular form 'goes'"
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

### CLI desde terminal

```bash
cd agente_idiomas
python3 flashcards/anki_export.py flashcards.json exports/my_deck.tsv
```

## Ejecutar tests

```bash
cd agente_idiomas
python3 -m unittest discover -s tests -p "test_*.py"
```
