import os
from anthropic import Anthropic

def get_claude_response(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    Łączy się z API Anthropic, wysyła prompty i zwraca czysty tekst odpowiedzi.
    Temperatura domyślnie ustawiona na 0.2 zgodnie z wymogami projektu.
    """
    client = Anthropic()
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        temperature=temperature,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )
    
    return response.content[0].text