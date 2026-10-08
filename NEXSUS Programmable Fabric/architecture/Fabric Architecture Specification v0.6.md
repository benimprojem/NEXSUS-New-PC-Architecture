# NEXSUS Programmable Fabric
## Peripheral Protocol, Display & Control Engine Specification v0.6

**Document Type:** Technical Architecture Specification  
**Status:** Preliminary Architecture  
**Platform:** NEXSUS Programmable Fabric  
**Scope:** P1–P5 / PE4–PE5  
**Version:** 0.6

---

# 1. Amaç

v0.6 ile NEXSUS Programmable Fabric'in I/O katmanının üstündeki temel peripheral engines tanımlanır.

Bu katman:

- UART
- SPI
- I²C
- CAN
- Custom Protocol Engine
- Interrupt Matrix
- Trigger Matrix
- DMA interface
- Display Controller
- Display DMA
- Touch Interface

bileşenlerini kapsar.

Temel amaç, CPU'nun düşük seviyeli I/O işlemlerinin tamamını tek tek yönetmek zorunda kalmamasıdır.

---

# 2. Peripheral Engine Mimarisi

Genel yapı:

```text
                    ┌────────────────────┐
                    │       CPU          │
                    └─────────┬──────────┘
                              │
                       Control Interface
                              │
                    ┌─────────▼──────────┐
                    │  Peripheral Fabric │
                    └─────────┬──────────┘
                              │
       ┌──────────┬───────────┼────────────┬─────────────┐
       │          │           │            │             │
      UART       SPI         I²C          CAN       Custom Protocol
       │          │           │            │             │
       └──────────┴───────────┴────────────┴─────────────┘
                              │
                         I/O Router
                              │
                           Pins
```

Peripheral engine'ler Fabric kaynakları olarak görülür.

---

# 3. UART Engine

UART engine temel olarak:

```text
TX
RX
Baud Generator
FIFO
Status
Interrupt
DMA
```

bileşenlerinden oluşur.

Veri yolu:

```text
CPU / Fabric
      │
      ▼
TX FIFO
      │
      ▼
UART Engine
      │
      ▼
Physical Pin
```

RX:

```text
Physical Pin
      │
      ▼
UART Engine
      │
      ▼
RX FIFO
      │
      ▼
DMA / Fabric / CPU
```

## UART özellikleri

İlk hedef:

- 5–9 bit data mode
- configurable parity
- 1/1.5/2 stop bit
- configurable baud rate
- TX/RX FIFO
- hardware flow control
- interrupt
- DMA
- break detection
- framing/error detection

---

# 4. SPI Engine

SPI engine:

```text
SCLK
MOSI
MISO
CS0...CSn
```

hatlarını yönetir.

Önerilen mimari:

```text
SPI Engine
├── Clock Generator
├── TX FIFO
├── RX FIFO
├── CS Controller
├── Mode Controller
├── DMA Interface
└── Fabric Interface
```

SPI mode:

```text
Mode 0
Mode 1
Mode 2
Mode 3
```

desteklenebilir.

CS sayısı engine başına yapılandırılabilir olmalıdır.

---

# 5. I²C Engine

I²C engine:

```text
SCL
SDA
```

hatlarını yönetir.

Temel özellikler:

- Master
- Slave
- Multi-master hazırlığı
- Start/Stop
- ACK/NACK
- Clock stretching
- Arbitration
- FIFO
- Interrupt
- DMA

I²C'nin open-drain yapısı I/O driver katmanında desteklenmelidir.

---

# 6. CAN Engine

CAN P2'den itibaren kullanılabilir.

```text
CAN Controller
      │
      ▼
CAN Transceiver
      │
      ▼
CAN Bus
```

Burada önemli ayrım:

> CAN controller Fabric içinde bulunur; fiziksel CAN transceiver ayrı analog/PHY katmanıdır.

Dolayısıyla çip doğrudan CANH/CANL pinlerini sürmek zorunda değildir.

Harici transceiver kullanılabilir.

---

# 7. Custom Protocol Engine

NEXSUS'un önemli peripheral bileşenlerinden biri Custom Protocol Engine'dir.

Amaç yalnızca mevcut protokolleri desteklemek değil, özel cihaz protokollerini CPU kullanmadan gerçekleştirmektir.

Temel yapı:

```text
                  ┌──────────────────┐
Input ───────────►│ State Machine    │
                  │                  │
                  │ Parser           │
                  │ Matcher          │
                  │ Counter          │
                  │ Timer            │
                  │ CRC              │
                  │ Response Engine  │
                  └────────┬─────────┘
                           │
                           ▼
                         FIFO
```

---

# 8. Custom Protocol State Machine

Protokol aşağıdaki gibi tanımlanabilir:

```text
IDLE
 │
 ▼
HEADER
 │
 ▼
LENGTH
 │
 ▼
PAYLOAD
 │
 ▼
CRC
 │
 ├── ERROR → ERROR
 │
 └── OK → RESPONSE
```

Bu state machine Fabric tarafından oluşturulabilir.

Böylece örneğin özel bir sensör protokolü için CPU interrupt beklemek zorunda kalmaz.

---

# 9. Hardware Parser

Custom Protocol Engine temel seviyede:

```text
Byte Match
Bit Match
Header Detect
Length Detect
CRC
Checksum
Timeout
Sequence Detect
```

işlemlerini donanımda gerçekleştirebilir.

Örnek:

```text
AA 55 [LEN] [TYPE] [DATA...] [CRC]
```

paketi doğrudan donanım tarafından ayrıştırılabilir.

---

# 10. Protocol FIFO

Her yüksek hızlı protocol engine için FIFO bulunur.

```text
Physical I/O
      │
      ▼
Protocol Engine
      │
      ▼
RX FIFO
      │
      ├──► Fabric
      ├──► DMA
      └──► CPU
```

TX tarafında da aynı yapı kullanılır.

---

# 11. Interrupt Matrix

Peripheral engine'lerden gelen olaylar merkezi Interrupt Matrix'e bağlanır.

```text
UART ─────┐
SPI ──────┤
I²C ──────┤
CAN ──────┤
ADC ──────┤
DMA ──────┤
GPIO ─────┤
Timer ────┤
Display ──┤
Touch ────┤
           ▼
    Interrupt Matrix
           │
      ┌────┴────┐
      ▼         ▼
     CPU      Fabric
```

Interrupt doğrudan CPU'ya gitmek zorunda değildir.

Örneğin:

```text
ADC Threshold
     │
     ▼
Fabric Event
     │
     ▼
DSP
```

şeklinde tamamen donanımsal işlem yapılabilir.

---

# 12. Event / Trigger Matrix

Interrupt ile Trigger aynı şey değildir.

### Interrupt

CPU veya yazılımı bilgilendirir.

### Trigger

Başka bir donanım bloğunu başlatır.

Örnek:

```text
Timer Event
    │
    ├──► ADC Start
    ├──► PWM Update
    ├──► DMA Start
    └──► Timestamp
```

Bu ayrım sistem latency'sini azaltır.

---

# 13. Hardware Event Chain

NEXSUS Fabric'te event'ler birbirine bağlanabilir.

Örnek:

```text
ADC Threshold
      │
      ▼
Event
      │
      ▼
DMA
      │
      ▼
Buffer
      │
      ▼
Fabric Processing
      │
      ▼
CAN / Ethernet / USB
```

CPU yalnızca sonuç oluştuğunda haberdar edilir.

---

# 14. Display Architecture

P3–P5 cihazlarında ekran bulunabileceği için display sistemi GPIO üzerinden oluşturulmamalıdır.

Önerilen yapı:

```text
CPU
 │
 ▼
Display Controller
 │
 ├── Frame Buffer
 ├── Timing Generator
 ├── Layer Engine
 ├── DMA
 └── Interface Controller
          │
          ▼
       Display
```

Burada önemli mimari karar:

> **P3–P5 için Display Controller mümkünse ana çipin içinde bulunmalıdır.**

Böylece ekran için ayrı bir CPU veya Fabric kaynaklarının büyük kısmını kullanmak gerekmez.

---

# 15. Harici Display Driver Gerekli mi?

Her durumda gerekli değildir.

Üç farklı durum vardır.

## Durum A — Dahili Display Controller

```text
NEXSUS Chip
   │
   ▼
Display Controller
   │
   ▼
LCD Interface
   │
   ▼
Panel
```

En basit çözüm.

---

## Durum B — Dahili Controller + Harici PHY/Bridge

```text
NEXSUS
 │
 ▼
Display Controller
 │
 ▼
Display PHY / Bridge
 │
 ▼
Panel
```

Panel arayüzü özel olduğunda kullanılabilir.

---

## Durum C — Harici Display Controller

```text
NEXSUS
 │
 ▼
High-Speed Interface
 │
 ▼
External Display Controller
 │
 ▼
Panel
```

Bu çözüm ancak gerekli panel arayüzü veya görüntü işleme kapasitesi ana çipte ekonomik değilse tercih edilir.

---

# 16. P1–P5 Display Scaling

Önerilen yapı:

| Model | Display | Touch | Display Controller |
|---|---|---|---|
| P1 | Yok / opsiyonel küçük | Yok | Opsiyonel |
| P2 | Küçük LCD | Yok | Basit |
| P3 | 720p | Evet | Dahili |
| P4 | FHD | Evet | Dahili |
| P5 | FHD | Evet | Gelişmiş |

Buradaki **FHD üst sınırı** özellikle standalone programmable device ailesi için korunur.

Bu cihazların amacı PC yerine geçmek değildir.

---

# 17. Display Controller Görevi

Display Controller'ın görevi yalnızca pixel göndermek değildir.

En azından:

```text
Frame Buffer
Timing
Pixel Format
DMA
Layer Composition
Cursor
VSync
Interrupt
```

yönetebilmelidir.

---

# 18. Frame Buffer

Frame buffer system memory'de veya cihazın yerel memory'sinde bulunabilir.

Örneğin FHD:

\[
1920\times1080
\]

RGB888 için:

\[
1920\times1080\times3
\]

yaklaşık:

\[
6.22\,MB
\]

tek frame'dir.

Double buffering:

\[
\approx12.44\,MB
\]

gerektirir.

Bu nedenle P5'te display için ayrı framebuffer memory veya ayrılmış system memory bölgesi mantıklı olabilir.

---

# 19. Display DMA

Display Controller kendi DMA'sına sahip olmalıdır.

```text
System Memory
     │
     ▼
Display DMA
     │
     ▼
Frame Buffer
     │
     ▼
Display Controller
     │
     ▼
Panel
```

CPU her pixel'i tek tek göndermemelidir.

---

# 20. Display Layer Engine

P4/P5 için basit bir layer compositor düşünülebilir.

Örneğin:

```text
Layer 0 → Background
Layer 1 → Application UI
Layer 2 → Sensor Graph
Layer 3 → Warning / Overlay
```

Display Controller bunları hardware seviyesinde birleştirebilir.

Bu, Fabric'in sürekli pixel compositing yapma yükünü azaltır.

---

# 21. Display Interface

Panel arayüzü için ilk mimari seçenekler:

```text
RGB Parallel
LVDS
MIPI DSI
eDP
```

olarak değerlendirilebilir.

Ancak burada önemli olan:

> Fiziksel panel interface'i henüz kesinleştirilmemiştir.

P3/P4/P5 package ve pin budget hesapları yapıldıktan sonra karar verilmelidir.

---

# 22. Touch Controller

P3 ve üstünde touch desteği bulunabilir.

Touch sistemi:

```text
Touch Panel
     │
     ▼
Touch Controller
     │
     ▼
I²C / SPI
     │
     ▼
NEXSUS
```

şeklinde olabilir.

Burada touch controller'ın analog sensing kısmını ayrı bir dedicated block veya harici IC gerçekleştirebilir.

---

# 23. Display + Touch Veri Akışı

```text
Touch
  │
  ▼
Touch Controller
  │
  ▼
Interrupt
  │
  ▼
CPU / Fabric
  │
  ▼
UI State
  │
  ▼
Frame Buffer
  │
  ▼
Display DMA
  │
  ▼
Display Controller
  │
  ▼
LCD
```

Bu yapı UI latency'sini düşük tutar.

---

# 24. Neden Display'i Fabric'e Bırakmıyoruz?

Teorik olarak Fabric üzerinden LCD sürmek mümkündür.

Ancak:

```text
Fabric
 ↓
Pixel Generation
 ↓
Timing
 ↓
DMA
 ↓
Panel
```

şeklinde yapılması Fabric kaynaklarını gereksiz yere tüketebilir.

Display timing deterministik olduğu için özel Display Controller daha verimlidir.

Bu nedenle:

> **Display Controller, Programmable Fabric'in alternatifi değil; Fabric'in özel amaçlı tamamlayıcısıdır.**

---

# 25. Display Controller ile Fabric İlişkisi

Fabric görüntüyü işleyebilir.

Display Controller görüntüyü taşır.

Örneğin:

```text
Sensor
  │
  ▼
ADC
  │
  ▼
Fabric DSP
  │
  ▼
Graph Data
  │
  ▼
Frame Composer
  │
  ▼
Frame Buffer
  │
  ▼
Display Controller
  │
  ▼
LCD
```

Bu ayrım mimari olarak daha temizdir.

---

# 26. Display Engine'in P5 Kullanımı

P5 için:

```text
                    ┌──────────────┐
                    │     CPU      │
                    └──────┬───────┘
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
          Fabric        Display       Touch
             │          Controller     Ctrl
             │             │
             ▼             ▼
        Sensor Data     Frame Buffer
             │             │
             └──────┬──────┘
                    ▼
                 Display
```

Bu, cihazın gerçek zamanlı kontrol paneli olarak kullanılmasını mümkün kılar.

---

# 27. Display Controller Kaynakları

İlk hedef:

| Model | Controller | DMA | Layers | Max Resolution |
|---|---|---:|---:|---:|
| P1 | – | – | – | – |
| P2 | Basic | 1 | 1 | küçük LCD |
| P3 | Standard | 1 | 2 | 1280×720 |
| P4 | Advanced | 2 | 3 | 1920×1080 |
| P5 | Advanced+ | 2–4 | 4 | 1920×1080 |

Bu değerler yine **preliminary** olarak kabul edilir.

---

# 28. Peripheral + Display Ortak DMA

Display DMA ile sensor DMA aynı sistem memory bandwidth'ini kullanabilir.

Örneğin:

```text
ADC DMA ──────┐
Sensor DMA ───┤
Network DMA ──┤
Display DMA ──┤
USB DMA ──────┤
               ▼
          DMA Arbiter
               │
               ▼
         Memory Controller
```

Bu nedenle DMA scheduler önemli bir mimari bileşendir.

---

# 29. DMA Priority

İlk öncelik sınıfları:

```text
Priority 0 → Real-time acquisition
Priority 1 → Control / protocol
Priority 2 → Display
Priority 3 → Bulk transfer
Priority 4 → Background
```

Örneğin yüksek hızlı ADC aktarımı display refresh nedeniyle geciktirilmemelidir.

---

# 30. Peripheral Resource Scaling

İlk hedef:

| Resource | P1 | P2 | P3 | P4 | P5 |
|---|---:|---:|---:|---:|---:|
| UART | 2 | 4 | 6 | 8 | 8 |
| SPI | 2 | 4 | 6 | 8 | 8 |
| I²C | 2 | 3 | 4 | 6 | 8 |
| CAN | – | 1 | 2 | 2 | 4 |
| Custom Protocol Engine | 1 | 2 | 4 | 8 | 12 |
| DMA | 2 | 4 | 8 | 12 | 16 |
| Display Controller | – | 1 | 1 | 1 | 1 |
| Touch Interface | – | – | 1 | 1 | 1 |

DMA ve Custom Protocol sayıları sonraki bandwidth analizinde yeniden değerlendirilecektir.

---

# 31. P1–P5 Sistem Karakteri

### P1

```text
Basic Controller
GPIO
ADC
UART/SPI/I²C
Small Fabric
```

### P2

```text
Embedded Device Controller
+
CAN
+
Small Display
+
More Fabric
```

### P3

```text
Advanced Controller
+
720p
+
Touch
+
Ethernet/Wireless
+
Sensor Processing
```

### P4

```text
High Performance Controller
+
FHD
+
Touch
+
High-Speed I/O
+
Advanced Fabric
+
DSP
```

### P5

```text
High-End Programmable Controller
+
FHD
+
Touch
+
High-Speed Network
+
Large Fabric
+
DSP
+
High-Speed Acquisition
+
Expansion
```

---

# 32. PE4 / PE5

PE4 ve PE5'te display controller zorunlu değildir.

Bu kartların ana amacı:

```text
Data Acquisition
DSP
Protocol Processing
Network Processing
Sensor Aggregation
Custom I/O
```

olduğundan display kaynakları isteğe bağlı olabilir.

Ancak aynı Display Controller IP'sinin PE5'e opsiyonel olarak eklenebilmesi mimari olarak mümkün tutulabilir.

---

# 33. Genel Peripheral Architecture

v0.6 sonrasında Fabric çevresindeki yapı:

```text
                         ┌─────────────┐
                         │     CPU     │
                         └──────┬──────┘
                                │
                         Control Interface
                                │
 ┌──────────────────────────────┼──────────────────────────────┐
 │                              │                              │
 ▼                              ▼                              ▼
Fabric                    Peripheral Fabric              Display
 │                              │                              │
 │                  ┌───────────┼────────────┐                 │
 │                  │           │            │                 │
 ▼                 UART        SPI          CAN               DMA
DSP                 I²C        Custom        │                 │
 │                  │           │             │                 ▼
 ▼                  └───────────┴─────────────┘            Frame Buffer
I/O                              │                              │
 │                               ▼                              ▼
 ▼                          I/O Router                       LCD
Sensors
```

---

# 34. Mimari İlke

NEXSUS'ta her işi CPU'ya yüklemek yerine görevler üç sınıfa ayrılır:

### CPU

```text
Configuration
Control
Application Logic
High-Level Decisions
```

### Fabric

```text
Parallel Processing
DSP
Filtering
Protocol Logic
Sensor Processing
Custom Hardware
```

### Dedicated Engines

```text
ADC
DMA
Display
UART
SPI
I²C
CAN
Timers
```

Bu ayrım NEXSUS sisteminin temel performans yaklaşımıdır.

---

# 35. Display Chip Kararı

Bu aşamada mimari karar:

### P1

Display zorunlu değil.

### P2

Basit display için dahili controller.

### P3

Dahili Display Controller.

### P4

Gelişmiş dahili Display Controller.

### P5

Gelişmiş Display Controller + daha yüksek DMA/bandwidth kapasitesi.

### Harici Display Driver

Sadece panelin fiziksel arayüzü veya analog/PHY gereksinimleri ana çipte ekonomik olmadığı durumda kullanılır.

Dolayısıyla:

> **P3–P5 için ayrı bir display CPU/driver chip'i temel mimariye koymak yerine Display Controller Engine'i NEXSUS çipine entegre etmek daha doğru başlangıçtır.**

Harici bridge/PHY ise gerektiğinde eklenebilir.

---

# 36. Sonraki Aşama

v0.6 ile peripheral ve display katmanının mimari çerçevesi oluşturulmuştur.

Bir sonraki aşamada:

1. **Memory Controller**
2. **DMA Arbiter**
3. **Peripheral Bus**
4. **Fabric ↔ Peripheral interconnect**
5. **Display DMA bandwidth**
6. **Ethernet/Wireless DMA**
7. **USB DMA**
8. **Sensor DMA**
9. **Memory bandwidth budget**
10. **P1–P5 toplam veri yolu analizi**

birlikte ele alınmalıdır.

Özellikle burada artık tek tek blokları tanımlamak yerine:

```text
ADC
 ↓
FIFO
 ↓
DMA
 ↓
Interconnect
 ↓
Memory
```

ile

```text
Sensor
 ↓
Fabric
 ↓
Display
```

gibi gerçek veri akışlarının aynı anda çalışması durumunda **bant genişliği ve arbitration** hesabına geçilecektir.
---