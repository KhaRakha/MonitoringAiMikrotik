# Panduan Menjalankan Bot MikroTik AI 24/7 (Always-On)

Panduan ini menjelaskan cara membuat sistem **MikroTik AI Agent Automation** berjalan otomatis terus-menerus tanpa henti (**24/7 Always-On**), baik saat menggunakan laptop sendiri maupun saat laptop dimatikan total.

---

## ⚠️ Konsep Dasar: Apakah Program Bisa Jalan Saat Laptop Mati?

Secara teknis arsitektur komputer:
> **Jika laptop mati total (Shutdown / Power Off / Tidak Ada Listrik)**, arus listrik ke Prosesor (CPU), RAM, dan Sistem Operasi terputus sepenuhnya. **Tidak ada software di dunia yang bisa berjalan di dalam laptop yang sedang mati total.**

Namun, ada **dua skenario** yang bisa Anda pilih sesuai kebutuhan:

1. **Skenario A (Biaya Rp 0 - Pakai Laptop Sendiri)**:
   Laptop **tetap hidup sebagai server mini**, tetapi **layar ditutup (Lid Closed)** dan ditaruh di pojokan meja. Layar laptop mati menghemat daya dan umur LCD, tetapi bot tetap berjalan memantau jaringan 24 jam nonstop.
2. **Skenario B (Laptop Benar-Benar Mati Total & Dibawa Pergi)**:
   Bot dipindahkan ke **Cloud VPS** (misal: Oracle Cloud Gratis Selamanya / VPS murah) atau **Mini PC / STB Armbian Bekas** yang colok di router kantor/lab 24 jam.

---

## 🚀 Skenario A: Laptop Mode Server 24/7 (Layar Ditutup Tetap Nyala)

Jika Anda ingin menggunakan laptop Anda sendiri tanpa biaya tambahan:

### 1. Jalankan Skrip 1-Klik Setup Always-On
Buka folder `service/` di File Explorer, lalu:
1. Klik kanan pada file **`setup_laptop_always_on.bat`** -> Pilih **Run as Administrator** (atau double click).
2. Skrip akan otomatis:
   * Mengatur Windows agar **TIDAK SLEEP / TIDAK MATI** saat layar laptop ditutup (saat charger terpasang).
   * Menonaktifkan batas waktu sleep (*Never Sleep*).
   * Mendaftarkan bot ke **Windows Startup** dan **Scheduled Task** agar setiap kali laptop dinyalakan/restart, bot langsung otomatis aktif di background.

### 2. Cara Menggunakannya Sehari-hari
1. Pastikan **charger laptop terpasang**.
2. Tutup layar laptop Anda.
3. Layar akan mati, tetapi bot AI Telegram tetap aktif memantau MikroTik 24/7 di latar belakang.
4. Anda bisa memeriksa status bot kapan saja dengan menjalankan:
   ```powershell
   powershell service/status_bot.ps1
   ```

---

## ☁️ Skenario B: Deploy ke Cloud VPS (Laptop Bebas Mati Total)

Jika Anda ingin laptop pribadi bisa **dimatikan total, dimasukkan ke tas, atau dibawa bepergian**, pindahkan bot ke VPS (Virtual Private Server) yang menyala 24/7 di datacenter.

### Rekomendasi Penyedia VPS:
* **Oracle Cloud Always Free** (100% **GRATIS Selamanya**, spesifikasi ARM Ampere hingga 4 OCPU & 24GB RAM).
* **VPS Lokal Indonesia** (Domainesia, IdCloudHost, Biznet Gio, Nevacloud mulai Rp 30.000 - Rp 50.000/bulan).
* **Cloud Internasional** (DigitalOcean, Linode, Hetzner mulai $4/bulan).

---

### 🌐 Tantangan Jaringan: Menghubungkan VPS ke MikroTik Kantor/Lab

Router MikroTik di kantor/lab (`10.20.33.240` atau `192.168.88.1`) berada di jaringan IP lokal (Private IP). Bagaimana VPS di cloud internet bisa mengaksesnya?

Pilih salah satu dari 2 metode standar industri berikut:

#### Metode 1: ZeroTier (Paling Mudah, Gratis & Native di RouterOS v7)
1. Buat akun gratis di [zerotier.com](https://www.zerotier.com) dan buat Network baru.
2. Di MikroTik (RouterOS v7):
   ```routeros
   /zerotier/interface/add network=<Network-ID-Anda> name=zt1
   /zerotier/enable zt1
   ```
3. Di VPS Linux:
   ```bash
   curl -s https://install.zerotier.com | sudo bash
   sudo zerotier-cli join <Network-ID-Anda>
   ```
4. Centang tombol **Auth** di dashboard ZeroTier untuk kedua perangkat.
5. Sekarang VPS dan MikroTik berada dalam 1 jaringan lokal virtual yang aman! Masukkan IP ZeroTier MikroTik ke `config/devices.yaml`.

#### Metode 2: WireGuard / IP Cloud DDNS
* Jika router MikroTik memiliki IP Publik, aktifkan DDNS bawaan MikroTik:
  ```routeros
  /ip/cloud/set ddns-enabled=yes
  ```
  Lalu gunakan DNS Name MikroTik (`*.sn.mynetname.net`) di `config/devices.yaml`.
* Atau gunakan **WireGuard VPN** yang sudah ada di menu `/interface/wireguard` RouterOS v7.

---

### 📦 Cara Deploy di VPS Linux

Proyek ini sudah dilengkapi dengan konfigurasi **Docker** dan **Systemd**.

#### Pilihan 1: Menggunakan Docker Compose (Paling Direkomendasikan)
1. Clone repositori ke VPS:
   ```bash
   git clone <URL_REPO_ANDA> mikrotik-ai
   cd mikrotik-ai
   ```
2. Salin dan isi konfigurasi `.env` (Token Telegram & API Key Gemini):
   ```bash
   cp .env.example .env
   nano .env
   ```
3. Jalankan container di latar belakang:
   ```bash
   docker compose up -d --build
   ```
4. Cek log bot:
   ```bash
   docker compose logs -f
   ```
   > **Catatan**: Container menggunakan `restart: always`, sehingga jika VPS reboot atau listrik datacenter restart, bot otomatis hidup kembali.

#### Pilihan 2: Menggunakan Systemd Linux Service (1-Klik Installer)
Jika VPS Anda tidak memiliki Docker, gunakan installer otomatis bawaan proyek ini:
```bash
sudo bash service/deploy_linux.sh
```
Skrip ini akan otomatis:
* Menginstall Python 3, pip, dan dependensi sistem.
* Menyiapkan virtual environment (`venv`).
* Mendaftarkan service `mikrotik-ai.service` ke `systemd`.
* Mengaktifkan auto-start saat VPS booting (`systemctl enable mikrotik-ai`).

Perintah manajemen bot di VPS:
```bash
# Cek status bot
systemctl status mikrotik-ai

# Lihat log aktivitas bot realtime
journalctl -u mikrotik-ai -f

# Restart bot
systemctl restart mikrotik-ai

# Stop bot
systemctl stop mikrotik-ai
```

---

## 🍓 Skenario C: Mini Server Lokal / STB TV Android Bekas (Hemat Biaya)

Jika Anda tidak ingin menyewa VPS dan tidak ingin memakai laptop:

1. Beli **STB TV Android Bekas** (tipe ZTE B860H atau Fiberhome HG680P) seharga **Rp 70.000 - Rp 90.000** di e-commerce.
2. Flash dengan **Linux Armbian**.
3. Colokkan kabel LAN STB ke switch / router MikroTik kantor atau lab.
4. Konsumsi daya STB hanya **3 - 5 Watt** (biaya listrik hanya ~Rp 3.000/bulan).
5. Jalankan `sudo bash service/deploy_linux.sh` di dalam STB.
6. Bot MikroTik AI Anda sekarang aktif 24 jam nonstop langsung di jaringan lokal tanpa perlu VPN dan tanpa laptop!

---

## 📋 Ringkasan Perbandingan Solusi

| Solusi | Status Laptop | Biaya | Akses Jaringan Lokal | Kompleksitas |
| :--- | :--- | :--- | :--- | :--- |
| **Skenario A: Laptop Clamshell** | Layar ditutup, dicolok charger | **Gratis (Rp 0)** | Langsung (LAN / WiFi) | **Sangat Mudah (1 Klik)** |
| **Skenario B: Cloud VPS (Oracle Free)** | **Mati Total / Dibawa Pergi** | **Gratis** | Butuh ZeroTier / WireGuard | Menengah |
| **Skenario B: Cloud VPS (Lokal)** | **Mati Total / Dibawa Pergi** | Rp 30rb - 50rb/bln | Butuh ZeroTier / WireGuard | Menengah |
| **Skenario C: STB Armbian / Raspi** | **Mati Total / Dibawa Pergi** | ~Rp 80rb (Sekali beli) | Langsung (Kabel LAN) | Mudah - Menengah |

---

## 🛠️ Langkah Cepat yang Harus Anda Lakukan Sekarang:

Jika Anda ingin langsung aktif sekarang di laptop ini:
1. Hubungkan kabel charger ke laptop.
2. Jalankan `service\setup_laptop_always_on.bat`.
3. Tutup layar laptop Anda. Bot sudah langsung aktif 24 jam!
