import sqlite3

DB_NAME = "editorial_team.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabel untuk antrean konten (ditambah kolom media_type)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            source_url TEXT,
            raw_content TEXT,
            caption TEXT,
            image_path TEXT,
            github_url TEXT,
            media_type TEXT DEFAULT 'carousel',
            status TEXT DEFAULT 'new'
        )
    """)

    # Tabel untuk mencatat komentar yang sudah dibalas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS replied_comments (
            comment_id TEXT PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()


def add_new_news(title, source_url, raw_content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO content_queue (title, source_url, raw_content, status) VALUES (?, ?, ?, 'new')",
        (title, source_url, raw_content),
    )
    conn.commit()
    conn.close()


def get_pending_news():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, raw_content FROM content_queue WHERE status = 'new' LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    return row


def update_status(news_id, status, github_url=None, caption=None, media_type="carousel"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE content_queue 
        SET status = ?, github_url = ?, caption = ?, media_type = ?
        WHERE id = ?
    """,
        (status, github_url, caption, media_type, news_id),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("[INFO] Database dan tabel berhasil diinisialisasi.")