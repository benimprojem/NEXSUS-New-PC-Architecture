# NEXSUS Wireless Link
## Kanal Kimliği, Akış Modeli ve Paralel Radyo Zamanlayıcısı

**Doküman Kodu:** NEXSUS-NWL-ARCH-003  
**Konu:** Wireless Channel Fabric, stream modeli, routing ve paralel RF zamanlayıcısı  
**Statü:** Kavramsal Teknik Tasarım

---

# 1. Temel Hiyerarşi

NWL'nin önceki aşamasında ortaya çıkan en önemli sonuç şudur:

```text
Device
   ↓
Service
   ↓
Stream
   ↓
Channel
   ↓
Radio
```

Bu beş kavram birbirinden ayrılmalıdır.

Örneğin sekiz hoparlörlü sistemde:

```text
Device:
    Speaker 0

Services:
    Audio
    Control
    Status

Streams:
    Audio Stream
    Control Stream

Channels:
    Front Left
    Device Control
    Device Status

Radio:
    RF-02
```

Bir cihazın birden fazla servisi olabilir.

Bir servisin birden fazla stream'i olabilir.

Bir stream bir veya daha fazla mantıksal kanala bağlanabilir.

Kanallar ise çalışma sırasında farklı fiziksel radyolara atanabilir.

---

# 2. Device ID

Her cihazın temel kimliği:

```text
DEVICE_ID
```

olur.

Örneğin:

```text
SPK-0001
SPK-0002
MOUSE-0001
PHONE-0001
HEADSET-0001
```

Ancak Device ID **verinin hedefi değildir**.

Device ID yalnızca cihazı tanımlar.

Asıl veri yönlendirmesi daha alt seviyelerde yapılır.

---

# 3. Service ID

Cihaz üzerinde bulunan işlevler Service ID ile ayrılır.

Örneğin headset:

```text
HEADSET-0001

SERVICE 01 → AUDIO_OUT
SERVICE 02 → MICROPHONE
SERVICE 03 → CONTROL
SERVICE 04 → STATUS
```

Telefon:

```text
PHONE-0001

SERVICE 01 → AUDIO
SERVICE 02 → MICROPHONE
SERVICE 03 → CAMERA
SERVICE 04 → DATA
SERVICE 05 → NOTIFICATION
SERVICE 06 → APPLICATION
```

Böylece işletim sistemi bütün telefonu tek bir veri kanalı olarak görmek zorunda kalmaz.

---

# 4. Stream ID

Service'in çalışma sırasında oluşturduğu gerçek veri akışı:

```text
STREAM_ID
```

ile tanımlanır.

Örneğin:

```text
AUDIO_SERVICE
      ↓
STREAM 017
      ↓
GAME_AUDIO
```

Başka bir uygulama:

```text
AUDIO_SERVICE
      ↓
STREAM 018
      ↓
VOICE_CHAT
```

oluşturabilir.

Aynı cihaz aynı anda çok sayıda stream taşıyabilir.

---

# 5. Channel ID

Channel, stream'in mantıksal taşıma yoludur.

Örneğin 7.1:

```text
STREAM = GAME_AUDIO

CH00 → Front Left
CH01 → Front Right
CH02 → Center
CH03 → LFE
CH04 → Surround Left
CH05 → Surround Right
CH06 → Rear Left
CH07 → Rear Right
```

Burada **7.1 bir protokol tipi değildir.**

Sadece sekiz kanal içeren bir audio stream konfigürasyonudur.

---

# 6. Channel ID ile Hoparlör ID Ayrımı

Örneğin:

```text
CH00 = Front Left
```

fiziksel olarak:

```text
SPK-0006
```

üzerinde oynatılabilir.

Başka bir kullanıcı:

```text
CH00 = Front Left
```

için:

```text
SPK-0002
```

seçebilir.

Dolayısıyla:

```text
Channel ≠ Device
```

Bu ayrım NWL'nin temel özelliklerinden biridir.

---

# 7. Routing Entry

Her aktif kanal için bir routing entry bulunabilir:

```text
CHANNEL ROUTE

Channel ID
Source
Destination
Stream ID
Radio ID
Priority
Timing Mode
Security Context
```

Örneğin:

```text
CH00
Source      = Audio Engine
Destination = SPK-0006
Stream      = GAME-017
Radio       = RF-02
Priority    = RT
Timing      = ISO
```

---

# 8. 7.1 İçin Gerçek Routing Tablosu

Örneğin:

| Channel | İşlev | Hoparlör | RF | Öncelik |
|---|---|---|---|---|
| CH00 | Front Left | SPK06 | RF02 | RT |
| CH01 | Front Right | SPK02 | RF02 | RT |
| CH02 | Center | SPK00 | RF03 | RT |
| CH03 | LFE | SPK07 | RF03 | RT |
| CH04 | Surround Left | SPK04 | RF04 | RT |
| CH05 | Surround Right | SPK05 | RF04 | RT |
| CH06 | Rear Left | SPK01 | RF05 | RT |
| CH07 | Rear Right | SPK03 | RF05 | RT |

Böylece sekiz hoparlör dört farklı RF üzerinde çalışabilir.

Ama işletim sistemi açısından hâlâ:

```text
ONE AUDIO STREAM
```

vardır.

---

# 9. Radio ID

Fiziksel kablosuz kaynak:

```text
RADIO_ID
```

ile tanımlanır.

Örneğin:

```text
RF00
RF01
RF02
RF03
RF04
RF05
```

Bunların hepsi aynı NWC'nin parçasıdır.

```text
             NWC
              │
 ┌────────────┼────────────┐
 │            │            │
 RF00        RF01         RF02
 │            │            │
 Audio       HID          Data
```

---

# 10. Bir Radio Birden Fazla Channel Taşıyabilir

RF02 yalnızca tek bir cihaz için ayrılmak zorunda değildir.

Örneğin:

```text
RF02
 ├── CH00 → SPK06
 ├── CH01 → SPK02
 └── CH08 → Headset Audio
```

olabilir.

Böylece fiziksel radyo ile mantıksal kanal arasında bire bir ilişki kurulmaz.

---

# 11. Bir Channel Gerektiğinde Radio Değiştirebilir

Daha da önemlisi:

```text
CH00
   ↓
RF02
```

başlangıçta böyleyken sistem:

```text
CH00
   ↓
RF05
```

haline getirebilir.

Bu değişim kullanıcıya görünmemelidir.

Bunun amacı:

- parazit
- yük
- RF yoğunluğu
- mesafe
- bağlantı kalitesi
- güç tüketimi

gibi koşullara göre kaynakların yeniden dağıtılabilmesidir.

---

# 12. Radio Scheduler

Bu işi:

**NWL Radio Scheduler**

yapar.

Temel girdileri:

```text
Channel
Priority
Bandwidth
Latency
Deadline
Reliability
Radio Quality
Device Distance
Power State
```

olabilir.

Scheduler bunlara göre:

```text
Channel → Radio → Time Slot
```

eşlemesi oluşturur.

---

# 13. Sabit ve Dinamik Trafik

İki temel trafik tipi ayırmak faydalı olur.

### Fixed/Reserved

Önceden garanti edilmiş zaman:

```text
Audio
Microphone
Critical Control
```

### Dynamic

Boş kapasiteyi kullanan trafik:

```text
File Transfer
Phone Sync
Backup
Background Data
```

Örneğin:

```text
RF02

[ AUDIO ][ AUDIO ][ AUDIO ][ AUDIO ]

RF05

[ DATA ][ DATA ][ DATA ][ DATA ]
```

Audio zamanlaması korunurken Data kapasiteye göre genişleyebilir.

---

# 14. Scheduler'ın Önceliği

Örneğin aynı anda:

```text
Mouse
Keyboard
8 × Audio
Microphone
Phone Data
```

aktif.

Scheduler bunu şöyle değerlendirebilir:

```text
1. Critical Control
2. Interactive HID
3. Isochronous Audio
4. Interactive Data
5. Bulk Data
6. Background
```

Ancak burada salt öncelik yeterli değildir.

Audio'nun **deadline** bilgisi vardır.

Mouse'un ise **latency** bilgisi daha önemlidir.

Bu nedenle scheduler birden fazla parametreyle karar vermelidir.

---

# 15. Deadline Kavramı

Bir audio frame:

```text
Timestamp = T
Deadline = T + D
```

ile tanımlanabilir.

Örneğin:

```text
Frame 1821

Presentation Time = 100.000 ms
Deadline          = 100.500 ms
```

Scheduler bu frame'i 100.500 ms'den sonra gönderirse frame artık kullanılmayabilir.

Bu nedenle:

```text
Deadline geçti
      ↓
DROP
```

yapılabilir.

Zaman bağımlı verinin süresi dolduğunda atılması, mevcut izokron iletişim mimarilerinde de temel bir prensiptir.

---

# 16. Audio Senkronizasyonu

Sekiz hoparlör için:

```text
CH00 → T
CH01 → T
CH02 → T
CH03 → T
CH04 → T
CH05 → T
CH06 → T
CH07 → T
```

olmalıdır.

Fakat paketler farklı zamanlarda gönderilebilir.

Örneğin:

```text
RF02 → CH00 → 1.2 ms
RF02 → CH01 → 1.5 ms
RF03 → CH02 → 1.8 ms
RF04 → CH03 → 2.0 ms
```

Bunların hepsi:

```text
PLAYBACK TIME = T
```

olabilir.

Alıcılar paketi aldıkları anda çalmaz.

**Ortak presentation time'a göre çalar.**

Bu yaklaşım, çoklu bağımsız alıcıların aynı anda render edilmesini sağlamak için kullanılan izokron senkronizasyon prensibiyle uyumludur.

---

# 17. Wireless Timebase

Bunun için NWC'de:

```text
WIRELESS MASTER CLOCK
```

bulunması mantıklıdır.

```text
                 NWC
                  │
          MASTER TIMEBASE
                  │
      ┌───────────┼───────────┐
      ↓           ↓           ↓
    RF00        RF01        RF02
      │           │           │
     SPK         SPK         SPK
```

RF'lerin kendi çalışma saatleri olabilir ama NWL'nin **ortak sistem zamanı** bulunur.

---

# 18. Alıcı Saat Düzeltmesi

Her hoparlör:

```text
LOCAL CLOCK
```

kullanır.

NWL ise:

```text
MASTER CLOCK
```

ile bunun farkını izler.

Örneğin:

```text
Speaker 0
Clock Offset = +18 μs

Speaker 1
Clock Offset = -7 μs

Speaker 2
Clock Offset = +3 μs
```

NWL bu farkları hesaba katabilir.

Böylece uzun süreli kullanımda hoparlörler birbirinden kaymaz.

---

# 19. Buffer

Hoparlör alıcısında küçük bir zaman tamponu bulunmalıdır.

```text
Radio RX
   ↓
Packet Buffer
   ↓
Timestamp Sort
   ↓
Clock Alignment
   ↓
DAC
```

Amaç gecikmeyi gereksiz büyütmek değildir.

Ama sıfır buffer da gerçek kablosuz sistemlerde yeterli olmayabilir.

Dolayısıyla:

> **minimum gerekli synchronization buffer**

kullanılmalıdır.

---

# 20. Paralel RF'nin Gerçek Avantajı

Burada önemli bir ayrım ortaya çıkıyor.

Paralel RF sadece:

> “daha yüksek toplam Mbps”

demek değildir.

Asıl avantaj:

> **farklı trafik sınıflarının fiziksel kaynaklarının ayrılabilmesi**

olmalıdır.

Örneğin:

```text
RF00 → Audio
RF01 → Audio
RF02 → HID
RF03 → Microphone
RF04 → Bulk Data
RF05 → Phone
```

Böylece büyük bir dosya aktarımı:

```text
RF04
```

üzerinde yoğunlaşırken:

```text
RF02 → Mouse
RF03 → Microphone
RF00/RF01 → Audio
```

etkilenmeyebilir.

---

# 21. Radio Pool

Fakat radyoları tamamen sabitlemek de doğru olmayabilir.

Bunun yerine:

```text
RADIO POOL

RF00
RF01
RF02
RF03
RF04
RF05
...
```

bulunur.

Scheduler gerektiğinde:

```text
Audio → RF00 + RF01
HID   → RF02
Data  → RF03 + RF04
Phone → RF05
```

atanabilir.

Sonra şartlar değişirse:

```text
Audio → RF00 + RF02
HID   → RF01
Data  → RF03 + RF04
Phone → RF05
```

olabilir.

---

# 22. Radio Bonding

Bir veri akışı birden fazla radyoyu aynı anda kullanabilir.

Örneğin büyük veri:

```text
DATA STREAM
      │
 ┌────┴────┐
 ↓         ↓
RF03      RF04
 │         │
 └────┬────┘
      ↓
 Destination
```

Burada iki yaklaşım olabilir:

### Split

Veri paketleri farklı RF'lere dağıtılır.

### Redundant

Aynı kritik paket birden fazla RF üzerinden gönderilir.

İkisi aynı şey değildir.

---

# 23. Split Mode

Örneğin:

```text
Packet 100 → RF03
Packet 101 → RF04
Packet 102 → RF03
Packet 103 → RF04
```

Toplam throughput artabilir.

Alıcı:

```text
RF03 ─┐
      ├── Reorder
RF04 ─┘
```

yapar.

---

# 24. Redundant Mode

Kritik bir kontrol paketinde:

```text
CONTROL PACKET 55
       │
   ┌───┴───┐
   ↓       ↓
 RF02    RF03
   │       │
   └───┬───┘
       ↓
    Receiver
```

kullanılabilir.

İlk gelen geçerli paket yeterlidir.

Bu:

- kritik kontrol
- acil sistem komutu
- bağlantı kurtarma

gibi durumlarda düşünülebilir.

---

# 25. RF Hatası

Bir RF bağlantısı bozulursa kanalın tamamı ölmek zorunda değildir.

Örneğin:

```text
RF02 = FAILED

CH00
CH01
CH08
```

bu radyoda olsun.

Scheduler:

```text
CH00 → RF04
CH01 → RF04
CH08 → RF05
```

şeklinde yeniden yerleştirebilir.

Dolayısıyla:

> **Radio failure ≠ Service failure**

olmalıdır.

Bu NEXSUS mimarisinin önemli dayanıklılık özelliklerinden biri olabilir.

---

# 26. Audio'da Hata Kurtarma

Audio için her paketi sonsuza kadar yeniden göndermek doğru değildir.

Bunun yerine:

```text
Packet
 ↓
Received?
 ├── YES → Buffer
 └── NO
      ↓
   Deadline?
   ├── NO  → Retransmit
   └── YES → Drop
```

olabilir.

Böylece gecikme kontrol altında tutulur.

Mevcut LE Audio'da da bağlantılı izokron akışlar için yeniden iletim ve zaman sınırı kavramları bulunuyor.

---

# 27. HID İçin Farklı Davranış

Mouse paketinde:

```text
Movement Event
```

kaybolursa yeni hareket olayı daha önemli olabilir.

Örneğin:

```text
Mouse event 100
Mouse event 101
Mouse event 102
```

gönderilirken 100 kaybolmuşsa:

```text
100 → RETRY
```

yerine çoğu durumda:

```text
101
102
```

ile devam etmek daha anlamlı olabilir.

Dolayısıyla NWL'nin retransmission davranışı **servis tipine göre değişebilmelidir.**

---

# 28. Data İçin Farklı Davranış

Dosya transferinde ise durum tamamen farklıdır.

```text
Packet 100
Packet 101
Packet 102
```

102 kaybolduysa:

```text
RETRANSMIT
```

gerekebilir.

Çünkü burada:

```text
Accuracy > Latency
```

olur.

Audio'da ise çoğu durumda:

```text
Timing > Perfect Delivery
```

olabilir.

Bu ayrım NWL'nin servis mimarisinde açıkça tanımlanmalıdır.

---

# 29. Service QoS

Her Service bir QoS profiline sahip olabilir.

Örneğin:

```text
AUDIO
Latency: Very Low
Deadline: Strict
Reliability: Medium/High
Ordering: Required
Sync: Required
```

Mouse:

```text
Latency: Extremely Low
Deadline: Strict
Reliability: High
Ordering: Context-dependent
Sync: No
```

Data:

```text
Latency: Medium
Deadline: None
Reliability: Very High
Ordering: Required
Sync: No
```

Bu bilgiler scheduler'ın karar mekanizmasının girdisi olur.

---

# 30. NWC'nin Karar Döngüsü

Kavramsal olarak:

```text
             ┌───────────────┐
             │ ACTIVE STREAMS│
             └───────┬───────┘
                     ↓
              QoS Analysis
                     ↓
              Channel Demand
                     ↓
               Radio Status
                     ↓
             Interference
                     ↓
             Radio Assignment
                     ↓
              Time Scheduling
                     ↓
              Packet Dispatch
                     ↓
             Feedback / Metrics
                     │
                     └──────→ tekrar
```

Bu yapı sürekli çalışır.

---

# 31. Channel Fabric'in System Fabric ile Bağlantısı

Artık iki fabric arasında açık bir ayrım oluşuyor:

```text
              NEXSUS SYSTEM FABRIC
                       │
                ┌──────┴──────┐
                │     NWC     │
                └──────┬──────┘
                       │
              WIRELESS CHANNEL
                   FABRIC
                       │
          ┌────────────┼────────────┐
          ↓            ↓            ↓
       RADIO         RADIO        RADIO
        FABRIC        FABRIC       FABRIC
          │            │            │
       Devices       Devices      Devices
```

System Fabric:

**sistemin tamamındaki veri hareketini**

yönetir.

Wireless Channel Fabric:

**kablosuz taraftaki mantıksal veri akışını**

yönetir.

Radio Fabric:

**fiziksel RF kaynaklarını**

yönetir.

---

# 32. Bu Üçlü Ayrım Önemli

Dolayısıyla:

```text
System Fabric
     │
     └── Wireless Channel Fabric
             │
             └── Radio Fabric
```

şeklinde üç seviyeli bir yapı oluşur.

Bu, NEXSUS'un diğer mimari kararlarıyla da uyumludur:

```text
CPU ≠ System Fabric
NWC ≠ Wireless Channel
Radio ≠ Wireless Device
Channel ≠ Speaker
Service ≠ Device
```

Her katmanın görevi ayrıdır.

---

# 33. Örnek Tam Akış

PC'de oyun çalışıyor.

Sekiz hoparlör 7.1 ses veriyor.

Aynı anda mouse hareket ediyor.

Telefon dosya gönderiyor.

Headset mikrofonu aktif.

Akış:

```text
GAME AUDIO
    ↓
Audio Engine
    ↓
8 Logical Channels
    ↓
Wireless Channel Fabric
    ↓
Radio Scheduler
    ↓
RF00/RF01/RF02/RF03
    ↓
8 Speaker Receivers
```

Aynı anda:

```text
MOUSE
 ↓
RF04
 ↓
NWC
 ↓
System Fabric
 ↓
CPU Input
```

ve:

```text
HEADSET MIC
 ↓
RF05
 ↓
NWC
 ↓
System Fabric
 ↓
Audio Buffer
```

ve:

```text
PHONE
 ↓
RF06/RF07
 ↓
NWC
 ↓
System Fabric
 ↓
Data MOSRAM
```

hepsi bağımsız olarak çalışabilir.

---

# 34. NEXSUS'un Asıl Kablosuz Modeli

Böylece NWL'yi artık şöyle tanımlayabiliriz:

\[
\boxed{
Device \rightarrow Service \rightarrow Stream
\rightarrow Channel \rightarrow Radio
}
\]

ters yönde ise:

\[
\boxed{
Radio \rightarrow Channel \rightarrow Stream
\rightarrow Service \rightarrow Device
}
\]

Routing mekanizması bu iki yön arasındaki eşlemeyi gerçekleştirir.

---

# 35. Sonuç

NWL'nin hedefi:

**“PC'ye kablosuz cihaz bağlamak”**

değildir.

Hedef:

> **PC'nin kablosuz tarafını, System Fabric'in doğal bir uzantısı olan yönlendirilebilir ve paralel bir iletişim fabric'i haline getirmektir.**

Bunun sonucunda:

```text
8 Speaker
+ Mouse
+ Keyboard
+ Headset
+ Microphone
+ Phone
+ Storage
+ Controller
```

aynı sistem içerisinde çalışabilir.

Ve bunların hiçbiri:

```text
"Bluetooth cihazı"
"USB cihazı"
"Audio cihazı"
```

olarak birbirinden kopuk mimariler olmak zorunda değildir.

Hepsi:

```text
NEXSUS DEVICE
      ↓
NEXSUS SERVICE
      ↓
NEXSUS STREAM
      ↓
NEXSUS CHANNEL
      ↓
NEXSUS RADIO FABRIC
```

üzerinden System Fabric'e bağlanır.

---

# 36. Bir Sonraki Teknik Katman

Buradan sonra NWL'nin **paket/frame yapısına** geçilebilir.

Özellikle şu alanların tasarlanması gerekir:

```text
┌──────────────────────────────┐
│ Frame Header                 │
├──────────────────────────────┤
│ Device / Session             │
├──────────────────────────────┤
│ Service ID                   │
├──────────────────────────────┤
│ Stream ID                    │
├──────────────────────────────┤
│ Channel ID                   │
├──────────────────────────────┤
│ Sequence                     │
├──────────────────────────────┤
│ Timestamp / Deadline         │
├──────────────────────────────┤
│ QoS / Priority               │
├──────────────────────────────┤
│ Security / Integrity         │
├──────────────────────────────┤
│ Payload                      │
└──────────────────────────────┘
```

Fakat bu alanların hepsini hemen sabitlemek yerine önce **minimum header + stream kontrol bilgisi + zaman bilgisi + routing bilgisi** ayrımını kurmak daha doğru olacaktır. Özellikle büyük dosya aktarımında her pakete uzun Device/Service bilgilerini tekrar tekrar koymak gereksiz overhead oluşturacağından, bağlantı kurulduktan sonra bazı bilgilerin **Session Context** içinde tutulması daha verimli olabilir.

Bu da NWL'yi sıradan bir paket protokolünden çıkarıp, **bağlantı kurulduktan sonra kendi sanal kanallarını oluşturan bir kablosuz fabric protokolüne** dönüştürüyor.
---