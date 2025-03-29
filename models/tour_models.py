from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP, Boolean, Float, JSON
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
    website = Column(String, unique=False, nullable=False)
    country = Column(String, unique=False, nullable=False)
    city = Column(String, unique=False, nullable=False)
    zip_code = Column(String, unique=False, nullable=False)
    agent_name = Column(String, unique=False, nullable=False)
    user_name = Column(String, unique=False, nullable=False)
    mobile_number = Column(String, unique=False, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, unique=False, nullable=False)
    user_token = Column(String, nullable=True)

    created_at = Column(TIMESTAMP, nullable=False)
    is_admin = Column(Boolean, default=False)
    user_status = Column(Boolean, default=False)

    admin_id = Column(Integer, ForeignKey("admin.id", ondelete="CASCADE"), nullable=False)


class Bookings(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String, unique=False, nullable=False)
    booking_title = Column(String, unique=False, nullable=False)
    check_in_date = Column(TIMESTAMP, nullable=False)
    check_out_date = Column(TIMESTAMP, nullable=False)
    booking_image = Column(String, unique=False, nullable=False)
    book_days = Column(String, unique=False, nullable=False)
    booking_details = Column(String, unique=False, nullable=False)
    booking_status = Column(Boolean, default=False)

    admin_id = Column(Integer, ForeignKey("admin.id", ondelete="CASCADE"), nullable=False)


class BookingDays(Base):
    __tablename__ = "booking_days"
    id = Column(Integer, primary_key=True, autoincrement=True)
    day_title = Column(String, unique=False, nullable=False)
    booking_day_images = Column(JSON, unique=False, nullable=False)
    booking_day_details = Column(String, unique=False, nullable=False)

    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)

class BookingDayEvents(Base):
    __tablename__ = "booking_day_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(JSON, unique=False, nullable=False)
    day_number = Column(Integer, unique=False, nullable=False)
    day_event_images = Column(JSON, unique=False, nullable=False)
    day_event_details = Column(String, unique=False, nullable=False)

    booking_days_id = Column(Integer, ForeignKey("booking_days.id", ondelete="CASCADE"), nullable=False)
