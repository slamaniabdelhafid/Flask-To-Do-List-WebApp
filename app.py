from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
# It's better to set a fixed secret key for development
app.config["SECRET_KEY"] = "a_very_secret_key" 
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- Models (No changes here) ---
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(7), default="#3498db")
    
    def __repr__(self):
        return f"<Category {self.name}>"

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Integer, default=0)
    pub_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.Integer, default=1)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    category = db.relationship('Category', backref=db.backref('todos', lazy=True))
    
    
    def __repr__(self):
        return f"<Task {self.id}>"

# --- Routes ---

@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        task_content = request.form["task"]
        category_id = request.form.get("category")
        priority = int(request.form.get("priority", 1))
        due_date_str = request.form.get("due_date")
        
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "error")
                return redirect("/")
        
        new_task = Todo(
            content=task_content,
            category_id=category_id if category_id else None,
            priority=priority,
            due_date=due_date
        )
        
        try:
            db.session.add(new_task)
            db.session.commit()
            flash("Task added successfully!", "success")
            return redirect("/")
        except Exception as e:
            db.session.rollback()
            flash(f"There was an issue adding your task: {str(e)}", "error")
            return redirect("/")
    else:
        # Get filter parameters
        category_filter = request.args.get("category", "all")
        completed_filter = request.args.get("completed", "all")
        
        # Build query based on filters
        query = Todo.query
        
        if category_filter != "all":
            query = query.filter_by(category_id=category_filter)
            
        if completed_filter != "all":
            completed_value = 1 if completed_filter == "completed" else 0
            query = query.filter_by(completed=completed_value)
            
        tasks = query.order_by(Todo.priority.desc(), Todo.due_date.asc().nullslast(), Todo.pub_date.desc()).all()
        categories = Category.query.all()
        
        return render_template(
            "index.html", 
            tasks=tasks, 
            categories=categories,
            category_filter=category_filter,
            completed_filter=completed_filter
        )

@app.route("/delete/<int:id>")
def delete(id):
    task_to_delete = Todo.query.get_or_404(id)
    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        flash("Task deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"There was a problem deleting the task: {str(e)}", "error")
    return redirect("/")

@app.route("/update/<int:id>", methods=["POST", "GET"])
def update(id):
    task_to_update = Todo.query.get_or_404(id)
    if request.method == "POST":
        task_to_update.content = request.form["task"]
        task_to_update.category_id = request.form.get("category") or None
        task_to_update.priority = int(request.form.get("priority", 1))
        
        due_date_str = request.form.get("due_date")
        if due_date_str:
            try:
                task_to_update.due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "error")
                return redirect(request.referrer)
        else:
            task_to_update.due_date = None

        try:
            db.session.commit()
            flash("Task updated successfully!", "success")
            return redirect("/")
        except Exception as e:
            db.session.rollback()
            flash(f"There was an issue updating your task: {str(e)}", "error")
            return redirect(request.referrer)
    else:
        # *** FIX IS HERE ***
        # Get filter parameters to maintain state on the page
        category_filter = request.args.get("category", "all")
        completed_filter = request.args.get("completed", "all")
        
        # Build query to display the list of tasks correctly
        query = Todo.query
        if category_filter != "all":
            query = query.filter_by(category_id=category_filter)
        if completed_filter != "all":
            completed_value = 1 if completed_filter == "completed" else 0
            query = query.filter_by(completed=completed_value)
        
        tasks = query.order_by(Todo.priority.desc(), Todo.due_date.asc().nullslast(), Todo.pub_date.desc()).all()
        categories = Category.query.all()
        
        return render_template(
            "index.html", 
            update_task=task_to_update, 
            tasks=tasks,
            categories=categories,
            # Pass the filter variables to the template
            category_filter=category_filter,
            completed_filter=completed_filter
        )

@app.route("/toggle/<int:id>", methods=['POST'])
def toggle_complete(id):
    task_to_toggle = Todo.query.get_or_404(id)
    try:
        task_to_toggle.completed = 1 if task_to_toggle.completed == 0 else 0
        db.session.commit()
        return jsonify({"success": True, "completed": task_to_toggle.completed})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})

@app.route("/add_category", methods=["POST"])
def add_category():
    name = request.form.get("name")
    color = request.form.get("color", "#3498db")
    
    if not name:
        flash("Category name is required!", "error")
        return redirect("/")
    
    try:
        new_category = Category(name=name, color=color)
        db.session.add(new_category)
        db.session.commit()
        flash("Category added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"There was an issue adding the category: {str(e)}", "error")
    
    return redirect("/")

# --- Main execution ---
with app.app_context():
    db.create_all()
    if Category.query.count() == 0:
        default_categories = [
            Category(name="Personal", color="#3498db"),
            Category(name="Work", color="#e74c3c"),
            Category(name="Shopping", color="#2ecc71"),
            Category(name="Health", color="#f39c12"),
            Category(name="Other", color="#9b59b6")
        ]
        db.session.add_all(default_categories)
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)