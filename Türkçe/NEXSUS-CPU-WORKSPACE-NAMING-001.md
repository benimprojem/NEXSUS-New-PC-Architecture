# NEXSUS CPU — İşlevsel Bellek/Çalışma Alanı Adlandırması

**Belge ID:** NEXSUS-CPU-WORKSPACE-NAMING-001  
**Durum:** Adlandırma temeli  
**Kural:** Kanonik adlar amaca göre belirlenir. Eski SPM adları yalnızca uyumluluk eşlemesidir.

## Kanonik bellek/çalışma alanları

| Eski ad | Kanonik ad | Kapasite / düzen | Temel amaç |
|---|---|---:|---|
| SPM0 | **EB — Execution Buffer** | 4 KiB; 2 × 2 KiB ping-pong bankası | Aktif komut akışı; CFM pasif bankayı doldurur ve değiştirir |
| SPM1 | **OW — OS Workpad** | 8 KiB | OS yerel geçici çalışma alanı; task context değildir |
| SPM2 | **TW — Task Workpad** | 8 KiB | Task/kullanıcı yerel geçici çalışma alanı |
| SPM3–SPM6 | **CTP — Context Pool** | 4 × 8 KiB banka; core başına 16 × 2 KiB slot | Mimari context kayıt/yükleme alanı |
| SPM7 | **XW — Exception Workpad** | 8 KiB; 8 × 1 KiB dilim | Exception/interrupt girişi, geçici frame ve kurtarma alanı |

## Adlandırma kuralları

- Yeni mimari belgelerde, diyagramlarda, simülatör çıktılarında ve uygulama adlarında **EB, OW, TW, CTP, XW** kullanılır.
- Tekil kaynağa sonuna `0` eklenmez: **EB**, EB0 değil. Bankalı kaynaklarda belirli banka/dilim adreslenirken indeks kullanılabilir (örn. CTP bank 0).
- SPM0…SPM7 yalnızca geçiş notu, uyumluluk eşlemesi veya tarihsel alıntıda bulunabilir. SPM artık kanonik kaynak sınıfı değildir.
- Adlar işlevi ve sahipliği belirtir; CPU'nun tüm fiziksel SRAM'lerinin listesi oldukları anlamına gelmez. Kapasite, izolasyon ve zamanlama sözleşmeleri korunarak ayrı diziler, bölümler veya korumalı alanlar şeklinde uygulanabilirler.
- **EB komut staging alanıdır, context slotu değildir. CTP context saklar, çalıştırılabilir kod değildir.** Sahiplik, valid bitleri ve scheduler davranışları ayrıdır.

## Veri yolu özeti

```text
App RAM -> C0 Code Cache -> CS0..CS7 -> EB (ping-pong execution bankaları)
OS servisleri ------------------------> OW
Task/kullanıcı scratch ----------------> TW
Context kaydet/yükle <----------------> CTP
Exception/interrupt ------------------> XW
```

## Geçiş listesi

1. Kanonik SPM0 referanslarını EB ile değiştir.
2. SPM1 → OW; SPM2 → TW.
3. SPM3–SPM6 context bankalarını CTP olarak birleştir (banka/dilim indeksleri açık kalır).
4. SPM7 → XW.
5. Eski doküman veya araçlar için gerekli yerde legacy alias tablosunu koru.
6. CS Code Slots ile CTP Context Pool adlarını/işlevlerini karıştırma.
