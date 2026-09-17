import json
import shutil
import uuid
from collections import defaultdict
from typing import Any
from fastapi import UploadFile
from sqlalchemy import and_
from sqlalchemy.orm import Session


def add_data_in_db(db: Session, db_data):
    db.add(db_data)
    db.commit()
    db.refresh(db_data)

def delete_db_data(db: Session, table, compair_with, compair_data):
    try:
        db_data = db.query(table).filter(compair_with == compair_data).first()
        db.delete(db_data)
        db.commit()
        return True
    except Exception as e:
        return False

def get_one_db_data(db: Session, table, compair_with, compair_data):
    db_data = db.query(table).filter(compair_with == compair_data).first()
    return db_data

def get_all_db_data_with(db: Session, model, filter_column, filter_value, agency_name: str = None):
    query = db.query(model).filter(filter_column == filter_value)

    if agency_name:
        query = query.filter(model.agency_name.ilike(f"%{agency_name}%"))  # Case-insensitive search

    return query.all()

def get_all_db_data_and_with(db: Session, table, compair_with1, compair_with2, compair_data1, compair_data2):
    db_data = db.query(table).filter(and_(compair_with1 == compair_data1, compair_with2 == compair_data2)).all()
    return db_data

def get_one_db_data_and_with(db: Session, table, compair_with1, compair_with2, compair_data1, compair_data2):
    db_data = db.query(table).filter(and_(compair_with1 == compair_data1, compair_with2 == compair_data2)).first()
    return db_data

def get_all_db_data(db: Session, table):
    db_data = db.query(table).all()
    return db_data

def save_image(upload_dir, file: UploadFile):
    file_ext = file.filename.split(".")[-1]  # Get file extension
    unique_filename = f"{uuid.uuid4()}.{file_ext}"  # Generate unique filename
    file_path = upload_dir / unique_filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return f"/static/home_images/{unique_filename}"

def get_booking_events_data(db: Session, is_admin: bool, user_id: int = None, booking_model=Any, booking_day_model=Any,
                            booking_day_event_model=Any):
    if is_admin:
        bookings = get_all_db_data(db, booking_model)
    else:
        bookings = get_all_db_data_with(db, booking_model, booking_model.agent_id, user_id)

    if not bookings:
        return {}, {}

    booking_ids = [booking.id for booking in bookings]

    booking_days = db.query(booking_day_model).filter(booking_day_model.booking_id.in_(booking_ids)).all()
    booking_day_ids = [bd.id for bd in booking_days]

    # Get events for these specific booking days
    events = db.query(booking_day_event_model).filter(
        booking_day_event_model.booking_days_id.in_(booking_day_ids)).all() if booking_day_ids else []

    # Convert image strings to lists
    for event in events:
        if isinstance(event.day_event_images, str):
            try:
                event.day_event_images = json.loads(event.day_event_images)
            except:
                event.day_event_images = []

    # Organize events by booking
    booking_event_map = defaultdict(list)
    for event in events:
        day = next((d for d in booking_days if d.id == event.booking_days_id), None)
        if day:
            booking = next((b for b in bookings if b.id == day.booking_id), None)
            if booking:
                booking_event_map[booking.id].append({"event": event, "day_title": day.day_title})

    booking_map = {b.id: b for b in bookings}

    return booking_map, booking_event_map