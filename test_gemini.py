import google.generativeai as genai

genai.configure(api_key="AIzaSyC2jCwDHrqBEbP2Y4rZZn5EbI4egzPISbc")

try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Привет! Как дела?")
    print("✅ AI работает:", response.text)
except Exception as e:
    print("❌ Ошибка AI:", e)