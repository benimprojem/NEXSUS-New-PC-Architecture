# NEXSUS CPU — Birleşik Mimari Karşılaştırma ve CodeFlow Testi (CROSS-001)

## Amaç

Birleşik test paketi aynı bileşik iş yükünü dört mimari modelde çalıştırır:
- AMD Ryzen 9 9950X3D2 / Zen 5,
- Intel Xeon 698X,
- Apple M6 ARM,
- 8 çekirdekli NEXSUS CPU.

Ayrıca NEXSUS CodeFlow kod besleme hattını App RAM 64-bit beat aralığı (1/2/4/8 cycle) duyarlılığıyla çalıştırır.

## Önemli model sınırı

CPU execution modeli ve CodeFlow pipeline modeli **ayrı katmanlar olarak raporlanır**. CodeFlow henüz her CPU komutunun fetch/scheduler döngüsüne bağlanmış değildir; pipeline gecikmesini CPU toplam çevrimine eklenmiş gibi yorumlamak doğru olmaz. Bu bir sonraki entegrasyon aşamasıdır.

## Çalıştırma

```bash
python run_cross_arch_codeflow_suite.py --scale 1 --pages 64 --tasks 4 --json
```

CI şu kontrolleri uygular:
- dört mimaride aynı mantıksal işlem sayısı;
- dört CPU profilinin raporda bulunması;
- dört App RAM beat interval senaryosunun tamamlanması;
- tüm CodeFlow senaryolarında aynı sayfa tamamlanma sayısı.

Çıktı GitHub Actions artifact'i olarak saklanır. Sonuçlar gerçek CPU ölçümü değil, parametre tabanlı simülasyon sonuçlarıdır.
