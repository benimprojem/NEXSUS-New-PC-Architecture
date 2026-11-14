# NEXSUS CPU — OS / CodeFlow / Context Arayüzü (OS-CFM-001)

## 1. Sorumluluk sınırı

**OS politika sahibidir:** görev seçimi, öncelik, deadline, adalet/fairness, sayfa isteği, prefetch ve kaynak adresi eşlemesi.

**CPU/CodeFlow Manager güvenlik ve donanım sahibidir:** izin ve nesil doğrulama, sayfa tahsisi, aktarım, READY yayımlaması, aktif fetch koruması, context save/restore ve atomik dispatch commit.

OS, fiziksel Code Slot (CS0–CS7; eski PX P0–P7) durumunu güvenlik denetimini atlayarak değiştiremez.

## 2. Kod yolu

```text
App RAM -> Code Cache C0 (64 KiB, eski L0I)
        -> Code Slots CS0–CS7 (8 x 2 KiB, eski PX)
        -> Execution Buffer EB0 (2 x 2 KiB, eski SPM0)
```

App RAM temel hattı 64-bit'tir. Code Cache görev/sayfa bazlı parça doldurulur; fiziksel kaynak adresleri ardışık olmayabilir. Üç kuyruk (App RAM→C0, C0→CS, CS→EB0) bağımsızdır.

## 3. Önerilen OS komutları

| Komut | İşlev |
|---|---|
| `CF_ALLOC` | Kod yuvası/rezidans kaynağı talep et |
| `CF_LOAD` | Görev mantıksal sayfasını kaynak aralıktan yükle |
| `CF_QUERY` | Rezidans ve aktarım durumunu sorgula |
| `CF_MAP` / `CF_UNMAP` | Mantıksal sayfa eşle/çöz |
| `CF_PREFETCH` | İleri kod sayfası hazırlama iste |
| `CF_PIN` / `CF_UNPIN` | Sayfa değiştirme politikasına pin ipucu ver |
| `CF_RELEASE` | Güvenli serbest bırakma talep et |
| `CTX_SAVE` / `CTX_RESTORE` | Görev register/context görüntüsünü koru/geri yükle |
| `CTX_QUERY` | Context rezidansını sorgula |
| `TASK_COMMIT` | Dispatch koşullarını atomik olarak onayla |

Bunlar önerilen mimari komutlardır; ISA/ABI kesinleşmeden sabit opcode kabul edilmez.

## 4. Dispatch koşulları

Görev ancak şu koşulların tümü sağlandığında yürütülebilir:
- OS politika kararı dispatch'e izin verir;
- context geçerli ve geri yüklemeye hazırdır;
- PC mantıksal kod eşlemesi geçerlidir;
- gereken kod sayfası READY ve eşlenmiştir;
- izinler ve görev nesli doğrulanmıştır;
- çakışan invalidation/aktarım yoktur.

## 5. Görev geçişi

1. OS yeni görevi seçer.
2. Güvenli noktada mevcut görev durdurulur.
3. CTX_SAVE tamamlanır; canlı register'lar save bitmeden ezilmez.
4. Eski kod sayfaları gerekiyorsa tutulur, değilse güvenli serbest bırakma istenir.
5. Yeni görev context ve kod sayfaları paralel hazırlanabilir.
6. Dispatch readiness doğrulanır.
7. TASK_COMMIT kaydedilmiş PC'den atomik devam sağlar.

Code Slot ve context rezidansı bağımsızdır: context Data RAM'e taşınsa bile kod sayfaları önbellekte kalabilir.

## 6. Fairness ve olaylar

OS priority aging/fairness uygular; sürekli yüksek öncelikli işlerin düşük öncelikli görevleri aç bırakması engellenir. CFM olayları en azından request, C0-ready, CS-ready, EB-ready, stale-generation reject, eviction ve starvation durumlarını ayırt eder.

## 7. Terimler

Yeni metinlerde CodeFlow Manager (CFM), Code Cache (C0), Code Slots (CS0–CS7) ve Execution Buffer (EB0) kullanılır; PX/L0I/SPM0 eski adları uyumluluk için korunur.
