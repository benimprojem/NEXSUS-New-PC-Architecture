# NEXSUS CPU — Birleşik Mimari Karşılaştırma ve CodeFlow Testi (CROSS-001)

## Amaç

Birleşik test paketi aynı bileşik iş yükünü dört mimari modelde çalıştırır:
- AMD Ryzen 9 9950X3D2 / Zen 5,
- Intel Xeon 698X,
- Apple M6 ARM,
- 8 çekirdekli NEXSUS CPU.

Ayrıca NEXSUS CodeFlow kod besleme hattını App RAM 64-bit beat aralığı (1/2/4/8 cycle) duyarlılığıyla çalıştırır.

## Önemli model sınırı

NEXSUS CPU execution modeli artık dispatch'i CodeFlow sayfa hazır durumuna bağlar; App RAM→C0, C0→CS ve CS→EB gecikmeleri CPU çevrimlerine entegredir. Ayrı CodeFlow pipeline sweep'i kuyruk/overlap ayrıntılarını inceler ve CPU toplam çevrimi üzerine ikinci kez eklenmez.

## Çalıştırma

```bash
python run_cross_arch_codeflow_suite.py --scale 1 --pages 64 --tasks 4 --json
```

CI şu kontrolleri uygular:
- dört mimaride aynı mantıksal işlem sayısı;
- dört CPU profilinin raporda bulunması;
- dört App RAM beat interval senaryosunun tamamlanması;
- tüm standalone CodeFlow senaryolarında aynı sayfa tamamlanma sayısı;\n- entegre NEXSUS CPU fetch testlerinde App RAM beat, C0 miss ve Code Slot/Code Stream aktarım sayaçları;\n- kod sayfası hazır olmadan dispatch'in ilerlememesi.

Çıktı GitHub Actions artifact'i olarak saklanır. Sonuçlar gerçek CPU ölçümü değil, parametre tabanlı simülasyon sonuçlarıdır.
