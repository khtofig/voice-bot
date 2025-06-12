from ai_tools import AITools

tools = AITools()

print("🧪 ТЕСТИРОВАНИЕ CONFIDENCE SCORING:")
print("=" * 60)

# Тест 1: Высокий confidence
print("ТЕСТ 1: Высокий confidence")
analysis1 = tools.analyze_response_confidence(
    "Хочу забронировать столик",
    "Конечно! У нас есть свободные места. Уточните количество гостей и время."
)
print(f"  Confidence: {analysis1['confidence']:.2f}")
print(f"  Эскалация: {analysis1['should_escalate']}")
print(f"  Причины: {analysis1['reasons']}")
print()

# Тест 2: Низкий confidence - неуверенные фразы
print("ТЕСТ 2: Низкий confidence - неуверенные фразы")
analysis2 = tools.analyze_response_confidence(
    "Есть ли столики?",
    "Возможно есть, но не уверен. Наверное можно что-то найти..."
)
print(f"  Confidence: {analysis2['confidence']:.2f}")
print(f"  Эскалация: {analysis2['should_escalate']}")
print(f"  Причины: {analysis2['reasons']}")
print()

# Тест 3: Сложный запрос
print("ТЕСТ 3: Сложный запрос (автоэскалация)")
analysis3 = tools.analyze_response_confidence(
    "Хочу VIP зал для корпоратива на 50 человек с особым меню",
    "Это можно организовать"
)
print(f"  Confidence: {analysis3['confidence']:.2f}")
print(f"  Эскалация: {analysis3['should_escalate']}")
print(f"  Причины: {analysis3['reasons']}")
print()

# Тест 4: Fallback фразы
print("ТЕСТ 4: Fallback фразы")
fallback1 = tools.get_fallback_response('low_confidence')
fallback2 = tools.get_fallback_response('complex_request')
fallback3 = tools.get_fallback_response('error')

print(f"  Low confidence: {fallback1}")
print(f"  Complex request: {fallback2}")  
print(f"  Error: {fallback3}")
print()

# Тест 5: Запрос человека
print("ТЕСТ 5: Обнаружение запроса человека")
needs_human1, reason1 = tools.should_request_human_help("хочу говорить с человеком", [])
needs_human2, reason2 = tools.should_request_human_help("соедините с менеджером", [])
needs_human3, reason3 = tools.should_request_human_help("обычный вопрос о меню", [])

print(f"  'хочу говорить с человеком': {needs_human1} ({reason1})")
print(f"  'соедините с менеджером': {needs_human2} ({reason2})")
print(f"  'обычный вопрос о меню': {needs_human3} ({reason3})")

print("\n✅ Тестирование завершено!")