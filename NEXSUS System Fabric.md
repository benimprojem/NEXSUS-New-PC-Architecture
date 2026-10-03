# NEXSUS System Fabric
## Kavramsal ve Teknik Mimari

### 1. Tanım

**NEXSUS System Fabric (NSF)**, NEXSUS bilgisayarındaki işlemciler, bellekler, depolama birimleri, sistem kontrol işlemcisi ve çevre birimleri arasındaki veri, kontrol ve durum iletişimini sağlayan ortak sistem bağlantı mimarisidir.

NSF klasik anlamda yalnızca bir veri yolu değildir.

Temel amacı:

> **Veriyi mümkün olduğunca kısa fiziksel ve mantıksal yol üzerinden, doğru işlem birimine ve doğru bellek bölgesine ulaştırmaktır.**

NEXSUS'ta fabric mimarisi, sistemin sonradan eklenen bir bağlantı katmanı değil, işlemci ve bellek yerleşimiyle birlikte tasarlanan temel mimari katmanlardan biridir.

---

# 2. Neden klasik bus yaklaşımı yeterli değildir?

Klasik bilgisayar mimarisinde farklı cihazlar için farklı bağlantı sistemleri bulunur:

```text
CPU
 │
 ├── Memory bus
 ├── PCIe
 ├── USB
 ├── SATA
 ├── Network
 └── çeşitli özel bağlantılar
```

Bu yapı her teknolojinin kendi gereksinimine göre gelişmiştir.

NEXSUS ise sistemin başından itibaren birlikte tasarlanması sayesinde bu ayrışmayı azaltabilir.

Temel yaklaşım:

```text
                NEXSUS SYSTEM FABRIC
                         │
        ┌────────────────┼────────────────┐
        │                │                │
       CPU              FAPU             NPU
        │                │                │
        ├──────── MOSRAM ┼────────────────┤
        │                │                │
       SCP              M-SSD            I/O
```

Böylece farklı birimler arasında ortak bir iletişim modeli oluşturulur.

---

# 3. Fabric'in üç temel iletişim sınıfı

NSF üzerinde üç temel iletişim türü bulunmalıdır:

### 3.1. Data

Gerçek veri taşınması.

Örneğin:

```text
MOSRAM → CPU
MOSRAM → FAPU
FAPU → MOSRAM
M-SSD → MOSRAM
CPU → I/O
```

### 3.2. Control

Birimin diğer birime işlem talimatı veya kontrol mesajı göndermesi.

Örneğin:

```text
CPU → FAPU
"Bu veri üzerinde işlemi başlat."

CPU → NPU
"Bu davranış modelini güncelle."

SCP → CPU
"Donanım durumu değişti."
```

### 3.3. Status

Birimin kendi durumunu bildirmesi.

Örneğin:

```text
FAPU → Fabric
BUSY

NPU → Fabric
MODEL_READY

M-SSD → Fabric
READ_COMPLETE

SCP → Fabric
THERMAL_WARNING
```

Bu üç iletişim türünün aynı fiziksel altyapıyı kullanması mümkün olmakla birlikte mantıksal olarak birbirinden ayrılmalıdır.

---

# 4. Fabric'in temel düğümleri

NEXSUS sisteminin temel fabric düğümleri:

```text
CPU
FAPU
NPU
SCP
Application MOSRAM
Data MOSRAM
M-SSD
I/O Controller
Wireless Controller
```

olarak düşünülebilir.

Bunların tamamı eşit değildir.

Özellikle bellekler fabric içerisinde yalnızca veri kaynağı değildir; sistemin ana veri merkezleridir.

---

# 5. Application MOSRAM ve Data MOSRAM

NEXSUS'un önemli farklılıklarından biri belleklerin fiziksel ve işlevsel olarak ayrılmasıdır.

```text
                NEXSUS CPU
                    │
                    │
          APPLICATION MOSRAM
                    │
              kısa bağlantı
                    │
             SYSTEM FABRIC
                    │
       ┌────────────┼────────────┐
       │            │            │
   DATA MOSRAM   DATA MOSRAM   DATA MOSRAM
```

### Application MOSRAM

CPU'ya mümkün olduğunca yakın konumlandırılır.

Öncelikli kullanım:

- program kodu,
- executable,
- runtime,
- sık kullanılan kütüphaneler,
- instruction verileri,
- sabit program tabloları.

### Data MOSRAM

Daha büyük kapasiteye sahip olabilir.

Öncelikli kullanım:

- kullanıcı verileri,
- değişkenler,
- bufferlar,
- grafik/ses verileri,
- hesaplama verileri,
- cache benzeri çalışma alanları.

Bu ayrım fabric tasarımını doğrudan etkiler.

---

# 6. Fiziksel yakınlık tabanlı fabric

NSF'nin önemli prensiplerinden biri:

> **Her bağlantının aynı mesafede olması gerekmez.**

Örneğin:

```text
CPU
 │
 └── Application MOSRAM
       çok kısa yol
```

iken:

```text
CPU
 │
 └── Data MOSRAM
       daha uzun yol
```

olabilir.

Benzer şekilde:

```text
FAPU
 │
 └── FAPU'ya yakın Data MOSRAM
```

ve:

```text
NPU
 │
 └── NPU çalışma belleği
```

oluşturulabilir.

Bu nedenle NSF tek bir düz ağ değil, **mesafe ve kullanım yoğunluğuna göre hiyerarşik bir fabric** olabilir.

---

# 7. Fabric bölgeleri

Kavramsal olarak NSF dört ana bölgeye ayrılabilir.

```text
                    NSF
                     │
       ┌─────────────┼─────────────┐
       │             │             │
     LOCAL         SHARED        EXTERNAL
       │             │             │
       │             │             │
 Application      Data MOSRAM     I/O
 MOSRAM           M-SSD           Network
       │             │             │
       └─────────────┴─────────────┘
                     │
                  SYSTEM
```

### Local Fabric

İşlemci ile ona yakın kaynaklar.

### Shared Fabric

Birden fazla işlem biriminin eriştiği ortak kaynaklar.

### Storage Fabric

M-SSD ve kalıcı veri kaynakları.

### External Fabric

Kullanıcı ve dış cihazlarla iletişim.

---

# 8. Local Fabric

En düşük gecikme gerektiren bağlantıdır.

Örneğin:

```text
CPU
 │
 ║
 ║
Application MOSRAM
```

Bu bağlantı mümkün olduğunca kısa tutulur.

Aynı yaklaşım FAPU ve NPU için de kullanılabilir.

Burada amaç fabric üzerinden uzak bir yönlendirme yapmak yerine işlemciye yakın belleği doğrudan kullanmaktır.

---

# 9. Shared Fabric

Birden fazla işlemcinin ortak kullandığı kaynakların bağlantısıdır.

Örneğin:

```text
                  Shared Fabric
                       │
       ┌───────────────┼───────────────┐
       │               │               │
      CPU             FAPU            NPU
       │               │               │
       └───────────────┼───────────────┘
                       │
                  Data MOSRAM
```

Buradaki önemli problem **erişim çakışmasıdır**.

Üç işlemci aynı anda aynı bellek bankına erişmek istediğinde fabric:

- öncelik,
- zamanlama,
- sıra,
- bant genişliği

yönetimini gerçekleştirmelidir.

---

# 10. Bellek Bank Paralelliği

MOSRAM'ın yüksek paralellik potansiyeli nedeniyle NSF'nin bellek erişimini banklara ayırması önemlidir.

Örneğin:

```text
                 DATA MOSRAM
                      │
          ┌───────────┼───────────┐
          │           │           │
        BANK 0      BANK 1      BANK 2
          │           │           │
          │           │           │
         CPU         FAPU        NPU
```

Bu durumda farklı işlemciler farklı banklara erişiyorsa işlemler aynı anda gerçekleştirilebilir.

Dolayısıyla NSF yalnızca:

> "Veriyi taşı"

mantığında değil:

> **"Verinin hangi bankta olduğunu bil ve en kısa yolu seç."**

mantığında çalışabilir.

---

# 11. Data locality

Bu nedenle NEXSUS Fabric'in önemli bir prensibi:

### Data Locality

Veri hangi işlem birimi tarafından yoğun kullanılıyorsa o işlem birimine mümkün olduğunca yakın tutulur.

Örneğin:

```text
FAPU hesaplaması
      ↓
FAPU'ya yakın veri bankı
      ↓
FAPU
```

CPU üzerinden:

```text
FAPU
 ↓
CPU
 ↓
MOSRAM
 ↓
CPU
 ↓
FAPU
```

gibi gereksiz dolaşım yapılmaz.

Bu özellikle büyük veri kümelerinde fabric trafiğini ciddi şekilde azaltabilecek temel bir mimari prensiptir.

2026'da yayınlanan bir araştırmada da bellekler arasında doğrudan die-to-die veri aktarımının hesaplama çipinden veri geçirme zorunluluğunu azaltabildiği ve bellek bant genişliğini artırabildiği gösterilmiştir.

NEXSUS'ta bunun daha genel bir versiyonu hedeflenebilir:

> **Veriyi yalnızca CPU üzerinden dolaştırmamak.**

---

# 12. Direct Memory Path

NSF'nin önemli özelliklerinden biri doğrudan bellek erişim yollarıdır.

Örneğin:

```text
M-SSD
  │
  ↓
Data MOSRAM
  │
  ↓
FAPU
```

CPU'nun araya girmesi zorunlu olmamalıdır.

Benzer şekilde:

```text
Data MOSRAM
     │
     ↓
    NPU
```

olabilir.

Bu sayede CPU yalnızca veri taşıyan bir aracı haline gelmez.

CPU esas işlem görevine odaklanır.

---

# 13. Fabric üzerinde işlem birimleri arası doğrudan iletişim

Daha ileri seviyede:

```text
CPU ↔ FAPU
FAPU ↔ NPU
FAPU ↔ GPU*
NPU ↔ MOSRAM
FAPU ↔ M-SSD*
```

gibi doğrudan iletişimler mümkün olabilir.

Buradaki `*` gelecekte eklenebilecek birimlerdir.

Örneğin FAPU bir hesaplama sonucu oluşturduğunda sonucu önce CPU'ya gönderip sonra NPU'ya vermek zorunda kalmamalıdır.

```text
FAPU
 │
 └────────→ NPU
```

doğrudan mümkün olabilir.

---

# 14. Fabric ve CPU arasındaki ilişki

CPU fabric'in sahibi olmak zorunda değildir.

Bu önemli bir ayrımdır.

Klasik düşüncede:

```text
CPU
 │
 ├── Memory
 ├── I/O
 └── Devices
```

gibi CPU merkezli bir organizasyon oluşur.

NEXSUS'ta:

```text
                SYSTEM FABRIC
              /       │       \
            CPU      FAPU      NPU
             \        │        /
              \       │       /
                 MOSRAM
```

CPU fabric üzerinde **eşit derecede önemli bir işlem düğümüdür**, fakat bütün iletişimin zorunlu merkezi değildir.

---

# 15. SCP'nin Fabric üzerindeki rolü

SCP normal uygulama verisinin içinde olmamalıdır.

SCP daha çok **yönetim düzleminde** bulunmalıdır.

```text
                SYSTEM FABRIC
                      │
       ┌──────────────┴──────────────┐
       │                             │
   DATA PLANE                  CONTROL PLANE
       │                             │
 CPU/FAPU/NPU/MOSRAM               SCP
```

### Data Plane

Normal çalışma sırasında veri taşır.

### Control Plane

Sistem durumu, güç, reset, hata, firmware ve donanım yönetimini gerçekleştirir.

Bu ayrım fabric'in karmaşıklaşmasını önler.

---

# 16. Fabric'in üç düzlemli yapısı

Bunu bir adım daha ileri götürmek mümkün:

```text
              NEXSUS SYSTEM FABRIC

        ┌───────────────────────────┐
        │       CONTROL PLANE       │
        │       SCP / System        │
        ├───────────────────────────┤
        │       DATA PLANE          │
        │       CPU / FAPU / NPU    │
        ├───────────────────────────┤
        │       MEMORY PLANE        │
        │       MOSRAM / M-SSD      │
        └───────────────────────────┘
```

Bu üç düzlem fiziksel olarak aynı fabric altyapısını paylaşabilir ancak mantıksal olarak ayrıdır.

Bu sayede büyük veri transferi sırasında:

> “Sistem sıcaklığı kritik seviyeye çıktı”

gibi bir SCP mesajının beklemesi engellenebilir.

Kontrol mesajları **yüksek öncelikli** olabilir.

---

# 17. Öncelik sistemi

NSF'de bütün paketlerin eşit olması gerekmeyebilir.

Örneğin:

```text
Priority 0 → Emergency / system control
Priority 1 → Real-time control
Priority 2 → CPU/FAPU/NPU data
Priority 3 → Memory transfer
Priority 4 → Storage
Priority 5 → background
```

Bu sadece kavramsal bir örnektir; sayısal sınıflar daha sonra belirlenir.

Ama prensip önemlidir:

> **Sistem kontrolü, büyük bir veri aktarımının arkasında beklememelidir.**

UCIe'nin güncel 3.0 özelliklerinde de zaman açısından kritik sistem olayları için öncelikli sideband paketleri ve acil durum sinyalleşmesi gibi mekanizmalar bulunuyor; bu, fabric'te veri ile kontrol trafiğinin ayrıştırılmasının pratik önemini gösteriyor.

---

# 18. Fabric ve fiziksel anakart

NSF yalnızca mantıksal bir ağ değildir.

PCB yerleşimi fabric'in fiziksel karşılığıdır.

Örneğin:

```text
                   ÖN YÜZ

             ┌─────────────┐
             │ NEXSUS CPU  │
             └──────┬──────┘
                    │
          Application MOSRAM
                    │
        ┌───────────┴───────────┐
        │                       │
       FAPU                    NPU
        │                       │
════════════════════════════════════════
              SYSTEM FABRIC
════════════════════════════════════════

                   ARKA YÜZ

        Data MOSRAM   Data MOSRAM
             │             │
             └──────┬──────┘
                    │
                  M-SSD
```

Bu nedenle fiziksel mesafe fabric tasarımının bir parametresidir.

---

# 19. İki taraflı anakart

NEXSUS anakartının iki yüzü aktif olarak kullanılabilir.

Bu:

> yalnızca daha fazla komponent koymak

anlamına gelmez.

İşlevsel bir yerleşim oluşturur.

### Ön yüz

Kullanıcı ve işlemci odaklı:

```text
CPU
FAPU
NPU
SCP
Application MOSRAM
I/O connectors
```

### Arka yüz

Yüksek yoğunluklu veri ve bağlantı:

```text
Data MOSRAM
M-SSD
Fabric routing
Power distribution
```

Bu yapı kablo karmaşasını azaltırken yüksek hızlı bağlantıların mesafesini de azaltabilir.

---

# 20. Fabric'in katmanlı çalışma modeli

NSF için kavramsal olarak:

```text
Application
     ↓
System Service
     ↓
Fabric Protocol
     ↓
Routing
     ↓
Physical Link
     ↓
Destination
```

şeklinde bir yapı düşünülebilir.

Örneğin CPU:

```text
"FAPU'ya veri gönder"
```

dediğinde sistem:

```text
CPU
 ↓
Fabric
 ↓
destination = FAPU
 ↓
route selection
 ↓
FAPU
```

işlemini gerçekleştirir.

CPU'nun fiziksel bağlantı ayrıntılarını bilmesi gerekmez.

---

# 21. Adresleme

Fabric üzerinde iki farklı adres kavramını ayırmak gerekir.

### Memory Address

Bellek içindeki veri adresi.

### Fabric Address

Verinin hangi sistem düğümüne gönderileceğini belirleyen adres.

Örneğin:

```text
Destination:
    DATA_MOSRAM_BANK_04

Offset:
    0x....
```

veya:

```text
Destination:
    FAPU
Channel:
    2
```

şeklinde düşünülebilir.

Bu ayrım NEXSUS ISA kesinleşmeden önce bile mimari seviyede tanımlanabilir.

---

# 22. Fabric'in en önemli özelliği: gereksiz veri hareketini azaltmak

NEXSUS Fabric'in temel performans ölçütü yalnızca:

**GB/s**

olmamalıdır.

Aynı zamanda:

**kaç kez veri yer değiştirdi?**

sorusunu da dikkate almalıdır.

Örneğin kötü mimari:

```text
M-SSD
 ↓
CPU
 ↓
MOSRAM
 ↓
CPU
 ↓
FAPU
 ↓
CPU
 ↓
MOSRAM
```

NEXSUS yaklaşımı:

```text
M-SSD
 ↓
Data MOSRAM
 ↓
FAPU
```

Sonuç:

- daha az fabric trafiği,
- daha düşük gecikme,
- daha az enerji,
- CPU'nun daha az meşgul olması.

---

# 23. Fabric'in gelecekteki genişleme modeli

NEXSUS'a daha sonra yeni işlem birimleri eklenebilir.

Örneğin:

```text
System Fabric
     │
     ├── CPU
     ├── FAPU
     ├── NPU
     ├── GPU
     ├── DSP
     ├── Security
     ├── ISP
     └── future accelerator
```

Yeni birimin fabric'e bağlanması, bütün sistemin yeniden tasarlanmasını gerektirmemelidir.

Yeni düğüm:

```text
Device
 ↓
Capability discovery
 ↓
Fabric registration
 ↓
Resource allocation
 ↓
Ready
```

şeklinde sisteme dahil olabilir.

Bu özellik özellikle NEXSUS'un uzun ömürlü bir mimari olması açısından önemlidir.

---

# 24. Fabric'in güvenilirlik mekanizması

Fabric yalnızca hızlı olmamalıdır.

Veri hataları da tespit edilmelidir.

Temel seviyede:

```text
Data
 ↓
Integrity check
 ↓
Transmission
 ↓
Integrity check
 ↓
Destination
```

gibi bir mekanizma bulunabilir.

Hata durumunda:

```text
error
 ↓
retry / correction
 ↓
status
```

uygulanabilir.

Buradaki ayrıntılı ECC/CRC seçimi daha sonraki tasarım aşamasına bırakılabilir.

---

# 25. Fabric'in yeni nesil yaklaşımı

NEXSUS System Fabric'in temel prensipleri şu şekilde özetlenebilir:

1. **CPU merkezli olmamak**
2. **İşlemciye yakın belleği kullanmak**
3. **Application ve Data MOSRAM'ı ayırmak**
4. **Belleği banklara bölerek paralellik oluşturmak**
5. **İşlemciler arasında doğrudan veri aktarımına izin vermek**
6. **Veriyi gereksiz yere CPU üzerinden geçirmemek**
7. **Data / Control / Status trafiğini ayırmak**
8. **Kritik kontrol mesajlarına öncelik vermek**
9. **Fiziksel mesafeyi fabric tasarımının parçası yapmak**
10. **Anakartın iki yüzünü aktif kullanmak**
11. **Yeni işlem birimlerinin fabric'e eklenebilmesini sağlamak**
12. **Fabric'i CPU'dan bağımsız ortak sistem altyapısı olarak tasarlamak**

---

# 26. NEXSUS Fabric'in kavramsal farkı

NEXSUS System Fabric'in amacı:

> **“Bütün cihazları birbirine bağlamak”**

değildir.

Daha doğru ifade:

> **“Sistemdeki verinin mümkün olan en kısa, en düşük gecikmeli ve en az enerji harcayan yoldan doğru işlem birimine ulaşmasını sağlamak.”**

Bu nedenle NSF bir **bus**, yalnızca bir **interconnect** veya yalnızca bir **chiplet bağlantısı** değildir.

NSF:

**işlem + bellek + depolama + kontrol + fiziksel yerleşim**

birlikte düşünülerek oluşturulan sistem iletişim mimarisidir.

---

# 27. NEXSUS System Fabric'in temel modeli

Sonuçta sistem:

```text
                         NEXSUS SYSTEM

                           ┌───────┐
                           │  CPU  │
                           └───┬───┘
                               │
                      Application MOSRAM
                               │
                               │
       ┌───────────────────────┼──────────────────────┐
       │                  SYSTEM FABRIC               │
       │                                               │
     FAPU                    NPU                     SCP
       │                      │                       │
       └──────────────────────┼───────────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
                  DATA       DATA      DATA
                 MOSRAM     MOSRAM    MOSRAM
                    │         │         │
                    └─────────┼─────────┘
                              │
                            M-SSD
                              │
                       External I/O
                              │
                    ┌─────────┴─────────┐
                    │                   │
                   NPI          NEXSUS Wireless
```

şeklinde düşünülebilir.

Buradaki en önemli fikir şudur:

**NEXSUS'ta fabric, parçaları birbirine bağlayan sonradan eklenmiş bir kablo sistemi değildir; parçaların nasıl yerleştirileceğini ve verinin sistem içerisinde nasıl hareket edeceğini belirleyen temel mimari katmandır.**
---