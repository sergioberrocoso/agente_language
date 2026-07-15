"""Utilidades para exportar flashcards a formatos compatibles con Anki."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def _escape_field(value: str) -> str:
	"""Sanitiza saltos de linea y tabulaciones para TSV."""
	return value.replace("\t", " ").replace("\n", " ").strip()


def _card_to_tsv_row(card: dict) -> str:
	front = _escape_field(str(card.get("front", "")))
	back = card.get("back", {}) if isinstance(card.get("back"), dict) else {}

	definition = _escape_field(str(back.get("definition", "")))
	example = _escape_field(str(back.get("example", "")))
	translation = _escape_field(str(back.get("translation", "")))

	# Anki soporta HTML en campos; <br> mantiene separacion visual en una sola celda.
	back_text = "<br>".join(
		[
			f"Definition: {definition}",
			f"Example: {example}",
			f"Translation: {translation}",
		]
	)
	return f"{front}\t{back_text}"


def export_flashcards_to_tsv(flashcards: Iterable[dict], output_path: str) -> Path:
	"""Exporta una coleccion de flashcards al formato TSV (frente\tretro)."""
	output = Path(output_path)
	output.parent.mkdir(parents=True, exist_ok=True)

	rows = [_card_to_tsv_row(card) for card in flashcards]
	output.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
	return output


def export_flashcards_to_json(flashcards: Iterable[dict], output_path: str) -> Path:
	"""Exporta flashcards a JSON para uso posterior o debug."""
	output = Path(output_path)
	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text(json.dumps(list(flashcards), indent=2, ensure_ascii=False), encoding="utf-8")
	return output


if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Exporta flashcards en formato Anki TSV.")
	parser.add_argument("input_json", help="Ruta al JSON con flashcards")
	parser.add_argument("output_tsv", help="Ruta de salida del archivo TSV")
	args = parser.parse_args()

	cards = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
	output_file = export_flashcards_to_tsv(cards, args.output_tsv)
	print(f"Export completado: {output_file}")
 
