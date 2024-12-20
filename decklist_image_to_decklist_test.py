from PIL import ImageGrab
import easyocr

def extract_text_from_clipboard():
    try:
        # Acquisire l'immagine dalla clipboard
        image = ImageGrab.grabclipboard()
        if image is not None:
            # Salvataggio temporaneo dell'immagine in RAM
            image.save("temp_image.png")
            print("Immagine acquisita dalla clipboard.")
            
            # Inizializzare EasyOCR Reader
            reader = easyocr.Reader(['en', 'it'])  # Specifica le lingue
            results = reader.readtext("temp_image.png", detail=0)
            
            # Mostrare il testo estratto
            print("\n--- Testo estratto dall'immagine ---\n")
            for line in results:
                print(line)
        else:
            print("Nessuna immagine trovata nella clipboard. Copia un'immagine e riprova.")
    except Exception as e:
        print(f"Errore durante l'elaborazione dell'immagine: {e}")

if __name__ == "__main__":
    extract_text_from_clipboard()
