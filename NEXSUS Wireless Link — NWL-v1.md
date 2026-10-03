# NEXSUS Wireless Link (NWL)
## Kavramsal, Mimari ve Teknik Tasarım

**Sistem:** NEXSUS  
**Alt Sistem:** NEXSUS Wireless Link — NWL  
**Bileşen:** NEXSUS Wireless Controller — NWC  
**Durum:** Kavramsal + Ön Teknik Tasarım  
**Mimari Sürüm:** NWL-1

---

## 1. Amaç

NEXSUS Wireless Link (NWL), klasik Bluetooth benzeri “cihaz bağlama” yaklaşımının yerine, bilgisayarın bütün kablosuz çevre birimlerini tek bir sistem altında yöneten ortak bir kablosuz iletişim mimarisi olarak tasarlanır.

Temel yaklaşım:

\[
\boxed{\text{Cihaz} \neq \text{Bağlantı}}
\]

Bir cihazın tek bir bağlantısı olmak zorunda değildir.

Bir cihaz birden fazla servis ve akış sağlayabilir:

```text
Telefon
 ├── Ses
 ├── Mikrofon
 ├── Kamera
 ├── Dosya
 ├── Bildirim
 └── Uygulama servisi
```

Benzer şekilde bir kulaklık:

```text
Kulaklık
 ├── Sol ses
 ├── Sağ ses
 ├── Mikrofon
 ├── Kontrol
 └── Durum / batarya
```

NWL bu servisleri bağımsız mantıksal akışlar olarak yönetir.

---

# 2. Temel Mimari Hiyerarşi

NWL'nin temel adresleme ve yönlendirme modeli:

\[
\boxed{
Device \rightarrow Service \rightarrow Stream \rightarrow Channel \rightarrow Radio
}
\]

### Device

Fiziksel cihaz.

Örneğin:

- hoparlör
- kulaklık
- klavye
- fare
- telefon
- kamera
- harici depolama
- mikrofon

### Service

Cihazın sunduğu işlev.

Örneğin:

```text
Speaker
 └── Audio Service

Headset
 ├── Audio Service
 ├── Microphone Service
 └── Control Service
```

### Stream

Sürekli veya paket tabanlı veri akışı.

Örneğin:

```text
7.1 Audio Stream
Mouse HID Stream
File Transfer Stream
Microphone Stream
```

### Channel

Stream içerisindeki mantıksal kanal.

7.1 ses için:

\[
CH_0 \ldots CH_7
\]

olmak üzere sekiz bağımsız ses kanalı bulunabilir.

### Radio

Gerçek RF kaynağı.

Bir channel belirli bir RF'ye kalıcı olarak bağlı değildir.

Scheduler çalışma sırasında uygun RF'yi seçebilir.

---

# 3. NEXSUS Wireless Controller

NWL'nin merkezi bileşeni:

\[
\boxed{NWC = NEXSUS\ Wireless\ Controller}
\]

NWC içerisinde temel olarak şu birimler bulunur:

```text
                 NEXSUS WIRELESS CONTROLLER
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   Device Manager     Channel Fabric     Radio Fabric
        │                  │                  │
        │             QoS / Routing      RF Scheduler
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                     System Fabric
```

NWC'nin temel görevleri:

- cihaz keşfi
- servis keşfi
- bağlantı yönetimi
- RF yönetimi
- kanal tahsisi
- zamanlama
- QoS
- paket sıralama
- hata yönetimi
- yeniden iletim
- RF değiştirme
- stream migration
- güvenlik
- zaman senkronizasyonu

NWC, CPU'nun altında çalışan basit bir çevre birimi değil, NWL'nin gerçek iletişim yöneticisidir.

---

# 4. Minimum RF Mimarisi

Başlangıç teknik tasarımında:

\[
\boxed{N_{RF}=4}
\]

bağımsız tam çift yönlü RF transceiver öngörülür.

```text
                    NWC
                     │
        ┌────────────┼────────────┐
        │            │            │
       RF0          RF1          RF2          RF3
        │            │            │            │
     2.4 GHz       6 GHz        6 GHz        6 GHz
```

Ancak bu bağlantı yalnızca üç RF anlamına gelmez; toplam:

- 1 × 2.4 GHz RF
- 3 × 6 GHz RF

olmak üzere **4 bağımsız RF zinciri** bulunur.

Bu sayı protokolün değişmez bir parçası değildir.

Örneğin ileride:

\[
N_{RF}=8
\]

olan bir NWL sürümü üretilebilir.

Dolayısıyla:

\[
NWL\ Protocol \neq RF\ Count
\]

Bu ayrım önemlidir.

---

# 5. 2.4 GHz RF

2.4 GHz RF'nin temel görevi düşük ve orta veri oranlı, geniş uyumluluk gerektiren cihazları taşımaktır.

Özellikle:

- klavye
- fare
- kumanda
- düşük veri sensörleri
- sistem kontrolü
- düşük hızlı durum bilgisi
- yedek bağlantı

için kullanılabilir.

2.4 GHz bandında mevcut Bluetooth LE teknolojisi 40 adet 2 MHz kanal kullanmakta ve adaptif frekans atlaması uygulamaktadır.

NWL'nin aynı protokolü kullanması gerekmez; ancak 2.4 GHz ortamının yoğunluğu nedeniyle benzer şekilde kanal kalitesi ölçümü ve adaptif kanal seçimi mimaride bulunmalıdır.

### Önerilen NWL-2.4 PHY

İlk teknik profil:

| Parametre | NWL-2.4 |
|---|---:|
| Bant | 2.4 GHz ISM |
| RF sayısı | 1 |
| Kanal genişliği | 2 / 5 / 10 MHz sınıfı |
| Modülasyon | OFDM veya düşük hızlı alternatif PHY |
| FEC | Var |
| CRC | Var |
| Adaptive Channel Selection | Var |
| Frequency Hopping | Opsiyonel |
| TX/RX | Full duplex* |
| Ana kullanım | HID / Control / Low-rate Data |

\* RF fiziksel katmanının aynı anda gerçek full-duplex çalışması veya hızlı TDD kullanması sonraki RF devre tasarımında kesinleştirilecektir.

---

# 6. 6 GHz RF

NWL'nin yüksek hızlı ana RF bandı 6 GHz olarak belirlenir.

Başlangıç hedefi:

\[
5945-6425\ MHz
\]

sınıfındaki 6 GHz RLAN bandıdır.

ETSI EN 303 687 bu bandı 5945–6425 MHz olarak tanımlar.

Bu bandın kullanılabilirliği ve izin verilen güç/kanal profili ürünün hedef ülkesine göre ayrıca doğrulanmalıdır.

Türkiye dahil gerçek ürün tasarımında BTK'nın güncel spektrum ve cihaz düzenlemeleri esas alınacaktır.

Dolayısıyla NWL'nin RF mimarisi:

```text
NWL RF Profile
       │
       ├── Global PHY
       │
       ├── Regional Band Profile
       │
       └── Regulatory Power Profile
```

şeklinde tasarlanmalıdır.

---

# 7. 6 GHz Kanal Genişliği

İlk teknik tasarımda tek bir kanal genişliği zorunlu tutulmaz.

Önerilen çalışma aralığı:

\[
20/40/80/160\ MHz
\]

Wi-Fi 6E sınıfı 6 GHz ekipmanlarda 20, 40, 80 ve 160 MHz kanal genişlikleri zaten kullanılmaktadır.

NWL için ilk prototipte:

\[
\boxed{80\ MHz}
\]

ana çalışma modu olarak düşünülebilir.

160 MHz ise yüksek veri ihtiyacında açılabilir.

Böylece:

```text
Normal ortam
    ↓
40 / 80 MHz

Yoğun veri
    ↓
80 / 160 MHz

Yoğun RF ortamı
    ↓
20 / 40 MHz
```

şeklinde dinamik PHY seçimi yapılabilir.

320 MHz başlangıç tasarımında zorunlu tutulmaz.

Bunun nedeni tek bir RF'nin aşırı genişletilmesi yerine mevcut dört bağımsız RF'nin birlikte kullanılmasının NWL'nin mimari amacına daha uygun olmasıdır.

---

# 8. Modülasyon ve Kodlama

6 GHz yüksek hızlı PHY için başlangıçta OFDM tabanlı bir yapı uygundur.

Temel seçenek:

\[
\boxed{OFDM + LDPC + Adaptive\ MCS}
\]

MCS seviyesi kanal durumuna göre değiştirilir.

Örneğin:

```text
Kötü kanal
   ↓
QPSK + güçlü FEC

Orta kanal
   ↓
16-QAM

İyi kanal
   ↓
64-QAM

Çok iyi kanal
   ↓
256-QAM / daha yüksek
```

Amaç maksimum teorik hız değil, gerçek sistem throughput'unu korumaktır.

---

# 9. RF Kaynaklarının Sabit Görevli Olmaması

Önemli mimari kural:

```text
RF0 = Mouse
RF1 = Audio
RF2 = Data
RF3 = Storage
```

şeklinde sabit bir yapı **yoktur**.

Bunun yerine:

```text
                 RADIO POOL
          ┌──────┬──────┬──────┬──────┐
          │ RF0  │ RF1  │ RF2  │ RF3  │
          └──┬───┴──┬───┴──┬───┴──┬───┘
             │      │      │      │
             └──────┴──────┴──────┘
                    │
              RADIO SCHEDULER
                    │
              LOGICAL STREAMS
```

kullanılır.

Örneğin bir anda:

```text
RF0 → Mouse
RF1 → Audio
RF2 → File Transfer
RF3 → Phone
```

olabilir.

Başka bir anda:

```text
RF0 → Mouse + Keyboard
RF1 → Audio
RF2 → File Transfer
RF3 → File Transfer
```

olabilir.

---

# 10. Radio Fabric

RF'lerin fiziksel kaynak yönetimini:

\[
\boxed{Radio\ Fabric}
\]

yapar.

Radio Fabric her RF için sürekli olarak:

- RSSI
- SNR
- paket hata oranı
- retransmission oranı
- kanal doluluğu
- gecikme
- RF çakışması
- güç tüketimi

gibi değerleri izler.

Her RF için bir kalite metriği tanımlanabilir:

\[
Q_{RF}=f(SNR,PER,Latency,Load,Power)
\]

Scheduler uygun RF'yi:

\[
RF_{selected}=\arg\max(Q_{RF})
\]

mantığıyla seçebilir.

Bu yalnızca throughput optimizasyonu değildir.

Örneğin ses akışı için:

\[
Q_{audio}=f(Latency,Jitter,PER)
\]

öncelikli olabilir.

Dosya aktarımı için ise:

\[
Q_{data}=f(Throughput,PER)
\]

daha önemli olabilir.

---

# 11. Channel Fabric

Radio Fabric fiziksel RF'leri yönetirken:

\[
\boxed{Channel\ Fabric}
\]

mantıksal akışları yönetir.

Aradaki temel fark:

```text
Channel Fabric
     ↓
"Ne taşınacak?"

Radio Fabric
     ↓
"Nereden taşınacak?"
```

Bu ayrım NWL'nin ana yeniliklerinden biridir.

---

# 12. 7.1 Ses Mimarisi

NWL'de 7.1 ses sekiz fiziksel RF bağlantısı anlamına gelmez.

7.1:

\[
8\ logical\ audio\ channels
\]

demektir.

Örneğin:

```text
CH00 → Front Left
CH01 → Front Right
CH02 → Center
CH03 → LFE
CH04 → Surround Left
CH05 → Surround Right
CH06 → Rear Left
CH07 → Rear Right
```

Bu kanallar kullanıcı tarafından fiziksel hoparlörlere yönlendirilebilir.

Örneğin:

```text
CH00 → Speaker 06
CH01 → Speaker 02
CH02 → Speaker 00
CH03 → Speaker 07
CH04 → Speaker 04
CH05 → Speaker 05
CH06 → Speaker 01
CH07 → Speaker 03
```

Dolayısıyla hoparlör numarası ses kanalının kendisi değildir.

---

# 13. Dinamik Audio Routing Matrix

Ses yönlendirmesi bir matris olarak ifade edilebilir:

\[
R_{ij}
\]

Burada:

- \(i\) = mantıksal ses kanalı
- \(j\) = fiziksel hoparlör

Basit durumda:

\[
R_{ij}\in\{0,1\}
\]

olur.

Daha gelişmiş durumda:

\[
R_{ij}\in[0,1]
\]

olabilir.

Örneğin:

\[
R_{0,3}=1
\]

Front Left kanalının Speaker 3'e gönderildiğini ifade eder.

Daha gelişmiş kullanımda:

\[
R_{0,3}=0.7
\]

\[
R_{0,4}=0.3
\]

olabilir.

Böylece bir kanal iki fiziksel hoparlöre kontrollü olarak dağıtılabilir.

Bu yapı aynı zamanda:

- stereo genişletme
- downmix
- upmix
- çoklu hoparlör
- yedek hoparlör

gibi işlemleri destekleyebilir.

---

# 14. 7.1 Bant Genişliği

Sıkıştırılmamış 24-bit / 96 kHz 7.1 ses için:

\[
96000\times24\times8
=
18.432\ Mbps
\]

gerekir.

24-bit / 192 kHz için:

\[
192000\times24\times8
=
36.864\ Mbps
\]

olur.

Dolayısıyla 7.1 sesin kendisi çok yüksek bir RF kapasitesi gerektirmez.

Asıl problem:

\[
\boxed{
Latency + Jitter + Synchronization + Reliability
}
\]

olur.

Bu nedenle NWL'de RF'lerin paralel olması yalnızca bandwidth için değil, **trafik izolasyonu** için önemlidir.

---

# 15. Audio Timebase

Kablosuz hoparlörlerde en önemli sorunlardan biri paketlerin farklı zamanlarda ulaşmasıdır.

Bu nedenle NWL'de ortak zaman tabanı bulunur:

\[
\boxed{NWL\ Master\ Timebase}
\]

Audio paketi yalnızca:

```text
Stream ID
Channel ID
Sequence
Payload
```

taşımamalıdır.

Buna ek olarak:

```text
Presentation Timestamp
```

bulunmalıdır.

Hoparlör:

\[
t_{play}=Timestamp
\]

anında veriyi oynatır.

Dolayısıyla paket:

- erken gelirse buffer'da bekler,
- geç gelirse uygun deadline politikasına göre atılabilir,
- kaybolursa ses akışının yapısına göre tekrar istenebilir veya interpolasyon uygulanabilir.

Bu yaklaşım Bluetooth LE'nin isochronous stream kavramlarıyla aynı problem alanına hitap eder; Bluetooth LE'de CIS/CIG yapıları zamanlanmış izokron akışlar için kullanılmaktadır.

NWL ise bunu kendi Channel Fabric ve Radio Fabric mimarisi içinde daha genel bir sistem akışına dönüştürür.

---

# 16. QoS Sınıfları

NWL bütün paketleri aynı şekilde ele almaz.

Önerilen sınıflar:

| Öncelik | Sınıf | Örnek |
|---|---|---|
| P0 | System Critical | Güç / bağlantı kontrolü |
| P1 | Realtime Control | Mouse / keyboard |
| P2 | Isochronous | Audio / microphone |
| P3 | Interactive | Kamera / telefon |
| P4 | Bulk | Dosya aktarımı |
| P5 | Background | Senkronizasyon |

Böylece büyük bir dosya transferi:

\[
FileTransfer \neq Audio
\]

olarak değerlendirilir.

Örneğin Data Stream 500 MB/s seviyesinde RF kaynaklarını kullanıyor olsa bile Audio Scheduler gerekli zamanı ayırır.

---

# 17. Paket Yapısı

İlk NWL MAC çerçevesi için kavramsal yapı:

```text
┌──────────────┬──────────────┬─────────────┬──────────────┐
│ PHY Header   │ NWL Header   │ Payload     │ Integrity    │
└──────────────┴──────────────┴─────────────┴──────────────┘
```

NWL Header içerisinde kavramsal olarak:

```text
Version
Frame Type
Device ID
Service ID
Stream ID
Channel ID
Sequence
Timestamp
QoS
Length
Flags
```

bulunabilir.

Kesin bit genişlikleri henüz ISA/protokol tasarımında olduğu gibi dondurulmaz.

---

# 18. Frame Tipleri

Temel frame sınıfları:

```text
CONTROL
DISCOVERY
CAPABILITY
DATA
AUDIO
STATUS
ACK
NACK
SYNC
MANAGEMENT
SECURITY
```

Örneğin:

```text
AUDIO
 ├── Stream ID
 ├── Channel ID
 ├── Sequence
 ├── Presentation Time
 └── Audio Payload
```

Mouse:

```text
HID
 ├── Device ID
 ├── Sequence
 ├── X
 ├── Y
 ├── Buttons
 └── Timestamp
```

Dosya:

```text
DATA
 ├── Stream ID
 ├── Sequence
 ├── Offset
 ├── Length
 └── Payload
```

---

# 19. Retransmission Politikası

Her stream için aynı hata düzeltme yöntemi kullanılmaz.

### Mouse

Kayıp paket mümkün olduğunca hızlı yeni durumla değiştirilir.

\[
Retransmission \approx Low
\]

### Audio

Eski ses paketini geç tekrar göndermek anlamsız olabilir.

\[
Deadline < Retransmission\ Delay
\]

ise paket atılır.

### Dosya

Veri kaybı kabul edilmez.

\[
Reliability \rightarrow 100\%
\]

hedeflenir.

Dolayısıyla:

```text
Audio  → Deadline oriented
HID    → Freshness oriented
Data   → Reliability oriented
```

---

# 20. RF Bonding

Tek bir stream gerektiğinde birden fazla RF kullanılabilir.

Örneğin:

```text
             File Stream
                 │
          ┌──────┴──────┐
          │             │
         RF2           RF3
          │             │
       Packet A       Packet B
       Packet C       Packet D
```

NWC bunları alıcı tarafta tekrar birleştirir.

Bu:

\[
Throughput_{total}
\approx
Throughput_{RF2}
+
Throughput_{RF3}
\]

seviyesine yaklaşabilir.

Gerçek değer protokol overhead'i, RF koşulları ve scheduler nedeniyle daha düşük olacaktır.

---

# 21. RF Redundancy

Kritik stream için iki RF kullanılabilir.

```text
              Audio Stream
                  │
             ┌────┴────┐
             │         │
            RF1       RF2
             │         │
          Primary   Redundant
```

Alıcı duplicate packet'leri sequence numarası ile ayırır.

Bu durumda:

\[
Reliability \uparrow
\]

ancak:

\[
Spectrum\ Usage \uparrow
\]

olur.

Scheduler bu modu yalnızca gerekli olduğunda açar.

---

# 22. RF Migration

Bir stream aktifken RF değiştirilebilir.

Örneğin:

```text
t0:
Audio → RF1

t1:
RF1 quality ↓

t2:
Audio → RF2

t3:
RF1 released
```

Bu geçişin kullanıcı tarafından hissedilmemesi hedeflenir.

Bunun için stream'in mantıksal kimliği RF'den bağımsız tutulur.

\[
StreamID = constant
\]

\[
RadioID = dynamic
\]

Bu NWL'nin en önemli mimari özelliklerinden biridir.

---

# 23. Paralel RF ile Fiziksel Trafik İzolasyonu

NWL'nin dört RF'li tasarımının asıl avantajlarından biri budur.

Örneğin:

```text
RF0
 └── Mouse + Keyboard

RF1
 └── 7.1 Audio

RF2
 └── Phone + Camera

RF3
 └── File Transfer
```

Böylece büyük veri aktarımı ses akışının bütün RF kapasitesini tüketmek zorunda kalmaz.

Ancak RF'ler tamamen birbirinden bağımsız spektrumlar değildir.

Bu nedenle NWC ayrıca RF'ler arası:

- leakage
- harmonics
- intermodulation
- antenna coupling
- coexistence

durumlarını da izlemelidir.

---

# 24. RF Frekans Ayrımı

Önerilen fiziksel yapı:

```text
RF0 → 2.4 GHz
RF1 → 6 GHz
RF2 → 6 GHz
RF3 → 6 GHz
```

6 GHz RF'ler aynı bant içerisinde birbirinden yeterli kanal ayrımı ile çalışabilir.

Örneğin:

```text
6 GHz Band
┌───────────────────────────────────────────┐
│     RF1       │      RF2      │    RF3    │
└───────────────────────────────────────────┘
```

veya ortam koşuluna göre:

```text
RF1 ────────────────
RF2       ────────────────
RF3               ────────────────
```

şeklinde dinamik spektrum yerleşimi yapılabilir.

ETSI'nin 6 GHz RLAN standardı 20–160 MHz sınıfındaki çoklu kanal işletimini de tanımlayan spektral maskeler içerir; bu nedenle NWL'nin dinamik kanal genişliği yaklaşımı teknik olarak gerçek bir RF tasarım problemi olarak ele alınabilir.

---

# 25. Anten Mimarisi

RF sayısı ile anten sayısı aynı olmak zorunda değildir.

Başlangıç prototipinde:

\[
4\ RF \rightarrow 4\ bağımsız\ RF\ path
\]

kullanılabilir.

Ancak daha ileri model:

```text
             RF Chains
          ┌────┬────┬────┬────┐
          │RF0 │RF1 │RF2 │RF3 │
          └─┬──┴─┬──┴─┬──┴─┬──┘
            │    │    │    │
          ┌─┴────┴────┴────┴─┐
          │ Antenna Frontend  │
          └───────────────────┘
                   │
            Multiple Antennas
```

şeklinde olabilir.

Bu yapı beamforming veya spatial diversity için ileride kullanılabilir.

İlk prototipte gereksiz karmaşıklık eklenmemesi tercih edilir.

---

# 26. NWC — System Fabric Bağlantısı

NWC, NEXSUS System Fabric'e doğrudan bağlanır.

```text
                    NEXSUS SYSTEM FABRIC
                           │
          ┌────────────────┼─────────────────┐
          │                │                 │
         CPU              FAPU              NWC
          │                                  │
     Application                         Wireless
                                          Devices
```

Kablosuz veri her zaman CPU üzerinden geçirilmek zorunda değildir.

Örneğin:

```text
Wireless Camera
       │
       ▼
      NWC
       │
       ▼
 Data MOSRAM
```

veya:

```text
Wireless Sensor
       │
       ▼
      NWC
       │
       ▼
      FAPU
```

mümkün olabilir.

Bu, NEXSUS System Fabric'in “gereksiz veri hareketini azaltma” ilkesine doğrudan uyar.

---

# 27. NWC ve SCP Ayrımı

NWC ile SCP aynı görevde değildir.

### NWC

- RF
- cihaz
- bağlantı
- kanal
- stream
- scheduler
- wireless security

yönetir.

### SCP

- güç
- reset
- termal kontrol
- board management
- firmware
- donanım başlatma
- sistem durumları

yönetir.

```text
              NEXSUS
                 │
        ┌────────┴────────┐
        │                 │
       SCP               NWC
        │                 │
 System Control       Wireless Control
```

NWC gerektiğinde SCP'den güç durumu veya sistem durumu bilgisi alabilir.

---

# 28. CPU Uyku Durumu

NWC CPU'ya tamamen bağımlı olmamalıdır.

CPU uyurken:

```text
CPU = Sleep

NWC = Active
SCP = Active
```

olabilir.

Örneğin telefon bağlantısı veya klavye olayı NWC tarafından alınır.

NWC:

```text
Wireless Event
      ↓
NWC
      ↓
SCP
      ↓
CPU Wake
```

şeklinde CPU'yu uyandırabilir.

---

# 29. Cihaz Keşfi

NWL bağlantı süreci:

```text
DISCOVERY
    ↓
DEVICE IDENTIFICATION
    ↓
CAPABILITY DISCOVERY
    ↓
SERVICE DISCOVERY
    ↓
SECURITY
    ↓
RESOURCE ASSIGNMENT
    ↓
STREAM CREATION
    ↓
ACTIVE
```

Örneğin yeni bir hoparlör:

```text
Device:
Speaker-03

Services:
Audio

Capabilities:
2-channel
24-bit
192 kHz
```

şeklinde kendisini tanıtabilir.

NWC buna göre uygun stream ve channel oluşturur.

---

# 30. Tek Alıcı ile Çoklu Cihaz

NWL'nin hedefi:

\[
\boxed{
1\ NWC
\rightarrow
çok\ sayıda\ cihaz
}
\]

olmasıdır.

Klavye için:

```text
NWL Receiver
 └── Keyboard
```

Fare için ayrı USB dongle:

```text
NWL Receiver
 └── Mouse
```

kulaklık için başka dongle:

```text
NWL Receiver
 └── Headset
```

gerekmemelidir.

Bütün cihazlar aynı NWC tarafından yönetilir.

---

# 31. Telefonun NWL İçerisindeki Konumu

Telefon yalnızca “Bluetooth cihazı” olarak görülmez.

NWL telefonu birden fazla servis sunan cihaz olarak görebilir:

```text
PHONE
 ├── Audio
 ├── Microphone
 ├── Camera
 ├── Storage
 ├── Notifications
 ├── Input
 └── Application Service
```

Dolayısıyla telefon ile bilgisayar arasında:

```text
Audio
Camera
File
Control
Notification
Application
```

akışları aynı anda çalışabilir.

Her biri farklı QoS ve RF kaynaklarına sahip olabilir.

---

# 32. Güvenlik

NWL'nin güvenliği cihaz seviyesinde değil, stream/service seviyesinde uygulanmalıdır.

Temel yapı:

```text
Device Authentication
        ↓
Service Authorization
        ↓
Session Key
        ↓
Stream Security
        ↓
Integrity
```

Her veri frame'i en azından bütünlük kontrolüne sahip olmalıdır.

Hassas servislerde şifreleme:

\[
Payload \rightarrow Encryption \rightarrow RF
\]

şeklinde uygulanır.

---

# 33. Adaptif Kanal Seçimi

Kablosuz ortam sürekli değişir.

Bu nedenle NWC:

\[
ChannelQuality(t)
\]

değerini zaman içinde izler.

Kanal kötüleşirse:

```text
Bad Channel
     ↓
Mark degraded
     ↓
Move stream
     ↓
Select new channel
     ↓
Resume
```

yapılır.

Bluetooth LE'de de kanalların kalitesi ölçülerek kötü kanalların kullanım dışı bırakılabildiği adaptive frequency hopping yaklaşımı kullanılmaktadır.

NWL bunu daha üst seviyede Radio Fabric'in parçası haline getirir.

---

# 34. Latency Yönetimi

Her servis için farklı latency hedefi bulunur.

Örneğin:

| Servis | Öncelikli özellik |
|---|---|
| Mouse | düşük latency |
| Keyboard | düşük latency |
| Audio | düşük jitter |
| Microphone | düşük latency + sürekli akış |
| Camera | latency + throughput |
| File | throughput |
| Backup | reliability |

Dolayısıyla tek bir “NWL latency” değeri yoktur.

\[
Latency_{service}=f(ServiceType)
\]

---

# 35. NEXSUS Wireless Scheduler

Scheduler'ın görevi yalnızca paket sıraya koymak değildir.

Aynı anda:

\[
Resource =
\{RF,Channel,Time,Power,Bandwidth\}
\]

kaynaklarını yönetir.

Karar fonksiyonu kavramsal olarak:

\[
Score =
w_1Q_{RF}
+w_2Priority
+w_3Deadline
+w_4Throughput
-w_5Power
\]

şeklinde düşünülebilir.

Buradaki katsayılar henüz sabit değildir.

---

# 36. Örnek Gerçek Sistem Yükü

Bir NEXSUS bilgisayarında aynı anda:

```text
7.1 Wireless Audio
        +
Wireless Mouse
        +
Wireless Keyboard
        +
Phone Connection
        +
Camera Stream
        +
Large File Transfer
```

çalışabilir.

NWL bunu:

```text
RF0
 ├── Mouse
 └── Keyboard

RF1
 └── 7.1 Audio

RF2
 └── Camera

RF3
 ├── Phone
 └── File Transfer
```

şeklinde dağıtabilir.

Ancak RF tahsisi dinamik olduğundan bu yalnızca örnek bir durumdur.

---

# 37. Minimum Teknik Konfigürasyon

İlk NEXSUS masaüstü sistemi için önerilen NWL-1:

| Parametre | Tasarım |
|---|---|
| RF sayısı | **4** |
| 2.4 GHz RF | **1** |
| 6 GHz RF | **3** |
| RF tipi | Full TX/RX transceiver |
| 6 GHz ana kanal | **80 MHz sınıfı** |
| 6 GHz geniş kanal | **160 MHz** |
| Dinamik kanal | **20/40/80/160 MHz** |
| PHY | OFDM sınıfı |
| FEC | LDPC sınıfı |
| Kanal seçimi | Dinamik |
| RF migration | Var |
| RF bonding | Var |
| RF redundancy | Var |
| Ortak zaman tabanı | Var |
| Channel Fabric | Var |
| Radio Fabric | Var |
| QoS | Var |
| Stream timestamp | Var |
| 7.1 audio | 8 logical channels |
| CPU bağımlılığı | Düşük |
| System Fabric bağlantısı | Doğrudan |

Bu tablo **NWL-1 ön teknik profili**dir; nihai RF standardı değildir.

---

# 38. Neden Dört RF?

Dört RF'nin amacı yalnızca daha yüksek toplam Mbps değildir.

Asıl hedef:

\[
\boxed{
Parallelism + Isolation + Reliability + Flexibility
}
\]

olmasıdır.

İki RF ile sistem kurulabilir; ancak farklı servislerin aynı RF üzerinde zaman paylaşımı yapması daha sık hale gelir.

Sekiz RF ise ilk NEXSUS sistemi için fiziksel maliyet, güç, anten karmaşıklığı ve RF izolasyonu açısından gereksiz olabilir.

Bu nedenle:

\[
\boxed{N_{RF}=4}
\]

ilk mimari için dengeli başlangıç noktası olarak tutulur.

Ancak gerçek optimum değer ancak RF laboratuvar ölçümleri ve yük testlerinden sonra belirlenebilir.

---

# 39. RF Sayısından Bağımsız Protokol

NWL'nin önemli bir özelliği:

\[
NWL_{Protocol}(N_{RF}=4)
=
NWL_{Protocol}(N_{RF}=8)
\]

olmasıdır.

Yani kullanıcı açısından:

```text
NWL-4
NWL-6
NWL-8
```

farklı protokoller değildir.

Sadece Radio Fabric kapasitesi değişir.

Bu, gelecekte anakartın farklı modellerinde:

```text
NEXSUS Basic
NEXSUS Pro
NEXSUS Workstation
```

gibi farklı RF kapasitesi kullanılmasını mümkün kılar.

---

# 40. Gelecek RF Katmanları

NWL'nin ilk sürümünde 60 GHz zorunlu değildir.

İleride:

```text
2.4 GHz
6 GHz
60 GHz
```

aynı Radio Fabric'e eklenebilir.

60 GHz özellikle:

- çok yüksek kısa mesafe veri
- docking
- ekran
- kısa mesafe yüksek hızlı storage

gibi kullanım alanlarında değerlendirilebilir.

Böylece Radio Fabric:

```text
             Radio Fabric
                  │
       ┌──────────┼──────────┐
       │          │          │
     2.4 GHz     6 GHz      60 GHz
       │          │          │
      HID       Main        Future
               Wireless
```

haline gelebilir.

---

# 41. NEXSUS Wireless Link'in Temel Tasarım İlkeleri

NWL şu prensipler üzerine kuruludur:

1. **Cihaz değil servis temel birimdir.**
2. **Servis değil stream temel iletişim nesnesidir.**
3. **Stream RF'ye sabit bağlı değildir.**
4. **Mantıksal Channel Fabric ile fiziksel Radio Fabric ayrıdır.**
5. **RF kaynakları paralel çalışabilir.**
6. **RF sayısı protokolden bağımsızdır.**
7. **Audio zaman tabanlıdır.**
8. **HID düşük gecikmeli çalışır.**
9. **Bulk data throughput odaklıdır.**
10. **RF arızası stream arızasına dönüşmemelidir.**
11. **CPU bütün kablosuz verinin zorunlu geçiş noktası değildir.**
12. **NWC System Fabric'e doğrudan bağlanır.**
13. **SCP sistem kontrolünü, NWC kablosuz iletişimi yönetir.**
14. **Tek NWC çok sayıda cihazı yönetir.**
15. **7.1 sekiz RF değil, sekiz mantıksal ses kanalıdır.**
16. **Kanal → hoparlör eşlemesi kullanıcı tarafından değiştirilebilir.**
17. **RF kaynakları çalışma sırasında yeniden tahsis edilebilir.**
18. **PHY parametreleri ortam koşullarına göre değişebilir.**
19. **Bölgesel spektrum kuralları RF profilinin parçasıdır.**
20. **NWL yüksek throughput'tan önce kontrollü veri hareketini hedefler.**

---

# 42. Son Mimari

NWL'nin bütün yapısı şu şekilde özetlenebilir:

```text
                         NEXSUS SYSTEM
                               │
                        SYSTEM FABRIC
                               │
                        NEXSUS WIRELESS
                          CONTROLLER
                               │
                ┌──────────────┴──────────────┐
                │                             │
          CHANNEL FABRIC                RADIO FABRIC
                │                             │
       ┌────────┼────────┐          ┌─────────┼─────────┐
       │        │        │          │         │         │
     Audio     HID      Data       RF0       RF1       RF2/RF3
       │        │        │          │         │         │
       └────────┴────────┘          └─────────┴─────────┘
                │                             │
                └─────────── Scheduler ───────┘
                               │
                         Wireless Devices
```

Daha alt seviyede:

```text
Device
   ↓
Service
   ↓
Stream
   ↓
Channel
   ↓
QoS / Timestamp
   ↓
Channel Fabric
   ↓
Radio Scheduler
   ↓
Radio Fabric
   ↓
PHY
   ↓
Antenna
   ↓
Wireless Device
```

---

# 43. Sonuç

NEXSUS Wireless Link, klasik anlamda yeni bir “Bluetooth alternatifi” olarak değil, **NEXSUS sistem mimarisinin kablosuz uzantısı** olarak tasarlanır.

Ana fark:

\[
\boxed{
Device\ Centric
\rightarrow
Service/Stream\ Centric
}
\]

ve:

\[
\boxed{
Single\ Radio
\rightarrow
Radio\ Fabric
}
\]

yaklaşımıdır.

Böylece NEXSUS bilgisayarında:

- klavye,
- fare,
- kulaklık,
- mikrofon,
- 7.1 hoparlör sistemi,
- kamera,
- telefon,
- kablosuz depolama,
- diğer çevre birimleri

tek bir NWL altyapısına bağlanabilir.

Dört bağımsız RF, bu mimarinin ilk fiziksel uygulaması için başlangıç noktasıdır:

\[
\boxed{
1\times2.4GHz + 3\times6GHz
}
\]

Ancak protokol bu sayıya bağımlı değildir.

NWL'nin gerçek hedefi daha yüksek kablosuz hızdan çok:

\[
\boxed{
\text{Paralel iletişim}
+
\text{düşük gecikme}
+
\text{zaman senkronizasyonu}
+
\text{dinamik yönlendirme}
+
\text{RF izolasyonu}
+
\text{System Fabric entegrasyonu}
}
\]

sağlamaktır.

Bu nedenle NWL, NEXSUS içerisinde ayrı bir kablosuz çevre birimi protokolünden ziyade **kablosuz System Fabric** olarak değerlendirilebilir.
----
