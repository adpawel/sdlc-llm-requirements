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
$env:SDLC_EXPERIMENT="llm_only"
uv run main.py gpt r2 appointment-booking
```

**Linux / macOS:**
```bash
export OPENAI_API_KEY="twój_klucz_tutaj"
export SDLC_EXPERIMENT="llm_only"
uv run main.py gpt r2 appointment-booking
```


Wyniki eksperymentu (prompty oraz odpowiedzi modeli) są zapisywane w katalogu `outputs/<nazwa_eksperymentu>`.
Domyślny eksperyment to `llm_only`. Aby przełączyć na nowy wariant, ustaw `SDLC_EXPERIMENT="multi_stakeholder"`.

Przykladowe uruchomienie multi-stakeholder:
```bash
$env:SDLC_EXPERIMENT="multi_stakeholder"
uv run main.py gpt r2-ms appointment-booking
```
