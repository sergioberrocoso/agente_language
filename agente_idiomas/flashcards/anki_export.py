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
	"""Exporta una coleccion de flashcards al formato TSV (frente\\tretro).

	*output_path* debe ser una ruta de confianza ya validada por el llamador.
	Nunca pases directamente rutas procedentes de input de usuario sin sanear
	previamente (ver ``validate_export_path`` para CLI y el uso de UUID en API).
	"""
	output = Path(output_path)
	output.parent.mkdir(parents=True, exist_ok=True)

	rows = [_card_to_tsv_row(card) for card in flashcards]
	output.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
	return output


def export_flashcards_to_json(flashcards: Iterable[dict], output_path: str) -> Path:
	"""Exporta flashcards a JSON para uso posterior o debug.

	Mismas precauciones que ``export_flashcards_to_tsv``.
	"""
	output = Path(output_path)
	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text(json.dumps(list(flashcards), indent=2, ensure_ascii=False), encoding="utf-8")
	return output


def validate_export_path(user_path: str, base_dir: Path) -> Path:
	"""Valida y restringe *user_path* al directorio *base_dir*.

	Devuelve la ruta segura y absoluta dentro de *base_dir*, o lanza
	``ValueError`` si el nombre contiene traversal o caracteres no permitidos.
	"""
	base = base_dir.resolve()
	# Solo usar el componente de nombre de archivo; descartar cualquier directorio
	name = Path(user_path).name
	if not name:
		raise ValueError("El nombre de archivo no puede estar vacío.")
	resolved = (base / name).resolve()
	if not str(resolved).startswith(str(base) + "/") and resolved != base:
		raise ValueError(f"Ruta no permitida fuera del directorio base: {user_path}")
	return resolved


if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Exporta flashcards en formato Anki TSV.")
	parser.add_argument("input_json", help="Ruta al JSON con flashcards")
	parser.add_argument("output_tsv", help="Nombre de archivo de salida (se crea en el directorio actual)")
	args = parser.parse_args()

	# Validar y restringir la ruta al directorio actual antes de usar
	try:
		safe_output = validate_export_path(args.output_tsv, Path.cwd())
	except ValueError as exc:
		raise SystemExit(f"Error: {exc}") from exc

	cards = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
	output_file = export_flashcards_to_tsv(cards, str(safe_output))
	print(f"Export completado: {output_file}")

