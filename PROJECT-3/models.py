from peewee import *
import datetime

db = SqliteDatabase('result_managment.db')

class BaseModel(Model):
    class Meta :
        database = db

class User(BaseModel):
    name = CharField()
    email = CharField(unique=True)
    roll_no = CharField(unique=True)
    image = CharField(null=True)
    password = CharField()
    role = CharField(default='student')

class Subject(BaseModel):
    name = CharField()
    sub_code = CharField(unique=True)

class Result(BaseModel):
    student = ForeignKeyField(User,backref="results")
    declaration_date = DateField(default=datetime.date.today)

class ResultItem(BaseModel):
    result = ForeignKeyField(Result, backref='items')
    subject = ForeignKeyField(Subject)
    marks_obtained = IntegerField()
    total_marks = IntegerField()

if __name__ == "__main__":
    db.connect()
    db.create_tables([User, Subject, Result, ResultItem])
    print("Database tables created!")
    db.close()
