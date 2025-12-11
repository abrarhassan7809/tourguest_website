from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP, Boolean, Float, JSON
from sqlalchemy.orm import relationship

from db_configration.db_connection import Base


class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    user_token = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)
    is_admin = Column(Boolean, default=False)
    user_status = Column(Boolean, default=False)

    # Relationships
    agents = relationship("Agents", cascade="all, delete", passive_deletes=True)
    bookings = relationship("Bookings", cascade="all, delete", passive_deletes=True)


class Agents(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agency_name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    website = Column(String, nullable=False)
    country = Column(String, nullable=False)
    city = Column(String, nullable=False)
    zip_code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    mobile_number = Column(String, nullable=False)
    email = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    user_token = Column(String, nullable=True)

    created_at = Column(TIMESTAMP, nullable=False)
    is_admin = Column(Boolean, default=False)
    user_status = Column(Boolean, default=False)

    admin_id = Column(Integer, ForeignKey("admin.id", ondelete="CASCADE"), nullable=False)

    # Relationship
    bookings = relationship("Bookings", cascade="all, delete", passive_deletes=True)


class HomeImages(Base):
    __tablename__ = "home_images"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title_1 = Column(String, nullable=False)
    title_2 = Column(String, nullable=False)
    title_3 = Column(String, nullable=False)
    description_1 = Column(String, nullable=False)
    description_2 = Column(String, nullable=False)
    description_3 = Column(String, nullable=False)
    image_1 = Column(String, nullable=False)
    image_2 = Column(String, nullable=False)
    image_3 = Column(String, nullable=False)


class Bookings(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agency_name = Column(String, nullable=False)
    booking_title = Column(String, nullable=False)
    check_in_date = Column(TIMESTAMP, nullable=False)
    check_out_date = Column(TIMESTAMP, nullable=False)
    booking_image = Column(String, nullable=False)
    book_days = Column(String, nullable=False)
    booking_details = Column(String, nullable=False)
    booking_status = Column(Boolean, default=False)

    admin_id = Column(Integer, ForeignKey("admin.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)

    # Relationship
    days = relationship("BookingDays", cascade="all, delete", passive_deletes=True)


class BookingDays(Base):
    __tablename__ = "booking_days"
    id = Column(Integer, primary_key=True, autoincrement=True)
    day_title = Column(String, nullable=False)
    booking_day_images = Column(JSON, nullable=True)
    booking_day_details = Column(String, nullable=False)

    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)

    # Relationship
    events = relationship("BookingDayEvents", cascade="all, delete", passive_deletes=True)

class BookingDayEvents(Base):
    __tablename__ = "booking_day_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String, nullable=False)
    booking_title = Column(String, nullable=False)
    day_number = Column(Integer, nullable=False)
    day_event_images = Column(JSON, nullable=True)
    day_event_details = Column(String, nullable=False)

    booking_days_id = Column(Integer, ForeignKey("booking_days.id", ondelete="CASCADE"), nullable=False)
