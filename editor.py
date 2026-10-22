import base64
import json
import os
import re
import tempfile
import time
import textwrap
import sqlite3

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from google import genai
from google.genai import types
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

from config import (
    GEMINI_API_KEY,
    CANVAS_WIDTH,
    CANVAS_HEIGHT,
    GITHUB_TOKEN,
    GITHUB_REPO,
)

from database import get_pending_news, update_status, DB_NAME


# ============================================================
# CONFIG
# ============================================================

client = genai.Client(api_key=GEMINI_API_KEY)

BRANCH = "main"

MODEL_CONTENT = "gemini-3.6-flash"
MODEL_IMAGE = "imagen-3.0-generate-002"

BRAND_NAME = "RUANG HOMESCHOOL"
BRAND_HANDLE = "@ruanghomeschool"

JPEG_QUALITY = 95


# ============================================================
# GITHUB UPLOAD
# ============================================================

def upload_to_github(local_file_path, github_path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{github_path}"
    try:
        with open(local_file_path, "rb") as file:
            content_bytes = file.read()

        base64_content = base64.b64encode(content_bytes).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }

        payload = {
            "message": f"Auto-upload asset {github_path}",
            "content": base64_content,
            "branch": BRANCH,
        }

        response = requests.put(url, json=payload, headers=headers, timeout=120)
        result = response.json()

        if response.status_code in [200, 201]:
            raw_link = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{BRANCH}/{github_path}"
            print(f"[GITHUB] Upload berhasil: {raw_link}")
            return raw_link

        print(f"[GITHUB ERROR] Upload gagal: {result.get('message')}")
        return None

    except Exception as e:
        print(f"[GITHUB ERROR] Exception upload: {e}")
        return None


# ============================================================
# AI CONTENT GENERATOR
# ============================================================

def generate_content_with_ai(title, raw_content, target_mode="carousel"):
    print(f"[AI] Menganalisis berita untuk mode: {target_mode.upper()}...")

    clean_content = raw_content.strip()
    if len(clean_content) > 12000:
        clean_content = clean_content[:12000]

    quran_prompt_rule = ""
    if target_mode == "reels":
        quran_prompt_rule = """
2. Karena formatnya REELS, pilih SATU ayat Al-Qur'an (Nomor Surah & Nomor Ayat) yang relevan untuk dijadikan audio latar belakang tilawah.
"""
    else:
        quran_prompt_rule = "2. Format adalah CAROUSEL gambar biasa, abaikan pemilihan ayat (isi 0)."

    prompt = f"""
Bertindaklah sebagai professional Indonesian education content.

INPUT BERITA:
JUDUL:
{title}
ISI BERITA:
{clean_content}

TUGAS:
1. Analisis berita dan buat konsep carousel Instagram (3 slide) yang disesuaikan dengan informasi yg kamu dapat.{quran_prompt_rule}

ATURAN:
1. Kembalikan HANYA format JSON murni tanpa markdown block.
2. Struktur harus tepat seperti contoh.

STRUKTUR JSON:
{{
  "angle": "Sudut pandang utama",
  "quran_surah": 3,
  "quran_ayah": 190,
  "slides": [
    {{
      "slide": 1,
      "type": "hook",
      "headline": "Teks headline singkat",
      "body": "Teks body penjelasan",
      "highlight": "KATA KUNCI",
      "background_theme": "Tema visual",
      "visual_keywords": ["keyword1"],
      "mood": "Suasana visual"
    }},
    {{
      "slide": 2,
      "type": "insight",
      "headline": "Teks headline",
      "body": "Teks body",
      "highlight": "KATA KUNCI",
      "background_theme": "Tema visual",
      "visual_keywords": ["keyword1"],
      "mood": "Suasana visual"
    }},
    {{
      "slide": 3,
      "type": "reflection_cta",
      "headline": "Teks headline",
      "body": "Teks body",
      "cta": "Teks cta",
      "highlight": "KATA KUNCI",
      "background_theme": "Tema visual",
      "visual_keywords": ["keyword1"],
      "mood": "Suasana visual"
    }}
  ],
  "caption": "Teks caption Instagram lengkap.",
  "hashtags": ["#homeschooling", "#pendidikananak"]
}}
"""

    try:
        response = client.models.generate_content(
            model=MODEL_CONTENT,
            contents=prompt,
            config={"temperature": 0.7, "response_mime_type": "application/json"},
        )

        result_text = response.text.strip()
        result_text = re.sub(r"^```json\s*", "", result_text)
        result_text = re.sub(r"^```\s*", "", result_text)
        result_text = re.sub(r"\s*```$", "", result_text)
        result_text = result_text.strip()

        try:
            data = json.loads(result_text)
        except json.JSONDecodeError:
            cleaned_text = re.sub(r',\s*([\]}])', r'\1', result_text)
            data = json.loads(cleaned_text)

        return data
    except Exception as e:
        print(f"[AI ERROR] Gagal membuat konten: {e}")
        if 'result_text' in locals():
            print(f"[DEBUG] Respon mentah dari AI:\n{result_text}")
        return None




def download_quran_audio(surah, ayah, temp_dir, reciter="Alafasy_128kbps"):
    s_str = str(surah).zfill(3)
    a_str = str(ayah).zfill(3)
    url = f"https://everyayah.com/data/{reciter}/{s_str}{a_str}.mp3"
    audio_path = os.path.join(temp_dir, "quran_audio.mp3")
    
    print(f"[AUDIO] Mengunduh audio ayat dari: {url}")
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(audio_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return audio_path
        return None
    except Exception as e:
        print(f"[AUDIO ERROR] {e}")
        return None


def create_reels_video(slide_paths, audio_path, output_video_path):
    print("[VIDEO] Merakit slide dan audio menjadi Reels...")
    audio_clip = None
    final_video = None
    try:
        audio_clip = AudioFileClip(audio_path)
        total_duration = max(audio_clip.duration, 6.0)
        slide_duration = total_duration / len(slide_paths)
        
        image_clips = [ImageClip(slide, duration=slide_duration) for slide in slide_paths]
        video_sequence = concatenate_videoclips(image_clips, method="compose")
        final_video = video_sequence.with_audio(audio_clip)
        
        final_video.write_videofile(
            output_video_path, fps=24, codec="libx264", audio_codec="aac", preset="medium", logger=None
        )
        return output_video_path
    except Exception as e:
        print(f"[VIDEO ERROR] {e}")
        return None
    finally:
        if final_video:
            try: final_video.close()
            except: pass
        if audio_clip:
            try: audio_clip.close()
            except: pass


def generate_background_image(slide_data, slide_index, temp_dir):
    keywords = ", ".join(slide_data.get("visual_keywords", []))
    prompt = f"Create a vertical 9:16 editorial Instagram background. Theme: {slide_data.get('background_theme', '')}. Keywords: {keywords}. Mood: {slide_data.get('mood', '')}. No text, no logos."
    try:
        response = client.models.generate_images(
            model='imagen-3.0-generate-002', prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="9:16", output_mime_type="image/jpeg")
        )
        output_path = os.path.join(temp_dir, f"background_{slide_index}.jpg")
        with open(output_path, "wb") as f:
            f.write(response.generated_images[0].image.image_bytes)
        return output_path
    except:
        return None


def create_slide_image(slide_data, slide_index, background_path, temp_dir):
    if background_path and os.path.exists(background_path):
        background = resize_cover(Image.open(background_path).convert("RGB"), CANVAS_WIDTH, CANVAS_HEIGHT).filter(ImageFilter.GaussianBlur(1.0))
    else:
        background = create_gradient_background(CANVAS_WIDTH, CANVAS_HEIGHT, (25, 15, 55), (80, 15, 60))

    img = apply_editorial_overlay(background)
    draw = ImageDraw.Draw(img)

    headline = slide_data.get("headline", "").strip()
    body = slide_data.get("body", "").strip()
    highlight = slide_data.get("highlight", "").strip().upper()
    cta = slide_data.get("cta", "").strip()

    font_small = load_font(28, bold=True)
    font_highlight = load_font(30, bold=True)
    font_headline = load_font(66, bold=True)
    font_body = load_font(34, bold=False)
    font_cta = load_font(34, bold=True)

    padding_x = 70
    content_width = CANVAS_WIDTH - (padding_x * 2)
    current_y = 70

    draw.text((padding_x, current_y), BRAND_NAME, font=font_small, fill=(255, 255, 255, 230))
    slide_number = f"{slide_index}/3"
    number_bbox = draw.textbbox((0, 0), slide_number, font=font_small)
    draw.text((CANVAS_WIDTH - padding_x - (number_bbox[2] - number_bbox[0]), current_y), slide_number, font=font_small, fill=(255, 255, 255, 210))
    current_y += 90

    if highlight:
        label_bbox = draw.textbbox((0, 0), highlight, font=font_highlight)
        box_x2 = padding_x + (label_bbox[2] - label_bbox[0]) + 44
        box_y2 = current_y + (label_bbox[3] - label_bbox[1]) + 28
        draw.rounded_rectangle((padding_x, current_y, box_x2, box_y2), radius=16, fill=(255, 205, 70, 235))
        draw.text((padding_x + 22, current_y + 10), highlight, font=font_highlight, fill=(20, 20, 20, 255))
        current_y = box_y2 + 50

    headline_wrapped = wrap_text_by_pixels(draw, headline, font_headline, content_width)
    draw.multiline_text((padding_x, current_y), headline_wrapped, font=font_headline, fill=(255, 255, 255, 255), spacing=12)
    current_y += get_multiline_height(draw, headline_wrapped, font_headline, 12) + 45

    if body:
        body_wrapped = wrap_text_by_pixels(draw, body, font_body, content_width)
        draw.multiline_text((padding_x, current_y), body_wrapped, font=font_body, fill=(235, 235, 235, 255), spacing=14)
        current_y += get_multiline_height(draw, body_wrapped, font_body, 14) + 35

    if cta:
        cta_y = min(current_y + 30, CANVAS_HEIGHT - 220)
        cta_wrapped = wrap_text_by_pixels(draw, cta, font_cta, content_width)
        cta_height = get_multiline_height(draw, cta_wrapped, font_cta, 10)
        draw.rounded_rectangle((padding_x - 20, cta_y - 20, CANVAS_WIDTH - padding_x + 20, cta_y + cta_height + 35), radius=20, fill=(255, 255, 255, 35), outline=(255, 255, 255, 80), width=2)
        draw.multiline_text((padding_x, cta_y), cta_wrapped, font=font_cta, fill=(255, 215, 80, 255), spacing=10)

    footer_y = CANVAS_HEIGHT - 80
    draw.line((padding_x, footer_y - 18, CANVAS_WIDTH - padding_x, footer_y - 18), fill=(255, 255, 255, 60), width=1)
    draw.text((padding_x, footer_y), BRAND_HANDLE, font=font_small, fill=(255, 255, 255, 180))

    output_path = os.path.join(temp_dir, f"slide_{slide_index}.jpg")
    img.convert("RGB").save(output_path, quality=JPEG_QUALITY, optimize=True)
    return output_path


def create_gradient_background(w, h, c1, c2):
    base = Image.new("RGB", (w, h), c1)
    top = Image.new("RGB", (w, h), c2)
    mask = Image.new("L", (w, h))
    mask.putdata([int(255 * (y / max(h - 1, 1))) for y in range(h) for _ in range(w)])
    base.paste(top, (0, 0), mask)
    return base

def resize_cover(img, tw, th):
    sw, sh = img.size
    scale = max(tw / sw, th / sh)
    img = img.resize((int(sw * scale), int(sh * scale)), Image.LANCZOS)
    return img.crop(((img.width - tw) // 2, (img.height - th) // 2, (img.width + tw) // 2, (img.height + th) // 2))

def load_font(size, bold=False):
    for path in ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", "arialbd.ttf" if bold else "arial.ttf"]:
        try: return ImageFont.truetype(path, size=size)
        except: continue
    return ImageFont.load_default()

def wrap_text_by_pixels(draw, text, font, mw):
    words, lines, current = text.split(), [], ""
    for w in words:
        test = w if not current else current + " " + w
        if (draw.textbbox((0, 0), test, font=font)[2] - draw.textbbox((0, 0), test, font=font)[0]) <= mw or not current:
            current = test
        else:
            lines.append(current)
            current = w
    if current: lines.append(current)
    return "\n".join(lines)

def get_multiline_height(draw, text, font, spacing):
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
    return bbox[3] - bbox[1]

def apply_editorial_overlay(img):
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pixels = overlay.load()
    for y in range(h):
        alpha = int(210 - (y/h) * 120) if (y/h) < 0.35 else (int(90 + (((y/h) - 0.70) * 500)) if (y/h) > 0.70 else 85)
        for x in range(w): pixels[x, y] = (0, 0, 0, max(0, min(220, alpha)))
    return Image.alpha_composite(img.convert("RGBA"), overlay)

def build_caption(ai_data):
    caption = ai_data.get("caption", "").strip()
    hashtags = ai_data.get("hashtags", [])
    if hashtags: caption += "\n\n" + " ".join(t.strip() for t in hashtags if t.strip())
    return caption


def run_editor():
    print("\n" + "=" * 50)
    print("AUTO NEWS → HYBRID EDITOR (CAROUSEL / REELS)")
    print("=" * 50 + "\n")

    news = get_pending_news()
    if not news:
        print("[EDITOR] Tidak ada antrean berita baru.")
        return

    news_id, title, raw_content = news
    
    # Menentukan mode secara bergantian (Contoh: Setiap ID ganjil = Reels, genap = Carousel)
    # Atau bisa diatur berdasarkan jumlah total row di database.
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM content_queue WHERE status = 'published'")
    published_count = cursor.fetchone()[0]
    conn.close()

    # Siklus: 2 Carousel, lalu 1 Reels (atau sesuaikan modulusnya)
    target_mode = "reels" if (published_count % 3 == 2) else "carousel"
    print(f"[EDITOR] Mode terpilih untuk Berita ID {news_id}: {target_mode.upper()}")

    ai_data = generate_content_with_ai(title, raw_content, target_mode=target_mode)
    if not ai_data or len(ai_data.get("slides", [])) != 3:
        print("[EDITOR ERROR] AI gagal membuat konten.")
        return

    timestamp = int(time.time())

    with tempfile.TemporaryDirectory() as temp_dir:
        slide_paths = []
        for idx, slide_data in enumerate(ai_data["slides"], start=1):
            bg_path = generate_background_image(slide_data, idx, temp_dir)
            slide_path = create_slide_image(slide_data, idx, bg_path, temp_dir)
            if slide_path: slide_paths.append(slide_path)
            else: return

        if target_mode == "reels":
            # Mode Reels: Gabungkan slide + Audio Qur'an menjadi MP4
            surah = ai_data.get("quran_surah", 3)
            ayah = ai_data.get("quran_ayah", 190)
            audio_path = download_quran_audio(surah, ayah, temp_dir)
            
            if not audio_path:
                print("[EDITOR ERROR] Gagal unduh audio Qur'an, fallback ke Carousel.")
                target_mode = "carousel"
            else:
                output_video_path = os.path.join(temp_dir, f"news_{news_id}_reels_{timestamp}.mp4")
                if create_reels_video(slide_paths, audio_path, output_video_path):
                    raw_url = upload_to_github(output_video_path, f"posts/news_{news_id}_reels_{timestamp}.mp4")
                    if raw_url:
                        update_status(news_id, "ready", github_url=raw_url, caption=build_caption(ai_data), media_type="reels")
                        print(f"[EDITOR SUCCESS] Berita ID {news_id} siap dipublikasikan sebagai REELS.")
                        return

        # Mode Carousel (Default atau Fallback): Upload 3 gambar terpisah
        github_urls = []
        for idx, slide_path in enumerate(slide_paths, start=1):
            github_dest = f"posts/news_{news_id}_slide_{idx}_{timestamp}.jpg"
            raw_url = upload_to_github(slide_path, github_dest)
            if raw_url: github_urls.append(raw_url)
            else: return

        if len(github_urls) == 3:
            joined_urls = ",".join(github_urls)
            update_status(news_id, "ready", github_url=joined_urls, caption=build_caption(ai_data), media_type="carousel")
            print(f"[EDITOR SUCCESS] Berita ID {news_id} siap dipublikasikan sebagai CAROUSEL.")


if __name__ == "__main__":
    run_editor()