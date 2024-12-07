from werkzeug.security import generate_password_hash

hashed_password = generate_password_hash('123')  # Ganti '123' dengan password yang kamu inginkan
print(hashed_password)
