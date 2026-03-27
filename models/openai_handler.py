import os
from openai import OpenAI

def get_openai_response(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    Łączy się z API OpenAI, wysyła prompty i zwraca czysty tekst odpowiedzi.
    Temperatura domyślnie ustawiona na 0.2 zgodnie z wymogami projektu.
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature
    )
    
    # Zwracamy wyłącznie sam tekst wygenerowany przez LLM
    return response.choices[0].message.content