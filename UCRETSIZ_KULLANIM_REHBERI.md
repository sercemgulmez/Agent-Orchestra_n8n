# Ücretsiz / Düşük Maliyetli Kullanım Rehberi

Bu belge, YemekTest Orchestrator + n8n stack'ini sıfır veya minimum maliyetle çalıştırmak için üç farklı yolu detaylıca açıklar.

---

## Maliyet Haritası

| Bileşen | Maliyet | Açıklama |
|---|---|---|
| Docker (n8n, PostgreSQL, Redis) | **Ücretsiz** | Lokal çalışır |
| FastAPI Orchestrator | **Ücretsiz** | Lokal çalışır |
| Mock API / Mock UI | **Ücretsiz** | Lokal çalışır |
| Anthropic API (`/api/orchestrate`) | **Ücretli** | Her çağrıda token bedeli |
| Slack Webhook | **Ücretsiz** | Slack'ın ücretsiz planında da çalışır |

**Sonuç:** Tek ücretli parça `ANTHROPIC_API_KEY` gerektiren AI pipeline'ı. Aşağıdaki yollardan biri ile bu maliyeti sıfıra veya minimuma indirebilirsin.

---

## Yol 1 — AI Olmadan Stack Testi (Tam Ücretsiz)

API key olmadan n8n'nin tüm plumbing'ini (trigger → HTTP → safety check → token report) test edebilirsin. Orchestrator API hatası aldığında `QUALITY_SCORE: 75` ile mock yanıt döner ve workflow tamamlanır.

### Adım 1 — .env Oluştur

```bash
cp .env.example .env
```

`.env` içinde şunları ayarla (gerçek key gerekmez):

```bash
ANTHROPIC_API_KEY=sk-ant-fake-key-for-testing   # sahte, çalışmaz ama crash etmez
POSTGRES_PASSWORD=yemektest
N8N_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=guclu-bir-sifre-yaz
N8N_WEBHOOK_URL=http://localhost:5678
TOKEN_BUDGET_USD=0.0   # harcama limiti sıfır → API çağrısı yapılmaz
```

### Adım 2 — Stack'i Başlat

```bash
docker compose up --build
```

Servis başlatma sırası (otomatik):
```
postgres → redis → mock-api → orchestrator → n8n
```

### Adım 3 — n8n UI'ye Giriş

Tarayıcıda: `http://localhost:5678`
- Kullanıcı: `.env`'deki `N8N_BASIC_AUTH_USER`
- Şifre: `.env`'deki `N8N_BASIC_AUTH_PASSWORD`

Sol panelde 4 workflow otomatik yüklenmiş olmalı:
- `api_only_pipeline`
- `complete_orchestration`
- `prod_smoke_pipeline`
- `token_monitor`

### Adım 4 — Manuel Workflow Testi

1. `api_only_pipeline` workflow'unu aç
2. Sağ üstten **Execute Workflow** tıkla
3. Workflow çalışır → orchestrator API error döner → n8n `QUALITY_SCORE: 75` ile tamamlar
4. Token Monitor: `http://localhost:8000/api/token-report` endpoint'ini poll eder

### Adım 5 — Orchestrator'ı Doğrula

```bash
# Orchestrator sağlıklı mı?
curl http://localhost:8000/health

# Test profilleri listeleniyor mu?
curl http://localhost:8000/api/test-profiles | python -m json.tool

# Sahte key ile orchestrate (mock response döner)
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"profile":"mock","test_type":"api","mode":"CODEX_CODEX","budget_usd":0.1}'
```

### Ne Test Edilmiş Olur?

- n8n workflow import mekanizması
- n8n → orchestrator HTTP bağlantısı
- Safety policy kontrolleri
- Token report polling
- Docker network (yemektest bridge)
- Healthcheck zincirleri

### Ne Test Edilmemiş Olur?

- Gerçek AI test planı ve kod üretimi (API key gerekir)

---

## Yol 2 — Anthropic Ücretsiz Kredi ile Gerçek Kullanım

Anthropic yeni hesaplara **$5 ücretsiz kredi** veriyor. Haiku modeli ile bu kredi onlarca orchestration için yeterli.

### Fiyatlandırma Tablosu

| Model | Input (1M token) | Output (1M token) | Tipik Çağrı Maliyeti |
|---|---|---|---|
| claude-haiku-4-5-20251001 | $0.80 | $4.00 | ~$0.001 |
| claude-sonnet-4-20250514 | $3.00 | $15.00 | ~$0.005 |
| claude-opus-4-20250514 | $15.00 | $75.00 | ~$0.05 |

**$5 kredi ile:**
- Haiku: ~5.000 orchestration çağrısı
- Sonnet: ~1.000 orchestration çağrısı
- Opus: ~100 orchestration çağrısı

### Adım 1 — API Key Al

1. [console.anthropic.com](https://console.anthropic.com) adresinde hesap aç
2. **API Keys** → **Create Key**
3. Key'i kopyala (bir daha gösterilmez)

### Adım 2 — .env Ayarla (Maksimum Tasarruf İçin)

```bash
# Gerçek key
ANTHROPIC_API_KEY=sk-ant-api03-...

# Harcama limiti — her orchestration için max $0.10
TOKEN_BUDGET_USD=0.10

# Diğer zorunlu değişkenler
POSTGRES_PASSWORD=yemektest
N8N_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=guclu-bir-sifre-yaz
N8N_WEBHOOK_URL=http://localhost:5678
```

### Adım 3 — En Ucuz Modu Kullan

n8n workflow'larında veya direkt API çağrısında `mode: "CODEX_CODEX"` kullan:

```bash
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "mock",
    "test_type": "api",
    "mode": "CODEX_CODEX",
    "budget_usd": 0.05
  }'
```

### Adım 4 — Complexity Routing'i Aktif Tut

`routing: true` (varsayılan) olduğunda:
- `COMPLEXITY_THRESHOLD=60` altında kalan tasklar → otomatik **Haiku**'ya yönlenir
- Basit API testleri genellikle Haiku'ya düşer → çok ucuz

`.env`'de agresif tasarruf için:
```bash
COMPLEXITY_THRESHOLD=90   # Neredeyse hepsini Haiku'ya yönlendir
QUALITY_THRESHOLD=60       # FIX stage'i daha az tetikle
TOKEN_BUDGET_USD=0.05      # Hard limit
```

### Adım 5 — Harcama Takibi

```bash
# Anlık token/maliyet raporu
curl http://localhost:8000/api/token-report | python -m json.tool

# Token grafiği (her stage için ayrı)
curl http://localhost:8000/api/graph | python -m json.tool

# Dashboard (tarayıcıda)
open http://localhost:8000/dashboard
```

### n8n'den Workflow Tetikleme (Ücretsiz Kredi İle)

1. n8n UI: `http://localhost:5678`
2. `api_only_pipeline` → **Execute Workflow**
   - 5 API testi çalışır, her biri ~$0.001 (Haiku ile)
   - Toplam: ~$0.005
3. `complete_orchestration` → Nightly cron (02:00) veya manuel tetikle
   - Full E2E, Opus+Sonnet: ~$0.05–0.10

---

## Yol 3 — Groq Ücretsiz API ile Entegrasyon (Kod Değişikliği)

[Groq](https://console.groq.com) ücretsiz bir tier sunuyor: dakikada 30 istek, günde 14.400 istek. LLaMA 3.1 / Mixtral modelleri kullanılıyor.

**Anthropic SDK'sı yerine OpenAI-uyumlu endpoint kullanacağız** — Groq, OpenAI formatıyla çalışır.

### Adım 1 — Groq API Key Al

1. [console.groq.com](https://console.groq.com) → hesap aç (ücretsiz)
2. **API Keys** → **Create API Key**

### Adım 2 — Bağımlılığı Ekle

```bash
pip install groq
```

`requirements.txt`'e ekle:
```
groq>=0.9.0
```

### Adım 3 — `agents/flexible_coordinator.py` Değişikliği

`MultiAgentCoordinator.__init__` metodunda (satır 84–88) Anthropic istemcisini koşullu hale getir:

```python
# Mevcut (satır 84–88):
self._client = (
    anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    if anthropic is not None
    else None
)

# Yeni hali:
_use_groq = os.environ.get("LLM_PROVIDER", "anthropic") == "groq"
if _use_groq:
    from groq import Groq
    self._groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    self._client = None
else:
    self._groq_client = None
    self._client = (
        anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        if anthropic is not None
        else None
    )
```

`_call_api` metoduna (satır 105) Groq dalı ekle:

```python
def _call_api(self, model: str, prompt: str, stage: AgentStage, complexity_score: int = 50) -> str:
    # ... mevcut cache/compress kodu ...

    # Groq path
    if getattr(self, '_groq_client', None) is not None:
        groq_model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
        try:
            response = self._groq_client.chat.completions.create(
                model=groq_model,
                messages=[{"role": "user", "content": compressed}],
                max_tokens=max_tokens,
            )
            text = response.choices[0].message.content or ""
            input_tok = response.usage.prompt_tokens
            output_tok = response.usage.completion_tokens
        except Exception as exc:
            text = f"[Groq error: {exc}]\nQUALITY_SCORE: 75"
            input_tok, output_tok = len(compressed.split()), len(text.split())
        self.optimizer.record_usage(stage, groq_model, input_tok, output_tok)
        self.optimizer.store_cache(prompt, text)
        return text

    # ... mevcut Anthropic kodu devam eder ...
```

### Adım 4 — .env Ayarla

```bash
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-8b-instant   # Ücretsiz tier'da en hızlı

# Anthropic key artık gerekmiyor (boş bırakabilirsin)
ANTHROPIC_API_KEY=not-needed
```

### Groq Model Seçenekleri

| Model | Hız | Kalite | Ücretsiz Limit |
|---|---|---|---|
| `llama-3.1-8b-instant` | En hızlı | Temel | 30 req/dk |
| `llama-3.3-70b-versatile` | Orta | İyi | 30 req/dk |
| `mixtral-8x7b-32768` | Orta | İyi | 30 req/dk |

### Uyarılar

- Groq modelleri Anthropic modellerinden farklı çıktı formatı üretebilir; `QUALITY_SCORE:` satırı parse etme başarısız olabilir.
- Rate limit (30 req/dk) aşılırsa `api_only_pipeline` 5 görevi batch'lerken throttle yiyebilir.
- `n8n_workflows/*.json` içindeki `mode` parametresi orchestrator tarafında parse edilir; Groq ile bu alanın önemi kalmaz (model seçimi env ile yapılır).

---

## Karşılaştırma Tablosu

| | Yol 1 (Sahte Key) | Yol 2 (Anthropic $5) | Yol 3 (Groq) |
|---|---|---|---|
| **Maliyet** | $0 | $0–$5 | $0 |
| **Kurulum zorluğu** | Çok kolay | Kolay | Orta (kod değişikliği) |
| **Gerçek AI çıktısı** | Hayır | Evet | Evet |
| **n8n plumbing testi** | Tam | Tam | Tam |
| **Kalite** | Mock | Yüksek (Opus/Sonnet) | Orta (LLaMA) |
| **Kod değişikliği** | Yok | Yok | Var (2 metod) |
| **Rate limit riski** | Yok | Düşük | Orta |

---

## Önerilen Başlangıç Sırası

```
1. Yol 1 ile başla → stack çalışıyor mu doğrula (15 dakika)
2. Anthropic hesabı aç → $5 kredi ile Yol 2'ye geç (gerçek test)
3. Kredi biterse veya ücretsiz kalmak istersen → Yol 3 (Groq entegrasyonu)
```

---

## Sık Yapılan Hatalar

### "docker compose up" başlarken hata

```bash
# N8N_ENCRYPTION_KEY boş bırakılmış
# Çözüm:
python -c "import secrets; print(secrets.token_hex(32))"
# Çıktıyı .env'e yapıştır
```

### n8n açılınca workflow yok

```bash
# Import logunu kontrol et
docker compose logs n8n | grep -i "import\|workflow\|error"

# Manuel import
docker compose exec n8n n8n import:workflow --separate --input=/home/node/workflows/
```

### Orchestrator "ModuleNotFoundError: mock_api"

```bash
# Image'ı temizden build et (Dockerfile.orchestrator düzeltildi ama eski cache varsa)
docker compose build --no-cache orchestrator
docker compose up orchestrator
```

### TOKEN_BUDGET_USD aşıldı hatası

`.env`'de limiti artır veya `budget_usd` parametresini API çağrısında override et:

```bash
curl -X POST http://localhost:8000/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"profile":"mock","test_type":"api","mode":"CODEX_CODEX","budget_usd":1.0}'
```
