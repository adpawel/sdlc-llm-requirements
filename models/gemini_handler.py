import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def get_gemini_response(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    Łączy się z API Gemini. Automatycznie używa zmiennej środowiskowej GEMINI_API_KEY.
    Temperatura domyślnie ustawiona na 0.2 zgodnie z wymogami projektu.
    """
    client = genai.Client()
    
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
        top_p=0.9,
        top_k=40,
        max_output_tokens=4096,
    )
    
    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=user_prompt,
        config=config
    )
    
    return response.text