import sqlite3


def connection(database: str):
    return sqlite3.connect(database)


def cursor(connection: sqlite3.Connection):
    return connection.cursor()


def execute(cursor: sqlite3.Cursor, query: str, params: tuple):
    return cursor.execute(query, params)

def upsert():
	import sqlite3
	create = '''CREATE TABLE "wallet" (
		"id"                INTEGER NOT NULL UNIQUE,
		"pubkey"        CHAR(66) NOT NULL UNIQUE,
		"address"       CHAR(34) NOT NULL,
		"cpu"           INTEGER,
		"disk"          INTEGER,
		"ram"           INTEGER,
		"bandwidth"     INTEGER,
		"ts"            DATETIME DEFAULT(STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')) NOT NULL,
		PRIMARY KEY("id" AUTOINCREMENT));'''
	conn = sqlite3.connect('db.sqlite')
	cur = conn.cursor()
	x = cur.executescript(create)
	insert = '''INSERT INTO "wallet" ("pubkey", "address", "cpu") VALUES (?, ?, ?);'''
	values = ('pubkey', 'address', 1)
	x = cur.execute(insert, values)

	upsert = '''INSERT INTO "wallet" ("pubkey", "address", "cpu") VALUES (?, ?, ?) ON CONFLICT("pubkey") DO UPDATE SET address=?, cpu=? WHERE pubkey = ?;'''
	uvalues = ('pubkey', 'address', 2, 'address', 2, 'pubkey')
	x = cur.execute(upsert, uvalues)
