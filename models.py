from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base

# Define the base class for all the
Base = declarative_base()

class Email(Base):
    __tablename__ = 'email'
    id = Column(Integer, primary_key=True)
    message_id = Column(String(255),default='')
    label = Column(String(64),default='')
    sender = Column(String(255),default='')
    subject = Column(String(255),default='')
    recepient = Column(String(255),default='')
    received_date = Column(DateTime)

    def __repr__(self):
        return f"<(sender={self.sender}, subject={self.subject}, received_date={self.received_date})>"