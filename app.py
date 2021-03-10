from flask import Flask, request
from flask import render_template
from flask import redirect
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

HOME = redirect('/')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    done = db.Column(db.Boolean, default=False)
    pos = db.Column(db.Integer, unique=True)
    created = db.Column(db.DateTime)

    def __init__(self, content, pos):
        self.content = content
        self.done = False
        self.pos = pos
        self.created = datetime.now()

    def __repr__(self):
        return '<Content %s>' % self.content


db.create_all()


@app.route('/')
def tasks_list():
    tasks = Task.query.order_by(Task.pos).all()
    return render_template('list.html', tasks=tasks)


@app.route('/task', methods=['POST'])
def add_task():
    content = request.form['content']
    if not content:
        return 'Error'

    task = Task(content, pos=len(Task.query.all())+1)
    db.session.add(task)
    db.session.commit()
    return HOME


@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return redirect('/')
    pos = task.pos
    db.session.delete(task)
    for oth in Task.query.filter(Task.pos > pos).all():
        oth.pos -= 1
    db.session.commit()
    return HOME


@app.route('/done/<int:task_id>')
def resolve_task(task_id):
    task = Task.query.get(task_id)

    if not task:
        return redirect('/')
    if task.done:
        task.done = False
    else:
        task.done = True

    db.session.commit()
    return HOME

def swap_pos(task, other):
    pos = task.pos, other.pos
    # Avoid duplicate pos ( https://stackoverflow.com/q/9109915/2858145 ):
    task.pos, other.pos = -2, -3
    db.session.flush()
    other.pos, task.pos = pos
    db.session.commit()

@app.route('/up/<int:task_id>')
def move_up(task_id):
    task = Task.query.get(task_id)
    if not task:
        return HOME

    oth = Task.query.filter_by(pos=task.pos - 1).first()
    if oth:
        swap_pos(task, oth)
    return HOME

@app.route('/down/<int:task_id>')
def move_down(task_id):
    task = Task.query.get(task_id)
    if not task:
        return HOME

    oth = Task.query.filter_by(pos=task.pos + 1).first()
    if oth:
        swap_pos(task, oth)
    return HOME

application = app

if __name__ == '__main__':
    app.run()
