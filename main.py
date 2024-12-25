import requests
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import Integer, String
from pathlib import Path

db_name = Path(__file__).parent / 'expense_tracker.db'


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{db_name}'
db.init_app(app)


class ExpenseTracker(db.Model):
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String)
    category = mapped_column(String)
    amount = mapped_column(Integer)


with app.app_context():
    db.create_all()
    print('Created db')


@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    expense_name = request.args.get('name')
    category = request.args.get('category')
    amount = request.args.get('amount')
    data = ExpenseTracker(
        name=expense_name,
        category=category,
        amount=amount
    )
    db.session.add(data)
    db.session.commit()

    return jsonify(
        f'Expense: {expense_name}',
        f'Category: {category}',
        f'Amount: {amount}',
    )


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
    return jsonify(results)


if __name__ == '__main__':
    app.run(port=8000, debug=True)
