from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP, Boolean, Float
from db_configration.db_connection import Base


class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=False, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, unique=False, nullable=False)
    user_token = Column(String, nullable=True)

    created_at = Column(TIMESTAMP, nullable=False)
    is_admin = Column(Boolean, default=False)
    user_status = Column(Boolean, default=False)


class Agents(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agency_name = Column(String, unique=False, nullable=False)
    address = Column(String, unique=False, nullable=False)
    website = Column(String, unique=True, nullable=False)
    country = Column(String, unique=True, nullable=False)
    city = Column(String, unique=True, nullable=False)
    zip_code = Column(String, unique=True, nullable=False)
    agent_name = Column(String, unique=True, nullable=False)
    user_name = Column(String, unique=True, nullable=False)
    mobile_number = Column(String, unique=True, nullable=False)
    email = Column(String, unique=False, nullable=False)
    password = Column(String, unique=False, nullable=False)
    user_token = Column(String, nullable=True)

    created_at = Column(TIMESTAMP, nullable=False)
    is_admin = Column(Boolean, default=False)
    user_status = Column(Boolean, default=False)

    admin_id = Column(Integer, ForeignKey("admin.id", ondelete="CASCADE"), nullable=False)


class Bookings(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_name = Column(String, unique=False, nullable=False)
    booking_image = Column(String, unique=False, nullable=False)
    booking_details = Column(String, unique=False, nullable=False)
    book_days = Column(String, unique=False, nullable=False)
    booking_date = Column(TIMESTAMP, nullable=False)
    booking_status = Column(Boolean, default=False)


class BookingDays(Base):
    __tablename__ = "booking_days"
    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_day = Column(String, unique=False, nullable=False)
    booking_day_image1 = Column(String, unique=False, nullable=False)
    booking_day_image2 = Column(String, unique=False, nullable=False)
    booking_day_image3 = Column(String, unique=False, nullable=False)
    booking_day_image4 = Column(String, unique=False, nullable=False)
    booking_day_image5 = Column(String, unique=False, nullable=False)
    booking_day_image6 = Column(String, unique=False, nullable=False)
    booking_day_image7 = Column(String, unique=False, nullable=False)
    booking_day_image8 = Column(String, unique=False, nullable=False)
    booking_day_image9 = Column(String, unique=False, nullable=False)
    booking_day_image10 = Column(String, unique=False, nullable=False)
    booking_day_details = Column(String, unique=False, nullable=False)
    booking_day_date = Column(TIMESTAMP, nullable=False)
    booking_status = Column(Boolean, default=False)
