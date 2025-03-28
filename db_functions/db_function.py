from sqlalchemy.orm import Session


def add_data_in_db(db: Session, db_data):
    db.add(db_data)
    db.commit()
    db.refresh(db_data)

def get_one_db_data(db: Session, table, compair_with, compair_data):
    db_data = db.query(table).filter(compair_with == compair_data).first()
    return db_data

def get_all_db_data_with(db: Session, table, compair_with, compair_data):
    db_data = db.query(table).filter(compair_with == compair_data).all()
    return db_data

def get_all_db_data(db: Session, table):
    db_data = db.query(table).all()
    return db_data