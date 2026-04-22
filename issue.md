# Frontend API Integration Issues

Berikut adalah daftar GitHub Issues yang sudah diperluas dengan langkah-langkah detail, penjelasan teknis, dan *Definition of Done* (DoD) agar mudah dikerjakan oleh Junior Software Engineer atau AI model (seperti Cursor/Copilot). 

Anda dapat menyalin teks ini langsung ke GitHub Issues, atau menambahkannya ke dalam file `epic-12-dashboard.md` Anda mulai dari nomor `T-12.15`.

---

## T-12.15: Setup API Client & State Management (React Query)

**Labels:** `epic-12`, `dashboard`, `api`, `priority-critical`
**Milestone:** Fase 5 — Interface

### Deskripsi
Frontend saat ini belum memiliki utilitas standar untuk melakukan request ke backend FastAPI dan belum ada manajemen *state* untuk auto-refresh data. Kita akan menggunakan Axios untuk HTTP client dan React Query untuk data fetching & caching.

### Langkah-Langkah (Step-by-Step)
1. **Install Dependencies:**
   Jalankan perintah `npm install axios @tanstack/react-query` di folder `frontend/`.
2. **Buat API Client (`src/lib/api.ts`):**
   - Buat instance Axios baru.
   - Atur `baseURL` mengambil dari `process.env.NEXT_PUBLIC_API_URL` (fallback ke `http://localhost:8000`).
   - Tambahkan *Request Interceptor* untuk menyisipkan header `Authorization: Bearer <token>` jika token JWT tersedia di `localStorage` atau cookies.
3. **Setup React Query Provider:**
   - Buat komponen `src/components/providers/QueryProvider.tsx` yang membungkus `children` dengan `QueryClientProvider`.
   - Konfigurasi default `QueryClient` dengan `staleTime: 5000` (5 detik) agar tidak terlalu sering memanggil API.
   - Bungkus aplikasi di `src/app/layout.tsx` menggunakan `QueryProvider` tersebut.

### Definition of Done
- [ ] `axios` dan `@tanstack/react-query` terinstall.
- [ ] `api.ts` terkonfigurasi dengan interceptor JWT.
- [ ] Aplikasi berjalan tanpa error dengan `QueryClientProvider` di root layout.

---

## T-12.16: Integrasi Data Portfolio (OverviewCards.tsx)

**Labels:** `epic-12`, `dashboard`, `integration`, `priority-high`
**Milestone:** Fase 5 — Interface
**Depends On:** T-12.15

### Deskripsi
Mengganti data statistik dummy (seperti Total Balance, PnL, Win Rate) pada komponen `OverviewCards.tsx` dengan data *real-time* dari endpoint `/api/portfolio/summary`.

### Langkah-Langkah (Step-by-Step)
1. **Definisikan Interface (TypeScript):**
   Buat interface `PortfolioSummary` di `src/types/api.ts` yang berisi: `balance`, `equity`, `total_pnl`, `daily_pnl`, `win_rate`, dan `total_trades`.
2. **Buat Custom Hook (`usePortfolioSummary`):**
   Gunakan `useQuery` dari React Query untuk melakukan `GET` ke `/api/portfolio/summary` menggunakan API client yang dibuat di T-12.15. Atur `refetchInterval: 10000` (polling setiap 10 detik).
3. **Integrasi ke Komponen:**
   - Buka `src/components/dashboard/OverviewCards.tsx`.
   - Hapus variabel konstanta `stats` yang berisi data dummy.
   - Panggil `const { data, isLoading } = usePortfolioSummary()`.
   - Petakan `data` ke kartu-kartu yang ada.
4. **Implementasi Loading State:**
   Jika `isLoading` bernilai `true`, tampilkan komponen Skeleton (`<Skeleton className="h-20 w-full" />`) dari shadcn/ui sebagai pengganti angka agar UI tidak kosong saat data di-fetch.

### Definition of Done
- [ ] Endpoint `/api/portfolio/summary` berhasil dipanggil.
- [ ] Data yang tampil di `OverviewCards` sesuai dengan database backend.
- [ ] Terdapat efek loading (skeleton) saat data belum siap.

---

## T-12.17: Integrasi Bot Control & Mode (BotControl.tsx)

**Labels:** `epic-12`, `dashboard`, `integration`, `priority-critical`
**Milestone:** Fase 5 — Interface
**Depends On:** T-12.15

### Deskripsi
Menghubungkan *switch* "System Operation" (On/Off) dan mode (Paper/Live) ke endpoint backend, sehingga UI ini benar-benar bisa mengontrol mesin trading.

### Langkah-Langkah (Step-by-Step)
1. **Fetch Initial State:**
   Gunakan `useQuery` untuk memanggil `GET /api/bot/status` saat komponen di-mount. Gunakan data ini untuk mengisi nilai awal `isRunning` dan `mode`.
2. **Buat Mutation Hooks (`useMutation`):**
   - `useToggleBot`: Memanggil `POST /api/bot/start` atau `POST /api/bot/stop`.
   - `useChangeMode`: Memanggil `POST /api/bot/mode` dengan payload `{ mode: 'live' | 'paper' }`.
3. **Update UI Logic:**
   - Saat switch diklik, jalankan fungsi mutasi. Jika mutasi *pending*, *disable* (nonaktifkan) switch agar user tidak klik berkali-kali.
   - Gunakan `toast.success` jika API mengembalikan respons 200 OK.
   - Jika API mengembalikan error (misal gagal ganti ke Live karena belum 14 hari), tangkap error di blok `onError`, tampilkan `toast.error`, dan kembalikan posisi UI ke state semula.

### Definition of Done
- [ ] Switch On/Off benar-benar menyalakan/mematikan bot di backend.
- [ ] Pilihan mode Paper/Live terhubung dengan validasi backend.
- [ ] Switch menjadi *disabled* saat *loading request*.

---

## T-12.18: Integrasi Tabel Open Positions (PositionsTable.tsx)

**Labels:** `epic-12`, `dashboard`, `integration`, `priority-high`
**Milestone:** Fase 5 — Interface
**Depends On:** T-12.15

### Deskripsi
Menampilkan daftar posisi trading yang sedang aktif (terbuka) di bursa dengan memanggil API backend, menggantikan array dummy `positions`.

### Langkah-Langkah (Step-by-Step)
1. **Definisikan Interface:**
   Buat interface `OpenPosition` dengan atribut seperti `symbol`, `side`, `size`, `entry_price`, `current_price`, `unrealized_pnl`, dll.
2. **Data Fetching:**
   Gunakan `useQuery` untuk fetch `GET /api/portfolio/positions`. Atur `refetchInterval: 5000` agar tabel sering ter-update (karena harga bergerak cepat).
3. **Map Data ke Tabel:**
   Di `src/components/dashboard/PositionsTable.tsx`, loop melalui data API, bukan dummy array.
4. **Fungsi Close Position:**
   - Tambahkan `useMutation` untuk `POST /api/trades/close/{symbol}`.
   - Pasangkan fungsi ini pada tombol "Close Position" di setiap baris.
   - Berikan konfirmasi singkat (modal/alert) sebelum memanggil API close position untuk mencegah salah klik.

### Definition of Done
- [ ] Tabel menampilkan posisi dari bursa yang sebenarnya.
- [ ] Tabel otomatis memperbarui harga/PnL setiap 5 detik.
- [ ] Tombol "Close Position" berfungsi dan memicu penutupan trade.

---

## T-12.19: Integrasi AI Insights (page.tsx)

**Labels:** `epic-12`, `dashboard`, `ai`, `priority-medium`
**Milestone:** Fase 5 — Interface
**Depends On:** T-12.15

### Deskripsi
Mengganti teks hardcoded narasi sentimen AI (*"Trend BTC dominan BULLISH..."*) dengan analisis nyata dari agen LLM di backend.

### Langkah-Langkah (Step-by-Step)
1. **Data Fetching:**
   Buat hook `useQuery` untuk `GET /api/agents/insights` yang mengembalikan objek berisi `{ narrative: string, scores: { technical: number, sentiment: number, onchain: number } }`.
2. **Render Narasi Dinamis:**
   Di `page.tsx` (atau pisahkan ke komponen `AIInsightCard.tsx`), ganti teks deskripsi dengan variabel `data.narrative`.
3. **Update Progress Bar Confidence:**
   Petakan nilai `data.scores.technical`, `sentiment`, dan `onchain` ke lebar `width: \${value}%` pada progress bar.

### Definition of Done
- [ ] Narasi AI insight berasal dari backend API.
- [ ] Persentase *Active Confidence* merender nilai asli dari backend.

---

## T-12.20: Sinkronisasi Manual (Tombol Run Sync)

**Labels:** `epic-12`, `dashboard`, `ui`, `priority-low`
**Milestone:** Fase 5 — Interface
**Depends On:** T-12.15

### Deskripsi
Memfungsikan tombol "Run Sync" agar pengguna bisa memaksa pembaruan seluruh data secara manual tanpa harus menunggu *auto-polling* dari React Query.

### Langkah-Langkah (Step-by-Step)
1. **Akses Query Client:**
   Di dalam `page.tsx`, gunakan hook `const queryClient = useQueryClient()`.
2. **Buat Handler Sinkronisasi:**
   - Buat fungsi `handleSync` yang menjalankan `queryClient.invalidateQueries()`. Ini akan memaksa React Query mengambil ulang semua data dari backend.
   - Tambahkan `state` lokal `isSyncing` untuk mengontrol animasi rotasi pada icon `<Zap />` (`animate-spin`).
3. **Trigger Notifikasi:**
   Setelah invalidasi selesai, tampilkan `toast.success("Data successfully synchronized!")`.

### Definition of Done
- [ ] Tombol "Run Sync" memiliki animasi berputar saat diklik.
- [ ] Semua komponen di dashboard (*cards*, *tables*, *insights*) otomatis melakukan *refetch* saat tombol diklik.
