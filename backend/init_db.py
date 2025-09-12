# -*- coding: utf-8 -*-
import sqlite3
import random
import math

conn = sqlite3.connect('food_delivery.db')
c = conn.cursor()

# Drop existing tables to recreate with new data
c.execute('DROP TABLE IF EXISTS cart')
c.execute('DROP TABLE IF EXISTS menu')
c.execute('DROP TABLE IF EXISTS restaurants')

c.execute('''CREATE TABLE restaurants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT,
    cuisine_type TEXT,
    rating REAL,
    delivery_time INTEGER,
    lat REAL,
    lon REAL,
    description TEXT
)''')

c.execute('''CREATE TABLE menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER,
    item_name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    category TEXT,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
)''')

c.execute('''CREATE TABLE cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER DEFAULT 1,
    restaurant_id INTEGER,
    item_id INTEGER,
    quantity INTEGER,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
    FOREIGN KEY (item_id) REFERENCES menu(id)
)''')

# Generate random restaurant data
restaurant_names = [
    'Бургер Хаус', 'Пицца Мания', 'Суши Токио', 'Тако Лока', 'Паста Бар',
    'Стейк Хаус', 'Китайский Дракон', 'Индийские Специи', 'Французское Бистро', 'Итальянская Терраса',
    'Морские Деликатесы', 'Вегетарианский Рай', 'Мексиканская Фиеста', 'Корейская Кухня', 'Тайские Ароматы',
    'Греческая Таверна', 'Турецкий Гурман', 'Ливанский Дворик', 'Испанская Паэлья', 'Немецкая Пивная',
    'Американский Гриль', 'Японская Кухня', 'Перуанские Вкусы', 'Бразильское Барбекю', 'Аргентинский Гриль'
]

cuisine_types = ['Фастфуд', 'Пицца', 'Суши', 'Мексиканская', 'Итальянская', 'Стейки', 'Китайская', 'Индийская', 'Французская']

# Saint Petersburg center coordinates
base_lat = 59.9311
base_lon = 30.3609

restaurants_data = []
for i, name in enumerate(restaurant_names):
    # Generate coordinates within Saint Petersburg area (roughly 20km radius)
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0.01, 0.15)  # Roughly 1-15km from center
    lat = base_lat + distance * math.cos(angle)
    lon = base_lon + distance * math.sin(angle)
    
    cuisine = random.choice(cuisine_types)
    rating = round(random.uniform(3.5, 5.0), 1)
    delivery_time = random.randint(20, 60)
    
    restaurant_data = (
        name,
        f'ул. {random.choice(["Невский", "Литейный", "Мойки", "Фонтанки", "Каменноостровский", "Васильевский", "Московский"])}, {random.randint(1, 150)}',
        cuisine,
        rating,
        delivery_time,
        lat,
        lon,
        f'Уютный ресторан {cuisine.lower()} кухни с отличным сервисом и быстрой доставкой.'
    )
    restaurants_data.append(restaurant_data)

# Insert restaurants
for restaurant in restaurants_data:
    c.execute('''INSERT INTO restaurants 
                 (name, address, cuisine_type, rating, delivery_time, lat, lon, description) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', restaurant)

# Generate menu items for each restaurant
menu_items = {
    'Фастфуд': [
        ('Биг Бургер', 'Сочный говяжий бургер', 350, 'Основные блюда'),
        ('Картофель фри', 'Хрустящий картофель', 150, 'Гарниры'),
        ('Куриные наггетсы', 'Нежные кусочки курицы', 250, 'Основные блюда')
    ],
    'Пицца': [
        ('Маргарита', 'Классическая пицца с моцареллой', 450, 'Пицца'),
        ('Пепперони', 'Острая пицца с колбасой', 520, 'Пицца'),
        ('Четыре сыра', 'Пицца с четырьмя видами сыра', 580, 'Пицца')
    ],
    'Суши': [
        ('Филадельфия', 'Ролл с лососем и сыром', 420, 'Роллы'),
        ('Калифорния', 'Ролл с крабом и авокадо', 380, 'Роллы'),
        ('Сашими лосось', 'Свежий лосось', 350, 'Сашими')
    ],
    'Итальянская': [
        ('Карбонара', 'Паста с беконом и сыром', 390, 'Паста'),
        ('Лазанья', 'Классическая лазанья', 450, 'Основные блюда'),
        ('Ризотто', 'Кремовый рис с грибами', 380, 'Основные блюда')
    ]
}

# Default menu for other cuisines
default_menu = [
    ('Фирменное блюдо', 'Специальность заведения', 400, 'Основные блюда'),
    ('Суп дня', 'Горячий суп', 200, 'Супы'),
    ('Десерт', 'Сладкий десерт', 180, 'Десерты')
]

# Insert menu items
for i, (name, address, cuisine, rating, delivery_time, lat, lon, description) in enumerate(restaurants_data, 1):
    menu_for_cuisine = menu_items.get(cuisine, default_menu)
    for item_name, item_desc, price, category in menu_for_cuisine:
        # Add some price variation
        varied_price = price + random.randint(-50, 100)
        c.execute('''INSERT INTO menu 
                     (restaurant_id, item_name, description, price, category) 
                     VALUES (?, ?, ?, ?, ?)''', 
                  (i, item_name, item_desc, varied_price, category))

conn.commit()
conn.close()
print(f'Database initialized with {len(restaurants_data)} restaurants and their menus')
