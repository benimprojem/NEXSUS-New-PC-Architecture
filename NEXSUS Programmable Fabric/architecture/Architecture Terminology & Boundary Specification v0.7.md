# NEXSUS Programmable Fabric
## Architecture Terminology & Boundary Specification v0.7

**Document Code:** NXF-ARCH-007  
**Status:** Preliminary Architecture Standard  
**Scope:** P1–P5, PE4–PE5, NEXSUS S.Fabric  
**Purpose:** Define architectural terms, responsibilities, and component boundaries.

---

## 1. Temel Mimari Kural

NEXSUS mimarisinde her bileşen açıkça tanımlanmış bir sorumluluğa sahip olmalıdır.

Bir bileşen:

- kendi işlevini yerine getirir,
- diğer bileşenlerin işlevlerini gereksiz yere üstlenmez,
- standart bir arayüz üzerinden iletişim kurar,
- kaynaklarını ve performans sınırlarını bildirir.

Temel ayrım:

**Hesaplama, veri taşıma, çevresel aygıt yönetimi, fiziksel I/O ve sistem koordinasyonu ayrı mimari görevlerdir.**

Bunlar aynı çipte bulunabilir ancak aynı kavram olarak değerlendirilmemelidir.

## 2. Mimari Hiyerarşi

NEXSUS sisteminin kavramsal hiyerarşisi şöyledir:

```text
NEXSUS SYSTEM
│
├── Processing
│   ├── NEXSUS CPU
│   ├── FAPU
│   └── Programmable Fabric
│
├── System Interconnect
│   ├── S.Fabric
│   ├── Memory Interconnect
│   └── Expansion Links
│
├── Memory
│   ├── MOSRAM
│   ├── SRAM
│   ├── MSSD
│   └── External Memory
│
├── I/O Subsystem
│   ├── I/O Banks
│   ├── I/O Router
│   ├── ADC / DAC
│   └── Electrical Interfaces
│
├── Peripheral Subsystem
│   ├── UART / SPI / I²C / CAN
│   ├── Custom Protocol Engine
│   ├── Timers / Counters
│   └── Interrupt / Event Matrix
│
├── Data Movement
│   ├── DMA Engines
│   ├── DMA Scheduler / Arbiter
│   └── Buffering
│
├── Display Subsystem
│   ├── Display Controller
│   ├── Display DMA
│   └── Optional Display Bridge / PHY
│
└── External Connectivity
    ├── USB
    ├── Ethernet
    ├── Wireless
    └── PE Expansion Interface
```

Bu şema mantıksal hiyerarşiyi gösterir. Her kutunun ayrı fiziksel çip olması gerektiğini ifade etmez.

---

## 3. Bileşen Sınırları

### 3.1 NEXSUS CPU

**Görev:** Genel amaçlı program yürütme ve sistem düzeyinde karar verme.

CPU sorumlulukları:

- uygulama kodunu yürütmek,
- sistem kaynaklarını yapılandırmak,
- görevleri başlatmak ve yönetmek,
- Fabric konfigürasyonunu kontrol etmek,
- kesmeleri işlemek,
- üst düzey veri işleme ve kontrol mantığını yürütmek.

CPU'nun her ADC örneğini, her ekran pikselini veya her protokol bitini doğrudan yönetmesi hedeflenmez.

CPU, donanım kaynaklarının sahibi veya yöneticisi olabilir; ancak her veri transferinin fiziksel taşıyıcısı olmak zorunda değildir.

### 3.2 FAPU

**Görev:** NEXSUS sisteminde CPU'yu tamamlayan yardımcı işlem birimi.

FAPU'nun kesin işlem sınıfları, komut arayüzü ve bellek erişim modeli ayrıca tanımlanmalıdır.

Şimdilik şu sınır geçerlidir:

- CPU'nun yerine geçen genel sistem yöneticisi değildir.
- Programmable Fabric ile aynı kavram değildir.
- DMA veya Memory Controller ile eş anlamlı değildir.
- Hangi işlemleri hızlandıracağı belirlenmeden kaynak sayısı sabitlenmez.

### 3.3 Programmable Fabric

**Görev:** Yapılandırılabilir mantık, paralel veri işleme ve özel donanım veri yolları oluşturmak.

Fabric kaynakları:

- LUT ve flip-flop,
- yerel ve dağıtılmış bellek,
- routing,
- DSP/MAC,
- özel state machine'ler,
- pipeline,
- paralel işlem mantığı.

Fabric, bir ADC'nin analog dönüşüm devresi veya bir Ethernet PHY değildir. Bu birimlerin verisini işleyebilir, kontrol edebilir veya aralarında veri akışı oluşturabilir.

Fabric, uygulama ihtiyacına göre yapılandırılabilir donanım alanıdır.

### 3.4 S.Fabric

**Görev:** NEXSUS anakartı ve sistem düzeyindeki bileşenler arasında koordinasyon ve veri iletişimi sağlamak.

S.Fabric, Programmable Fabric ile aynı şey değildir.

| Özellik | Programmable Fabric | S.Fabric |
|---|---|---|
| Kapsam | Bir programlanabilir işlemci/çip içindeki kaynaklar | Sistem ve anakart düzeyi |
| Ana görev | Mantık oluşturma ve paralel işleme | Sistem bağlantısı ve koordinasyonu |
| Kaynaklar | LUT, DSP, yerel routing, FIFO | Linkler, portlar, arbitraj ve sistem yönlendirmesi |
| Yapılandırma | Donanım işlevini belirler | Sistem bağlantılarını ve kaynak erişimini yönetir |
| Örnek | ADC verisine filtre uygulamak | Veriyi PE5'ten ana bellek sistemine taşımak |

S.Fabric'in fiziksel uygulaması merkezi bir çip, dağıtılmış kontrol mantığı veya birleşik bir yapı olabilir. Bu karar henüz verilmiş değildir.

### 3.5 System Interconnect

**Görev:** Bileşenler arasındaki adresli veya akış tabanlı veri transferini taşımak.

Interconnect:

- bağlantı yollarını,
- erişim kurallarını,
- transfer protokollerini,
- gerektiğinde arbitrajı,
- hata ve akış kontrolünü

tanımlar.

Interconnect, verinin anlamını işlemek zorunda değildir. Örneğin ADC örneğini filtrelemek Fabric'in, örneği bellek adresine taşımak ise DMA ve interconnect'in görevidir.

### 3.6 Memory Controller

**Görev:** Belirli bir bellek teknolojisine erişimi yönetmek.

Sorumlulukları:

- bellek erişim zamanlaması,
- okuma/yazma komutları,
- erişim sıralaması,
- bellek protokolüne özgü işlemler,
- gerekiyorsa refresh ve kalibrasyon.

MOSRAM, SRAM ve harici bellek aynı erişim gereksinimlerine sahip olmak zorunda değildir. Bu nedenle her bellek türünün tek bir evrensel controller kullanacağı varsayılmamalıdır.

**Memory Controller, DMA değildir.** DMA transfer talep eder; Memory Controller bu talebin hedef belleğe uygun şekilde gerçekleştirilmesini sağlar.

### 3.7 DMA Engine

**Görev:** CPU'nun her veri birimi için müdahalesine gerek kalmadan veri taşımak.

Örnekler:

- ADC FIFO → SRAM,
- sensor FIFO → system memory,
- network buffer → memory,
- memory → display controller.

DMA, veriyi taşıyan donanım mekanizmasıdır. Filtreleme, protokol yorumlama veya görüntü kompozisyonu varsayılan DMA görevi değildir.

### 3.8 DMA Arbiter / Scheduler

**Görev:** Aynı veri yolunu veya bellek kaynağını isteyen transferlerin nasıl sıraya alınacağını belirlemek.

Bu bileşen şu konuları yönetebilir:

- öncelikler,
- burst boyutları,
- transfer adaleti,
- gecikme sınırları,
- gerçek zamanlı akışlara ayrılan kapasite.

DMA Engine ile arbiter mantıksal olarak ayrı tanımlanır. Fiziksel tasarımda aynı modülde birleştirilebilir.

### 3.9 I/O Bank

**Görev:** Fiziksel pinlerin elektriksel özelliklerini ve pin seviyesindeki giriş/çıkış işlevlerini yönetmek.

I/O Bank şunları kapsayabilir:

- pin buffer'ları,
- giriş senkronizasyonu,
- çıkış register'ları,
- pull-up/pull-down,
- drive strength,
- slew rate,
- pin multiplexer,
- desteklenen elektriksel modlar.

I/O Bank, UART protokolünü veya ADC dönüşüm algoritmasını yürütmek zorunda değildir.

### 3.10 I/O Router

**Görev:** Fiziksel pinleri seçilen işlevlere bağlamak.

Örneğin bir pinin GPIO, UART TX veya PWM çıkışı olarak kullanılmasını sağlar.

I/O Router, Fabric içindeki genel amaçlı routing ağı ile aynı şey değildir:

- **I/O Router:** Fiziksel pinler ve I/O işlevleri arasındaki bağlantı.
- **Fabric Router:** Programlanabilir mantık kaynakları arasındaki bağlantı.
- **System Interconnect:** Çipler ve sistem bileşenleri arasındaki bağlantı.

Bu üç kavram birbirinin yerine kullanılmamalıdır.

### 3.11 ADC / DAC

**ADC görevi:** Analog sinyali dijital örneklere dönüştürmek.

**DAC görevi:** Dijital değeri analog sinyale dönüştürmek.

ADC alt sistemi analog giriş seçimini, acquisition süresini, dönüşümü ve örnek sonucunu yönetebilir.

ADC'nin arkasındaki FIFO, DMA ve Fabric işleme aşamaları ayrı işlevlerdir.

Benzer şekilde DAC, dijital veriyi analog çıkışa dönüştürür; çıkışın ne zaman ve hangi değerde güncelleneceğini CPU, timer, DMA veya Fabric belirleyebilir.

### 3.12 Peripheral Engine

**Görev:** Belirli bir haberleşme veya zamanlama protokolünü donanımda yürütmek.

Örnekler:

- UART,
- SPI,
- I²C,
- CAN controller,
- timer,
- counter,
- capture,
- Custom Protocol Engine.

Peripheral Engine protokol durumunu, zamanlamayı, hata tespitini ve uygun FIFO arayüzünü yönetir.

Fiziksel elektriksel sürücü veya transceiver gerekliyse bu ayrı bir katmandır.

### 3.13 Custom Protocol Engine

**Görev:** Önceden standartlaştırılmamış veya uygulamaya özgü protokollerin yapılandırılabilir donanım mantığıyla yürütülmesi.

Olası kaynaklar:

- state machine,
- bit/byte parser,
- timer,
- pattern matcher,
- CRC/checksum,
- FIFO,
- Fabric bağlantısı.

Custom Protocol Engine tüm protokolleri otomatik olarak tanıyan bir sistem değildir. Desteklediği protokolün kuralları konfigürasyon veya derleme aşamasında tanımlanmalıdır.

### 3.14 Interrupt Matrix

**Görev:** Donanım olaylarının kesme kaynaklarına ve kesme hedeflerine yönlendirilmesi.

Interrupt, yazılımın veya CPU'nun bir olaydan haberdar edilmesidir.

### 3.15 Event / Trigger Matrix

**Görev:** Bir donanım olayının başka bir donanım işlemini başlatmasını sağlamak.

Örnek:

`Timer Event → ADC Start → FIFO Threshold → DMA Request`

Interrupt Matrix ile Trigger Matrix aynı şey değildir. Bazı kaynakları paylaşabilirler; ancak görevleri ayrı tanımlanmalıdır.

### 3.16 Display Controller

**Görev:** Frame buffer verisini ekranın gerektirdiği görüntü zamanlaması ve piksel akışına dönüştürmek.

Display Controller şunları yönetebilir:

- çözünürlük ve timing,
- pixel format,
- frame buffer okuma,
- VSync/blanking,
- katman birleştirme,
- display DMA arayüzü.

Display Controller, panelin tüm analog sürüş elektroniğinin mutlaka içinde bulunduğu anlamına gelmez.

### 3.17 Display Bridge / PHY / Panel Driver

Bu terimler birbirinden ayrılmalıdır.

- **Display Controller:** Görüntü verisini ve zamanlamasını oluşturur.
- **Display PHY:** İlgili fiziksel bağlantının elektriksel veya yüksek hızlı sinyal katmanını gerçekleştirir.
- **Display Bridge:** Bir görüntü arayüzünü başka bir arayüze dönüştürür.
- **Panel Driver:** Panel teknolojisine bağlı olarak piksel satır/sütunlarını veya panelin analog sürüşünü yönetebilir.
- **Touch Controller:** Dokunma algılama sinyallerini koordinat veya olay verisine dönüştürür.

Bir ürün bu bileşenlerden bazılarını entegre edebilir; tümünün ayrı IC olması zorunlu değildir.

---

## 4. Veri Yolu Sınırları

NEXSUS mimarisinde üç farklı bağlantı sınıfı bulunur.

### 4.1 Yerel Veri Yolu

Bir blok içindeki veya yakın bloklar arasındaki bağlantılar.

Örnek:

`ADC Core → Sample Buffer → ADC FIFO`

### 4.2 Çip İçi Interconnect

Aynı çipteki bağımsız alt sistemleri bağlar.

Örnek:

`ADC DMA → On-chip Interconnect → Memory Controller`

### 4.3 Sistem / Expansion Link

Farklı çipleri, kartları veya anakart kaynaklarını bağlar.

Örnek:

`PE5 → Expansion Link → S.Fabric → System Memory`

Fiziksel katman ile protokol katmanı ayrı belirtilmelidir. PCIe uyumlu fiziksel bağlantı kullanılması, üst protokolün otomatik olarak PCIe olduğu anlamına gelmez.

---

## 5. Veri Akışının Sahipliği

Her veri akışında dört farklı görev tanımlanır:

1. **Producer:** Veriyi üreten kaynak.
2. **Buffer:** Veriyi geçici olarak tutan kaynak.
3. **Transport:** Veriyi bir noktadan diğerine taşıyan mekanizma.
4. **Consumer:** Veriyi kullanan hedef.

Örnek:

`ADC → ADC FIFO → DMA → Memory Controller → Memory`

| Aşama | Sorumluluk |
|---|---|
| ADC | Örneği üretir |
| ADC FIFO | Örneği geçici olarak tutar |
| DMA | Transferi gerçekleştirir |
| Memory Controller | Belleğe erişimi yönetir |
| Memory | Veriyi saklar |
| CPU/Fabric | Veriyi işler veya kullanır |

Bu ayrım tasarım belgelerinde korunmalıdır.

---

## 6. Bellek Sınırları

Bellek kavramları da birbirinden ayrılır.

- **Register:** Çok küçük ve hızlı işlem durumu veya operand alanı.
- **FIFO:** Sıralı veri akışını geçici olarak tutan tampon.
- **Distributed RAM:** Fabric mantığına yakın, küçük yerel bellek.
- **Block RAM:** Fabric içinde veya yakınında bulunan daha büyük bellek bloğu.
- **SRAM:** Genel amaçlı hızlı çip içi bellek.
- **MOSRAM:** NEXSUS için önerilen, ayrı fiziksel hücre ve okuma mimarisi doğrulanması gereken bellek yaklaşımı.
- **MSSD:** Kalıcı depolama için önerilen ayrı bellek yaklaşımı.
- **System Memory:** CPU ve sistem kaynaklarının kullandığı ana bellek alanı.
- **Frame Buffer:** Ekran görüntüsünü tutan mantıksal bellek bölgesi; mutlaka ayrı fiziksel bellek olmak zorunda değildir.

Bir FIFO, system memory'nin yerine geçmez. Frame buffer da otomatik olarak ayrı bir bellek çipi anlamına gelmez.

---

## 7. P-Series ve PE-Series Sınırı

### P1–P5: Standalone Programmable Devices

P-Series cihazlar bağımsız kontrol ve veri toplama ürünleridir.

Kendi işlem, I/O, bellek ve bağlantı kaynaklarına sahip olabilirler. P3–P5'te ekran ve ağ özellikleri ürün seviyesine göre entegre edilebilir.

### PE4–PE5: Expansion Variants

PE-Series, aynı temel Fabric mimarisinin genişleme kartı uygulamasıdır.

PE kartları:

- daha fazla I/O,
- daha yüksek veri toplama kapasitesi,
- DSP,
- protokol işleme,
- sensör toplama,
- yüksek hızlı veri akışı

sağlayabilir.

PE4/PE5 ayrı bir Fabric mimarisi değildir. Ancak kartın güç, bağlantı, bellek ve host erişim tasarımı P-Series'ten farklı olabilir.

### S.Fabric ile ilişki

`NEXSUS CPU ↔ S.Fabric ↔ PE4/PE5`

şeması mantıksal ilişkiyi gösterir. Kesin fiziksel bağlantı, protokol ve bant genişliği daha sonra belirlenmelidir.

---

## 8. Display Karar Sınırı

P3–P5 için Display Controller Engine'in ana çipe entegre edilmesi başlangıç tercihidir.

Harici bir çip şu koşullarda gündeme gelir:

- panelin arayüzü ana çipte desteklenmiyorsa,
- gereken PHY ayrı bir bileşen gerektiriyorsa,
- panelin sürüş gerilimi veya analog devresi harici bileşen gerektiriyorsa,
- entegrasyon alan, güç veya maliyet açısından uygun değilse.

Bu nedenle “ekran sürücü çipi” ifadesi tasarım belgelerinde tek başına kullanılmamalıdır. Önce ihtiyaç duyulan bileşen belirtilmelidir: controller, bridge, PHY, panel driver veya touch controller.

P3 için 720p, P4/P5 için FHD hedefi standalone cihaz ailesi için korunur. Bu hedefler henüz panel arayüzü veya fiziksel pinout kararı değildir.

---

## 9. Mimari Olarak Kesinleşenler

Bu sürümle aşağıdaki kavramsal sınırlar sabitlenir:

1. Programmable Fabric ile S.Fabric farklı kapsamlara sahiptir.
2. I/O Router ile Fabric Router farklı görevler üstlenir.
3. DMA ile Memory Controller farklı işlevlerdir.
4. Peripheral Engine ile fiziksel transceiver/PHY aynı şey değildir.
5. Interrupt Matrix ile Trigger Matrix farklı görevler üstlenir.
6. Display Controller ile panel sürüş elektroniği aynı şey değildir.
7. Physical I/O sayısı, logical channel sayısı ve eşzamanlı işleme kapasitesi ayrı ölçülür.
8. P-Series standalone cihazları ile PE-Series expansion kartları aynı temel Fabric yaklaşımını paylaşır, fakat aynı ürün biçiminde değildir.
9. Bileşenlerin mantıksal ayrımı, her biri için ayrı fiziksel çip gerektiği anlamına gelmez.

## 10. Henüz Kesinleşmeyenler

Aşağıdaki kararlar bu dokümanla sabitlenmez:

- S.Fabric'in fiziksel uygulaması,
- çip içi interconnect protokolü,
- DMA engine sayıları ve scheduler algoritması,
- bellek controller topolojisi,
- MOSRAM'ın fiziksel olarak uygulanabilirliği ve performansı,
- ADC'nin kesin çözünürlük/hız kombinasyonları,
- display PHY ve panel arayüzü,
- USB/Ethernet/expansion fiziksel katmanları,
- PE4/PE5 bağlantı protokolü ve bant genişliği,
- saat alanları ve güç alanlarının kesin dağılımı.

Bu kararlar, veri yolu ve kaynak bütçesi hesaplarıyla verilmelidir.

---

## 11. Sonraki Tasarım Kuralı

Bundan sonraki her donanım belgesi şu başlıkları içermelidir:

1. **Purpose:** Bileşenin amacı.
2. **Inputs:** Kabul ettiği veri ve kontrol girişleri.
3. **Outputs:** Ürettiği veri ve olaylar.
4. **Resources:** Bellek, mantık, pin ve saat gereksinimleri.
5. **Interfaces:** Bağlantı protokolleri.
6. **Bandwidth:** Sürekli ve tepe veri kapasitesi.
7. **Latency:** İşlem ve aktarım gecikmesi.
8. **Ownership:** Kaynakları kimin yapılandırdığı ve kullandığı.
9. **Failure Handling:** Hata, taşma ve zaman aşımı davranışı.
10. **Implementation Status:** Kavramsal, modellenmiş, prototiplenmiş veya doğrulanmış.

**Nihai ilke:** NEXSUS'ta mimari sınırlar önce mantıksal olarak belirlenir; fiziksel entegrasyon, kaynak sayıları ve protokoller daha sonra hesaplanır ve doğrulanır.
