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


@app.route('/update_expense/<int:id>', methods=['GET', 'POST'])
def update_expense(id):
    expense_to_update = ExpenseTracker.query.get_or_404(id)
    if request.method == 'POST':
        expense_to_update.name = request.args.get('name', expense_to_update.name)
        expense_to_update.category = request.args.get('category', expense_to_update.category)
        expense_to_update.amount = request.args.get('amount', expense_to_update.amount)

        db.session.commit()

        return jsonify(
        f'Expense: {expense_to_update.name}',
        f'Category: {expense_to_update.category}',
        f'Amount: {expense_to_update.amount}',
    )

@app.route('/delete_expense/<int:id>', methods=['DELETE'])
def delete_expense(id):
    expense_to_delete = ExpenseTracker.query.get_or_404(id)
    if request.method == 'DELETE':
        db.session.delete(expense_to_delete)
        db.session.commit()

    return jsonify(f'{expense_to_delete.name} expense deleted successfully!')

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
