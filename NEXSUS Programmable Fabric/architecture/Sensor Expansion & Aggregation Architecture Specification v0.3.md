# NEXSUS Programmable Fabric
## Sensor Expansion & Aggregation Architecture Specification v0.3

**Project:** NEXSUS  
**Subsystem:** Programmable Computing Fabric  
**Document Type:** Technical Architecture  
**Status:** Preliminary Architecture Specification  
**Previous Revision:** v0.2  
**Target:** P1–P5 / PE4–PE5

---

# 1. Physical I/O Count ≠ Sensor Capacity

NEXSUS Fabric mimarisinde fiziksel I/O sayısı ile sistemin destekleyebileceği toplam sensör sayısı birbirinden ayrılmalıdır.

Örneğin:

```text
P5
 │
 ├── 40 Analog Input
 └── 160 Digital GPIO
```

ifadesi:

> P5 yalnızca 40 analog + 160 dijital sensör destekler.

anlamına gelmez.

Bu değerler chip üzerindeki **doğrudan fiziksel I/O kapasitesini** belirtir.

Gerçek sensör kapasitesi:

```text
Direct I/O
+
Multiplexed I/O
+
Serial Sensor Buses
+
Sensor Aggregators
+
External Expansion
+
Networked Sensor Nodes
```

toplamından oluşabilir.

---

# 2. Üç Seviyeli Sensör Mimarisi

NEXSUS sensör bağlantısı üç seviyeye ayrılmalıdır.

```text
Level 0
Direct Sensor I/O

Level 1
Local Sensor Expansion

Level 2
Distributed Sensor Aggregation
```

Bu yapı P4/P5 ve PE4/PE5 modellerinde özellikle önemlidir.

---

# 3. Level 0 — Direct Sensor I/O

Sensör doğrudan chip üzerindeki fiziksel I/O'ya bağlanır.

Örnek:

```text
Sensor
   │
   ▼
P5 ADC
```

veya:

```text
Digital Sensor
      │
      ▼
P5 GPIO
```

Avantajları:

- minimum gecikme,
- doğrudan örnekleme,
- yüksek zamanlama hassasiyeti,
- harici controller gerektirmemesi.

Bu bağlantı tipi özellikle hızlı veya hassas ölçümler için kullanılmalıdır.

---

# 4. Level 1 — Local Sensor Expansion

Birden fazla sensör fiziksel I/O'yu paylaşabilir.

Örneğin analog tarafta:

```text
Sensor 0 ─┐
Sensor 1 ─┤
Sensor 2 ─┤
Sensor 3 ─┤
           ▼
       Analog MUX
           │
           ▼
         ADC
```

Böylece:

```text
4 Sensor
   ↓
1 ADC
```

veya:

```text
16 Sensor
    ↓
1 ADC
```

gibi yapılara izin verilebilir.

Ancak burada önemli bir ayrım vardır:

> Multiplexer kullanımı toplam sensör sayısını artırır fakat eşzamanlı örnekleme kapasitesini artırmaz.

Örneğin 16 sensör tek ADC üzerinden bağlanıyorsa ADC örnekleme zamanı sensörler arasında paylaşılır.

---

# 5. Dijital Sensor Multiplexing

Dijital sensörlerde daha farklı yöntemler kullanılabilir.

Örneğin:

```text
Sensor Array
     │
     ▼
GPIO Expander
     │
     ▼
SPI / I2C
     │
     ▼
P5 Fabric
```

100 sensör:

```text
100 GPIO
```

gerektirmek yerine:

```text
SPI
+
GPIO Expander
```

üzerinden bağlanabilir.

Ancak çok yüksek veri hızına sahip sensörlerde SPI/I2C yerine daha hızlı protokoller kullanılmalıdır.

---

# 6. Serial Sensor Architecture

Sensörlerin kendi dijital interface'i bulunuyorsa chip'in fiziksel GPIO sayısına bağımlılık daha da azalır.

Örneğin:

```text
Sensor 0 ─┐
Sensor 1 ─┤
Sensor 2 ─┤
Sensor 3 ─┤
           ▼
        Sensor Hub
           │
          SPI
           │
           ▼
         P5/PE5
```

Sensor Hub:

- sensörleri yönetir,
- verileri toplar,
- zaman damgası ekler,
- buffer'lar,
- paketler.

P5 yalnızca hub ile haberleşir.

---

# 7. Level 2 — Distributed Sensor Aggregation

Binlerce sensör söz konusu olduğunda tek bir P5 chip'in bütün sensörleri doğrudan yönetmesi hedeflenmemelidir.

Bunun yerine dağıtık aggregation kullanılabilir.

```text
             P5 / PE5
                 │
        ┌────────┼────────┐
        │        │        │
        ▼        ▼        ▼
      Hub 0    Hub 1    Hub 2
        │        │        │
      100 S    100 S    100 S
```

Örneğin:

```text
10 Sensor Hub
×
100 Sensor
=
1000 Sensor
```

olabilir.

P5 bu durumda 1000 fiziksel bağlantıyı doğrudan taşımak zorunda değildir.

---

# 8. Sensor Hub

Sensor Hub ayrı bir ürün olmak zorunda değildir.

Üç farklı şekilde gerçekleştirilebilir:

### A — Basit Expander

```text
GPIO/ADC
+
MUX
+
SPI/I2C
```

### B — Programmable Sensor Node

```text
Small NEXSUS Fabric
+
ADC
+
GPIO
+
FIFO
+
Communication
```

### C — PE Expansion

```text
PE4
 │
 ├── ADC
 ├── GPIO
 ├── DSP
 ├── FIFO
 └── Sensor Interfaces
```

B modeli özellikle karmaşık sensör sistemleri için daha güçlüdür.

---

# 9. Sensor Aggregation Pipeline

Binlerce sensörden gelen verinin doğrudan CPU'ya aktarılması yerine:

```text
Sensor
   │
   ▼
Local Acquisition
   │
   ▼
Filtering
   │
   ▼
Calibration
   │
   ▼
Timestamp
   │
   ▼
FIFO
   │
   ▼
Aggregation
   │
   ▼
DMA
   │
   ▼
System Memory
```

pipeline'ı kullanılabilir.

Böylece CPU:

```text
1000 sensor × individual software handling
```

yapmak yerine:

```text
Sensor Data Stream
```

işleyebilir.

---

# 10. Binlerce Sensörün PC'ye Aktarılması

Burada önemli nokta:

> Binlerce sensör olması, binlerce bağımsız PC bağlantısı gerektiği anlamına gelmez.

Örneğin:

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
S.Fabric
     │
     ▼
System Memory
     │
     ▼
NEXSUS CPU
```

şeklinde tek bir yüksek hızlı veri yolu kullanılabilir.

---

# 11. Data Reduction

Her sensörün ham verisinin sürekli olarak PC'ye gönderilmesi gerekmeyebilir.

Fabric üzerinde:

```text
Raw Data
   │
   ├── Filter
   ├── Average
   ├── Threshold
   ├── FFT
   ├── Compression
   └── Event Detection
```

gerçekleştirilebilir.

Örneğin:

```text
1000 sensors
×
1 ksample/s
×
16 bit
```

ham veri:

```text
16 Mbit/s
```

olur.

Bunun tamamının PC'ye gönderilmesi mümkün olsa da her durumda gerekli değildir.

Örneğin yalnızca değişimleri göndermek:

```text
Sensor
 │
 ▼
Threshold
 │
 └── No Change → discard
 │
 └── Change → transmit
```

şeklinde veri miktarını ciddi biçimde azaltabilir.

---

# 12. Raw Data Mode

Bununla birlikte NEXSUS mimarisi veriyi zorunlu olarak azaltmamalıdır.

Bilimsel ölçüm sistemlerinde ham veri önemlidir.

Bu nedenle en az iki çalışma modu tanımlanabilir:

### Raw Mode

```text
Sensor
 ↓
FIFO
 ↓
DMA
 ↓
Memory
```

### Processed Mode

```text
Sensor
 ↓
DSP / Filter
 ↓
Aggregation
 ↓
DMA
 ↓
Memory
```

Kullanıcı veya OCC uygulaması hangi modun kullanılacağını belirleyebilir.

---

# 13. Timestamp Architecture

Çok sensörlü sistemlerde yalnızca değer taşımak yeterli değildir.

Veriye zaman bilgisi eklenmelidir.

Önerilen veri kaydı:

```text
Sensor ID
Timestamp
Channel
Value
Status
Quality
Sequence
```

Örneğin:

```text
[Sensor: 0234]
[Time: 18273651]
[Channel: 02]
[Value: 1432]
[Status: OK]
```

Bu özellikle farklı Sensor Hub'ların aynı sistemde kullanılması durumunda önemlidir.

---

# 14. Sensor ID

Binlerce sensör için fiziksel GPIO numarası sensör kimliği olarak kullanılmamalıdır.

Bunun yerine logical Sensor ID kullanılmalıdır.

Örneğin:

```text
Sensor ID:
0x0000
0x0001
0x0002
...
0x0FFF
...
```

Böylece sistem:

```text
Physical Port
      ↓
Hub
      ↓
Channel
      ↓
Logical Sensor ID
```

eşlemesi yapabilir.

Bu yaklaşım binlerce hatta daha fazla sensörün tek bir sistem altında yönetilmesini mümkün kılar.

---

# 15. Analog Sensor Architecture

Analog tarafta üç temel bağlantı tipi desteklenebilir.

### Direct ADC

```text
Sensor → ADC
```

### MUX ADC

```text
Sensor × N
     ↓
   MUX
     ↓
    ADC
```

### Distributed ADC

```text
Sensors
   ↓
Local ADC
   ↓
Digital Link
   ↓
P5 / PE5
```

Üçüncü yöntem büyük sistemler için en ölçeklenebilir yöntemdir.

---

# 16. Digital Sensor Architecture

Dijital sensörlerde:

```text
GPIO
UART
SPI
I2C
CAN
Custom Serial
Ethernet
```

gibi bağlantılar kullanılabilir.

P4/P5 fabric'inin programmable I/O yapısı sayesinde ileride yeni sensor protocol'leri de fabric üzerinde uygulanabilir.

---

# 17. Sensor Expansion Bus

İleride NEXSUS için özel bir:

> **Sensor Expansion Bus — SEB**

tanımlanabilir.

Bu aşamada fiziksel protokolün belirlenmesi gerekmemektedir.

Ancak mimari hedef şu olabilir:

```text
                 P5 / PE5
                     │
              Sensor Expansion
                     │
       ┌─────────────┼─────────────┐
       │             │             │
     Hub 0         Hub 1         Hub 2
       │             │             │
    Sensors       Sensors       Sensors
```

SEB'nin fiziksel katmanı:

- elektriksel,
- diferansiyel,
- fiber,
- kablosuz

gibi farklı seçeneklere açık bırakılabilir.

---

# 18. Hierarchical Sensor Network

Çok büyük sistemlerde:

```text
Sensor
   ↓
Sensor Hub
   ↓
Local Aggregator
   ↓
Regional Aggregator
   ↓
PE5
   ↓
S.Fabric
   ↓
System Memory
```

şeklinde hiyerarşik yapı kullanılabilir.

Bu mimari sayesinde tek bir PE5'in fiziksel I/O sayısı sistemin toplam sensor kapasitesini sınırlamaz.

---

# 19. Sensor Capacity Definition

Bu nedenle NEXSUS ürün datasheet'lerinde:

```text
Analog Inputs
Digital Inputs
```

yanında mutlaka:

```text
Maximum Direct Sensors
Maximum Multiplexed Sensors
Maximum Distributed Sensors
Maximum Sensor Data Rate
```

parametreleri ayrı verilmelidir.

Örneğin gelecekte bir PE5 için:

```text
Direct Analog Inputs       : X
Direct Digital Inputs      : Y
Serial Interfaces          : Z
Maximum Aggregated Sensors : TBD
Maximum Input Data Rate    : TBD
```

şeklinde bir tanımlama yapılmalıdır.

**TBD değerleri gerçek fabric, ADC, DMA, memory ve link bant genişliği hesaplarından sonra belirlenmelidir.**

---

# 20. Sensor Count'un Asıl Sınırı

Binlerce sensör sisteminde teorik sınır genellikle GPIO sayısı olmayacaktır.

Asıl sınırlar:

```text
ADC Throughput
Digital Bus Bandwidth
Fabric Processing Capacity
FIFO Capacity
DMA Bandwidth
System Memory Bandwidth
Expansion Link Bandwidth
Power
Synchronization
```

olacaktır.

Bu nedenle:

```text
"PE5 kaç sensör destekliyor?"
```

sorusunun tek bir sayı ile cevaplanması doğru değildir.

Daha doğru tanım:

```text
PE5 Sensor Capacity =
f(
  interface type,
  sample rate,
  resolution,
  protocol,
  aggregation,
  processing,
  total bandwidth
)
```

şeklindedir.

---

# 21. Mimari Sonuç

NEXSUS Fabric'in sensör mimarisi şu hale gelir:

```text
             ┌──────────────────┐
             │     NEXSUS PC    │
             │                  │
             │ CPU + S.Fabric   │
             └────────┬─────────┘
                      │
                    PE5
                      │
             ┌────────┴────────┐
             │                 │
        Aggregator         Aggregator
             │                 │
       ┌─────┼─────┐     ┌─────┼─────┐
       ▼     ▼     ▼     ▼     ▼     ▼
      Hub   Hub   Hub   Hub   Hub   Hub
       │     │     │     │     │     │
      S×N   S×N   S×N   S×N   S×N   S×N
```

Bu yapı ile:

> **P4/P5 ve PE4/PE5, doğrudan sensör bağlama cihazı olmaktan çıkıp büyük ölçekli sensör veri toplama ve işleme platformlarının merkezine dönüşebilir.**

Fakat bunu şimdiden "PE5 = 4096 sensör" gibi sabit bir rakama bağlamak doğru değildir.

Önce:

1. ADC mimarisi
2. ADC channel multiplexing
3. Digital I/O bank yapısı
4. Sensor Expansion Bus
5. DMA
6. FIFO
7. Fabric bandwidth
8. PE5 ↔ S.Fabric link bandwidth
9. System memory bandwidth

belirlenmeli; **maksimum sensör sayısı bundan sonra hesaplanmalıdır.**

---

# 22. Sonraki Mimari Adım

Bu nedenle sıradaki tasarım aşaması artık oldukça net:

## I/O Fabric Architecture

Aşağıdaki blokları ayrıntılı olarak tanımlamak gerekir:

```text
                 NEXSUS FABRIC
                       │
        ┌──────────────┼──────────────┐
        │              │              │
      Digital        Analog        Serial
        I/O            I/O            I/O
        │              │              │
     GPIO Bank       ADC/MUX       UART/SPI/I2C
        │              │              │
        └──────────────┼──────────────┘
                       │
                     FIFO
                       │
                      DMA
                       │
                  System Fabric
```

Bundan sonra **P1 → P5 → PE4 → PE5 için gerçek I/O bank mimarisini** çıkarabiliriz.

Bu noktada artık yalnızca "P5'te 40 ADC var" demek yerine:

- kaç ADC engine,
- kaç ADC channel,
- kaç channel aynı anda örneklenebilir,
- kaç GPIO bank,
- bank başına kaç pin,
- kaç UART/SPI/I²C instance,
- kaç bağımsız sensor bus,
- kaç DMA channel,
- her birinin maksimum veri hızı

gibi değerleri tanımlamaya başlayabiliriz.

Bu da sonunda bize gerçekten **"P5/PE5 aynı anda kaç sensörü, hangi örnekleme hızında, hangi veri genişliğinde taşıyabilir?"** hesabını yapma imkânı verecek.
---