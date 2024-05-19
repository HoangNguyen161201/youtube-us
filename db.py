import sqlite3

def connect_db():
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS links 
                    (id INTEGER PRIMARY KEY, url TEXT)''')

    conn.commit()
    conn.close()



def check_link_exists(url):
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM links WHERE url=?", (url,))
    
    result = cursor.fetchone()

    conn.close()

    if result:
        return True
    else:
        return False
    

def insert_link(url):
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()

    cursor.execute("INSERT INTO links (url) VALUES (?)", (url,))
    conn.commit()
    conn.close()

def delete_link(url):
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM links WHERE url=?", (url,))
    conn.commit()
    conn.close()