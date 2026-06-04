# Agent Orchestra n8n

Agent Orchestra n8n, n8n uzerinde ajan tabanli otomasyon akislari gelistirmek ve versiyonlamak icin olusturulmus bir calisma alanidir.

## Amac

- n8n workflow'larini duzenli bicimde saklamak
- Ajan orkestrasyonu denemelerini izlenebilir hale getirmek
- Hassas kimlik bilgilerini repodan ayri tutmak

## Klasor Yapisi

```text
.
├── workflows/   # Disa aktarilan n8n workflow JSON dosyalari
└── README.md
```

## Notlar

- Kimlik bilgileri, API anahtarlari ve `.env` dosyalari commit edilmemelidir.
- n8n workflow'lari disari aktarildiktan sonra `workflows/` altina eklenebilir.
- Gerekirse ortam degiskenleri icin `.env.example` dosyasi olusturulabilir.

