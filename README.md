<div align="center">

# 🎬 YouTube Shorts Generator

**Ubah video YouTube panjang menjadi Shorts vertikal 9:16 secara otomatis dengan bantuan AI.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenRouter](https://img.shields.io/badge/AI-OpenRouter%20(Gemini)-6467F2)](https://openrouter.ai/)
[![MoviePy](https://img.shields.io/badge/MoviePy-v1%20%26%20v2-orange)](https://zulko.github.io/moviepy/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#-kontribusi)

</div>

---

## 📖 Deskripsi

**YouTube Shorts Generator** adalah tool command-line berbasis Python yang mengotomatiskan pembuatan konten Shorts dari video YouTube. Cukup berikan satu URL, dan script akan:

1. **Mengunduh** video sumber (maks. 720p) menggunakan `yt-dlp`.
2. **Menganalisis** frame kunci video dengan model Gemini Flash melalui **OpenRouter** untuk menemukan momen paling berpotensi viral (15–55 detik).
3. **Memotong & mengonversi** klip tersebut ke format **9:16 (1080×1920)** dengan center-crop menggunakan **MoviePy**.
4. **Menghasilkan** judul dan deskripsi (lengkap dengan hashtag) yang siap dipakai.

## ✨ Fitur

- 🤖 **Analisis visual AI** — 4 frame kunci dikirim ke model multimodal untuk menentukan timestamp terbaik.
- 🛡️ **Output JSON yang tangguh** — max token diperbesar, auto-retry jika respons bukan JSON, dan parsing yang toleran terhadap markdown fence.
- 🔄 **Fallback model otomatis** — jika model gagal (404), script mencari model Gemini Flash reguler yang valid.
- 🎞️ **Kompatibel MoviePy v1 & v2** — deteksi versi otomatis.
- ✂️ **Validasi durasi** — klip lebih dari 60 detik otomatis dikoreksi ke 55 detik.
- 🧹 **Auto-cleanup** — file sementara dihapus setelah proses selesai.
- ⚠️ **Pesan error yang jelas** — penanganan khusus untuk error 401 (autentikasi), 402 (saldo habis), dan 404 (model tidak ditemukan).

## 🔄 Alur Kerja

```
URL YouTube ─► yt-dlp ─► Ekstrak 4 frame ─► OpenRouter (Gemini) ─► JSON timestamp
                                                                        │
      shorts_final.mp4 (1080x1920) ◄─ MoviePy crop 9:16 + resize ◄──────┘
```

## 📁 Struktur Project

```
project/
├── .env                  # Konfigurasi API key (JANGAN di-commit!)
├── shorts_generator.py   # Script utama
├── requirements.txt      # Daftar dependency
├── LICENSE
├── README.md
├── temp/                 # (auto-created) video mentah, dihapus setelah selesai
└── output/               # (auto-created) hasil Shorts
```

## 📋 Prasyarat

- **Python 3.9+**
- **FFmpeg** (wajib untuk MoviePy)
- **API key OpenRouter** — daftar di [openrouter.ai](https://openrouter.ai/keys) dan pastikan saldo mencukupi

## 🚀 Instalasi

### 1. Clone repository

```bash
git clone https://github.com/USERNAME/REPO_NAME.git
cd REPO_NAME
```

### 2. Buat virtual environment (direkomendasikan)

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependency

```bash
pip install --upgrade yt-dlp openai moviepy python-dotenv Pillow
```

### 4. Install FFmpeg

| OS | Perintah |
|----|----------|
| Ubuntu / Debian | `sudo apt install ffmpeg` |
| macOS (Homebrew) | `brew install ffmpeg` |
| Windows | Unduh dari [ffmpeg.org/download](https://ffmpeg.org/download.html) lalu tambahkan ke `PATH` |

## ⚙️ Konfigurasi

Buat file `.env` di root project:

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx

# Opsional. Jika error 404, script otomatis mencari model Gemini Flash yang valid.
TARGET_MODEL=google/gemini-flash-1.5
```

| Variabel | Wajib | Keterangan |
|----------|:-----:|------------|
| `OPENROUTER_API_KEY` | ✅ | API key OpenRouter. Harus diawali `sk-or-v1-` dan tanpa spasi. |
| `TARGET_MODEL` | ❌ | Model multimodal yang dipakai. Default: `google/gemini-flash-1.5`. |

> ⚠️ **Keamanan:** tambahkan `.env` ke `.gitignore` agar API key tidak ikut terunggah ke GitHub.

```bash
echo ".env" >> .gitignore
echo "temp/" >> .gitignore
echo "output/" >> .gitignore
echo "venv/" >> .gitignore
```

## ▶️ Cara Penggunaan

```bash
python shorts_generator.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Jika URL tidak diberikan, script memakai URL contoh bawaan.

### Contoh output

```
═══════════════════════════════════════════════════════
  ✅  YOUTUBE SHORTS BERHASIL DIBUAT!
═══════════════════════════════════════════════════════
  📁 File     : output/shorts_final.mp4
  📝 Title    : Judul Catchy
  📄 Desc     : Deskripsi singkat #shorts #viral
  ⏱  Durasi   : 45.0 detik
═══════════════════════════════════════════════════════
```

### Penggunaan sebagai modul

```python
from shorts_generator import generate_shorts

result = generate_shorts("https://www.youtube.com/watch?v=VIDEO_ID", output_dir="output")
print(result["file_path"], result["title"], result["description"])
```

## 🧩 Spesifikasi Output

| Properti | Nilai |
|----------|-------|
| Resolusi | 1080 × 1920 (9:16) |
| Codec video | H.264 (`libx264`) |
| Codec audio | AAC |
| Bitrate | 5000k |
| FPS | maks. 30 |
| Durasi klip | 15–55 detik (dibatasi maks. 60 detik) |

## 🛠️ Troubleshooting

| Masalah | Penyebab & Solusi |
|---------|-------------------|
| `401 User not found` | API key salah atau ada spasi. Periksa `.env`. |
| `402` | Saldo OpenRouter habis. Top up di dashboard OpenRouter. |
| `404` model tidak ditemukan | Ganti `TARGET_MODEL`, atau biarkan script memakai fallback otomatis. |
| `moviepy belum terinstall` | Jalankan `pip install moviepy`. |
| Error FFmpeg / `ffmpeg not found` | Pastikan FFmpeg terpasang dan ada di `PATH`. |
| AI tidak mengembalikan JSON | Script otomatis mencoba ulang satu kali. Coba ganti model jika berulang. |
| Gagal download video | Perbarui yt-dlp: `pip install --upgrade yt-dlp`. |

## ⚖️ Catatan Hukum & Etika

Tool ini disediakan untuk keperluan edukasi dan produktivitas pribadi. Anda **bertanggung jawab penuh** untuk:

- Hanya memproses video yang Anda miliki, atau yang lisensinya mengizinkan penggunaan ulang (mis. Creative Commons) atau Anda memiliki izin dari pemilik konten.
- Mematuhi [Ketentuan Layanan YouTube](https://www.youtube.com/t/terms) dan hukum hak cipta yang berlaku.
- Mencantumkan atribusi kepada kreator asli bila diperlukan.

Penulis tidak bertanggung jawab atas penyalahgunaan tool ini.

## 🤝 Kontribusi

Kontribusi sangat diterima!

1. Fork repository ini
2. Buat branch fitur: `git checkout -b fitur/nama-fitur`
3. Commit perubahan: `git commit -m "Tambah fitur X"`
4. Push ke branch: `git push origin fitur/nama-fitur`
5. Buka Pull Request

## 🗺️ Roadmap

- [ ] Subtitle otomatis (speech-to-text)
- [ ] Smart crop berbasis deteksi wajah/objek
- [ ] Analisis audio & transkrip untuk pemilihan momen
- [ ] Output beberapa klip sekaligus
- [ ] Mode batch untuk banyak URL
- [ ] Argumen CLI (`--model`, `--output`, `--duration`)

## 📄 Lisensi

Didistribusikan di bawah **MIT License**. Lihat file [`LICENSE`](LICENSE) untuk detail lengkap.

## 🙏 Kredit

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — pengunduh video
- [MoviePy](https://zulko.github.io/moviepy/) — editing video
- [OpenRouter](https://openrouter.ai/) — gateway API model AI
- [Pillow](https://python-pillow.org/) — pemrosesan gambar

---

<div align="center">

Dibuat dengan ❤️ oleh *REVA DWI PRASETIA*· Jika project ini membantu, berikan ⭐ di GitHub!

</div>
# Cliper-id
