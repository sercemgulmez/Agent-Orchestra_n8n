# Yemeksepeti Web + App Test Orchestrator

Bu proje, `yemeksepeti.com` ve Yemeksepeti mobil app kullanıcı akışlarını güvenli bir mock/staging mirror ortamında test etmek için hazırlanmış ajan tabanlı test orkestrasyonudur.

## Amac

- Gerçek Yemeksepeti ürün yüzeylerini modellemek: Restoran, Gel Al, Marketler, konum/adres, sepet, kupon, checkout ve sipariş takip.
- Canlı prod üzerinde yan etkili login, ödeme veya sipariş testi çalıştırmadan güvenli mirror testleri üretmek.
- Web, Android ve iOS senaryolarını aynı orkestrasyon modeliyle yönetmek.
- n8n workflow'larını, token/maliyet raporlarını ve test profillerini izlenebilir hale getirmek.

## Klasor Yapisi

```text
.
├── agents/              # Plan/execute/review/fix ajanları, token optimizer, complexity analyzer
├── mock_api/            # Yemeksepeti mirror API
├── mock_ui/             # Yemeksepeti mirror web UI
├── mobile_appium/       # Android/iOS Appium capability profilleri
├── n8n_workflows/       # n8n orkestrasyon JSON dosyaları
├── obsidian_maps_plugin/# Token optimizer profile örnek plugin scaffold'u
└── tests/               # API, web, mobile profile ve orchestrator testleri
```

## Test Profilleri

| Profil | Amaç |
|---|---|
| `mock` | Tüm API/web/mobile/e2e mirror testleri yerel mock servislerde çalışır. |
| `web-prod-smoke` | Canlı `https://www.yemeksepeti.com/` için sadece yan etkisiz smoke/navigation kontrolü. |
| `mobile-android` | Appium Android emulator/cihaz profili. App path env üzerinden gelir. |
| `mobile-ios` | Appium iOS simulator/cihaz profili. App path env üzerinden gelir. |

Canlı prod üzerinde sipariş, ödeme, gerçek hesap veya scraping testi çalıştırılmaz. Bu yalnızca dokümantasyon kuralı değil; `/api/orchestrate` runtime güvenlik kapısı `web-prod-smoke`, `mobile-android` ve `mobile-ios` profillerinde sepet, checkout, ödeme, sipariş, kupon ve gerçek login-submit niyetlerini otomatik reddeder.

## Çalıştırma

```bash
python3 -m uvicorn mock_api.server:app --host 127.0.0.1 --port 8001
cd mock_ui && npm install && npm run dev -- --host 127.0.0.1
python3 main.py
```

Dashboard: `http://localhost:8000/dashboard`

## n8n Kullanim Sekli

n8n bu projede karar veren katman degildir; kontrollu tetikleyici ve raporlama katmanidir. Test guvenligi, profil validasyonu ve yan etkili aksiyon engelleme FastAPI orchestrator icinde calisir. n8n workflow'lari yalnizca schedule/manual trigger, `/api/orchestrate` cagirma, token/maliyet raporu alma ve bildirim gonderme icin kullanilir.

- Lokal gelistirme icin tek n8n instance + Postgres yeterlidir.
- CI/nightly workflow'lari sadece `profile=mock` ile mirror regression suite calistirir.
- Canli smoke workflow'u ayri tutulur ve yalniz `profile=web-prod-smoke`, `test_type=prod-smoke` ile public, yan etkisiz navigation kontrolleri yapar.
- Siparis, odeme, login-submit, sepet ve kupon akislari sadece `mock` profilde calisir.
- Olcek gerekirse n8n queue mode + Redis + worker yapisina gecilir; bu proje icin varsayilan local tek instance yeterlidir.

## n8n Guvenlik Checklist

- `N8N_BASIC_AUTH_PASSWORD`, `POSTGRES_PASSWORD` ve `N8N_ENCRYPTION_KEY` sadece lokal `.env` uzerinden verilir; workflow JSON veya repo icine yazilmaz.
- `N8N_ENCRYPTION_KEY` ilk kurulumdan sonra sabit tutulur; degistirmek mevcut credential'lari okunamaz hale getirebilir.
- n8n local gelistirmede `127.0.0.1:5678` uzerinden baglanir. Dis ortama acilacaksa reverse proxy, TLS ve guclu auth zorunludur.
- n8n credential store kullanilir; Slack/webhook/token degerleri workflow JSON icine gomulmez.
- Riskli node'lar kapali tutulur: Execute Command ve Read/Write Files from Disk.
- Execution pruning aciktir; prompt/test payload'lari ve raporlar uzun sure saklanmaz.
- Safety violation donen orchestration yaniti n8n'de kalite skoruna gecmeden durdurulur.

## Notlar

- Kimlik bilgileri, API anahtarlari ve `.env` dosyalari commit edilmemelidir.
- Test hesapları, Appium server URL ve mobil app path bilgileri sadece env üzerinden verilir.
- `.env.example` dahil `.env*` dosyaları gitignore kapsamındadır.
