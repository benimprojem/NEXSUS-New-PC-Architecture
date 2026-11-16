# NEXSUS CPU — Cache Topolojisi ve Paylaşım Kararı 001

**Belge Kimliği:** NEXSUS-CPU-CACHE-TOPOLOGY-001  
**Durum:** Kapasite ve paylaşım topolojisi FIXED; port/bant genişliği OPEN  
**Kapsam:** Sekiz çekirdeklik bir L4 bloğundaki cache örnekleri ve erişim kapsamı.

## 1. Sekiz çekirdek başına cache örnekleri

```text
Core 0 ─ private L1 ─┐
Core 1 ─ private L1 ─┴─ shared L2 (pair 0–1) ─┐
Core 2 ─ private L1 ─┐                         │
Core 3 ─ private L1 ─┴─ shared L2 (pair 2–3) ─┤
                         shared L3 (cores 0–3) ─┤
Core 4 ─ private L1 ─┐                         │
Core 5 ─ private L1 ─┴─ shared L2 (pair 4–5) ─┤
Core 6 ─ private L1 ─┐                         │
Core 7 ─ private L1 ─┴─ shared L2 (pair 6–7) ─┤
                         shared L3 (cores 4–7) ─┤
                              shared L4 (0–7) ──┘
```

| Seviye | Sekiz core içinde örnek sayısı | Kapasite / örnek | Erişim kapsamı |
|---|---:|---:|---|
| L1 | 8 | 1 MiB | Yalnızca sahibi olan core |
| L2 | 4 | 2 MiB | İkişerli core çifti |
| L3 | 2 | 8 MiB | Dörderli core grubu |
| L4 | 1 | 64 MiB+ | Sekiz core'un tamamı |

## 2. Core erişim kuralı

Her core, izin ve görünürlük kurallarına göre aşağıdaki cache alanlarına erişebilir:

- Kendi özel L1'ine,
- Kendi çiftinin ortak L2'sine,
- Kendi dört-core grubunun ortak L3'üne,
- Sekiz-core bloğunun ortak L4'üne.

**Önemli:** İki ayrı L3 grubu aynı L4 örneğini paylaşır. L3 sınırı L4 erişimini kesmez. L4 izolasyonu, sekiz-core L4 blokları arasındaki sınırda başlar. Farklı L4 blokları arası paylaşım otomatik değildir; açık transfer/görünürlük mekanizması gerekir.

## 3. Working-set home seçimi

| İşbirliği yapan core sayısı | Doğal ortak çalışma alanı |
|---:|---|
| 1 | L1 |
| 2 | L2 |
| 3–4 | L3 |
| 5–8 | L4 |
| >8 | Her sekiz-core blokta ayrı L4 home; bloklar arası açık mekanizma |

Bu seçim, çalışma kümesinin doğal yerleşim/ hazırlık seviyesini tanımlar. Simülatörde her L1'e kopyalayarak ortak L3/L4 paylaşımı taklit edilmez. Untimed prefill yalnızca ölçüm hazırlığıdır; donanımda ücretsiz yükleme anlamına gelmez.

## 4. Sekizden fazla core: bellekten L4 dağıtımı

Birden fazla sekiz-core bloğu kullanan iş yüklerinde her bloğun ayrı L4 home'u bulunur. Veri, gerektiğinde Data RAM/ana bellekten doğrudan hedef L4 home'larına parçalar halinde dağıtılabilir. Paylaşılan verinin dağıtım kaynağı bellektir; bir L4'ün diğer L4'e zincirleme veri aktarması zorunlu değildir.

| Dağıtım biçimi | Bellekten L4'e davranış | Kullanım |
|---|---|---|
| Bölümlü (partitioned) | Farklı veri parçaları farklı L4 home'larına gider | Her core grubu farklı veri işler |
| Kopyalı/paylaşılan (replicated) | Aynı salt-okunur/paylaşılan aralık seçilen L4 home'larına doğrudan yüklenir | Birden fazla grup aynı veriyi okur |
| Seçmeli çoklu hedef (selective multicast) | Veri yalnızca seçilmiş L4 home'larına dağıtılır | Kısmi grup paylaşımı |

Bu karar veri kaynağı ve dağıtım yolunu tanımlar. Parça boyutu, hedef seçimi, adres aralığı sahipliği, transfer planlama, bant genişliği rezervasyonu ve tamamlanma/hata yönetimi henüz açık tasarım konularıdır. Yazılabilir kopyalar otomatik olarak tutarlı kabul edilmez; eşzamanlı yazma için açık sahiplik/güncelleme protokolü gerekir.

## 5. Topoloji ve port ayrımı

**8×L1 / 4×L2 / 2×L3 / 1×L4 cache örnek sayısıdır; port sayısı veya bant genişliği değildir.**

Cache portları, servis kapasitesi, erişim gecikmesi, arbitraj ve contention parametreleri henüz mimari olarak kesinleşmemiştir. Simülatörde kullanılan tek-istek/cycle ortak port varsayımı geçici bir deney parametresidir; FIXED karar değildir.

## 6. Durum

- Cache kapasitesi ve paylaşım kapsamı: **FIXED**
- Sekiz-core L4 içinde iki L3 grubunun ortak L4'e erişmesi: **FIXED**
- Cache portları, bandwidth, hit/miss latency, arbitration ve coherence: **OPEN**
- Simülatör port modeli: deneysel/parametrelenebilir; silikon iddiası değildir.

İlgili ana kayıt: [Architecture Decision Register 001](../NEXUS%20CPU/NEXSUS-CPU-ARCHITECTURE-DECISION-REGISTER-001.md)
