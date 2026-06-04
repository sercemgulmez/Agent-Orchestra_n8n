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

Canlı prod üzerinde sipariş, ödeme, gerçek hesap veya scraping testi çalıştırılmaz.

## Çalıştırma

```bash
python3 -m uvicorn mock_api.server:app --host 127.0.0.1 --port 8001
cd mock_ui && npm install && npm run dev -- --host 127.0.0.1
python3 main.py
```

Dashboard: `http://localhost:8000/dashboard`

## Notlar

- Kimlik bilgileri, API anahtarlari ve `.env` dosyalari commit edilmemelidir.
- Test hesapları, Appium server URL ve mobil app path bilgileri sadece env üzerinden verilir.
- `.env.example` dahil `.env*` dosyaları gitignore kapsamındadır.
