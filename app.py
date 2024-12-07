import logging
from flask import Flask, request, jsonify
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal
import pandas as pd
import uuid 
import cloudinary
import cloudinary.uploader




logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

# Fungsi untuk koneksi ke PostgreSQL
def dapatkan_koneksi_db():
    return psycopg2.connect(
        host="localhost",
        database="umkm_tyaskitchen",
        user="postgres",
        password="root",  # Ganti dengan password PostgreSQL kamu
        port="5432"  # Port default PostgreSQL
    )


# Konfigurasi Cloudinary
cloudinary.config(
    cloud_name="dvikahwug",  # Ganti dengan Cloudinary cloud_name
    api_key="475351695686969",  # Ganti dengan Cloudinary API Key
    api_secret="HKUoAsZI5hLLtp7WmWgMGkgcAw4"  # Ganti dengan Cloudinary API Secret
)

@app.route('/')
def home():
    return "API sedang berjalan!"


# Load CSV data into a DataFrame when the app starts
csv_file_path = 'C:\\api_umkm\\UMKM_TyasKitchen.csv'

transactions_df = pd.read_csv(csv_file_path)


# Preprocessing untuk Apriori
def preprocess_transactions(df):
    # Ubah data menjadi format basket agar siap untuk digunakan oleh algoritma Apriori
    basket = df.groupby(['Transaksi ID']).sum()
    basket = basket.applymap(lambda x: 1 if x > 0 else 0)
    return basket

# Asumsikan transaksi_df adalah DataFrame yang sudah didefinisikan sebelumnya
basket = preprocess_transactions(transactions_df)









from psycopg2.errors import UniqueViolation
from werkzeug.security import generate_password_hash
from flask import jsonify, request

# Rute untuk registrasi pengguna baru
@app.route('/register', methods=['POST'])
def registrasi():
    koneksi = dapatkan_koneksi_db()
    data = request.json
    username = data.get('username')
    password = data.get('password')
    nomor_hp = data.get('nomor_hp')  # Menggunakan nomor HP sebagai pengganti email
    alamat = data.get('alamat')
    role_id = data.get('roleID')

    # Memeriksa apakah semua field sudah diisi
    if not username or not password or not nomor_hp or not alamat or not role_id:
        return jsonify({"error": "Semua field diperlukan!"}), 400

    try:
        cur = koneksi.cursor()

        # Cek apakah username atau nomor HP sudah terdaftar
        cur.execute("SELECT 1 FROM user_account WHERE username = %s", (username,))
        if cur.fetchone():
            return jsonify({"error": "Username sudah terdaftar. Silakan pilih username lain."}), 400

        cur.execute("SELECT 1 FROM user_account WHERE nomor_hp = %s", (nomor_hp,))
        if cur.fetchone():
            return jsonify({"error": "Nomor HP sudah terdaftar. Silakan gunakan nomor lain."}), 400

        # Jika belum terdaftar, lanjutkan dengan pendaftaran
        hashed_password = generate_password_hash(password)
        cur.execute("INSERT INTO user_account (username, password_hash, nomor_hp, alamat, roleID) VALUES (%s, %s, %s, %s, %s)",
                    (username, hashed_password, nomor_hp, alamat, role_id))
        koneksi.commit()

        return jsonify({"pesan": "Pengguna berhasil terdaftar!"}), 201

    except UniqueViolation:
        # Tangani error untuk key unik
        return jsonify({"error": "Username atau nomor HP sudah terdaftar. Silakan gunakan data lain."}), 400

    except Exception as e:
        # Tangani error server dengan pesan yang lebih user-friendly
        print(f"Server error: {e}")  # Log detail error di server
        return jsonify({"error": "Terjadi kesalahan pada server."}), 500

    finally:
        cur.close()
        koneksi.close()







# Rute untuk login pengguna
@app.route('/login', methods=['POST'])
def login():
    koneksi = dapatkan_koneksi_db()
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username dan password diperlukan!"}), 400

    try:
        cur = koneksi.cursor()
        # Tambahkan username ke query SELECT
        cur.execute("SELECT id, username, password_hash, roleid FROM user_account WHERE username = %s", (username,))
        user = cur.fetchone()

        if user:
            user_id, username, password_hash, role_id = user
            if check_password_hash(password_hash, password):
                # Tambahkan username pada respons
                return jsonify({"pesan": "Login berhasil!", "user_id": user_id, "username": username, "roleid": role_id}), 200
            else:
                return jsonify({"pesan": "Password tidak valid"}), 401
        else:
            return jsonify({"pesan": "Pengguna tidak ditemukan"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        koneksi.close()




@app.route('/produk', methods=['GET'])
def get_produk_by_category():
    category_id = request.args.get('category_id')
    user_id = request.args.get('user_id')
    
    if not category_id or not user_id:
        return jsonify({"error": "Parameter 'category_id' dan 'user_id' diperlukan"}), 400

    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()

        # Query untuk mengambil produk dengan rata-rata rating
        cur.execute("""
            SELECT p.id, p.name, p.description, p.price, p.category_id, p.image_url, 
                   COALESCE(k.qty_produk, 0) AS qty_in_cart, 
                   COALESCE(AVG(h.ratingproduk), 0) AS average_rating  -- Hitung rata-rata rating
            FROM tbl_produk p
            LEFT JOIN tbl_keranjang k ON p.id = k.produk_id AND k.user_id = %s AND k.statuskeranjang = 'pending'
            LEFT JOIN tbl_history h ON p.id = h.produk_id  -- Join untuk mendapatkan rating
            WHERE p.category_id = %s
            GROUP BY p.id, k.qty_produk
            """, (int(user_id), int(category_id)))

        produk = cur.fetchall()

        produk_list = []
        for row in produk:
            produk_data = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'price': float(row[3]),
                'category_id': row[4],
                'image_url': row[5],
                'qty_in_cart': row[6],
                'average_rating': float(row[7])  # Tampilkan dua angka di belakang koma
            }
            produk_list.append(produk_data)

        return jsonify(produk_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()



@app.route('/cart/update', methods=['POST'])
def update_cart():
    data = request.json
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    qty_produk = data.get('qty_produk')

    if not user_id or not product_id:
        return jsonify({"error": "Parameter 'user_id' dan 'product_id' diperlukan"}), 400

    try:
        conn = dapatkan_koneksi_db()
        cur = conn.cursor()

        if qty_produk == 0:
            # Jika kuantitas 0, hapus produk dari keranjang
            cur.execute("DELETE FROM tbl_keranjang WHERE user_id = %s AND produk_id = %s", (user_id, product_id))
            message = "Produk berhasil dihapus dari keranjang!"
        else:
            # Jika kuantitas lebih dari 0, update kuantitas di keranjang
            cur.execute("UPDATE tbl_keranjang SET qty_produk = %s WHERE user_id = %s AND produk_id = %s", (qty_produk, user_id, product_id))
            message = "Kuantitas produk di keranjang berhasil diupdate!"

        conn.commit()
        return jsonify({"message": message}), 200

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/cart/remove', methods=['DELETE'])
def remove_from_cart():
    data = request.json
    user_id = data.get('user_id')
    product_id = data.get('product_id')

    if not user_id or not product_id:
        return jsonify({"error": "Parameter 'user_id' dan 'product_id' diperlukan"}), 400

    try:
        conn = dapatkan_koneksi_db()
        cur = conn.cursor()

        # Hapus produk dari keranjang berdasarkan user_id dan product_id
        cur.execute("""
            DELETE FROM tbl_keranjang 
            WHERE user_id = %s AND produk_id = %s AND statuskeranjang = 'pending'
        """, (user_id, product_id))

        conn.commit()

        return jsonify({"message": "Produk berhasil dihapus dari keranjang"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    data = request.json
    user_id = data.get('user_id')
    product_id = data.get('produk_id')
    qty_produk = data.get('qty_produk')

    # Log data yang diterima untuk debugging
    print(f"Received user_id: {user_id}, produk_id: {product_id}, qty_produk: {qty_produk}")

    if not user_id or not product_id or qty_produk is None:
        return jsonify({"error": "Parameter 'user_id', 'produk_id', dan 'qty_produk' diperlukan"}), 400

    try:
        conn = dapatkan_koneksi_db()
        cur = conn.cursor()

        # Jika qty_produk adalah 0, hapus produk dari keranjang
        if qty_produk == 0:
            cur.execute("""
                DELETE FROM tbl_keranjang 
                WHERE user_id = %s AND produk_id = %s AND statuskeranjang = 'pending'
            """, (user_id, product_id))
            conn.commit()
            return jsonify({"message": "Produk berhasil dihapus dari keranjang!"}), 200

        # Ambil detail produk (nama dan harga) dari tabel tbl_produk
        cur.execute("SELECT name, price FROM tbl_produk WHERE id = %s", (product_id,))
        product = cur.fetchone()

        if product is None:
            return jsonify({"error": "Produk tidak ditemukan"}), 404

        nama_produk = product[0]  # Ambil nama produk
        harga_produk = product[1]  # Ambil harga produk

        # Cek apakah produk sudah ada di keranjang user dengan status 'pending'
        cur.execute("""
            SELECT * FROM tbl_keranjang 
            WHERE user_id = %s AND produk_id = %s AND statuskeranjang = 'pending'
        """, (user_id, product_id))
        existing_cart_item = cur.fetchone()

        if existing_cart_item:
            # Jika produk sudah ada, update jumlah kuantitasnya
            cur.execute("""
                UPDATE tbl_keranjang 
                SET qty_produk = %s
                WHERE user_id = %s AND produk_id = %s AND statuskeranjang = 'pending'
            """, (qty_produk, user_id, product_id))
            message = "Jumlah produk di keranjang berhasil diubah!"
        else:
            # Jika produk belum ada, tambahkan produk ke keranjang
            cur.execute("""
                INSERT INTO tbl_keranjang (user_id, produk_id, nama_produk, qty_produk, harga_produk, statuskeranjang, added_at) 
                VALUES (%s, %s, %s, %s, %s, 'pending', NOW())
            """, (user_id, product_id, nama_produk, qty_produk, harga_produk))
            message = "Produk berhasil ditambahkan ke keranjang!"

        conn.commit()
        return jsonify({"message": message}), 201 if not existing_cart_item else 200

    except Exception as e:
        # Logging error untuk debugging
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()










@app.route('/get_cart_items', methods=['GET'])
def get_cart_items():
    user_id = request.args.get('user_id')  # Ambil user_id dari query string
    if not user_id:
        return jsonify({"error": "Parameter 'user_id' diperlukan"}), 400

    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT k.produk_id, p.name, k.qty_produk, k.harga_produk, k.qty_produk * k.harga_produk AS totalprodukharga 
            FROM tbl_keranjang k 
            JOIN tbl_produk p ON k.produk_id = p.id
            WHERE k.user_id = %s AND k.statuskeranjang = 'pending'
        """, (int(user_id),))
        cart_items = cur.fetchall()

        # Buat list untuk menyimpan hasil dalam format JSON
        cart_list = []
        for item in cart_items:
            cart_data = {
                'produk_id': item[0],
                'productName': item[1],
                'quantity': item[2],
                'price': float(item[3]),  # Harga satuan produk
                'totalProductPrice': float(item[4])  # Total harga produk (price * quantity)
            }
            cart_list.append(cart_data)

        return jsonify(cart_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()







@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    data = request.get_json()  
    cart_items = data.get('cart_items', [])

    if not cart_items:
        return jsonify({"error": "Cart items are required"}), 400

    # Get recommended products based on cart items
    recommended_products = recommend_products(cart_items)

    # Connect to the PostgreSQL database
    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()

        # Build the response with details from the database
        response_data = []
        for product_name in recommended_products:
       
            cur.execute("""
                SELECT p.id, p.name, p.price, p.image_url, 
                COALESCE(AVG(h.ratingproduk), 0) AS average_rating
                FROM tbl_produk p
                LEFT JOIN tbl_history h ON p.id = h.produk_id
                WHERE p.name = %s
                GROUP BY p.id
            """, (product_name,))
            product = cur.fetchone()
            
            if product:  # If the product is found in the database
                response_data.append({
                    "id": product[0], 
                    "name": product[1],  
                    "price": float(product[2]),  
                    "imageUrl": product[3],
                    "average_rating": float(product[4]) 
                })

        return jsonify({"recommendations": response_data}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()


    
import uuid  # Untuk membuat UUID

@app.route('/checkout', methods=['POST'])
def checkout():
    try:
        data = request.get_json()

        # Ambil user_id dari request body
        user_id = data.get('user_id')
        checkout_items = data.get('checkout_items')

        if not user_id:
            return jsonify({"error": "Parameter 'user_id' diperlukan"}), 400

        logging.debug(f"Data diterima untuk checkout: {checkout_items}")

        conn = dapatkan_koneksi_db()
        cur = conn.cursor()

        total_harga = 0
        total_qty = 0
        transaction_id = str(uuid.uuid4())  # Generate UUID untuk transaction_id

        # Proses setiap item dalam checkout_items
        for item in checkout_items:
            produk_id = item.get('product_id')
            quantity = item.get('quantity')
            price = item.get('price')
            total_harga_item = quantity * price

            total_harga += total_harga_item
            total_qty += quantity

            # Ambil nama produk dari tbl_produk berdasarkan produk_id
            cur.execute("SELECT name FROM tbl_produk WHERE id = %s", (produk_id,))
            product = cur.fetchone()
            if not product:
                logging.error(f"Produk dengan id {produk_id} tidak ditemukan")
                return jsonify({"error": f"Produk dengan id {produk_id} tidak ditemukan"}), 400

            nama_produk = product[0]

            # Masukkan data ke tbl_history menggunakan transaction_id yang sama untuk setiap item
            cur.execute("""
                INSERT INTO tbl_history (transaction_id, user_id, produk_id, nama_produk, qty_produk, harga_produk, total_harga, status_transaksi)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'proses')
            """, (transaction_id, user_id, produk_id, nama_produk, quantity, price, total_harga_item))

        # Simpan total harga dan qty ke dalam tbl_hargatransaksi
        cur.execute("""
            INSERT INTO tbl_hargatransaksi (transaction_id, totalharga, totalqty)
            VALUES (%s, %s, %s)
        """, (transaction_id, total_harga, total_qty))

        # Update status item di tbl_keranjang menjadi 'proses'
        cur.execute("""
            UPDATE tbl_keranjang
            SET statuskeranjang = 'proses'
            WHERE user_id = %s AND statuskeranjang = 'pending'
        """, (user_id,))

        conn.commit()
        logging.debug("Checkout berhasil, item dipindahkan ke history dan transaksi tercatat.")
        return jsonify({"message": "Checkout berhasil, item dipindahkan ke history"}), 200

    except Exception as e:
        logging.error(f"Terjadi error selama checkout: {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'conn' in locals() and conn:
            conn.close()

from decimal import Decimal

# Fungsi untuk mengonversi Decimal ke float
def convert_decimal_to_float(data):
    if isinstance(data, Decimal):
        return float(data)
    return data

@app.route('/api/order/history', methods=['GET'])
def get_order_history():
    user_id = request.args.get('user_id')
    role_id = request.args.get('role_id')

    # Validasi parameter
    if not user_id or not role_id:
        return jsonify({"error": "Parameter 'user_id' dan 'role_id' diperlukan"}), 400

    # Koneksi ke database
    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()

        # Query untuk customer (role_id = 2)
        if int(role_id) == 2:
            cur.execute("""
                SELECT h.transaction_id, u.username, u.alamat, NULL AS nomor_hp, ht.totalqty as total_qty, ht.totalharga as total_harga, 
                    h.status_transaksi, MAX(h.tanggal_transaksi) as tanggal_transaksi, ht.status_pembayaran
                FROM tbl_history h
                JOIN user_account u ON h.user_id = u.id
                JOIN tbl_hargatransaksi ht ON h.transaction_id = ht.transaction_id
                WHERE h.user_id = %s
                GROUP BY h.transaction_id, u.username, u.alamat, h.status_transaksi, ht.totalqty, ht.totalharga, ht.status_pembayaran
                ORDER BY tanggal_transaksi DESC
            """, (user_id,))


        # Query untuk admin (role_id = 1)
        elif int(role_id) == 1:
            cur.execute("""
                SELECT h.transaction_id, u.username, u.alamat, u.nomor_hp, ht.totalqty as total_qty, ht.totalharga as total_harga, 
                       h.status_transaksi, MAX(h.tanggal_transaksi) as tanggal_transaksi, ht.status_pembayaran
                FROM tbl_history h
                JOIN user_account u ON h.user_id = u.id
                JOIN tbl_hargatransaksi ht ON h.transaction_id = ht.transaction_id
                GROUP BY h.transaction_id, u.username, u.alamat, u.nomor_hp, h.status_transaksi, ht.totalqty, ht.totalharga, ht.status_pembayaran
                ORDER BY tanggal_transaksi DESC
            """)

        # Ambil hasil query
        orders = cur.fetchall()
        order_list = []

        for order in orders:
            transaction_id = order[0]

            # Query untuk mengambil produk berdasarkan transaction_id
            cur.execute("""
                SELECT p.name, ph.qty_produk, p.price
                FROM tbl_produk p
                JOIN tbl_history ph ON p.id = ph.produk_id
                WHERE ph.transaction_id = %s
            """, (transaction_id,))
            products = cur.fetchall()

            # Membuat list produk
            product_list = []
            for product in products:
                product_data = {
                    'name': product[0],
                    'quantity': product[1],
                    'price': convert_decimal_to_float(product[2])
                }
                product_list.append(product_data)

            # Membuat data pesanan
            order_data = {
                'transaction_id': order[0],
                'user_name': order[1],
                'alamat': order[2],
                'nomor_hp': order[3] if int(role_id) == 1 else None,  # Tambahkan nomor_hp jika role_id adalah admin
                'total_qty': order[4],
                'total_harga': convert_decimal_to_float(order[5]),
                'status_transaksi': order[6],
                'tanggal_transaksi': order[7],
                'status_pembayaran': order[8],
                'product_list': product_list
            }
            order_list.append(order_data)

        # Return JSON response
        return jsonify(order_list), 200

    except Exception as e:
        # Error handling
        return jsonify({"error": str(e)}), 500

    finally:
        # Tutup koneksi
        cur.close()
        conn.close()







@app.route('/api/order/update_status', methods=['POST'])
def update_order_status():
    data = request.json
    transaction_id = data.get('transaction_id')
    status_pembayaran = data.get('status_pembayaran')
    status_pemesanan = data.get('status_pemesanan')

    # Validasi input
    if not transaction_id or not status_pembayaran or not status_pemesanan:
        return jsonify({"error": "Semua field harus diisi"}), 400

    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()
        
        # Update status_pembayaran di tbl_hargatransaksi
        cur.execute("""
            UPDATE tbl_hargatransaksi
            SET status_pembayaran = %s
            WHERE transaction_id = %s
        """, (status_pembayaran, transaction_id))
        
        # Update status_transaksi (status pemesanan) di tbl_history
        cur.execute("""
            UPDATE tbl_history
            SET status_transaksi = %s
            WHERE transaction_id = %s
        """, (status_pemesanan, transaction_id))

        # Commit perubahan ke database
        conn.commit()

        return jsonify({"message": "Status berhasil diperbarui"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()



        

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

@app.route('/api/order/rating', methods=['GET'])
def get_ratings():
    # Ambil parameter query
    status_transaksi = request.args.get('status_transaksi')
    user_id = request.args.get('user_id')
    role_id = request.args.get('role_id')

    # Validasi input
    if not status_transaksi or not user_id or not role_id:
        return jsonify({"error": "Parameter 'status_transaksi', 'user_id', dan 'role_id' diperlukan"}), 400

    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()

        # Query berdasarkan role_id
        if int(role_id) == 1:  # Admin: semua transaksi
            cur.execute("""
                SELECT h.transaction_id, u.username, u.alamat, ht.totalqty AS total_qty, 
                       CAST(ht.totalharga AS float) AS total_harga, h.status_transaksi, 
                       MAX(h.tanggal_transaksi) AS tanggal_transaksi, ht.status_pembayaran,
                       COALESCE(AVG(ph.ratingproduk), 0) AS average_rating
                FROM tbl_history h
                JOIN user_account u ON h.user_id = u.id
                JOIN tbl_hargatransaksi ht ON h.transaction_id = ht.transaction_id
                LEFT JOIN tbl_history ph ON h.transaction_id = ph.transaction_id
                WHERE h.status_transaksi = %s
                GROUP BY h.transaction_id, u.username, u.alamat, h.status_transaksi, 
                         ht.totalqty, ht.totalharga, ht.status_pembayaran
                ORDER BY tanggal_transaksi DESC
            """, (status_transaksi,))
        elif int(role_id) == 2:  # Customer: hanya transaksi miliknya
            cur.execute("""
                SELECT h.transaction_id, u.username, u.alamat, ht.totalqty AS total_qty, 
                       CAST(ht.totalharga AS float) AS total_harga, h.status_transaksi, 
                       MAX(h.tanggal_transaksi) AS tanggal_transaksi, ht.status_pembayaran,
                       COALESCE(AVG(ph.ratingproduk), 0) AS average_rating
                FROM tbl_history h
                JOIN user_account u ON h.user_id = u.id
                JOIN tbl_hargatransaksi ht ON h.transaction_id = ht.transaction_id
                LEFT JOIN tbl_history ph ON h.transaction_id = ph.transaction_id
                WHERE h.status_transaksi = %s AND h.user_id = %s
                GROUP BY h.transaction_id, u.username, u.alamat, h.status_transaksi, 
                         ht.totalqty, ht.totalharga, ht.status_pembayaran
                ORDER BY tanggal_transaksi DESC
            """, (status_transaksi, user_id))
        else:
            return jsonify({"error": "Role ID tidak valid"}), 403

        orders = cur.fetchall()
        order_list = []

        for order in orders:
            transaction_id = order[0]
            average_rating = float(order[8]) if order[8] is not None else 0.0  # Konversi average_rating ke float

            # Ambil data produk per transaction_id dengan rating dan deskripsi
            cur.execute("""
                SELECT p.id AS produk_id, p.name, ph.qty_produk, CAST(p.price AS float), 
                       COALESCE(ph.ratingproduk, 0) AS ratingproduk, COALESCE(ph.deskripsi_rating, '') AS deskripsi_rating
                FROM tbl_produk p
                JOIN tbl_history ph ON p.id = ph.produk_id
                WHERE ph.transaction_id = %s
            """, (transaction_id,))
            products = cur.fetchall()

            product_list = [{
                'produk_id': prod[0],
                'name': prod[1],
                'quantity': prod[2],
                'price': float(prod[3]),  # Pastikan harga dikonversi ke float
                'ratingproduk': prod[4],
                'deskripsi_rating': prod[5]
            } for prod in products]

            order_data = {
                'transaction_id': transaction_id,
                'user_name': order[1],
                'alamat': order[2],
                'total_qty': order[3],
                'total_harga': float(order[4]),  # Pastikan total_harga dikonversi ke float
                'status_transaksi': order[5],
                'tanggal_transaksi': order[6],
                'status_pembayaran': order[7],
                'average_rating': round(average_rating, 2),
                'product_list': product_list
            }
            order_list.append(order_data)

        return jsonify(order_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()



@app.route('/api/product/average_rating', methods=['GET'])
def get_product_average_ratings():
    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()
        
        # Query for average rating with filter for values above 0
        cur.execute("""
            SELECT produk_id, AVG(CASE WHEN ratingproduk > 0 THEN ratingproduk ELSE NULL END) AS average_rating
            FROM tbl_history
            GROUP BY produk_id
            HAVING AVG(CASE WHEN ratingproduk > 0 THEN ratingproduk ELSE NULL END) > 0
        """)
        
        results = cur.fetchall()
        
        # Convert results to JSON-serializable format
        ratings_data = [
            {
                "produk_id": row[0], 
                "average_rating": round(float(row[1]), 2) if row[1] is not None else None
            }
            for row in results
        ]
        
        return jsonify(ratings_data), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        cur.close()
        conn.close()


@app.route('/api/order/rating', methods=['POST'])
def add_rating_per_product():
    data = request.get_json()
    transaction_id = data.get('transaction_id')
    products = data.get('products')  # Expecting a list of product ratings

    if not transaction_id or not products:
        return jsonify({"error": "Field 'transaction_id' and 'products' are required"}), 400

    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()

        for product in products:
            produk_id = product.get('produk_id')
            deskripsi_rating = product.get('deskripsi_rating')
            bintang_rating = product.get('ratingproduk')

            # Validate each product rating entry
            if not produk_id or deskripsi_rating is None or bintang_rating is None:
                return jsonify({"error": "Each product entry must have 'produk_id', 'deskripsi_rating', and 'ratingproduk'"}), 400

            # Update rating and description for each product in tbl_history
            cur.execute("""
                UPDATE tbl_history
                SET deskripsi_rating = %s, ratingproduk = %s
                WHERE transaction_id = %s AND produk_id = %s
            """, (deskripsi_rating, bintang_rating, transaction_id, produk_id))

        conn.commit()
        return jsonify({"success": True}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()











@app.route('/api/produk/manajemen', methods=['GET'])
def get_produk_manajemen():
    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, description, price, category_id, image_url FROM tbl_produk")
        rows = cur.fetchall()

        produk_list = []
        for row in rows:
            produk_data = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'price': float(row[3]),  # Konversi Decimal ke float
                'category_id': row[4],
                'image_url': row[5]
            }
            produk_list.append(produk_data)

        return jsonify(produk_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/api/produk/update/<int:product_id>', methods=['PUT'])
def update_produk(product_id):
    data = request.get_json()
    
    # Ambil produk yang ada berdasarkan product_id
    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name, price, description, image_url, category_id FROM tbl_produk WHERE id = %s", (product_id,))
        product = cur.fetchone()
        
        if product is None:
            return jsonify({"error": "Product not found"}), 404
        
        # Ambil nilai sebelumnya dari produk
        current_name = product[0]
        current_price = product[1]
        current_description = product[2]
        current_image_url = product[3]
        current_category_id = product[4]
        
        # Periksa apakah ada nilai baru untuk setiap kolom, jika tidak, gunakan nilai lama
        name = data.get('name', current_name)
        price = data.get('price', current_price)
        description = data.get('description', current_description)
        image_url = data.get('image_url', current_image_url)  # Jika gambar tidak diubah, tetap pakai URL lama
        category_id = data.get('category_id', current_category_id)  # Tambahkan pembaruan category_id
        
        # Update produk
        cur.execute("""
            UPDATE tbl_produk 
            SET name = %s, price = %s, description = %s, image_url = %s, category_id = %s
            WHERE id = %s
        """, (name, price, description, image_url, category_id, product_id))
        conn.commit()
        
        return jsonify({"success": True, "message": "Product updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()



@app.route('/api/produk/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # Upload ke Cloudinary
        upload_result = cloudinary.uploader.upload(file)
        image_url = upload_result.get('secure_url')  # Dapatkan URL gambar dari Cloudinary

        # Return the image URL to the client
        return jsonify({"image_url": image_url}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/produk', methods=['POST'])
def add_produk():
    data = request.get_json()

    # Ambil data produk dari request body
    name = data.get('name')
    price = data.get('price')
    description = data.get('description')
    image_url = data.get('image_url')  # URL gambar (bisa kosong jika belum ada)
    category_id = data.get('category_id')  # Tambahkan category_id untuk kategori produk

    # Validasi sederhana
    if not name or not price or not category_id:
        return jsonify({"error": "Missing required fields"}), 400

    # Insert produk baru ke dalam database
    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tbl_produk (name, price, description, image_url, category_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, price, description, image_url, category_id))
        conn.commit()
        return jsonify({"success": True, "message": "Product added successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/api/produk/delete/<int:product_id>', methods=['DELETE'])
def delete_produk(product_id):
    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()

        # Cek apakah produk ada di database
        cur.execute("SELECT id FROM tbl_produk WHERE id = %s", (product_id,))
        product = cur.fetchone()

        if product is None:
            return jsonify({"error": "Product not found"}), 404

        # Hapus produk berdasarkan product_id
        cur.execute("DELETE FROM tbl_produk WHERE id = %s", (product_id,))
        conn.commit()

        return jsonify({"success": True, "message": "Product deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()




@app.route('/api/user/profile/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()
        # Ganti `email` dengan `nomor_hp` pada query
        cur.execute("SELECT username, nomor_hp, alamat FROM user_account WHERE id = %s", (user_id,))
        user = cur.fetchone()

        if user is None:
            return jsonify({"error": "User not found"}), 404

        # Mengembalikan data user dengan nomor HP
        user_data = {
            "username": user[0],
            "nomor_hp": user[1],  # Ganti `email` dengan `nomor_hp`
            "alamat": user[2]
        }
        return jsonify(user_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/api/user/profile/<int:user_id>', methods=['PUT'])
def update_user_profile(user_id):
    data = request.get_json()
    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()

        # Dapatkan input baru
        username = data['username']
        nomor_hp = data['nomor_hp']  # Ganti email dengan nomor_hp
        alamat = data['alamat']
        password = data.get('password', None)

        # Lakukan hashing baru untuk password jika diubah
        if password:
            hashed_password = generate_password_hash(password)
            cur.execute("""
                UPDATE user_account 
                SET username = %s, nomor_hp = %s, alamat = %s, password_hash = %s 
                WHERE id = %s
            """, (username, nomor_hp, alamat, hashed_password, user_id))
        else:
            # Jika password tidak diubah, hanya update username, nomor_hp, dan alamat
            cur.execute("""
                UPDATE user_account 
                SET username = %s, nomor_hp = %s, alamat = %s
                WHERE id = %s
            """, (username, nomor_hp, alamat, user_id))

        conn.commit()

        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()



@app.route('/api/product/<int:product_id>/increment_views', methods=['POST'])
def increment_product_views(product_id):
    connection = dapatkan_koneksi_db()
    try:
        cur = connection.cursor()
        # Update the product's view count
        cur.execute("UPDATE tbl_produk SET views = views + 1 WHERE id = %s", (product_id,))
        connection.commit()
        return jsonify({"message": "Product views incremented successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        connection.close()


@app.route('/api/products/most_viewed', methods=['GET'])
def get_most_viewed_products():
    connection = dapatkan_koneksi_db()
    try:
        cur = connection.cursor()
        
        # Query to get the top 10 most viewed products along with their average ratings
        cur.execute("""
            SELECT p.id, p.name, p.description, p.image_url, p.price, p.views, p.category_id, 
            COALESCE(AVG(h.ratingproduk), 0) as average_rating
            FROM tbl_produk p
            LEFT JOIN tbl_history h ON p.id = h.produk_id
            GROUP BY p.id
            ORDER BY p.views DESC
            LIMIT 10
        """)
        
        products = cur.fetchall()

        product_list = []
        for product in products:
            product_dict = {
                "id": product[0],
                "name": product[1],
                "description": product[2],
                "image_url": product[3],
                "price": float(product[4]),  # Convert price from Decimal to float
                "views": product[5],
                "category_id": product[6],
                "average_rating": float(product[7])  # Include average rating in response
            }
            product_list.append(product_dict)

        return jsonify(product_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        connection.close()

@app.route('/api/sales_report', methods=['GET'])
def get_sales_report():
    # Ambil parameter tahun dan bulan dari query
    tahun = request.args.get('tahun')
    bulan = request.args.get('bulan')

    # Validasi input tahun dan bulan
    if not tahun or not bulan:
        return jsonify({"error": "Parameter 'tahun' dan 'bulan' diperlukan"}), 400

    # Koneksi ke database
    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()

        # Query untuk menghitung total pesanan, pendapatan, dan produk terjual
        cur.execute("""
            SELECT 
                COUNT(DISTINCT ht.transaction_id) AS total_pesanan,
                COALESCE(SUM(h.qty_produk * h.total_harga / h.qty_produk), 0) AS total_pendapatan,
                COALESCE(SUM(h.qty_produk), 0) AS total_produk_terjual
            FROM 
                tbl_history h
            JOIN 
                tbl_hargatransaksi ht ON h.transaction_id = ht.transaction_id
            WHERE 
                h.status_transaksi = 'Pesanan Telah Sampai' 
                AND ht.status_pembayaran = 'Sudah dibayar'
                AND EXTRACT(YEAR FROM h.tanggal_transaksi) = %s
                AND EXTRACT(MONTH FROM h.tanggal_transaksi) = %s
        """, (tahun, bulan))

        result = cur.fetchone()
        total_pesanan = result[0] if result and result[0] else 0
        total_pendapatan = float(result[1]) if result and result[1] else 0.0
        total_produk_terjual = result[2] if result and result[2] else 0

        # Ambil detail transaksi per transaction_id termasuk category_id
        cur.execute("""
            SELECT 
                h.transaction_id, 
                h.tanggal_transaksi, 
                h.nama_produk, 
                h.qty_produk, 
                h.total_harga, 
                p.category_id
            FROM 
                tbl_history h
            JOIN 
                tbl_hargatransaksi ht ON h.transaction_id = ht.transaction_id
            JOIN 
                tbl_produk p ON h.produk_id = p.id
            WHERE 
                h.status_transaksi = 'Pesanan Telah Sampai' 
                AND ht.status_pembayaran = 'Sudah dibayar'
                AND EXTRACT(YEAR FROM h.tanggal_transaksi) = %s
                AND EXTRACT(MONTH FROM h.tanggal_transaksi) = %s
            ORDER BY h.tanggal_transaksi ASC
        """, (tahun, bulan))
        transaction_details = cur.fetchall()

        # Group transaction details by transaction_id
        grouped_transactions = {}
        for detail in transaction_details:
            transaction_id = detail[0]
            tanggal_transaksi = detail[1].strftime('%d')  # Format tanggal menjadi "dd"
            product_info = {
                "nama_produk": detail[2],
                "qty_produk": detail[3],
                "total_harga": float(detail[4]),
                "category_id": detail[5]
            }
            if transaction_id not in grouped_transactions:
                grouped_transactions[transaction_id] = {
                    "tanggal_transaksi": tanggal_transaksi,
                    "products": []
                }
            grouped_transactions[transaction_id]["products"].append(product_info)

        transactions_list = [
            {
                "transaction_id": transaction_id,
                "tanggal_transaksi": details["tanggal_transaksi"],
                "products": details["products"]
            }
            for transaction_id, details in grouped_transactions.items()
        ]

        # Format response
        response = {
            "tahun": tahun,
            "bulan": bulan,
            "total_pesanan": total_pesanan,
            "total_pendapatan": total_pendapatan,
            "total_produk_terjual": total_produk_terjual,
            "transaction_details": transactions_list
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()






@app.route('/api/product_sales_report', methods=['GET'])
def get_product_sales_report():
    # Ambil parameter tahun dan bulan dari query
    tahun = request.args.get('tahun')
    bulan = request.args.get('bulan')

    # Validasi input tahun dan bulan
    if not tahun or not bulan:
        return jsonify({"error": "Parameter 'tahun' dan 'bulan' diperlukan"}), 400

    # Koneksi ke database
    conn = dapatkan_koneksi_db()
    try:
        cur = conn.cursor()

        # Query untuk menghitung jumlah produk yang telah dibeli pada bulan tersebut
        cur.execute("""
            SELECT 
                h.nama_produk, 
                SUM(h.qty_produk) AS total_qty
            FROM 
                tbl_history h
            JOIN 
                tbl_hargatransaksi ht ON h.transaction_id = ht.transaction_id
            WHERE 
                h.status_transaksi = 'Pesanan Telah Sampai' 
                AND ht.status_pembayaran = 'Sudah dibayar'
                AND EXTRACT(YEAR FROM h.tanggal_transaksi) = %s
                AND EXTRACT(MONTH FROM h.tanggal_transaksi) = %s
            GROUP BY 
                h.nama_produk
            ORDER BY 
                total_qty DESC
        """, (tahun, bulan))

        result = cur.fetchall()

        if result:
            # Bagi data menjadi grup Top 1-5, Top 6-10, dan Top 11-15
            top_5 = [{"nama_produk": row[0], "total_qty": row[1]} for row in result[:5]]
            top_6_to_10 = [{"nama_produk": row[0], "total_qty": row[1]} for row in result[5:10]]
            top_11_to_15 = [{"nama_produk": row[0], "total_qty": row[1]} for row in result[10:15]]

            # Format hasil ke dalam dictionary untuk JSON response
            response = {
                "Top 1-5": top_5,
                "Top 6-10": top_6_to_10,
                "Top 11-15": top_11_to_15
            }
            return jsonify(response), 200
        else:
            return jsonify({"message": "Tidak ada data produk untuk bulan dan tahun yang dipilih"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()








from mlxtend.frequent_patterns import apriori, association_rules

# Fungsi untuk menjalankan Apriori dan menghasilkan aturan asosiasi
def apriori_rules(basket, min_support=0.05, min_threshold=1):
    frequent_itemsets = apriori(basket, min_support=min_support, use_colnames=True)
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_threshold)
    return rules

# Jalankan apriori saat aplikasi dimulai
rules = apriori_rules(basket)

# Fungsi untuk mendapatkan rekomendasi berdasarkan item di keranjang
def recommend_products(cart_items):
    recommendations = set()

    # Filter aturan asosiasi berdasarkan item yang ada di keranjang
    for item in cart_items:
        filtered_rules = rules[rules['antecedents'].apply(lambda x: item in x)]
        for _, rule in filtered_rules.iterrows():
            recommendations.update(rule['consequents'])

    return list(recommendations)

    
  





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    app.run(debug=True)
