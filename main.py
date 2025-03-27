from fastapi import FastAPI, Request, Depends, UploadFile, status, Form, File
from db_configration.db_connection import get_db, Base, engine
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from db_functions.db_function import get_one_db_data, add_data_in_db
from user_auth.auth_token import create_token
from user_auth.email_and_pass_verification import email_checker
from user_auth.password_hashing import Hash
from sqlalchemy.orm import Session
from models import tour_models
import datetime
import uvicorn

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
                print('user created')
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

    return templates.TemplateResponse("base.html", {"request": request, "admin_data": is_admin})

@app.post('/home/', status_code=status.HTTP_200_OK)
def home_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("base.html", {"request": request, "admin_data": is_admin})

# ========users apis=========
@app.get('/users/', status_code=status.HTTP_200_OK)
def users_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)

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

    return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin})

@app.post('/add_user/', status_code=status.HTTP_200_OK)
def add_user_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("add_user.html", {"request": request, "admin_data": is_admin})

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

    return templates.TemplateResponse("booking.html", {"request": request, "admin_data": is_admin})

@app.post('/booking/', status_code=status.HTTP_200_OK)
def booking_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("booking.html", {"request": request, "admin_data": is_admin})

@app.get('/booking/data_id/', status_code=status.HTTP_200_OK)
def booking_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)

    return templates.TemplateResponse("booking_detail.html", {"request": request, "admin_data": is_admin})

@app.post('/booking/data_id/', status_code=status.HTTP_200_OK)
def booking_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("booking_detail.html", {"request": request, "admin_data": is_admin})

@app.get('/add_booking/', status_code=status.HTTP_200_OK)
def add_booking_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)

    return templates.TemplateResponse("add_booking.html", {"request": request, "admin_data": is_admin})

@app.post('/add_booking/', status_code=status.HTTP_200_OK)
def add_booking_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("add_booking.html", {"request": request, "admin_data": is_admin})

@app.get('/booking_status/', status_code=status.HTTP_200_OK)
def booking_status_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)

    return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_admin})

@app.post('/booking_status/', status_code=status.HTTP_200_OK)
def booking_status_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_admin})

@app.get('/booking_status/data_id/updates/', status_code=status.HTTP_200_OK)
def booking_status_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)

    return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_admin})

@app.post('/booking_status/data_id/updates/', status_code=status.HTTP_200_OK)
def booking_status_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("booking_status.html", {"request": request, "admin_data": is_admin})

@app.get('/add_booking_status/data_id/', status_code=status.HTTP_200_OK)
def add_booking_status_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)

    return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_admin})

@app.post('/add_booking_status/data_id/', status_code=status.HTTP_200_OK)
def add_booking_status_api(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = get_one_db_data(db, tour_models.Admin, tour_models.Admin.user_token, is_token)
    if is_admin:
        return templates.TemplateResponse("add_booking_status.html", {"request": request, "admin_data": is_admin})


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
