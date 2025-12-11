from fastapi import FastAPI, Request, Depends, UploadFile, status, Form, File
from starlette.responses import JSONResponse
from db_configration.db_connection import get_db, Base, engine
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from db_functions.db_function import (get_one_db_data, add_data_in_db, get_all_db_data_with, get_all_db_data,
                                      save_image, delete_db_data, get_one_db_data_and_with, get_booking_events_data)
from user_auth.auth_token import create_token
from user_auth.email_and_pass_verification import email_checker
from user_auth.password_hashing import Hash
from sqlalchemy.orm import Session
from models import tour_models
from pathlib import Path
from typing import List, Optional
from collections import defaultdict
import datetime
import uvicorn
import json

app = FastAPI()
Base.metadata.create_all(engine)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# =========admin register and login===========
@app.get("/logout/")
def logout(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        is_admin = db.query(tour_models.Admin).filter(tour_models.Admin.user_token == is_token).first()
        is_user = db.query(tour_models.Agents).filter(tour_models.Agents.user_token == is_token).first()

        if is_admin:
            is_admin.user_token = ""
            is_admin.user_status = False
            db.commit()
            db.refresh(is_admin)

        if is_user:
            is_user.user_token = ""
            db.commit()
            db.refresh(is_user)

        response = RedirectResponse(url=app.url_path_for("login_api"), status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie('token')
        return response
    else:
        return RedirectResponse(url=app.url_path_for("login_api"), status_code=status.HTTP_303_SEE_OTHER)

@app.get('/register/', status_code=status.HTTP_200_OK)
def register_api(request: Request):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("home_api"))

    message = ''
    return templates.TemplateResponse("admin_register.html", {"request": request, "error": message})

@app.post('/register/', status_code=status.HTTP_200_OK)
def register_api(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...),
                 confirm_password: str = Form(...), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("home_api"))

    if email_checker(email):
        user = get_one_db_data(db, tour_models.Admin, tour_models.Admin.email, email)
        if user:
            message = 'User already exist'
            return templates.TemplateResponse("admin_register.html", {"request": request, "error": message})
        else:
            if password != confirm_password:
                message = 'Password is not matched'
                return templates.TemplateResponse("admin_register.html", {"request": request, "error": message})
            else:
                message = 'User Created Successfully'
                current_time = datetime.datetime.now()
                new_user = tour_models.Admin(name=name, email=email, password=password, user_token='',
                                             created_at=current_time, is_admin=True, user_status=False)
                add_data_in_db(db, new_user)
                return templates.TemplateResponse("admin_login.html", {"request": request, "success": message})

    return RedirectResponse(url=app.url_path_for('register_api'))

@app.get('/admin_login/', status_code=status.HTTP_200_OK)
def admin_login_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        is_admin = db.query(tour_models.Admin).filter(tour_models.Admin.user_token == is_token).first()
        if is_admin:
            return RedirectResponse(url=app.url_path_for("home_api"), status_code=status.HTTP_303_SEE_OTHER)

    admin_exist = db.query(tour_models.Admin).filter(tour_models.Admin.email == 'admin123@gmail.com').first()
    if not admin_exist:
        new_admin = tour_models.Admin(
            name="Alpha Excursion team", email="admin123@gmail.com", password="admin123",
            user_token="", created_at=datetime.datetime.now(), is_admin=True, user_status=False)
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post('/admin_login/', status_code=status.HTTP_200_OK)
def admin_login_api(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("home_api"))

    is_admin = db.query(tour_models.Admin).filter(tour_models.Admin.email == email).first()
    error = "User not exits!"
    if is_admin:
        if email_checker(email):
            if password == is_admin.password:
                is_admin.user_token = create_token()
                is_admin.user_status = True
                db.commit()

                updated_token = db.query(tour_models.Admin).filter(tour_models.Admin.email == email).first()
                response = RedirectResponse(url=app.url_path_for("home_api"))
                response.set_cookie(key="token", value=updated_token.user_token)

                return response

            error = "Invalid credentials!"
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": error})

# ========agent login apis=========
@app.get('/', status_code=status.HTTP_200_OK)
def login_api(request: Request):
    is_token = request.cookies.get('token')
    if not is_token:
        return templates.TemplateResponse("tour_login.html", {"request": request})

    return RedirectResponse(url=app.url_path_for("home_api"), status_code=status.HTTP_303_SEE_OTHER)

@app.post('/', status_code=status.HTTP_200_OK)
def login_api(request: Request, user_name: str = Form(...), email: str = Form(...), password: str = Form(...),
              db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("home_api"))

    is_agent = get_one_db_data_and_with(db, tour_models.Agents, tour_models.Agents.email, tour_models.Agents.user_name,
                                        email, user_name)
    error = "User not exits/allowed!"
    if is_agent and is_agent.user_status:
        if email_checker(email):
            if password:
                is_agent.user_token = create_token()
                db.commit()

                updated_token = get_one_db_data(db, tour_models.Agents, tour_models.Agents.email, email)
                response = RedirectResponse(url=app.url_path_for("home_api"))
                response.set_cookie(key="token", value=updated_token.user_token)

                return response

            error = "Invalid credentials!"
    return templates.TemplateResponse("tour_login.html", {"request": request, "error": error})

# ========home apis=========
@app.get('/home/', status_code=status.HTTP_200_OK)
def home_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    home_images = db.query(tour_models.HomeImages).order_by(tour_models.HomeImages.id.desc()).first()
    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        all_booking_data = get_all_db_data(db, tour_models.Bookings)
        for booking in all_booking_data:
            if isinstance(booking.booking_image, str):
                try:
                    booking.booking_image = json.loads(booking.booking_image)  # Convert to list
                except json.JSONDecodeError:
                    booking.booking_image = [booking.booking_image]

            booking.check_in_date = booking.check_in_date.date()
            booking.check_out_date = booking.check_out_date.date()
        return templates.TemplateResponse("base.html", {"request": request, "admin_data": is_admin,
                                                        "current_date": datetime.date.today(),
                                                        "home_images": home_images,
                                                        "all_booking_data": all_booking_data})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        all_booking_data = get_all_db_data_with(db, tour_models.Bookings, tour_models.Bookings.agent_id, is_agent.id)
        for booking in all_booking_data:
            if isinstance(booking.booking_image, str):
                try:
                    booking.booking_image = json.loads(booking.booking_image)  # Convert to list
                except json.JSONDecodeError:
                    booking.booking_image = [booking.booking_image]

            booking.check_in_date = booking.check_in_date.date()
            booking.check_out_date = booking.check_out_date.date()
        return templates.TemplateResponse("base.html", {"request": request, "admin_data": is_agent, "is_agent": True,
                                                        "current_date": datetime.date.today(),
                                                        "home_images": home_images,
                                                        "all_booking_data": all_booking_data})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/home/', status_code=status.HTTP_200_OK)
def home_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    home_images = db.query(tour_models.HomeImages).order_by(tour_models.HomeImages.id.desc()).first()
    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        all_booking_data = get_all_db_data(db, tour_models.Bookings)
        for booking in all_booking_data:
            # Convert JSON string to a list if it's stored as a string
            if isinstance(booking.booking_image, str):
                try:
                    booking.booking_image = json.loads(booking.booking_image)  # Convert to list
                except json.JSONDecodeError:
                    booking.booking_image = [booking.booking_image]

            booking.check_in_date = booking.check_in_date.date()
            booking.check_out_date = booking.check_out_date.date()
        return templates.TemplateResponse("base.html", {"request": request, "admin_data": is_admin,
                                                        "current_date": datetime.date.today(),
                                                        "home_images": home_images,
                                                        "all_booking_data": all_booking_data})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        all_booking_data = get_all_db_data_with(db, tour_models.Bookings, tour_models.Bookings.agent_id, is_agent.id)
        for booking in all_booking_data:
            # Convert JSON string to a list if it's stored as a string
            if isinstance(booking.booking_image, str):
                try:
                    booking.booking_image = json.loads(booking.booking_image)  # Convert to list
                except json.JSONDecodeError:
                    booking.booking_image = [booking.booking_image]

            booking.check_in_date = booking.check_in_date.date()
            booking.check_out_date = booking.check_out_date.date()
        return templates.TemplateResponse("base.html", {"request": request, "admin_data": is_agent, "is_agent": True,
                                                        "current_date": datetime.date.today(),
                                                        "home_images": home_images,
                                                        "all_booking_data": all_booking_data})

    return RedirectResponse(url=app.url_path_for('logout'))

# ========users apis=========
@app.get('/users/', status_code=status.HTTP_200_OK)
def users_api(request: Request, db: Session = Depends(get_db), search: str = None):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        if search:
            all_users = get_all_db_data_with(db, tour_models.Agents, tour_models.Agents.is_admin, False,
                                             agency_name=search)
        else:
            # Fetch all users if no search query
            all_users = get_all_db_data_with(db, tour_models.Agents, tour_models.Agents.is_admin, False)

        return templates.TemplateResponse("users.html", {"request": request, "admin_data": is_admin,
                                                         "all_users": all_users})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        return templates.TemplateResponse("users.html", {"request": request, "admin_data": is_agent, "is_agent": True})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/users/', status_code=status.HTTP_200_OK)
def users_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        all_users = get_all_db_data_with(db, tour_models.Agents, tour_models.Agents.is_admin, False)
        return templates.TemplateResponse("users.html", {"request": request, "admin_data": is_admin,
                                                         "all_users": all_users})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        return templates.TemplateResponse("users.html", {"request": request, "admin_data": is_agent, "is_agent": True,})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/add_user/', status_code=status.HTTP_200_OK)
def add_user_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    if is_admin:
        return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/add_user/', status_code=status.HTTP_200_OK)
def add_user_api(request: Request, agency_name: str = Form(...), address: str = Form(...), website: str = Form(...),
                 country: str = Form(...), city: str = Form(...), zip_code: int = Form(...),
                 agent_name: str = Form(...), user_name: str = Form(...), mobile_number: str = Form(...),
                 email: str = Form(...), confirm_email: str = Form(...), password: str = Form(...),
                 confirm_password: str = Form(...), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    if is_admin:
        if password != confirm_password:
            return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin,
                                                                "error": "Passwords do not match"})

        user_exist = get_one_db_data(db, tour_models.Agents, tour_models.Agents.email, email)
        if user_exist:
            return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin,
                                                                "error": "User already exists"})

        try:
            created_time = datetime.datetime.now()
            user_data = tour_models.Agents(agency_name=agency_name, address=address, website=website, country=country,
                                           city=city, zip_code=str(zip_code), name=agent_name, email=email,
                                           mobile_number=mobile_number, password=password, user_name=user_name,
                                           created_at=created_time, admin_id=is_admin.id)
            db.add(user_data)
            db.commit()
            db.refresh(user_data)

            return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin,
                                                                "success": "User added successfully"})
        except Exception as e:
            db.rollback()
            return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin,
                                                                "error": f"Something went wrong: {str(e)}"})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/change_status/{data_id}/', status_code=status.HTTP_200_OK)
def change_status_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        user_data = get_one_db_data(db, tour_models.Agents, tour_models.Agents.id, data_id)
        if user_data:
            if user_data.user_status:
                user_data.user_status = False
            else:
                user_data.user_status = True
            db.commit()
            db.refresh(user_data)
        return RedirectResponse(url=app.url_path_for("users_api"))

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        return RedirectResponse(url=app.url_path_for("users_api"))

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/update_user/{data_id}/', status_code=status.HTTP_200_OK)
def update_user_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    if is_admin:
        user_data = get_one_db_data(db, tour_models.Agents, tour_models.Agents.id, data_id)
        return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin,
                                                            "user_data": user_data})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/update_user/{data_id}/', status_code=status.HTTP_200_OK)
def update_user_api(request: Request, data_id: int, agency_name: str = Form(...), address: str = Form(...),
                    website: str = Form(...), country: str = Form(...), city: str = Form(...),
                    zip_code: int = Form(...), agent_name: str = Form(...), user_name: str = Form(...),
                    mobile_number: str = Form(...), email: str = Form(...), confirm_email: str = Form(...),
                    password: str = Form(None), confirm_password: str = Form(None), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    user_data = get_one_db_data(db, tour_models.Agents, tour_models.Agents.id, data_id)
    if not user_data:
        return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin,
                                                            "error": "User not found."})

    if email != user_data.email:
        user_exist = get_one_db_data(db, tour_models.Agents, tour_models.Agents.email, email)
        if user_exist:
            return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin,
                                                                "user_data": user_data,
                                                                "error": "User with this email already exists."})

    if password and password != confirm_password:
        return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin,
                                                            "user_data": user_data, "error": "Passwords do not match."})

    try:
        user_data.agency_name = agency_name
        user_data.address = address
        user_data.website = website
        user_data.country = country
        user_data.city = city
        user_data.zip_code = str(zip_code)
        user_data.name = agent_name
        user_data.user_name = user_name
        user_data.mobile_number = mobile_number
        user_data.email = email
        user_data.password = password

        db.commit()
        db.refresh(user_data)
        return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin,
                                                            "user_data": user_data,
                                                            "success": "User updated successfully."})
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin,
                                                            "user_data": user_data,
                                                            "error": f"Something went wrong: {str(e)}"})

@app.get('/delete_user/{data_id}/', status_code=status.HTTP_200_OK)
def delete_user_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    if is_admin:
        delete_db_data(db, tour_models.Agents, tour_models.Agents.id, data_id)
        return RedirectResponse(url=app.url_path_for("users_api"))

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/update_profile/', status_code=status.HTTP_200_OK)
def update_profile_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("update_profile.html", {"request": request, "admin_data": is_admin})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        return templates.TemplateResponse("update_profile.html", {"request": request, "admin_data": is_agent,
                                                                  "is_agent": True,})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/update_profile/', status_code=status.HTTP_200_OK)
def update_profile_api(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...),
                       db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        try:
            is_admin.name = name
            is_admin.email = email
            if password:
                is_admin.password = password

            db.commit()
            db.refresh(is_admin)

            return templates.TemplateResponse("update_profile.html", {"request": request, "admin_data": is_admin,
                                                                      "is_agent": True,
                                                                      "success": "Profile updated successfully."})
        except Exception as e:
            db.rollback()
            return templates.TemplateResponse("update_profile.html", {"request": request, "admin_data": is_admin,
                                                                      "is_agent": True,
                                                                      "error": f"Something went wrong: {str(e)}"})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        try:
            is_agent.name = name
            is_agent.email = email
            if password:
                is_agent.password = password

            db.commit()
            db.refresh(is_agent)

            return templates.TemplateResponse("update_profile.html", {"request": request, "admin_data": is_agent,
                                                                      "is_agent": True,
                                                                      "success": "Profile updated successfully."})
        except Exception as e:
            db.rollback()
            return templates.TemplateResponse("update_profile.html", {"request": request, "admin_data": is_agent,
                                                                      "is_agent": True,
                                                                      "error": f"Something went wrong: {str(e)}"})

    return RedirectResponse(url=app.url_path_for('logout'))

# ========booking apis=========
@app.get('/booking/', status_code=status.HTTP_200_OK)
def booking_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        all_booking_data = get_all_db_data(db, tour_models.Bookings)
        for booking in all_booking_data:
            # Convert JSON string to a list if it's stored as a string
            if isinstance(booking.booking_image, str):
                try:
                    booking.booking_image = json.loads(booking.booking_image)  # Convert to list
                except json.JSONDecodeError:
                    booking.booking_image = [booking.booking_image]

            booking.check_in_date = booking.check_in_date.date()
            booking.check_out_date = booking.check_out_date.date()
        return templates.TemplateResponse("booking.html", {"request": request, "admin_data": is_admin,
                                                           "current_date": datetime.date.today(),
                                                           "all_booking_data": all_booking_data})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        all_booking_data = get_all_db_data_with(db, tour_models.Bookings, tour_models.Bookings.agent_id, is_agent.id)
        for booking in all_booking_data:
            # Convert JSON string to a list if it's stored as a string
            if isinstance(booking.booking_image, str):
                try:
                    booking.booking_image = json.loads(booking.booking_image)  # Convert to list
                except json.JSONDecodeError:
                    booking.booking_image = [booking.booking_image]

            booking.check_in_date = booking.check_in_date.date()
            booking.check_out_date = booking.check_out_date.date()
        return templates.TemplateResponse("booking.html", {"request": request, "admin_data": is_agent,
                                                           "is_agent": True, "current_date": datetime.date.today(),
                                                           "all_booking_data": all_booking_data})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/booking/', status_code=status.HTTP_200_OK)
def booking_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        all_booking_data = get_all_db_data(db, tour_models.Bookings)
        for booking in all_booking_data:
            # Convert JSON string to a list if it's stored as a string
            if isinstance(booking.booking_image, str):
                try:
                    booking.booking_image = json.loads(booking.booking_image)  # Convert to list
                except json.JSONDecodeError:
                    booking.booking_image = [booking.booking_image]

            booking.check_in_date = booking.check_in_date.date()
            booking.check_out_date = booking.check_out_date.date()
        return templates.TemplateResponse("booking.html", {"request": request, "admin_data": is_admin,
                                                           "current_date": datetime.date.today(),
                                                           "all_booking_data": all_booking_data})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        all_booking_data = get_all_db_data_with(db, tour_models.Bookings, tour_models.Bookings.agent_id, is_agent.id)
        for booking in all_booking_data:
            # Convert JSON string to a list if it's stored as a string
            if isinstance(booking.booking_image, str):
                try:
                    booking.booking_image = json.loads(booking.booking_image)  # Convert to list
                except json.JSONDecodeError:
                    booking.booking_image = [booking.booking_image]

            booking.check_in_date = booking.check_in_date.date()
            booking.check_out_date = booking.check_out_date.date()
        return templates.TemplateResponse("booking.html", {"request": request, "admin_data": is_agent, "is_agent": True,
                                                           "all_booking_data": all_booking_data})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/add_booking/', status_code=status.HTTP_200_OK)
def add_booking_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    if is_admin:
        agents_data = get_all_db_data(db, tour_models.Agents)
        return templates.TemplateResponse("add_booking.html", {"request": request, "admin_data": is_admin,
                                                               "agents_data": agents_data})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/add_booking/', status_code=status.HTTP_200_OK)
async def add_booking_api(request: Request, db: Session = Depends(get_db), agent_id: int = Form(...),
                          booking_title: str = Form(...), check_in_date: str = Form(...),
                          check_out_date: str = Form(...), description: str = Form(...),
                          images: List[UploadFile] = File(...)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('login_api'))

    agents_data = get_all_db_data(db, tour_models.Agents)
    try:
        upload_dir = Path("static/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Convert string dates to datetime objects
        check_in = datetime.datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.datetime.strptime(check_out_date, "%Y-%m-%d")

        # Calculate booking days
        booking_days = (check_out - check_in).days

        if booking_days >= 1:
            booking_days = booking_days + 1
        elif booking_days <= 0:
            booking_days = 1

        image_paths = []
        for image in images:
            if image.filename:
                timestamp = int(datetime.datetime.now().timestamp())
                # Sanitize filename
                safe_filename = "".join(c for c in image.filename if c.isalnum() or c in (' ', '.', '_')).rstrip()
                file_path = upload_dir / f"{timestamp}_{safe_filename}"
                with open(file_path, "wb") as buffer:
                    buffer.write(await image.read())
                image_paths.append(str(file_path))

        agent_data = get_one_db_data(db, tour_models.Agents, tour_models.Agents.id, agent_id)
        new_booking = tour_models.Bookings(agency_name=agent_data.agency_name, booking_title=booking_title,
                                           check_in_date=check_in, check_out_date=check_out,
                                           booking_image=json.dumps(image_paths), book_days=str(booking_days),
                                           booking_details=description, booking_status=True, admin_id=is_admin.id,
                                           agent_id=agent_id)
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)

        return templates.TemplateResponse("add_booking.html", {"request": request, "admin_data": is_admin,
                                                               "agents_data": agents_data,
                                                               "success": "Booking added successfully!"})

    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("add_booking.html", {"request": request, "admin_data": is_admin,
                                                               "agents_data": agents_data,
                                                               "error": f"Error adding booking: {str(e)}"})

@app.get('/booking/{data_id}/', status_code=status.HTTP_200_OK)
def booking_detail_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        booking_days_data = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id,
                                                     data_id)

        return templates.TemplateResponse("booking_detail.html", {"request": request, "admin_data": is_admin,
                                                                  "data_id": data_id,
                                                                  "booking_days_data": booking_days_data})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        booking_days_data = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id,
                                                 data_id)

        return templates.TemplateResponse("booking_detail.html", {"request": request, "admin_data": is_admin,
                                                                  "is_agent": True, "data_id": data_id,
                                                                  "booking_days_data": booking_days_data})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/booking/{data_id}/', status_code=status.HTTP_200_OK)
def booking_detail_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        booking_days_data = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id,
                                                     data_id)
        return templates.TemplateResponse("booking_detail.html", {"request": request, "admin_data": is_admin,
                                                                  "data_id": data_id,
                                                                  "booking_days_data": booking_days_data})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        booking_days_data = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id,
                                                 data_id)

        return templates.TemplateResponse("booking_detail.html", {"request": request, "admin_data": is_admin,
                                                                  "is_agent": True, "data_id": data_id,
                                                                  "booking_days_data": booking_days_data})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/edit_booking/{data_id}/', status_code=status.HTTP_200_OK)
def edit_booking_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    if is_admin:
        agents_data = get_all_db_data(db, tour_models.Agents)
        booking_data = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)

        return templates.TemplateResponse("edit_booking.html", {"request": request, "admin_data": is_admin,
                                                                  "agents_data": agents_data, "data_id": data_id,
                                                                  "booking_data": booking_data})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/edit_booking/{data_id}/', status_code=status.HTTP_200_OK)
async def edit_booking_api(request: Request, data_id: int, agent_id: int = Form(None), booking_title: str = Form(...),
                     check_in_date: str = Form(...), check_out_date: str = Form(...), description: str = Form(...),
                     images: Optional[List[UploadFile]] = File(None), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    agents_data = get_all_db_data(db, tour_models.Agents)
    booking_data = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)

    try:
        upload_dir = Path("static/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        image_paths = []
        if images:
            for image in images:
                if image.filename:
                    timestamp = int(datetime.datetime.now().timestamp())
                    safe_filename = "".join(c for c in image.filename if c.isalnum() or c in (' ', '.', '_')).rstrip()
                    file_path = upload_dir / f"{timestamp}_{safe_filename}"
                    with open(file_path, "wb") as buffer:
                        buffer.write(await image.read())
                    image_paths.append(str(file_path))

        # Convert dates
        check_in = datetime.datetime.strptime(check_in_date, "%Y-%m-%d") if check_in_date else None
        check_out = datetime.datetime.strptime(check_out_date, "%Y-%m-%d") if check_out_date else None
        booking_days = (check_out - check_in).days + 1 if check_in and check_out else None

        # Update booking fields only if new values are provided
        if booking_title:
            booking_data.booking_title = booking_title

        if check_in:
            booking_data.check_in_date = check_in

        if check_out:
            booking_data.check_out_date = check_out

        if booking_days:
            booking_data.book_days = str(booking_days)

        if description:
            booking_data.booking_details = description

        if agent_id:
            booking_data.agent_id = agent_id

        # Update image only if a new one is uploaded
        if image_paths:
            booking_data.booking_image = image_paths[0]

        # Commit changes
        db.commit()
        db.refresh(booking_data)

        return templates.TemplateResponse("edit_booking.html", {"request": request, "admin_data": is_admin,
                                                                "agents_data": agents_data, "data_id": data_id,
                                                                "booking_data": booking_data,
                                                                "success": "Booking updated successfully!"})

    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("edit_booking.html", {"request": request, "admin_data": is_admin,
                                                                "agents_data": agents_data, "data_id": data_id,
                                                                "booking_data": booking_data,
                                                                "error": f"Error updating booking: {str(e)}"})

@app.get('/delete_booking/{data_id}/', status_code=status.HTTP_200_OK)
def delete_booking_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    if is_admin:
        booking_data = delete_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)
        return RedirectResponse(url=app.url_path_for("booking_api"))

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/add_booking_days/{data_id}/', status_code=status.HTTP_200_OK)
def add_booking_days_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        booking_data = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)
        return templates.TemplateResponse("add_booking_days.html", {"request": request, "admin_data": is_admin,
                                                                    "booking_data": booking_data, "data_id": data_id})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        booking_data = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)
        return templates.TemplateResponse("add_booking_days.html", {"request": request, "admin_data": is_agent,
                                                                    "booking_data": booking_data, "is_agent": True,
                                                                    "data_id": data_id})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/add_booking_days/{data_id}/', status_code=status.HTTP_200_OK)
async def add_booking_days_api(request: Request, data_id: int, booking_title: str = Form(...),
                               description: str = Form(...), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    upload_dir = Path("static/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    if is_admin:
        try:
            booking_day = tour_models.BookingDays(day_title=booking_title, booking_day_details=description,
                                                  booking_id=data_id)
            db.add(booking_day)
            db.commit()
            db.refresh(booking_day)

            booking_data = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)
            return templates.TemplateResponse("add_booking_days.html", {"request": request, "admin_data": is_admin,
                                                                        "booking_data": booking_data, "data_id": data_id,
                                                                        "success": "Booking added successfully!"})

        except Exception as e:
            db.rollback()
            booking_data = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)
            return templates.TemplateResponse("add_booking_days.html", {"request": request, "admin_data": is_admin,
                                                                   "booking_data": booking_data, "data_id": data_id,
                                                                   "error": f"Error adding booking: {str(e)}"})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        try:
            booking_day = tour_models.BookingDays(day_title=booking_title, booking_day_details=description,
                                                  booking_id=data_id)
            db.add(booking_day)
            db.commit()
            db.refresh(booking_day)

            booking_data = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)
            return templates.TemplateResponse("add_booking_days.html", {"request": request, "admin_data": is_agent,
                                                                        "booking_data": booking_data, "is_agent": True,
                                                                        "data_id": data_id,
                                                                        "success": "Booking added successfully!"})

        except Exception as e:
            db.rollback()
            booking_data = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)
            return templates.TemplateResponse("add_booking.html", {"request": request, "admin_data": is_admin,
                                                                   "booking_data": booking_data, "is_agent": True,
                                                                   "data_id": data_id,
                                                                   "error": f"Error adding booking: {str(e)}"})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/edit_booking_day/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
def edit_booking_day_api(request: Request, data_id: int, day_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    booking_day_data = get_one_db_data(db, tour_models.BookingDays, tour_models.BookingDays.id, day_id)
    return templates.TemplateResponse("edit_booking_days.html", {"request": request, "admin_data": is_admin,
                                                                 "data_id": data_id,
                                                                 "booking_day_data": booking_day_data})

@app.post('/edit_booking_day/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
async def edit_booking_day_api(request: Request, data_id: int, day_id: int, day_title: str = Form(...),
                               description: str = Form(...), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    booking_day_data = get_one_db_data(db, tour_models.BookingDays, tour_models.BookingDays.id, day_id)
    try:
        if day_title:
            booking_day_data.day_title = day_title

        if description:
            booking_day_data.booking_day_details = description

        # Commit changes
        db.commit()
        db.refresh(booking_day_data)

        return templates.TemplateResponse("edit_booking_days.html", {"request": request, "admin_data": is_admin,
                                                                     "data_id": data_id,
                                                                     "booking_day_data": booking_day_data,
                                                                     "success": "Booking updated successfully!"})

    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("edit_booking_days.html", {"request": request, "admin_data": is_admin,
                                                                     "data_id": data_id,
                                                                     "booking_day_data": booking_day_data,
                                                                     "error": f"Error updating booking: {str(e)}"})

@app.get('/delete_booking_day/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
def delete_booking_day_api(request: Request, data_id: int, day_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    if is_admin:
        booking_data = delete_db_data(db, tour_models.BookingDays, tour_models.BookingDays.id, day_id)
        return RedirectResponse(url=app.url_path_for("booking_api"))

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/update_booking/{data_id}/', status_code=status.HTTP_200_OK)
def add_booking_day_detail_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    if is_admin:
        booking_days_data = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id,
                                                     data_id)

        return templates.TemplateResponse("booking_detail.html", {"request": request, "admin_data": is_admin,
                                                                  "booking_days_data": booking_days_data})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/update_booking/{data_id}/', status_code=status.HTTP_200_OK)
def add_booking_day_detail_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    if is_admin:
        booking_days_data = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id,
                                                     data_id)
        return templates.TemplateResponse("booking_detail.html", {"request": request, "admin_data": is_admin,
                                                                  "booking_days_data": booking_days_data})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/booking_status/', status_code=status.HTTP_200_OK)
def booking_status_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    edit_booking_status = True

    if is_admin:
        booking_map, booking_event_map = get_booking_events_data(
            db, is_admin=True, booking_model=tour_models.Bookings, booking_day_model=tour_models.BookingDays,
            booking_day_event_model=tour_models.BookingDayEvents)

        return templates.TemplateResponse("booking_status.html", {
            "request": request, "admin_data": is_admin, "edit_booking_status": edit_booking_status,
            "is_agent": False, "booking_map": booking_map, "booking_event_map": booking_event_map})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        booking_map, booking_event_map = get_booking_events_data(
            db, is_admin=False, user_id=is_agent.id, booking_model=tour_models.Bookings,
            booking_day_model=tour_models.BookingDays, booking_day_event_model=tour_models.BookingDayEvents)

        return templates.TemplateResponse("booking_status.html", {
            "request": request, "admin_data": is_agent, "edit_booking_status": edit_booking_status,
            "is_agent": True, "booking_map": booking_map, "booking_event_map": booking_event_map})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/booking_status/', status_code=status.HTTP_200_OK)
def booking_status_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    edit_booking_status = True

    if is_admin:
        booking = get_all_db_data(db, tour_models.Bookings)
        booking_days = get_all_db_data(db, tour_models.BookingDays)
        events = get_all_db_data(db, tour_models.BookingDayEvents)

        # Convert image strings to lists
        for event in events:
            if isinstance(event.day_event_images, str):
                event.day_event_images = json.loads(event.day_event_images)

        # Organize events by booking
        booking_event_map = defaultdict(list)
        for event in events:
            day = next((d for d in booking_days if d.id == event.booking_days_id), None)
            if day:
                booking_event_map[booking.id].append({"event": event, "day_title": day.day_title})

        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_admin,
                                                                  "edit_booking_status": edit_booking_status,
                                                                  "is_agent": False,
                                                                  "booking_map": {booking.id: booking},
                                                                  "booking_event_map": booking_event_map})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        booking = get_all_db_data_with(db, tour_models.Bookings, tour_models.Bookings.agent_id, is_agent.id)
        booking_days = get_all_db_data(db, tour_models.BookingDays)
        events = get_all_db_data(db, tour_models.BookingDayEvents)

        # Convert image strings to lists
        for event in events:
            if isinstance(event.day_event_images, str):
                event.day_event_images = json.loads(event.day_event_images)

        # Organize events by booking
        booking_event_map = defaultdict(list)
        for event in events:
            day = next((d for d in booking_days if d.id == event.booking_days_id), None)
            if day:
                booking_event_map[booking.id].append({"event": event, "day_title": day.day_title})

        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_agent,
                                                                  "edit_booking_status": edit_booking_status,
                                                                  "is_agent": True,
                                                                  "booking_map": {booking.id: booking},
                                                                  "booking_event_map": booking_event_map})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/booking_status/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
def booking_day_status_api(request: Request, data_id: int, day_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        booking = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)
        booking_days = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id, data_id)
        events = db.query(tour_models.BookingDayEvents).join(tour_models.BookingDays,
                                                             tour_models.BookingDayEvents.booking_days_id == day_id
                                                             ).filter(tour_models.BookingDays.booking_id == data_id).all()

        # Convert image strings to lists
        for event in events:
            if isinstance(event.day_event_images, str) and event.day_event_images.strip():
                try:
                    event.day_event_images = json.loads(event.day_event_images)
                except json.JSONDecodeError:
                    event.day_event_images = []
            else:
                event.day_event_images = []

        # Organize events by booking
        booking_event_map = defaultdict(list)
        for event in events:
            day = next((d for d in booking_days if d.id == event.booking_days_id), None)
            if day:
                booking_event_map[booking.id].append({"event": event, "day_title": day.day_title})

        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_admin,
                                                                  "day_id": day_id, "is_agent": False,
                                                                  "data_id": data_id,
                                                                  "booking_map": {booking.id: booking},
                                                                  "booking_event_map": booking_event_map})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        booking = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)
        booking_days = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id, data_id)
        events = db.query(tour_models.BookingDayEvents).join(tour_models.BookingDays,
                                                             tour_models.BookingDayEvents.booking_days_id == day_id
                                                             ).filter(
            tour_models.BookingDays.booking_id == data_id).all()

        # Convert image strings to lists
        for event in events:
            if isinstance(event.day_event_images, str) and event.day_event_images.strip():
                try:
                    event.day_event_images = json.loads(event.day_event_images)
                except json.JSONDecodeError:
                    event.day_event_images = []
            else:
                event.day_event_images = []

        # Organize events by booking
        booking_event_map = defaultdict(list)
        for event in events:
            day = next((d for d in booking_days if d.id == event.booking_days_id), None)
            if day:
                booking_event_map[booking.id].append({"event": event, "day_title": day.day_title})

        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_agent,
                                                                  "day_id": day_id, "is_agent": True,
                                                                  "data_id": data_id,
                                                                  "booking_map": {booking.id: booking},
                                                                  "booking_event_map": booking_event_map})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/booking_status/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
def booking_day_status_api(request: Request, data_id: int, day_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        booking = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)
        booking_days = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id, data_id)
        events = db.query(tour_models.BookingDayEvents).join(tour_models.BookingDays,
                                                             tour_models.BookingDayEvents.booking_days_id == day_id
                                                             ).filter(
            tour_models.BookingDays.booking_id == data_id).all()

        # Convert image strings to lists
        for event in events:
            if isinstance(event.day_event_images, str) and event.day_event_images.strip():
                try:
                    event.day_event_images = json.loads(event.day_event_images)
                except json.JSONDecodeError:
                    event.day_event_images = []
            else:
                event.day_event_images = []

        # Organize events by booking
        booking_event_map = defaultdict(list)
        for event in events:
            day = next((d for d in booking_days if d.id == event.booking_days_id), None)
            if day:
                booking_event_map[booking.id].append({"event": event, "day_title": day.day_title})

        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_admin,
                                                                  "day_id": day_id, "is_agent": False,
                                                                  "data_id": data_id,
                                                                  "booking_map": {booking.id: booking},
                                                                  "booking_event_map": booking_event_map})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        booking = get_one_db_data(db, tour_models.Bookings, tour_models.Bookings.id, data_id)
        booking_days = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id, data_id)
        events = db.query(tour_models.BookingDayEvents).join(tour_models.BookingDays,
                                                             tour_models.BookingDayEvents.booking_days_id == day_id
                                                             ).filter(
            tour_models.BookingDays.booking_id == data_id).all()

        # Convert image strings to lists
        for event in events:
            if isinstance(event.day_event_images, str) and event.day_event_images.strip():
                try:
                    event.day_event_images = json.loads(event.day_event_images)
                except json.JSONDecodeError:
                    event.day_event_images = []
            else:
                event.day_event_images = []

        # Organize events by booking
        booking_event_map = defaultdict(list)
        for event in events:
            day = next((d for d in booking_days if d.id == event.booking_days_id), None)
            if day:
                booking_event_map[booking.id].append({"event": event, "day_title": day.day_title})

        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_agent,
                                                                  "day_id": day_id, "is_agent": True,
                                                                  "data_id": data_id,
                                                                  "booking_map": {booking.id: booking},
                                                                  "booking_event_map": booking_event_map})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/add_booking_status/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
def add_booking_status_api(request: Request, data_id: int, day_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        agents_data = get_all_db_data(db, tour_models.Agents)
        return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_admin,
                                                                      "agents_data": agents_data,
                                                                      "data_id": data_id, "day_id": day_id,})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        agents_data = get_all_db_data(db, tour_models.Agents)
        return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_agent,
                                                                      "data_id": data_id, "day_id": day_id,
                                                                      "agents_data": agents_data, "is_agent": True})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/add_booking_status/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
async def add_booking_status_api(request: Request, data_id: int, day_id: int, agent_name: str = Form(...),
                                 description: str = Form(...), booking_title: str = Form(...),
                                 images: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        upload_dir = Path("static/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        image_paths = []
        for image in images:
            if image.filename:  # Process only if a file was uploaded
                timestamp = int(datetime.datetime.now().timestamp())
                safe_filename = "".join(c for c in image.filename if c.isalnum() or c in (' ', '.', '_')).rstrip()
                file_path = upload_dir / f"{timestamp}_{safe_filename}"

                with open(file_path, "wb") as buffer:
                    buffer.write(await image.read())

                # Save relative path for frontend display
                image_paths.append(f"/static/uploads/{timestamp}_{safe_filename}")

        try:
            booking_status = tour_models.BookingDayEvents(agent_name=agent_name, booking_title=booking_title,
                                                          day_event_details=description, day_number=day_id,
                                                          day_event_images=json.dumps(image_paths),
                                                          booking_days_id=day_id)
            add_data_in_db(db, booking_status)
            message = 'Status Added Successfully'
            return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_admin,
                                                                          "success": message, "data_id": data_id,
                                                                          "day_id": day_id,})
        except Exception as e:
            message = 'Something went wrong'
            return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_admin,
                                                                          "error": message, "data_id": data_id,
                                                                          "day_id": day_id,})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        upload_dir = Path("static/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        image_paths = []
        for image in images:
            if image.filename:  # Process only if a file was uploaded
                timestamp = int(datetime.datetime.now().timestamp())
                safe_filename = "".join(c for c in image.filename if c.isalnum() or c in (' ', '.', '_')).rstrip()
                file_path = upload_dir / f"{timestamp}_{safe_filename}"

                with open(file_path, "wb") as buffer:
                    buffer.write(await image.read())

                # Save relative path for frontend display
                image_paths.append(f"/static/uploads/{timestamp}_{safe_filename}")

        try:
            booking_status = tour_models.BookingDayEvents(agent_name=agent_name, booking_title=booking_title,
                                                          day_event_details=description, day_number=day_id,
                                                          day_event_images=json.dumps(image_paths),
                                                          booking_days_id=day_id)
            add_data_in_db(db, booking_status)
            message = 'Status Added Successfully'
            return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_agent,
                                                                          "success": message, "data_id": data_id,
                                                                          "day_id": day_id, "is_agent": True})
        except Exception as e:
            message = 'Something went wrong'
            return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_agent,
                                                                          "error": message, "data_id": data_id,
                                                                          "day_id": day_id, "is_agent": True})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/edit_booking_day_status/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
def edit_booking_day_status_api(request: Request, data_id: int, day_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    day_status_data = get_one_db_data(db, tour_models.BookingDayEvents, tour_models.BookingDayEvents.id, day_id)
    return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_admin,
                                                                 "data_id": data_id,
                                                                 "day_status_data": day_status_data})

@app.post('/edit_booking_day_status/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
async def edit_booking_day_status_api(request: Request, data_id: int, day_id: int, agent_name: str = Form(...),
                                      booking_title: str = Form(...), description: str = Form(...),
                                      images: Optional[List[UploadFile]] = File(None), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    day_status_data = get_one_db_data(db, tour_models.BookingDayEvents, tour_models.BookingDayEvents.id, day_id)
    try:
        upload_dir = Path("static/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        image_paths = []

        if agent_name:
            day_status_data.agent_name = agent_name

        if booking_title:
            day_status_data.booking_title = booking_title

        if description:
            day_status_data.day_event_details = description

        if images:
            for image in images:
                if image.filename:
                    timestamp = int(datetime.datetime.now().timestamp())
                    safe_filename = "".join(c for c in image.filename if c.isalnum() or c in (' ', '.', '_')).rstrip()
                    file_path = upload_dir / f"{timestamp}_{safe_filename}"
                    with open(file_path, "wb") as buffer:
                        buffer.write(await image.read())
                    # Add leading slash and ensure POSIX format
                    image_paths.append(f"/{file_path.as_posix()}")

        # Only update images if new ones were uploaded
        if len(image_paths) > 0:
            day_status_data.day_event_images = json.dumps(image_paths)

        # Commit changes
        db.commit()
        db.refresh(day_status_data)

        return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_admin,
                                                                     "data_id": data_id,
                                                                     "day_status_data": day_status_data,
                                                                     "success": "Booking updated successfully!"})

    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_admin,
                                                                     "data_id": data_id,
                                                                     "day_status_data": day_status_data,
                                                                     "error": f"Error updating booking: {str(e)}"})

@app.get('/delete_booking_day_status/{data_id}/{day_id}/{event_id}/', status_code=status.HTTP_200_OK)
def delete_booking_day_status_api(request: Request, data_id: int, day_id: int, event_id: int,
                                  db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('logout'))

    if is_admin:
        booking_data = delete_db_data(db, tour_models.BookingDayEvents, tour_models.BookingDayEvents.id, event_id)
        return RedirectResponse(url=app.url_path_for("booking_day_status_api", data_id=data_id, day_id=day_id),
                                status_code=302)

    return RedirectResponse(url=app.url_path_for('logout'))

@app.get('/add_home_images/')
def add_home_images(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("add_home_images.html", {"request": request, "admin_data": is_admin})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        return templates.TemplateResponse("add_home_images.html", {"request": request, "admin_data": is_agent,
                                                                   "is_agent": True})

    return RedirectResponse(url=app.url_path_for('logout'))

@app.post('/add_home_images/')
def add_home_images(request: Request, title_1: str = Form(...), title_2: str = Form(...), title_3: str = Form(...),
                    description_1: str = Form(...), description_2: str = Form(...), description_3: str = Form(...),
                    image_1: UploadFile = Form(...), image_2: UploadFile = Form(...), image_3: UploadFile = Form(...),
                    db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        try:
            upload_dir = Path("static/home_images")
            upload_dir.mkdir(parents=True, exist_ok=True)

            image_1_path = save_image(upload_dir, image_1)
            image_2_path = save_image(upload_dir, image_2)
            image_3_path = save_image(upload_dir, image_3)

            home_images = tour_models.HomeImages(title_1=title_1, title_2=title_2, title_3=title_3,
                                                 description_1=description_1, description_2=description_2,
                                                 description_3=description_3, image_1=image_1_path,
                                                 image_2=image_2_path, image_3=image_3_path)
            add_data_in_db(db, home_images)
            return templates.TemplateResponse("add_home_images.html", {"request": request, "admin_data": is_admin,
                                                                       "success": "Images add successfully!"})

        except Exception as e:
            return templates.TemplateResponse("add_home_images.html", {"request": request, "admin_data": is_admin,
                                                                       "error": f"Something went wrong! {e}"})

    is_agent = get_one_db_data(db, tour_models.Agents, tour_models.Agents.user_token, is_token)
    if is_agent:
        return templates.TemplateResponse("add_home_images.html", {"request": request, "admin_data": is_agent,
                                                                   "is_agent": True})

    return RedirectResponse(url=app.url_path_for('logout'))


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
