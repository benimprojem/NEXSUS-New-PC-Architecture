# NEXSUS Programmable Fabric
## Routing, Configuration and Expansion Architecture Specification v0.2

**Project:** NEXSUS  
**Subsystem:** Programmable Computing Fabric  
**Document Type:** Technical Architecture  
**Status:** Preliminary Architecture Specification  
**Previous Revision:** v0.1  
**Target:** P1–P5 / PE4–PE5

---

# 1. Mimari Genişleme

NEXSUS Programmable Fabric mimarisi yalnızca P1–P5 bağımsız cihazlarında kullanılmak üzere tasarlanmaz.

Fabric kaynaklarının, routing yapısının ve sistem arayüzünün yeterince ölçeklenebilir olması durumunda aynı mimari:

- bağımsız programlanabilir cihazlarda,
- ölçüm ve veri toplama cihazlarında,
- sensör kontrol sistemlerinde,
- protokol dönüştürücülerinde,
- veri işleme modüllerinde,
- NEXSUS anakartına takılan genişleme kartlarında,
- yüksek hızlı veri işleme kartlarında

kullanılabilir.

Bu nedenle mimari iki ürün ailesine ayrılır:

### P-Series

Bağımsız programlanabilir cihaz ailesi:

```text
P1
P2
P3
P4
P5
```

### PE-Series

NEXSUS sistemlerine takılabilen programlanabilir expansion ailesi:

```text
PE4
PE5
```

PE modelleri yeni bir fabric mimarisi değildir.

Temel prensip:

```text
P4 Fabric
    │
    ├── P4 Device
    │
    └── PE4 Expansion

P5 Fabric
    │
    ├── P5 Device
    │
    └── PE5 Expansion
```

Böylece aynı compiler, configuration formatı, routing modeli ve fabric programlama mantığı korunabilir.

---

# 2. Routing Architecture

Fabric performansını yalnızca LUT veya DSP sayısı belirlemez.

Büyük bir fabric için kritik unsurlardan biri:

> **routing kaynaklarının veri akışını darboğaz oluşturmadan taşıyabilmesidir.**

Bu nedenle NEXSUS Fabric routing yapısı üç seviyeye ayrılır:

```text
L0 — Local Routing
        │
        ▼
L1 — Cluster Routing
        │
        ▼
L2 — Global Routing
```

---

# 3. L0 — Local Routing

L0 routing, aynı Logic Tile içerisindeki kaynaklar arasındaki bağlantıyı sağlar.

Temel bağlantılar:

```text
LUT
 │
 ├── Register
 │
 ├── Carry
 │
 ├── Local RAM
 │
 └── Tile Output
```

Bir Logic Tile içerisinde mümkün olduğunca kısa fiziksel bağlantılar kullanılır.

Amaç:

- düşük gecikme,
- düşük routing alanı,
- düşük switching power,
- yüksek maksimum clock frekansı.

L0 routing mümkün olduğunca statik ve deterministik olacaktır.

---

# 4. Logic Tile Data Path

Temel Logic Tile:

```text
                 ┌───────────────┐
Input A ────────►│               │
Input B ────────►│    6-LUT      │
Input C ────────►│               │
                 └───────┬───────┘
                         │
                         ▼
                    ┌─────────┐
                    │ Register│
                    └────┬────┘
                         │
                         ▼
                    Tile Output
```

Ek olarak:

```text
Carry In  ───────────────► Carry Logic
Carry Out ◄─────────────── Carry Logic

Local RAM ◄──────────────► Tile Logic
```

Logic Tile içerisinde mümkün olduğunca fazla operasyonun tek tile veya komşu tile seviyesinde gerçekleştirilebilmesi hedeflenir.

Örneğin:

```text
LUT → Register → LUT → Register
```

şeklindeki pipeline yapısı L0/L1 routing üzerinden kurulabilir.

---

# 5. L1 — Cluster Routing

Bir Cluster içerisinde:

```text
16 × Logic Tile
```

bulunur.

Cluster Router bu tile'ların birbirleriyle ve cluster içerisindeki özel kaynaklarla iletişimini sağlar.

Örnek:

```text
       ┌──────────── Cluster ────────────┐

       Tile ─┐
       Tile ─┤
       Tile ─┤
       Tile ─┤
       ...   ├──► Cluster Router
       Tile ─┤
       Tile ─┤
       Tile ─┘

                │
        ┌───────┼────────┐
        ▼       ▼        ▼
       DSP     BRAM     FIFO
```

Cluster Router aşağıdaki kaynakları bağlayabilir:

- Logic Tile
- DSP/MAC
- Block RAM
- FIFO
- local control
- clock/control resources
- Cluster dışı global routing

---

# 6. Cluster Router Yapısı

Cluster Router merkezi bir crossbar olmak zorunda değildir.

Büyük crossbar yapıları transistor alanını ve routing capacitance'ını hızlı biçimde artırabileceğinden **hiyerarşik ve segmentli routing** tercih edilir.

Önerilen yapı:

```text
             Cluster Router
                  │
       ┌──────────┼──────────┐
       │          │          │
   Local Bus   Data Bus   Control Bus
       │          │          │
   ┌───┴───┐  ┌───┴───┐  ┌───┴───┐
  Tile    Tile Tile    Tile Tile   Tile
```

Burada data ve control yollarının fiziksel olarak tamamen ayrı olması zorunlu değildir.

Ancak mimari seviyede:

- data path,
- control path,
- configuration path

ayrıştırılacaktır.

Bu ayrım routing congestion problemlerini azaltabilir.

---

# 7. Routing Switch

Routing noktalarında programlanabilir switch kullanılır.

Basitleştirilmiş yapı:

```text
             North
               │
               ▼
West ───────► SWITCH ───────► East
               ▲
               │
             South
```

Ek olarak:

```text
               Local
                 │
                 ▼
West ───────► SWITCH ───────► East
                 ▲
                 │
               Global
```

Switch yapısının kesin transistor seviyesi daha sonraki fiziksel tasarım aşamasında belirlenecektir.

İlk mimari hedef:

- yön seçimi,
- bağlantı seçimi,
- bus segment seçimi,
- broadcast desteği,
- multicast desteği,
- pipeline insertion noktaları.

---

# 8. Broadcast ve Multicast

Fabric yalnızca point-to-point routing ile sınırlandırılmamalıdır.

Örneğin ADC verisinin aynı anda:

```text
ADC
 │
 ├──► Filter
 │
 ├──► FFT
 │
 └──► Monitor
```

kaynaklarına gönderilmesi gerekebilir.

Bu nedenle fabric routing:

### Point-to-Point

```text
A ─────────► B
```

### Broadcast

```text
       ┌──► B
A ─────┼──► C
       └──► D
```

### Multicast

```text
A ─────► B
  └────► D
```

modlarını desteklemelidir.

Ancak fiziksel olarak her bağlantıyı çoğaltmak yerine mümkün olduğunca routing network içerisinde ortak veri segmentleri kullanılmalıdır.

---

# 9. L2 — Global Routing

Global routing cluster'lar arasındaki bağlantıyı sağlar.

```text
Cluster 0 ─────┐
Cluster 1 ─────┤
Cluster 2 ─────┤
Cluster 3 ─────┼──── Global Fabric
Cluster 4 ─────┤
Cluster 5 ─────┤
Cluster N ─────┘
```

Global Fabric aşağıdaki kaynaklara erişim sağlayabilir:

```text
Logic Clusters
      │
      ├── DSP
      ├── BRAM
      ├── FIFO
      ├── DMA
      ├── Memory Controller
      ├── CPU Interface
      └── External I/O
```

---

# 10. Global Fabric Bus

Global Fabric'in tamamen tek bir ortak bus olarak tasarlanması önerilmemektedir.

Bunun yerine segmented/interconnected network yaklaşımı kullanılmalıdır.

Örneğin:

```text
Cluster 0 ──┐
Cluster 1 ──┤
             ├── Segment A
Cluster 2 ──┘
                 │
                 ▼
              Bridge
                 │
                 ▼
Cluster 3 ──┐
Cluster 4 ──┤
             ├── Segment B
Cluster 5 ──┘
```

Bu yapı büyük fabric'lerde routing congestion'ı azaltabilir.

Kesin topology:

- mesh,
- hierarchical mesh,
- segmented bus,
- hybrid network

seçenekleri fiziksel tasarım simülasyonları sonucunda belirlenecektir.

---

# 11. Fabric Network-on-Chip Yaklaşımı

P4/P5 ve özellikle PE4/PE5 seviyesinde fabric büyüdükçe klasik FPGA tarzı routing network yeterli olmayabilir.

Bu nedenle NEXSUS Fabric'in ilerleyen sürümlerinde:

> **Fabric NoC**

yaklaşımı değerlendirilecektir.

Örneğin:

```text
┌────┐    ┌────┐    ┌────┐
│ C0 │────│ C1 │────│ C2 │
└────┘    └────┘    └────┘
  │         │         │
  │         │         │
┌────┐    ┌────┐    ┌────┐
│ C3 │────│ C4 │────│ C5 │
└────┘    └────┘    └────┘
```

Burada cluster'lar network node olarak davranabilir.

Bu yaklaşım özellikle PE5 gibi yüksek kaynaklı modeller için önemlidir.

---

# 12. Pipeline Routing

Uzun routing yollarında yalnızca kombinasyonel bağlantı kullanılması maksimum clock frekansını düşürebilir.

Bu nedenle routing network üzerinde pipeline noktaları bulunabilir.

Örnek:

```text
Cluster A
   │
   ▼
[Route]
   │
[REG]
   │
   ▼
[Route]
   │
[REG]
   │
   ▼
Cluster B
```

Böylece:

```text
Routing delay
      ↓
Pipeline
      ↓
Higher Fmax
```

elde edilebilir.

Bu register'ların otomatik yerleştirilmesi OCC'nin görevlerinden biri olabilir.

---

# 13. Configuration Fabric

Fabric'in çalışma yapısı configuration memory tarafından belirlenir.

Configuration aşağıdaki kaynakları kontrol eder:

```text
LUT Configuration
Routing Switches
Registers
DSP Modes
FIFO Modes
BRAM Modes
I/O Modes
Clock Configuration
DMA Configuration
Interrupt Routing
```

Temel ayrım:

```text
Configuration Plane
        │
        ▼
Fabric
        │
        ▼
Data Plane
```

Configuration plane normal veri akışından mümkün olduğunca ayrılmalıdır.

---

# 14. Full Configuration

Power-on veya reset sonrasında fabric tamamen yeniden yapılandırılabilir.

Örnek:

```text
Configuration Storage
        │
        ▼
Fabric Configuration Controller
        │
        ▼
┌─────────────────────┐
│ Routing             │
│ LUT                 │
│ DSP                 │
│ FIFO                │
│ BRAM                │
│ I/O                 │
└─────────────────────┘
```

Bu işlem sonucunda cihaz belirli bir uygulama için özel bir hardware accelerator haline gelebilir.

Örneğin:

```text
P4
 │
 └── Configuration A
       │
       └── FFT + Filter + ADC

P4
 │
 └── Configuration B
       │
       └── Protocol Converter
```

Aynı fiziksel chip farklı görevlerde kullanılabilir.

---

# 15. Partial Reconfiguration

P4/P5 ve özellikle PE4/PE5 için partial reconfiguration desteklenmesi hedeflenmektedir.

Örneğin:

```text
┌────────────────────────────────────┐
│        Fabric                      │
│                                    │
│  Static Region                     │
│                                    │
│  ┌──────────────┐                  │
│  │ Reconfig A   │                  │
│  └──────────────┘                  │
│                                    │
│  Static Region                     │
└────────────────────────────────────┘
```

`Reconfig A` yeniden programlanırken diğer fabric bölümleri çalışmaya devam edebilir.

Örnek:

```text
ADC Controller
      │
      ▼
Filter
      │
      ▼
[Reconfigurable DSP]
      │
      ▼
FIFO
```

DSP algoritması değiştirilebilirken ADC ve FIFO altyapısı korunabilir.

Bu özellik özellikle:

- ölçüm cihazları,
- protokol dönüştürücüler,
- test cihazları,
- veri işleme sistemleri

için değerlidir.

---

# 16. Fabric ↔ CPU Interface

Fabric ile CPU arasında doğrudan bir kontrol/data interface bulunmalıdır.

Temel yapı:

```text
              NEXSUS CPU
                  │
          Fabric Control Interface
                  │
                  ▼
        ┌────────────────────┐
        │ Fabric Controller  │
        └─────────┬──────────┘
                  │
          ┌───────┴───────┐
          ▼               ▼
      Config Plane     Data Plane
```

CPU'nun her fabric operasyonunda doğrudan veri taşıması hedeflenmez.

Örneğin:

```text
CPU
 │
 └── Configure FFT
       │
       ▼
     Fabric
       │
       ▼
ADC → FFT → FIFO → Memory
```

CPU yalnızca:

- başlatma,
- durdurma,
- parametre değiştirme,
- durum okuma,
- hata yönetimi

işlerini yapabilir.

Verinin kendisi fabric tarafından taşınabilir.

---

# 17. Fabric ↔ System Memory

Fabric'in system memory'ye erişimi DMA üzerinden gerçekleştirilmelidir.

```text
ADC
 │
 ▼
Fabric Processing
 │
 ▼
FIFO
 │
 ▼
DMA
 │
 ▼
System Memory
```

CPU:

```text
"Bu buffer'ı kullan."
```

komutunu verebilir.

Ancak:

```text
ADC → CPU → Memory
```

şeklinde her veri kelimesinin CPU üzerinden geçirilmesi gerekmez.

Bu yapı özellikle yüksek örnekleme hızlarında CPU yükünü ciddi şekilde azaltabilir.

---

# 18. Fabric ↔ I/O

I/O kaynakları fabric'e doğrudan bağlanabilir.

Örneğin:

```text
Physical Pin
     │
     ▼
I/O Controller
     │
     ▼
Fabric
     │
 ┌───┼────┬──────┐
 ▼   ▼    ▼      ▼
UART SPI  FIFO   DSP
```

Bu sayede aynı fiziksel pin farklı görevlerde kullanılabilir.

Örnek:

```text
GPIO
UART
SPI
I2C
PWM
CAN
Trigger
Custom Protocol
```

seçilebilir.

---

# 19. PE4 / PE5 Expansion Architecture

PE4 ve PE5, P4/P5 fabric mimarisinin expansion-card varyantları olarak tanımlanır.

Temel yapı:

```text
NEXSUS Motherboard
        │
        │ High-Speed Fabric Interface
        ▼
┌───────────────────────┐
│ PE4 / PE5             │
│                       │
│ Programmable Fabric   │
│ DSP                   │
│ FIFO                  │
│ BRAM                  │
│ DMA                   │
│ I/O                   │
└───────────────────────┘
```

PE kartının görevi klasik bir ekran kartı olmak zorunda değildir.

Örneğin:

### PE4

```text
High-speed data acquisition
Protocol conversion
Sensor processing
DSP acceleration
Industrial I/O
```

### PE5

```text
High-throughput DSP
Multi-channel acquisition
Large data pipelines
Network processing
Hardware acceleration
Custom device interfaces
```

---

# 20. PE4 / PE5 ve S.Fabric

NEXSUS anakartında PE kartlarının doğrudan S.Fabric tarafından yönetilmesi hedeflenmektedir.

```text
                  NEXSUS CPU
                      │
                      ▼
                   S.Fabric
                 ┌────┼────┐
                 │    │    │
                 ▼    ▼    ▼
               PE4   PE5   Other
```

Bu durumda expansion kartı yalnızca CPU tarafından görülen bir PCIe benzeri cihaz olmak zorunda değildir.

S.Fabric kartı sistemin native fabric resource'u olarak tanıyabilir.

Bu, NEXSUS mimarisinin önemli farklılıklarından biri olabilir.

---

# 21. PE Kartları İçin Fiziksel Interface

PE4/PE5 için fiziksel interface ayrı bir tasarım aşamasında belirlenecektir.

Olası seçenekler:

```text
PCIe-compatible physical layer
        +
NEXSUS Fabric Protocol
```

veya:

```text
NEXSUS Native High-Speed Link
```

İlk prototiplerde standart yüksek hızlı fiziksel katmanların kullanılması maliyet ve geliştirme süresini azaltabilir.

Ancak üst protokol:

```text
NEXSUS Fabric Link
```

olarak tanımlanabilir.

Böylece fiziksel bağlantı ile sistem protokolü birbirinden ayrılır.

---

# 22. Fabric Link

PE4/PE5 ile S.Fabric arasındaki bağlantı aşağıdaki mantığı taşıyabilir:

```text
┌──────────────┐
│ S.Fabric     │
└──────┬───────┘
       │
       │ Fabric Link
       │
┌──────▼───────┐
│ PE4 / PE5    │
└──────────────┘
```

Link üzerinde:

- configuration traffic,
- control traffic,
- DMA traffic,
- interrupt/event traffic,
- memory transaction,
- fabric synchronization

taşınabilir.

---

# 23. Ürün Ailesi

Bu mimari sonucunda ürün ailesi şu şekilde konumlandırılabilir:

| Model | Sınıf | Fabric | Display | Touch | PC/System bağlantısı |
|---|---|---|---|---|---|
| P1 | Basic Controller | küçük | optional | – | USB-C |
| P2 | Device Controller | orta | small LCD | – | USB-C |
| P3 | Advanced Controller | büyük | 720p | ✓ | USB-C / Ethernet / Wireless |
| P4 | High Performance | çok büyük | FHD | ✓ | Ethernet / Wireless |
| P5 | High-End Controller | çok büyük | FHD | ✓ | Ethernet / Wireless |
| PE4 | Expansion Fabric | çok büyük | – | – | S.Fabric |
| PE5 | High-End Expansion | maksimum | – | – | S.Fabric |

PE4/PE5 cihazlarında display ve touch bulunması zorunlu değildir.

Bunlar esas olarak:

> **programmable compute / I/O / acceleration expansion**

modülleridir.

---

# 24. Mimari Sonuç

Bu yapı sayesinde NEXSUS Fabric tek bir ürünün donanımına bağlı kalmaz.

Aynı temel mimari:

```text
                    NEXSUS FABRIC
                         │
          ┌──────────────┴──────────────┐
          │                             │
       P-Series                       PE-Series
          │                             │
    ┌─────┼─────┐                  ┌────┴────┐
    P1    P2    P3                  PE4      PE5
                │
              ┌─┴─┐
              P4 P5
```

şeklinde ölçeklenebilir.

Daha önemlisi, bütün modeller aynı temel yazılım ekosistemini paylaşabilir:

```text
                 OCC
                  │
          ┌───────┴────────┐
          │                │
       CPU Code       Fabric Image
          │                │
          ▼                ▼
      NEXSUS CPU       P / PE Fabric
```

Bu durumda OCC yalnızca CPU compiler olmaktan çıkar ve:

> **NEXSUS System Compiler**

haline gelir.

---

# 25. Sonraki Fiziksel Tasarım Aşaması

Routing mimarisinin mantıksal tanımı tamamlandıktan sonra aşağıdaki blokların ayrıntılı olarak tanımlanması gerekir:

1. Logic Tile transistor-level abstraction
2. LUT yapısı
3. Register yapısı
4. Routing switch
5. Cluster Router
6. Global Router
7. Fabric NoC
8. DSP/MAC block
9. Block RAM
10. FIFO
11. DMA
12. Fabric Controller
13. Configuration Memory
14. Partial Reconfiguration Controller
15. Clock Network
16. Reset Network
17. Fabric ↔ CPU interface
18. Fabric ↔ S.Fabric interface
19. PE4/PE5 physical link
20. OCC Fabric Mapping

Bu aşamada **LUT sayısını artırmaktan önce routing mimarisini kesinleştirmek** daha doğru olacaktır.

Çünkü gerçek fabric performansını belirleyecek temel soru:

```text
"Kaç LUT var?"
```

değil,

```text
"Bu LUT'lar birbirleriyle ne kadar hızlı ve ne kadar düşük
enerji maliyetiyle iletişim kurabiliyor?"
```

sorusudur.

Bu nedenle bir sonraki tasarım adımı:

> **Routing Switch + Cluster Router'ın ayrıntılı mimarisinin çıkarılması**

olmalıdır.
---