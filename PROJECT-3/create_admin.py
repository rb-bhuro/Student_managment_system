from models import User
from utils import newPassword

User.create(
    name='Admin User',
    email='admin@example.com',
    roll_no='ADMIN001',
    password=newPassword('adminpassword'),
    role='admin'
)
print("Admin user created!")
