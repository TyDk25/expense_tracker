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
from tables import Budget, db, ExpenseTracker
from cls import ExpenseLogger

db_name = Path(__file__).parent / 'expense_tracker.db'


# TODO: Fix GitHub

class Base(DeclarativeBase):
    pass


load_dotenv('.env')
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{db_name}'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.json.sort_keys = False
db.init_app(app)

with app.app_context():
    db.create_all()
    category_spent = db.session.query(ExpenseTracker.category, func.sum(ExpenseTracker.amount)).group_by(
        ExpenseTracker.category).order_by(desc(func.sum(ExpenseTracker.amount))).all()
    results = "\n".join([f"{category}: {amount}" for category, amount in category_spent]).title()
    print(results)


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


def prompt_menu(dict_, key, resp):
    dict_[key] = 1
    return resp.message('What would you like to do next?\n'
                        '1. Add Expense\n'
                        '2. Get Budget\n'
                        '3. Set Budget\n'
                        '4. Exit'
                        )


@app.route("/sms", methods=['GET', 'POST'])
def incoming_sms():
    tracker = ExpenseLogger()
    print(tracker.session['track_flow'])
    tracker.prompt_menu()
    tracker.add_expense()
    tracker.get_budget()
    tracker.set_budget()
    tracker.get_category_spent()
    tracker.exit()

    return tracker.send_response()


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
