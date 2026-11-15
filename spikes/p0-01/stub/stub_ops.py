# Throwaway spike code (task 1.7). Never imported by application code.
"""Stub store: create_task and propose_schedule persist a row in SQLite and return an id."""
import os, sqlite3, uuid
DB = os.environ.get("STUB_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "stub.db"))
def _con():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, title TEXT, instructions TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS schedules(id TEXT PRIMARY KEY, title TEXT, cadence TEXT, instructions TEXT, status TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)")
    return c
def create_task(title, instructions=""):
    i = "task-" + uuid.uuid4().hex[:8]
    with _con() as c: c.execute("INSERT INTO tasks(id,title,instructions) VALUES(?,?,?)", (i, title, instructions))
    return i
def propose_schedule(title, cadence, instructions=""):
    i = "sched-" + uuid.uuid4().hex[:8]
    with _con() as c: c.execute("INSERT INTO schedules(id,title,cadence,instructions,status) VALUES(?,?,?,?,'proposed')", (i, title, cadence, instructions))
    return i
