# agente_language

Agente educativo para practicar idiomas con:

- seleccion de misiones predefinidas
- creacion de misiones abiertas a partir de descripciones naturales
- generacion de vocabulario relevante, dialogos y ejercicios
- generacion y exportacion de flashcards a formato Anki

## Estructura

```
agente_idiomas/
	main.py
	agent/
		language_tutor.py
	data/
		core_vocab_500.json
		missions.json
	flashcards/
		anki_export.py
	tests/
		test_language_tutor.py
```

## Requisitos

- Python 3.10+ (recomendado)

No se requieren dependencias externas para ejecutar el ejemplo ni los tests.

## Ejecutar demo

Desde la raiz del repositorio:

```bash
cd agente_idiomas
python3 main.py
```

Esto ejecuta un flujo completo:

1. Carga vocabulario y misiones.
2. Selecciona una mision base.
3. Crea una mision abierta a partir de texto libre.
4. Genera flashcards para la mision activa.

## Exportar flashcards a Anki (TSV)

El modulo de exportacion esta en `agente_idiomas/flashcards/anki_export.py`.

### Opcion A: usar funciones desde Python

```python
from flashcards.anki_export import export_flashcards_to_tsv

flashcards = [
		{
				"front": "dog",
				"back": {
						"definition": "A domesticated animal",
						"example": "I walk my dog every day",
						"translation": "perro"
				}
		}
]

export_flashcards_to_tsv(flashcards, "exports/my_deck.tsv")
```

### Opcion B: CLI desde terminal

Primero crea un JSON con una lista de flashcards, luego:

```bash
cd agente_idiomas
python3 flashcards/anki_export.py flashcards.json exports/my_deck.tsv
```

Despues, importa el archivo TSV en Anki (campos separados por tabulador).

## Ejecutar tests

```bash
cd agente_idiomas
python3 -m unittest discover -s tests -p "test_*.py"
```