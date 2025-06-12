from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import RestaurantDatabase
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Замените на случайную строку

# Подключаем базу данных
db = RestaurantDatabase()

@app.route('/')
def dashboard():
    """Главная страница - дашборд ресторана"""
    # Прямое подключение к базе для получения всех данных
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    
    # Получаем данные ресторана включая новые поля
    cursor.execute("SELECT name, phone, address, working_hours, greeting_message, ai_personality FROM restaurants WHERE id = 1")
    restaurant_data = cursor.fetchone()
    
    # Получаем меню
    cursor.execute("SELECT category, name, description, price FROM menu_items WHERE restaurant_id = 1")
    menu_items = cursor.fetchall()
    
    # Получаем сводку по столикам
    cursor.execute("""
        SELECT location_type, COUNT(*), SUM(seats_count)
        FROM tables 
        WHERE restaurant_id = 1 AND status = 'active'
        GROUP BY location_type
    """)
    tables_summary = cursor.fetchall()
    
    # Получаем последние бронирования
    cursor.execute("""
        SELECT b.customer_name, b.booking_date, b.booking_time, b.guests_count, 
               b.status, t.table_number, t.location_type
        FROM bookings b
        LEFT JOIN tables t ON b.table_id = t.id
        WHERE b.restaurant_id = 1 
        ORDER BY b.created_at DESC 
        LIMIT 5
    """)
    recent_bookings = cursor.fetchall()
    
    conn.close()
    
    if not restaurant_data:
        flash('Ресторан не найден в базе данных', 'error')
        return render_template('dashboard.html', 
                             restaurant={'name': 'Не настроен', 'phone': '', 'address': '', 'working_hours': '', 'greeting_message': '', 'ai_personality': ''},
                             menu_by_category={}, tables_summary=[], recent_bookings=[])
    
    # Распаковываем данные
    name, phone, address, working_hours, greeting_message, ai_personality = restaurant_data
    
    # Группируем меню по категориям
    menu_by_category = {}
    for category, item_name, description, price in menu_items:
        if category not in menu_by_category:
            menu_by_category[category] = []
        menu_by_category[category].append({
            'name': item_name,
            'description': description,
            'price': price
        })
    
    return render_template('dashboard.html', 
                         restaurant={
                             'name': name,
                             'phone': phone,
                             'address': address,
                             'working_hours': working_hours,
                             'greeting_message': greeting_message,
                             'ai_personality': ai_personality
                         },
                         menu_by_category=menu_by_category,
                         tables_summary=tables_summary,
                         recent_bookings=recent_bookings)

# =============== УПРАВЛЕНИЕ СТОЛИКАМИ ===============

@app.route('/tables')
def tables_list():
    """Список всех столиков С ПРАВИЛЬНОЙ СТАТИСТИКОЙ"""
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, table_number, seats_count, location_type, description, status
        FROM tables 
        WHERE restaurant_id = 1 
        ORDER BY CAST(table_number AS INTEGER)
    """)
    
    tables = cursor.fetchall()
    
    # Группируем по типу расположения И считаем статистику
    tables_by_location = {}
    total_tables = 0
    total_seats = 0
    
    for table in tables:
        table_id, number, seats, location, description, status = table
        
        # Считаем статистику
        total_tables += 1
        total_seats += seats
        
        # Группируем
        if location not in tables_by_location:
            tables_by_location[location] = []
        
        tables_by_location[location].append({
            'id': table_id,
            'number': number,
            'seats': seats,
            'location': location,
            'description': description,
            'status': status
        })
    
    # Рассчитываем среднее
    average_seats = round(total_seats / total_tables, 1) if total_tables > 0 else 0
    
    conn.close()
    
    # Формируем статистику
    stats = {
        'total_tables': total_tables,
        'total_seats': total_seats,
        'total_locations': len(tables_by_location),
        'average_seats': average_seats
    }
    
    return render_template('tables.html', 
                         tables_by_location=tables_by_location,
                         stats=stats)

@app.route('/add_table', methods=['GET', 'POST'])
def add_table():
    """Добавление нового столика"""
    if request.method == 'POST':
        table_number = request.form['table_number']
        seats_count = int(request.form['seats_count'])
        location_type = request.form['location_type']
        description = request.form['description']
        
        conn = sqlite3.connect('restaurant.db')
        cursor = conn.cursor()
        
        # Проверяем что номер столика не занят
        cursor.execute("SELECT COUNT(*) FROM tables WHERE table_number = ? AND restaurant_id = 1", (table_number,))
        if cursor.fetchone()[0] > 0:
            flash(f'Столик №{table_number} уже существует', 'error')
            conn.close()
            return redirect(url_for('add_table'))
        
        cursor.execute("""
            INSERT INTO tables (restaurant_id, table_number, seats_count, location_type, description, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (1, table_number, seats_count, location_type, description, 'active'))   
        
        conn.commit()
        conn.close()
        
        flash(f'Столик №{table_number} успешно добавлен!', 'success')
        return redirect(url_for('tables_list'))
    
    return render_template('add_table.html')

@app.route('/edit_table/<int:table_id>', methods=['GET', 'POST'])
def edit_table(table_id):
    """Редактирование столика"""
    if request.method == 'POST':
        table_number = request.form['table_number']
        seats_count = int(request.form['seats_count'])
        location_type = request.form['location_type']
        description = request.form['description']
        status = request.form['status']
        
        conn = sqlite3.connect('restaurant.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tables 
            SET table_number=?, seats_count=?, location_type=?, description=?, status=?
            WHERE id=? AND restaurant_id=1
        """, (table_number, seats_count, location_type, description, status, table_id))
        
        conn.commit()
        conn.close()
        
        flash(f'Столик №{table_number} обновлен!', 'success')
        return redirect(url_for('tables_list'))
    
    # GET запрос - получаем данные столика
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tables WHERE id = ? AND restaurant_id = 1", (table_id,))
    table_data = cursor.fetchone()
    conn.close()
    
    if not table_data:
        flash('Столик не найден', 'error')
        return redirect(url_for('tables_list'))
    
    return render_template('edit_table.html', table={
        'id': table_data[0],
        'number': table_data[2],
        'seats': table_data[3],
        'location': table_data[4],
        'description': table_data[5],
        'status': table_data[6]
    })

@app.route('/delete_table/<int:table_id>')
def delete_table(table_id):
    """Удаление столика"""
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    
    # Проверяем есть ли активные бронирования на этот столик
    cursor.execute("""
        SELECT COUNT(*) FROM bookings 
        WHERE table_id = ? AND status NOT IN ('отменено', 'завершено')
    """, (table_id,))
    
    active_bookings = cursor.fetchone()[0]
    
    if active_bookings > 0:
        flash(f'Нельзя удалить столик - есть {active_bookings} активных бронирований', 'error')
        conn.close()
        return redirect(url_for('tables_list'))
    
    # Получаем номер столика для сообщения
    cursor.execute("SELECT table_number FROM tables WHERE id = ?", (table_id,))
    table_number = cursor.fetchone()[0]
    
    # Удаляем столик
    cursor.execute("DELETE FROM tables WHERE id = ? AND restaurant_id = 1", (table_id,))
    
    conn.commit()
    conn.close()
    
    flash(f'Столик №{table_number} удален', 'success')
    return redirect(url_for('tables_list'))

# =============== СУЩЕСТВУЮЩИЕ ФУНКЦИИ ===============

@app.route('/edit_restaurant', methods=['GET', 'POST'])
def edit_restaurant():
    """Редактирование информации о ресторане"""
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']
        working_hours = request.form['working_hours']
        
        # Прямое обновление через SQLite
        conn = sqlite3.connect('restaurant.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE restaurants 
            SET name=?, phone=?, address=?, working_hours=?
            WHERE id=1
        """, (name, phone, address, working_hours))
        
        conn.commit()
        conn.close()
        
        flash('Информация о ресторане обновлена!', 'success')
        return redirect(url_for('dashboard'))
    
    # GET запрос - получаем данные для формы
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, phone, address, working_hours FROM restaurants WHERE id = 1")
    restaurant_data = cursor.fetchone()
    conn.close()
    
    if not restaurant_data:
        flash('Ресторан не найден', 'error')
        return redirect(url_for('dashboard'))
    
    name, phone, address, working_hours = restaurant_data
    
    return render_template('edit_restaurant.html', restaurant={
        'name': name,
        'phone': phone,
        'address': address,
        'working_hours': working_hours
    })

@app.route('/bot_settings', methods=['GET', 'POST'])
def bot_settings():
    """Настройки бота"""
    if request.method == 'POST':
        greeting_message = request.form['greeting_message']
        ai_personality = request.form['ai_personality']
        
        # Прямое обновление через SQLite
        conn = sqlite3.connect('restaurant.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE restaurants 
            SET greeting_message=?, ai_personality=?
            WHERE id=1
        """, (greeting_message, ai_personality))
        
        conn.commit()
        conn.close()
        
        flash('Настройки бота обновлены!', 'success')
        return redirect(url_for('dashboard'))
    
    # GET запрос - показываем форму
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    cursor.execute("SELECT greeting_message, ai_personality FROM restaurants WHERE id = 1")
    bot_data = cursor.fetchone()
    conn.close()
    
    if not bot_data:
        flash('Ресторан не найден', 'error')
        return redirect(url_for('dashboard'))
    
    greeting_message, ai_personality = bot_data
    
    return render_template('bot_settings.html', bot={
        'greeting_message': greeting_message,
        'ai_personality': ai_personality
    })

@app.route('/menu')
def menu_list():
    """Список меню"""
    # Используем прямой SQL запрос
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    cursor.execute("SELECT category, name, description, price FROM menu_items WHERE restaurant_id = 1")
    menu_items = cursor.fetchall()
    conn.close()
    
    # Группируем по категориям
    menu_by_category = {}
    for category, item_name, description, price in menu_items:
        if category not in menu_by_category:
            menu_by_category[category] = []
        menu_by_category[category].append({
            'name': item_name,
            'description': description,
            'price': price
        })
    
    return render_template('menu.html', menu_by_category=menu_by_category)

@app.route('/add_menu_item', methods=['GET', 'POST'])
def add_menu_item():
    """Добавление нового блюда"""
    if request.method == 'POST':
        category = request.form['category']
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        
        conn = sqlite3.connect('restaurant.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO menu_items (restaurant_id, category, name, description, price)
            VALUES (?, ?, ?, ?, ?)
        """, (1, category, name, description, price))   
        
        conn.commit()
        conn.close()
        
        flash(f'Блюдо "{name}" добавлено в меню!', 'success')
        return redirect(url_for('menu_list'))
    
    return render_template('add_menu_item.html')

@app.route('/edit_menu_item/<item_name>', methods=['GET', 'POST'])
def edit_menu_item(item_name):
    """Редактирование блюда"""
    if request.method == 'POST':
        category = request.form['category']
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        
        conn = sqlite3.connect('restaurant.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE menu_items 
            SET category=?, name=?, description=?, price=?
            WHERE name=?
        """, (category, name, description, price, item_name))
        
        conn.commit()
        conn.close()
        
        flash(f'Блюдо обновлено!', 'success')
        return redirect(url_for('menu_list'))
    
    # GET запрос - получаем данные блюда
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu_items WHERE name = ?", (item_name,))
    item_data = cursor.fetchone()
    conn.close()
    
    if not item_data:
        flash('Блюдо не найдено', 'error')
        return redirect(url_for('menu_list'))
    
    return render_template('edit_menu_item.html', item={
        'category': item_data[2],
        'name': item_data[3],
        'description': item_data[4],
        'price': item_data[5]
    })

@app.route('/delete_menu_item/<item_name>')
def delete_menu_item(item_name):
    """Удаление блюда"""
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM menu_items WHERE name = ?", (item_name,))
    
    conn.commit()
    conn.close()
    
    flash(f'Блюдо "{item_name}" удалено из меню', 'success')
    return redirect(url_for('menu_list'))

@app.route('/bookings')
def bookings_list():
    """Список всех бронирований С УКАЗАНИЕМ СТОЛИКОВ"""
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT b.id, b.customer_name, b.customer_phone, b.booking_date, b.booking_time, 
               b.guests_count, b.status, b.notes, b.created_at, b.special_requests,
               t.table_number, t.location_type, t.seats_count
        FROM bookings b
        LEFT JOIN tables t ON b.table_id = t.id
        WHERE b.restaurant_id = 1 
        ORDER BY b.booking_date DESC, b.booking_time DESC
    """)
    
    bookings = cursor.fetchall()
    conn.close()
    
    return render_template('bookings.html', bookings=bookings)

@app.route('/booking/<int:booking_id>/status/<new_status>')
def update_booking_status(booking_id, new_status):
    """Изменение статуса бронирования"""
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    
    cursor.execute("UPDATE bookings SET status = ? WHERE id = ?", (new_status, booking_id))
    conn.commit()
    conn.close()
    
    flash(f'Статус бронирования изменен на "{new_status}"', 'success')
    return redirect(url_for('bookings_list'))

if __name__ == '__main__':
    print("🌐 Запуск веб-интерфейса...")
    print("📱 Откройте: http://localhost:5000")
    app.run(debug=True, port=5000)