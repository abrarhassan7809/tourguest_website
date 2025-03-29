from fastapi import FastAPI, Request, Depends, UploadFile, status, Form, File
from db_configration.db_connection import get_db, Base, engine
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from db_functions.db_function import (get_one_db_data, add_data_in_db, get_all_db_data_with, get_all_db_data,
                                      get_all_db_data_and_with)
from user_auth.auth_token import create_token
from user_auth.email_and_pass_verification import email_checker
from user_auth.password_hashing import Hash
from sqlalchemy.orm import Session
from models import tour_models
from pathlib import Path
from typing import List
import datetime
import uvicorn
import json

app = FastAPI()
Base.metadata.create_all(engine)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# =========register and login===========
@app.get("/logout/")
def logout(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        is_user = db.query(tour_models.Admin).filter(tour_models.Admin.user_token == is_token).first()
        if is_user:
            is_user.user_token = None
            is_user.user_status = False
            db.commit()

        response = RedirectResponse(url=app.url_path_for("login_api"), status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie('token')
        request.cookies.pop('token')
        return response

    else:
        return RedirectResponse(url=app.url_path_for("login_api"), status_code=status.HTTP_303_SEE_OTHER)

@app.get('/register/', status_code=status.HTTP_200_OK)
def register_api(request: Request):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("home_api"))

    message = ''
    return templates.TemplateResponse("tour_register.html", {"request": request, "error": message})

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
            return templates.TemplateResponse("tour_register.html", {"request": request, "error": message})
        else:
            if password != confirm_password:
                message = 'Password is not matched'
                return templates.TemplateResponse("tour_register.html", {"request": request, "error": message})
            else:
                message = 'User Created Successfully'
                current_time = datetime.datetime.now()
                new_user = tour_models.Admin(name=name, email=email, password=Hash.argon2(password),
                                             created_at=current_time, is_admin=True, user_status=False)
                add_data_in_db(db, new_user)
                return templates.TemplateResponse("tour_login.html", {"request": request, "success": message})

    return RedirectResponse(url=app.url_path_for('register_api'))

@app.get('/', status_code=status.HTTP_200_OK)
def login_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        is_admin = db.query(tour_models.Admin).filter(tour_models.Admin.user_token == is_token).first()
        if not is_admin:
            admin_exist = db.query(tour_models.Admin).filter(tour_models.Admin.email == 'admin123@gmail.com').first()
            if not admin_exist:
                current_time = datetime.datetime.now()
                new_admin = tour_models.Admin(name="Admin", email="admin123@gmail.com", password=Hash.argon2("admin123"),
                                              user_token="", created_at=current_time, is_admin=True, user_status=False)
                db.add(new_admin)
                db.commit()
                db.refresh(new_admin)

        return templates.TemplateResponse("tour_login.html", {"request": request})

    return RedirectResponse(url=app.url_path_for("home_api"), status_code=status.HTTP_303_SEE_OTHER)

@app.post('/', status_code=status.HTTP_200_OK)
def login_api(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("home_api"))

    user = db.query(tour_models.Admin).filter(tour_models.Admin.email == email).first()
    error = "User not exits!"
    if user:
        if email_checker(email):
            if Hash.verify(password, user.password):
                if user:
                    user.user_token = create_token()
                    user.user_status = True
                    db.commit()

                    updated_token = db.query(tour_models.Admin).filter(tour_models.Admin.email == email).first()
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

        return templates.TemplateResponse("base.html", {"request": request, "admin_data": is_admin,
                                                        "all_booking_data": all_booking_data})

@app.post('/home/', status_code=status.HTTP_200_OK)
def home_api(request: Request, db: Session = Depends(get_db)):
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

        return templates.TemplateResponse("base.html", {"request": request, "admin_data": is_admin,
                                                        "all_booking_data": all_booking_data})

# ========users apis=========
@app.get('/users/', status_code=status.HTTP_200_OK)
def users_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("users.html", {"request": request, "admin_data": is_admin})

@app.post('/users/', status_code=status.HTTP_200_OK)
def users_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("users.html", {"request": request, "admin_data": is_admin})

@app.get('/add_user/', status_code=status.HTTP_200_OK)
def add_user_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin})

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
    if is_admin:
        if password != confirm_password:
            return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin, "error": "Passwords do not match"})

        user_exist = get_one_db_data(db, tour_models.Agents, tour_models.Agents.email, email)
        if user_exist:
            return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin, "error": "User already exists"})

        try:
            hashed_password = Hash.argon2(password)
            created_time = datetime.datetime.now()
            user_data = tour_models.Agents(agency_name=agency_name, address=address, website=website, country=country,
                                           city=city, zip_code=str(zip_code), agent_name=agent_name,
                                           user_name=user_name, mobile_number=mobile_number, email=email,
                                           password=hashed_password, created_at=created_time, admin_id=is_admin.id)
            db.add(user_data)
            db.commit()
            db.refresh(user_data)

            return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin, "success": "User added successfully"})
        except Exception as e:
            db.rollback()
            print(e)
            return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin, "error": f"Something went wrong: {str(e)}"})

@app.get('/update_profile/data_id/', status_code=status.HTTP_200_OK)
def update_profile_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)

    return templates.TemplateResponse("update_profile.html", {"request": request, "admin_data": is_admin})

@app.post('/update_profile/data_id/', status_code=status.HTTP_200_OK)
def update_profile_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("update_profile.html", {"request": request, "admin_data": is_admin})

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

        return templates.TemplateResponse("booking.html", {"request": request, "admin_data": is_admin,
                                                           "all_booking_data": all_booking_data})

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

        return templates.TemplateResponse("booking.html", {"request": request, "admin_data": is_admin,
                                                           "all_booking_data": all_booking_data})

@app.get('/booking/{data_id}/', status_code=status.HTTP_200_OK)
def booking_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        booking_days_data = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id,
                                                     data_id)

        return templates.TemplateResponse("booking_detail.html", {"request": request, "admin_data": is_admin,
                                                                  "booking_days_data": booking_days_data})

@app.post('/booking/{data_id}/', status_code=status.HTTP_200_OK)
def booking_api(request: Request, data_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        booking_days_data = get_all_db_data_with(db, tour_models.BookingDays, tour_models.BookingDays.booking_id,
                                                     data_id)
        return templates.TemplateResponse("booking_detail.html", {"request": request, "admin_data": is_admin,
                                                                  "booking_days_data": booking_days_data})

@app.get('/add_booking/', status_code=status.HTTP_200_OK)
def add_booking_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("add_booking.html", {"request": request, "admin_data": is_admin})

@app.post('/add_booking/', status_code=status.HTTP_200_OK)
async def add_booking_api(request: Request, db: Session = Depends(get_db), agent_name: str = Form(...),
                          booking_title: str = Form(...), check_in_date: str = Form(...),
                          check_out_date: str = Form(...), booking_days: int = Form(...), description: str = Form(...),
                          images: List[UploadFile] = File(...)):

    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if not is_admin:
        return RedirectResponse(url=app.url_path_for('login_api'))

    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("static/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Convert string dates to datetime objects
        check_in = datetime.datetime.strptime(check_in_date, "%Y-%m-%dT%H:%M")
        check_out = datetime.datetime.strptime(check_out_date, "%Y-%m-%dT%H:%M")

        # Process form data
        form_data = await request.form()

        # Save main booking images
        image_paths = []
        for image in images:
            if image.filename:  # Only process if file was uploaded
                timestamp = int(datetime.datetime.now().timestamp())
                # Sanitize filename
                safe_filename = "".join(c for c in image.filename if c.isalnum() or c in (' ', '.', '_')).rstrip()
                file_path = upload_dir / f"{timestamp}_{safe_filename}"
                with open(file_path, "wb") as buffer:
                    buffer.write(await image.read())
                image_paths.append(str(file_path))

        # Create main booking record
        new_booking = tour_models.Bookings(agent_name=agent_name, booking_title=booking_title, check_in_date=check_in,
                                           check_out_date=check_out, booking_image=json.dumps(image_paths),
                                           book_days=str(booking_days), booking_details=description,
                                           booking_status=True, admin_id=is_admin.id)
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)

        # Process each booking day
        for day in range(1, booking_days + 1):
            if day == 1:
                # Use main form data for first day
                day_title = booking_title
                day_description = description
                day_images = image_paths
            else:
                # Get dynamic fields for subsequent days
                day_title = form_data.get(f"booking_title_{day}")
                day_description = form_data.get(f"description_{day}")

                # Process day-specific images
                day_images = []
                day_files = request._form.getlist(f"images_{day}")
                for image in day_files:
                    if image.filename:  # Only process if file was uploaded
                        timestamp = int(datetime.datetime.now().timestamp())
                        # Sanitize filename
                        safe_filename = "".join(
                            c for c in image.filename if c.isalnum() or c in (' ', '.', '_')).rstrip()
                        file_path = upload_dir / f"day{day}_{timestamp}_{safe_filename}"
                        with open(file_path, "wb") as buffer:
                            buffer.write(await image.read())
                        day_images.append(str(file_path))

            # Create booking day record
            booking_day = tour_models.BookingDays(day_title=day_title, booking_day_images=json.dumps(day_images),
                                                  booking_day_details=day_description, booking_id=new_booking.id)
            db.add(booking_day)

        db.commit()

        return templates.TemplateResponse("add_booking.html", {"request": request, "admin_data": is_admin,
                                                               "success": "Booking added successfully!"})

    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("add_booking.html", {"request": request, "admin_data": is_admin,
                                                               "error": f"Error adding booking: {str(e)}"})

@app.get('/booking_status/', status_code=status.HTTP_200_OK)
def booking_status_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        all_days_events = get_all_db_data(db, tour_models.BookingDayEvents)
        # Ensure image paths are converted to Python lists
        for event in all_days_events:
            if isinstance(event.day_event_images, str):  # If stored as a string, convert it to a list
                event.day_event_images = json.loads(event.day_event_images)

        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_admin,
                                                                  "show_all_booking": True,
                                                                  "all_days_events": all_days_events})

@app.post('/booking_status/', status_code=status.HTTP_200_OK)
def booking_status_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        all_days_events = get_all_db_data(db, tour_models.BookingDayEvents)
        # Ensure image paths are converted to Python lists
        for event in all_days_events:
            if isinstance(event.day_event_images, str):  # If stored as a string, convert it to a list
                event.day_event_images = json.loads(event.day_event_images)

        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_admin,
                                                                  "show_all_booking": True,
                                                                  "all_days_events": all_days_events})

@app.get('/booking_status/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
def booking_status_api(request: Request, data_id: int, day_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        all_days_events = get_all_db_data_and_with(db, tour_models.BookingDayEvents,
                                                   tour_models.BookingDayEvents.booking_days_id,
                                                   tour_models.BookingDayEvents.day_number, data_id, day_id)
        # Ensure image paths are converted to Python lists
        for event in all_days_events:
            if isinstance(event.day_event_images, str):  # If stored as a string, convert it to a list
                event.day_event_images = json.loads(event.day_event_images)

        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_admin,
                                                                  "data_id": data_id, "day_id": day_id,
                                                                  "all_days_events": all_days_events})

@app.post('/booking_status/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
def booking_status_api(request: Request, data_id: int, day_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        all_days_events = get_all_db_data_and_with(db, tour_models.BookingDayEvents,
                                                   tour_models.BookingDayEvents.booking_days_id,
                                                   tour_models.BookingDayEvents.day_number, data_id, day_id)
        # Ensure image paths are converted to Python lists
        for event in all_days_events:
            if isinstance(event.day_event_images, str):  # If stored as a string, convert it to a list
                event.day_event_images = json.loads(event.day_event_images)

        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_admin,
                                                                  "data_id": data_id, "day_id": day_id,
                                                                  "all_days_events": all_days_events})

@app.get('/add_booking_status/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
def add_booking_status_api(request: Request, data_id: int, day_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_admin,
                                                                      "data_id": data_id, "day_id": day_id,})

@app.post('/add_booking_status/{data_id}/{day_id}/', status_code=status.HTTP_200_OK)
async def add_booking_status_api(request: Request, data_id: int, day_id: int, agent_name: str = Form(...),
                                 description: str = Form(...),
                                 images: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        # Create uploads directory if it doesn't exist
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
            booking_status = tour_models.BookingDayEvents(agent_name=agent_name, day_event_details=description,
                                                          day_event_images=json.dumps(image_paths), day_number=day_id,
                                                          booking_days_id=data_id)
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


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
