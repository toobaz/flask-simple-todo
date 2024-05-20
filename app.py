from flask import Flask, request, flash, Markup
from flask import render_template
from flask import redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
import os
import sys
sys.path.append(os.path.dirname(__file__))

try:
    from config import HOME_PATH
except (NameError, ModuleNotFoundError):
    HOME_PATH = '/'

try:
    from config import SECRET_KEY
except (NameError, ModuleNotFoundError):
    SECRET_KEY = b'notsosecret'

from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.secret_key = SECRET_KEY
db = SQLAlchemy(app)

HOME = redirect(HOME_PATH)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    done = db.Column(db.Boolean, default=False)
    pos = db.Column(db.Integer)
    created = db.Column(db.DateTime)
    deleted = db.Column(db.Boolean, default=False)

    def __init__(self, content, pos):
        self.content = content
        self.done = False
        self.pos = pos
        self.created = datetime.now()

    def __repr__(self):
        return '<Content %s>' % self.content


with app.app_context():
    db.create_all()


@app.route('/')
def tasks_list():
    tasks = (Task.query.filter_by(deleted=False, done=False)
                       .order_by(Task.done, -Task.pos))
    cond = (tasks.filter(Task.pos < 0)
                 .filter_by(done=False)
                 .order_by(Task.pos)).all()
    if len(cond):
        tasks = tasks.filter(or_((Task.pos > 0), Task.done))
    else:
        cond = False
    return render_template('list.html', tasks=tasks.all(), cond=cond,
                           done=False)

@app.route('/completed')
def tasks_list_done():
    tasks = (Task.query.filter_by(deleted=False, done=True)
                       .order_by(Task.done, -Task.pos))
    cond = (tasks.filter(Task.pos < 0)
                 .filter_by(done=True)
                 .order_by(Task.pos)).all()
    if len(cond):
        tasks = tasks.filter(or_((Task.pos > 0), Task.done))
    else:
        cond = False
    return render_template('list.html', tasks=tasks.all(), cond=cond,
                           done=True)


@app.route('/task', methods=['POST'])
def add_task():
    content = request.form['content']
    if not content:
        return 'Error'

    todo = Task.query.filter_by(done=False).order_by(-Task.pos)
    shift = min(int(request.form['shift'])-1, todo.count())

    if shift == 0:
        task = Task(content, pos=len(Task.query.all())+1)
    else:
        last_to_shift = (todo.limit(shift)
                             # Required for a "limit" followed by a "order_by"
                             .from_self()
                             .order_by(Task.pos)
                             .first())


        to_shift = Task.query.filter(Task.pos >= last_to_shift.pos)

        for oth in to_shift:
            oth.pos += 1

        task = Task(content, pos=to_shift[0].pos - 1)


    db.session.add(task)
    db.session.commit()

    flash(Markup(f'<b>Added</b> task <em>{task.content}</em>'))
    return HOME


@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return redirect('/')

    msg = f'<b>Deleted</b> task <em>{task.content}</em>'
    pos = task.pos
    task.deleted = True
    for oth in Task.query.filter(Task.pos > pos).all():
        oth.pos -= 1
    db.session.commit()

    flash(Markup(msg))

    return HOME


@app.route('/done/<int:task_id>')
def resolve_task(task_id):
    task = Task.query.get(task_id)

    if not task:
        return redirect('/')
    if task.done:
        update = 'todo'
        task.done = False
    else:
        update = 'done'
        task.done = True

    if task.pos < 0:
        task.pos = -task.pos

    db.session.commit()

    flash(Markup(f'Marked task <em>{task.content}</em> as <b>{update}</b>'))
    return HOME

def swap_pos(task, other):
    other.pos, task.pos = task.pos, other.pos
    db.session.commit()

@app.route('/up/<int:task_id>')
def move_up(task_id):
    task = Task.query.get(task_id)
    if not task:
        return HOME

    oth = (Task.query.filter((Task.pos > task.pos) & (Task.done == task.done))
                     .order_by(Task.pos)
                     .first())
    if oth:
        swap_pos(task, oth)
        flash(Markup(f'Moved task <em>{task.content}</em> <b>up</b>'))

    return HOME

@app.route('/down/<int:task_id>')
def move_down(task_id):
    task = Task.query.get(task_id)
    if not task:
        return HOME

    oth = (Task.query.filter((Task.pos < task.pos) & (Task.done == task.done))
                     .order_by(-Task.pos)
                     .first())
    if oth:
        swap_pos(task, oth)
        flash(Markup(f'Moved task <em>{task.content}</em> <b>down</b>'))

    return HOME

@app.route('/condition/<int:task_id>')
def condition(task_id):
    task = Task.query.get(task_id)
    if not task:
        return HOME

    task.pos = -task.pos
    db.session.commit()
    flash(Markup(f'Changed <b>conditioned</b> state of task <em>{task.content}</em>'))

    return HOME

@app.route('/edit/<int:task_id>')
def edit_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return HOME
    return render_template('edit.html', task=task)

@app.route('/edit/done/<int:task_id>', methods=['POST'])
def edited_task(task_id):
    content = request.form['content']
    if not content:
        return 'Error'

    task = Task.query.get(task_id)
    if not task:
        return 'Error'

    task.content = content

    db.session.add(task)
    db.session.commit()

    flash(Markup(f'<b>Task description changed</b> to <em>{task.content}</em>'))
    return HOME

application = app


@app.template_filter('get_classes')
def format_tags_filter(task):
    classes = []
    if task.done:
        classes.append("done")
    if task.content.startswith("{p}"):
        classes.append("project")
    return " ".join(classes)

if __name__ == '__main__':
    app.run()
