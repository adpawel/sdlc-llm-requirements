# SDLC-LLM Benchmark - Requirements Team

Projekt badawczy oceniający możliwości dużych modeli językowych (LLM) w automatycznym wspieraniu analizy wymagań w cyklu życia oprogramowania. Celem jest zbadanie zdolności modeli 
(takich jak GPT-4.1, Claude 3.5 Sonnet, Llama 3.1) do wykrywania niejednoznaczności, braków oraz generowania specyfikacji, w tym user stories.

## Wymagania wstępne
Do uruchomienia projektu wymagany jest Python oraz menedżer pakietów `uv`.

Instalacja narzędzia `uv` (jeśli jeszcze go nie posiadasz):
```bash
pip install uv
```

## Instalacja projektu

1. Sklonuj repozytorium i wejdź do głównego katalogu
2. Pobierz i zainstaluj wszystkie wymagane zależności:
```bash
uv sync
```

## Klucze API
Aplikacja łączy się z zewnętrznymi modelami, dlatego wymaga podania kluczy autoryzacyjnych. Należy je wygenerować na poniższych stronach i ustawić jako zmienne środowiskowe w systemie:
- OpenAI (GPT): platform.openai.com -> Zmienna: OPENAI_API_KEY
- Anthropic (Claude): console.anthropic.com -> Zmienna: ANTHROPIC_API_KEY
- Google (Gemini): aistudio.google.com -> Zmienna: GEMINI_API_KEY
- Groq (Llama): console.groq.com -> Zmienna: GROQ_API_KEY

## Uruchomienie testów
W pliku `main.py` odkomentuj fragment kodu odpowiadający modelowi, który chcesz aktualnie przetestować. Następnie przypisz odpowiedni klucz w terminalu i uruchom skrypt.

**Windows (PowerShell):**
```bash
$env:OPENAI_API_KEY="twój_klucz_tutaj"
uv run main.py
```

**Linux / macOS:**
```bash
export OPENAI_API_KEY="twój_klucz_tutaj"
uv run main.py
```


Wyniki eksperymentu (prompty oraz odpowiedzi modeli) zostaną automatycznie zapisane w ustandaryzowanym formacie w pliku `outputs/r1-inconsistencies.csv`
