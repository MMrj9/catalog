import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy import DateTime
from flask.ext.login import UserMixin

Base = declarative_base()


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_date = Column(DateTime)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
        }


class User(Base, UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    tokens = Column(String(300))


class Product(Base):
    __tablename__ = 'product'

    name = Column(String(100), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(300))
    price = Column(String(8))
    created_by_id = Column(Integer, ForeignKey('users.id'))
    created_date = Column(DateTime)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category.id,
        }

engine = create_engine('sqlite:///catalog.db')

Base.metadata.create_all(engine)
