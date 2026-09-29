#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  YouTube Shorts Generator — OpenRouter (Final Fixed)         ║
║  Fix: max_tokens diperbesar & kompatibilitas MoviePy v1/v2   ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import re
import base64
import io
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# ──────────────────────────────────────────────
# DEPENDENCY IMPORTS
# ──────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import yt_dlp
except ImportError:
    sys.exit("❌ yt-dlp belum terinstall. Jalankan: pip install yt-dlp")

try:
    from openai import OpenAI
except ImportError:
    sys.exit("❌ openai belum terinstall. Jalankan: pip install openai")

# Deteksi versi MoviePy untuk kompatibilitas method
try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_V2 = False
except ImportError:
    try:
        from moviepy import VideoFileClip
        MOVIEPY_V2 = True
    except ImportError:
        sys.exit("❌ moviepy belum terinstall. Jalankan: pip install moviepy")

try:
    from PIL import Image
except ImportError:
    sys.exit("❌ Pillow belum terinstall. Jalankan: pip install Pillow")

# ──────────────────────────────────────────────
# LOGGING CONFIGURATION
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ShortsGen")


# ══════════════════════════════════════════════
#  1. KONFIGURASI OPENROUTER
# ══════════════════════════════════════════════

def get_openrouter_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("❌ OPENROUTER_API_KEY tidak ditemukan di file .env!")
    if not api_key.startswith("sk-or-v1-"):
        raise EnvironmentError("❌ Format OPENROUTER_API_KEY tidak valid! Harus dimulai dengan 'sk-or-v1-'.")
    
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/shorts-generator",
            "X-Title": "Shorts Generator",
        }
    )


# ══════════════════════════════════════════════
#  2. VIDEO DOWNLOAD (yt-dlp)
# ══════════════════════════════════════════════

def download_video(url: str, output_dir: str = "temp") -> str:
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "source_video.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    logger.info(f"⬇  Mengunduh video: {url}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = str(Path(ydl.prepare_filename(info)).with_suffix(".mp4"))
            
        if not os.path.exists(filepath):
            mp4_files = sorted(Path(output_dir).glob("source_video*.mp4"))
            filepath = str(mp4_files[-1]) if mp4_files else filepath

        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        logger.info(f"✅ Download selesai: {filepath} ({size_mb:.1f} MB)")
        return filepath
    except Exception as e:
        raise RuntimeError(f"Gagal download video: {e}") from e


# ══════════════════════════════════════════════
#  3. AI ANALYSIS (OpenRouter + Anti-Truncated)
# ══════════════════════════════════════════════

def extract_key_frames(video_path: str, num_frames: int = 4) -> List[str]:
    clip = VideoFileClip(video_path)
    duration = clip.duration
    frames_b64 = []

    logger.info(f"📸 Mengekstrak {num_frames} frame kunci dari video...")
    
    for i in range(num_frames):
        t = (duration / (num_frames + 1)) * (i + 1)
        frame_array = clip.get_frame(t)
        
        img = Image.fromarray(frame_array)
        img.thumbnail((1024, 1024)) 
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        frames_b64.append(f"data:image/jpeg;base64,{img_b64}")

    clip.close()
    return frames_b64

def find_valid_gemini_flash_model(client: OpenAI) -> Optional[str]:
    logger.info("🔍 Mencari model Gemini Flash reguler (non-TTS) yang valid...")
    try:
        models = client.models.list()
        for m in models.data:
            model_id = m.id.lower()
            if "gemini" in model_id and "flash" in model_id:
                if "tts" not in model_id and "audio" not in model_id:
                    logger.info(f"✅ Model valid ditemukan: {m.id}")
                    return m.id
        for m in models.data:
            if "gemini" in m.id.lower() and "flash" in m.id.lower():
                return m.id
    except Exception as e:
        logger.warning(f"⚠ Gagal mengambil daftar model: {e}")
    return None

def analyze_with_openrouter(video_path: str) -> Dict[str, Any]:
    client = get_openrouter_client()
    model_name = os.getenv("TARGET_MODEL", "google/gemini-flash-1.5")
    
    frames_b64 = extract_key_frames(video_path, num_frames=4)
    
    strict_prompt = """Kamu adalah AI video editor. Tugasmu MURNI mengembalikan data JSON.
JANGAN PERNAH mengeluarkan teks biasa, penjelasan, atau markdown.
HANYA outputkan objek JSON valid dengan struktur persis seperti ini:

{
  "start_time": 0.0,
  "end_time": 45.0,
  "title": "Judul Catchy",
  "description": "Deskripsi singkat #shorts #viral"
}

Analisis frame visual yang diberikan. Temukan 1 momen paling viral (durasi 15-55 detik).
Kembalikan HANYA JSON. Tidak ada kata lain."""

    content_payload = [{"type": "text", "text": strict_prompt}]
    for img_b64 in frames_b64:
        content_payload.append({"type": "image_url", "image_url": {"url": img_b64}})

    messages = [{"role": "user", "content": content_payload}]

    def call_api(target_model: str, current_messages: list, force_json: bool = True):
        kwargs = {
            "model": target_model,
            "messages": current_messages,
            "temperature": 0.1,
            "max_tokens": 2048, # Diperbesar agar JSON tidak terpotong (truncated)
        }
        if force_json:
            kwargs["response_format"] = {"type": "json_object"}
            
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            if force_json and "400" in str(e):
                logger.warning("⚠ Model tidak mendukung response_format, mencoba tanpa paksaan JSON...")
                kwargs.pop("response_format")
                return client.chat.completions.create(**kwargs)
            raise e

    def find_and_call(target_model: str):
        try:
            return call_api(target_model, messages)
        except Exception as e:
            error_str = str(e)
            if "401" in error_str and "User not found" in error_str:
                raise RuntimeError("❌ GAGAL AUTENTIKASI OPENROUTER (401).\nPastikan API Key di .env benar dan TIDAK ADA SPASI.") from e
            elif "404" in error_str:
                logger.warning(f"⚠ Model '{target_model}' tidak ditemukan (404). Mencari model alternatif...")
                fallback_model = find_valid_gemini_flash_model(client)
                if fallback_model:
                    logger.info(f"🔄 Mencoba ulang dengan model fallback: {fallback_model}")
                    return call_api(fallback_model, messages)
                else:
                    raise RuntimeError(f"❌ Model '{target_model}' tidak ditemukan, dan gagal mencari model fallback.") from e
            elif "402" in error_str:
                raise RuntimeError("❌ SALDO OPENROUTER HABIS (402).") from e
            else:
                raise RuntimeError(f"OpenRouter API gagal: {e}") from e

    logger.info(f"🤖 Mengirim {len(frames_b64)} frame ke OpenRouter (Model: {model_name})...")
    response = find_and_call(model_name)
    raw_text = response.choices[0].message.content.strip()
    
    # AUTO-RETRY JIKA AI TETAP TIDAK MEMBERIKAN JSON
    if not re.search(r"\{[\s\S]*\}", raw_text):
        logger.warning("⚠ Respons AI bukan JSON. Mengirim koreksi otomatis...")
        messages.append({"role": "assistant", "content": raw_text})
        messages.append({"role": "user", "content": "Itu bukan JSON. Kembalikan HANYA objek JSON valid sesuai skema di atas. Jangan ada teks lain."})
        response = find_and_call(model_name)
        raw_text = response.choices[0].message.content.strip()

    logger.info(f"   Raw response: {raw_text[:200]}...")

    # Parse JSON
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    
    if not json_match:
        raise ValueError(f"AI tetap gagal menghasilkan JSON setelah koreksi.\nRespons mentah: {raw_text}")

    try:
        result = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON tidak valid dari AI: {e}\nRaw: {raw_text}") from e

    # Validasi & Koreksi Timestamp
    start = float(result.get("start_time", 0))
    end = float(result.get("end_time", 0))
    if (end - start) > 60:
        logger.warning("⚠ Durasi > 60s, dikoreksi otomatis ke 55s.")
        result["end_time"] = start + 55

    return result


# ══════════════════════════════════════════════
#  4. VIDEO EDITING (MoviePy 9:16 Crop - FIXED)
# ══════════════════════════════════════════════

def create_shorts(video_path: str, start_time: float, end_time: float, output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    logger.info(f"✂  Memotong: {start_time:.1f}s → {end_time:.1f}s")

    clip = None
    try:
        clip = VideoFileClip(video_path)
        
        # 1. Subclip (Kompatibel v1 dan v2)
        cut = clip.subclipped(start_time, end_time) if MOVIEPY_V2 else clip.subclip(start_time, end_time)

        # 2. Hitung dimensi center-crop 9:16
        w, h = cut.size
        target_ratio = 9 / 16
        if (w / h) > target_ratio:
            new_w = int(h * target_ratio)
            new_h = h
        else:
            new_w = w
            new_h = int(w / target_ratio)
            
        # Pastikan dimensi genap (syarat codec H.264)
        new_w, new_h = new_w - (new_w % 2), new_h - (new_h % 2)

        x1, y1 = (w - new_w) // 2, (h - new_h) // 2
        x2, y2 = x1 + new_w, y1 + new_h
        
        # 3. Crop (Kompatibel v1 dan v2)
        cropped = cut.cropped(x1=x1, y1=y1, x2=x2, y2=y2) if MOVIEPY_V2 else cut.crop(x1=x1, y1=y1, x2=x2, y2=y2)
        
        # 4. Resize (PERBAIKAN UTAMA: Kompatibel v1 dan v2)
        final = cropped.resized((1080, 1920)) if MOVIEPY_V2 else cropped.resize((1080, 1920))

        logger.info("🎞  Rendering video final (1080x1920)...")
        
        # 5. Konfigurasi export
        write_kwargs = {
            "codec": "libx264",
            "fps": min(30, int(clip.fps or 30)),
            "bitrate": "5000k",
            "threads": 4,
            "logger": None
        }
        
        # Pengecekan audio yang aman untuk semua versi MoviePy
        if getattr(clip, 'audio', None) is not None:
            write_kwargs["audio_codec"] = "aac"
            
        final.write_videofile(output_path, **write_kwargs)
        
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"✅ Shorts berhasil: {output_path} ({size_mb:.1f} MB)")
        return output_path
        
    finally:
        if clip: 
            clip.close()


# ══════════════════════════════════════════════
#  5. CLEANUP & MAIN PIPELINE
# ══════════════════════════════════════════════

def cleanup(files: List[str], directories: Optional[List[str]] = None):
    for f in files:
        if os.path.exists(f):
            try:
                os.remove(f)
                logger.info(f"🗑  Dihapus: {f}")
            except OSError:
                pass
                
    for d in (directories or []):
        if os.path.isdir(d) and not os.listdir(d):
            try:
                os.rmdir(d)
                logger.info(f"🗑  Dir dihapus: {d}")
            except OSError:
                pass

def generate_shorts(youtube_url: str, output_dir: str = "output") -> Dict[str, Any]:
    temp_dir = "temp"
    source_video = None
    
    try:
        logger.info("═" * 55 + "\n  STEP 1/3 │ Download Video YouTube")
        source_video = download_video(youtube_url, temp_dir)

        logger.info("═" * 55 + "\n  STEP 2/3 │ Analisis AI (OpenRouter Gemini)")
        clip_info = analyze_with_openrouter(source_video)
        logger.info(f"   🎯 Timestamp : {clip_info['start_time']:.1f}s → {clip_info['end_time']:.1f}s")
        logger.info(f"   📝 Title     : {clip_info['title']}")
        logger.info(f"   📄 Desc      : {clip_info['description']}")

        logger.info("═" * 55 + "\n  STEP 3/3 │ Video Editing (9:16 Center-Crop)")
        output_path = os.path.join(output_dir, "shorts_final.mp4")
        create_shorts(
            source_video, 
            float(clip_info["start_time"]), 
            float(clip_info["end_time"]), 
            output_path
        )

        return {
            "file_path": output_path,
            "title": clip_info["title"],
            "description": clip_info["description"],
            "start_time": clip_info["start_time"],
            "end_time": clip_info["end_time"]
        }
    
    finally:
        if source_video:
            cleanup([source_video], [temp_dir])


# ══════════════════════════════════════════════
#  6. ENTRY POINT
# ══════════════════════════════════════════════

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(r"""
    ╔═══════════════════════════════════════════════════╗
    ║   🎬  YOUTUBE SHORTS GENERATOR  (OpenRouter)     ║
    ║   Download → Gemini AI → 9:16 Crop → Done!       ║
    ╚═══════════════════════════════════════════════════╝
    """)

    try:
        result = generate_shorts(url)

        print("\n" + "═" * 55)
        print("  ✅  YOUTUBE SHORTS BERHASIL DIBUAT!")
        print("═" * 55)
        print(f"  📁 File     : {result['file_path']}")
        print(f"  📝 Title    : {result['title']}")
        print(f"  📄 Desc     : {result['description']}")
        print(f"  ⏱  Durasi   : {result['end_time'] - result['start_time']:.1f} detik")
        print("═" * 55)

    except KeyboardInterrupt:
        print("\n⛔ Dibatalkan oleh user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)
