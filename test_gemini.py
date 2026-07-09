from dotenv import load_dotenv
import os
import google.generativeai as genai

load_dotenv()

key=os.getenv("GEMINI_API_KEY")

genai.configure(api_key=key)

model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
model = genai.GenerativeModel(model_name)

response = model.generate_content("Say working")
print(response.text)
