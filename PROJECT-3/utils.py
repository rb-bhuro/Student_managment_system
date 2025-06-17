from werkzeug.security import generate_password_hash , check_password_hash
import uuid
import os

def newPassword(password):
    return generate_password_hash(password)

def verifyPassword(stored_password , provided_password):
    return check_password_hash(stored_password , provided_password)

def save_image(file_storage , upload_folder):
    ext = os.path.splitext(file_storage.filename)[1]   
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(upload_folder , filename )
    file_storage.save(filepath)
    return filename
