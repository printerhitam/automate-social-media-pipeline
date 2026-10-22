import sqlite3
import time
import traceback
import requests
from google import genai
from config import ACCESS_TOKEN, IG_USER_ID, GEMINI_API_KEY
from database import DB_NAME

client = genai.Client(api_key=GEMINI_API_KEY)


def setup_responder_table():
  """Membuat tabel khusus untuk melacak komentar yang sudah dibalas"""
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS replied_comments (
            comment_id TEXT PRIMARY KEY
        )
    """)
  conn.commit()
  conn.close()


def generate_ai_reply(comment_text):
  """Meminta Gemini merumuskan balasan komentar yang ramah & edukatif"""
  prompt = f"""
    Anda adalah seorang praktisi homeschooling dan pendidik yang ramah dan islami.
    Seseorang meninggalkan komentar di postingan Instagram Anda:
    "{comment_text}"

    Deteksi bahasa yg dipakai dan jawablah dengan bahasa tersebut. Tuliskan balasan komentar yang hangat, menghargai pendapat mereka, dan relevan dengan dunia pendidikan anak/homeschooling. Jawab secara ringkas (maksimal 2-3 kalimat).
    """
  try:
    # Perbaikan menggunakan SDK resmi google-genai
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )
    return response.text.strip()
  except Exception as e:
    print(f"[RESPONDER ERROR] Gagal memproses Gemini: {e}")
    return None


def check_and_reply_comments():
  setup_responder_table()
  print("[RESPONDER] Memeriksa komentar terbaru di Instagram...")

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()

  try:
    # 1. Ambil daftar media/postingan terakhir Anda
    media_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media?access_token={ACCESS_TOKEN}"
    media_res = requests.get(media_url).json()

    if "data" not in media_res or not media_res["data"]:
      print("[RESPONDER] Tidak ada postingan ditemukan.")
      conn.close()
      return

    # Ambil 8 postingan teratas untuk diperiksa komentarnya
    for post in media_res["data"][:8]:
      media_id = post["id"]

      comments_url = f"https://graph.facebook.com/v19.0/{media_id}/comments?access_token={ACCESS_TOKEN}"
      comments_res = requests.get(comments_url).json()

      if "data" not in comments_res:
        continue

      for comment in comments_res["data"]:
        comment_id = comment["id"]
        comment_text = comment["text"]

        # Cek apakah komentar ini sudah pernah dibalas sebelumnya di database
        cursor.execute(
            "SELECT 1 FROM replied_comments WHERE comment_id = ?", (comment_id,)
        )
        if cursor.fetchone():
          continue  # Lewati jika sudah pernah dibalas

        print(f"[RESPONDER] Menemukan komentar baru: '{comment_text}'")

        # Generate balasan via Gemini
        reply_text = generate_ai_reply(comment_text)
        if reply_text:
          # Kirim balasan ke Instagram
          reply_url = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
          payload = {"message": reply_text, "access_token": ACCESS_TOKEN}
          post_res = requests.post(reply_url, data=payload).json()

          if "id" in post_res:
            print(f"[RESPONDER] Berhasil membalas: {reply_text}")
            # Simpan ID komentar ke database agar tidak dibalas 2x
            cursor.execute(
                "INSERT OR IGNORE INTO replied_comments (comment_id) VALUES"
                " (?)",
                (comment_id,),
            )
            conn.commit()

            # Jeda waktu aman (5 detik) antar balasan agar terlihat natural dan tidak spam
            time.sleep(5)
          else:
            print(f"[RESPONDER ERROR] Gagal mengirim balasan: {post_res}")

  except Exception as e:
    print(f"[RESPONDER ERROR] Terjadi kesalahan: {e}")

  conn.close()
  print("[RESPONDER] Pemeriksaan komentar selesai.")


if __name__ == "__main__":
  print("[RESPONDER] Bot aktif secara otomatis dengan perulangan 15 menit...")
  while True:
    try:
      check_and_reply_comments()
    except Exception as e:
      print(f"[MAIN LOOP ERROR] {e}")
      traceback.print_exc()

    # Jeda 15 menit (900 detik) sebelum siklus pemeriksaan berikutnya
    print("[RESPONDER] Menunggu siklus berikutnya dalam 15 menit...")
    time.sleep(900)
