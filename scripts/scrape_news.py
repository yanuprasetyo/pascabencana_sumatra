#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraper berita — Monitor Pascabencana Banjir Sumatera
======================================================

Mengambil berita dari Google News RSS untuk 4 fase penanggulangan bencana:
  - banjir     : Banjir Sumatera (liputan umum)
  - darurat    : Tanggap Darurat
  - rehab      : Rehabilitasi & Rekonstruksi
  - pemulihan  : Pemulihan & Bantuan Sosial

Data diakumulasi (tidak pernah dihapus) ke dalam satu file JSON yang dibaca
langsung oleh dashboard (index_banjir_sumatera.html -> fetch('data/news.json')).

Cara pakai:
    pip install feedparser python-dateutil
    python scripts/scrape_news.py

Jadwalkan lewat GitHub Actions (lihat .github/workflows/scrape-banjir-sumatera.yml).
"""

import json
import os
import re
import time
import html
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
from dateutil import parser as dateparser

# ─────────────────────────────────────────────────────────────────────
# KONFIGURASI
# ─────────────────────────────────────────────────────────────────────

# Path output JSON. Sesuaikan jika halaman dashboard ditaruh di /docs
# (pola GitHub Pages "docs/" seperti dua dashboard sebelumnya) atau di root repo.
OUTPUT_PATH = "docs/data/news.json"

# Urutan prioritas topik ketika satu artikel cocok dengan lebih dari satu
# kata kunci (fase yang lebih spesifik menang atas kategori umum "banjir").
TOPIC_PRIORITY = ["darurat", "rehab", "pemulihan", "banjir"]

# Kata kunci pencarian per fase. Silakan tambah/kurangi sesuai kebutuhan —
# setiap kata kunci akan dikirim sebagai satu query terpisah ke Google News RSS.
KEYWORDS = {
    "banjir": [
        "banjir Sumatera",
        "banjir Sumatera Barat",
        "banjir Sumatera Utara",
        "banjir Aceh",
        "banjir bandang Sumatera",
        "korban banjir Sumatera",
        "banjir longsor Sumatera",
    ],
    "darurat": [
        "tanggap darurat banjir Sumatera",
        "evakuasi banjir Sumatera",
        "posko pengungsian banjir Sumatera",
        "BNPB banjir Sumatera",
        "bantuan darurat banjir Sumatera",
        "status tanggap darurat bencana Sumatera",
        "pencarian korban banjir Sumatera",
    ],
    "rehab": [
        "rehabilitasi rekonstruksi banjir Sumatera",
        "perbaikan infrastruktur pascabanjir Sumatera",
        "rekonstruksi jalan jembatan banjir Sumatera",
        "rehab rekon BNPB Sumatera",
        "pembangunan kembali pascabencana Sumatera",
        "perbaikan rumah rusak banjir Sumatera",
    ],
    "pemulihan": [
        "pemulihan ekonomi pascabanjir Sumatera",
        "bantuan sosial korban banjir Sumatera",
        "relokasi korban banjir Sumatera",
        "pemulihan mata pencaharian banjir Sumatera",
        "trauma healing korban banjir Sumatera",
        "bantuan modal usaha pascabencana Sumatera",
    ],
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

REQUEST_DELAY_SECONDS = 1.5  # jeda antar-request agar tidak dianggap spam

TAG_RE = re.compile(r"<[^>]+>")


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────

def strip_html(text):
    """Buang tag HTML dari deskripsi RSS dan rapikan entitas HTML."""
    if not text:
        return ""
    text = TAG_RE.sub("", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def split_source_from_title(title):
    """
    Judul dari Google News RSS biasanya berformat "Judul Asli - Nama Media".
    Fungsi ini memisahkan keduanya jika memungkinkan.
    """
    if " - " in title:
        head, _, tail = title.rpartition(" - ")
        # Nama media biasanya pendek (< 40 karakter) dan tidak mengandung tanda tanya/seru
        if 0 < len(tail) <= 40:
            return head.strip(), tail.strip()
    return title.strip(), ""


def parse_entry(entry, topic):
    """Ubah satu entry feedparser menjadi dict artikel siap simpan."""
    raw_title = html.unescape(entry.get("title", "")).strip()

    # Google News RSS umumnya menyertakan <source> per item
    source = ""
    src_obj = entry.get("source")
    if isinstance(src_obj, dict):
        source = src_obj.get("title", "") or ""
    elif hasattr(src_obj, "title"):
        source = getattr(src_obj, "title", "") or ""

    title = raw_title
    if not source:
        title, source = split_source_from_title(raw_title)

    link = entry.get("link", "")

    pub_raw = entry.get("published", "") or entry.get("updated", "")
    try:
        pub_dt = dateparser.parse(pub_raw)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        pub_dt = pub_dt.astimezone(timezone.utc)
        pub_date = pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pub_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    desc = strip_html(entry.get("summary", ""))

    return {
        "topic": topic,
        "title": title,
        "source": source,
        "pub_date": pub_date,
        "desc": desc,
        "link": link,
    }


def normalize_key(article):
    """Kunci dedupe: judul yang dinormalisasi + sumber (bukan link, karena
    link Google News bisa berbeda-beda meski artikelnya sama)."""
    t = re.sub(r"[^a-z0-9 ]", "", article["title"].lower()).strip()
    t = re.sub(r"\s+", " ", t)
    return f"{t}::{article['source'].lower()}"


def fetch_topic(topic, queries):
    """Ambil semua artikel untuk satu topik dari daftar query-nya."""
    results = []
    for q in queries:
        url = (
            "https://news.google.com/rss/search?q="
            + quote(q)
            + "&hl=id&gl=ID&ceid=ID:id"
        )
        print(f"  [{topic}] mengambil: {q}")
        try:
            feed = feedparser.parse(url, agent=USER_AGENT)
            for entry in feed.entries:
                results.append(parse_entry(entry, topic))
        except Exception as e:
            print(f"    ! gagal mengambil '{q}': {e}")
        time.sleep(REQUEST_DELAY_SECONDS)
    return results


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

def load_existing(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"! Gagal membaca data lama ({e}), mulai dari kosong.")
    return []


def save(path, articles):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)


def main():
    print("=== Scraper Berita Banjir Sumatera ===")
    existing = load_existing(OUTPUT_PATH)
    print(f"Data lama: {len(existing)} artikel")

    # Kumpulkan semua artikel baru per topik (urutan prioritas dijaga
    # supaya topik yang lebih spesifik tidak ketiban topik umum)
    fresh_by_topic = {}
    for topic in TOPIC_PRIORITY:
        fresh_by_topic[topic] = fetch_topic(topic, KEYWORDS[topic])

    # Gabungkan artikel lama + baru, dedupe berdasarkan (judul dinormalisasi + sumber),
    # dengan prioritas topik yang lebih spesifik jika ada tumpang tindih pencarian
    merged = {}

    for article in existing:
        merged[normalize_key(article)] = article

    for topic in TOPIC_PRIORITY:
        for article in fresh_by_topic[topic]:
            key = normalize_key(article)
            if key in merged:
                # Artikel sudah ada — hanya timpa topik jika topik baru
                # lebih prioritas (lebih spesifik) daripada yang tersimpan
                old_topic = merged[key]["topic"]
                if TOPIC_PRIORITY.index(topic) < TOPIC_PRIORITY.index(old_topic):
                    merged[key]["topic"] = topic
                continue
            merged[key] = article

    all_articles = list(merged.values())
    all_articles.sort(key=lambda a: a["pub_date"], reverse=True)

    save(OUTPUT_PATH, all_articles)

    added = len(all_articles) - len(existing)
    print(f"Selesai. Total artikel: {len(all_articles)} (+{max(added,0)} baru)")


if __name__ == "__main__":
    main()
