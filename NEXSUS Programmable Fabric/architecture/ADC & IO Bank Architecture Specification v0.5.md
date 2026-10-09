# NEXSUS Programmable Fabric
## ADC & I/O Bank Architecture Specification v0.5

**Document Type:** Technical Architecture Specification  
**Status:** Preliminary Architecture  
**Platform:** NEXSUS Programmable Fabric  
**Scope:** P1–P5 / PE4–PE5  
**Version:** 0.5

---

## 1. Amaç

Bu doküman NEXSUS Programmable Fabric'in analog veri toplama ve fiziksel I/O altyapısının temel mimarisini tanımlar.

Özellikle şu kavramlar birbirinden ayrılır:

- fiziksel analog giriş sayısı,
- ADC conversion engine sayısı,
- eşzamanlı örnekleme kapasitesi,
- multiplexed kanal kapasitesi,
- örnekleme hızı,
- ADC FIFO kapasitesi,
- DMA veri aktarımı,
- Fabric işleme kapasitesi.

Bu ayrım önemlidir çünkü:

> **40 analog giriş, 40 kanalın aynı anda örneklendiği anlamına gelmez.**

NEXSUS mimarisinde fiziksel giriş sayısı ile gerçek ADC throughput'u ayrı parametrelerdir.

---

# 2. ADC Genel Mimarisi

Temel veri yolu:

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
ADC Conversion Engine
    │
    ▼
Sample Buffer
    │
    ▼
ADC FIFO
    │
    ▼
Fabric / DMA
    │
    ├──► SRAM
    ├──► System Memory
    ├──► DSP
    └──► Protocol Engine
```

ADC sistemi üç temel seviyeye ayrılır:

### Level 1 — Physical Input

Gerçek analog pin.

### Level 2 — Logical Channel

Fabric tarafından adreslenebilen analog kanal.

### Level 3 — Conversion Engine

Gerçek ADC dönüşümünü gerçekleştiren donanım.

Bu yapı sayesinde çok sayıda fiziksel giriş daha az sayıda ADC conversion engine tarafından paylaşılabilir.

---

# 3. ADC Engine Kavramı

Bir ADC Engine tek bir conversion core olarak kabul edilir.

Her engine aşağıdaki bileşenlerden oluşur:

```text
ADC Engine
├── Input MUX
├── Sample/Hold
├── ADC Core
├── Reference Interface
├── Calibration
├── Result Register
├── Sample FIFO Interface
└── Trigger Interface
```

Bir engine aynı anda yalnızca kendi conversion core kapasitesi kadar dönüşüm gerçekleştirebilir.

Örneğin:

```text
8 ADC Engines
```

şu anlama gelir:

> En fazla 8 analog kanal aynı conversion cycle içerisinde eşzamanlı örneklenebilir.

Bu, sistemde yalnızca 8 analog giriş bulunduğu anlamına gelmez.

---

# 4. P1–P5 ADC Yapısı

İlk mimari hedef aşağıdaki gibidir:

| Model | ADC Engine | Fiziksel Analog Giriş | ADC Resolution | Engine Sample Rate |
|---|---:|---:|---:|---:|
| P1 | 2 | 8 | 12 bit | 500 kS/s |
| P2 | 4 | 16 | 12/16 bit | 1 MS/s |
| P3 | 4 | 24 | 16 bit | 2 MS/s |
| P4 | 6 | 32 | 16 bit | 4 MS/s |
| P5 | 8 | 40 | 16 bit | 8 MS/s |

Bu değerler **nihai silikon özellikleri değildir**.

Bunlar architecture-level hedeflerdir.

Transistör bütçesi, ADC IP seçimi/tasarımı, güç tüketimi, die area, analog routing ve package kısıtları ile yeniden optimize edilecektir.

---

# 5. ADC Engine / Physical Input İlişkisi

Önerilen ilk yapı:

```text
P1

8 Analog Inputs
       │
   ┌───┴───┐
   │       │
  MUX     MUX
   │       │
 ADC0    ADC1
```

Her ADC engine yaklaşık dört fiziksel giriş arasında seçim yapabilir.

P5 için:

```text
40 Analog Inputs
        │
 ┌──────┼──────┐
 │      │      │
MUX    MUX    MUX ...
 │      │      │
ADC0   ADC1   ADC2
 ...
ADC7
```

Burada 40 fiziksel giriş yaklaşık 8 ADC engine tarafından paylaşılır.

Dolayısıyla:

```text
40 Physical Inputs
        ≠
40 Simultaneous ADC Channels
```

Gerçek eşzamanlı kapasite:

```text
8 Channels
```

olacaktır.

---

# 6. ADC Çalışma Modları

NEXSUS ADC sistemi üç temel çalışma modu destekleyecek şekilde tasarlanır.

## 6.1 Single Channel Mode

Tek kanal sürekli örneklenir.

```text
ADC0 → CH0 → CH0 → CH0 → CH0
```

Bu mod yüksek örnekleme hızının gerekli olduğu sensörlerde kullanılır.

Örnek:

```text
ADC0
8 MS/s
16 bit
```

---

## 6.2 Scan / Multiplexed Mode

Bir ADC engine birden fazla fiziksel kanal arasında dolaşır.

```text
CH0
 ↓
CH1
 ↓
CH2
 ↓
CH3
 ↓
CH0
 ↓
...
```

Örneğin 8 MS/s engine ve 4 kanal:

```text
8 MS/s / 4 ≈ 2 MS/s/channel
```

Ancak gerçek değer:

```text
R_channel =
R_engine / N_channels × η
```

olacaktır.

Burada:

- `R_engine` = ADC conversion rate
- `N_channels` = multiplexed channel sayısı
- `η` = settling + switching + acquisition efficiency

Dolayısıyla teorik bölme doğrudan gerçek kanal hızına eşit kabul edilmemelidir.

---

# 7. Simultaneous Sampling Mode

Bazı uygulamalarda multiplexing kabul edilemez.

Örneğin:

- çok kanallı titreşim ölçümü,
- faz karşılaştırması,
- motor/sensör analizi,
- senkron analog ölçüm.

Bu durumda:

```text
ADC0 → CH0
ADC1 → CH1
ADC2 → CH2
ADC3 → CH3
```

şeklinde ayrı conversion engine'ler kullanılır.

P5 için:

```text
8 ADC Engines
      │
      ├── CH0
      ├── CH1
      ├── CH2
      ├── CH3
      ├── CH4
      ├── CH5
      ├── CH6
      └── CH7
```

Böylece 8 kanal eşzamanlı örneklenebilir.

---

# 8. ADC Trigger Sistemi

ADC yalnızca sürekli clock ile çalışmak zorunda değildir.

Trigger kaynakları:

```text
Internal Timer
External Trigger Pin
PWM Event
GPIO Edge
Fabric Event
Protocol Event
Software Trigger
Sensor Hub Trigger
```

olabilir.

Örnek:

```text
External Trigger
       │
       ▼
Trigger Matrix
       │
 ┌─────┼─────┐
 ▼     ▼     ▼
ADC0  ADC1  ADC2
```

Bu yapı özellikle senkron ölçüm sistemleri için önemlidir.

---

# 9. Trigger Matrix

Trigger sistemi merkezi bir Fabric kaynağı olarak tasarlanır.

```text
                 ┌── ADC0
External Trigger ├── ADC1
                 ├── ADC2
                 ├── PWM
                 ├── Capture
                 └── DMA
```

Bir olay birden fazla donanım birimini aynı anda tetikleyebilir.

Örneğin:

```text
Trigger 0
   │
   ├── ADC sampling
   ├── Timestamp
   ├── FIFO capture
   └── DMA transfer
```

Böylece CPU'nun her örnek için müdahale etmesine gerek kalmaz.

---

# 10. ADC Sample FIFO

ADC sonucu doğrudan CPU register'ına gönderilmez.

Temel yapı:

```text
ADC
 │
 ▼
Sample Register
 │
 ▼
ADC FIFO
 │
 ├──► Fabric
 └──► DMA
```

FIFO şu problemleri azaltır:

- CPU latency,
- DMA scheduling jitter,
- Fabric processing delay,
- burst transfer ihtiyacı,
- temporary memory contention.

Her sample metadata ile birlikte tutulabilir.

Örnek:

```text
Sample {
    sensor_id
    channel_id
    timestamp
    value
    status
    sequence
}
```

Ancak minimum hızlı modda metadata her sample ile birlikte taşınmak zorunda değildir.

Bunun yerine:

```text
Data Buffer
Metadata Buffer
```

ayrımı kullanılabilir.

Bu, yüksek ADC throughput için daha verimli olacaktır.

---

# 11. ADC Channel Configuration

Her logical ADC channel için aşağıdaki parametreler tanımlanabilir:

```text
Channel ID
Input Source
Gain
Reference
Resolution
Sample Rate
Acquisition Time
Trigger Source
Threshold
Filter
Calibration
FIFO Destination
DMA Channel
Timestamp Mode
```

Örneğin:

```text
ADC_CH07

Input      = ANALOG_23
Resolution = 16 bit
Rate       = 500 kS/s
Gain       = ×2
Trigger    = TIMER_1
FIFO       = FIFO_3
DMA        = DMA_2
```

---

# 12. Analog Front End

ADC girişinden önce analog sinyal koşullandırma katmanı bulunabilir.

```text
Pin
 │
 ▼
Protection
 │
 ▼
ESD / Clamp
 │
 ▼
Analog MUX
 │
 ▼
PGA / Buffer
 │
 ▼
Sample & Hold
 │
 ▼
ADC
```

P1/P2 için daha basit yapı kullanılabilir.

P4/P5'te daha gelişmiş AFE seçenekleri bulunabilir.

Örneğin:

- programmable gain,
- differential input,
- single-ended input,
- low-pass filtering,
- bias generation,
- reference selection.

---

# 13. Differential ADC Input

P4/P5 seviyesinde bazı ADC kanalları differential çalışabilir.

Örnek:

```text
AIN+
AIN-
 │
 ▼
Differential AFE
 │
 ▼
ADC
```

Bu yapı:

- common-mode noise,
- uzun kablo gürültüsü,
- düşük seviyeli sensör sinyalleri

için avantaj sağlayabilir.

Ancak tüm fiziksel analog pinlerin differential yapılması zorunlu değildir.

Pinler yapılandırılabilir şekilde:

```text
Single Ended
veya
Differential
```

olarak kullanılabilir.

---

# 14. Analog Channel Multiplexer

MUX yalnızca kanal seçimi yapmaz.

MUX kontrol sistemi şu parametreleri de yönetmelidir:

```text
Channel Select
Acquisition Time
Settling Delay
Gain
Reference
Trigger
```

Örneğin:

```text
CH0 → 2 µs acquisition
CH1 → 5 µs acquisition
CH2 → 10 µs acquisition
CH3 → 2 µs acquisition
```

Bu sayede farklı sensör karakteristikleri aynı ADC engine üzerinde çalıştırılabilir.

---

# 15. Digital I/O Bank Architecture

Dijital I/O pinleri 16-pin banklar halinde organize edilir.

Temel yapı:

```text
I/O BANK
├── PIN00
├── PIN01
├── ...
└── PIN15
```

Her bank aşağıdaki kaynaklara bağlanabilir:

```text
GPIO
UART
SPI
I²C
CAN
PWM
Capture
Counter
Interrupt
Fabric
Custom Protocol
```

---

# 16. I/O Bank İç Yapısı

Her pin için:

```text
Physical Pin
     │
 ┌───┴─────────────┐
 │                 │
Input Path      Output Path
 │                 │
Synchronizer    Output Register
 │                 │
 │              Output Driver
 │                 │
 └───────┬─────────┘
         │
     I/O Router
         │
         ▼
       Fabric
```

---

# 17. Pin Multiplexer

Bir pin aynı anda yalnızca uygun bir fonksiyona atanabilir.

Örnek:

```text
PIN04

GPIO
UART0_TX
SPI1_MOSI
PWM3
CUSTOM_IO7
```

Configuration register:

```text
PIN04_FUNCTION = SPI1_MOSI
```

olarak ayarlanabilir.

---

# 18. Bank-Level Protocol Allocation

Bazı protokoller tek bir pin kullanmaz.

Örneğin SPI:

```text
MOSI
MISO
SCLK
CS
```

gerektirir.

Bu nedenle I/O Fabric protokol kaynaklarını pin bazında değil, gerektiğinde **pin group** olarak yönetmelidir.

Örnek:

```text
BANK2

PIN00 → SPI0_SCLK
PIN01 → SPI0_MOSI
PIN02 → SPI0_MISO
PIN03 → SPI0_CS0
```

Aynı bankta kalan pinler GPIO olarak kullanılabilir.

---

# 19. GPIO Hardware Features

GPIO birimleri yalnızca basit input/output olmayacaktır.

Her uygun pin:

```text
Input
Output
Bidirectional
Pull-Up
Pull-Down
Open Drain
Schmitt Input
Interrupt
Edge Detect
Level Detect
Debounce
Capture
Toggle
Counter
```

özelliklerini destekleyebilir.

---

# 20. Hardware Counter

Pulse üreten sensörler için CPU gerektirmeyen counter desteği bulunur.

Örnek:

```text
Sensor Pulse
     │
     ▼
GPIO Capture
     │
     ▼
Hardware Counter
     │
     ▼
Timestamp
     │
     ▼
FIFO / DMA
```

Bu yapı:

- encoder,
- frequency sensor,
- pulse sensor,
- flow sensor,
- event counter

gibi uygulamalarda kullanılabilir.

---

# 21. Digital Capture

GPIO girişleri yalnızca logic state okumak için kullanılmaz.

Edge timestamp alınabilir:

```text
Rising Edge
    │
    ▼
Timestamp Capture
    │
    ▼
FIFO
```

Böylece:

```text
frequency
period
pulse width
duty cycle
event interval
```

donanım seviyesinde hesaplanabilir.

---

# 22. Interrupt Matrix

Interrupt kaynakları merkezi bir matrix üzerinden Fabric/CPU'ya bağlanır.

```text
GPIO
ADC
DMA
UART
SPI
I2C
CAN
Timer
Counter
Capture
Sensor Hub
      │
      ▼
Interrupt Matrix
      │
      ├── CPU
      └── Fabric
```

Bu sayede her fiziksel interrupt'ın doğrudan CPU hattına bağlanması gerekmez.

---

# 23. DMA Architecture

ADC ve yüksek hızlı I/O için DMA temel veri taşıma mekanizmasıdır.

Örnek:

```text
ADC
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

CPU yalnızca:

```text
Configure
Start
Monitor
Process
```

işlerini yapar.

Her sample için CPU müdahalesi gerekmemelidir.

---

# 24. DMA Transfer Modes

En az aşağıdaki modlar hedeflenir:

### Linear

```text
Buffer[0] → Buffer[N]
```

### Circular

```text
Buffer
┌─────────────┐
│             │
└──────▲──────┘
       │
       └──────── repeat
```

### Scatter/Gather

```text
ADC
 │
 ├──► Buffer A
 ├──► Buffer B
 ├──► Buffer C
 └──► Buffer D
```

### Timestamped Stream

```text
Sensor Data
     +
Timestamp
     │
     ▼
DMA Stream
```

---

# 25. ADC Raw Throughput

ADC throughput:

\[
R_{ADC}=N_{simultaneous}\times B_{sample}\times f_{sample}
\]

Burada:

- \(N\) = eşzamanlı ADC engine sayısı
- \(B\) = sample bit sayısı
- \(f\) = sample rate

P5 için:

\[
8\times16\times8\,MS/s
\]

\[
=1024\,Mbit/s
\]

yani:

\[
R_{ADC}=128\,MB/s
\]

ham veri throughput'u elde edilir.

Bu değer metadata ve protocol overhead içermez.

---

# 26. P5 Multiplexed ADC Örneği

P5:

```text
8 ADC engines
40 analog inputs
8 MS/s / engine
```

olduğunda ortalama olarak her engine yaklaşık 5 fiziksel giriş arasında paylaşılabilir.

Teorik olarak:

\[
8\,MS/s / 5 = 1.6\,MS/s
\]

kanal başına düşer.

Fakat gerçek değer:

\[
R_{channel}\approx
\frac{8\,MS/s}{5}\times\eta
\]

olacaktır.

Buradaki `η`, acquisition, MUX switching ve settling kayıplarını temsil eder.

Bu nedenle:

> **1.6 MS/s teorik tarama oranıdır; garanti edilen efektif kanal throughput'u değildir.**

---

# 27. Simultaneous vs Multiplexed

| Mod | Kanal Sayısı | Eşzamanlılık | Kullanım |
|---|---:|---:|---|
| Single | 1 | 1 | yüksek hızlı ölçüm |
| MUX | çoklu | düşük | çok sayıda yavaş sensör |
| Simultaneous | engine sayısı kadar | yüksek | faz/senkron ölçüm |
| Distributed | çok yüksek | hub'a bağlı | binlerce sensör |

Bu ayrım NEXSUS sensor architecture'ın temel prensiplerinden biridir.

---

# 28. Sensor Data Pipeline

ADC veya dijital sensör verisi doğrudan CPU'ya gitmek zorunda değildir.

Önerilen pipeline:

```text
Sensor
  │
  ▼
I/O
  │
  ▼
Acquisition
  │
  ▼
Calibration
  │
  ▼
Filtering
  │
  ▼
Timestamp
  │
  ▼
FIFO
  │
  ▼
Fabric Processing
  │
  ▼
DMA
  │
  ▼
System Memory
```

Örneğin:

```text
ADC
 ↓
Low Pass Filter
 ↓
Threshold
 ↓
Event Detection
 ↓
FIFO
 ↓
DMA
```

CPU yalnızca sonuçlarla ilgilenebilir.

---

# 29. Sensor Hub Entegrasyonu

P1–P5 üzerinde doğrudan binlerce sensör bağlanması hedeflenmez.

Bunun yerine mimari şu şekilde ölçeklenir:

```text
Sensor
   │
   ▼
Sensor Hub
   │
   ▼
Local Aggregator
   │
   ▼
P5 / PE5
   │
   ▼
S.Fabric
   │
   ▼
System Memory
```

Sensor Hub aşağıdakileri gerçekleştirebilir:

- ADC,
- GPIO,
- MUX,
- filtering,
- calibration,
- timestamp,
- local FIFO,
- protocol conversion.

---

# 30. Sensor Hub Seviyeleri

### Level 0 — Direct

```text
Sensor → P5
```

Az sayıda sensör.

### Level 1 — Local Hub

```text
Sensors
  ↓
Hub
  ↓
P5
```

Onlarca sensör.

### Level 2 — Aggregator

```text
Sensors
 ↓
Hubs
 ↓
Aggregator
 ↓
PE5
```

Yüzlerce/binlerce sensör.

### Level 3 — Distributed Fabric

```text
Sensors
 ↓
Hubs
 ↓
Regional Aggregators
 ↓
PE5
 ↓
S.Fabric
 ↓
System Memory
```

Büyük veri toplama sistemleri.

---

# 31. Bin Sensör Örneği

1000 sensörün her biri:

```text
1 kS/s
16 bit
```

üretiyorsa:

\[
1000\times1000\times16
=
16\,Mbit/s
\]

yani yaklaşık:

\[
2\,MB/s
\]

ham veri oluşur.

Bu, uygun aggregation ve packetization ile oldukça yönetilebilir bir veri miktarıdır.

Ancak sensörler:

```text
100 kS/s
16 bit
```

olursa:

\[
1000\times100000\times16
=
1.6\,Gbit/s
\]

ve:

\[
200\,MB/s
\]

ham veri oluşur.

Dolayısıyla:

> Sensör sayısı tek başına sistem kapasitesini belirlemez.

Asıl parametre:

\[
Bandwidth =
N_{sensor}
\times
SampleRate
\times
BitsPerSample
\]

ve buna protocol/metadata overhead eklenmesidir.

---

# 32. Logical Sensor ID

Sensor sisteminde fiziksel GPIO numarası sensor adresi olarak kullanılmamalıdır.

Örneğin:

```text
Physical Pin = GPIO_47
```

yerine:

```text
Sensor ID = TEMP_ZONE_023
```

kullanılabilir.

Fabric/driver katmanı bunu fiziksel kaynağa map eder:

```text
TEMP_ZONE_023
      │
      ▼
Sensor Map
      │
      ▼
Hub 3
      │
      ▼
ADC Channel 5
```

Bu yapı sistemin fiziksel donanımdan bağımsız yönetilmesini sağlar.

---

# 33. I/O Clock Domains

ADC ve dijital I/O aynı clock domain içerisinde olmak zorunda değildir.

Örneğin:

```text
Fabric Clock
Peripheral Clock
ADC Clock
I/O Clock
Timer Clock
Low Power Clock
```

ayrı olabilir.

Clock Domain Crossing için:

```text
Synchronizer
Async FIFO
Handshake
Timestamp Alignment
```

mekanizmaları kullanılmalıdır.

---

# 34. I/O Bank Resource Scaling

İlk hedef:

| Model | Digital I/O | Bank | Analog Input | ADC Engine |
|---|---:|---:|---:|---:|
| P1 | 32 | 2 × 16 | 8 | 2 |
| P2 | 64 | 4 × 16 | 16 | 4 |
| P3 | 96 | 6 × 16 | 24 | 4 |
| P4 | 128 | 8 × 16 | 32 | 6 |
| P5 | 160 | 10 × 16 | 40 | 8 |

Bu tablo şu aşamada **mimari hedef** olarak kabul edilir.

---

# 35. P4/P5 Analog Expansion

P4/P5'te fiziksel analog pin sayısının artırılması tek çözüm değildir.

Ölçekleme seçenekleri:

```text
More ADC Engines
       +
Larger MUX
       +
External ADC
       +
Sensor Hub
       +
PE Expansion
```

Bu nedenle PE4/PE5 mimarisi gelecekte harici yüksek hızlı ADC kartlarını da destekleyebilir.

Örneğin:

```text
External ADC
      │
      ▼
PE5
      │
      ▼
Fabric DSP
      │
      ▼
DMA
```

---

# 36. PE5 High-Speed Acquisition

PE5, P5'in yalnızca daha fazla GPIO'ya sahip versiyonu olarak tasarlanmamalıdır.

PE5'in rolü:

```text
High-Speed Acquisition
+
High-Speed Processing
+
Protocol Processing
+
DMA
+
Fabric Acceleration
```

olmalıdır.

Örnek:

```text
External ADC
      │
      ▼
PE5 I/O
      │
      ▼
FIFO
      │
      ▼
DSP
      │
      ▼
Compression / Filtering
      │
      ▼
DMA
      │
      ▼
S.Fabric
```

Böylece ham verinin tamamının CPU üzerinden geçirilmesi gerekmez.

---

# 37. I/O Bandwidth Budget

Bir cihazın gerçek sensör kapasitesi:

\[
N_{usable}
\leq
min(
I/O,
ADC,
Protocol,
Fabric,
DMA,
Memory,
Expansion
)
\]

olarak değerlendirilmelidir.

Daha genel olarak:

\[
R_{system}
=
\sum_i
R_{sensor,i}
+
R_{protocol}
+
R_{metadata}
\]

ve:

\[
R_{system}
<
R_{bottleneck}
\]

olmalıdır.

Bottleneck şu katmanlardan herhangi biri olabilir:

```text
ADC
MUX
I/O
FIFO
Fabric
DMA
Memory
Expansion Link
Network
```

---

# 38. Tasarım İlkesi

NEXSUS I/O mimarisinde temel yaklaşım:

> **Pin sayısını büyütmek yerine veri yolunu ölçeklendirmek.**

Küçük sistem:

```text
Sensor → P3
```

Orta sistem:

```text
Sensors → Hub → P5
```

Büyük sistem:

```text
Sensors
 ↓
Hubs
 ↓
Aggregators
 ↓
PE5
 ↓
S.Fabric
 ↓
System Memory
```

Bu sayede aynı Fabric mimarisi çok farklı uygulamalara ölçeklenebilir.

---

# 39. Sonraki Mimari Aşama

ADC ve temel I/O bank yapısı tanımlandıktan sonra aşağıdaki katmanlar formalize edilmelidir:

1. GPIO bank elektriksel mimarisi
2. Pin voltage domains
3. Drive strength
4. Slew rate
5. Pull-up / pull-down
6. Analog protection
7. ADC reference architecture
8. ADC resolution modes
9. ADC calibration
10. ADC FIFO depth
11. Trigger Matrix
12. Interrupt Matrix
13. DMA channel architecture
14. UART engine
15. SPI engine
16. I²C engine
17. CAN engine
18. Custom Protocol Engine
19. Sensor Hub interface
20. Sensor Expansion Bus
21. PE4/PE5 high-speed I/O
22. I/O ↔ Fabric routing bandwidth
23. Fabric ↔ DMA bandwidth
24. DMA ↔ memory bandwidth

---

# 40. Mimari Sonuç

v0.5 ile NEXSUS Programmable Fabric'in I/O tarafında üç farklı ölçek netleşmiştir:

```text
                    ┌─────────────────────┐
                    │     System Memory   │
                    └──────────▲──────────┘
                               │
                              DMA
                               │
                    ┌──────────┴──────────┐
                    │        Fabric      │
                    └───────▲─────▲──────┘
                            │     │
                         ADC/I/O  │ PE
                            │     │
                   ┌────────┘     └────────┐
                   │                       │
               Direct I/O              Expansion
                   │                       │
                 Sensor                Sensor Hub
                                           │
                                      Aggregator
                                           │
                                        Sensors
```

Bu mimari ile:

- P1–P2 küçük doğrudan kontrol sistemlerini,
- P3 orta ölçekli sensör ve cihaz arayüzlerini,
- P4–P5 gelişmiş veri toplama ve kontrol sistemlerini,
- PE4–PE5 ise yüksek hızlı genişleme ve yoğun veri işleme sistemlerini

aynı temel Fabric mimarisi altında destekleyebilir.

**Önemli:** Bu aşamadaki ADC hızları, engine sayıları ve I/O sayıları silikon tasarımı için kesin spesifikasyon değildir. Bunlar sonraki güç, alan, bant genişliği ve proses bütçesi hesaplarının başlangıç parametreleridir.
---