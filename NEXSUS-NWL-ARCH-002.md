# NEXSUS Wireless Link
## Çoklu Kanal, Paralel Radyo ve Dinamik Yönlendirme Mimarisi

**Doküman Kodu:** NEXSUS-NWL-ARCH-002  
**Konu:** Çoklu kablosuz kanal, paralel radyo, ses yönlendirme ve dinamik trafik mimarisi  
**Statü:** Kavramsal Teknik Tasarım

---

# 1. Temel Değişiklik

NWL'de temel birim:

> **Cihaz değil, kanal/akıştır.**

Bir cihaz birden fazla kanal taşıyabilir.

Bir kanal bir cihazdan başka bir cihaza bağlanabilir.

Birden fazla fiziksel radyo aynı anda çalışabilir.

Dolayısıyla:

```text
                NEXSUS WIRELESS DOMAIN

      PHYSICAL RADIOS
      ┌──────┬──────┬──────┬──────┐
      │ RF-0 │ RF-1 │ RF-2 │ RF-3 │
      └──┬───┴──┬───┴──┬───┴──┬───┘
         │      │      │      │
         └──────┴──────┴──────┘
                    │
              CHANNEL FABRIC
                    │
        ┌───────────┼────────────┐
        │           │            │
      AUDIO        HID          DATA
        │           │            │
    8 channels   mouse/key    transfer
```

Buradaki **Channel Fabric**, NWL'nin en önemli yeni katmanlarından biri olmalıdır.

---

# 2. 7.1 Sistem Örneği

Bilgisayara sekiz kablosuz hoparlör bağlandığını düşünelim.

Fiziksel olarak:

```text
             NEXSUS PC
                 │
             NWC / NWL
                 │
       ┌─────────┼─────────┐
       │         │         │
     RF-0      RF-1      RF-2 ...
       │         │
   ┌───┴───┐ ┌───┴───┐
   │       │ │       │
 SPK1    SPK2 SPK3  SPK4
```

Ancak işletim sistemi açısından bunlar:

```text
Speaker 1
Speaker 2
Speaker 3
Speaker 4
Speaker 5
Speaker 6
Speaker 7
Speaker 8
```

olarak ayrı hedeflerdir.

---

# 3. 7.1 Kanal Matrisi

Ses sistemi:

```text
CH0 = Front Left
CH1 = Front Right
CH2 = Center
CH3 = LFE / Subwoofer
CH4 = Surround Left
CH5 = Surround Right
CH6 = Rear Left
CH7 = Rear Right
```

Hoparlörler:

```text
SPK0
SPK1
SPK2
SPK3
SPK4
SPK5
SPK6
SPK7
```

NWL bunları doğrudan eşlemek zorunda değildir.

Bir **routing matrix** bulunur.

```text
              SPEAKERS
          0  1  2  3  4  5  6  7
       ┌─────────────────────────────
 CH0   │ X
 CH1   │    X
 CH2   │       X
 CH3   │          X
 CH4   │             X
 CH5   │                X
 CH6   │                   X
 CH7   │                      X
```

Ama kullanıcı bunu değiştirebilir.

Örneğin:

```text
Front Left → Speaker 6
Front Right → Speaker 2
Center → Speaker 0
LFE → Speaker 7
Surround Left → Speaker 4
Surround Right → Speaker 5
Rear Left → Speaker 1
Rear Right → Speaker 3
```

NWL bunu bir yönlendirme tablosu olarak saklar.

---

# 4. Kullanıcının Görmek İstediği Sistem

NEXSUS işletim sisteminde:

```text
NEXSUS AUDIO ROUTING

Logical Channel       Physical Device

Front Left       →    Speaker 6
Front Right      →    Speaker 2
Center           →    Speaker 0
LFE              →    Speaker 7
Surround Left    →    Speaker 4
Surround Right   →    Speaker 5
Rear Left        →    Speaker 1
Rear Right       →    Speaker 3
```

Burada önemli nokta:

**Ses kanalının hoparlörle fiziksel olarak sabitlenmemiş olmasıdır.**

---

# 5. Aynı Hoparlöre Birden Fazla Kanal

Sistem daha da esnek olabilir.

Örneğin:

```text
Front Left  ──┐
              ├── Speaker 0
Rear Left   ──┘
```

Bu durumda iki kanal aynı fiziksel hedefe gönderilebilir.

NWL'nin mixer/router katmanı bunları:

- ayrı bırakabilir,
- miksleyebilir,
- önceliklendirebilir,
- birini susturabilir.

Bu tamamen yazılım tarafından belirlenebilir.

---

# 6. Bir Kanalın Birden Fazla Hoparlöre Gönderilmesi

Tersi de mümkün olmalıdır.

Örneğin:

```text
Center
  │
  ├──── Speaker 2
  ├──── Speaker 3
  └──── Speaker 6
```

Bu durumda aynı ses akışı üç hoparlörde senkron oynatılabilir.

Bu, mevcut kablosuz teknolojilerdeki synchronized/broadcast audio yaklaşımının daha genel bir kullanım şeklidir. Bluetooth LE Audio örneğin bir kaynaktan birden fazla alıcıya zaman senkronlu ses akışları gönderebiliyor.

---

# 7. Stereo'ya Mahkûm Olmamak

NWL'de stereo özel bir mod değildir.

Stereo yalnızca:

```text
2 Logical Channels
```

demektir.

7.1:

```text
8 Logical Channels
```

5.1:

```text
6 Logical Channels
```

16 kanal:

```text
16 Logical Channels
```

32 kanal:

```text
32 Logical Channels
```

olabilir.

Dolayısıyla ses sistemi:

```text
N = kanal sayısı
M = fiziksel ses cihazı sayısı
```

şeklinde modellenebilir.

Routing:

\[
R_{ij}
\]

ile ifade edilebilir.

Burada:

- \(i\) = mantıksal kanal
- \(j\) = fiziksel hedef

ve:

\[
R_{ij}\in\{0,1\}
\]

temel bağlantıyı belirtir.

Daha gelişmiş durumda katsayı da kullanılabilir:

\[
R_{ij}\in[0,1]
\]

Böylece aynı kanal farklı hoparlörlere farklı seviyelerde gönderilebilir.

---

# 8. Asıl Önemli Nokta: Paralel Radyo

Burada senin ikinci söylediğin nokta daha da önemli.

NWL:

> **tek radyo + zaman paylaşımı yapmak zorunda değildir.**

NWC içerisinde birden fazla bağımsız RF zinciri bulunabilir.

```text
                    NWC
                     │
       ┌─────────────┼─────────────┐
       │             │             │
      RF0           RF1           RF2
       │             │             │
    Audio-A       Audio-B        HID
       │             │             │
    Speaker       Speaker       Mouse
```

Ve aynı anda:

```text
RF0 → Audio
RF1 → Audio
RF2 → Mouse
RF3 → Data
```

çalışabilir.

---

# 9. Böylece Hava Zamanı Paylaşımı Azalır

Tek RF sistemi:

```text
        RF0
         │
 ┌───────┼────────┐
 │       │        │
Audio   Mouse    Data
```

olursa hepsi aynı fiziksel radyo kaynağı üzerinde zaman paylaşır.

Paralel RF:

```text
       ┌── RF0 ── Audio
NWC ───┼── RF1 ── Audio
       ├── RF2 ── Mouse
       └── RF3 ── Data
```

olduğunda fiziksel kaynaklar ayrılabilir.

Bu da NWL'nin gerçek anlamda **parallel wireless fabric** haline gelmesini sağlar.

---

# 10. Radyo ile Kanal Aynı Şey Değildir

Ancak burada önemli bir ayrım yapmalıyız.

```text
Physical Radio
       ↓
Wireless Link
       ↓
Logical Channel
       ↓
Service
```

Örneğin:

```text
RF0
 ├── Speaker 0
 ├── Speaker 1
 └── Speaker 2
```

mümkündür.

Aynı şekilde:

```text
RF1
 ├── Keyboard
 └── Mouse
```

olabilir.

Dolayısıyla:

> **1 cihaz = 1 radyo**

zorunluluğu yoktur.

---

# 11. Dinamik Radio Assignment

NWC, bağlantıları çalışma sırasında farklı radyolara taşıyabilmelidir.

Örneğin başlangıç:

```text
RF0 → Audio
RF1 → Mouse
RF2 → Keyboard
RF3 → Data
```

Dosya transferi büyüdüğünde:

```text
RF0 → Audio
RF1 → Mouse + Keyboard
RF2 → Data
RF3 → Data
```

olabilir.

Burada scheduler, kanal yüküne göre kaynak dağıtabilir.

---

# 12. Data Transfer Örneği

Diyelim kullanıcı 50 GB dosya gönderiyor.

Aynı anda:

- 8 hoparlör aktif
- mouse aktif
- keyboard aktif
- headset microphone aktif

olsun.

NWL'nin hedefi:

```text
                    NWC

        ┌────────────┼─────────────┐
        │            │             │
     AUDIO          HID           DATA
        │            │             │
   8 speakers    mouse/key      phone/SSD
```

olmalıdır.

Data transferi:

**audio'nun zamanlamasını bozmamalıdır.**

Mouse:

**dosya transferi yüzünden gecikmemelidir.**

Keyboard:

**audio trafiğinin altında beklememelidir.**

---

# 13. Trafik Sınıfları

Bunu scheduler'ın temel kuralı haline getirebiliriz.

| Sınıf | Örnek | Gereksinim |
|---|---|---|
| RT-CONTROL | mouse, keyboard | çok düşük gecikme |
| ISO-AUDIO | 7.1 audio | sabit zamanlama |
| ISO-VIDEO | kamera | zamanlama + bant genişliği |
| INTERACTIVE | phone control | düşük gecikme |
| DATA | dosya transferi | yüksek bant genişliği |
| BULK | yedekleme | gecikme toleranslı |
| BACKGROUND | sync | düşük öncelik |

---

# 14. Audio İçin Sabit Zaman Referansı

8 hoparlörün ayrı ayrı kablosuz alıcısı varsa en kritik konu:

**aynı anda çalmalarıdır.**

Aksi durumda:

```text
Speaker 0 → 10.000 ms
Speaker 1 → 10.004 ms
Speaker 2 → 10.011 ms
Speaker 3 → 10.007 ms
```

gibi farklılıklar oluşabilir.

Bu özellikle fiziksel olarak birbirinden uzak hoparlörlerde yankı/bozulma yaratabilir.

Bu yüzden NWL'de ortak bir **Wireless Timebase** bulunmalıdır.

```text
NWC
 │
 └── Master Wireless Clock
          │
     ┌────┼────┬────┐
     ↓    ↓    ↓    ↓
   SPK0 SPK1 SPK2 SPK3
```

Her hoparlör kendi saatine göre “paket geldiğinde çal” dememelidir.

Onun yerine:

> **timestamp = T**

olan ses paketi bütün hedeflerde aynı referans zamana göre oynatılmalıdır.

---

# 15. Audio Packet

Kavramsal olarak:

```text
AUDIO FRAME

Stream ID
Sequence
Timestamp
Channel ID
Payload
Integrity
```

Örneğin:

```text
Stream = GAME_AUDIO_01
Channel = FRONT_LEFT
Sequence = 18421
Timestamp = 82937420
Payload = ...
```

Speaker 6 bu paketi aldığında:

```text
Timestamp = 82937420
```

referansına göre oynatır.

Speaker 2 de aynı timestamp'i kullanır.

---

# 16. Paket Geç Gelirse

Audio'da önemli bir kural:

> **Geç gelen paket her zaman tekrar gönderilmek zorunda değildir.**

Çünkü:

```text
Playback deadline = 20.000 ms
Packet arrival    = 20.030 ms
```

ise artık o paketi 20.030 ms'de çalmak doğru değildir.

Bu nedenle paket:

```text
VALID
   ↓
BUFFER
   ↓
PLAY
```

veya:

```text
EXPIRED
   ↓
DROP
```

olabilir.

Bu yaklaşım zaman bağlı iletişim için mevcut isochronous sistemlerde de kullanılan temel prensiptir.

---

# 17. Hoparlör Alıcısının Yapısı

Sekiz hoparlörün her birinde:

```text
NWL Speaker Receiver
        │
   ┌────┼────┐
   │    │    │
 Radio Clock Decoder
   │         │
   └────┬────┘
        │
       DAC
        │
    Amplifier
        │
     Speaker
```

bulunabilir.

Bu alıcı yalnızca ses verisini almakla kalmaz.

Aynı zamanda:

- timestamp senkronizasyonu
- buffer
- volume
- mute
- device status
- latency compensation
- link quality

gibi bilgileri de yönetebilir.

---

# 18. Hoparlör Konum Bilgisi

Daha ileri aşamada her hoparlör:

```text
Device ID
Speaker Type
Position
Channel Capability
Latency
Clock Offset
```

gibi bilgileri bildirebilir.

Örneğin:

```text
Speaker 04

Position:
    Rear Left

Capability:
    Full Range

Latency:
    1.8 ms

Clock Offset:
    +0.12 ms
```

Böylece sistem hoparlörleri yalnızca “8 tane ses cihazı” olarak değil, **uzamsal ses düğümleri** olarak görebilir.

---

# 19. Kanal Ataması Kullanıcıdan Gelebilir

Kullanıcı:

```text
AUDIO SETUP

Front Left
    → Speaker 06

Front Right
    → Speaker 02

Center
    → Speaker 00

Subwoofer
    → Speaker 07

Surround Left
    → Speaker 04

Surround Right
    → Speaker 05

Rear Left
    → Speaker 01

Rear Right
    → Speaker 03
```

diyebilir.

Bunun üzerine sistem:

```text
Audio Router
      ↓
Routing Matrix
      ↓
NWC
      ↓
Wireless Scheduler
      ↓
RF assignment
```

işlemlerini gerçekleştirir.

---

# 20. Otomatik Atama da Olabilir

Kullanıcı isterse:

```text
AUTO CONFIGURE
```

seçeneği bulunabilir.

NWL:

1. tüm hoparlörleri keşfeder,
2. yeteneklerini okur,
3. gecikmelerini ölçer,
4. sinyal kalitesini ölçer,
5. konum bilgilerini alır,
6. kanal eşleştirmesi önerir.

Ama son karar kullanıcıya bırakılabilir.

---

# 21. Aynı Sistem İçinde Farklı RF Ağları

Bir başka önemli sonuç:

Sekiz hoparlörün hepsinin aynı RF kanalında olması gerekmez.

Örneğin:

```text
RF0
 ├── Speaker 0
 ├── Speaker 1

RF1
 ├── Speaker 2
 ├── Speaker 3

RF2
 ├── Speaker 4
 ├── Speaker 5

RF3
 ├── Speaker 6
 └── Speaker 7
```

Ama hepsi:

```text
           ONE AUDIO STREAM
                  │
             NEXSUS AUDIO
                  │
             NWC / Router
                  │
       ┌──────────┼──────────┐
      RF0        RF1        RF2/RF3
```

altında aynı sistem olarak çalışır.

---

# 22. RF'ler Arası Senkronizasyon

Burada NWC'nin çok önemli bir görevi daha ortaya çıkıyor:

**radyo zamanlarını ortak bir zaman tabanında tutmak.**

```text
                 MASTER TIME
                     │
          ┌──────────┼──────────┐
          ↓          ↓          ↓
        RF0        RF1        RF2
          │          │          │
        SPK0       SPK3       SPK6
```

Böylece farklı fiziksel radyolar üzerinden gelen paketler de aynı audio timeline'a oturtulabilir.

---

# 23. RF ile İşlemci Arasındaki Paralellik

Paralellik yalnızca RF tarafında kalmamalıdır.

NWC:

```text
             NWC
              │
      ┌───────┼────────┐
      │       │        │
    RX DMA   TX DMA   Scheduler
      │       │
      └───────┼───────┘
              │
        System Fabric
```

şeklinde tasarlanabilir.

Örneğin:

```text
Wireless RX
    ↓
DMA
    ↓
Data MOSRAM
```

CPU'nun her paketi kopyalaması gerekmez.

---

# 24. Audio Buffer Yapısı

8 kanal için:

```text
             Audio Buffer
                  │
      ┌───────────┼───────────┐
      │           │           │
     CH0         CH1        ... CH7
      │           │           │
    buffer      buffer       buffer
```

veya daha yüksek performanslı durumda:

```text
Bank 0 → CH0
Bank 1 → CH1
Bank 2 → CH2
...
Bank 7 → CH7
```

gibi MOSRAM banklarına dağıtılabilir.

Bu da System Fabric + MOSRAM mimarisiyle doğal biçimde birleşir.

---

# 25. Wireless Channel Fabric

Bu noktada NWL'nin gerçek mimarisini artık şöyle tanımlayabiliriz:

```text
                       NEXSUS WIRELESS DOMAIN

                              NWC
                               │
                    ┌──────────┴──────────┐
                    │                     │
             RADIO FABRIC          CHANNEL FABRIC
                    │                     │
          ┌─────────┼─────────┐    ┌──────┼───────┐
          │         │         │    │      │       │
         RF0       RF1       RF2  AUDIO   HID    DATA
          │         │         │    │      │       │
       Speaker    Mouse     Phone  7.1   Mouse   File
```

**Radio Fabric** fiziksel kaynakları yönetir.

**Channel Fabric** mantıksal akışları yönetir.

Bu ikisini ayırmak NWL'nin temel mimari kararlarından biri olmalı.

---

# 26. Çoklu Alıcı / Verici

Aynı cihazın birden fazla radyo modülü de bulunabilir.

Örneğin yüksek kaliteli bir hoparlör:

```text
Speaker Receiver
       │
    ┌──┴──┐
   RX-A  RX-B
    │      │
 Audio   Control
```

olabilir.

Veya headset:

```text
RX0 → Audio
RX1 → Microphone / Control
```

gibi fiziksel ayrım kullanabilir.

Bu, cihaz tasarımının gerektirdiği durumda kullanılabilecek bir seçenektir.

---

# 27. NWL'de Sabit Kanal Kavramı Yok

Kullanıcı açısından:

```text
Mouse → Channel 12
```

gibi sabit fiziksel bir kanal olması gerekmiyor.

Bunun yerine:

```text
Mouse
 ↓
Logical Service
 ↓
NWL Scheduler
 ↓
Available Radio
```

çalışır.

Sistem gerektiğinde mouse'u başka bir fiziksel bağlantıya taşıyabilir.

---

# 28. Örnek: Her Şey Aynı Anda Çalışıyor

Kullanıcı bilgisayarında:

- 8 kablosuz hoparlör
- kablosuz headset
- mikrofon
- mouse
- keyboard
- telefon
- kablosuz SSD

olduğunu varsayalım.

NWL:

```text
                    NWC

         ┌───────────┼────────────┐
         │           │            │
      AUDIO         HID          DATA
         │           │            │
   ┌─────┴─────┐   ┌─┴──┐    ┌───┴────┐
   │           │   │    │    │        │
 7.1         Headset Mouse Key     Phone SSD
   │
 ┌─┴──────────────────────┐
 │ RF0 RF1 RF2 RF3 ...    │
 └────────────────────────┘
```

şeklinde kaynakları dağıtır.

Sonuçta:

```text
8 hoparlör
     +
mouse
     +
keyboard
     +
headset
     +
phone
     +
data transfer
```

aynı NWL alanında eşzamanlı çalışabilir.

---

# 29. Buradaki En Önemli Tasarım İlkesi

NWL'nin temel prensibini artık şöyle yazabiliriz:

> **Bir kablosuz bağlantı, tek bir cihaz bağlantısı değildir; zamanlanmış, yönlendirilebilir ve gerektiğinde birden fazla fiziksel radyo üzerinden taşınabilen mantıksal veri akışlarının birleşimidir.**

Bunun sonucu:

```text
DEVICE
    ↓
SERVICES
    ↓
LOGICAL CHANNELS
    ↓
STREAMS
    ↓
CHANNEL ROUTER
    ↓
RADIO SCHEDULER
    ↓
PARALLEL RADIOS
```

olur.

---

# 30. NEXSUS İçin Yeni Kavram: Wireless Routing Table

NWL'nin çekirdek veri yapılarından biri:

```text
WIRELESS ROUTING TABLE
```

olmalıdır.

Örneğin:

| Stream | Source | Destination | RF | Priority | Sync |
|---|---|---|---|---|---|
| Audio-0 | PC | SPK6 | RF0 | RT | T |
| Audio-1 | PC | SPK2 | RF0 | RT | T |
| Audio-2 | PC | SPK0 | RF1 | RT | T |
| Audio-3 | PC | SPK7 | RF1 | RT | T |
| HID-0 | Mouse | CPU | RF2 | HIGH | — |
| HID-1 | Keyboard | CPU | RF2 | HIGH | — |
| DATA-0 | Phone | MOSRAM | RF3 | NORMAL | — |

Bu tablo çalışma sırasında değişebilir.

---

# 31. Böylece NEXSUS Audio Sistemi de Genel Bir Wireless Service Olur

7.1 örneği yalnızca bir ses özelliği değildir.

Aynı mimari:

```text
Audio
Video
Microphone
Camera
HID
Storage
Sensor
Phone
Controller
```

için kullanılabilir.

Dolayısıyla NWL'nin temelinde:

**“Bluetooth audio”**

değil,

**“Wireless Service Routing”**

bulunmalıdır.

---

# 32. Tasarımın Bir Sonraki Aşaması

Bu noktada NWL'nin mimari omurgası oluştu.

Bir sonraki teknik katman artık daha somut olabilir:

```text
NWL
│
├── Device ID
├── Capability Table
├── Service ID
├── Stream ID
├── Channel ID
├── Routing Table
├── Radio ID
├── Priority
├── Timestamp
├── Sequence
├── Security Context
└── Scheduler
```

Burada özellikle **Channel ID – Stream ID – Radio ID** ayrımını doğru kurmamız gerekiyor.

Çünkü:

```text
1 Device
   ↓
N Services
   ↓
N Streams
   ↓
M Logical Channels
   ↓
K Physical Radios
```

olabilmeli.

Bu yapı kurulduğunda NWL gerçekten **System Fabric'in kablosuz uzantısı** haline gelir.
