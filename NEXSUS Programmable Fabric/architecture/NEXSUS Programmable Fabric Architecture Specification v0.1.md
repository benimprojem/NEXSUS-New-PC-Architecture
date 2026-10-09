# NEXSUS Programmable Fabric
## Architecture Specification v0.1

**Project:** NEXSUS  
**Subsystem:** Programmable Computing Fabric  
**Document Type:** Technical Architecture  
**Status:** Preliminary Architecture Specification  
**Target:** NEXSUS P1–P5 Programmable Devices

---

## 1. Overview

NEXSUS Programmable Fabric, NEXSUS işlemci ve cihaz mimarisinin genel amaçlı programlanabilir donanım katmanıdır.

Fabric'in amacı yalnızca FPGA benzeri programlanabilir lojik sağlamak değildir. Sistem;

- programlanabilir lojik,
- paralel işlem,
- yerel bellek,
- FIFO,
- DSP/MAC,
- programlanabilir I/O,
- cihaz protokolleri,
- yüksek hızlı veri akışı

işlevlerini tek bir hiyerarşik mimari altında birleştirmeyi hedefler.

NEXSUS Programmable Fabric, P1–P5 ürün ailesinin tamamında aynı temel mimariyi kullanır. Ürünler arasındaki temel fark, fabric kaynaklarının miktarı, bağlantı genişliği, bellek kapasitesi, işlem kaynakları ve I/O kapasitesidir.

---

# 2. Design Principles

NEXSUS Programmable Fabric aşağıdaki temel prensiplere göre tasarlanır.

### 2.1 Hierarchical Fabric

Fabric tek seviyeli bir bağlantı ağı yerine üç seviyeli bir yapı kullanır:

```text
Logic Tile
    ↓
Cluster
    ↓
Global Fabric
```

Bu yapı, küçük yerel işlemlerin global routing ağına gereksiz şekilde taşınmasını önlemeyi amaçlar.

### 2.2 Locality

Birbirine yakın çalışan lojik kaynakları mümkün olduğunca yerel bağlantılar üzerinden haberleşir.

Bu sayede:

- routing yükü,
- bağlantı gecikmesi,
- güç tüketimi

azaltılabilir.

### 2.3 Dataflow-Oriented Operation

Fabric, klasik işlemci gibi yalnızca komutları sırayla yürütmek için değil, sürekli veri akışını işlemek için tasarlanır.

Örnek:

```text
ADC
 │
 ▼
Filter
 │
 ▼
FFT
 │
 ▼
Threshold
 │
 ▼
FIFO
 │
 ▼
Ethernet / USB
```

Bu yapı oluşturulduğunda veri akışının her aşaması bağımsız donanım olarak çalışabilir.

### 2.4 CPU Independence

Fabric, NEXSUS CPU'nun yardımcısı olarak çalışabilir ancak CPU'ya sürekli bağımlı olmak zorunda değildir.

CPU:

- yapılandırmayı başlatabilir,
- fabric'i programlayabilir,
- parametreleri değiştirebilir,
- sonuçları okuyabilir.

Ancak sürekli veri işleme fabric tarafından gerçekleştirilebilir.

---

# 3. Logic Tile

Logic Tile, NEXSUS Programmable Fabric'in temel programlanabilir birimidir.

Önerilen temel yapı:

```text
┌───────────────────────────────┐
│        NEXSUS LOGIC TILE      │
│                               │
│  ┌─────┐ ┌─────┐              │
│  │LUT  │ │LUT  │              │
│  ├─────┤ ├─────┤              │
│  │LUT  │ │LUT  │              │
│  └─────┘ └─────┘              │
│                               │
│  Flip-Flops                   │
│  Local RAM                    │
│  Carry Logic                  │
│  Local Routing                │
│  Configuration               │
└───────────────────────────────┘
```

İlk mimari hedef olarak bir Logic Tile:

- 4 adet 6-input LUT
- 8 adet temel register/flip-flop
- local routing
- carry path
- küçük distributed RAM
- configuration state

içerecek şekilde tanımlanabilir.

Bu değerler ilk mimari referanstır ve fiziksel implementasyon sırasında değiştirilebilir.

---

# 4. LUT Architecture

NEXSUS Logic Tile içerisindeki temel lojik elemanı 6-input LUT'tur.

Bir LUT:

```text
A
B
C
D
E
F
│
▼
┌────────┐
│ 6-LUT  │
└────┬───┘
     │
     ▼
    OUT
```

şeklinde çalışır.

Dört LUT'un aynı tile içerisinde bulunması, küçük kombinasyonel mantık fonksiyonlarının tek bir yerel kaynak grubu içinde oluşturulmasına olanak sağlar.

LUT'lar aşağıdaki gibi zincirlenebilir:

```text
LUT0 → LUT1 → LUT2 → LUT3
```

Bu bağlantıların local routing üzerinden gerçekleştirilmesi hedeflenir.

---

# 5. Local Register Architecture

Her Logic Tile içerisindeki LUT çıkışları register'lara bağlanabilir.

```text
LUT
 │
 ▼
Register
 │
 ▼
Local Routing
```

Bu yapı iki temel çalışma biçimi sağlar:

### Combinational

```text
Input → LUT → Output
```

### Sequential

```text
Input → LUT → Register → Output
```

Böylece fabric hem kombinasyonel hem de saat kontrollü veri yolları oluşturabilir.

---

# 6. Carry and Arithmetic Path

Toplama, çıkarma ve karşılaştırma gibi işlemler için LUT routing üzerinden uzun zincirler oluşturmak yerine özel carry bağlantıları kullanılmalıdır.

Örnek:

```text
Tile 0
  │
Carry
  ▼
Tile 1
  │
Carry
  ▼
Tile 2
  │
Carry
  ▼
Tile 3
```

Bu yapı özellikle:

- counter,
- adder,
- subtractor,
- comparator,
- address generator

gibi devrelerin daha verimli oluşturulmasını sağlar.

---

# 7. Logic Cluster

Logic Tile'lar tek başına büyük sistemler oluşturmak yerine Cluster adı verilen gruplar halinde düzenlenir.

Önerilen ilk yapı:

```text
┌─────────────────────────────┐
│        LOGIC CLUSTER        │
│                             │
│ Tile  Tile  Tile  Tile      │
│                             │
│ Tile  Tile  Tile  Tile      │
│                             │
│ Tile  Tile  Tile  Tile      │
│                             │
│ Tile  Tile  Tile  Tile      │
│                             │
│       Cluster Router        │
└─────────────────────────────┘
```

Bir Cluster için başlangıç hedefi:

**16 Logic Tile**

olarak belirlenebilir.

Böylece:

```text
1 Cluster = 16 Tiles
```

olur.

---

# 8. Cluster Router

Cluster içerisindeki tile'lar öncelikle Cluster Router üzerinden haberleşir.

```text
Tile
 │
 ├─────────────┐
 │             │
 ▼             ▼
Local        Cluster
Route        Router
               │
               ▼
          Other Tiles
```

Bu router, global fabric'e çıkmadan Cluster içindeki iletişimi mümkün olduğunca tamamlamayı amaçlar.

Bu mimari sayesinde küçük bir hesaplama devresinin bütün çip routing ağına bağlanması gerekmez.

---

# 9. Global Fabric

Cluster'lar arasındaki iletişim Global Fabric tarafından sağlanır.

```text
       Cluster
          │
          ▼
    ┌────────────┐
    │   Global   │
    │   Router   │
    └─────┬──────┘
          │
     ┌────┼────┐
     ▼    ▼    ▼
 Cluster Cluster Cluster
```

Global Fabric;

- Cluster-to-Cluster data,
- Memory access,
- DSP access,
- FIFO access,
- I/O communication

için kullanılabilir.

---

# 10. Routing Hierarchy

NEXSUS routing sistemi üç temel seviyeye ayrılır.

### L0 — Local Routing

Logic Tile içerisindeki bağlantılar.

```text
LUT ↔ LUT
LUT ↔ Register
Register ↔ LUT
```

### L1 — Cluster Routing

Aynı Cluster içerisindeki Tile'lar.

```text
Tile ↔ Tile
Tile ↔ Cluster Router
```

### L2 — Global Routing

Cluster'lar ve sistem kaynakları.

```text
Cluster ↔ Cluster
Cluster ↔ RAM
Cluster ↔ DSP
Cluster ↔ I/O
```

Bu yapı:

```text
L0 → L1 → L2
```

şeklinde hiyerarşik olarak çalışır.

---

# 11. DSP / MAC Blocks

P3 ve üstü modellerde fabric içerisinde özel DSP/MAC blokları bulunur.

Temel DSP yapısı:

```text
        A
        │
        ▼
      ┌─────┐
B ───►│ MUL │
      └──┬──┘
         │
         ▼
      ┌─────┐
C ───►│ ADD │
      └──┬──┘
         │
         ▼
       OUT
```

DSP blokları aşağıdaki işlemleri destekleyecek şekilde tasarlanabilir:

- multiplication
- addition
- subtraction
- multiply-accumulate
- accumulation
- shift
- comparison

İlk hedef veri genişlikleri:

```text
INT8
INT16
INT32
FP16
FP32
```

olarak belirlenebilir.

FP32 desteği özellikle P4/P5 seviyesinde isteğe bağlı veya kaynak maliyetine bağlı olarak değerlendirilebilir.

---

# 12. FIFO Fabric

NEXSUS Fabric içerisinde FIFO kaynakları temel donanım bileşeni olarak bulunur.

Örnek veri yolu:

```text
ADC
 │
 ▼
FIFO
 │
 ▼
Filter
 │
 ▼
FIFO
 │
 ▼
DSP
 │
 ▼
FIFO
 │
 ▼
Network
```

FIFO kullanımı:

- ADC buffering
- sensor streaming
- DMA
- protocol conversion
- burst transfer
- CPU/Fabric synchronization

için kullanılabilir.

---

# 13. Memory Architecture

Fabric belleği üç seviyede ele alınır.

```text
                 Memory System
                      │
        ┌─────────────┼─────────────┐
        │             │             │
 Distributed RAM   Block RAM    System Memory
        │             │             │
     Logic Tile    Cluster       External
```

### Distributed RAM

Logic Tile içerisinde küçük veri depolama.

### Block RAM

Fabric içerisinde yüksek hızlı yerel veri depolama.

### System Memory

Fabric'in NEXSUS sistem belleğine erişimi.

P4/P5 sistemlerinde harici yüksek kapasiteli bellek desteği ayrıca sağlanabilir.

---

# 14. Memory-to-Fabric Interface

Fabric ile sistem belleği arasındaki erişim doğrudan CPU üzerinden yapılmak zorunda değildir.

```text
Fabric
   │
   ▼
Memory Controller
   │
   ▼
System Memory
```

Bu yapı DMA benzeri doğrudan veri transferlerine olanak sağlar.

Örneğin:

```text
ADC
 ↓
Fabric
 ↓
DMA
 ↓
System Memory
```

CPU yalnızca transferi başlatabilir ve sonucu daha sonra işleyebilir.

---

# 15. Programmable I/O Fabric

NEXSUS GPIO sistemi yalnızca sabit GPIO işlevlerinden oluşmaz.

Bir fiziksel pin:

```text
GPIO
UART
SPI
I²C
PWM
CAN
Trigger
Custom I/O
```

işlevlerinden biri olarak yapılandırılabilir.

P3 ve üstü modellerde özel I/O state-machine kaynakları bulunması hedeflenir.

Bu sayede üreticiye özel cihaz protokolleri fabric içerisinde doğrudan oluşturulabilir.

---

# 16. Custom Device Interface

Örneğin harici bir ölçüm cihazı:

```text
CLK
DATA
SYNC
TRIGGER
```

sinyallerini kullanıyorsa, NEXSUS fabric içerisinde buna özel bir interface oluşturulabilir.

```text
Device
 │
 ▼
Programmable I/O
 │
 ▼
State Machine
 │
 ▼
FIFO
 │
 ▼
NEXSUS Data Fabric
```

Bu özellik NEXSUS'un cihaz arayüzü kullanım alanının temel özelliklerinden biri olacaktır.

---

# 17. Fabric Clock Domains

Fabric tek bir global saat ile sınırlandırılmaz.

Önerilen saat domainleri:

```text
Fabric Clock
Peripheral Clock
Memory Clock
I/O Clock
ADC Clock
Low-Power Clock
```

P1–P5 modellerinde desteklenen bağımsız clock domain sayısı:

| Model | Clock Domains |
|---|---:|
| P1 | 3 |
| P2 | 4 |
| P3 | 5 |
| P4 | 6 |
| P5 | 8 |

Clock domain'ler arasındaki veri aktarımı FIFO veya uygun clock-domain-crossing mekanizmaları üzerinden gerçekleştirilir.

---

# 18. Initial Fabric Scaling

İlk mimari kaynak hedefleri:

| Kaynak | P1 | P2 | P3 | P4 | P5 |
|---|---:|---:|---:|---:|---:|
| Logic Tiles | 256 | 1,024 | 4,096 | 12,288 | 32,768 |
| 6-LUT | 1,024 | 4,096 | 16,384 | 49,152 | 131,072 |
| Flip-Flops | 2,048 | 8,192 | 32,768 | 98,304 | 262,144 |
| DSP/MAC | 16 | 64 | 256 | 512 | 1,024 |
| Block RAM | 256 KB | 1 MB | 4 MB | 8 MB | 16 MB |
| FIFO Resources | 16 | 64 | 256 | 512 | 1,024 |

Bu tablo mimarinin ilk ölçeklendirme modelidir.

Fiziksel silikon tasarımına geçildiğinde:

- transistor budget,
- process node,
- die area,
- routing density,
- power budget,
- package,
- yield

gibi parametreler dikkate alınarak yeniden optimize edilmelidir.

---

# 19. Fabric Programming Model

NEXSUS Programmable Fabric, NEXSUS Flow ve OCC Compiler ile programlanacaktır.

Örnek:

```text
target = "nexsus_p3"
```

olarak seçildiğinde OCC:

1. algoritmayı analiz eder,
2. paralelleştirilebilir bölümleri belirler,
3. fabric kaynaklarını tahsis eder,
4. Logic Tile yapılandırmasını oluşturur,
5. DSP/FIFO/Memory kaynaklarını eşler,
6. routing bağlantılarını oluşturur,
7. configuration image üretir.

Sonuç:

```text
NEXSUS Flow
      │
      ▼
     OCC
      │
      ├───────────────┐
      │               │
      ▼               ▼
 CPU Code       Fabric Configuration
      │               │
      ▼               ▼
 NEXSUS CPU       NEXSUS Fabric
```

Böylece NEXSUS Flow yalnızca CPU programı üreten bir compiler değil, gerektiğinde **donanım yapılandırması üreten bir sistem derleyicisi** haline gelir.

---

# 20. Target Architecture

NEXSUS'un uzun vadeli hedefi:

```text
                NEXSUS FLOW
                     │
                     ▼
                    OCC
                     │
        ┌────────────┼─────────────┐
        │            │             │
        ▼            ▼             ▼
     CPU Code    Fabric Image    Device I/O
        │            │             │
        ▼            ▼             ▼
   NEXSUS CPU    P1–P5 Fabric   NEXSUS Device
```

şeklinde ortak bir geliştirme modelidir.

Bu yaklaşımda yazılım ve programlanabilir donanım birbirinden tamamen ayrı geliştirilmek yerine aynı sistem tanımının farklı hedefleri haline gelir.

---

# 21. Architectural Goal

NEXSUS Programmable Fabric'in temel amacı yeni bir FPGA standardı oluşturmak değil, **genel amaçlı programlanabilir cihazların ortak bir donanım ve yazılım mimarisini oluşturmak**tır.

Aynı mimari;

- ölçüm cihazı arayüzü,
- sensör kontrolörü,
- otomasyon kontrolörü,
- veri toplama cihazı,
- protokol dönüştürücü,
- özel işlem hızlandırıcı,
- robotik yardımcı kontrolör,
- laboratuvar cihazı kontrolörü

gibi farklı sistemlerde kullanılabilir.

NEXSUS P1–P5 ürün ailesi bu nedenle yalnızca performans açısından değil, **programlanabilir kaynak miktarı ve cihaz bağımsızlığı açısından** ölçeklenir.

---

## 22. Next Architecture Layer

Bir sonraki tasarım aşamasında aşağıdaki bileşenler tanımlanacaktır:

1. **Logic Tile fiziksel veri yolu**
2. **Cluster Router mimarisi**
3. **Global Router mimarisi**
4. **Routing switch yapısı**
5. **Configuration memory**
6. **Partial reconfiguration**
7. **DSP/MAC iç mimarisi**
8. **Block RAM organizasyonu**
9. **FIFO yapısı**
10. **Fabric ↔ CPU interface**
11. **Fabric ↔ System Memory interface**
12. **Fabric ↔ NEXSUS I/O interface**
13. **Configuration image format**
14. **OCC → Fabric compilation pipeline**

Bu katmanların tamamlanmasıyla NEXSUS Programmable Fabric'in mimari tanımı, ürün seviyesinden gerçek bir **donanım mimarisi spesifikasyonuna** dönüşecektir.
---