import sqlite3
from datetime import datetime

DB = "bot.db"

def db():
    return sqlite3.connect(DB)

def init():
    with db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id        INTEGER PRIMARY KEY,
                username  TEXT DEFAULT '',
                name      TEXT DEFAULT '',
                joined    TEXT DEFAULT '',
                banned    INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS movies (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                code        TEXT UNIQUE NOT NULL,
                file_id     TEXT NOT NULL,
                poster_id   TEXT DEFAULT '',
                type        TEXT DEFAULT 'movie',
                year        TEXT DEFAULT '',
                genre       TEXT DEFAULT '',
                duration    TEXT DEFAULT '',
                description TEXT DEFAULT '',
                added       TEXT DEFAULT '',
                views       INTEGER DEFAULT 0,
                likes       INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS liked (
                user_id  INTEGER,
                movie_id INTEGER,
                PRIMARY KEY (user_id, movie_id)
            );
        """)

def save_user(uid, username, name):
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users (id,username,name,joined) VALUES (?,?,?,?)",
                  (uid, username or '', name, datetime.now().strftime("%d.%m.%Y")))

def get_user(uid):
    with db() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def ban(uid):
    with db() as c:
        c.execute("UPDATE users SET banned=1 WHERE id=?", (uid,))

def unban(uid):
    with db() as c:
        c.execute("UPDATE users SET banned=0 WHERE id=?", (uid,))

def all_users():
    with db() as c:
        return c.execute("SELECT * FROM users WHERE banned=0").fetchall()

def stats():
    with db() as c:
        total  = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active = c.execute("SELECT COUNT(*) FROM users WHERE banned=0").fetchone()[0]
        banned = c.execute("SELECT COUNT(*) FROM users WHERE banned=1").fetchone()[0]
        movies = c.execute("SELECT COUNT(*) FROM movies WHERE type='movie'").fetchone()[0]
        serial = c.execute("SELECT COUNT(*) FROM movies WHERE type='serial'").fetchone()[0]
        views  = c.execute("SELECT COALESCE(SUM(views),0) FROM movies").fetchone()[0]
    return total, active, banned, movies, serial, views

def add_movie(title, code, file_id, poster_id, mtype, year, genre, duration, desc):
    try:
        with db() as c:
            c.execute("""INSERT INTO movies
                (title,code,file_id,poster_id,type,year,genre,duration,description,added)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (title, code.upper(), file_id, poster_id, mtype, year, genre, duration, desc,
                 datetime.now().strftime("%d.%m.%Y")))
        return True
    except sqlite3.IntegrityError:
        return False

def get_by_code(code):
    with db() as c:
        r = c.execute("SELECT * FROM movies WHERE code=?", (code.upper(),)).fetchone()
        if r:
            c.execute("UPDATE movies SET views=views+1 WHERE code=?", (code.upper(),))
        return r

def search(q):
    with db() as c:
        return c.execute("SELECT * FROM movies WHERE title LIKE ? LIMIT 8", (f"%{q}%",)).fetchall()

def delete_movie(code):
    with db() as c:
        c.execute("DELETE FROM movies WHERE code=?", (code.upper(),))

def toggle_like(uid, mid):
    with db() as c:
        exists = c.execute("SELECT 1 FROM liked WHERE user_id=? AND movie_id=?", (uid, mid)).fetchone()
        if exists:
            c.execute("DELETE FROM liked WHERE user_id=? AND movie_id=?", (uid, mid))
            c.execute("UPDATE movies SET likes=likes-1 WHERE id=?", (mid,))
            return False
        else:
            c.execute("INSERT INTO liked VALUES (?,?)", (uid, mid))
            c.execute("UPDATE movies SET likes=likes+1 WHERE id=?", (mid,))
            return True

def is_liked(uid, mid):
    with db() as c:
        return bool(c.execute("SELECT 1 FROM liked WHERE user_id=? AND movie_id=?", (uid, mid)).fetchone())

def get_by_id(mid):
    with db() as c:
        return c.execute("SELECT * FROM movies WHERE id=?", (mid,)).fetchone()

def top_movies(limit=5):
    with db() as c:
        return c.execute("SELECT * FROM movies ORDER BY views DESC LIMIT ?", (limit,)).fetchall()
