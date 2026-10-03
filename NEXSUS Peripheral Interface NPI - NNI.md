# NEXSUS Peripheral Interface (NPI) - NEXSUS Network Interface (NNI) 
## Seri Kablolu Çevre Birimi Bağlantısı ve Fiber Optik Ağ Mimarisi

**Sistem:** NEXSUS  
**Alt Sistemler:** NPI + NNI 
**Durum:** Kavramsal + Ön Teknik Mimari  
**Mimari Sürüm:** NPI-1

---

# 1. Genel Yaklaşım

NEXSUS'ta kablolu bağlantı mimarisi iki ayrı probleme ayrılır:

\[
\boxed{Peripheral\ Connectivity}
\]

ve

\[
\boxed{Network\ Connectivity}
\]

Çevre birimleri için:

\[
\boxed{NPI}
\]

kullanılır.

Yerel ağ ve Internet bağlantısı için:

\[
\boxed{NEXSUS\ Optical\ Network}
\]

kullanılır.

Bu ayrım önemlidir.

NPI bir bilgisayarın çevre birimleriyle konuşur.

Fiber ağ bağlantısı ise bilgisayarı başka bilgisayarlar, switch'ler, sunucular ve Internet altyapısıyla bağlar.

---

# 2. NPI Nedir?

NPI:

\[
\boxed{NEXSUS\ Peripheral\ Interface}
\]

olarak tanımlanır.

NPI, USB'nin doğrudan kopyası değildir.

Temel amacı:

> NEXSUS üzerindeki farklı çevre birimlerini tek bir seri fiziksel bağlantı ailesi üzerinden, ortak bir paketleme ve yönlendirme mimarisiyle bağlamak.

olur.

NPI'nin temel mantığı:

```text
Physical Link
      ↓
NPI Link
      ↓
NPI Channel
      ↓
Service
      ↓
Device
```

Dolayısıyla fiziksel bağlantı ile cihaz protokolü birbirinden ayrılır.

---

# 3. NPI'nin Temel İlkesi

NWL'de olduğu gibi NPI'de de:

\[
\boxed{Device \neq Link}
\]

olmalıdır.

Bir fiziksel NPI bağlantısı üzerinde aynı anda:

```text
Keyboard
Mouse
Audio
Microphone
Camera
Storage
Display
Phone
Control
```

gibi farklı servisler bulunabilir.

Örneğin tek bir NPI kablosu:

```text
NEXSUS
   │
   │ NPI
   │
   ▼
Dock
 ├── Keyboard
 ├── Mouse
 ├── Display
 ├── Audio
 ├── SSD
 └── Phone
```

şeklinde kullanılabilir.

Bu nedenle NPI'nin temel birimi cihaz değil **kanal/servis** olur.

---

# 4. Seri İletişim

NPI paralel veri yolu yerine yüksek hızlı seri bağlantı kullanır.

Temel yapı:

\[
\boxed{
Parallel\ Internal\ Fabric
\rightarrow
Serial\ External\ Link
}
\]

olur.

Bilgisayarın içerisinde NSF geniş ve paralel olabilir.

Anakart dışına çıkıldığında ise veri seri olarak taşınır.

```text
NEXSUS Internal Fabric
        │
        ▼
   NPI Controller
        │
   Serial PHY
        │
   Connector
        │
      Cable
        │
   Peripheral
```

Böylece yüksek hızlı paralel anakart hatlarını kasanın dışına çıkarmak gerekmez.

---

# 5. NPI Fiziksel Bağlantısı

İlk NPI sürümünde fiziksel konnektör olarak USB-C sınıfında küçük, ters çevrilebilir bir konnektör kullanılabilir.

Ancak:

\[
NPI \neq USB
\]

olur.

Konnektör yalnızca fiziksel mekanik standarttır.

Protokol tamamen NEXSUS'a ait olabilir.

Bu yaklaşımın avantajı mevcut kablo/konnektör ekosisteminden yararlanırken protokolü NEXSUS için özgürce tasarlayabilmektir.

---

# 6. NPI Lane Yapısı

NPI fiziksel olarak birden fazla seri lane içerebilir.

Örneğin:

```text
              NPI
        ┌───────────────┐
        │ TX0     RX0   │
        │ TX1     RX1   │
        │ TX2     RX2   │
        │ TX3     RX3   │
        │ Power        │
        │ Control      │
        └───────────────┘
```

Böylece:

\[
N_{lane}=1,2,4
\]

gibi farklı fiziksel konfigürasyonlar mümkün olabilir.

Ancak lane sayısı ilk aşamada kesinleştirilmez.

Önemli olan protokolün lane sayısından bağımsız olmasıdır.

---

# 7. Lane Bonding

Bir veri akışı yüksek hız gerektiriyorsa birden fazla lane birlikte kullanılabilir.

```text
                Stream
                  │
           ┌──────┴──────┐
           │             │
         Lane 0        Lane 1
           │             │
           └──────┬──────┘
                  │
              Reassembly
```

Dolayısıyla:

\[
Bandwidth_{total}
\approx
N_{lane}\times Bandwidth_{lane}
\]

olur.

Bu yaklaşım ileride NPI'nin hızının artırılmasını kolaylaştırır.

---

# 8. NPI Paket Mimarisi

Kavramsal NPI frame:

```text
┌──────────┬──────────┬──────────┬────────────┬──────────┐
│ PHY      │ NPI      │ Channel  │ Payload    │ CRC      │
│ Header   │ Header   │ Info     │            │          │
└──────────┴──────────┴──────────┴────────────┴──────────┘
```

NPI Header içerisinde:

```text
Version
Frame Type
Device ID
Service ID
Channel ID
Sequence
Priority
Length
Flags
```

gibi alanlar bulunabilir.

Kesin bit genişlikleri sonraki protokol tasarımında belirlenecektir.

---

# 9. NPI Channel Yapısı

Bir fiziksel bağlantıda:

```text
NPI Link
 ├── Control Channel
 ├── HID Channel
 ├── Audio Channel
 ├── Camera Channel
 ├── Storage Channel
 ├── Display Channel
 └── Data Channel
```

bulunabilir.

Böylece tek kablo farklı veri türlerini taşıyabilir.

---

# 10. QoS

NPI de NWL'deki gibi veri türlerini birbirinden ayırmalıdır.

Örneğin:

| Öncelik | Kanal | Özellik |
|---|---|---|
| P0 | System Control | Kritik |
| P1 | HID | Düşük gecikme |
| P2 | Audio | Zaman kritik |
| P3 | Display | Yüksek sürekli hız |
| P4 | Storage | Yüksek throughput |
| P5 | Background | Artan boş kapasite |

Örneğin 2 TB harici SSD'den veri aktarılırken mouse hareketlerinin gecikmemesi gerekir.

Dolayısıyla:

\[
Storage \neq HID
\]

olarak scheduler seviyesinde ayrılır.

---

# 11. NPI ve System Fabric

NPI doğrudan System Fabric'e bağlanmalıdır.

```text
                NEXSUS SYSTEM FABRIC
                         │
             ┌───────────┼───────────┐
             │           │           │
            CPU         FAPU        NPI
                                     │
                           ┌─────────┼─────────┐
                           │         │         │
                         Audio    Storage    Display
```

Bu sayede harici SSD'den gelen veri:

```text
NPI
 ↓
Data MOSRAM
```

şeklinde CPU'yu gereksiz yere araya sokmadan aktarılabilir.

Benzer şekilde:

```text
NPI Camera
     ↓
NPI Controller
     ↓
FAPU
```

mümkün olabilir.

---

# 12. NPI ve Güç

NPI'nin veri ve güç tarafı birbirinden ayrılmalıdır.

```text
NPI Connector
 ├── Data
 ├── Control
 └── Power
```

Bu sayede:

- klavye
- mouse
- telefon
- kulaklık
- küçük SSD
- kamera

gibi cihazlar tek kablo üzerinden çalışabilir.

Ancak güç sınırları cihaz sınıfına göre belirlenmelidir.

Yüksek güç isteyen cihazlar için ayrı güç girişi bulunabilir.

---

# 13. NPI Hot Plug

NPI bağlantıları çalışma sırasında takılıp çıkarılabilir.

Bağlantı süreci:

```text
Cable Insert
     ↓
PHY Detect
     ↓
Link Training
     ↓
Device Discovery
     ↓
Capability Discovery
     ↓
Service Discovery
     ↓
Resource Allocation
     ↓
ACTIVE
```

Çıkarma durumunda:

```text
Link Lost
   ↓
Services Closed
   ↓
Resources Released
```

uygulanır.

---

# 14. Link Training

NPI bağlantısı açılırken iki taraf önce fiziksel hattı test eder.

```text
NEXSUS
   │
   │ Training
   ▼
Peripheral
```

Karşılıklı olarak:

- lane sayısı
- hız
- encoding
- link quality
- hata seviyesi
- güç durumu

belirlenebilir.

Sonrasında en uygun ortak mod seçilir.

Örneğin:

\[
4\ Lane
\rightarrow
2\ Lane
\]

veya:

\[
80\ Gbps
\rightarrow
40\ Gbps
\]

gibi düşüşler mümkün olabilir.

Amaç bağlantının tamamen kopması yerine güvenilir daha düşük hızda çalışabilmesidir.

---

# 15. NPI Hızlandırılabilir Mimari

Bugün USB4 80 Gbps sınıfına ulaşmış durumdadır ve tek bağlantı üzerinde farklı veri/display protokollerinin paylaşımını destekler.

NEXSUS'un NPI'si başlangıçta mevcut teknolojiyi yakalamaya çalışmak yerine mimariyi daha yüksek hızlara açık bırakmalıdır.

Örneğin:

\[
NPI-40
\]

\[
NPI-80
\]

\[
NPI-160
\]

gibi hız sınıfları daha sonra tanımlanabilir.

Burada önemli olan protokolün hızdan bağımsız tasarlanmasıdır.

---

# 16. NPI'nin USB'den Farkı

NPI'nin amacı USB'den daha fazla özellik eklemek değildir.

Fark daha temel düzeydedir.

USB:

\[
Peripheral\ Bus/Interconnect
\]

olarak gelişmiştir.

NPI:

\[
\boxed{NEXSUS\ System\ Fabric\ Extension}
\]

olarak tasarlanır.

Bu nedenle NPI:

```text
Peripheral
   ↓
NPI
   ↓
System Fabric
```

şeklinde doğrudan sistem mimarisinin parçasıdır.

---

# 17. Fiber Optik Ağ

NEXSUS'un network bağlantısında bakır Ethernet yerine fiber optik bağlantı temel seçenek olarak belirlenebilir.

\[
\boxed{
NEXSUS\ Network
=
Optical\ Ethernet
}
\]

Bunun önemli avantajları:

- elektromanyetik girişimden etkilenmeme
- elektriksel izolasyon
- yüksek bant genişliği
- uzun kablo mesafesi
- düşük ağırlık
- gelecekte hız yükseltme kolaylığı

olmasıdır.

Ethernet ekosisteminde SFP/SFP28/SFP56 gibi takılabilir optik arayüzler 25 GbE ve 50 GbE sınıflarına kadar kullanılan fiziksel seçenekler sunmaktadır.

---

# 18. NEXSUS Optical Network Interface

Anakart üzerinde:

\[
\boxed{NONI = NEXSUS\ Optical\ Network\ Interface}
\]

adıyla bir ağ denetleyicisi tanımlanabilir.

```text
NEXSUS
   │
System Fabric
   │
   ▼
NONI
   │
Optical PHY
   │
SFP / Optical Module
   │
Fiber
   │
Switch / Router
```

NONI doğrudan System Fabric'e bağlanabilir.

---

# 19. Neden Cat6/Cat7 Kullanılmıyor?

NEXSUS tasarımında Cat6/Cat7 tamamen yasaklanmak zorunda değildir.

Ancak **ana ağ bağlantısı olarak fiber tercih edilir.**

Bunun nedeni NEXSUS'un:

- yüksek hızlı
- düşük EMI
- modüler
- uzun ömürlü
- gelecekte yükseltilebilir

bir platform olarak tasarlanmasıdır.

Bakır Ethernet özellikle masaüstü bilgisayarlarda oldukça kullanışlıdır; fakat NEXSUS'un yeni bir mimari olması nedeniyle fiziksel ağ katmanında fiberi temel almak daha tutarlı olabilir.

---

# 20. Fiberin Güç Sorunu

Fiberin önemli bir dezavantajı vardır:

\[
Fiber \neq Power
\]

Optik kablo normal durumda cihazı beslemez.

Dolayısıyla:

```text
Fiber
 └── Data

Power
 └── Separate
```

olmalıdır.

Bu durum NPI'de sorun değildir çünkü NPI çevre birimlerine güç sağlayabilir.

Ağ bağlantısında ise ağ cihazlarının çoğu zaten ayrı güç kaynağına sahiptir.

---

# 21. Fiber Connector

İlk NEXSUS masaüstü tasarımında optik ağ için modüler bir yapı tercih edilebilir.

Örneğin:

```text
NEXSUS
┌─────────────────────┐
│ Optical Network     │
│                     │
│ [ SFP ] [ SFP ]     │
└─────────────────────┘
```

şeklinde iki port bulunabilir.

İki portun görevleri:

```text
Port 0 → Main Network
Port 1 → Secondary / High Speed / Redundant
```

olabilir.

Böylece iki fiziksel fiber bağlantı kullanılabilir.

---

# 22. 25 / 50 / 100 GbE

NEXSUS'un ilk modelinde 25 veya 50 GbE sınıfı bir optik bağlantı değerlendirilebilir.

Ethernet ekosisteminde:

\[
25GbE \rightarrow SFP28
\]

ve:

\[
50GbE \rightarrow SFP56
\]

gibi fiziksel modül sınıfları bulunmaktadır.

İleride:

\[
100GbE
\]

ve üzeri bağlantılar için daha yüksek lane sayılı optik modüllere geçilebilir.

Bu nedenle network PHY'nin anakarta sabit bir hızla gömülmesi yerine modüler optik transceiver mimarisi tercih edilebilir.

---

# 23. Fiber Ağın NEXSUS System Fabric'e Bağlanması

En önemli noktalardan biri:

Network verisinin zorunlu olarak CPU'dan geçmemesidir.

Örneğin:

```text
Fiber Network
      │
     NONI
      │
      ▼
 Data MOSRAM
```

veya:

```text
Fiber Network
      │
     NONI
      │
      ▼
     FAPU
```

mümkün olabilir.

CPU yalnızca gerçekten gerekli olduğunda devreye girer.

Bu yapı NSF'nin temel ilkesini korur:

\[
\boxed{
Minimize\ Unnecessary\ Data\ Movement
}
\]

---

# 24. Fiber + M-SSD

Ağdan gelen büyük veri doğrudan depolama sistemine aktarılabilir.

Örneğin:

```text
Network
   │
Fiber
   │
NONI
   │
System Fabric
   │
   ▼
M-SSD
```

veya:

```text
M-SSD
  │
  ▼
NONI
  │
  ▼
Network
```

CPU'nun her byte'ı işleme zorunluluğu ortadan kaldırılabilir.

Bu özellikle:

- NAS
- network backup
- dosya sunucusu
- medya sunucusu
- yüksek hızlı yerel ağ

uygulamalarında önemlidir.

---

# 25. Fiber Ağda İki Portlu Yapı

NEXSUS'un üst seviye modellerinde iki bağımsız optik port kullanılabilir.

```text
                NEXSUS
                  │
          ┌───────┴───────┐
          │               │
        NONI-0          NONI-1
          │               │
       Fiber A         Fiber B
          │               │
       Network         Network
```

Bunlar:

- redundancy
- link aggregation
- ayrı network
- yüksek toplam throughput

için kullanılabilir.

Ancak ilk modelde tek fiber port yeterli olabilir.

---

# 26. NPI + NWL + Fiber

NEXSUS'un dış iletişim mimarisi böylece üç parçaya ayrılır:

```text
                    NEXSUS
                       │
        ┌──────────────┼──────────────┐
        │              │              │
       NPI            NWL          Optical
     Kablolu        Kablosuz        Network
        │              │              │
  Peripheral       Peripheral      Network
```

### NPI

Yüksek hızlı fiziksel çevre birimleri.

### NWL

Kablosuz çevre birimleri.

### Optical Network

Ağ iletişimi.

Bu üç sistem birbirinin yerine geçmez.

---

# 27. Fiziksel Bağlantı Haritası

NEXSUS anakartında dış bağlantılar kabaca:

```text
                NEXSUS ANAKART
┌─────────────────────────────────────────┐
│                                         │
│              NEXSUS CPU                 │
│                  │                      │
│           Application MOSRAM             │
│                                         │
│ FAPU      NPU       SCP       NWC       │
│  │         │         │         │        │
│  └─────────┴─────────┴─────────┘        │
│                │                        │
│          SYSTEM FABRIC                  │
│                │                        │
│      ┌─────────┴──────────┐             │
│      │                    │             │
│     NPI                  NONI           │
│      │                    │             │
└──────┼────────────────────┼─────────────┘
       │                    │
   Peripheral              Fiber
       │                    │
   USB-C class          Optical Network
```

---

# 28. Bağlantıların Görev Dağılımı

| Bağlantı | Ana kullanım |
|---|---|
| NPI | Kablolu çevre birimleri |
| NWL | Kablosuz çevre birimleri |
| Optical Network | LAN / Internet |
| System Fabric | Dahili bileşenler |
| M-SSD Interface | Dahili kalıcı depolama |
| MOSRAM Interface | Dahili bellek |

Bu ayrım sayesinde tek bir bağlantıya bütün görevleri yüklemek gerekmez.

---

# 29. Temel Tasarım İlkesi

NEXSUS dış bağlantı mimarisinin temel prensibi:

\[
\boxed{
\text{Doğru veri için doğru fiziksel taşıyıcı}
}
\]

olur.

Örneğin:

```text
Mouse
 → NWL / NPI

External SSD
 → NPI

Wireless Speaker
 → NWL

LAN
 → Fiber

Internet
 → Fiber

Internal CPU ↔ MOSRAM
 → System Fabric
```

Bu yaklaşım klasik bilgisayarlardaki “her şeyi USB/Ethernet üzerinden çözme” yaklaşımından ayrılır.

---

# 30. İlk NEXSUS Bağlantı Profili

Başlangıç için:

### NPI

- yüksek hızlı seri
- ters çevrilebilir küçük konnektör
- çoklu lane
- lane bonding
- QoS
- hot plug
- power + data
- System Fabric doğrudan bağlantısı

### NWL

- 4 bağımsız RF
- 1 × 2.4 GHz
- 3 × 6 GHz
- Channel Fabric
- Radio Fabric

### Network

- fiber optik
- modüler optical PHY
- başlangıçta 25/50 GbE sınıfı değerlendirilebilir
- ileride 100 GbE+
- tercihen 1 veya 2 optik port

---

# 31. Sonuç

NEXSUS'un kablolu bağlantı mimarisi klasik PC'deki gibi:

\[
USB + Ethernet + Bluetooth
\]

şeklinde birbirinden kopuk sistemler olarak tasarlanmaz.

Bunun yerine:

\[
\boxed{
NPI + NWL + Optical\ Network
}
\]

şeklinde üç tamamlayıcı dış bağlantı sistemi oluşturulur.

NPI:

\[
\boxed{Kablolu\ Peripheral\ Fabric}
\]

NWL:

\[
\boxed{Kablosuz\ Peripheral\ Fabric}
\]

Optical Network:

\[
\boxed{Network\ Fabric}
\]

olarak düşünülebilir.

Üçü de NEXSUS System Fabric'e bağlanır.

Böylece:

```text
                         NEXSUS
                            │
                    SYSTEM FABRIC
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
      NPI                  NWL              OPTICAL NET
       │                    │                    │
   Kablolu              Kablosuz              Fiber
 Peripheral            Peripheral            Network
       │                    │                    │
       └────────────────────┴────────────────────┘
```

oluşur.

Bu yapı NEXSUS'un genel felsefesiyle uyumludur: **fiziksel bağlantıyı, veri türünü ve sistem kaynağını birbirinden ayırmak; ardından bunları System Fabric üzerinden doğrudan ve mümkün olduğunca kısa veri yollarıyla birleştirmek.**
----


## 11. NEXSUS Display Mimarisi ve NPI Display Desteği

NEXSUS mimarisinde görüntü aktarımının tamamının NPI üzerinden gerçekleştirilmesi gerekli değildir. Özellikle anakart üzerinde doğrudan ekran bağlantısı için mevcut ve olgunlaşmış DisplayPort standardının kullanılması daha uygun bir çözümdür.

Bu nedenle görüntü sistemi iki ayrı kullanım yolu olarak ele alınır:

1. **Native DisplayPort:** Anakart üzerindeki ana ve yüksek performanslı ekran çıkışı.
2. **NPI Display:** İkincil ekranlar, dock yapıları, özel çevre birimleri ve NPI üzerinden bağlanan görüntü cihazları.

Böylece NPI çok amaçlı bir çevre birimi bağlantısı olarak kalırken, yüksek bant genişlikli ana görüntü yolu için özel DisplayPort fiziksel bağlantısı kullanılır.

### 11.1 Native DisplayPort

NEXSUS anakartında bir veya daha fazla doğrudan DisplayPort çıkışı bulunabilir.

Temel hedef:

| Özellik | NEXSUS hedefi |
|---|---|
| Bağlantı | Native DisplayPort |
| Hedef standart | DisplayPort 2.1 sınıfı / güncel uyumlu sürüm |
| Fiziksel bağlantı | 4 lane |
| Hedef maksimum link | UHBR20 sınıfı, 80 Gbps |
| Hedef çözünürlük | En az 8K |
| 8K hedefi | 7680×4320 @ 60 Hz |
| Renk | 4:4:4 |
| HDR | Desteklenecek |
| Ses | Çok kanallı DisplayPort Audio |
| DSC | Desteklenecek |
| Adaptive Sync | Desteklenecek |

DisplayPort 2.x ailesinde UHBR20, dört lane üzerinden 80 Gbps bağlantı hızına ulaşabilir. VESA, bu sınıfın 8K/60 Hz, 4:4:4 ve HDR gibi yüksek bant genişlikli ekran yapılarını desteklediğini belirtmektedir.

Dolayısıyla NEXSUS için ana ekran bağlantısında yeni bir görüntü protokolü geliştirmek yerine mevcut DisplayPort standardının doğrudan kullanılması, geliştirme yükünü azaltırken yüksek çözünürlük ve çoklu ekran desteğini hazır bir ekosistem üzerinden sağlar.

### 11.2 Display Controller → DisplayPort

Görüntü yolu System Fabric üzerinde şu şekilde modellenir:

```text
                    SYSTEM FABRIC
                         │
                         ▼
                DISPLAY CONTROLLER
                         │
             ┌───────────┴───────────┐
             │                       │
          DP PHY 0                DP PHY 1
             │                       │
          DP OUT 0                DP OUT 1
             │                       │
          Ekran 1                  Ekran 2
```

Burada Display Controller, görüntü verisini doğrudan DisplayPort fiziksel katmanına aktarır.

Bu yolun temel amacı:

```text
Görüntü üretimi
      ↓
Display Controller
      ↓
DP PHY
      ↓
DisplayPort
      ↓
Monitör
```

şeklinde mümkün olduğunca doğrudan bir veri yolu oluşturmaktır.

CPU'nun her görüntü paketini yazılımsal olarak taşıması veya NPI üzerinden yeniden yönlendirmesi gerekmez.

### 11.3 NPI Display

NPI'daki Display desteği ise korunur.

Bunun amacı NPI'yi yalnızca klavye, mouse, depolama ve benzeri düşük/orta bant genişlikli çevre birimleriyle sınırlamamak; gerektiğinde ekran cihazlarının da aynı çok amaçlı bağlantı mimarisine dahil edilebilmesini sağlamaktır.

Örneğin:

```text
NEXSUS
   │
System Fabric
   │
  NPI
   │
   ├── Keyboard
   ├── Mouse
   ├── Camera
   ├── Audio
   ├── Storage
   ├── Phone
   └── Display
```

Bu durumda NPI Display aşağıdaki kullanım alanlarına sahip olabilir:

- ikinci veya üçüncü ekran,
- taşınabilir ekran,
- NPI dock üzerinden ekran,
- özel endüstriyel ekran,
- kontrol paneli,
- kamera/ekran birleşik cihazları,
- özel NEXSUS çevre birimleri.

NPI üzerinden görüntü aktarımı, NPI'nin çoklu servis ve kanal mimarisinin bir servisi olarak ele alınır:

```text
NPI Link
    │
    ├── CONTROL
    ├── HID
    ├── AUDIO
    ├── DATA
    ├── STORAGE
    ├── CAMERA
    └── DISPLAY
```

Dolayısıyla **NPI Display vardır; ancak NPI, NEXSUS'un ana ekran bağlantısı olmak zorunda değildir.**

### 11.4 Native DP ve NPI Display Arasındaki Ayrım

Bu iki yol birbirinin alternatifi değil, tamamlayıcı bağlantılardır.

| Özellik | Native DisplayPort | NPI Display |
|---|---|---|
| Ana ekran | **Evet** | Gerekmez |
| İkincil ekran | Evet | **Evet** |
| Yüksek bant genişliği | **Öncelikli** | Gerektiğinde |
| Çok amaçlı çevre birimi | Hayır | **Evet** |
| Klavye/mouse | Hayır | **Evet** |
| Depolama | Hayır | **Evet** |
| Kamera | Hayır | **Evet** |
| Ses | DP Audio | NPI Audio |
| Dock | Doğrudan değil | **Evet** |
| Standart | DisplayPort | NPI |
| System Fabric bağlantısı | Display Controller üzerinden | NPI Controller üzerinden |

Bu ayrım sayesinde NPI'nin tasarımında ekran desteği korunurken, NPI'nin bütün sistemin görüntü altyapısını taşıması gibi gereksiz bir zorunluluk oluşmaz.

### 11.5 Çoklu Ekran

NEXSUS anakartında birden fazla native DisplayPort çıkışı bulunabilir.

Örneğin:

```text
                    SYSTEM FABRIC
                         │
                 DISPLAY CONTROLLER
                         │
             ┌───────────┼───────────┐
             │           │           │
            DP0         DP1         DP2
             │           │           │
          Ekran 1     Ekran 2     Ekran 3
```

Buna ek olarak NPI üzerinden başka bir ekran bağlanabilir:

```text
DP0 ───────────── Ana ekran
DP1 ───────────── İkinci ekran
DP2 ───────────── Üçüncü ekran
NPI ───────────── NPI Display
```

DisplayPort'un yüksek bant genişliği ve çoklu ekran yetenekleri bu tür yapıların oluşturulmasına olanak verir; VESA ayrıca DisplayPort 2.x/UHBR yapısının çoklu yüksek çözünürlüklü ekran senaryolarını desteklediğini belirtmektedir.

### 11.6 Ses

Native DisplayPort bağlantısı yalnızca görüntü taşımaz; DisplayPort üzerinden çok kanallı ses de aktarılabilir.

Bu nedenle:

```text
Display Controller
       │
       ├── Video
       └── Audio
              │
              ▼
       DisplayPort PHY
```

şeklinde tek bağlantı üzerinden ekran ve ekranın ses sistemi birlikte çalışabilir.

Bu, NEXSUS'un ayrıca ekran için ayrı bir ses kablosuna ihtiyaç duymasını önler.

### 11.7 NEXSUS Dış Bağlantı Mimarisi

Bu düzenlemeyle NEXSUS'un dış bağlantıları daha net bir şekilde ayrılmış olur:

```text
                         NEXSUS
                            │
                     SYSTEM FABRIC
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
      NPI                   NWL              DisplayPort
       │                    │                    │
  Kablolu I/O          Kablosuz I/O          Görüntü
       │                    │                 + Ses
       │                    │                    │
       │                    │              Native Display
       │                    │
       └──────────────┐     │
                      │     │
                 Çevre birimleri
                      
                            │
                     Optical Network
                            │
                          Fiber
                            │
                       LAN / Internet
```

Böylece dört temel dış bağlantı sınıfı oluşur:

| Sistem | Ana görev |
|---|---|
| **NPI** | Kablolu çevre birimleri ve harici veri |
| **NWL** | Kablosuz çevre birimleri |
| **DisplayPort** | Native görüntü + ekran sesi |
| **Optical Network** | LAN / Internet |

NPI'nin Display yeteneği ise bu yapının içinde **ikincil ve esnek bir görüntü taşıma seçeneği** olarak korunur.

### 11.8 Tasarım İlkesi

NEXSUS'un bağlantı mimarisindeki temel yaklaşım şu şekilde özetlenebilir:

> **Bir bağlantının her şeyi taşıyabilmesi, her şeyi o bağlantı üzerinden taşımamız gerektiği anlamına gelmez.**

Bu nedenle:

- yüksek performanslı native görüntü → **DisplayPort**
- çok amaçlı kablolu çevre birimleri → **NPI**
- kablosuz çevre birimleri → **NWL**
- yüksek hızlı ağ → **fiber optik**
- bütün bu sistemlerin dahili koordinasyonu → **System Fabric**

olarak ayrıştırılır.

Bu yapı, NEXSUS'un hem mevcut standartlardan yararlanmasını hem de yeni geliştirilen NPI/NWL mimarilerinin gereksiz yere mevcut ve güçlü standartların yerine geçirilmemesini sağlar.