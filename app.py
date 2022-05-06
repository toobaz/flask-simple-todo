from flask import Flask, request, flash, Markup
from flask import render_template
from flask import redirect
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.secret_key = b'notsosecret'
db = SQLAlchemy(app)

HOME = redirect('/')

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


db.create_all()


@app.route('/')
def tasks_list():
    tasks = (Task.query.filter_by(deleted=False)
                            .order_by(Task.done, -Task.pos)
                            .all())
    return render_template('list.html', tasks=tasks)


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

application = app

if __name__ == '__main__':
    app.run()
