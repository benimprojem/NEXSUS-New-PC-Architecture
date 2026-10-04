# NEXSUS Peripheral Interface
## NPI v1.0 — Teknik Tasarım Dokümantasyonu

**Doküman Kodu:** NEXSUS-NPI-1.0  
**Konu:** Kablolu çevre birimi ve harici veri bağlantı mimarisi  
**Statü:** Teknik Tasarım / v1.0  
**Mimari:** NEXSUS System Fabric  
**Bağlantı tipi:** Yüksek hızlı seri diferansiyel bağlantı

---

# 1. Amaç

NEXSUS Peripheral Interface (NPI), NEXSUS bilgisayar mimarisinde klavye, mouse, kamera, mikrofon, kulaklık, harici depolama, telefon, kontrol cihazları, özel çevre birimleri ve gerektiğinde ekran gibi cihazların tek bir ortak bağlantı mimarisi üzerinden sisteme bağlanmasını sağlayan yüksek hızlı seri arayüzdür.

NPI'nin amacı USB'nin mevcut protokolünü kopyalamak değildir.

NPI:

- System Fabric ile doğrudan bütünleşir.
- Cihaz yerine **servis ve kanal** merkezli çalışır.
- Aynı fiziksel bağlantı üzerinde birden fazla bağımsız veri akışını taşıyabilir.
- Trafik önceliğini destekler.
- Düşük gecikmeli kontrol trafiğini büyük veri transferlerinden ayırabilir.
- Hata algılama ve yeniden iletim mekanizmalarına sahiptir.
- Çift yönlü tam veri iletişimi sağlar.
- Gelecekteki daha yüksek hızlı NPI sürümlerine genişletilebilir.

---

# 2. Mimari Konum

NPI, NEXSUS System Fabric'in dış dünyaya açılan kablolu seri uzantısıdır.

```text
                         NEXSUS
                            │
                     SYSTEM FABRIC
                            │
                     NPI CONTROLLER
                            │
                     NPI LINK ENGINE
                            │
                       NPI PHY
                            │
                    NPI CONNECTOR
                            │
                         KABLO
                            │
                    NPI CONNECTOR
                            │
                       NPI PHY
                            │
                    NPI LINK ENGINE
                            │
                     DEVICE CONTROLLER
                            │
                       ÇEVRE BİRİMİ
```

NPI doğrudan System Fabric'e bağlı olduğundan, her veri transferinin CPU tarafından yazılımsal olarak taşınması zorunlu değildir.

Örneğin:

```text
NPI SSD
   │
   ▼
NPI Controller
   │
   ▼
System Fabric
   │
   ▼
Data MOSRAM
```

veya:

```text
NPI Camera
   │
   ▼
NPI Controller
   │
   ▼
FAPU
```

şeklinde doğrudan veri yolları oluşturulabilir.

---

# 3. Temel Tasarım İlkeleri

NPI v1.0 şu temel ilkeler üzerine kuruludur:

1. Seri bağlantı
2. Tam çift yönlü iletişim
3. Diferansiyel sinyal
4. Çoklu lane
5. Dinamik bant genişliği kullanımı
6. Çoklu mantıksal kanal
7. Hizmet tabanlı cihaz modeli
8. QoS ve trafik önceliği
9. CRC tabanlı hata algılama
10. Link-level yeniden iletim
11. Link training
12. Hot-plug
13. Düşük güç durumları
14. Gelecek sürümlere ölçeklenebilirlik

---

# 4. NPI Fiziksel Bağlantı

NPI v1.0 için hedeflenen temel fiziksel bağlantı:

**4 yüksek hızlı diferansiyel çift**

şeklindedir.

Bunlar:

```text
TX0+
TX0-

TX1+
TX1-

RX0+
RX0-

RX1+
RX1-
```

olarak gruplanır.

Dolayısıyla:

```text
                 NEXSUS
                   │
          ┌────────┴────────┐
          │                 │
       TX0/TX1           RX0/RX1
          │                 │
          │    NPI KABLO   │
          └─────────────────┘
                   │
                 DEVICE
```

yapısı oluşur.

Her iki yönde iki lane bulunması nedeniyle bağlantı aynı anda veri gönderebilir ve alabilir.

---

# 5. Lane Yapısı

NPI v1.0:

**2 TX lane + 2 RX lane**

kullanır.

Her lane bağımsız olarak link eğitiminden geçer.

```text
NEXSUS → DEVICE

TX0 ───────────────►
TX1 ───────────────►


DEVICE → NEXSUS

RX0 ◄───────────────
RX1 ◄───────────────
```

Lane'ler gerektiğinde birlikte kullanılır.

Bu nedenle NPI:

- tek lane,
- iki lane,
- dört lane

gibi fiziksel çalışma durumlarını destekleyebilecek şekilde tasarlanır.

Ancak v1.0'ın tam performans modu:

**2 TX + 2 RX**

olacaktır.

---

# 6. NPI v1.0 Hızları

NPI v1.0 için dört bağlantı hızı tanımlanır.

| Mod | Lane hızı | TX toplamı | RX toplamı | Çift yönlü toplam |
|---|---:|---:|---:|---:|
| NPI-10 | 5 GT/s sınıfı | 10 Gbps | 10 Gbps | 20 Gbps |
| NPI-20 | 10 GT/s sınıfı | 20 Gbps | 20 Gbps | 40 Gbps |
| **NPI-40** | **20 GT/s sınıfı** | **40 Gbps** | **40 Gbps** | **80 Gbps** |

Burada önemli bir düzeltme vardır: fiziksel link kapasitesini ifade ederken TX ve RX yönlerini ayrı değerlendirmek gerekir.

Bu nedenle v1.0'ın ana hedefi:

> **40 Gbps TX + 40 Gbps RX = 80 Gbps tam çift yönlü fiziksel kapasite**

olarak tanımlanır.

NPI-10 ve NPI-20 daha düşük hızlı cihazlar, uzun kablolar veya daha düşük güç tüketimi için kullanılabilir.

### Önerilen ana mod

**NPI-40**

NPI v1.0'ın standart yüksek performans modudur.

---

# 7. Neden 160 Gbps Değil?

NPI'nin ilk sürümünde 160 Gbps hedeflenmemektedir.

Bunun nedeni yalnızca bant genişliği değildir.

80 Gbps sınıfında:

- sinyal bütünlüğü,
- konektör kaybı,
- kablo kaybı,
- crosstalk,
- EMI,
- equalization,
- PHY karmaşıklığı

zaten önemli hale gelir.

Mevcut USB4 mimarisi de 80 Gbps sınıfında çalışmakta ve PAM3 gibi gelişmiş fiziksel katman teknikleri kullanmaktadır.

Dolayısıyla NPI v1.0 için:

**80 Gbps toplam fiziksel kapasite → yeterli başlangıç noktası**

olarak kabul edilir.

160 Gbps ve üzeri:

**NPI v2.x / v3.x**

için bırakılır.

---

# 8. PHY Sinyalleşmesi

NPI v1.0 için temel PHY yaklaşımı:

**yüksek hızlı diferansiyel seri sinyal**

olacaktır.

İlk prototip aşamasında:

- NRZ tabanlı PHY
- güçlü equalization
- transmitter pre-emphasis
- receiver CTLE/DFE
- lane deskew
- CRC
- düşük gecikmeli retry

tercih edilmesi planlanır.

PAM4/PAM3 doğrudan zorunlu tutulmaz.

Bunun nedeni NPI v1.0'ın önceliğinin maksimum teorik hızdan ziyade:

**kararlılık + düşük gecikme + üretilebilirlik**

olmasıdır.

Daha yüksek hız sürümlerinde çok seviyeli modülasyon tekrar değerlendirilebilir.

PCIe 6.0 örneğinde 64 GT/s seviyesinde PAM4 ile birlikte FEC, CRC ve sabit boyutlu FLIT yapısının kullanılmasının nedeni de yüksek hızlı bağlantıda hata oranını kontrol altında tutmaktır.

---

# 9. Kablo Mimarisi

NPI kablosu dört yüksek hızlı diferansiyel çift içerir.

Temel yapı:

```text
┌───────────────────────────────────────┐
│             NPI KABLO                 │
│                                       │
│  Pair 0     TX0+ / TX0-              │
│  Pair 1     TX1+ / TX1-              │
│  Pair 2     RX0+ / RX0-              │
│  Pair 3     RX1+ / RX1-              │
│                                       │
│  GND / Shield / Return                │
│                                       │
│  Sideband / Control                   │
│                                       │
└───────────────────────────────────────┘
```

Yüksek hızlı çiftler birbirlerinden fiziksel olarak ayrılmalı ve mümkün olduğunca kontrollü empedans yapısında tutulmalıdır.

---

# 10. Kablo Empedansı

NPI v1.0 için hedef:

**100 Ω diferansiyel empedans**

olarak belirlenir.

Bu değer:

- yüksek hızlı diferansiyel bağlantı,
- PCB routing,
- konektör,
- kablo,
- PHY

arasında ortak bir elektriksel hedef oluşturur.

Gerçek üretim değerleri konektör ve kablo prototipi üzerinde SI/PI simülasyonlarıyla doğrulanacaktır.

---

# 11. Kablo Uzunluğu

NPI v1.0 için ilk tasarım hedefleri:

| Hız | Hedef pasif kablo |
|---|---:|
| NPI-10 | 3 m |
| NPI-20 | 2 m |
| NPI-40 | 1 m |

Bunlar **tasarım hedefidir**, henüz kesin fiziksel sınır değildir.

Aktif kablo veya daha gelişmiş retimer kullanılması halinde daha uzun bağlantılar sonraki aşamada tanımlanabilir.

Amaç:

> Kısa kabloda maksimum performans, uzun kabloda otomatik hız düşürme.

---

# 12. Konektör

NPI'nin konektörü:

- ters takılabilir,
- mekanik olarak dayanıklı,
- yüksek hızlı diferansiyel çiftleri korumalı,
- hot-plug destekli,
- yeterli GND pinine sahip

olmalıdır.

İki seçenek vardır:

### Seçenek A — USB-C mekanik yapı

USB-C benzeri mevcut fiziksel konektör kullanılabilir ancak NPI kendi PHY/link protokolünü çalıştırır.

Avantaj:

- küçük
- çift taraflı
- yaygın mekanik yapı
- mevcut kablo teknolojilerinden yararlanma

### Seçenek B — NEXSUS özgün konektörü

NPI için tamamen yeni fiziksel konektör geliştirilir.

Avantaj:

- pinler tamamen NPI için optimize edilir
- güç ve sinyal dağılımı yeniden tasarlanabilir
- mekanik kilitleme yapılabilir
- gelecekteki yüksek hızlı sürümler için daha iyi ölçeklenebilir

### v1.0 kararı

NPI protokolü **konektörden bağımsız** tasarlanmalıdır.

İlk prototiplerde USB-C sınıfı fiziksel konektör değerlendirilebilir.

Ancak NPI standardı:

**“NPI = USB-C”**

şeklinde tanımlanmaz.

---

# 13. Konektör Pin Grupları

Özgün NPI konektörü için örnek pin gruplaması:

```text
┌──────────────────────────────┐
│ GND                          │
│ TX0+ TX0-                    │
│ TX1+ TX1-                    │
│ RX0+ RX0-                    │
│ RX1+ RX1-                    │
│ GND                          │
│                              │
│ SIDE0                        │
│ SIDE1                        │
│ RESET / WAKE                 │
│ POWER / IDENT                │
│ GND                          │
│ SHIELD                       │
└──────────────────────────────┘
```

Buradaki sideband hatları yüksek hızlı veri taşımaz.

Bunlar:

- cihaz algılama,
- link wake,
- düşük hızlı yönetim,
- güç durumu,
- fiziksel bağlantı durumu

gibi görevlerde kullanılabilir.

---

# 14. Güç ve Veri Ayrımı

NPI veri ve güç bağlantısını destekleyebilir ancak yüksek güç isteyen cihazlarda veri ile güç tamamen aynı fiziksel sınırlar içine zorlanmamalıdır.

Temel yaklaşım:

```text
NPI
│
├── DATA
│
├── CONTROL
│
└── POWER
```

olmalıdır.

NPI'nin yüksek hızlı veri bağlantısı cihazın güç ihtiyacını belirlemez.

Örneğin:

- mouse → düşük güç
- keyboard → düşük güç
- headset → düşük/orta güç
- SSD → orta güç
- kamera → orta güç
- dock → yüksek güç
- harici ekran → ayrı güç gerekebilir

şeklinde farklı profiller tanımlanabilir.

---

# 15. Link Başlatma

NPI cihaz bağlandığında doğrudan veri göndermeye başlamaz.

İlk aşamalar:

```text
DISCONNECTED
     │
     ▼
DETECT
     │
     ▼
PHY TRAINING
     │
     ▼
LANE ALIGN
     │
     ▼
LINK NEGOTIATION
     │
     ▼
DEVICE DISCOVERY
     │
     ▼
SERVICE DISCOVERY
     │
     ▼
ACTIVE
```

---

# 16. PHY Training

PHY training sırasında iki uç:

- desteklenen hızları,
- lane sayısını,
- equalization parametrelerini,
- hata durumunu,
- güç durumunu

belirler.

Örneğin:

```text
Host:
NPI-40 / NPI-20 / NPI-10

Device:
NPI-20 / NPI-10

Result:
NPI-20
```

Bu durumda bağlantı otomatik olarak NPI-20 hızında çalışır.

---

# 17. Servis Tabanlı Cihaz Modeli

NPI'nin en önemli özelliklerinden biri cihaz ile bağlantının aynı şey olarak kabul edilmemesidir.

Mimari:

```text
DEVICE
  │
  ├── SERVICE
  │      │
  │      ├── CHANNEL
  │      ├── CHANNEL
  │      └── CHANNEL
  │
  └── SERVICE
```

Örneğin bir headset:

```text
HEADSET
│
├── AUDIO OUT
├── MICROPHONE
├── CONTROL
└── STATUS
```

Telefon:

```text
PHONE
│
├── AUDIO
├── MICROPHONE
├── CAMERA
├── DATA
├── STORAGE
├── CONTROL
└── APPLICATION
```

tek NPI bağlantısı üzerinden birden fazla servise sahip olabilir.

---

# 18. NPI Kanal Yapısı

Her servis bir veya daha fazla mantıksal kanal kullanabilir.

Temel kanal sınıfları:

| Kanal | Görev |
|---|---|
| CONTROL | Sistem kontrolü |
| STATUS | Durum bilgisi |
| HID | Klavye/mouse vb. |
| AUDIO | Ses |
| MICROPHONE | Mikrofon |
| CAMERA | Kamera |
| DATA | Genel veri |
| STORAGE | Depolama |
| DISPLAY | Görüntü |
| APPLICATION | Özel uygulama servisi |

DISPLAY kanalının bulunması NPI'nin ekran taşıyabileceği anlamına gelir.

Ancak NEXSUS anakartının ana ekran çıkışı **native DisplayPort** olarak kalır.

---

# 19. Trafik Öncelikleri

NPI trafiği önceliklendirilir.

| Öncelik | Trafik |
|---|---|
| P0 | Sistem / acil kontrol |
| P1 | HID / düşük gecikmeli kontrol |
| P2 | Gerçek zamanlı audio |
| P3 | Kamera / interactive data |
| P4 | Normal data |
| P5 | Bulk / background |

Örneğin büyük bir SSD transferi sırasında mouse hareketinin gecikmesi kabul edilmez.

Bu nedenle scheduler:

```text
SSD BULK DATA
████████████████████

MOUSE
        ▲
        │
     hemen ilet
```

şeklinde davranabilir.

---

# 20. Paket Yapısı

NPI veri birimi:

```text
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│ LINK HDR │ CHANNEL  │ SERVICE  │ LENGTH   │ PAYLOAD  │
├──────────┴──────────┴──────────┴──────────┴──────────┤
│                         CRC                          │
└─────────────────────────────────────────────────────┘
```

şeklinde tasarlanır.

Daha ayrıntılı olarak:

```text
LINK HEADER
    │
    ├── Version
    ├── Packet Type
    ├── Priority
    ├── Sequence
    ├── Flags
    └── Length

CHANNEL HEADER
    │
    ├── Device ID
    ├── Service ID
    └── Channel ID

PAYLOAD
    │
    └── Data

CRC
```

---

# 21. Hata Yönetimi

NPI v1.0:

**CRC + Retry**

mekanizmasını kullanır.

```text
TX
 │
 ▼
PACKET
 │
 ▼
RX
 │
 ├── CRC OK ─────► ACCEPT
 │
 └── CRC ERROR
          │
          ▼
        RETRY
```

Gerçek zamanlı trafik için sonsuz retry yapılmaz.

Örneğin audio paketinin artık zamanı geçmişse yeniden gönderilmesi yerine atılması daha doğru olabilir.

Bu nedenle:

**reliable transport**

ile

**real-time transport**

aynı sistem içinde bulunabilir.

---

# 22. Paket Zamanlaması

NPI scheduler paketlere:

- priority
- deadline
- sequence
- stream ID

bilgileri atayabilir.

Bu özellikle:

- audio
- microphone
- camera
- display

gibi sürekli veri akışlarında önemlidir.

---

# 23. Flow Control

Alıcı tarafın tamponu dolduğunda gönderici kontrol edilmelidir.

Temel yapı:

```text
TX BUFFER
    │
    ▼
NPI LINK
    │
    ▼
RX BUFFER
    │
    ▼
DEVICE
```

Alıcı taraf:

```text
READY
PAUSE
RESUME
```

gibi akış kontrol durumları bildirebilir.

Bu mekanizma büyük veri transferlerinde paket kaybını azaltır.

---

# 24. DMA ve System Fabric

NPI'nin NEXSUS'a en önemli entegrasyonlarından biri DMA benzeri doğrudan veri aktarımıdır.

Örneğin:

```text
NPI SSD
   │
   ▼
NPI DMA
   │
   ▼
System Fabric
   │
   ▼
Data MOSRAM
```

CPU:

```text
"Bu veriyi buraya taşı"
```

komutunu başlatabilir.

Fakat:

```text
SSD → NPI → CPU → RAM
```

gibi gereksiz bir veri dolaşımı zorunlu değildir.

Bu NEXSUS System Fabric prensibinin önemli bir parçasıdır.

---

# 25. Adresleme

NPI'da iki adresleme seviyesi bulunur.

### Fabric Address

Cihazın System Fabric üzerindeki konumu.

### NPI Address

Harici NPI cihazının link üzerindeki adresi.

```text
SYSTEM FABRIC ADDRESS
        │
        ▼
NPI CONTROLLER
        │
        ▼
NPI DEVICE ADDRESS
        │
        ▼
SERVICE
        │
        ▼
CHANNEL
```

Böylece fiziksel cihaz adresi ile servis adresi birbirinden ayrılır.

---

# 26. Hot Plug

NPI cihazları sistem çalışırken takılıp çıkarılabilir.

Çıkarma sırasında:

```text
ACTIVE
  │
  ▼
QUIESCE
  │
  ▼
FLUSH
  │
  ▼
DISCONNECT
```

süreci uygulanır.

Depolama cihazlarında veri tamponlarının güvenli şekilde kapatılması gerekir.

---

# 27. Güç Durumları

NPI v1.0 için:

```text
ACTIVE
IDLE
LOW POWER
SLEEP
OFF
```

durumları tanımlanabilir.

Örneğin mouse kullanılmadığında yüksek hızlı PHY tamamen açık tutulmak zorunda değildir.

---

# 28. NPI ve DisplayPort İlişkisi

NPI Display desteği korunur.

Ancak NEXSUS anakartında ana ekran bağlantısı:

**Native DisplayPort**

olacaktır.

```text
                    SYSTEM FABRIC
                         │
              ┌──────────┴──────────┐
              │                     │
        DISPLAY CONTROLLER       NPI CONTROLLER
              │                     │
          DisplayPort             NPI
              │                     │
          Ana ekran          İkincil/özel ekran
```

Bu nedenle NPI'nin yüksek bant genişliğinin tamamının ekran için ayrılması gerekmez.

---

# 29. Kablo İçin Tasarım Hedefleri

NPI v1.0 kablosu için başlangıç hedefleri:

| Parametre | Hedef |
|---|---|
| Diferansiyel çift | 4 |
| TX | 2 lane |
| RX | 2 lane |
| Empedans | 100 Ω diferansiyel |
| Ana hız | 40 Gbps TX + 40 Gbps RX |
| Toplam fiziksel kapasite | 80 Gbps |
| Minimum hız | 10 Gbps sınıfı |
| Kısa kablo | 1 m sınıfı |
| Uzun kablo | Aktif/retimer ile genişletilebilir |
| Hot plug | Evet |
| Shield | Evet |
| EMI kontrolü | Evet |
| GND | Çoklu |
| Sideband | Evet |

---

# 30. Performans Profilleri

NPI v1.0 için üç temel performans profili:

### NPI-10

Düşük maliyetli / düşük güç cihazlar.

Örnek:

- keyboard
- mouse
- basit controller

### NPI-20

Orta performans.

Örnek:

- audio interface
- kamera
- telefon
- normal harici SSD

### NPI-40

Tam performans.

Örnek:

- yüksek hızlı SSD
- profesyonel kamera
- yüksek hızlı dock
- çoklu veri akışı
- yüksek bant genişlikli özel cihazlar

---

# 31. Bant Genişliği Paylaşımı

NPI tek bir cihazın bütün linki işgal etmesini engeller.

Örneğin NPI-40:

```text
                 80 Gbps PHY
                     │
          ┌──────────┼──────────┐
          │          │          │
        SSD         Audio     Camera
       50 Gbps       2 Gbps     8 Gbps
          │          │          │
          └──────────┼──────────┘
                     │
                 Scheduler
```

Gerçek kullanılabilir payload kapasitesi PHY encoding, paket başlıkları, CRC, retry ve diğer protokol overhead'leri nedeniyle teorik 80 Gbps'den daha düşük olacaktır.

Bu nedenle NPI'nin pazarlanabilir hız değeri ile gerçek uygulama throughput'u birbirinden ayrı tutulmalıdır.

---

# 32. Güvenilirlik

NPI v1.0:

- CRC
- sequence number
- retry
- timeout
- link monitoring
- lane error monitoring
- link retraining

mekanizmalarını desteklemelidir.

Uzun süreli hata durumunda:

```text
ACTIVE
   │
ERROR
   │
RETRAIN
   │
RECOVER
   │
ACTIVE
```

veya başarısızlık halinde:

```text
ACTIVE
   │
ERROR
   │
RECOVER FAILED
   │
SAFE DISCONNECT
```

durumu uygulanabilir.

---

# 33. Güvenlik

NPI'nin fiziksel olarak takılabilir olması nedeniyle cihaz kimliği ve yetkilendirme desteklenmelidir.

Cihaz:

- Device ID
- Vendor/Manufacturer ID
- Device Class
- Capability
- Security Capability

bilgilerini sağlayabilir.

Güvenilmeyen cihazların System Fabric'e sınırsız erişimi verilmemelidir.

Özellikle:

```text
NPI Device
     │
     ▼
Device Discovery
     │
     ▼
Capability Check
     │
     ▼
Security Check
     │
     ▼
Service Enable
```

şeklinde bir süreç kullanılabilir.

---

# 34. NPI Controller

NEXSUS tarafındaki NPI Controller'ın temel blokları:

```text
┌─────────────────────────────────────┐
│          NPI CONTROLLER             │
│                                     │
│  Device Manager                     │
│  Service Manager                    │
│  Channel Manager                    │
│  QoS Scheduler                      │
│  DMA Engine                         │
│  Packet Engine                      │
│  CRC / Retry Engine                 │
│  Flow Control                       │
│  Link Manager                       │
│  Power Manager                      │
│  PHY Controller                     │
└─────────────────────────────────────┘
```

NPI Controller doğrudan System Fabric'e bağlanır.

---

# 35. NPI v1.0 Veri Akış Modeli

Genel akış:

```text
Application
     │
     ▼
System Service
     │
     ▼
NPI Service
     │
     ▼
Channel
     │
     ▼
Scheduler
     │
     ▼
Packet Engine
     │
     ▼
NPI PHY
     │
     ▼
Cable
     │
     ▼
Device PHY
```

Ters yönde aynı yapı çalışır.

---

# 36. NPI v1.0 Ana Teknik Özeti

| Özellik | NPI v1.0 |
|---|---|
| Mimari | Seri diferansiyel |
| Yön | Full Duplex |
| Fiziksel lane | 2 TX + 2 RX |
| Ana PHY | NRZ sınıfı |
| Ana hız | 40 Gbps / yön |
| Toplam link | 80 Gbps |
| Düşük hız modu | 10 Gbps sınıfı |
| Orta hız | 20 Gbps sınıfı |
| Empedans | 100 Ω |
| CRC | Evet |
| Retry | Evet |
| Flow Control | Evet |
| QoS | Evet |
| DMA | Evet |
| Hot Plug | Evet |
| Power States | Evet |
| Device Discovery | Evet |
| Service Discovery | Evet |
| Multi-channel | Evet |
| Display | Desteklenir |
| Native ana ekran | DisplayPort |
| Güvenlik | Evet |
| System Fabric | Doğrudan entegrasyon |

---

# 37. v1.0 Sonrası Genişleme

NPI mimarisinin fiziksel ve protokol katmanları gelecekteki hız artışlarına izin vermelidir.

Muhtemel:

```text
NPI v1.0
80 Gbps
   │
   ▼
NPI v1.x
PHY optimizasyonları
   │
   ▼
NPI v2.0
160 Gbps+
   │
   ▼
NPI v3.x
320 Gbps+
```

Bu hız artışlarında konektör ve kablo yeniden tasarlanabilir.

Ancak:

**Device → Service → Channel → Packet**

mantığının korunması hedeflenir.

Böylece işletim sistemi ve uygulama katmanının her yeni PHY sürümünde yeniden tasarlanması gerekmez.

---

# 38. NPI v1.0 Tasarım Kararları

NPI v1.0 için başlangıçta aşağıdaki kararlar alınmıştır:

### Kesin mimari kararlar

- Seri bağlantı
- Full duplex
- Diferansiyel sinyal
- 2 TX + 2 RX lane
- Service/Channel tabanlı iletişim
- QoS
- CRC
- Retry
- Flow control
- Hot plug
- DMA
- System Fabric entegrasyonu
- Display servisinin korunması
- Native DisplayPort'un ana ekran yolu olması

### Tasarım hedefleri

- 80 Gbps toplam fiziksel kapasite
- 40 Gbps/yön
- 100 Ω diferansiyel hat
- 1 m sınıfı yüksek hızlı pasif kablo
- 10/20/40 Gbps çalışma profilleri
- NRZ tabanlı ilk PHY

### Henüz prototiple doğrulanması gerekenler

- kesin konektör pin sayısı
- kesin pin yerleşimi
- kesin sinyal voltajı
- PHY equalization parametreleri
- kablo iletken geometrisi
- maksimum pasif kablo uzunluğu
- konektör insertion loss
- crosstalk sınırı
- EMI sınırı
- gerçek BER hedefi
- gerçek payload throughput
- retimer gereksinimi
- PHY üretim teknolojisi

---

# 39. NPI v1.0 Temel Felsefesi

NPI'nin temel amacı yalnızca yüksek hızlı bir kablo üretmek değildir.

NPI'nin amacı:

> **Harici cihazları NEXSUS System Fabric'in doğal uzantıları haline getirmektir.**

Bu nedenle NPI:

```text
Kablo
  ↓
PHY
  ↓
Link
  ↓
Packet
  ↓
Channel
  ↓
Service
  ↓
System Fabric
```

şeklinde bütünleşik bir mimari oluşturur.

Bu yaklaşım sayesinde NEXSUS'ta klavye, mouse, kamera, SSD, telefon, ses sistemi ve diğer çevre birimleri birbirinden tamamen bağımsız protokoller kullanan cihazlar olmaktan çıkar; aynı NPI altyapısı üzerinde farklı servisler sunan sistem bileşenleri haline gelir.

**NPI v1.0'ın hedefi 80 Gbps'lik bir bağlantı üretmekten daha büyüktür: amaç, harici I/O'yu NEXSUS System Fabric'in bir parçası haline getirmektir.**

---

# NEXSUS Peripheral Interface — NPI v1.0
## Teknik Tasarım Dokümantasyonu

**Doküman Kodu:** NEXSUS-NPI-2026-001  
**Konu:** NEXSUS çevre birimi bağlantı ve iletişim mimarisi  
**Sürüm:** NPI v1.0  
**Statü:** Kavramsal Teknik Tasarım

---

## 1. Amaç

NPI (NEXSUS Peripheral Interface), NEXSUS sisteminin harici ve dahili çevre birimleriyle haberleşmesini sağlayan, USB gibi mevcut bir haberleşme protokolünün üzerine kurulmuş bir katman değildir.

NPI, **NEXSUS tarafından baştan tasarlanan bağımsız bir çevre birimi iletişim mimarisidir.**

NPI'nin fiziksel bağlantısında USB-C tipi konnektör kullanılabilir; ancak USB-C'nin USB 3.x veya USB4 iletişim protokolleri kullanılmaz.

Temel ayrım:

> **USB-C = fiziksel konnektör**  
> **NPI = NEXSUS iletişim sistemi**

Böylece NEXSUS, USB'nin host/device, endpoint, enumeration, transfer tipi ve USB paketleme modeline bağlı kalmadan kendi çevre birimi mimarisini oluşturur.

---

# 2. Temel Mimari

NPI'nin genel yapısı:

```text
                 NEXSUS SYSTEM FABRIC
                         │
                         ▼
                  NPI CONTROLLER
                         │
        ┌────────────────┼────────────────┐
        │                │                │
       PHY              LINK           TRANSPORT
        │                │                │
        └────────────────┼────────────────┘
                         │
                    NPI SERVICE
                         │
                    NPI CHANNEL
                         │
                    USB-C PHY
                         │
                    USB-C CONNECTOR
                         │
                       KABLO
                         │
                    USB-C CONNECTOR
                         │
                    USB-C PHY
                         │
                    NPI LINK
                         │
                    NPI SERVICE
                         │
                  SYSTEM FABRIC
```

USB-C konnektörün ötesindeki bütün iletişim mimarisi NEXSUS tarafından tanımlanır.

---

# 3. USB-C'nin NPI İçindeki Rolü

USB-C, NPI'de yalnızca fiziksel bağlantı arayüzüdür.

NPI:

- USB 3.x kullanmaz.
- USB4 kullanmaz.
- USB enumeration kullanmaz.
- USB endpoint modelini kullanmaz.
- USB transfer tiplerini kullanmaz.
- USB class mimarisine bağlı değildir.
- USB4 tunneling kullanmaz.
- USB host/device iletişim modelini temel almaz.

Bunun yerine NPI kendi:

- PHY
- Link
- Transport
- Packet
- Service
- Channel
- QoS
- Discovery
- Flow Control
- Error Control

mekanizmalarını kullanır.

Bu nedenle NPI'nin USB ile ilişkisi esas olarak **fiziksel konnektör form faktörü** seviyesindedir.

---

# 4. NEXSUS NPI PHY

NPI'nin fiziksel katmanı NEXSUS tarafından tasarlanır.

PHY'nin görevleri:

- TX/RX sinyal üretimi
- diferansiyel iletişim
- sinyal bütünlüğü kontrolü
- link training
- kanal kalibrasyonu
- hız belirleme
- hata algılama
- lane yönetimi
- gerekli durumlarda lane bonding

PHY'nin gerçek elektriksel parametreleri NPI'nin sonraki fiziksel tasarım aşamasında belirlenecektir.

İlk mimari aşamada PHY'nin USB 3.x veya USB4 PHY olmak zorunda olmadığı kabul edilir.

---

# 5. USB-C Pinlerinin Kullanımı

USB-C'nin fiziksel pin yapısı NPI tarafından yeniden yorumlanabilir.

NPI'nin ihtiyaç duyduğu:

- TX/RX çiftleri
- güç
- toprak
- ekranlama
- gerekli kontrol/sinyal hatları

NPI PHY tasarımına göre kullanılacaktır.

USB-C konnektörün fiziksel simetrisi ve ters takılabilir yapısı korunurken, iletişim protokolü NPI'ye ait olacaktır.

Pinlerin kesin görev dağılımı NPI PHY tasarımında belirlenecektir.

---

# 6. NPI Kablo Mimarisi

NEXSUS, USB-C konnektörünü kullanırken kabloyu USB standartlarının zorunlu bir parçası olarak kabul etmek zorunda değildir.

NPI için ayrıca NEXSUS kablo spesifikasyonları tanımlanabilir.

Örneğin:

```text
NEXSUS NPI Cable
────────────────────────────
USB-C mekanik konnektör
NEXSUS iletken yapısı
NEXSUS empedans gereksinimi
NEXSUS ekranlama
NEXSUS uzunluk sınırı
NEXSUS sinyal bütünlüğü
NEXSUS maksimum veri hızı
```

Kablo sınıfları ilerleyen aşamada örneğin:

```text
NPI-40
NPI-80
NPI-160
NPI-320
```

şeklinde tanımlanabilir.

Bu değerler **NPI v1.0 için henüz kesinleştirilmiş hızlar değildir**; örnek sınıflandırmadır.

---

# 7. Üçüncü Taraf USB-C Kablolar

NPI'nin USB-C fiziksel konnektör kullanması, son kullanıcıya kullanılan her USB-C kabloyla belirli bir NPI hızının garanti edildiği anlamına gelmez.

NEXSUS:

> **NEXSUS tarafından belirtilen kablo özelliklerini sağlayan kablolarla belirtilen maksimum NPI hızını garanti eder.**

Diğer USB-C kablolar fiziksel olarak çalışabilir; ancak NPI bağlantısı:

- daha düşük hızda çalışabilir,
- farklı bir link modu seçebilir,
- sinyal kalitesi nedeniyle bağlantıyı kuramayabilir,
- veya NEXSUS tarafından desteklenmeyen bir kablo olarak değerlendirilebilir.

Bu nedenle NEXSUS'un üçüncü taraf USB-C kablolar için maksimum performans garantisi vermesi gerekmez.

---

# 8. Dinamik Link Hızı

NPI bağlantısı sabit tek bir hız kullanmak zorunda değildir.

Bağlantı sırasında:

```text
Cable Detect
      │
      ▼
PHY Detection
      │
      ▼
Signal Integrity Test
      │
      ▼
Link Training
      │
      ▼
Capability Detection
      │
      ▼
Maximum Stable Rate
      │
      ▼
NPI ACTIVE
```

işlemi gerçekleştirilebilir.

Örneğin:

```text
NPI PHY          Kablo
  │                │
  │── test ───────>│
  │<─ response ───│
  │                │
  │ 160 Gb/s       │
  │──── başarısız ─│
  │                │
  │ 80 Gb/s        │
  │──── başarılı ──│
  │                │
  ▼
NPI = 80 Gb/s
```

Böylece fiziksel bağlantının izin verdiği en yüksek kararlı hız seçilir.

---

# 9. NPI Link Katmanı

PHY'nin üzerinde NPI Link katmanı bulunur.

Görevleri:

- bağlantı kurulması
- lane yönetimi
- link training sonrası aktivasyon
- paket sınırlarının belirlenmesi
- hata algılama
- yeniden gönderim
- akış kontrolü
- bağlantı durumu

Link durumları:

```text
DISCONNECTED
      ↓
DETECT
      ↓
PHY TRAINING
      ↓
LANE ALIGNMENT
      ↓
LINK NEGOTIATION
      ↓
DEVICE DISCOVERY
      ↓
SERVICE DISCOVERY
      ↓
ACTIVE
```

---

# 10. NPI Transport Katmanı

NPI Transport, USB transport yerine NEXSUS'un kendi veri taşıma mekanizmasıdır.

Transport katmanı:

- paketlerin taşınması
- akışların ayrılması
- kanal yönetimi
- sıra numarası
- zaman bilgisi
- hata yönetimi
- flow control
- QoS

işlevlerini gerçekleştirir.

Temel yapı:

```text
NPI PHY
   ↓
NPI Link
   ↓
NPI Transport
   ↓
NPI Channel
   ↓
NPI Service
   ↓
Device
```

---

# 11. NPI Paket Yapısı

İlk kavramsal paket yapısı:

```text
┌────────────┬────────────┬───────────┬─────────┬───────┐
│ Link Header│ Service ID │ Channel ID│ Payload │ CRC   │
└────────────┴────────────┴───────────┴─────────┴───────┘
```

Daha sonraki tasarım aşamasında:

- sequence number
- timestamp
- packet type
- priority
- length
- flags
- routing information

gibi alanlar eklenebilir.

Paket formatı NPI v1.0 ISA/protokol dondurma aşamasında kesinleştirilecektir.

---

# 12. Cihaz Modeli

NPI'de temel birim yalnızca cihaz değildir.

NPI'nin temel mantığı:

```text
DEVICE
   │
   ├── SERVICE
   │      │
   │      ├── CHANNEL
   │      ├── CHANNEL
   │      └── CHANNEL
   │
   └── SERVICE
          │
          ├── CHANNEL
          └── CHANNEL
```

Örneğin bir kulaklık:

```text
Headset
 ├── Audio Output
 ├── Microphone
 ├── Control
 └── Status
```

Tek fiziksel cihaz, birden fazla bağımsız NPI servisine sahip olabilir.

---

# 13. NPI Servisleri

Temel servis türleri:

- CONTROL
- STATUS
- HID
- AUDIO
- MICROPHONE
- CAMERA
- DATA
- STORAGE
- DISPLAY
- APPLICATION

Bunlar NPI'nin USB class'larına bağımlı değildir.

NEXSUS kendi servis tanımlama sistemini oluşturur.

---

# 14. NPI Kanal Modeli

Her servis bir veya daha fazla kanal kullanabilir.

Örneğin kamera:

```text
Camera
  │
  ├── CONTROL
  ├── STATUS
  ├── VIDEO
  └── METADATA
```

Ses cihazı:

```text
Audio Device
  │
  ├── AUDIO OUT
  ├── AUDIO IN
  ├── CONTROL
  └── STATUS
```

Bu yapı NPI'nin farklı veri türlerini aynı fiziksel bağlantı üzerinden bağımsız olarak taşımasını sağlar.

---

# 15. QoS

NPI farklı veri türlerine farklı öncelikler verebilir.

Örnek:

| Öncelik | Trafik |
|---|---|
| P0 | Sistem kontrolü |
| P1 | Gerçek zamanlı kontrol |
| P2 | Audio / Video |
| P3 | Etkileşimli veri |
| P4 | Normal veri |
| P5 | Arka plan / büyük veri |

Örneğin kamera görüntüsü ile dosya transferi aynı bağlantıyı kullanıyorsa dosya transferi gerçek zamanlı görüntünün önüne geçmemelidir.

---

# 16. Gerçek Zamanlı Veri

Audio, video ve benzeri akışlarda paketlerin yalnızca sırasına değil zamanlamasına da önem verilir.

Örneğin:

```text
Packet
 ├── Stream ID
 ├── Sequence
 ├── Timestamp
 ├── Channel
 └── Payload
```

Geç kalan gerçek zamanlı paketlerin sonsuza kadar yeniden gönderilmesi yerine paket düşürülebilir.

Bu yaklaşım:

```text
Latency
   ↓
Predictable
   ↓
Real-Time
```

hedefini destekler.

---

# 17. Hata Yönetimi

NPI fiziksel ve mantıksal hataları algılamalıdır.

Temel mekanizmalar:

- CRC
- sequence kontrolü
- link error detection
- retry
- timeout
- flow control

Ancak bütün veri türleri aynı hata davranışını kullanmaz.

Örneğin:

```text
Mouse event
    → retry

Dosya
    → retry

SSD data
    → retry

Audio packet
    → deadline kontrolü
    → geç kaldıysa drop
```

---

# 18. System Fabric Entegrasyonu

NPI'nin en önemli özelliklerinden biri NEXSUS System Fabric ile doğrudan bütünleşmesidir.

Veri her zaman CPU üzerinden geçirmek zorunda değildir.

Örneğin:

```text
NPI SSD
   │
   ▼
NPI Controller
   │
   ▼
System Fabric
   │
   ▼
Data MOSRAM
```

ve:

```text
NPI Camera
   │
   ▼
NPI Controller
   │
   ▼
System Fabric
   │
   ▼
FAPU
```

mümkündür.

Böylece CPU:

> **her çevre birimi transferinin zorunlu veri taşıyıcısı olmaktan çıkar.**

---

# 19. DMA ve Doğrudan Veri Yolları

NPI Controller, System Fabric üzerinden DMA benzeri doğrudan veri aktarım mekanizmalarını kullanabilir.

Örnek:

```text
External SSD
     │
     ▼
 NPI Controller
     │
     ▼
 System Fabric
     │
     ▼
Data MOSRAM
```

CPU yalnızca:

```text
"Şu veriyi şu adrese aktar."
```

gibi kontrol işlemini gerçekleştirebilir.

Verinin kendisi CPU register'larından geçmek zorunda değildir.

---

# 20. NPI Adresleme

NPI'de iki adresleme seviyesi bulunabilir:

### NPI Device Address

Fiziksel NPI bağlantısı üzerindeki cihazın tanımlanması.

### Fabric Address

Cihazın NEXSUS System Fabric üzerindeki erişim adresi.

Örnek:

```text
NPI Device
     ↓
NPI Address
     ↓
NPI Controller
     ↓
Fabric Address
     ↓
System Fabric
```

---

# 21. NPI Port Mimarisi

NPI fiziksel port sayısı ile NPI domain sayısı aynı şey değildir.

Bir NPI domain birden fazla fiziksel USB-C portunu yönetebilir.

```text
             NPI-A
          ┌────┼────┐
          │    │    │
        USB-C USB-C USB-C
```

Bu yapı **Shared NPI** olarak adlandırılır.

---

# 22. Shared NPI

Shared NPI'de bir NPI controller/domain birden fazla fiziksel USB-C bağlantısını yönetebilir.

Örneğin:

```text
NPI-A
 │
 ├── USB-C 1 → Keyboard
 ├── USB-C 2 → Mouse
 └── USB-C 3 → Headset
```

Bütün cihazlar aynı NPI domainini paylaşabilir.

NPI Scheduler gerektiğinde kaynakları dinamik olarak dağıtır.

---

# 23. Dedicated High-Bandwidth NPI

Yüksek bant genişliği gerektiren cihazlar için bağımsız NPI kaynakları kullanılabilir.

Bu port:

> **Dedicated High-Bandwidth NPI Port**

olarak tanımlanır.

Port belirli bir cihaz türüne özel değildir.

Örneğin:

```text
Dedicated NPI
     │
     ├── External SSD
     ├── Camera
     ├── Capture Device
     ├── Display
     ├── Network Device
     └── başka yüksek bant genişlikli cihaz
```

Kullanıcı portu hiçbir zaman kullanmayabilir; ancak kullanıldığında diğer NPI bağlantılarından bağımsız bir veri yolu sağlayabilir.

---

# 24. Minimum NPI Yapısı

NEXSUS anakartının temel tasarımında en az:

- 3 bağımsız harici NPI domaini
- 1 bağımsız dahili NPI bağlantı/domaini

bulunması hedeflenir.

Fiziksel USB-C portlarının sayısı bundan daha fazla olabilir.

Örnek:

```text
                 SYSTEM FABRIC
                       │
          ┌────────────┼────────────┐
          │            │            │
        NPI-A         NPI-B        NPI-C
       Shared        Shared       Shared
        │ │ │         │ │ │        │ │
      USB-C ...     USB-C ...    USB-C ...

                       │
                 NPI-D Internal
                       │
                Internal USB-C
                / NPI Device
```

Buna ek olarak yüksek bant genişliği gereksinimleri için Dedicated NPI domainleri eklenebilir.

---

# 25. Dahili NPI

NPI yalnızca anakartın arka panelindeki bağlantılar için değildir.

Dahili cihazlar da NPI kullanabilir.

Örneğin:

```text
Internal Camera
      │
      ▼
Internal NPI
      │
      ▼
System Fabric
```

veya:

```text
Internal Module
      │
      ▼
Internal NPI
      │
      ▼
System Fabric
```

Bu yapı anakart üzerindeki çevre birimlerinin de ortak NPI mimarisini kullanmasını sağlar.

---

# 26. NPI Display

NPI Display desteği korunur.

Ancak NEXSUS'un ana ekran bağlantısı için native DisplayPort kullanılır.

```text
Main Display
     │
     ▼
Display Controller
     │
     ▼
DisplayPort
```

NPI Display ise:

```text
NPI
 │
 ▼
USB-C
 │
 ▼
External Display
```

şeklinde ikincil veya özel ekran bağlantıları için kullanılabilir.

Dolayısıyla:

> **Native DisplayPort = ana ekran mimarisi**  
> **NPI Display = harici/ikincil ekran desteği**

---

# 27. NPI Kamera

Kamera gibi sürekli veri üreten cihazlar NPI'nin yüksek bant genişlikli servislerinden yararlanabilir.

```text
Camera
  │
  ▼
NPI Video Stream
  │
  ▼
NPI Controller
  │
  ▼
System Fabric
  │
  ▼
FAPU / Data MOSRAM
```

CPU'nun her görüntü paketini işlemesi gerekmez.

---

# 28. Hot Plug

NPI cihazları sistem çalışırken bağlanıp çıkarılabilir.

Temel süreç:

```text
CONNECT
   ↓
DETECT
   ↓
PHY TRAINING
   ↓
LINK
   ↓
DEVICE DISCOVERY
   ↓
SERVICE DISCOVERY
   ↓
ACTIVE
```

Çıkarma:

```text
DEVICE REMOVED
      ↓
SERVICE RELEASE
      ↓
CHANNEL RELEASE
      ↓
LINK RELEASE
```

---

# 29. Güç

USB-C fiziksel bağlantısı güç taşımak için de kullanılabilir.

Ancak güç mimarisi NEXSUS tarafından tanımlanmalıdır.

NPI güç yönetimi:

- düşük güç cihazları
- normal çevre birimleri
- yüksek güç cihazları
- güç sınırları
- aşırı akım koruması
- güç durumları

ile System Control Processor ve anakart güç yönetimiyle birlikte çalışabilir.

USB Power Delivery protokolünün NPI tarafından kullanılacağı varsayılmaz.

---

# 30. Güvenlik

NPI cihaz keşfi sırasında cihazın kimliği ve yetenekleri belirlenebilir.

Örneğin:

```text
Device ID
     ↓
Device Authentication
     ↓
Capability Discovery
     ↓
Service Discovery
     ↓
Permission
     ↓
ACTIVE
```

Gerekli durumlarda cihaz bazında:

- güvenilirlik
- erişim izni
- veri türü
- güvenlik seviyesi

belirlenebilir.

---

# 31. NPI Controller

NPI Controller'ın temel blokları:

```text
┌───────────────────────────────┐
│         NPI CONTROLLER        │
│                               │
│ Device Manager                │
│ Service Manager               │
│ Channel Manager               │
│ QoS Scheduler                 │
│ DMA / Fabric Engine           │
│ Packet Engine                 │
│ CRC / Error Control           │
│ Flow Control                  │
│ Link Manager                  │
│ PHY Controller                │
│ Power Manager                 │
└───────────────────────────────┘
```

NPI Controller System Fabric'e doğrudan bağlanır.

---

# 32. NPI ve SCP

NPI ile SCP'nin görevleri ayrıdır.

### NPI

Veri iletişimi ve çevre birimi bağlantısı.

### SCP

Sistem yönetimi:

- güç
- reset
- thermal management
- boot
- board management
- cihaz güç durumları
- sistem güvenliği

Bu nedenle SCP NPI veri trafiğinin merkezi işlemcisi değildir.

---

# 33. NPI ve CPU

CPU:

- cihazları yönetebilir
- servisleri başlatabilir
- veri işleme yapabilir
- uygulama seviyesinde çevre birimlerini kullanabilir

ancak fiziksel veri transferlerinin tamamında zorunlu aracı değildir.

Örnek:

```text
CPU
 │
 │ command
 ▼
NPI Controller
 │
 ▼
System Fabric
 │
 ▼
Data MOSRAM
```

Verinin kendisi:

```text
NPI → Fabric → Memory
```

yolundan ilerleyebilir.

---

# 34. NPI'nin Katmanları

NPI'nin genel mimarisi:

```text
┌───────────────────────┐
│ Application / OS      │
├───────────────────────┤
│ NPI Service           │
├───────────────────────┤
│ NPI Channel           │
├───────────────────────┤
│ NPI Transport         │
├───────────────────────┤
│ NPI Link              │
├───────────────────────┤
│ NEXSUS PHY            │
├───────────────────────┤
│ USB-C Connector       │
└───────────────────────┘
```

Burada USB-C yalnızca en alt fiziksel bağlantı elemanıdır.

---

# 35. NPI'nin USB'den Bağımsızlığı

NPI'nin amacı USB'yi yeniden uygulamak değildir.

NPI kendi:

- bağlantı modeli
- cihaz modeli
- servis modeli
- kanal modeli
- paket modeli
- QoS modeli
- hata modeli
- DMA modeli
- fabric yönlendirme modeli

üzerine kuruludur.

USB-C yalnızca fiziksel bağlantı avantajından yararlanmak için seçilmiştir.

Böylece NEXSUS'un gelecekteki gelişimi USB protokolünün gelişiminden bağımsız kalabilir.

---

# 36. Kablo ve Performans Garantisi Politikası

NEXSUS için iki farklı kablo kategorisi bulunabilir.

### NEXSUS Sertifikalı Kablo

Belirli NPI hızları için test edilmiş kablo.

Örneğin:

```text
NPI-80
→ 80 Gb/s sınıfı

NPI-160
→ 160 Gb/s sınıfı
```

### Genel USB-C Kablo

Fiziksel olarak kullanılabilir olabilir.

Ancak:

> **NEXSUS bu kablolarla belirli bir maksimum NPI performansı garanti etmez.**

Bu ayrım son kullanıcı beklentisini açık biçimde yönetir.

---

# 37. NPI Portlarının Ölçeklenebilirliği

NPI fiziksel port sayısı sabit olmak zorunda değildir.

Örneğin bir anakart:

```text
4 USB-C
```

ile başlayabilir.

Daha geniş bir sistem:

```text
8 USB-C
12 USB-C
16 USB-C
```

veya daha fazlasına sahip olabilir.

Burada önemli olan fiziksel konnektör sayısından çok:

> **bağımsız NPI domainlerinin ve toplam fabric bant genişliğinin yeterli olmasıdır.**

---

# 38. Örnek NEXSUS Anakart Yapısı

```text
                    NEXSUS SYSTEM FABRIC
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
      NPI-A                NPI-B                NPI-C
      Shared              Shared               Shared
        │                    │                    │
    USB-C × 3            USB-C × 3            USB-C × 2

                             │
                    Dedicated NPI
                             │
                         USB-C × 1

                             │
                     Internal NPI
                             │
                       Internal I/O
```

Bütün NPI domainleri System Fabric'e bağlanır.

---

# 39. Veri Akışı Örnekleri

### Klavye

```text
Keyboard
   ↓
USB-C
   ↓
NPI
   ↓
HID Service
   ↓
System Fabric
   ↓
CPU
```

### SSD

```text
External SSD
   ↓
USB-C
   ↓
NPI
   ↓
Storage Service
   ↓
System Fabric
   ↓
Data MOSRAM / M-SSD
```

### Kamera

```text
Camera
   ↓
USB-C
   ↓
NPI
   ↓
Video Service
   ↓
System Fabric
   ↓
FAPU
```

### Harici ekran

```text
External Display
   ↑
NPI Display
   ↑
USB-C
   ↑
NPI
   ↑
System Fabric
```

Ana ekran ise doğrudan DisplayPort kullanır.

---

# 40. NPI'nin Temel Tasarım İlkeleri

1. **USB-C yalnızca fiziksel konnektördür.**
2. **NPI iletişim protokolü tamamen NEXSUS'a aittir.**
3. **USB 3.x veya USB4 NPI'nin zorunlu transport katmanı değildir.**
4. **NEXSUS kendi PHY'sini tasarlayabilir.**
5. **NEXSUS kendi kablo gereksinimlerini belirleyebilir.**
6. **Üçüncü taraf USB-C kablolarda maksimum NPI hız garantisi verilmez.**
7. **NEXSUS sertifikalı kablolar belirli NPI hızları için garanti sağlayabilir.**
8. **Link hızı bağlantı koşullarına göre dinamik olarak belirlenebilir.**
9. **Bir NPI domaini birden fazla fiziksel USB-C portunu yönetebilir.**
10. **Yüksek bant genişliği için Dedicated NPI kullanılabilir.**
11. **Ana ekran için native DisplayPort kullanılır.**
12. **NPI Display ikincil/harici ekranlar için desteklenir.**
13. **NPI doğrudan System Fabric'e bağlanır.**
14. **CPU bütün veri transferlerinde zorunlu aracı değildir.**
15. **DMA ve doğrudan Fabric yolları desteklenir.**
16. **Cihaz yerine servis ve kanal merkezli mimari kullanılır.**
17. **QoS trafik türüne göre uygulanır.**
18. **Gerçek zamanlı trafik ile bulk veri birbirinden ayrılır.**
19. **NPI fiziksel port sayısından bağımsız olarak ölçeklenebilir.**
20. **NPI, USB protokolünün gelecekteki değişimlerinden bağımsızdır.**

---

# 41. Sonuç

NPI v1.0'ın temel yaklaşımı artık:

```text
              NEXSUS NPI
                   │
          ┌────────┴────────┐
          │                 │
     NEXSUS PROTOCOL    NEXSUS PHY
          │                 │
          └────────┬────────┘
                   │
                USB-C
             fiziksel form
                   │
                 Kablo
```

şeklindedir.

Bu mimaride NEXSUS, USB teknolojisini yeniden uygulamaya çalışmaz.

USB-C'nin:

- yaygın fiziksel formunu,
- ters takılabilir konnektör yapısını,
- mekanik ekosistemini

kullanırken iletişimin geri kalanını kendisi tasarlar.

Sonuç olarak NPI:

> **USB-C konnektörü kullanan, fakat iletişim mimarisi USB'den bağımsız olan NEXSUS'a özgü çevre birimi iletişim sistemidir.**

Bu yaklaşım NEXSUS'un PHY'den System Fabric'e kadar bütün veri yolunu kendi ihtiyaçlarına göre optimize etmesine olanak verir.

----


Evet. Burada artık NEXSUS'un klasik PC'den en fazla ayrılacağı iki yüksek hızlı bağlantıyı birlikte düşünmek gerekiyor. PCIe bugün bu işi çok iyi yapıyor; örneğin PCIe 7.0 x16 için 128 GT/s ve 512 GB/s çift yönlü bant genişliği tanımlıyor. Dolayısıyla bizim hedefimiz yalnızca “PCIe'den daha hızlı” olmak değil, **GPU ve diğer genişletme cihazlarının System Fabric'e nasıl bağlandığını yeniden tasarlamak** olmalı. [PCI-SIG](https://pcisig.com/specifications/pcie-70-specification-version-03-now-available-members?utm_source=chatgpt.com)

## 1. NEI — NEXSUS Expansion Interface

Bence genişletme kartları için isim:

> **NEI — NEXSUS Expansion Interface**

olsun.

NEI'nin temel fikri:

```text
                    NEXSUS SYSTEM FABRIC
                             │
                 ┌───────────┴───────────┐
                 │                       │
              NEI Root               NEI Root
                 │                       │
          ┌──────┴──────┐          ┌─────┴─────┐
          │             │          │           │
        GPU          Accelerator   NIC       Capture
```

Burada **NEI bir I/O portu değil, doğrudan genişletme mimarisi**.

---

# 2. Neden PCIe modelini aynen almıyoruz?

PCIe'nin temel başarısı cihazları ortak bir yüksek hızlı I/O mimarisine bağlamak. Ancak NEXSUS'ta zaten:

```text
CPU
FAPU
NPU
MOSRAM
M-SSD
NPI
SCP
```

aynı **System Fabric** içerisinde.

Dolayısıyla GPU'yu şöyle bağlamak gerekmiyor:

```text
GPU
 ↓
PCIe
 ↓
CPU / Root Complex
 ↓
Memory
```

Bunun yerine:

```text
                 SYSTEM FABRIC
              /       |        \
             /        |         \
           CPU       FAPU       GPU
             \        |         /
              \       |        /
               Data MOSRAM
```

GPU artık CPU'nun "çevre cihazı" olmaktan çıkıp **System Fabric üzerinde doğrudan bir hesaplama düğümü** haline geliyor.

Bu, NEXSUS'un asıl farkı olabilir.

---

# 3. NEI'nin üç temel yolu

NEI'de üç farklı trafik sınıfı düşünelim:

```text
NEI
 │
 ├── CONTROL
 │
 ├── DATA
 │
 └── MEMORY
```

### CONTROL

GPU'nun:

- komutları
- durum bilgisi
- interrupt/event
- konfigürasyon

### DATA

Normal veri transferleri.

### MEMORY

Doğrudan bellek erişimi.

Özellikle sonuncusu önemli.

---

# 4. GPU → Data MOSRAM

Klasik modelde CPU'nun veya sistem belleğinin etrafında bir PCIe DMA mimarisi bulunur.

NEXSUS'ta:

```text
GPU
 │
 │ NEI
 ▼
System Fabric
 │
 ▼
Data MOSRAM
```

GPU doğrudan Data MOSRAM'a erişebilir.

Tersi de mümkün:

```text
Data MOSRAM
     │
     ▼
System Fabric
     │
     ▼
GPU
```

CPU bu veri yolunda zorunlu değildir.

---

# 5. GPU'nun kendi belleği

Burada önemli bir karar var.

İlk aşamada GPU'nun kendi VRAM'i olabilir:

```text
GPU
 │
 ├── Local VRAM
 │
 └── NEI
       │
       ▼
  System Fabric
       │
       ▼
  Data MOSRAM
```

Ancak NEXSUS mimarisinin ileride şu modeli desteklemesi daha ilginç:

```text
             Data MOSRAM
                  │
       ┌──────────┼──────────┐
       │          │          │
      CPU        FAPU       GPU
```

Yani ortak yüksek hızlı sistem belleği.

GPU için özel VRAM gereksinimi performans testleriyle belirlenecek.

Bunu şimdilik **açık bırakmak** doğru.

---

# 6. NEI fiziksel bağlantısı

Burada NPI'den tamamen farklı davranmalıyız.

NPI:

```text
USB-C
  │
  ▼
NPI PHY
```

NEI ise:

```text
Expansion Card
      │
      ▼
NEI PHY
      │
      ▼
NEI Controller
      │
      ▼
System Fabric
```

Fiziksel konnektörün de **USB-C olması gerekmiyor**.

Çünkü burada:

- çok daha fazla sinyal
- çok daha yüksek bant genişliği
- kartın mekanik olarak sabitlenmesi
- güç
- soğutma
- çok sayıda lane

gerekiyor.

Dolayısıyla NEI için **özel edge connector** tasarlamak mantıklı.

---

# 7. Kart bağlantısı

Kabaca:

```text
        NEXSUS ANAKART

┌────────────────────────────────────────────┐
│                                            │
│              SYSTEM FABRIC                │
│                    │                       │
│              NEI CONTROLLER               │
│                    │                       │
│════════════════════╪═══════════════════════│
│                    │                       │
│                 NEI SLOT                  │
│════════════════════╪═══════════════════════│
│                    │                       │
└────────────────────┼───────────────────────┘
                     │
                     │ Edge Connector
                     │
              ┌──────┴──────┐
              │ Expansion   │
              │    Card     │
              │             │
              │ GPU / FAPU  │
              │ NIC / etc.  │
              └─────────────┘
```

---

# 8. Lane yapısı

Burada henüz hız rakamını dondurmayalım.

Örneğin:

```text
NEI ×4
NEI ×8
NEI ×16
NEI ×32
```

gibi fiziksel lane seçenekleri olabilir.

Ama PCIe'deki x16'yı kopyalamak zorunda değiliz.

Örneğin NEI'nin fiziksel lane yapısı:

```text
TX/RX
TX/RX
TX/RX
TX/RX
...
```

olabilir.

Daha sonra PHY teknolojisine göre:

- NRZ
- PAM4
- daha ileri modülasyon

değerlendirilebilir.

PCIe 6/7 gibi yüksek hızlı sistemlerde PAM4 ve FEC/CRC kullanılması, bizim de yüksek hızlarda sinyal bütünlüğü ve hata düzeltme katmanlarını baştan hesaba katmamız gerektiğini gösteriyor. [PCI-SIG](https://pcisig.com/pci-express-6.0-specification?utm_source=chatgpt.com)

---

# 9. NEI'nin en önemli farkı: Fabric-native

Bence burada özel olarak şu kavramı tanımlayabiliriz:

> **Fabric-Native Device**

Bir GPU NEI üzerinden bağlandığında yalnızca "PCIe cihazı" değildir.

System Fabric üzerinde:

```text
GPU
 │
 ├── Compute Endpoint
 ├── Memory Endpoint
 ├── DMA Endpoint
 ├── Control Endpoint
 └── Event Endpoint
```

olarak görünür.

Aynı yapı FAPU veya başka hızlandırıcılar için de kullanılabilir.

---

# 10. Örneğin GPU görüntü üretirken

Klasik yaklaşım:

```text
CPU
 │
 ▼
GPU
 │
 ▼
VRAM
 │
 ▼
Display
```

NEXSUS'ta:

```text
                 System Fabric
                      │
          ┌───────────┼───────────┐
          │           │           │
        CPU          GPU       Display
                      │
                     NEI
                      │
                   VRAM
```

Hatta GPU çıktısı doğrudan Display Controller'a aktarılabilir:

```text
GPU
 │
 ▼
System Fabric
 │
 ▼
Display Controller
 │
 ▼
DisplayPort
```

CPU görüntü verisini taşımak zorunda değildir.

---

# 11. GPU → FAPU

Bu da önemli.

```text
GPU
 │
 ▼
System Fabric
 │
 ▼
FAPU
```

ve:

```text
FAPU
 │
 ▼
System Fabric
 │
 ▼
GPU
```

mümkün olur.

Yani GPU ve FAPU birbirlerinin doğrudan veri kaynağı olabilir.

Bu, klasik CPU-merkezli mimariden daha farklı bir yapı oluşturuyor.

---

# 12. Birden fazla genişletme kartı

NEI tek kartla sınırlı olmamalı.

Örneğin:

```text
                 SYSTEM FABRIC
                       │
          ┌────────────┼────────────┐
          │            │            │
        NEI-0        NEI-1        NEI-2
          │            │            │
         GPU          NIC         FAPU
```

Her NEI slotunun bağımsız veya paylaşılmış Fabric bant genişliği olabilir.

Bu noktada **slot sayısından daha önemli olan toplam Fabric kapasitesi**.

---

# 13. NEI Switch / Router

İleride daha fazla kart gerektiğinde:

```text
System Fabric
      │
      ▼
  NEI Switch
   │   │   │
   ▼   ▼   ▼
 GPU  GPU  NIC
```

yapısı da mümkün.

Ama ilk NEXSUS sisteminde bunu zorunlu hale getirmeyelim.

İlk hedef:

> **Doğrudan Fabric bağlantılı NEI slotları.**

---

# 14. NEI ile NPI arasındaki kesin ayrım

| Özellik | NPI | NEI |
|---|---|---|
| Amaç | Çevre birimleri | Genişletme kartları |
| Konnektör | USB-C | Özel edge connector |
| CPU bağımlılığı | Yok | Yok |
| System Fabric | Evet | Evet |
| GPU | Hayır | Evet |
| Kamera | Evet | Gerekirse | 
| SSD | Harici | Genişletme kartı olarak mümkün |
| NIC | Mümkün | Yüksek performanslı NIC |
| FAPU | Hayır/özel | Evet |
| Bant genişliği | Yüksek | Çok yüksek |
| Fiziksel yapı | Kablo | Kart/slot |
| Hot plug | Evet | İlk sürümde şart değil |

---


# NEI v1.0 — Fiziksel ve Mantıksal Mimari

## 1. Temel yapı

```text
                    NEXSUS SYSTEM FABRIC
                             │
                     NEI ROOT CONTROLLER
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
        NEI-0              NEI-1              NEI-2
          │                  │                  │
         GPU                FAPU                NIC
```

Burada NEI Root Controller'ın görevi PCIe Root Complex'in kopyası olmak değil.

Görevi:

- kart bağlantısını yönetmek
- fiziksel linki oluşturmak
- kartı keşfetmek
- kaynakları tanımlamak
- Fabric adresi vermek
- DMA erişimini yönetmek
- bellek erişimini kontrol etmek
- hata yönetmek
- güç durumunu yönetmek

olacak.

---

# 2. NEI fiziksel slotu

Özel edge connector kullanmak mantıklı.

İlk tasarımda fiziksel yapı kabaca:

```text
┌─────────────────────────────────────┐
│             NEI CARD                │
│                                     │
│ GPU / FAPU / NIC / Accelerator      │
│                                     │
└───────────────┬─────────────────────┘
                │
════════════════╪════════════════════════
                │
          NEI EDGE CONNECTOR
                │
════════════════╪════════════════════════
                │
         NEXSUS MOTHERBOARD
```

Konnektör yalnızca veri için olmayacak.

En az dört temel grup olacak:

```text
NEI
├── DATA LANES
├── CLOCK / TIMING
├── CONTROL
└── POWER
```

Ancak clock mimarisini mümkün olduğunca azaltmak isteriz. İleri aşamada embedded clock kullanımı daha uygun olabilir.

---

# 3. Lane yapısı

Burada PCIe'yi birebir kopyalamayalım.

NEI için temel bir fiziksel lane:

```text
TX+
TX-
RX+
RX-
```

şeklinde full-duplex olabilir.

Örneğin:

```text
NEI x4
NEI x8
NEI x16
NEI x32
```

fiziksel genişlik seçenekleri olabilir.

Ancak önemli bir fark:

> **Lane sayısı cihazın fiziksel kapasitesi ile System Fabric kapasitesinden bağımsız olarak ölçeklenebilir.**

Örneğin küçük NIC:

```text
NEI x4
```

GPU:

```text
NEI x16
```

çok yüksek performanslı GPU:

```text
NEI x32
```

kullanabilir.

---

# 4. Bant genişliği hedefi

Burada henüz kesin PHY hızını seçmeyelim.

Fakat tasarım hedefini belirleyebiliriz.

Örneğin NEI v1.0 için:

> **Tek x16 bağlantı, PCIe 7 x16 seviyesini referans alabilecek veya aşabilecek toplam kullanılabilir bant genişliğine ölçeklenebilir olmalıdır.**

PCIe 7.0'ın x16 bağlantısı 128 GT/s seviyesinde ve yaklaşık 512 GB/s çift yönlü bant genişliği sınıfındadır. 

NEXSUS'un amacı burada yalnızca ham hız değildir.

Önemli olan:

\[
B_{effective}
=
B_{raw}
\cdot \eta_{protocol}
\cdot \eta_{fabric}
\]

Burada:

- \(B_{raw}\) = fiziksel ham bant genişliği
- \(\eta_{protocol}\) = protokol verimliliği
- \(\eta_{fabric}\) = Fabric kullanım verimliliği

---

# 5. NEXSUS'un asıl avantajı

PCIe'de cihaz ile sistem belleği arasında yine bir I/O protokol katmanı vardır.

NEXSUS'ta ise:

```text
GPU
 │
 │ NEI
 ▼
SYSTEM FABRIC
 │
 ├── CPU
 ├── FAPU
 ├── NPU
 ├── Data MOSRAM
 ├── M-SSD
 └── Display
```

Bu nedenle GPU:

> **System Fabric'in birinci sınıf düğümü**

haline gelir.

Bu kavramı **Fabric-Native Device** olarak tanımlayabiliriz.

---

# 6. Fabric-Native Device

Bir NEI cihazı sisteme bağlandığında kendisini şu kaynaklarla tanıtabilir:

```text
DEVICE
│
├── COMPUTE
├── MEMORY
├── DMA
├── CONTROL
├── EVENT
└── STREAM
```

Örneğin GPU:

```text
GPU
├── Compute Engine
├── Local Memory
├── DMA Engine
├── Command Engine
├── Event Engine
└── Display Engine
```

FAPU:

```text
FAPU
├── Compute Engine
├── Local Memory
├── DMA Engine
└── Event Engine
```

NIC:

```text
NIC
├── RX Engine
├── TX Engine
├── DMA
├── Packet Engine
└── Control
```

Hepsi aynı NEI mimarisini kullanabilir.

---

# 7. NEI adresleme

Burada klasik PCIe adresleme modelini doğrudan kopyalamak yerine System Fabric adreslemesini kullanmak daha doğru.

Örneğin:

```text
Fabric Address
│
├── Node ID
├── Resource ID
├── Region
└── Offset
```

Kavramsal olarak:

\[
A_{fabric} =
(N,R,G,O)
\]

burada:

- \(N\) = Node
- \(R\) = Resource
- \(G\) = Region
- \(O\) = Offset

---

# 8. GPU belleği

GPU'nun iki tür belleği olabilir:

```text
GPU
│
├── Local Memory
│
└── Fabric Memory
```

### Local Memory

GPU'nun fiziksel kartındaki yüksek hızlı bellek.

### Fabric Memory

Data MOSRAM veya başka bir Fabric belleği.

Böylece:

```text
GPU
 │
 ├──── Local Memory
 │
 └──── System Fabric
           │
           ▼
       Data MOSRAM
```

oluşur.

Bu iki bellek birbirinin alternatifi değil; farklı kullanım amaçlarına sahip olabilir.

---

# 9. DMA

NEI'nin en önemli özelliklerinden biri DMA.

Örneğin GPU görüntü oluşturdu:

```text
GPU
 │
 │ DMA WRITE
 ▼
Data MOSRAM
```

CPU bunu taşımıyor.

Tersi:

```text
Data MOSRAM
 │
 │ DMA READ
 ▼
GPU
```

Aynı şekilde:

```text
M-SSD
 │
 ▼
System Fabric
 │
 ▼
GPU
```

doğrudan mümkün olabilir.

---

# 10. M-SSD → GPU

Bu NEXSUS için önemli bir kullanım senaryosu.

Örneğin büyük bir veri kümesi M-SSD'de:

```text
M-SSD
  │
  ▼
MSSI
  │
  ▼
System Fabric
  │
  ▼
GPU
```

CPU arada veri taşımaz.

Hatta:

```text
M-SSD
 │
 ▼
Data MOSRAM
 │
 ▼
GPU
```

veya gerekli durumlarda doğrudan:

```text
M-SSD
 │
 ▼
GPU
```

yolu bulunabilir.

Bu karar daha sonra Fabric routing tasarımında kesinleştirilebilir.

---

# 11. GPU → Display

NEI'nin Display Controller ile doğrudan iletişim kurabilmesi de önemli.

```text
GPU
 │
 ▼
System Fabric
 │
 ▼
Display Controller
 │
 ▼
DisplayPort
```

CPU burada yalnızca:

```text
"Şu görüntü yapılandırmasını kullan."
```

gibi kontrol bilgisi verebilir.

Görüntü frame'lerinin kendisi CPU'dan geçmez.

---

# 12. GPU → GPU

Birden fazla GPU varsa:

```text
GPU 0
 │
 ▼
System Fabric
 │
 ▼
GPU 1
```

ile doğrudan haberleşebilirler.

Bu, gelecekte çok GPU'lu sistemlerde önemli olabilir.

Örneğin:

```text
GPU 0
 ├── CPU
 ├── FAPU
 ├── GPU 1
 └── Data MOSRAM
```

---

# 13. FAPU ↔ GPU

FAPU özel hesaplama motoru olduğundan:

```text
GPU
 │
 ▼
System Fabric
 │
 ▼
FAPU
```

ve:

```text
FAPU
 │
 ▼
System Fabric
 │
 ▼
GPU
```

doğrudan veri aktarımı yapabilir.

Örneğin GPU:

> büyük matris/veri hazırlama

FAPU:

> karmaşık matematiksel işlem

yapabilir.

---

# 14. NEI Control Plane / Data Plane

NEI içerisinde kontrol ve veri trafiğini ayırmak önemli.

```text
NEI
│
├── CONTROL PLANE
│
└── DATA PLANE
```

### Control Plane

- cihaz keşfi
- kaynak tanımlama
- reset
- power state
- configuration
- event
- error

### Data Plane

- DMA
- memory transfer
- stream
- compute data

Böylece büyük GPU transferleri küçük kontrol paketlerini engellemez.

---

# 15. Event sistemi

NEI cihazlarının CPU'ya sürekli polling yapması gerekmemeli.

Örneğin GPU:

```text
GPU
 │
 │ EVENT
 ▼
System Fabric
 │
 ▼
CPU
```

veya:

```text
GPU
 │
 │ EVENT
 ▼
FAPU
```

gönderebilir.

Event:

```text
COMPLETION
ERROR
BUFFER_READY
DATA_READY
FRAME_READY
DEVICE_EVENT
```

gibi olabilir.

---

# 16. Kart keşfi

Sistem açıldığında NEI:

```text
POWER
 ↓
PHY TRAINING
 ↓
LINK
 ↓
DEVICE DISCOVERY
 ↓
RESOURCE DISCOVERY
 ↓
MEMORY DISCOVERY
 ↓
FABRIC ADDRESS
 ↓
ACTIVE
```

sürecinden geçer.

Kart örneğin:

```text
DEVICE:
NEXSUS GPU

TYPE:
COMPUTE + DISPLAY

LANES:
x16

MEMORY:
24 GB Local

FABRIC ACCESS:
YES

DMA:
YES

DISPLAY:
YES
```

gibi yeteneklerini bildirir.

---

# 17. Boot sırasında GPU

Firmware aşamasında NEI cihazları keşfedilebilir.

Örneğin:

```text
NEXSUS Firmware
       │
       ▼
NEI Discovery
       │
       ├── GPU
       ├── NIC
       └── Accelerator
```

SCP:

- güç
- reset
- thermal

kısmını yönetirken,

Firmware:

- cihaz tanımlama
- kaynak yapılandırma
- boot desteği

kısmını yönetebilir.

---

# 18. Hot Plug

NEI'nin ilk sürümünde masaüstü genişletme kartları için hot-plug zorunlu olmayabilir.

Bu önemli çünkü:

- yüksek güç
- mekanik kart
- soğutucu
- fiziksel sabitleme

gibi sebeplerle PCIe tarzı hot-plug her sistem için gerekli değil.

İlk NEXSUS:

> **Power-off insertion/removal**

kullanabilir.

İleride özel NEI hot-plug destekli sistemler yapılabilir.

---

# 19. Güç

NEI slotunun güç mimarisi doğrudan NEXSUS anakartıyla bütünleşir.

Kabaca:

```text
PSU
 │
 ▼
Power Controller
 │
 ├── NEI Slot 0
 ├── NEI Slot 1
 └── NEI Slot 2
```

SCP:

- güç açma
- kapatma
- reset
- sıcaklık
- akım
- hata

durumlarını izleyebilir.

Bu nedenle NEI'nin güç yönetimi yalnızca kartın kendi VRM'sine bırakılmaz.

---

# 20. NEI hata yönetimi

Yüksek hızlı fiziksel bağlantıda hata kaçınılmaz olarak tasarımın parçası.

NEI:

```text
PHY Error
    ↓
Link Error
    ↓
Packet Error
    ↓
CRC
    ↓
Recovery
```

mekanizmasına sahip olmalı.

Çok yüksek hızlarda gerekirse:

- CRC
- FEC
- retry
- lane recovery

birlikte kullanılabilir.

---

# 21. NEI ile MSSI arasındaki fark

İki sistem birbirine benzeyecek ama aynı şey olmayacak.

### MSSI

Optimize edilmiş:

> **Storage → Fabric**

bağlantısı.

### NEI

Optimize edilmiş:

> **Compute/Expansion Device → Fabric**

bağlantısı.

```text
                 SYSTEM FABRIC
                      │
             ┌────────┴────────┐
             │                 │
            MSSI              NEI
             │                 │
           M-SSD          GPU/FAPU/NIC
```

Bu ayrım mimariyi sade tutuyor.

---

# 22. NEXSUS genişletme mimarisinin son şekli

Şu anda:

```text
                        NEXSUS SYSTEM FABRIC
                                  │
          ┌───────────────┬───────┴────────┬───────────────┐
          │               │                │               │
         NPI             MSSI              NEI            DP
          │               │                │               │
     USB-C devices      M-SSD        Expansion Cards    Display
          │               │                │
          │               │         ┌──────┼──────┐
          │               │         │      │      │
          │               │        GPU    FAPU    NIC
```

Bu artık oldukça net bir ayrım oluşturuyor:

**NPI → çevre birimleri**

**MSSI → kalıcı depolama**

**NEI → hesaplama/genişletme**

**DisplayPort → ana görüntü**

**NSF → hepsinin ortak omurgası**




