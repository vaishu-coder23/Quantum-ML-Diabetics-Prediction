import google.generativeai as genai

# Note: Keep API keys out of repo; this file is informational only.
def list_generate_models(api_key=None):
    if api_key:
        genai.configure(api_key=api_key)
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"{m.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_generate_models()
