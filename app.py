from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        number TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        price REAL NOT NULL,
        image TEXT NOT NULL,
        structure TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS booking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        date DATE NOT NULL,
        time TIME NOT NULL,
        guests INTEGER NOT NULL
    )''')

    conn.commit()
    conn.close()

@app.route('/')
def home():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, name, description, image FROM menu_items LIMIT 3") # Ограничение количества блюд
    items = c.fetchall()
    conn.close()

    featured_items = [
        {"id": item[0], "name": item[1], "description": item[2], "image": item[3]}
        for item in items
    ]

    return render_template('index.html', featured_items=featured_items)

@app.route('/menu')
def menu():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, name, description, price, image FROM menu_items")
    items = c.fetchall()
    conn.close()

    menu_items = [
        {"id": item[0], "name": item[1], "description": item[2], "price": item[3], "image": item[4]}
        for item in items
    ]

    return render_template('menu.html', menu_items=menu_items)

@app.route('/menu/<int:item_id>')
def menu_item(item_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT name, description, price, image, ingredients FROM menu_items WHERE id = ?", (item_id,))
    item = c.fetchone()
    conn.close()

    if item:
        dish = {"name": item[0], "description": item[1], "price": item[2], "image": item[3], "ingredients": item[4]}
        return render_template('menu_item.html', dish=dish)
    else:
        flash("Блюдо не найдено", "error")
        return redirect(url_for('menu'))


@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if 'user' not in session:
        flash('You must be logged in to make a booking.', 'error')
        return redirect(url_for('login'))

    username = session['user']

    # Get email and phone from the database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, phone FROM users WHERE username = ?", (username,))
    user_data = cursor.fetchone()
    email = user_data[0] if user_data else ''
    phone = user_data[1] if user_data else ''  # Ensure phone is defined

    if request.method == 'POST':
        email = request.form['email']
        phone = request.form['phone']
        date = request.form['date']
        time = request.form['time']
        guests = request.form['guests']

        try:
            cursor.execute("INSERT INTO booking(name, email, phone, date, time, guests) VALUES(?, ?, ?, ?, ?, ?)",
                           (username, email, phone, date, time, guests))
            conn.commit()
            flash('Бронирование прошло успешно', 'success')
        except sqlite3.IntegrityError:
            flash('Дата уже забронирована', 'error')
            return redirect(url_for('booking'))
        finally:
            conn.close()

    return render_template('booking.html', username=username, email=email, phone=phone)



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', 'no_email@domain.com')
        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", (username, hashed_password, email))
            conn.commit()
            conn.close()
            flash('Регистрация прошла успешно!', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Пользователь уже зарегистрирован!', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        flash('Сначала войдите в аккаунт.', 'error')
        return redirect(url_for('login'))

    username = session['user']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    if request.method == 'POST':
        new_username = request.form['username']
        new_email = request.form['email']
        new_phone = request.form['phone']
        new_password = request.form['password']

        # Получаем старые данные пользователя из базы
        c.execute("SELECT username, email, phone, password FROM users WHERE username = ?", (username,))
        user_data = c.fetchone()

        # Если новый пароль пустой, оставляем старый пароль
        if new_password == '':
            new_password = user_data[3]  # Старый пароль из базы данных
        else:
            # Хешируем новый пароль, если он был введен
            new_password = generate_password_hash(new_password)

        try:
            # Обновляем только те поля, которые были изменены
            c.execute("UPDATE users SET username = ?, email = ?, phone = ?, password = ? WHERE username = ?",
                       (new_username, new_email, new_phone, new_password, username))
            conn.commit()
            session['user'] = new_username  # Обновляем имя пользователя в сессии
            flash('Профиль успешно обновлён!', 'success')
        except sqlite3.IntegrityError:
            flash('Такое имя пользователя уже занято.', 'error')

    # Загружаем данные пользователя из базы
    c.execute("SELECT username, email, phone FROM users WHERE username = ?", (username,))
    user_data = c.fetchone()
    conn.close()

    return render_template('profile.html', user=user_data)





@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session['user'] = username

            flash('Вы успешно вошли', 'success')
            return redirect(url_for('home'))
        else:
            flash('Не правильные данные', 'error')
            return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Вы вышли из аккаунта', 'success') # Второй параметр а точнее 'success' отвечает за цвет
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)