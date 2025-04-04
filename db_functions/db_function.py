import shutil
import uuid

from fastapi import UploadFile
from sqlalchemy import and_
from sqlalchemy.orm import Session


def add_data_in_db(db: Session, db_data):
    db.add(db_data)
    db.commit()
    db.refresh(db_data)

def delete_db_data(db: Session, db_data):
    db.delete(db_data)
    db.commit()

def get_one_db_data(db: Session, table, compair_with, compair_data):
    db_data = db.query(table).filter(compair_with == compair_data).first()
    return db_data

def get_all_db_data_with(db: Session, table, compair_with, compair_data):
    db_data = db.query(table).filter(compair_with == compair_data).all()
    return db_data

def get_all_db_data_and_with(db: Session, table, compair_with1, compair_with2, compair_data1, compair_data2):
    db_data = db.query(table).filter(and_(compair_with1 == compair_data1, compair_with2 == compair_data2)).all()
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