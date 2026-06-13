# QA Orkestrasyon & Obsidian Maps Graph UI — Kullanım Rehberi

Bu belge iki sistemi detaylıca açıklar:
1. **QA Agent Orkestrasyon** — AI tabanlı test planı üretimi ve yürütme pipeline'ı
2. **Obsidian Maps Graph UI** — Token kullanımını görselleştiren interaktif graph arayüzü

---

## Bölüm 1: QA Agent Orkestrasyon

### 1.1 Nedir, Ne Yapar?

QA Orkestrasyon sistemi, bir test görevi aldığında aşağıdaki 4 aşamalı AI pipeline'ını çalıştırır:

```
[Görev]
   │
   ▼
┌─────────┐   ┌─────────────┐   ┌──────────┐   ┌─────┐
│  PLAN   │──▶│   EXECUTE   │──▶│  REVIEW  │──▶│ FIX │ (opsiyonel)
│ (Opus)  │   │ (Sonnet/    │   │ (Codex)  │   │     │
└─────────┘   │  Haiku*)    │   └──────────┘   └─────┘
              └─────────────┘
```

> *Haiku: ComplexityAnalyzer task'ı EASY olarak değerlendirirse otomatik devreye girer (maliyet tasarrufu)

Her aşama şunları yapar:

| Aşama | Model | Çıktı |
|---|---|---|
| **PLAN** | Opus (en güçlü) | Test senaryolarının listesi ve yapısı |
| **EXECUTE** | Sonnet veya Haiku* | Çalıştırılabilir pytest kodu |
| **REVIEW** | Codex (Sonnet'in tersi) | Kod kalitesi değerlendirmesi + `QUALITY_SCORE: 85` |
| **FIX** | Sonnet (opsiyonel) | Review'da "critical" bulgu varsa ve skor < 80 ise tetiklenir |

---

### 1.2 Hızlı Başlangıç

#### Adım 1 — Ortamı hazırla

```bash
cp .env.example .env
# .env içinde ANTHROPIC_API_KEY değerini gerçek key ile değiştir

pip install -r requirements.txt
python main.py   # Orchestrator http://localhost:8000 adresinde başlar
```

#### Adım 2 — İlk orchestration çağrısı

```bash
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "mock",
    "test_type": "api",
    "task": "Test user login with valid credentials",
    "mode": "CODEX_CODEX",
    "budget_usd": 0.5
  }'
```

#### Adım 3 — Sonucu oku

```json
{
  "plan": "## Test Plan\n1. POST /v2/user/login ...",
  "execution": "import pytest\n\ndef test_login_valid():\n    ...",
  "review": "Code quality: Good. QUALITY_SCORE: 82",
  "fix": null,
  "quality_score": 82,
  "error": null,
  "token_report": { "total_cost_usd": 0.0023, "api_calls": 3, ... }
}
```

---

### 1.3 Test Profilleri

Her profil, hangi testlerin yapılabileceğini ve hangi işlemlerin yasak olduğunu tanımlar.

#### `mock` — Tam özellikli, yan etki yok

```bash
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "mock",
    "test_type": "e2e",
    "task": "Login, restaurant search, add to cart, checkout, track order"
  }'
```

- Tüm akışlar test edilebilir: login, sepet, ödeme, sipariş, kupon
- Gerçek API'ye dokunmaz — lokal mock servisi (port 8001) kullanır
- `test_type`: `api`, `web`, `mobile`, `e2e`

#### `web-prod-smoke` — Canlı site, sadece okuma

```bash
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "web-prod-smoke",
    "test_type": "prod-smoke",
    "task": "homepage loads, navigation tabs visible"
  }'
```

- Sadece `prod-smoke` test tipine izin verir
- Login, sepet, ödeme, sipariş kelimeleri içeren görevler **otomatik reddedilir**
- Gerçek `yemeksepeti.com` üzerinde salt okunur navigation

#### `mobile-android` / `mobile-ios` — Appium profilleri

```bash
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "mobile-android",
    "test_type": "mobile",
    "task": "open app, verify onboarding screens visible"
  }'
```

- App path `.env`'den alınır (`YEMEKSEPETI_ANDROID_APP`)
- Login submit ve checkout işlemleri engellenir

---

### 1.4 Modlar ve Maliyet Kontrolü

#### Mevcut modlar

```bash
# Hangi modlar var?
curl http://localhost:8000/api/modes | python -m json.tool
```

| Mod | Plan | Execute | Review | Kalite | Maliyet |
|---|---|---|---|---|---|
| `OPUS_SONNET` | Opus | Sonnet | Codex | En yüksek | Orta |
| `OPUS_CODEX` | Opus | Codex | Sonnet | Yüksek | Orta |
| `CODEX_SONNET` | Codex | Sonnet | Codex | İyi | Düşük |
| `CODEX_CODEX` | Codex | Codex | Sonnet | Kabul edilebilir | **En düşük** |

#### Bütçe kontrolü

```bash
# Max $0.10 harcama limiti
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "mock",
    "test_type": "api",
    "budget_usd": 0.10,
    "mode": "CODEX_CODEX"
  }'
```

> **Önemli:** `budget_usd` aşıldığında pipeline `BudgetExceededError` ile durur.
> Geçerli aralık: `0 < budget_usd ≤ 100`

#### Complexity routing (otomatik tasarruf)

`routing: true` (varsayılan) aktif olduğunda ComplexityAnalyzer her görevi puanlar:

```
Score ≥ 60 → HARD → Seçilen model ile çalış (Sonnet/Opus)
Score < 60 → EASY → Otomatik Haiku'ya geç (çok ucuz)
```

Neyi etkiler:
- Kısa, basit API testleri → Haiku
- E2E, auth, mobile, çok adımlı → Sonnet/Opus

```bash
# Görevin complexity skorunu önceden öğren
curl "http://localhost:8000/api/complexity/analyze?task=Test+user+login+with+valid+credentials"
```

```json
{
  "score": 45,
  "level": "EASY",
  "recommended_model": "haiku",
  "reasons": ["1 steps (+15)", "auth/login/token detected (+20)"]
}
```

---

### 1.5 API Referansı

#### `POST /api/orchestrate`

**Request body:**

| Alan | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `profile` | string | `"mock"` | Test profili: `mock`, `web-prod-smoke`, `mobile-android`, `mobile-ios` |
| `test_type` | string | `"all"` | `api`, `web`, `mobile`, `e2e`, `prod-smoke` |
| `task` | string | null | Özel görev açıklaması (boş bırakılırsa tüm docs kullanılır) |
| `mode` | string | null | `OPUS_SONNET`, `CODEX_CODEX` vb. (plan/execute modelini birlikte ayarlar) |
| `plan_model` | string | `opus` | `mode` yoksa ayrı ayarlanır |
| `execute_model` | string | `sonnet` | `mode` yoksa ayrı ayarlanır |
| `budget_usd` | float | `5.0` | Max harcama limiti (0 < değer ≤ 100) |
| `routing` | bool | `true` | Complexity routing aktif mi? |
| `compression` | string | `moderate` | `none`, `light`, `moderate`, `aggressive` |

**Başarılı response:**

```json
{
  "plan": "...",          // AI'ın ürettiği test planı
  "execution": "...",    // pytest kodu
  "review": "...",       // kalite değerlendirmesi
  "fix": null,           // kritik sorun varsa düzeltilmiş kod
  "quality_score": 82,   // 0-100 arası kalite skoru
  "error": null,         // hata varsa açıklaması
  "mode": "OPUS_SONNET",
  "test_type": "api",
  "token_report": { ... }
}
```

**Safety violation response:**

```json
{
  "error": "Safety policy violation",
  "violations": [
    { "code": "checkout", "message": "...", "matched": "checkout" }
  ],
  "safe_alternative": "Use profile=mock for cart, checkout..."
}
```

#### Diğer önemli endpoint'ler

```bash
GET /api/test-profiles      # Tüm profilleri ve güvenlik politikalarını listele
GET /api/token-report       # Güncel token/maliyet raporu
GET /api/graph              # Token flow graph verisi (JSON)
GET /api/complexity/analyze?task=... # Görev karmaşıklığı analizi
GET /api/status             # Servis durumu
GET /dashboard              # Dashboard UI (tarayıcıda aç)
GET /graph                  # İnteraktif graph UI (tarayıcıda aç)
GET /health                 # Health check
```

---

### 1.6 Compression Seviyeleri

Prompt ne kadar sıkıştırılır? Az sıkıştırma = daha iyi kalite, daha fazla token harcaması.

| Seviye | Ne Yapar | Ne Zaman Kullan |
|---|---|---|
| `none` | Prompt'a dokunmaz | Debug, kalite kritik |
| `light` | Gereksiz boşlukları kaldırır | Hassas testler |
| `moderate` | Filler cümleler + uzun JSON dizilerini kırpar | **Varsayılan, dengeli** |
| `aggressive` | JSON minify + kod bloklarını 30 satırda keser | Bütçe sıkışıksa |

```bash
# Agresif sıkıştırma
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"profile":"mock","test_type":"api","compression":"aggressive","budget_usd":0.1}'
```

---

### 1.7 Test Profili: Obsidian Maps

Orchestrator, Obsidian Maps plugin kodu için özel bir token profili içerir.

```bash
# Obsidian Maps prompt analizi
curl -X POST http://localhost:8000/api/token-profiles/obsidian-maps/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "local-first map plugin with loadData, saveData, registerEvent, typescript strict"}'
```

```json
{
  "profile_id": "obsidian-maps",
  "score": 87,
  "matched_rules": ["local_first", "settings_persistence", "cleanup_lifecycle", "strict_typescript"],
  "missing_rules": ["no_hidden_telemetry"],
  "savings_est": 0.31
}
```

```bash
# Prompt'u Obsidian Maps profiliyle sıkıştır
curl -X POST http://localhost:8000/api/token-profiles/obsidian-maps/compress \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Please make sure to implement the map view feature carefully", "stage": "EXECUTE"}'
```

---

### 1.8 n8n Üzerinden Orkestrasyon

n8n workflow'ları manuel veya zamanlanmış olarak orchestrator'ı tetikler:

**Mevcut workflow'lar:**

| Workflow | Tetikleyici | Profil | Açıklama |
|---|---|---|---|
| `api_only_pipeline` | Manuel | mock | 5 API testi, complexity routing ile |
| `complete_orchestration` | Her gece 02:00 | mock | Full E2E suite |
| `prod_smoke_pipeline` | Manuel | web-prod-smoke | Canlı site navigation kontrolü |
| `token_monitor` | Her saat | — | Budget aşımında Slack uyarısı |

**n8n UI'ye giriş:** `http://localhost:5678`
- Kullanıcı: `.env`'deki `N8N_BASIC_AUTH_USER`
- Şifre: `.env`'deki `N8N_BASIC_AUTH_PASSWORD`

**Workflow çalıştırma:**
1. Sol menüden workflow'u seç
2. Sağ üstten **Execute Workflow** tıkla
3. Execution sonucunu node node izle

---

### 1.9 Yaygın Hatalar

#### "Safety policy violation"

```json
{ "error": "Safety policy violation", "violations": [{"code": "checkout"}] }
```

**Neden:** `web-prod-smoke` veya mobile profillerinde `checkout`, `cart`, `payment`, `order`, `login submit` gibi kelimeler kullanıldı.

**Çözüm:** Görev açıklamasından bu kelimeleri kaldır veya `profile: "mock"` kullan.

#### "budget_usd must be positive" (HTTP 422)

```bash
# Hatalı
curl ... -d '{"budget_usd": -1}'

# Doğru
curl ... -d '{"budget_usd": 0.5}'
```

#### "BudgetExceededError" response'ta

`budget_usd` değerini artır veya `compression: "aggressive"` ile token harcamasını azalt.

#### "API unavailable: anthropic package is not installed"

`ANTHROPIC_API_KEY` eksik veya yanlış. `.env` dosyasını kontrol et.

---

## Bölüm 2: Obsidian Maps Graph UI

### 2.1 Nedir?

Obsidian Maps Graph UI, YemekTest Orchestrator'ın agent pipeline'ının token akışını **Obsidian graph view benzeri** bir force-directed graph olarak görselleştirir.

Her orchestration çalıştırıldığında sistem şunları takip eder:
- Hangi stage hangi modeli kullandı
- Kaç token tüketildi
- Ne kadar harcandı
- Stage'ler arasında kaç token aktarıldı

Bu veriler `/api/graph` endpoint'inden JSON olarak gelir ve graph UI'da canlı olarak gösterilir.

---

### 2.2 Graph UI'ı Açma

#### Tarayıcıdan (en kolay)

```bash
# Orchestrator'ı başlat
python main.py

# Tarayıcıda aç
open http://localhost:8000/graph
```

#### Dashboard'dan

`http://localhost:8000/dashboard` → **"Interaktif Graph Görünümü →"** butonuna tıkla.

#### Obsidian Plugin'den

1. Obsidian'da plugin'i yükle
2. `Cmd+P` (Mac) veya `Ctrl+P` (Windows) → **"Open map view"** komutunu çalıştır
3. Plugin settings'e giderek **Orchestrator URL** alanına `http://localhost:8000` yaz

---

### 2.3 Graph Arayüzü — Sol Panel

```
┌────────────────────┐
│    Graph view      │ ← Başlık
├────────────────────┤
│ Filters            │ ← Hangi stage'ler görünsün?
│  ● PLAN    ☑      │
│  ● EXECUTE ☑      │
│  ● REVIEW  ☑      │
│  ● FIX     ☑      │
│  ● ANALYZE ☑      │
├────────────────────┤
│ Display            │ ← Görsel ayarlar
│  Node size  ────● │
│  Link thick ────● │
│  Text fade  ────● │
├────────────────────┤
│ Forces             │ ← Fizik simülasyonu
│  Center force ──● │
│  Repel force  ──● │
│  Link force   ──● │
│  [Animate]        │
│  [Auto-refresh:ON]│
├────────────────────┤
│ Nodes: 4          │ ← Anlık istatistikler
│ Edges: 3          │
│ Total tokens: 8.2K│
│ Total cost: $0.024│
└────────────────────┘
```

---

### 2.4 Node Renk Anlamları

| Renk | Stage | Açıklama |
|---|---|---|
| Mavi `#4a9eff` | PLAN | Test planı oluşturma |
| Yeşil `#43e97b` | EXECUTE | Kod üretimi |
| Turuncu `#ff9f43` | REVIEW | Kalite değerlendirmesi |
| Kırmızı `#ff6b6b` | FIX | Kritik sorun düzeltmesi |
| Mor `#a29bfe` | ANALYZE | Complexity analizi |

Node **boyutu** kullanılan token miktarıyla orantılıdır — büyük node = çok token.

---

### 2.5 Kontroller ve Etkileşim

#### Node üzerine gel (Hover)

```
┌─────────────────────────┐
│ EXECUTE                 │
│ claude-sonnet-4-...     │
│ Tokens    │ 4,200       │
│ Cost      │ $0.0021     │
│ Calls     │ 3           │
└─────────────────────────┘
```

#### Node'a tıkla

Seçilen node'a otomatik zoom yapar (3× büyütme, 600ms animasyon).

#### Filters

Belirli stage'leri gizle/göster. Örneğin FIX node'u hiç tetiklenmediyse göstermek anlamsız.

#### Display — Node size

Slider'ı sağa çektikçe tüm node'lar büyür. Çok fazla node varsa küçük değer daha okunaklı.

#### Display — Link thickness

Kenar kalınlığı çarpanı. Büyük değer = token akışı daha belirgin.

#### Display — Text fade threshold

Zoom seviyesinin kaçta bir'inde label'lar görünür hale gelsin. `60` = %60 zoom'da etiketler belirir.

#### Forces — Center force

Node'ların merkeze çekilme kuvveti. `0` = merkeze çekilme yok, `1` = çok güçlü.

#### Forces — Repel force

Node'ların birbirini itme kuvveti. Daha negatif = node'lar daha ayrışık durur.

#### Forces — Link force

Bağlı node'ların birbirine yaklaşma kuvveti. Yüksek değer = bağlı olanlar kümelenir.

#### Animate butonu

Fizik simülasyonunu yeniden ısıtır — node'lar hareket eder ve yeni denge noktası bulur. Güzel animasyon için kullan.

#### Auto-refresh

`ON` iken her 10 saniyede bir `/api/graph` verisi güncellenir. Canlı izleme için kullan.

---

### 2.6 Graph Verisi — Teknik Format

`GET /api/graph` endpoint'i şunu döner:

```json
{
  "nodes": [
    {
      "id": "PLAN:opus",
      "label": "PLAN",
      "model": "claude-opus-4-20250514",
      "total_tok": 3200,
      "total_cost": 0.048,
      "call_count": 2
    },
    {
      "id": "EXECUTE:sonnet",
      "label": "EXECUTE",
      "model": "claude-sonnet-4-20250514",
      "total_tok": 8400,
      "total_cost": 0.025,
      "call_count": 5
    }
  ],
  "edges": [
    {
      "source": "PLAN:opus",
      "target": "EXECUTE:sonnet",
      "tokens_passed": 2500,
      "weight": 2.5
    }
  ]
}
```

- `id`: `{STAGE}:{model_kısa_adı}` formatında
- `weight`: `(total_tokens / 1000)` — kenar kalınlığı için kullanılır
- `tokens_passed`: Bu geçişte aktarılan input token sayısı

---

### 2.7 Obsidian Plugin Kurulumu

#### Adım 1 — Plugin'i derle

```bash
cd obsidian_maps_plugin
npm install
npm run build
# Çıktı: main.js (plugin root'unda)
```

#### Adım 2 — Obsidian'a yükle

```
Obsidian Vault klasörüne git:
.obsidian/
  plugins/
    obsidian-maps/       ← Bu klasörü oluştur
      main.js            ← Build çıktısı
      manifest.json      ← Plugin manifest
```

`manifest.json` içeriği:
```json
{
  "id": "obsidian-maps",
  "name": "Obsidian Maps",
  "version": "1.0.0",
  "minAppVersion": "1.4.0",
  "description": "YemekTest token flow graph viewer",
  "author": "YemekTest",
  "isDesktopOnly": false
}
```

#### Adım 3 — Plugin'i aktif et

Obsidian → **Settings** → **Community plugins** → **Installed plugins** → **Obsidian Maps** → Toggle ON

#### Adım 4 — Orchestrator URL'ini ayarla

Obsidian → **Settings** → **Obsidian Maps** → **Orchestrator URL** → `http://localhost:8000`

#### Adım 5 — Graph view'ı aç

`Cmd+P` (Mac) / `Ctrl+P` (Windows) → **"Open map view"** yazıp Enter

---

### 2.8 Örnek Senaryo: Canlı İzleme

```bash
# Terminal 1 — Orchestrator başlat
python main.py

# Terminal 2 — Mock API başlat
uvicorn mock_api.server:app --port 8001

# Tarayıcı 1 — Graph UI aç
open http://localhost:8000/graph   # Auto-refresh ON durumda

# Terminal 3 — Orchestration başlat
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "mock",
    "test_type": "e2e",
    "task": "Full E2E: login, restaurant search, add to cart, apply coupon, checkout, track order",
    "mode": "OPUS_SONNET",
    "budget_usd": 1.0
  }'
```

Graph UI'da 10 saniye içinde node'ların belirdiğini ve stage geçişlerinin kenarlarla bağlandığını göreceksin.

---

### 2.9 Sık Sorulan Sorular

**Soru: Graph boş görünüyor.**
> `POST /api/orchestrate` henüz çağrılmamış. En az bir orchestration çalıştır, sonra sayfayı yenile veya auto-refresh bekle.

**Soru: Obsidian plugin'de "Cannot reach orchestrator" hatası.**
> Settings → Obsidian Maps → Orchestrator URL'nin `http://localhost:8000` olduğunu doğrula. Orchestrator'ın (`python main.py`) çalıştığından emin ol.

**Soru: Node'lar üst üste geliyor.**
> Sol panelde **Repel force** slider'ını daha negatif bir değere çek (ör. -300). Ardından **Animate** butonuna bas.

**Soru: Çok fazla edge var, karmaşık görünüyor.**
> **Filters** panelinden az kullanılan stage'leri (ör. FIX, ANALYZE) kaldır.

**Soru: Graph'taki maliyet gerçek mi?**
> Evet. `total_cost` değerleri Anthropic'in fiyatlandırma tablosuna göre hesaplanır ve `token_optimizer_data.json`'a kalıcı olarak kaydedilir.

**Soru: Graph verisi sıfırlanıyor mu?**
> Orchestrator yeniden başlatılırsa `token_optimizer_data.json`'dan veri yüklenir — sıfırlanmaz. Sıfırlamak için dosyayı sil veya `/api/status`'u kontrol et.

---

## Hızlı Komut Referansı

```bash
# ── Servisler ──────────────────────────────────────────────────────
python main.py                              # Orchestrator (port 8000)
uvicorn mock_api.server:app --port 8001    # Mock API
cd mock_ui && npm run dev                  # Mock UI (port 3000)
docker compose up                          # Tüm stack (n8n dahil)

# ── Test çalıştırma ────────────────────────────────────────────────
pytest tests/                              # Tüm testler
pytest tests/test_yemeksepeti_profiles.py  # Profil testleri
pytest tests/test_token_profiles.py        # Token profil testleri
pytest tests/test_n8n_security.py          # n8n güvenlik testleri

# ── Orchestration ──────────────────────────────────────────────────
# En ucuz mod (CODEX_CODEX + complexity routing)
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"profile":"mock","test_type":"api","mode":"CODEX_CODEX","budget_usd":0.1}'

# En kaliteli mod (OPUS_SONNET)
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"profile":"mock","test_type":"e2e","mode":"OPUS_SONNET","budget_usd":2.0}'

# Prod smoke (canlı site, salt okuma)
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"profile":"web-prod-smoke","test_type":"prod-smoke","mode":"CODEX_SONNET","budget_usd":0.5}'

# ── İzleme ─────────────────────────────────────────────────────────
curl http://localhost:8000/api/token-report | python -m json.tool
curl http://localhost:8000/api/graph | python -m json.tool
open http://localhost:8000/dashboard
open http://localhost:8000/graph

# ── Complexity analizi ─────────────────────────────────────────────
curl "http://localhost:8000/api/complexity/analyze?task=gel+al+akışı+sepet+ve+ödeme"

# ── Obsidian Maps token profili ────────────────────────────────────
curl -X POST http://localhost:8000/api/token-profiles/obsidian-maps/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "your plugin code or prompt here"}'
```
