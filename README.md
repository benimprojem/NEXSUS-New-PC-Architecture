# NEXSUS — Yeni Nesil Kişisel Bilgisayar Mimarisi

**NEXSUS**, işlemci, bellek, depolama, firmware ve çevre birimlerini tek bir bütünleşik platform olarak yeniden tasarlamayı amaçlayan deneysel bir PC mimarisi projesidir.

> Hedef: tarihsel PC katmanlarını yalnızca büyütmek yerine, sistem bileşenlerini baştan birlikte tasarlamak.

## Mimari bileşenler

- **NEXSUS CPU** — genel amaçlı işlem ve kontrol akışı
- **FAPU** — özel ve yüksek yoğunluklu hesaplama
- **NPU** — sistem davranışını öğrenme/tahmin
- **MOSRAM** — yeni çalışma belleği yaklaşımı
- **M-SSD** — kalıcı depolama
- **SCP** — platform ve güç yönetimi
- **NEXSUS System Fabric** — bileşenler arası iletişim
- **NEXSUS Firmware** — donanım başlatma ve OS geçişi
- **NPI / Wireless Link** — kablolu ve çoklu cihaz kablosuz çevre birimleri

Bu bileşenler araştırma ve tasarım önerileridir; tamamlanmış veya silikon üzerinde doğrulanmış ürün özellikleri olarak sunulmaz.

## Belgeler

### Genel mimari
- [CPU belgeleri ve tasarım kayıtları](NEXUS%20CPU/)
- [Türkçe belge merkezi](Türkçe/README.md)

### CPU — mimari, ISA ve bellek
- [CPU ana mimarisi](NEXUS%20CPU/Yeni%20Nesil%20Ayr%C4%B1%C5%9Ft%C4%B1r%C4%B1lm%C4%B1%C5%9F%20Register%20Tabanl%C4%B1%20CPU%20Mimarisi.md)
- [ISA ve yürütme modeli](NEXUS%20CPU/NEXSUS-CPU-ISA-001.md)
- [64-bit Instruction Encoding](NEXUS%20CPU/NEXSUS-CPU-INSTRUCTION-ENCODING-001.md)
- [Memory Bank Topology](NEXUS%20CPU/NEXSUS-CPU-MEMORY-BANK-TOPOLOGY-001.md)
- [OS / CodeFlow / Context Interface](NEXUS%20CPU/NEXSUS-CPU-OS-PX-CONTEXT-INTERFACE-001.md)
- [CodeFlow Manager ve Code Slot havuzu](NEXUS%20CPU/NEXSUS-CPU-PX-MANAGER-001.md)
- [Code-path naming decision](NEXUS%20CPU/NEXSUS-CPU-CODEFLOW-NAMING-001.md)

### CPU — simülasyon ve doğrulama
- [Karşılaştırma simülatörü](NEXUS%20CPU/tools/cpu_comparison_sim.py)
- [L0I / CodeFlow pipeline simülatörü](NEXUS%20CPU/tools/l0i_px_pipeline_sim.py)
- [Karşılaştırma simülatörü testleri](NEXUS%20CPU/tools/test_cpu_comparison_sim.py)
- [CodeFlow pipeline testleri](NEXUS%20CPU/tools/test_l0i_px_pipeline_sim.py)
- [Simülatör mimarisi](NEXUS%20CPU/NEXSUS-CPU-SIMULATOR-ARCHITECTURE-001.md)
- [Benchmark planı](NEXUS%20CPU/NEXSUS-CPU-FULL-ARCHITECTURE-BENCHMARK-001.md)
- [Simülasyon sonuçları ve sınırlar](NEXUS%20CPU/NEXSUS-CPU-SIMULATION-RESULTS-001.md)
- [GitHub Actions doğrulama](.github/workflows/nexus-cpu-simulator.yml)

## Dil ve belge düzeni

- Ana teknik dokümanlar İngilizce tutulur.
- Türkçe karşılıklar `Türkçe/` klasöründe, aynı belge kimliğiyle tutulur.
- Her iki dilde aynı mimari kararlar, parametreler ve durum bilgisi korunur.
- Yeni kararlar önce İngilizce ana belgeye, ardından Türkçe eşine işlenir.
- [Türkçe belge dizini](Türkçe/README.md)

## Proje durumu

NEXSUS araştırma ve mimari modelleme aşamasındadır. Simülasyon çıktıları parametre tabanlı model sonuçlarıdır; gerçek donanım performansı veya üretici CPU ölçümü değildir.
