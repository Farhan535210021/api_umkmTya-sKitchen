# API UMKM Tya's Kitchen

API ini adalah backend dari aplikasi Android [Tya's Kitchen](https://github.com/Farhan535210021/Tya-s-Kitchen), yang dirancang untuk mendukung fitur manajemen produk, transaksi, rekomendasi produk, dan laporan analitik.

## Deskripsi

Backend ini dibangun menggunakan **Flask** sebagai framework dan **PostgreSQL** sebagai database. API ini mendukung fitur seperti:
- **Manajemen Produk**: CRUD produk.
- **Keranjang Belanja**: Penambahan, penghapusan produk, dan checkout.
- **Rekomendasi Produk**: Menggunakan algoritma Apriori untuk analisis keranjang belanja.
- **Riwayat Transaksi**: Menyimpan pesanan pengguna.
- **Rating Produk**: Mengumpulkan ulasan pengguna.
- **Laporan Penjualan**: Statistik bulanan untuk UMKM.

## Fitur Utama

1. **Manajemen Produk**
   - Tambah, ubah, dan hapus produk.
2. **Keranjang Belanja**
   - Tambah ke keranjang, checkout, dan ubah status transaksi.
3. **Rekomendasi Produk**
   - Saran produk berdasarkan analisis keranjang belanja.
4. **Riwayat Transaksi**
   - Dokumentasi pesanan pengguna.
5. **Rating Produk**
   - Menyimpan rating dan ulasan untuk setiap produk.
6. **Laporan Penjualan**
   - Total pendapatan, jumlah pesanan, dan total produk terjual.

## Teknologi yang Digunakan

- **Backend Framework**: Flask
- **Database**: PostgreSQL
- **Analitik**: Market Basket Analysis dengan Apriori
- **Testing API**: Postman
- **Deployment**: Docker (opsional)

## Cara Instalasi

1. **Clone Repository**
   ```bash
   git clone https://github.com/Farhan535210021/api_umkmTya-sKitchen.git
   cd api_umkmTya-sKitchen
