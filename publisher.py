import sqlite3
import time
import requests
from config import IG_USER_ID, ACCESS_TOKEN
from database import DB_NAME


def wait_for_media_processing(creation_id):
    """Menunggu server Instagram selesai memproses video Reels"""
    status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={ACCESS_TOKEN}"
    while True:
        try:
            res = requests.get(status_url).json()
            status = res.get("status_code")
            print(f"[PUBLISHER] Status pemrosesan video Reels: {status}")
            
            if status == "FINISHED":
                return True
            elif status == "ERROR" or status == "EXPIRED":
                print(f"[PUBLISHER ERROR] Gagal memproses video di server IG: {res}")
                return False
        except Exception as e:
            print(f"[PUBLISHER ERROR] Exception saat cek status: {e}")
        
        time.sleep(10)


def publish_to_meta():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, github_url, caption, media_type FROM content_queue WHERE status = 'ready' LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        print("[PUBLISHER] Tidak ada konten berstatus 'ready' untuk dipublikasikan.")
        return

    news_id, github_url_data, caption, media_type = row

    # Fallback deteksi media_type jika kolom kosong
    if not media_type:
        media_type = "reels" if github_url_data.endswith(".mp4") else "carousel"

    print(f"[PUBLISHER] Mempublikasikan Konten ID {news_id} dengan format: {media_type.upper()}")

    try:
        creation_id = None

        # ==========================================
        # FORMAT REELS (VIDEO MP4 TUNGGAL)
        # ==========================================
        if media_type == "reels":
            container_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
            payload = {
                "media_type": "REELS",
                "video_url": github_url_data,
                "caption": caption,
                "access_token": ACCESS_TOKEN,
            }
            res = requests.post(container_url, data=payload).json()
            
            if "id" in res:
                creation_id = res["id"]
                print(f"[PUBLISHER] Container Reels berhasil dibuat (ID: {creation_id}). Menunggu proses Instagram...")
                
                # Tunggu video selesai diproses oleh Instagram
                if not wait_for_media_processing(creation_id):
                    return
            else:
                print(f"[PUBLISHER ERROR] Gagal membuat container Reels: {res}")
                return

        # ==========================================
        # FORMAT CAROUSEL (MULTIPLE GAMBAR)
        # ==========================================
        else:
            image_urls = [url.strip() for url in github_url_data.split(",")]
            child_container_ids = []
            
            for img_url in image_urls:
                container_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
                payload = {
                    "image_url": img_url,
                    "is_carousel_item": "true",
                    "access_token": ACCESS_TOKEN,
                }
                res = requests.post(container_url, data=payload).json()
                if "id" in res:
                    child_container_ids.append(res["id"])
                else:
                    print(f"[PUBLISHER ERROR] Gagal membuat item carousel: {res}")
                    return

            creation_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
            carousel_payload = {
                "media_type": "CAROUSEL",
                "caption": caption,
                "children": ",".join(child_container_ids),
                "access_token": ACCESS_TOKEN,
            }
            carousel_res = requests.post(creation_url, data=carousel_payload).json()
            
            if "id" in carousel_res:
                creation_id = carousel_res["id"]
            else:
                print(f"[PUBLISHER ERROR] Gagal membuat induk carousel: {carousel_res}")
                return

        # ==========================================
        # PUBLISH KE INSTAGRAM
        # ==========================================
        if creation_id:
            publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": ACCESS_TOKEN,
            }
            publish_res = requests.post(publish_url, data=publish_payload).json()

            if "id" in publish_res:
                print(f"[PUBLISHER] Sukses menerbitkan {media_type.upper()} ke Instagram! ID Post: {publish_res['id']}")
                
                # Update status database menjadi 'published'
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE content_queue SET status = 'published' WHERE id = ?",
                    (news_id,),
                )
                conn.commit()
                conn.close()
            else:
                print(f"[PUBLISHER ERROR] Gagal publikasi ke IG: {publish_res}")

    except Exception as e:
        print(f"[PUBLISHER ERROR] Exception: {e}")

    print(f"[PUBLISHER] Proses publikasi Konten ID {news_id} selesai.")


if __name__ == "__main__":
    publish_to_meta()