import os
from groq import Groq

def get_llama_response(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    Łączy się z API Groq w celu użycia modelu Llama. 
    Automatycznie używa zmiennej środowiskowej GROQ_API_KEY.
    Temperatura domyślnie ustawiona na 0.2 zgodnie z wymogami projektu.
    """
    client = Groq()
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
    )
    
    return response.choices[0].message.content