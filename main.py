import time
from editor import run_editor
from hunter import fetch_news
from publisher import publish_to_meta


def main():
  print("-" * 62)
  print("      MENJALANKAN TIM REDAKSI OTOMATIS (PYTHON AGENTS)")
  print("-" * 62)

  # 1. Staf Riset mencari berita baru
  fetch_news()
  print("-" * 62)

  # 2. Staf Penulis & Desainer mengolah antrean berita
  run_editor()
  print("-" * 62)

  # 3. Staf Publikasi menayangkan konten siap saji ke Medsos
  publish_to_meta()
  print("-" * 62)
  print("                        SIKLUS TIM SELESAI")
  print("-" * 62)


if __name__ == "__main__":
  print("[MAIN] Bot redaksi otomatis aktif dengan perulangan 2 jam...")
  while True:
    try:
      main()
    except Exception as e:
      print(f"[MAIN LOOP ERROR] {e}")

    # Jeda 2 jam (7200 detik) sebelum siklus berikutnya
    print("[MAIN] Menunggu siklus berikutnya dalam 2 jam...")
    time.sleep(7200)

