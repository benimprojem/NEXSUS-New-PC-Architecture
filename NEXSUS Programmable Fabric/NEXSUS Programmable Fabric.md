# NEXSUS Programmable Fabric

> **Programmable Hardware Fabric for the NEXSUS Computing Platform**

**Project:** NEXSUS  
**Subsystem:** Programmable Computing Fabric  
**Status:** Preliminary Architecture  
**Version:** 0.1

---

## 1. Overview

NEXSUS Programmable Fabric, NEXSUS platformı için geliştirilen **yeniden programlanabilir donanım altyapısıdır**.

Fabric'in amacı yalnızca FPGA benzeri programlanabilir mantık sağlamak değildir.

Sistem;

- programmable logic,
- parallel processing,
- DSP/MAC,
- FIFO,
- local memory,
- DMA,
- programmable I/O,
- sensor interfaces,
- protocol processing,
- hardware acceleration

gibi kaynakları tek bir programlanabilir mimaride birleştirir.

Temel amaç:

> **Bir NEXSUS sisteminin donanımını belirli bir uygulamaya göre yeniden yapılandırılabilir hale getirmek.**

---

# 2. Fabric Concept

Geleneksel bir sistemde işlem akışı büyük ölçüde CPU tarafından yürütülür:

```text
Input
  │
  ▼
CPU
  │
  ├── Process
  ├── Calculate
  ├── Transfer
  └── Output
```

NEXSUS Fabric yaklaşımında veri işlemenin önemli bölümü donanım seviyesinde gerçekleştirilebilir:

```text
Input
  │
  ▼
Fabric
  │
  ├── Filter
  ├── DSP
  ├── FFT
  ├── Threshold
  ├── FIFO
  └── DMA
       │
       ▼
    Memory
```

CPU bu durumda her veri parçasını tek tek işlemek yerine sistemi yönetebilir.

---

# 3. Fabric as a Dataflow System

Fabric'in temel çalışma modeli **dataflow-oriented hardware** yaklaşımıdır.

Örneğin:

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
DMA
 │
 ▼
System Memory
```

Bu pipeline fabric içerisinde doğrudan donanım bağlantılarıyla oluşturulabilir.

CPU yalnızca:

```text
Configure
Start
Monitor
Stop
```

işlemlerini gerçekleştirebilir.

---

# 4. Architecture

NEXSUS Fabric üç temel routing seviyesine sahiptir:

```text
L0 — Local Routing
      │
      ▼
L1 — Cluster Routing
      │
      ▼
L2 — Global Routing
```

### L0 — Local Routing

Logic Tile içerisindeki bağlantılar.

### L1 — Cluster Routing

Logic Tile'lar ve cluster kaynakları arasındaki bağlantılar.

### L2 — Global Routing

Cluster'lar, memory, DSP, DMA, I/O ve system interface arasındaki bağlantılar.

---

# 5. Logic Fabric

Temel programlanabilir mantık birimi:

```text
Logic Tile
```

olarak tanımlanır.

İlk mimari hedef:

```text
4 × 6-input LUT
8 × Register
Local Routing
Carry Logic
Distributed RAM
Configuration State
```

Logic Tile'lar bir araya gelerek Cluster oluşturur.

```text
16 × Logic Tile
        │
        ▼
     Cluster
```

Cluster'lar ise Global Fabric tarafından birbirine bağlanır.

---

# 6. Fabric Resources

NEXSUS Fabric aşağıdaki temel kaynakları içerir:

### Logic

- LUT
- Flip-Flop
- Carry Logic
- Local RAM

### Processing

- DSP
- MAC
- Accumulator
- Comparator
- Shift/Arithmetic Units

### Memory

- Distributed RAM
- Block RAM
- FIFO
- System Memory Interface

### Data Movement

- DMA
- Fabric Routing
- High-speed Data Paths

### I/O

- GPIO
- UART
- SPI
- I²C
- CAN
- PWM
- ADC
- DAC
- Custom I/O

---

# 7. Programmable I/O

NEXSUS Fabric'in fiziksel I/O kaynakları sabit bir kullanım şekline bağlı değildir.

Bir I/O kaynağı uygulamaya göre:

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

olarak yapılandırılabilir.

Bu sayede aynı chip farklı cihazlarda farklı görevler üstlenebilir.

---

# 8. Sensor Architecture

Fabric yalnızca doğrudan fiziksel sensör bağlantılarıyla sınırlı değildir.

Sensör sistemi üç seviyede ölçeklenebilir:

```text
Direct Sensor I/O
        │
        ▼
Local Sensor Expansion
        │
        ▼
Distributed Sensor Aggregation
```

Bu nedenle:

```text
Physical I/O Count
        ≠
Total Sensor Capacity
```

olur.

Özellikle P4/P5 ve PE4/PE5 sistemlerinde sensor hub, multiplexer, serial expansion ve distributed aggregation kullanılarak çok sayıda sensör yönetilebilir.

Binlerce sensör içeren sistemlerde temel yapı:

```text
Sensors
   │
   ▼
Sensor Hubs
   │
   ▼
Aggregators
   │
   ▼
PE4 / PE5
   │
   ▼
S.Fabric
   │
   ▼
System Memory
```

şeklinde ölçeklenebilir.

---

# 9. Configuration

Fabric'in çalışma yapısı configuration image tarafından belirlenir.

Configuration aşağıdaki kaynakları kontrol edebilir:

```text
LUT
Routing
Registers
DSP
FIFO
BRAM
I/O
Clock
DMA
Interrupts
```

Böylece aynı fiziksel chip farklı uygulamalara göre yeniden yapılandırılabilir.

Örnek:

```text
Configuration A
    │
    └── ADC + Filter + FFT

Configuration B
    │
    └── Protocol Converter

Configuration C
    │
    └── Sensor Controller
```

---

# 10. Partial Reconfiguration

P4/P5 ve PE4/PE5 seviyelerinde partial reconfiguration desteklenmesi hedeflenmektedir.

Fabric'in bir bölümü yeniden yapılandırılırken diğer bölümler çalışmaya devam edebilir.

```text
┌─────────────────────────────┐
│ Static Fabric               │
│                             │
│ ┌─────────────────────────┐ │
│ │ Reconfigurable Region   │ │
│ └─────────────────────────┘ │
│                             │
│ Static Fabric               │
└─────────────────────────────┘
```

Bu özellik özellikle uzun süre çalışan ölçüm ve kontrol sistemlerinde önemlidir.

---

# 11. CPU Integration

Fabric, NEXSUS CPU'nun yardımcı bir işlem birimi olarak kullanılabilir.

```text
              NEXSUS CPU
                   │
                   ▼
             Fabric Control
                   │
          ┌────────┴────────┐
          ▼                 ▼
   Configuration          Data
          │                 │
          ▼                 ▼
       Fabric             DMA
                              │
                              ▼
                           Memory
```

CPU'nun fabric üzerinden geçen bütün veriyi tek tek işlemesi gerekmez.

---

# 12. System Memory

Fabric doğrudan DMA kullanarak system memory ile veri alışverişi yapabilir.

Örnek:

```text
ADC
 │
 ▼
Fabric
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

Bu yaklaşım özellikle yüksek hızlı veri toplama sistemlerinde CPU yükünü azaltır.

---

# 13. P-Series

P-Series bağımsız kullanılabilen programlanabilir NEXSUS cihazlarını temsil eder.

| Model | Genel sınıf |
|---|---|
| P1 | Basic Programmable Controller |
| P2 | Device Interface Controller |
| P3 | Advanced Controller |
| P4 | High Performance Controller |
| P5 | High-End Programmable Controller |

P-Series cihazları:

- ölçüm sistemleri,
- sensör sistemleri,
- veri toplama,
- cihaz arayüzleri,
- protokol dönüştürme,
- otomasyon,
- laboratuvar cihazları,
- yardımcı kontrol sistemleri

gibi uygulamalarda kullanılabilir.

---

# 14. PE-Series

PE-Series, NEXSUS Programmable Fabric'in expansion-card / system-expansion varyantıdır.

```text
P-Series
    │
    └── Standalone Devices

PE-Series
    │
    └── NEXSUS System Expansion
```

İlk hedef modeller:

```text
PE4
PE5
```

PE4/PE5 doğrudan NEXSUS anakartındaki **S.Fabric** ile haberleşebilir.

```text
NEXSUS CPU
     │
     ▼
  S.Fabric
     │
 ┌───┴────┐
 ▼        ▼
PE4      PE5
```

Bu yapı sayesinde Programmable Fabric yalnızca bağımsız cihazlarda değil, NEXSUS PC sistemlerinde de kullanılabilir.

---

# 15. PE4 / PE5 Usage

PE kartları klasik bir ekran kartı veya genel amaçlı PC expansion card olmak zorunda değildir.

Örnek kullanım alanları:

```text
High-Speed Data Acquisition
DSP Acceleration
Sensor Aggregation
Protocol Conversion
Custom I/O
Network Processing
Hardware Acceleration
Scientific Instrumentation
```

Örneğin:

```text
1000 Sensors
     │
     ▼
Sensor Hubs
     │
     ▼
PE5
     │
     ▼
S.Fabric
     │
     ▼
NEXSUS System Memory
```

şeklinde bir sistem oluşturulabilir.

---

# 16. NEXSUS Flow Integration

NEXSUS Programmable Fabric, NEXSUS Flow ve OCC compiler ile birlikte çalışacak şekilde tasarlanır.

Örneğin:

```text
target = "nexsus_p5"
```

veya:

```text
target = "nexsus_pe5"
```

gibi bir hedef tanımı kullanılabilir.

OCC'nin uzun vadeli hedefi:

```text
Source Code
     │
     ▼
     OCC
     │
 ┌───┴────────────┐
 ▼                ▼
CPU Code      Fabric Configuration
```

üretebilmektir.

Böylece compiler yalnızca CPU kodu üretmez.

Sistemin:

- CPU,
- Fabric,
- DSP,
- DMA,
- I/O

kaynaklarını birlikte planlayabilir.

---

# 17. Hardware Acceleration

Bir algoritmanın uygun bölümleri fabric'e aktarılabilir.

Örneğin:

```text
Application
     │
     ▼
NEXSUS CPU
     │
     ├── Control
     │
     └── Heavy Processing
             │
             ▼
           Fabric
```

Bu yapı sayesinde aynı program mantığı korunurken kritik veri işleme bölümleri donanıma taşınabilir.

---

# 18. Scalability

Fabric mimarisinin önemli tasarım hedeflerinden biri ölçeklenebilirliktir.

```text
P1
 │
 ▼
P2
 │
 ▼
P3
 │
 ▼
P4
 │
 ▼
P5
 │
 ├──────────► PE4
 │
 └──────────► PE5
```

Kaynak miktarı arttıkça temel fabric modeli değişmemelidir.

Değişen temel unsurlar:

- Logic Tile sayısı
- Cluster sayısı
- DSP sayısı
- BRAM
- FIFO
- I/O
- DMA
- routing capacity
- memory bandwidth
- external link bandwidth

olmalıdır.

---

# 19. Preliminary Resource Scaling

İlk mimari hedefler:

| Resource | P1 | P2 | P3 | P4 | P5 |
|---|---:|---:|---:|---:|---:|
| Logic Tiles | 256 | 1,024 | 4,096 | 12,288 | 32,768 |
| 6-LUT | 1,024 | 4,096 | 16,384 | 49,152 | 131,072 |
| Flip-Flops | 2,048 | 8,192 | 32,768 | 98,304 | 262,144 |
| DSP/MAC | 16 | 64 | 256 | 512 | 1,024 |
| Block RAM | 256 KB | 1 MB | 4 MB | 8 MB | 16 MB |
| FIFO Resources | 16 | 64 | 256 | 512 | 1,024 |

Bu değerler **nihai chip spesifikasyonları değildir**.

Transistor bütçesi, process node, die area, routing density, power, package ve üretim sonuçlarına göre yeniden optimize edilecektir.

---

# 20. Design Philosophy

NEXSUS Programmable Fabric'in temel tasarım prensipleri:

### 1. CPU Independence

Fabric mümkün olduğunca CPU'dan bağımsız veri işleyebilmelidir.

### 2. Dataflow

Veri mümkün olduğunca doğrudan hardware pipeline üzerinden taşınmalıdır.

### 3. Locality

İşlem ve veri birbirine yakın tutulmalıdır.

### 4. Hierarchical Routing

Routing küçük yerel bağlantılardan global bağlantılara doğru hiyerarşik olmalıdır.

### 5. Reconfigurability

Aynı fiziksel hardware farklı uygulamalar için yeniden yapılandırılabilmelidir.

### 6. Scalability

Aynı mimari P1'den PE5'e kadar ölçeklenebilmelidir.

### 7. Programmable I/O

I/O kaynakları belirli bir protokole kalıcı olarak bağlı olmamalıdır.

### 8. Hardware/Software Co-Design

CPU ve Fabric birlikte programlanabilir bir sistem oluşturmalıdır.

---

# 21. Current Architecture Layers

NEXSUS Programmable Fabric geliştirme sırası:

```text
┌───────────────────────────────┐
│ NEXSUS Flow / OCC             │
├───────────────────────────────┤
│ Configuration / Reconfiguration│
├───────────────────────────────┤
│ Fabric Control                │
├───────────────────────────────┤
│ Global Routing / Fabric NoC   │
├───────────────────────────────┤
│ Cluster Routing               │
├───────────────────────────────┤
│ Logic Tile                    │
├───────────────────────────────┤
│ DSP / BRAM / FIFO / DMA       │
├───────────────────────────────┤
│ Programmable I/O              │
├───────────────────────────────┤
│ Physical Implementation       │
└───────────────────────────────┘
```

---

# 22. Development Roadmap

Fabric mimarisinin sonraki teknik aşamaları:

### Phase 1 — Core Fabric

- Logic Tile
- LUT
- Register
- Local Routing
- Cluster

### Phase 2 — Routing

- Routing Switch
- Cluster Router
- Global Router
- Fabric NoC

### Phase 3 — Processing

- DSP/MAC
- BRAM
- FIFO
- DMA

### Phase 4 — I/O

- GPIO
- ADC
- DAC
- UART
- SPI
- I²C
- CAN
- Custom I/O

### Phase 5 — Sensor Architecture

- ADC multiplexing
- Sensor Hub
- Sensor Expansion
- Sensor Aggregation
- Timestamping
- Distributed Sensor Network

### Phase 6 — System Integration

- CPU ↔ Fabric
- Fabric ↔ System Memory
- Fabric ↔ S.Fabric
- PE4 / PE5

### Phase 7 — Compiler

- OCC Fabric Mapping
- Resource Allocation
- Routing Generation
- Configuration Image Generation
- CPU + Fabric Co-compilation

---

# 23. Current Status

NEXSUS Programmable Fabric şu anda **architecture-stage** bir projedir.

Henüz:

- transistor-level implementation,
- final routing topology,
- final process node,
- final die size,
- final I/O count,
- final sensor capacity,
- final bandwidth,
- final power consumption

belirlenmiş değildir.

Bu parametreler mimari blokların ayrıntılı tasarımı ve fiziksel fizibilite çalışmaları sonrasında belirlenecektir.

---

# 24. Long-Term Goal

NEXSUS Programmable Fabric'in uzun vadeli amacı yalnızca FPGA benzeri bir programmable logic birimi oluşturmak değildir.

Hedef:

> **CPU, programmable hardware, DSP, memory, DMA ve I/O kaynaklarını tek bir programlanabilir sistem mimarisinde birleştirmek.**

Bu mimari sayesinde aynı temel hardware:

```text
Measurement Controller
Sensor Processor
Protocol Converter
Data Acquisition System
DSP Accelerator
Automation Controller
Scientific Instrument Interface
NEXSUS Expansion Card
```

gibi farklı sistemlere dönüştürülebilir.

---

## 25. Repository Structure

Önerilen repository yapısı:

```text
NEXSUS-Programmable-Fabric/
│
├── README.md
│
├── docs/
│   ├── architecture/
│   │   ├── fabric.md
│   │   ├── routing.md
│   │   ├── logic-tile.md
│   │   ├── cluster-router.md
│   │   ├── global-router.md
│   │   ├── fabric-noc.md
│   │   ├── dsp.md
│   │   ├── memory.md
│   │   ├── fifo.md
│   │   ├── dma.md
│   │   └── io-fabric.md
│   │
│   ├── sensors/
│   │   ├── sensor-architecture.md
│   │   ├── sensor-hub.md
│   │   └── sensor-expansion.md
│   │
│   ├── expansion/
│   │   ├── pe4.md
│   │   └── pe5.md
│   │
│   └── compiler/
│       └── occ-fabric-mapping.md
│
└── diagrams/
    ├── fabric-overview.svg
    ├── routing.svg
    ├── sensor-architecture.svg
    └── pe-architecture.svg
```

---

## 26. Summary

NEXSUS Programmable Fabric:

```text
Programmable Logic
        +
DSP
        +
Memory
        +
FIFO
        +
DMA
        +
Programmable I/O
        +
Sensor Processing
        +
Hardware Routing
        +
NEXSUS CPU
        +
S.Fabric
```

bileşenlerini tek bir ölçeklenebilir mimaride birleştirir.

P1–P5 bağımsız cihazlar için,

PE4–PE5 ise NEXSUS PC ve diğer sistemler için

aynı temel fabric mimarisini kullanır.

Mimarinin ana hedefi:

> **Aynı programmable hardware altyapısını küçük bir cihazdan yüksek performanslı NEXSUS expansion sistemine kadar ölçekleyebilmek.**
---
