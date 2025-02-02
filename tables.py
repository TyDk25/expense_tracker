import requests
import sqlalchemy
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, mapped_column, Session
from sqlalchemy import Integer, String, func, Float
from pathlib import Path
from datetime import datetime
from twilio.twiml.messaging_response import MessagingResponse
import os
import asyncio
from dotenv import load_dotenv
import time


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

class ExpenseTracker(db.Model):
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    name = mapped_column(String, nullable=False)
    category = mapped_column(String, nullable=False)
    amount = mapped_column(Integer, nullable=False)
    date = mapped_column(db.Date)


class Budget(db.Model):
    __tablename__ = 'budget'
    id = mapped_column(Integer, autoincrement=True, primary_key=True, default=1)
    budget = mapped_column(Float, nullable=True)
    remaining_budget = mapped_column(Float, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('id', name='unique_record_constraint'),
    )


