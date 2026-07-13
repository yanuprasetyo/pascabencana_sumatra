# Monitor Berita — Pascabencana Banjir Sumatera

Dashboard pemantauan otomatis pemberitaan media Indonesia terkait banjir Sumatera
(November 2025–sekarang), mencakup empat fase penanggulangan bencana:

- 🌊 **Banjir Sumatera (Umum)** — liputan umum kejadian dan dampak
- 🚨 **Tanggap Darurat** — evakuasi, SAR, posko pengungsian, bantuan darurat
- 🏗️ **Rehabilitasi & Rekonstruksi** — perbaikan infrastruktur, jalan, jembatan, rumah
- 🌱 **Pemulihan & Bantuan Sosial** — pemulihan ekonomi, mata pencaharian, bansos, relokasi

## Struktur folder

```
.
├── docs/                          # Dipublikasikan lewat GitHub Pages
│   ├── index.html                 # Halaman dashboard
│   └── data/
│       └── news.json              # Data berita (diakumulasi otomatis, jangan diedit manual)
├── scripts/
│   └── scrape_news.py             # Scraper Google News RSS
└── .github/workflows/
    └── scrape-banjir-sumatera.yml # Jadwal otomatis tiap 6 jam
```

## Cara mengaktifkan

1. Upload/push seluruh isi folder ini ke repo GitHub baru (atau clone repo lalu salin isinya).
2. Di repo GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch**,
   pilih branch `main` dan folder `/docs`.
3. Buka tab **Actions**, pilih workflow **"Scrape Berita Banjir Sumatera"**, klik
   **Run workflow** untuk mengisi data pertama kali.
4. Setelah `docs/data/news.json` terisi, buka URL GitHub Pages-nya — dashboard akan
   langsung menampilkan data.
5. Selanjutnya workflow berjalan otomatis tiap 6 jam tanpa perlu disentuh lagi.

## Menyesuaikan kata kunci pencarian

Edit bagian `KEYWORDS` di `scripts/scrape_news.py` untuk menambah/mengurangi kata
kunci pencarian per fase, sesuai perkembangan bencana di lapangan.

## Catatan

- Data **diakumulasi**, tidak pernah dihapus otomatis oleh scraper.
- Jika struktur repo Bapak tidak memakai folder `docs/` untuk GitHub Pages, ubah
  baris `OUTPUT_PATH` di `scripts/scrape_news.py` menjadi `"data/news.json"`, dan
  pindahkan folder `docs/` menjadi isi root repo.
