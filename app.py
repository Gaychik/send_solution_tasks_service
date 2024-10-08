from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import shutil
import os
import random
import string

app = FastAPI()

# Подключение шаблонов
templates = Jinja2Templates(directory="templates")

# База данных для хранения групп и студентов
groups_db = {}
students_db = {}

# Телеграм токен бота
TELEGRAM_TOKEN = "ВАШ_ТЕЛЕГРАМ_ТОКЕН"

# Маршрут для отображения страницы преподавателя
@app.get("/teacher", response_class=HTMLResponse)
async def get_teacher_form(request: Request):
    return templates.TemplateResponse("teacher_form.html", {"request": request})

# Маршрут для отображения страницы студента
@app.get("/student", response_class=HTMLResponse)
async def get_student_form(request: Request):
    return templates.TemplateResponse("student_form.html", {"request": request})

# Генерация случайного пароля
def generate_random_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Генерация логина
def generate_login(name, surname):
    return f"{name.lower()}.{surname.lower()}"

# Маршрут для загрузки списка студентов преподавателем
@app.post("/upload_students")
async def upload_students(group: str = Form(...), chat_id: str = Form(...), student_list: UploadFile = File(...)):
    students = student_list.file.read().decode('utf-8').splitlines()
    
    if group in groups_db:
        raise HTTPException(status_code=400, detail="Группа уже существует.")
    
    groups_db[group] = {"chat_id": chat_id, "students": {}}

    for student in students:
        name, surname = student.split('-')
        password = generate_random_password()
        login = generate_login(name, surname)
        
        full_name = f"{name} {surname}"
        students_db[full_name] = {"login": login, "password": password, "group": group}
        groups_db[group]["students"][full_name] = {"login": login, "password": password}
    
    return {"message": "Список студентов загружен и пароли сгенерированы."}

# Маршрут для входа студента
@app.post("/login")
async def login(request: Request, name: str = Form(...), surname: str = Form(...), password: str = Form(...)):
    full_name = f"{name} {surname}"
    if full_name in students_db and students_db[full_name]["password"] == password:
        return templates.TemplateResponse("student_form.html", {"request": request, "name": name, "surname": surname, "success": True})
    else:
        return {"success": False, "message": "Неправильное имя, фамилия или пароль."}

# Маршрут для отправки сообщения
@app.post("/send_message")
async def send_message(
    message: str = Form(...), file: UploadFile = None, 
    name: str = Form(...), surname: str = Form(...)):

    full_name = f"{name} {surname}"

    if full_name not in students_db:
        raise HTTPException(status_code=400, detail="Студент не зарегистрирован.")

    group = students_db[full_name]["group"]
    chat_id = groups_db[group]["chat_id"]

    telegram_message = f"Сообщение от студента: {full_name} из группы {group}\n\n{message}"
    send_to_telegram(telegram_message, chat_id)

    if file:
        file_location = f"files/{file.filename}"
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)

        send_file_to_telegram(file_location, chat_id)
        os.remove(file_location)

    return {"success": True}

# Функция отправки текста в Телеграм
def send_to_telegram(text: str, chat_id: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, data=payload)

# Функция отправки файла в Телеграм
def send_file_to_telegram(file_path: str, chat_id: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    files = {'document': open(file_path, 'rb')}
    data = {"chat_id": chat_id}
    requests.post(url, files=files, data=data)
