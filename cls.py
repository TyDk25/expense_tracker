import requests
import sqlalchemy
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, mapped_column, Session
from sqlalchemy import Integer, String, func, Float, desc, asc
from pathlib import Path
from datetime import datetime
from twilio.twiml.messaging_response import MessagingResponse
import os
import asyncio
from dotenv import load_dotenv
import time
from tables import Budget, ExpenseTracker, db


class ExpenseLogger:
    def __init__(self):
        self.body = request.values.get('Body', None)
        self.budget = Budget.query.first()
        self.session = session
        self.resp = MessagingResponse()
        self.budget_tb = Budget()

        if 'track_flow' not in self.session or self.session.get('track_flow') is None:
            self.session['track_flow'] = 0

        if 'expense' not in self.session:
            self.session['expense'] = {}

    def prompt_menu(self):
        if self.session['track_flow'] == 0:
            if self.body.lower() == 'hello':
                self.session['track_flow'] = 1
                return self.resp.message('Hello! What would you like to do?\n'
                                         '1. Add Expense\n'
                                         '2. Get Budget\n'
                                         '3. Set Budget\n'
                                         '4. Exit\n'
                                         '5. Get Category'
                                         )
            else:
                return self.resp.message('Start me by saying hello!')

    def return_to_main(self):
        self.session['track_flow'] = 1

        return self.resp.message('What would you like to do next?\n'
                                 '1. Add Expense\n'
                                 '2. Get Budget\n'
                                 '3. Set Budget\n'
                                 '5. Get Category\n'
                                 '6. Exit\n'
                                 )

    def add_expense(self):
        if self.session['track_flow'] == 1:
            if self.body == '1' or self.body.lower() == 'add expense':
                self.session['track_flow'] = 2
                self.resp.message('What is the name of the expense?')
                return str(self.resp)

        elif self.session['track_flow'] == 2:
            self.session['track_flow'] = 3
            self.session['expense']['name'] = self.body
            return self.resp.message('What is the category of the expense?')

        elif self.session['track_flow'] == 3:
            self.session['track_flow'] = 4
            self.session['expense']['category'] = self.body
            self.resp.message('What is the amount of this expense?')

        elif self.session['track_flow'] == 4:
            self.session['expense']['amount'] = self.body

            expense_data = ExpenseTracker(
                name=self.session['expense'].get('name'),
                category=self.session['expense'].get('category'),
                amount=self.session['expense'].get('amount'),
                date=datetime.today()
            )

            if self.budget.remaining_budget >= float(self.session['expense'].get('amount')):
                budget_after_expense = self.budget.remaining_budget - float(self.session['expense'].get('amount'))
                self.budget.remaining_budget = budget_after_expense

                db.session.add(expense_data)
                db.session.commit()
                self.resp.message(
                    f"Expense Added Successfully To DB:\n"
                    f"Name: {self.session['expense'].get('name').title()}\n"
                    f"Category: {self.session['expense'].get('category').title()}\n"
                    f"Amount: {self.session['expense'].get('amount')}\n"
                    f"Remaining Budget: {budget_after_expense}"
                )

                self.return_to_main()

            else:
                self.resp.message('You do not have the budget for this expense!\n'
                                  f'Your Remaining Budget: {self.budget.remaining_budget}\n'
                                  f'The amount of the expense: {session["expense"].get("amount")}\n'

                                  f'Please Update Budget!'
                                  )

                self.return_to_main()

    def get_budget(self):
        if self.session['track_flow'] == 1:
            if self.body == '2' or self.body.lower() == 'get budget':
                session['budget'] = self.budget.budget
                session['remaining_budget'] = self.budget.remaining_budget
                self.resp.message(
                    f"Your budget is: {self.session.get('budget')}\n"
                    f"Your Remaining Budget Is: {self.session.get('remaining_budget')}"
                )
                self.return_to_main()

    def set_budget(self):
        if self.session['track_flow'] == 1:
            if self.body == '3' or self.body.lower() == 'set budget':
                self.session['track_flow'] = 5
                return self.resp.message('What budget would you like to set?')

        if self.session['track_flow'] == 5:
            try:
                amount = float(self.body)

                if self.budget:
                    self.budget.budget = amount
                    self.budget.remaining_budget = amount

                    db.session.commit()
                    self.resp.message(f'New Budget Set: {self.budget.budget}\n'
                                      f'Remaining Budget: {self.budget.remaining_budget}')
                    self.return_to_main()

            except ValueError as e:
                self.resp.message(
                    f' Enter a number for the amount: {e.__str__()}'
                )

    def get_category_spent(self):
        if session['track_flow'] == 1:
            if self.body == '5' or self.body.lower() == 'get category':
                self.session['track_flow'] = 99

                category_spent = (
        db.session.query(ExpenseTracker.category, func.coalesce(func.sum(ExpenseTracker.amount), 0))
        .group_by(ExpenseTracker.category)
        .order_by(desc(func.sum(ExpenseTracker.amount)))
        .all()
    )

                category_totals = {}
                for category, amount in category_spent:
                    if category in category_totals:
                        category_totals[category] += amount
                    else:
                        category_totals[category] = amount

                results = "\n".join([f"{category}: {amount:,.2f}" for category, amount in category_totals.items()]).title()

                self.resp.message(f'Most Expensive Categories\n {results}')

                self.return_to_main()

    def exit(self):
        if self.session['track_flow'] == 1:
            if self.body == '6' or self.body.lower() == 'exit':
                self.session.clear()
                self.resp.message('Goodbye!')

    def handle_methods(self):
        if session['track_flow'] == 0:
            self.prompt_menu()
        if session['track_flow'] == 1:
            self.add_expense()

    def send_response(self):
        return str(self.resp)
