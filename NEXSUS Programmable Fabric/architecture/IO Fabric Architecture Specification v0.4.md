# NEXSUS Programmable Fabric
## I/O Fabric Architecture Specification v0.4

**Project:** NEXSUS  
**Subsystem:** Programmable Computing Fabric  
**Document Type:** I/O Architecture  
**Status:** Preliminary Architecture Specification  
**Previous Revision:** v0.3  
**Target:** P1–P5 / PE4–PE5

---

# 1. I/O Fabric Overview

NEXSUS Fabric I/O sistemi, fiziksel chip pinleri ile fabric kaynakları arasında programlanabilir bir katman oluşturur.

Temel yapı:

```text
Physical Pin
     │
     ▼
I/O Pad
     │
     ▼
I/O Bank
     │
     ▼
I/O Controller
     │
     ├── GPIO
     ├── UART
     ├── SPI
     ├── I²C
     ├── CAN
     ├── PWM
     ├── Trigger
     └── Custom I/O
             │
             ▼
          Fabric
```

Analog tarafta ise ayrı bir acquisition path bulunur:

```text
Analog Pin
    │
    ▼
Analog Front-End
    │
    ▼
MUX
    │
    ▼
ADC
    │
    ▼
Sample FIFO
    │
    ▼
Fabric
```

Bu yapı sayesinde fiziksel pin ile fabric fonksiyonu birbirinden ayrılır.

---

# 2. Physical I/O ve Logical I/O

NEXSUS sisteminde iki farklı I/O kapasitesi tanımlanır.

## Physical I/O

Chip üzerinde gerçekten bulunan fiziksel pinlerdir.

Örneğin:

```text
P5
 ├── 40 Analog Pins
 └── 160 Digital-capable Pins
```

## Logical I/O

Fabric'in aynı fiziksel interface üzerinden yönetebildiği mantıksal kanallardır.

Örneğin:

```text
16 Sensors
      │
      ▼
 Analog MUX
      │
      ▼
    ADC
```

Burada:

```text
Physical Analog Input = 1
Logical Sensor Channels = 16
```

olabilir.

Dolayısıyla:

> **Physical I/O count sistemin toplam I/O kapasitesini tek başına belirlemez.**

---

# 3. I/O Bank Architecture

Digital I/O pinleri banklara ayrılır.

Önerilen temel yapı:

```text
              I/O Fabric
                  │
      ┌───────────┼───────────┐
      │           │           │
   Bank 0       Bank 1      Bank N
      │           │           │
   GPIO...      GPIO...     GPIO...
```

Her bank kendi içinde:

- input,
- output,
- bidirectional,
- pull-up,
- pull-down,
- interrupt,
- edge detection,
- protocol routing

kaynaklarına sahip olabilir.

---

# 4. I/O Bank Independence

Bankların mümkün olduğunca bağımsız çalışması hedeflenir.

Örneğin:

```text
Bank 0 → GPIO
Bank 1 → SPI
Bank 2 → UART
Bank 3 → PWM
Bank 4 → Custom Sensor Bus
```

şeklinde aynı anda farklı görevler gerçekleştirilebilir.

Bu yapı özellikle P4/P5 için önemlidir.

---

# 5. I/O Bank Width

İlk mimari hedef olarak bank genişlikleri model büyüklüğüne göre ölçeklenebilir.

Önerilen başlangıç:

| Model | Digital I/O | Önerilen Bank Yapısı |
|---|---:|---|
| P1 | 32 | 2 × 16 |
| P2 | 64 | 4 × 16 |
| P3 | 96 | 6 × 16 |
| P4 | 128 | 8 × 16 |
| P5 | 160 | 10 × 16 |

Bu değerler **architecture targets** olarak kabul edilir.

Fiziksel package tasarımı sonrasında bank genişliği 8/16/32 gibi farklı değerlere dönüştürülebilir.

---

# 6. I/O Pin Multiplexing

Her digital-capable pin birden fazla fonksiyon arasında seçilebilir.

Örneğin:

```text
Pin 23
 │
 ├── GPIO
 ├── UART_TX
 ├── SPI_MOSI
 ├── PWM
 ├── Trigger
 └── Custom I/O
```

Configuration memory hangi fonksiyonun aktif olduğunu belirler.

---

# 7. I/O Ownership

Bir fiziksel pin aynı anda yalnızca bir primary function tarafından sürülmelidir.

Örneğin:

```text
GPIO ─────┐
UART ─────┤
SPI ──────┼──► Pin MUX ───► Physical Pin
PWM ──────┤
Custom ───┘
```

Ancak input tarafında aynı sinyalin birden fazla fabric kaynağı tarafından izlenmesi mümkün olabilir.

Örneğin:

```text
Physical Input
      │
      ├──► Interrupt
      ├──► Counter
      └──► Fabric Logic
```

---

# 8. Digital Input Path

Digital input için temel yol:

```text
Physical Pin
     │
     ▼
Input Buffer
     │
     ▼
Synchronizer
     │
     ▼
Input Router
     │
     ├── GPIO
     ├── Interrupt
     ├── Counter
     ├── Capture
     └── Fabric
```

Asenkron dış sinyaller için synchronizer kullanılması gerekir.

Yüksek hızlı interface'lerde ise özel clock/data recovery veya source-synchronous input yapıları gerekebilir.

---

# 9. Digital Output Path

Output yolu:

```text
Fabric
   │
   ▼
Output Router
   │
   ▼
Output Register
   │
   ▼
Output Driver
   │
   ▼
Physical Pin
```

Output register kullanılması:

- timing,
- glitch reduction,
- deterministic output,
- clock-domain control

açısından önemlidir.

---

# 10. GPIO Features

GPIO controller aşağıdaki temel özellikleri destekleyebilir:

- input
- output
- bidirectional
- pull-up
- pull-down
- open-drain
- interrupt
- rising-edge detect
- falling-edge detect
- both-edge detect
- programmable debounce
- input capture
- output toggle

Özellikle sensor ve automation uygulamalarında input capture önemlidir.

---

# 11. Hardware Counter

Bazı dijital sensörler doğrudan frekans veya pulse üretir.

Bu nedenle GPIO input'ları fabric içerisinde hardware counter'a bağlanabilir.

```text
Sensor
  │
  ▼
GPIO
  │
  ▼
Pulse Counter
  │
  ▼
Timestamp
  │
  ▼
FIFO
```

CPU'nun her pulse'u işlemesi gerekmez.

---

# 12. Trigger System

I/O Fabric içerisinde ortak trigger network bulunması önerilir.

Örneğin:

```text
External Trigger
       │
       ├──► ADC
       ├──► Capture
       ├──► Timer
       ├──► GPIO
       └──► Fabric Pipeline
```

Bu yapı ölçüm sistemlerinde deterministic acquisition sağlar.

---

# 13. Analog Input Architecture

Analog girişler digital I/O'dan farklı bir acquisition subsystem üzerinden yönetilir.

```text
Analog Pin
    │
    ▼
Input Protection
    │
    ▼
Analog Front End
    │
    ▼
Channel MUX
    │
    ▼
ADC
    │
    ▼
Sample Buffer
    │
    ▼
Fabric
```

ADC mimarisi daha sonra ayrı bir analog specification içerisinde detaylandırılacaktır.

---

# 14. ADC Engine

Bir ADC engine aşağıdaki bloklardan oluşabilir:

```text
             ADC Engine
                 │
        ┌────────┴────────┐
        ▼                 ▼
    Channel MUX      Reference
        │                 │
        ▼                 │
     ADC Core ◄───────────┘
        │
        ▼
    Sample Buffer
```

ADC engine:

- resolution,
- sample rate,
- input mode,
- channel selection,
- trigger,
- averaging,
- calibration

parametrelerini kontrol edebilir.

---

# 15. Analog Multiplexing

Çok sayıda düşük/orta hızlı analog sensör için MUX kullanımı mümkündür.

Örnek:

```text
A0 ─┐
A1 ─┤
A2 ─┤
A3 ─┤
A4 ─┤
A5 ─┤
A6 ─┤
A7 ─┘
     │
     ▼
   8:1 MUX
     │
     ▼
    ADC
```

Bu durumda:

```text
8 Logical Channels
        ↓
1 ADC
```

olur.

Ancak tüm kanallar aynı anda örneklenmez.

---

# 16. Simultaneous Sampling

Yüksek hızlı veya faz ilişkisi önemli ölçümlerde multiplexed ADC yerine bağımsız ADC engine kullanılmalıdır.

Örneğin:

```text
Sensor A ─► ADC 0 ─┐
Sensor B ─► ADC 1 ─┤
Sensor C ─► ADC 2 ─┼──► Fabric
Sensor D ─► ADC 3 ─┤
Sensor E ─► ADC 4 ─┘
```

Bu yapı:

- synchronous sampling,
- phase comparison,
- waveform acquisition,
- multi-channel DSP

uygulamalarında kullanılabilir.

---

# 17. ADC Operating Modes

ADC subsystem için en az üç çalışma modu öngörülmektedir.

### Single Channel

```text
ADC → Channel 0
```

### Multiplexed

```text
ADC
 ├── CH0
 ├── CH1
 ├── CH2
 └── CH3
```

### Parallel

```text
ADC 0 → CH0
ADC 1 → CH1
ADC 2 → CH2
ADC 3 → CH3
```

Mode seçimi model ve uygulamaya göre değişebilir.

---

# 18. ADC Sample FIFO

ADC ile fabric arasında FIFO bulunması önerilir.

```text
ADC
 │
 ▼
Sample FIFO
 │
 ▼
Fabric
```

FIFO şu sorunları azaltır:

- clock-domain crossing,
- burst data,
- temporary fabric congestion,
- DMA latency.

---

# 19. DAC Architecture

DAC çıkışları da fabric tarafından kontrol edilebilir.

```text
Fabric
 │
 ▼
DAC FIFO
 │
 ▼
DAC
 │
 ▼
Analog Output
```

DAC kullanım alanları:

- waveform generation,
- control signal,
- calibration,
- analog stimulus,
- test signal.

---

# 20. Serial I/O

NEXSUS Fabric aşağıdaki serial interface kaynaklarını desteklemeyi hedefler:

```text
UART
SPI
I²C
CAN
```

P3/P4/P5 seviyelerinde interface sayısı artırılabilir.

Her serial interface fabric'e doğrudan bağlanabilir.

```text
Serial Interface
       │
       ▼
Protocol Engine
       │
       ▼
FIFO
       │
       ▼
Fabric
```

---

# 21. Custom Protocol Engine

NEXSUS Fabric'in önemli özelliklerinden biri programmable protocol engine'dir.

Bir interface:

```text
Physical I/O
      │
      ▼
Programmable State Machine
      │
      ▼
FIFO
      │
      ▼
Fabric
```

şeklinde yapılandırılabilir.

Böylece standart protokoller dışında cihaz üreticisine özel protokoller de desteklenebilir.

---

# 22. Sensor Interface Model

Sensörler için doğrudan:

```text
Sensor
  │
  ▼
I/O Controller
  │
  ▼
Fabric
```

veya genişletilmiş:

```text
Sensors
   │
   ▼
Sensor Hub
   │
   ▼
Serial Link
   │
   ▼
I/O Controller
   │
   ▼
Fabric
```

modelleri kullanılabilir.

---

# 23. Sensor Aggregation

Çok sayıda sensör için:

```text
Sensor
   ↓
Local Acquisition
   ↓
Filtering
   ↓
Calibration
   ↓
Timestamp
   ↓
FIFO
   ↓
Aggregation
   ↓
DMA
```

pipeline'ı desteklenir.

Bu sayede fiziksel pin sayısı sistemin toplam sensor kapasitesini doğrudan belirlemez.

---

# 24. Distributed Sensor Expansion

P4/P5 ve PE4/PE5 için sensor expansion:

```text
                  P5 / PE5
                     │
          Sensor Expansion Link
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
        Hub 0      Hub 1      Hub 2
          │          │          │
       Sensors    Sensors    Sensors
```

şeklinde kurulabilir.

Sensor Hub'ın kendisi:

- basit I/O expander,
- ADC controller,
- küçük programmable controller,
- NEXSUS programmable node

olabilir.

---

# 25. Sensor Data Model

Fabric içerisinde sensör verisi yalnızca bir integer olarak taşınmamalıdır.

Önerilen logical record:

```text
+----------------+
| Sensor ID      |
+----------------+
| Timestamp      |
+----------------+
| Channel        |
+----------------+
| Value           |
+----------------+
| Status          |
+----------------+
| Sequence        |
+----------------+
```

Bu yapı distributed sensor systems için kullanılabilir.

---

# 26. DMA Integration

Yüksek miktarda I/O verisi CPU üzerinden geçirilmemelidir.

Önerilen yol:

```text
Sensor
  │
  ▼
I/O
  │
  ▼
FIFO
  │
  ▼
Fabric
  │
  ▼
DMA
  │
  ▼
System Memory
```

CPU:

```text
Configure
Start
Monitor
Process Metadata
```

gibi görevleri üstlenir.

---

# 27. I/O Clock Domains

I/O kaynaklarının tamamının aynı clock ile çalışması zorunlu değildir.

Örneğin:

```text
Fabric Clock
Peripheral Clock
ADC Clock
SPI Clock
UART Clock
PWM Clock
External Capture Clock
```

ayrı clock domains olabilir.

Clock Domain Crossing noktalarında:

- synchronizer,
- asynchronous FIFO,
- handshake

mekanizmaları kullanılmalıdır.

---

# 28. I/O Resource Scaling

İlk mimari hedefler:

| Resource | P1 | P2 | P3 | P4 | P5 |
|---|---:|---:|---:|---:|---:|
| Digital I/O | 32 | 64 | 96 | 128 | 160 |
| Analog Inputs | 8 | 16 | 24 | 32 | 40 |
| DAC | 2 | 4 | 6 | 8 | 8 |
| ADC Engine | 2 | 4 | 4 | 6 | 8 |
| PWM | 8 | 16 | 24 | 32 | 48 |
| UART | 2 | 4 | 6 | 8 | 8 |
| SPI | 2 | 4 | 6 | 8 | 8 |
| I²C | 2 | 3 | 4 | 6 | 8 |
| CAN | – | 1 | 2 | 2 | 4 |

Bu tablo **başlangıç mimari hedefidir**.

Özellikle ADC channel sayısı ile ADC engine sayısı bundan sonraki tasarımda ayrıca tanımlanacaktır.

---

# 29. PE4 / PE5 I/O Expansion

PE4/PE5'in I/O kapasitesi P5'in yalnızca daha büyük bir versiyonu olarak düşünülmemelidir.

PE ailesinin önemli avantajı:

> **I/O'nun expansion interface üzerinden ölçeklenebilmesidir.**

Örneğin:

```text
PE5
 │
 ├── Local I/O
 │
 ├── Sensor Expansion
 │
 ├── High-Speed Link
 │
 └── External I/O Cards
```

Bu yapı sayesinde özel uygulamalar için farklı I/O kartları bağlanabilir.

---

# 30. I/O Capacity Equation

Toplam sensör kapasitesi:

```text
N_total =
N_direct
+
N_mux
+
N_serial
+
N_hub
+
N_expansion
```

şeklinde düşünülebilir.

Ancak gerçek kullanılabilir kapasite:

```text
N_usable ≤
min(
  I/O capacity,
  ADC throughput,
  protocol bandwidth,
  fabric bandwidth,
  DMA bandwidth,
  memory bandwidth,
  expansion bandwidth
)
```

ile sınırlıdır.

Bu nedenle "maksimum sensör sayısı" tek başına anlamlı bir parametre değildir.

---

# 31. High-Scale Sensor Example

Örnek bir sistem:

```text
1000 Sensors
     │
     ▼
10 Sensor Hubs
     │
     ▼
2 Aggregators
     │
     ▼
PE5
     │
     ▼
DMA
     │
     ▼
System Memory
```

Sensörler lokal olarak:

- örneklenebilir,
- filtrelenebilir,
- kalibre edilebilir,
- timestamp edilebilir,
- paketlenebilir.

PE5 ise merkezi aggregation ve high-speed processing görevini üstlenebilir.

---

# 32. Design Rule

NEXSUS I/O mimarisinin temel tasarım kuralı:

> **Fiziksel pin sayısını artırmak yerine gerektiğinde I/O'yu hiyerarşik olarak ölçeklemek.**

Bunun sonucunda:

```text
Small Device
    │
    ▼
Direct I/O

Medium Device
    │
    ▼
MUX / Serial Expansion

Large Device
    │
    ▼
Sensor Hub

Very Large System
    │
    ▼
Distributed Aggregation
    │
    ▼
PE5 / S.Fabric
```

modeli oluşur.

---

# 33. Next Design Stage

I/O Fabric'in bir sonraki aşamasında aşağıdaki bloklar sayısal olarak tanımlanacaktır:

1. GPIO bank elektriksel yapısı
2. Pin multiplexing
3. ADC engine architecture
4. ADC channel count
5. ADC sampling bandwidth
6. ADC simultaneous sampling
7. Analog MUX architecture
8. DAC architecture
9. Digital I/O timing
10. Interrupt architecture
11. Trigger architecture
12. UART/SPI/I²C/CAN hardware engines
13. Custom protocol engine
14. I/O FIFO architecture
15. DMA channel architecture
16. Sensor Expansion Bus
17. Sensor Hub architecture
18. PE4/PE5 expansion I/O
19. I/O ↔ Fabric routing
20. I/O bandwidth budget

Bu aşamadan sonra P1–P5 ve PE4–PE5 için **gerçek I/O kapasite tabloları** oluşturulabilir.

---

# 34. Architectural Principle

NEXSUS I/O Fabric'in nihai hedefi:

```text
                 Physical I/O
                      │
                      ▼
                  I/O Fabric
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
     Analog        Digital         Serial
       │              │              │
       └──────────────┼──────────────┘
                      ▼
                    FIFO
                      │
                      ▼
                    DMA
                      │
                      ▼
                   Fabric
                      │
                      ▼
                  S.Fabric
                      │
                      ▼
                 System Memory
```

şeklinde ölçeklenebilir, programlanabilir ve CPU'dan mümkün olduğunca bağımsız bir I/O altyapısı oluşturmaktır.
---