import requests
import sqlalchemy
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import Integer, String, func, Float
from pathlib import Path
from datetime import datetime

db_name = Path(__file__).parent / 'expense_tracker.db'


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{db_name}'
db.init_app(app)


class ExpenseTracker(db.Model):
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String, nullable=False)
    category = mapped_column(String, nullable=False)
    amount = mapped_column(Integer, nullable=False)
    date = mapped_column(db.Date)


class Budget(db.Model):
    __tablename__ = 'budget'
    id = mapped_column(Integer, primary_key=True, default=1)
    budget = mapped_column(Float, nullable=False)
    remaining_budget = mapped_column(Float, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('id', name='unique_record_constraint'),
    )


with app.app_context():
    db.create_all()
    print('Created db')

@app.route('/set_budget', methods=['POST'])
def set_budget():
    total_budget = request.args.get('budget', 0)
    data = Budget(
        budget=total_budget,
        remaining_budget=total_budget
    )

    db.session.add(data)

    db.session.commit()

    return jsonify({
        "Total Budget": total_budget,
        "Remaining Budget": total_budget

    })
@app.route('/get_budget', methods=['GET'])
def total_budget():
    total_budget = request.args.get('budget')
    return jsonify(total_budget)


@app.route('/remaining_budget', methods=['GET'])
def remaining_budget():
    budget = total_budget().get_json()['budget']
    total_spent = get_total_spent().get_json()['Total Spent']
    remaining_left = budget - total_spent

    return jsonify(remaining_left)


@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    expense_name = request.args.get('name').title()
    category = request.args.get('category').title()
    amount = request.args.get('amount').title()
    now = datetime.today()
    data = ExpenseTracker(
        name=expense_name,
        category=category,
        amount=amount,
        date=now
    )
    db.session.add(data)
    db.session.commit()

    return jsonify(
        f'Expense: {expense_name}',
        f'Category: {category}',
        f'Amount: {amount}',
        f'Date: {now.date()}'
    )


@app.route('/update_expense/<int:id>', methods=['GET', 'POST'])
def update_expense(id):
    expense_to_update = ExpenseTracker.query.get_or_404(id)
    if request.method == 'POST':
        expense_to_update.name = request.args.get('name', expense_to_update.name).title()
        expense_to_update.category = request.args.get('category', expense_to_update.category).title()
        expense_to_update.amount = request.args.get('amount', expense_to_update.amount)

        db.session.commit()

        return jsonify(
            f'Expense: {expense_to_update.name}',
            f'Category: {expense_to_update.category}',
            f'Amount: {expense_to_update.amount}'
        )


@app.route('/delete_expense/<int:id>', methods=['DELETE'])
def delete_expense(id):
    expense_to_delete = ExpenseTracker.query.get_or_404(id)
    if request.method == 'DELETE':
        db.session.delete(expense_to_delete)
        db.session.commit()

    return jsonify(f'{expense_to_delete.name} expense deleted successfully!')


@app.route('/check_categories/<string:category>', methods=['POST'])
def check_categories(category):
    category_to_check = db.session.query(func.sum(ExpenseTracker.amount)).filter(
        ExpenseTracker.category == category
    ).scalar()

    return jsonify(f'Amount Spent on {category}: {category_to_check}')


@app.route('/expensive_category', methods=['POST'])
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
    return jsonify(results)


@app.route('/get_total_spend', methods=['GET'])
def get_total_spent():
    total_spent = db.session.query(func.sum(ExpenseTracker.amount).label('total_spent')).all()

    results = [
        {
            "Total Spent": i.total_spent
        }
        for i in total_spent
    ]

    return jsonify(results)

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


@app.route('/clear_table', methods=['DELETE'])
def clear_data():
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()

    return jsonify('Data cleared')


if __name__ == '__main__':
    app.run(port=8000, debug=True)
