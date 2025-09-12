from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import math

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication
DB_PATH = 'food_delivery.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat/2) * math.sin(dlat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon/2) * math.sin(dlon/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance

def calculate_delivery_time(distance_km, base_time_minutes=20):
    """Calculate estimated delivery time based on distance"""
    # Base time + 2 minutes per km
    return int(base_time_minutes + (distance_km * 2))

@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    cuisine_filter = request.args.get('cuisine', '')
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    
    conn = get_db()
    cur = conn.cursor()
    
    if cuisine_filter:
        cur.execute('SELECT * FROM restaurants WHERE cuisine_type LIKE ?', (f'%{cuisine_filter}%',))
    else:
        cur.execute('SELECT * FROM restaurants')
    
    restaurants = []
    for row in cur.fetchall():
        restaurant = dict(row)
        
        # Calculate distance and delivery time if user location provided
        if user_lat and user_lon:
            distance = calculate_distance(user_lat, user_lon, restaurant['lat'], restaurant['lon'])
            restaurant['distance'] = round(distance, 1)
            restaurant['estimated_delivery'] = calculate_delivery_time(distance, restaurant['delivery_time'])
        
        restaurants.append(restaurant)
    
    # Sort by distance if user location provided
    if user_lat and user_lon:
        restaurants.sort(key=lambda x: x.get('distance', float('inf')))
    
    conn.close()
    return jsonify(restaurants)

@app.route('/restaurant/<int:restaurant_id>', methods=['GET'])
def get_restaurant_details(restaurant_id):
    conn = get_db()
    cur = conn.cursor()
    
    # Get restaurant info
    cur.execute('SELECT * FROM restaurants WHERE id=?', (restaurant_id,))
    restaurant = dict(cur.fetchone())
    
    # Get menu items
    cur.execute('SELECT * FROM menu WHERE restaurant_id=? ORDER BY category', (restaurant_id,))
    menu_items = [dict(row) for row in cur.fetchall()]
    
    # Group menu by category
    menu_by_category = {}
    for item in menu_items:
        category = item['category']
        if category not in menu_by_category:
            menu_by_category[category] = []
        menu_by_category[category].append(item)
    
    restaurant['menu'] = menu_by_category
    
    conn.close()
    return jsonify(restaurant)

@app.route('/menu/<int:restaurant_id>', methods=['GET'])
def get_menu(restaurant_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM menu WHERE restaurant_id=?', (restaurant_id,))
    menu = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(menu)

@app.route('/cart', methods=['POST'])
def add_to_cart():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    
    # Check if item already exists in cart
    cur.execute('SELECT * FROM cart WHERE user_id=? AND item_id=?', 
                (data.get('user_id', 1), data['item_id']))
    existing_item = cur.fetchone()
    
    if existing_item:
        # Update quantity
        new_quantity = existing_item['quantity'] + data.get('quantity', 1)
        cur.execute('UPDATE cart SET quantity=? WHERE id=?', (new_quantity, existing_item['id']))
    else:
        # Insert new item
        cur.execute('''INSERT INTO cart (user_id, restaurant_id, item_id, quantity) 
                       VALUES (?, ?, ?, ?)''',
                    (data.get('user_id', 1), data['restaurant_id'], 
                     data['item_id'], data.get('quantity', 1)))
    
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Item added to cart'})

@app.route('/cart/<int:user_id>', methods=['GET'])
def get_cart(user_id=1):
    conn = get_db()
    cur = conn.cursor()
    
    # Get cart items with restaurant and menu details
    cur.execute('''
        SELECT c.*, m.item_name, m.description, m.price, m.category,
               r.name as restaurant_name, r.lat, r.lon, r.address
        FROM cart c
        JOIN menu m ON c.item_id = m.id
        JOIN restaurants r ON c.restaurant_id = r.id
        WHERE c.user_id = ?
    ''', (user_id,))
    
    cart_items = [dict(row) for row in cur.fetchall()]
    
    # Group by restaurant and calculate totals
    restaurants_in_cart = {}
    total_amount = 0
    
    for item in cart_items:
        restaurant_id = item['restaurant_id']
        if restaurant_id not in restaurants_in_cart:
            restaurants_in_cart[restaurant_id] = {
                'restaurant_name': item['restaurant_name'],
                'restaurant_address': item['address'],
                'lat': item['lat'],
                'lon': item['lon'],
                'items': [],
                'subtotal': 0
            }
        
        item_total = item['price'] * item['quantity']
        restaurants_in_cart[restaurant_id]['items'].append(item)
        restaurants_in_cart[restaurant_id]['subtotal'] += item_total
        total_amount += item_total
    
    conn.close()
    
    return jsonify({
        'restaurants': restaurants_in_cart,
        'total_amount': total_amount,
        'total_items': len(cart_items)
    })

@app.route('/cart/item/<int:item_id>', methods=['DELETE'])
def remove_from_cart(item_id):
    user_id = request.args.get('user_id', 1, type=int)
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM cart WHERE user_id=? AND item_id=?', (user_id, item_id))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'Item removed from cart'})

@app.route('/cart/clear', methods=['POST'])
def clear_cart():
    user_id = request.json.get('user_id', 1)
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM cart WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'Cart cleared'})

@app.route('/route', methods=['POST'])
def calculate_route():
    data = request.json
    user_lat = data['user_lat']
    user_lon = data['user_lon']
    restaurants = data['restaurants']
    
    route_info = []
    total_distance = 0
    total_time = 0
    
    current_lat, current_lon = user_lat, user_lon
    
    for restaurant in restaurants:
        distance = calculate_distance(current_lat, current_lon, restaurant['lat'], restaurant['lon'])
        delivery_time = calculate_delivery_time(distance)
        
        route_info.append({
            'restaurant_name': restaurant['name'],
            'distance_km': round(distance, 1),
            'delivery_time_minutes': delivery_time,
            'lat': restaurant['lat'],
            'lon': restaurant['lon']
        })
        
        total_distance += distance
        total_time += delivery_time
        
        # Update current position for next calculation
        current_lat, current_lon = restaurant['lat'], restaurant['lon']
    
    return jsonify({
        'route': route_info,
        'total_distance_km': round(total_distance, 1),
        'total_delivery_time_minutes': total_time
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Food Delivery API Server Starting...")
    print("📱 Access from your phone using:")
    print("   http://192.168.0.163:5000")
    print("💻 Access from this computer using:")
    print("   http://localhost:5000")
    print("🌐 Frontend available at:")
    print("   http://192.168.0.163:8000 (phone)")
    print("   http://localhost:8000 (computer)")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
