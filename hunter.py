import feedparser
from database import add_new_news

# Daftar target RSS Feed (Situs berita terkini)
TARGET_RSS_FEEDS = [
    "https://id.wikipedia.org/w/index.php?title=Istimewa:Perubahan_terbaru&feed=rss"
]

# Kata kunci penyaring konten
KEYWORDS = [""]


def fetch_news():
  print("[HUNTER] Memulai pencarian berita terbaru...")
  count = 0

  for feed_url in TARGET_RSS_FEEDS:
    try:
      feed = feedparser.parse(feed_url)
      for entry in feed.entries[:1]:  # Ambil 1 berita teratas dari tiap feed
        title = entry.title
        link = entry.link
        summary = getattr(entry, "summary", title)

        # Cek apakah judul atau ringkasan mengandung kata kunci
        combined_text = (title + " " + summary).lower()
        if any(kw in combined_text for kw in KEYWORDS):
          add_new_news(title, link, summary)
          count += 1
          print(f"[HUNTER] Berita ditemukan & disimpan: {title}")

    except Exception as e:
      print(f"[HUNTER ERROR] Gagal membaca feed {feed_url}: {e}")

  print(f"[HUNTER] Selesai. Total berita baru disimpan: {count}")


if __name__ == "__main__":
  fetch_news()
