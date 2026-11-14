# NEXSUS CPU — Simülatör Mimarisi (SIM-001)

## 1. Amaç

Simülatör, NEXSUS CPU önerilerini güncel AMD, Intel ve ARM referans profilleriyle aynı algoritma ve iş yüklerinde karşılaştırır. Bu çalışma gerçek silikon benchmark'ı, RTL simülasyonu veya üretici mikro mimarisinin birebir kopyası değildir; parametreleri açık bir çevrim/olay modelidir.

## 2. Karşılaştırma düzeni

- **Native profil:** AMD Ryzen 9 9950X3D2 (Zen 5), Intel Xeon 698X, Apple M6 ARM ve 8 çekirdekli NEXSUS önerisi.
- **Normalize 8-core:** Dört modelde sekiz aktif çekirdek; aynı mantıksal işlem miktarı.
- **Ortak kernel'ler:** scalar/control, pointer graph, numeric tile, streaming, task/context, atomics ve code-page baskısı.
- **Raporlar:** çevrim, işlem sayısı, IPC, kernel bazlı süre, bellek erişimleri ve stall sayaçları.
- Vendor'a özgü bilinmeyen parametreler varsayımdır; sonuçlar ölçüm değil model çıktısı olarak etiketlenir.

## 3. CodeFlow pipeline modeli

```text
App RAM -> Code Cache C0 (L0I, 64 KiB)
        -> Code Slots CS0–CS7 (PX, 8 x 2 KiB)
        -> Execution Buffer EB0 (SPM0, 2 x 2 KiB)
```

C0 görev/sayfa kimliğiyle artımlı doldurulur. App RAM kaynakları ardışık olmayabilir. Üç bağımsız aktarım kuyruğu:
1. App RAM → C0,
2. C0 → Code Slots,
3. Code Slots → pasif EB0 bankası.

Her aşama için kuyruk bekleme, servis süresi, beat, arbitration, backpressure ve overlap ayrı modellenir. C0 tamamen dolmadan sayfa aktarımı başlayabilir. Yalnızca doğrulanmış geçerli baytlar Code Slot'a aktarılır.

## 4. İlk çalışan pipeline simülatörü

Kaynak: [l0i_px_pipeline_sim.py](../NEXUS%20CPU/tools/l0i_px_pipeline_sim.py)  
Testler: [test_l0i_px_pipeline_sim.py](../NEXUS%20CPU/tools/test_l0i_px_pipeline_sim.py)

Model şu özellikleri içerir:
- görevler arası, ardışık olmayan App RAM kaynak adresleri;
- bounded App RAM request queue;
- 64-bit tek lane ve ayarlanabilir beat aralığı/ilk gecikme;
- 64 KiB C0 sayfa rezidansı;
- bağımsız C0→CS ve CS→EB kuyrukları;
- sekiz eşit dinamik Code Slot;
- iki 2 KiB EB0 ping-pong bankası;
- olay zaman çizelgesi, queue peak, hit/miss, beat, bank swap ve stall sayaçları.

Çalıştırma (`NEXUS CPU/tools` klasöründen):

```bash
python l0i_px_pipeline_sim.py --pages 64 --tasks 2
python l0i_px_pipeline_sim.py --pages 64 --tasks 2 --beat-interval 4 --json
python test_l0i_px_pipeline_sim.py
```

Varsayılan beat aralığı 1 cycle yalnızca baz duyarlılık varsayımıdır; donanım garantisi değildir.

## 5. Doğruluk kuralları

- geçersiz/yarım C0 verisi yürütülebilir sayfaya aktarılmaz;
- görevler arası kod erişimi açık paylaşım izni gerektirir;
- eski generation isteği READY yayımlayamaz;
- in-flight aktarım C0 kaynağını evict edemez;
- CF_NEXT/CF_END komut baytı değildir;
- EB0 bankası tüm geçerli baytlar tamamlanmadan READY/ACTIVE olmaz.

## 6. Test ve kanıt sınırı

CI, karşılaştırma simülatörü ve L0I pipeline regresyon testlerini derler/çalıştırır; ayrıca native/normalize karşılaştırma, predictor, PX kapasitesi ve fetch gecikmesi duyarlılıklarını yürütür. Pipeline modeli henüz vendor CPU kernel simülasyonunun instruction scheduler'ına entegre değildir; bu iki sonuç grubu ayrı raporlanmalıdır.
