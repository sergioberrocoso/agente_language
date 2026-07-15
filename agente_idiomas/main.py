from agent.language_tutor import LanguageTutorAgent
from flashcards.anki_export import export_flashcards_to_tsv

def main():
    # Crear el agente
    agent = LanguageTutorAgent(language="English")

    # Cargar vocabulario y misiones
    agent.load_core_vocab("data/core_vocab_500.json")
    agent.load_missions("data/missions.json")

    # Seleccionar una misión de ejemplo
    try:
        mission = agent.select_mission("mission_001")
        print("Misión seleccionada:", mission["name"])
    except Exception as e:
        print("Error:", e)

    # Obtener vocabulario relevante
    try:
        vocab = agent.get_mission_vocabulary()
        print("Vocabulario relevante:")
        for word in vocab:
            print("-", word["word"])
    except Exception as e:
        print("Error:", e)

    # Crear misión abierta
    print("\n--- Creando misión abierta ---")
    open_mission = agent.create_open_mission(
        description="I want to practice talking about my dog in the park",
        mission_id="open_001"
    )
    print("Misión abierta creada:", open_mission["name"])
    print("Tags detectados:", open_mission["vocabulary_tags"])

    # Generar flashcards
    print("\n--- Flashcards generadas ---")
    flashcards = agent.generate_flashcards()
    for card in flashcards:
        print("Front:", card["front"])
        print("Back:", card["back"])
        print("---")

    # Exportar mazo en formato TSV listo para importar en Anki.
    output_path = "flashcards/exports/mission_flashcards.tsv"
    export_flashcards_to_tsv(flashcards, output_path)
    print(f"Archivo Anki exportado en: {output_path}")

if __name__ == "__main__":
    main()
