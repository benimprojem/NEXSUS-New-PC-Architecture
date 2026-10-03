
# NEXSUS Wireless Link (NWL)
## Kablosuz Çevre Birimleri ve Çoklu Cihaz İletişim Mimarisi

**Doküman Kodu:** NEXSUS-NWL-ARCH-001  
**Konu:** NEXSUS Wireless Link kablosuz iletişim mimarisi  
**Statü:** Kavramsal Teknik Tasarım

---

## 1. Amaç

NEXSUS Wireless Link (NWL), bilgisayarın kablosuz çevre birimlerini tek tek ve birbirinden bağımsız bağlantılar olarak değil, **tek bir kablosuz sistem ağı** olarak yönetmesini amaçlar.

Temel yaklaşım:

```text
                    NEXSUS PC
                        │
                NEXSUS Wireless
                   Controller
                        │
          ┌─────────────┼─────────────┐
          │             │             │
       Keyboard       Mouse        Headset
          │             │          ┌──┴──┐
          │             │        Audio  Mic
          │
       Phone ─────── Speaker ───── Camera
```

Burada bilgisayarın her cihaz için ayrı bir alıcıya sahip olması gerekmez.

Tek bir **NEXSUS Wireless Controller (NWC)** bütün kablosuz cihazların bağlantısını yönetir.

---

# 2. Temel Mimari İlkesi

NWL'nin temel farkı:

> **Cihaz bağlantısı ile uygulama/işlev bağlantısı birbirinden ayrılır.**

Örneğin bir headset tek bir cihazdır ancak içinde birden fazla mantıksal kanal bulunabilir:

```text
Headset
   │
   ├── Audio OUT
   ├── Microphone IN
   ├── Control
   ├── Battery Status
   └── Device Management
```

Telefon ise daha fazla kanal açabilir:

```text
Phone
 │
 ├── Audio
 ├── Microphone
 ├── Camera
 ├── Notifications
 ├── File Transfer
 ├── Control
 └── Application Services
```

Dolayısıyla işletim sistemi açısından:

**cihaz ≠ tek bağlantı**

olur.

Bir cihaz, NWL üzerinde birden fazla mantıksal servis taşıyabilir.

---

# 3. NWC — NEXSUS Wireless Controller

NWL'nin merkezindeki donanım birimi:

**NWC — NEXSUS Wireless Controller**

olacaktır.

NWC'nin görevi yalnızca radyo sinyali üretmek değildir.

```text
             NEXSUS Wireless Controller
                       │
       ┌───────────────┼────────────────┐
       │               │                │
   Radio Engine   Link Scheduler   Security
       │               │                │
       └───────────────┼────────────────┘
                       │
                 Device Manager
                       │
                Service Manager
                       │
                  System Fabric
```

NWC böylece NWL'nin kablosuz tarafındaki karşılığı olur.

System Fabric ile doğrudan bağlantılıdır:

```text
Wireless Device
       │
      NWL
       │
      NWC
       │
  System Fabric
       │
 ┌─────┼─────────┐
CPU   MOSRAM    FAPU
```

CPU'nun her kablosuz paketle doğrudan ilgilenmesi gerekmez.

---

# 4. Tek Alıcı Mimarisi

Klasik bilgisayarda sık görülen yapı:

```text
Keyboard ── Dongle
Mouse ───── Dongle
Headset ─── Dongle
Controller ─ Dongle
```

NWL'de hedef:

```text
Keyboard ─┐
Mouse ────┤
Headset ──┤
Phone ────┼──► NWC
Speaker ──┤
Mic ──────┤
Controller┘
```

Böylece fiziksel alıcı sayısı azalır.

Daha önemlisi, bütün cihazlar aynı sistem yöneticisi tarafından görülür.

---

# 5. Cihaz Kimliği

Her NWL cihazının bir **Device ID** değeri bulunur.

Ancak Device ID tek başına cihazın nasıl kullanılacağını belirlemez.

Bağlantı sonrasında cihaz yeteneklerini bildirir.

Örnek:

```text
DEVICE_ID
    ↓
DEVICE_DISCOVERY
    ↓
CAPABILITY_DISCOVERY
    ↓
SERVICE_DISCOVERY
    ↓
CHANNEL_ALLOCATION
    ↓
ACTIVE
```

Örneğin mouse:

```text
Device ID: MOUSE-xxxx

Capabilities:
    HID
    Motion
    Buttons
    Wheel
    Battery
```

Headset:

```text
Device ID: HEADSET-xxxx

Capabilities:
    Audio Output
    Microphone
    Control
    Battery
```

Telefon:

```text
Device ID: PHONE-xxxx

Capabilities:
    Audio
    Microphone
    Camera
    Display
    Storage
    Notifications
    Application Link
```

Bu nedenle sistemin cihazın modelini önceden bilmesine gerek kalmaz.

---

# 6. Capability Discovery

NWL'nin önemli özelliklerinden biri **Capability Discovery** olacaktır.

Cihaz bağlandığında:

```text
NWC → Device
"Kimlik bildir."

Device → NWC
"Ben şu yeteneklere sahibim."

NWC → Device
"Şu servisleri etkinleştiriyorum."

Device → NWC
"Tamam."
```

Örneğin aynı fiziksel cihazın yalnızca ses çıkışı destekleyen bir modeli ile mikrofonlu modeli aynı temel protokolü kullanabilir.

Farkı capability tablosu belirler.

---

# 7. Logical Channel Model

NWL fiziksel bağlantı ile mantıksal kanalları ayırır.

Örnek:

```text
                    PHYSICAL LINK
                         │
                ┌────────┴────────┐
                │                 │
          Logical Channels
                │
      ┌─────────┼──────────┬──────────┐
      │         │          │          │
    HID       AUDIO       MIC       CONTROL
```

Bu nedenle tek radyo bağlantısı üzerinde birden fazla servis bulunabilir.

Örneğin:

```text
Headset
 ├─ Channel 01 → Audio
 ├─ Channel 02 → Microphone
 ├─ Channel 03 → Control
 └─ Channel 04 → Status
```

---

# 8. Kanal Türleri

İlk kavramsal kanal sınıfları:

| Kanal | Kullanım |
|---|---|
| CONTROL | bağlantı ve cihaz yönetimi |
| STATUS | batarya, sıcaklık, durum |
| HID | klavye, mouse, kontrolcü |
| AUDIO | ses çıkışı |
| MICROPHONE | ses girişi |
| DATA | genel veri |
| STORAGE | depolama erişimi |
| CAMERA | görüntü |
| APPLICATION | telefon/uygulama servisleri |

Bu liste nihai protokol değildir.

Yeni cihaz tipleri çıktığında yeni servis sınıfları eklenebilir.

---

# 9. Trafik Önceliği

Bütün kablosuz veriler aynı önceliğe sahip değildir.

Örneğin:

```text
Mouse hareketi
     ↓
çok düşük veri
çok düşük gecikme
yüksek öncelik
```

Buna karşılık:

```text
Telefon → Dosya Transferi
     ↓
yüksek veri miktarı
daha yüksek gecikme kabul edilebilir
```

Audio ise:

```text
Audio
 ↓
zaman hassas
sabit akış
gecikme kritik
```

Bu nedenle NWL'de paketler yalnızca FIFO mantığıyla gönderilmemelidir.

Önerilen sınıflandırma:

```text
P0  SYSTEM CONTROL
P1  REAL-TIME CONTROL
P2  AUDIO / VIDEO
P3  INTERACTIVE DATA
P4  BULK DATA
P5  BACKGROUND
```

Bu yapı System Fabric'deki öncelik mekanizmasıyla uyumlu olur.

---

# 10. Kablosuz Zamanlayıcı

NWC'nin en önemli donanım bloklarından biri:

**Wireless Scheduler**

olacaktır.

Görevi aynı anda birçok cihazın iletişim zamanlarını düzenlemektir.

Örneğin:

```text
ZAMAN

│ K │ M │ A │ H │ M │ A │ K │ D │ H │ M │
│   │   │   │   │   │   │   │   │   │   │

K = Keyboard
M = Mouse
A = Audio
H = Headset/Mic
D = Data
```

Ancak gerçek sistemde bu yapı statik olmak zorunda değildir.

Scheduler trafik durumuna göre slotları değiştirebilir.

---

# 11. Dinamik Airtime Allocation

Örneğin kullanıcı yalnızca mouse ve klavye kullanıyorsa:

```text
Keyboard  ──┐
Mouse     ──┼── yüksek erişilebilirlik
Control   ──┘

Audio     ─── düşük
Bulk Data ─── minimum
```

Bir dosya transferi başladığında:

```text
Keyboard ──┐
Mouse ─────┤
Audio ─────┤
            ├── scheduler yeniden dağıtır
Bulk Data ──┘
```

Dosya transferi, mouse hareketinin gecikmesini artırmamalıdır.

---

# 12. Gerçek Zamanlı Akışlar

Audio ve benzeri veriler için NWL'de **time-bound stream** kavramı bulunmalıdır.

Mantık:

```text
Audio Packet
      │
      ├── Arrival Deadline
      ├── Sequence
      ├── Timestamp
      └── Priority
```

Süresi geçmiş bir audio paketinin artık gönderilmesinin anlamı olmayabilir.

Bu yaklaşım günümüzde Bluetooth LE izokron iletişiminde de kullanılan temel prensiplerden biridir; bağlantılı izokron akışlarda zamanlanmış alt olaylar ve yeniden iletim mekanizmaları bulunur.

NWL'de ise bu kavram genel bir **Wireless Stream** mimarisine dönüştürülebilir.

---

# 13. Bidirectional Stream

Bir headset için:

```text
PC ───────────► Headset
       AUDIO

PC ◄─────────── Headset
       MICROPHONE
```

Tek fiziksel bağlantı üzerinde iki yönlü bağımsız mantıksal akış bulunur.

Dolayısıyla:

```text
DEVICE
   │
   ├── TX Streams
   └── RX Streams
```

şeklinde düşünülmelidir.

---

# 14. Çoklu Audio

NWL yalnızca tek headset'i hedeflememelidir.

Örneğin:

```text
                 NWC
                  │
       ┌──────────┼──────────┐
       │          │          │
    Headset     Speaker    Speaker
       │          │          │
      L/R        Room A     Room B
```

Bir ses kaynağı birden fazla hedefe yönlendirilebilir.

Bu, kablosuz sesin yalnızca “PC → tek kulaklık” bağlantısı olmaktan çıkıp bir **audio distribution service** haline gelmesini sağlar.

Bluetooth LE Audio'da da birden fazla bağımsız ve senkronize ses akışının gruplanması mümkün; NEXSUS burada aynı prensibi daha genel bir NWL servis mimarisinin parçası olarak ele alabilir.

---

# 15. Klavye ve Mouse

Klavye/mouse gibi cihazlar sürekli yüksek bant genişliği istemez.

Asıl gereksinimleri:

- çok düşük gecikme
- düşük güç
- yüksek güvenilirlik
- kısa paket
- hızlı uyandırma

olacaktır.

Örneğin:

```text
Mouse Event

X = +12
Y = -3
Button = 0
Wheel = 0
Timestamp = ...
```

Bu olayın yüzlerce byte taşımasına gerek yoktur.

NWL protokolü küçük kontrol paketlerini mümkün olduğunca düşük overhead ile taşımalıdır.

---

# 16. Uyku ve Uyanma

Kablosuz çevre birimleri için güç tüketimi önemlidir.

Cihaz:

```text
ACTIVE
   ↓
IDLE
   ↓
SLEEP
```

durumlarına geçebilir.

Kullanıcı mouse'u hareket ettirdiğinde:

```text
Mouse
  ↓
Wake
  ↓
NWL Link
  ↓
NWC
  ↓
System Fabric
  ↓
CPU
```

Bu işlem çok düşük gecikmeli olmalıdır.

---

# 17. Bağlantı Durumları

NWL cihaz durum makinesi:

```text
                    ┌──────────────┐
                    │  DISCOVERY   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ IDENTIFIED   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ CAPABILITY   │
                    │  DISCOVERY   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │  AUTHENTICATE│
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │   ACTIVE     │
                    └──────┬───────┘
                       ┌───┴────┐
                       ↓        ↓
                     IDLE     SLEEP
```

Bağlantı koparsa sistem doğrudan cihazı silmek yerine:

```text
ACTIVE
  ↓
LINK LOST
  ↓
RECONNECT
  ↓
ACTIVE
```

şeklinde çalışabilir.

---

# 18. Güvenlik

NWL'de güvenlik yalnızca bağlantı sırasında parola sormaktan ibaret olmamalıdır.

Her cihaz için:

```text
Device Identity
      +
Authentication
      +
Session Key
      +
Channel Permission
```

mantığı kullanılmalıdır.

Örneğin bir mouse:

```text
HID       ✓
Audio     ✗
Storage   ✗
Camera    ✗
```

Telefon:

```text
Audio       ✓
Microphone  ✓
Camera      kullanıcı izni
Storage     kullanıcı izni
Application kullanıcı izni
```

şeklinde yetkilendirilebilir.

Böylece **cihazın bağlanmış olması bütün yetkileri aldığı anlamına gelmez.**

---

# 19. Telefonun NWL İçindeki Konumu

Telefon özel bir cihaz sınıfı olarak değerlendirilebilir.

Bağlandığında yalnızca:

```text
Bluetooth Audio
```

gibi tek bir servis açmak yerine:

```text
                    PHONE
                      │
       ┌──────────────┼───────────────┐
       │              │               │
     AUDIO          CAMERA         DATA
       │              │               │
  MICROPHONE     NOTIFICATION    APPLICATION
                      │
                   CONTROL
```

şeklinde bir servis kümesi oluşturabilir.

Bu durumda telefon, NEXSUS sisteminin kablosuz bir uzantısı haline gelir.

Örneğin:

```text
Telefon kamerası
      ↓
NWL
      ↓
NWC
      ↓
System Fabric
      ↓
FAPU / CPU
```

veya:

```text
Telefon mikrofonu
      ↓
NWL
      ↓
NWC
      ↓
Audio Service
```

şeklinde çalışabilir.

---

# 20. NWL ve System Fabric

NWL'nin System Fabric ile bağlantısı doğrudan düşünülmelidir.

```text
                  NEXSUS SYSTEM FABRIC
                          │
                     ┌────┴────┐
                     │   NWC   │
                     └────┬────┘
                          │
                   WIRELESS LINK
                          │
          ┌───────────────┼───────────────┐
          │               │               │
       Keyboard         Headset         Phone
```

NWC gelen veriyi doğrudan uygun fabric hedefine aktarabilir.

Örneğin mouse:

```text
Mouse
 ↓
NWC
 ↓
Fabric
 ↓
CPU Input Service
```

Büyük bir veri:

```text
Phone
 ↓
NWC
 ↓
Fabric
 ↓
Data MOSRAM
```

Audio:

```text
Headset
 ↓
NWC
 ↓
Fabric
 ↓
Audio Buffer
```

Dolayısıyla CPU her paketin ara durağı olmak zorunda değildir.

---

# 21. Wireless → MOSRAM

NWL ile MOSRAM arasında doğrudan veri yolu bulunması özellikle önemlidir.

Örneğin telefon 1 GB veri gönderiyorsa:

Klasik yaklaşım:

```text
Wireless
   ↓
CPU
   ↓
RAM
```

NWL/NEXSUS yaklaşımı:

```text
Wireless
   ↓
NWC
   ↓
System Fabric
   ↓
Data MOSRAM
```

CPU yalnızca gerekli olduğunda veriye erişir.

Bu, System Fabric'in temel prensibiyle doğrudan uyumludur:

> **Veriyi işlemci üzerinden geçirmek yerine, mümkün olduğunca verinin bulunduğu yere yönlendirmek.**

---

# 22. Wireless → FAPU

Benzer şekilde:

```text
Wireless
    ↓
NWC
    ↓
System Fabric
    ↓
FAPU
```

mümkün olmalıdır.

Örneğin dışarıdan gelen şifreli veri:

```text
Phone
 ↓
NWL
 ↓
NWC
 ↓
FAPU
 ↓
Data MOSRAM
```

şeklinde işlenebilir.

CPU yalnızca kontrol ve sonuç gerektiğinde devreye girebilir.

---

# 23. Wireless Controller'ın CPU'dan Bağımsız Çalışması

NWC'nin bazı işlemleri CPU çalışmadan da gerçekleştirilebilmelidir.

Örneğin:

- cihaz keşfi
- bağlantı sürdürme
- uyku/uyanma
- bağlantı güvenliği
- paket zamanlaması
- cihaz durum takibi

Sistem düşük güç modundayken:

```text
CPU = OFF / SLEEP

SCP ───── System Control
 │
 NWC ──── Wireless Control
 │
 MOSRAM ─ gerekli düşük güç durumu
```

şeklinde çalışabilir.

Bu, NEXSUS'un genel “küçük kontrol işlemcileriyle ana CPU'nun yükünü azaltma” yaklaşımıyla uyumludur.

---

# 24. NWC + SCP İlişkisi

NWC ile SCP'nin görevleri ayrılmalıdır.

### NWC

Kablosuz iletişim:

- radio
- scheduling
- device management
- wireless security
- channel management

### SCP

Sistem:

- power
- reset
- thermal
- board state
- firmware
- hardware state

Örneğin:

```text
SCP
 │
 ├── NWC'yi aç
 ├── güç durumunu ayarla
 └── hata durumunu izle

NWC
 │
 ├── cihazları keşfet
 ├── bağlantıları yönet
 └── kablosuz trafiği zamanla
```

Böylece iki işlemci aynı işi yapmaz.

---

# 25. Fiziksel Radyo Yapısı

Bu aşamada belirli bir frekans veya mevcut standart seçmek gerekmemektedir.

NWL'nin fiziksel katmanı daha sonra belirlenebilir.

Önemli olan protokolün fiziksel katmandan ayrılmasıdır:

```text
NWL
 │
 ├── Service Layer
 ├── Session Layer
 ├── Link Layer
 └── Physical Radio Layer
```

Böylece ileride:

```text
Radio A
Radio B
Radio C
```

gibi farklı fiziksel uygulamalar mümkün olabilir.

---

# 26. Tek Radyo Zorunlu Değil

“Tek alıcı” demek mutlaka “tek anten/tek RF zinciri” demek değildir.

NWC fiziksel olarak birden fazla radyo zincirine sahip olabilir:

```text
              NWC
               │
       ┌───────┼────────┐
       │       │        │
     RF-A    RF-B     RF-C
       │       │        │
     Device  Device   Device
```

Ama işletim sistemi açısından bunların tamamı:

```text
             ONE
       NEXSUS WIRELESS
            DOMAIN
```

olarak görünür.

Bu ayrım önemlidir.

---

# 27. Birleşik Wireless Domain

Kullanıcı açısından:

```text
Settings
   ↓
NEXSUS Wireless
   │
   ├── Keyboard
   ├── Mouse
   ├── Headset
   ├── Phone
   ├── Speaker
   └── Controller
```

gibi tek bir sistem görünümü oluşur.

Her cihazın ayrı Bluetooth menüsü, ayrı dongle'ı veya ayrı özel yönetim yazılımı bulunması hedeflenmez.

---

# 28. NWL'nin Temel Teknik Katmanları

Sonraki ayrıntılı tasarım için NWL şu katmanlara ayrılabilir:

```text
┌─────────────────────────────┐
│ Application Services        │
├─────────────────────────────┤
│ Device Services             │
├─────────────────────────────┤
│ Logical Channel Layer       │
├─────────────────────────────┤
│ Session / Security Layer    │
├─────────────────────────────┤
│ Link Management Layer       │
├─────────────────────────────┤
│ Wireless Scheduler          │
├─────────────────────────────┤
│ Radio / PHY                 │
└─────────────────────────────┘
```

Bunun üzerinde System Fabric bulunur:

```text
Applications
     │
System Services
     │
System Fabric
     │
NWC
     │
NWL Protocol
     │
Radio
     │
Wireless Device
```

---

# 29. Temel Tasarım İlkeleri

NWL'nin ilkeleri:

1. **Tek kablosuz sistem alanı**
2. **Tek merkezi Wireless Controller**
3. **Çoklu cihaz**
4. **Cihaz başına çoklu mantıksal kanal**
5. **Capability Discovery**
6. **Dinamik kanal tahsisi**
7. **Öncelikli trafik**
8. **Gerçek zamanlı akış desteği**
9. **Düşük gecikmeli HID**
10. **Çoklu audio/video akışı**
11. **Cihaz bazlı yetkilendirme**
12. **Doğrudan System Fabric erişimi**
13. **CPU'dan bağımsız temel bağlantı yönetimi**
14. **SCP ile güç/yönetim ayrımı**
15. **Farklı fiziksel radyo katmanlarına açık mimari**

---

# 30. NEXSUS Wireless Link'in Farkı

Buradaki amaç yeni bir “Bluetooth alternatifi” üretmekten daha geniştir.

Bluetooth gibi mevcut sistemler bugün zaten çoklu bağlantı, cihaz keşfi, HID ve zamanlanmış ses akışları gibi birçok özelliği sağlayabiliyor.

NWL'nin asıl mimari farkı:

```text
Geleneksel yaklaşım

DEVICE
   ↓
PROTOCOL
   ↓
DRIVER
   ↓
OS
```

yerine:

```text
                  NEXSUS SYSTEM

DEVICE
   ↓
NWL
   ↓
NWC
   ↓
SYSTEM FABRIC
   ↓
SERVICE / MEMORY / PROCESSOR
```

yapısının kurulmasıdır.

Kablosuz iletişim böylece işletim sisteminin sonradan eklenmiş bir çevre birimi özelliği değil, **NEXSUS sistem mimarisinin doğal bir parçası** haline gelir.

---

# 31. Sonraki Tasarım Aşaması

NWL'nin kavramsal mimarisi bundan sonra beş teknik bölüme ayrılabilir:

```text
NWL
 │
 ├── 1. Radio / PHY
 │
 ├── 2. Packet / Frame Structure
 │
 ├── 3. Channel & Scheduler
 │
 ├── 4. Device Discovery / Security
 │
 └── 5. System Fabric Interface
```

Bunların içinde özellikle **Channel + Scheduler** kısmı önemlidir.

Çünkü NWL'nin asıl özgün mimari problemi:

> Aynı anda onlarca cihazı, farklı gecikme ve bant genişliği ihtiyaçlarıyla, tek bir sistem olarak nasıl zamanlayacağız?

sorusudur.

