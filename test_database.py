from ai_tools import AITools

tools = AITools()

# Тестируем разные форматы телефона
phones_to_test = [
    "+79995554433",
    "79995554433", 
    "+7 999 555 44 33",
    "8 999 555 44 33"
]

for phone in phones_to_test:
    print(f"\nТестируем телефон: '{phone}'")
    bookings = tools.get_user_bookings(phone)
    print(f"Найдено: {len(bookings)} бронирований")
    for booking in bookings:
        print(f"  #{booking['id']}: {booking['date']} {booking['time']}, статус: {booking['status']}")