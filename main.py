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

db_name = Path(__file__).parent / 'expense_tracker.db'


# TODO: Fix GitHub

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
load_dotenv('.env')
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{db_name}'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.json.sort_keys = False
db.init_app(app)


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


with app.app_context():
    db.create_all()
    print('Created db')


@app.route('/set_budget', methods=['POST'])
def set_budget():
    total_budget = float(request.args.get('budget'))

    budget = Budget.query.first()

    if budget:
        budget.budget = total_budget
        budget.remaining_budget = total_budget
    else:
        budget = Budget(budget=total_budget, remaining_budget=total_budget)
        db.session.add(budget)

    db.session.commit()

    return jsonify({
        "Total Budget": budget.budget,
        "Remaining Budget": budget.remaining_budget
    }), 200


@app.route('/update_budget', methods=['POST'])
def update_budget():
    updated_budget = float(request.args.get('new budget', 0))
    budget = Budget.query.first()

    if budget:
        budget.budget = updated_budget
        budget.remaining_budget = updated_budget
        db.session.commit()
        return jsonify({
            "Message": 'Budget updated successfully!',
            "Updated Budget": budget.budget
        }), 200

    else:
        return jsonify({"message": "No budget set."}), 404


@app.route('/get_budget', methods=['GET'])
def get_budget(remaining_budget=False, l=False):
    budget = Budget.query.first()
    if budget:
        return jsonify({"Total Budget": budget.budget, 'Remaining Budget': budget.remaining_budget}), 200

    if remaining_budget and budget:
        return db.session.query(Budget.remaining_budget).one()[0]
    else:
        return jsonify({"message": "No Budget Set"}), 404


@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    expense_name = request.args.get('name').title()
    category = request.args.get('category').title()
    amount = float(request.args.get('amount'))
    now = datetime.today()
    data = ExpenseTracker(
        name=expense_name,
        category=category,
        amount=amount,
        date=now
    )
    db.session.add(data)
    budget = Budget.query.first()
    if budget:
        if budget.remaining_budget > 0:
            budget.remaining_budget -= amount
        else:
            return jsonify({"Message": f"Your budget does not allow for this expense!",

                            'Your Remaining Budget':
                                {
                                    'Remaining Budget': budget.remaining_budget,
                                    'Expense price that you want to add': amount
                                }

                            }), 404
    db.session.commit()

    return jsonify({
        'Message': f'Expense {expense_name} added successfully.',
        'Expenses': {
            'Expense': expense_name,
            'Category': category,
            'Amount': amount,
            'Date': now.date(),
            'Remaining Budget': budget.remaining_budget
        }
    }
    ), 200


@app.route('/update_expense/<int:id>', methods=['GET', 'POST'])
def update_expense(id):
    expense_to_update = ExpenseTracker.query.get_or_404(id)
    if request.method == 'POST':
        expense_to_update.name = request.args.get('name', expense_to_update.name).title()
        expense_to_update.category = request.args.get('category', expense_to_update.category).title()
        expense_to_update.amount = request.args.get('amount', expense_to_update.amount)

        db.session.commit()

        return jsonify(
            {
                "message": "Updated Expense",
                "Expense Updated": {
                    "Expense": expense_to_update.name,
                    "Category": expense_to_update.category,
                    "Amount": expense_to_update.amount
                }
            }
        ), 200


@app.route('/delete_expense/<int:id>', methods=['DELETE'])
def delete_expense(id):
    expense_to_delete = ExpenseTracker.query.get_or_404(id)
    if request.method == 'DELETE':
        db.session.delete(expense_to_delete)
        db.session.commit()

    return jsonify({
        'Message': f'{expense_to_delete.name} removed successfully!'
    })


@app.route('/check_categories/<string:category>', methods=['GET'])
def check_categories(category):
    category_to_check = db.session.query(func.sum(ExpenseTracker.amount)).filter(
        ExpenseTracker.category == category
    ).scalar()

    return jsonify({
        f"Amount Spent On {category}": category_to_check
    })


@app.route('/expensive_category', methods=['GET'])
def check_expensive_category():
    expensive = db.session.query(ExpenseTracker.category, func.sum(ExpenseTracker.amount).label('Total')).group_by(
        ExpenseTracker.category).all()
    results = [
        {
            "Category": i.category,
            "Amount": i.Total

        }
        for i in expensive
    ]
    return jsonify({
        "Costly Categories": results
    })


@app.route('/get_total_spend', methods=['GET'])
def get_total_spent():
    total_spent = db.session.query(func.sum(ExpenseTracker.amount).label('total_spent')).all()

    results = [
        {
            "Total Spent": i.total_spent
        }
        for i in total_spent
    ]

    return jsonify({
        "Total Spent": results
    })


@app.route('/get_expenses', methods=['GET', 'POST'])
def get_expenses():
    expenses = ExpenseTracker.query.all()
    results = [
        {
            "Expenses": i.name,
            "Category": i.category,
            "Amount": i.amount

        }
        for i in expenses
    ]
    return jsonify({
        "Expenses": results
    })


def return_to_menu(dict_, key, resp):
            dict_[key] = 1
            return resp.message('1. Add Expense\n'
                                '2. Get Budget\n'
                                '3. Set Budget')



@app.route("/sms", methods=['GET', 'POST'])
def incoming_sms():
    """Send a dynamic reply to an incoming text message"""
    # Get the message the user sent our Twilio number
    body = request.values.get('Body', None)
    current = Budget.query.first()
    if 'track_flow' not in session:
        session['track_flow'] = 0
    print(session['track_flow'])
    if 'expense' not in session:
        session['expense'] = {}
    # TODO: Create a response to when the session state returns to 0.
    # Start our TwiML response
    resp = MessagingResponse()
    if session['track_flow'] == 0:
        if body == 'hello':
            session['track_flow'] = 1
            resp.message('Welcome, Please Choose From The Following:\n'
                         '1. Add Expense\n'
                         '2. Get Budget\n'
                         '3. Set Budget')

    if 'track_flow' in session and session.get('track_flow', 0) == 0:
        resp.message('Would you like to add another bill?')
        session['track_flow'] = 99
        return_to_menu(session, 'track_flow', resp)



    elif session['track_flow'] == 1:
        if body == '1' or body.lower() == 'add expense':
            resp.message('What is the name of the expense?')
            session['track_flow'] = 2




        elif body == '2' or body.lower() == 'get budget':
            session['track_flow'] = 0
            session['expense']['budget'] = current.budget
            session['expense']['remaining_budget'] = current.remaining_budget
            resp.message(f" Your budget is: {session['expense'].get('budget')}\n"
                         f"Your remaining budget is: {session['expense'].get('remaining_budget')}")
            if body[0].lower() == 'y':
                return_to_menu(session, 'track_flow', resp)

        elif body == '3' or body.lower() == 'set budget':
            resp.message('What budget would you like to set?')
            session['track_flow'] = 5


    elif session['track_flow'] == 2:
        resp.message('What is the category?')
        session['expense']['name'] = body
        session['track_flow'] = 3

    elif session['track_flow'] == 3:
        resp.message('What is the amount?')
        session['expense']['category'] = body
        session['track_flow'] = 4

    elif session['track_flow'] == 4:
        try:
            session['expense']['amount'] = float(body)
            data = ExpenseTracker(
                name=session['expense'].get('name'),
                category=session['expense'].get('category'),
                amount=session['expense'].get('amount'),
                date=datetime.today()
            )

            if current.remaining_budget > session['expense'].get('amount', 0):

                current.remaining_budget = current.remaining_budget - session['expense'].get(
                    'amount', 0)

                resp.message(
                    f"Expense Added Successfully To DB:\n"
                    f"Name: {session['expense'].get('name').title()}\n"
                    f"Category: {session['expense'].get('category').title()}\n"
                    f"Amount: {session['expense'].get('amount')}\n"
                    f"Remaining Budget: {current.remaining_budget}"

                )
                db.session.add(data)
                db.session.commit()

            else:
                resp.message('You do not have the budget for this expense!\n'
                             f'Your Remaining Budget: {current.remaining_budget}\n'
                             f'The amount of the expense: {session["expense"].get("amount")}\n'

                             f'Please Update Budget!'
                             )

                session['track_flow'] = 0

            session['track_flow'] = 0
        except ValueError:
            resp.message('Enter A Number')
            session['track_flow'] = 3

    elif session['track_flow'] == 5:
        new_budget = float(body)
        session['track_flow'] = 0

        if current:
            current.budget = new_budget
            current.remaining_budget = new_budget
            db.session.commit()
            resp.message(
                f'New Budget Set: {current.budget}\n'
                f'Remaining Budget: {current.remaining_budget}'
            )
            return_to_menu('track_flow', resp)

    return str(resp)


@app.route('/clear_table', methods=['DELETE'])
def clear_data():
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()

    return jsonify({
        "Message": "Tables Cleared"
    })


if __name__ == '__main__':
    app.run(port=9000, debug=True)
