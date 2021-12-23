from flask import Flask, render_template
import tables
from config import LOGIN_REGISTER_TABLE, GAME_HISTORY_TABLE, QUEUE

app = Flask(__name__)


@app.route("/")
def display_main_page():
    data = tables.get_in_order(QUEUE, fetch='*', order='position DESC')
    return render_template("index.html", queue_len=len(data), rows=data)


@app.route('/history')
def display_history():
    data = tables.get_in_order(GAME_HISTORY_TABLE, fetch='*', order='game_id DESC')
    if data is None:
        return render_template('history.html')
    return render_template('history.html', rows=data)


@app.route('/ranking')
def display_ranking():
    data = tables.get_in_order(LOGIN_REGISTER_TABLE, fetch='user_id, username, score, number_of_games, average_score',
                               order='score DESC')
    if data is None:
        return render_template('ranking.html')
    return render_template('ranking.html', rows=data)


def run_website(q):
    global queue
    queue = q.queue
    app.run(debug=False)
    print('[Server]: Website started')


queue = None

if __name__ == "__main__":
    app.run(debug=True)
