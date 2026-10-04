# NEXSUS Yeni Nesil Kişisel Bilgisayar Mimarisi

## 1. Giriş

Günümüzde kişisel bilgisayar mimarisi, çok uzun bir teknolojik evrimin sonucudur. Ancak bu evrim yalnızca yeni teknolojilerin eklenmesi şeklinde gerçekleşmiştir. Önceki nesillerden kalan birçok donanım ve yazılım katmanı, yeni sistemlerde de uyumluluk amacıyla yaşamaya devam etmektedir.

Modern bilgisayarlar çok güçlü işlemcilere, hızlı belleklere, yüksek bant genişlikli bağlantılara ve özel işlem birimlerine sahip olmasına rağmen temel sistem organizasyonu hâlâ tarihsel olarak oluşmuş birçok kavramı taşımaktadır.

NEXSUS yaklaşımı ise mevcut PC mimarisini geliştirmek yerine, kişisel bilgisayarı **işlemci, bellek, depolama, firmware ve çevre birimleri birlikte düşünülerek sıfırdan tasarlanan bir platform** olarak ele alır.

Temel amaç daha fazla donanım eklemek değil;

> **gereksiz tarihsel katmanları ortadan kaldırmak ve birbirleriyle doğal olarak çalışan yeni bir bilgisayar ekosistemi oluşturmaktır.**

Bu sistemin temel bileşenleri:

- Nexus Flow programlama dili,
- NEXSUS CPU,
- FAPU yardımcı işlemcisi,
- NPU öğrenme ve sistem davranışı işlemcisi,
- MOSRAM çalışma belleği,
- M-SSD kalıcı depolama,
- SCP sistem kontrol işlemcisi,
- yeni nesil sistem firmware'i,
- ortak kablolu çevre birimi arayüzü,
- çoklu cihaz destekli kablosuz iletişim sistemi

olarak düşünülmektedir.

---

# 2. Temel Mimari Felsefe

NEXSUS mimarisinin temel farkı, bilgisayarı yalnızca CPU merkezli düşünmemesidir.

Klasik yaklaşım kabaca:

```text
CPU
 │
 ├── RAM
 ├── Chipset
 ├── Storage
 ├── USB
 ├── Network
 └── Other Devices
```

şeklinde gelişmiştir.

NEXSUS yaklaşımında ise bütün birimler ortak bir sistem mimarisinin parçalarıdır:

```text
                     NEXSUS SYSTEM
                           │
             ┌─────────────┼─────────────┐
             │             │             │
           CPU            FAPU          NPU
             │             │             │
             └─────────────┼─────────────┘
                           │
                    SYSTEM FABRIC
                           │
             ┌─────────────┼─────────────┐
             │             │             │
          MOSRAM         M-SSD          SCP
                           │
                    I/O / NETWORK
```

Buradaki amaç her iş için ayrı bir kontrolcü üretmek değildir.

Her birimin **kendi doğal görev alanı** bulunur.

---

# 3. NEXSUS CPU

NEXSUS CPU sistemin genel amaçlı işlem merkezidir.

Daha önce tanımlanan temel register organizasyonu:

```text
RA00–RA63
DA00–DA63
MA00–MA31
```

şeklindedir.

RA genel amaçlı scalar işlemler için,

DA veri işlemleri için,

MA ise yüksek paralellikli vektör/matris işlemleri için kullanılmaktadır.

Burada CPU'nun görevi:

- program yürütmek,
- kontrol akışını yönetmek,
- genel hesaplamaları gerçekleştirmek,
- sistem kaynaklarını kullanmak,
- diğer işlem birimleriyle koordinasyon kurmaktır.

NEXSUS CPU bütün hesaplamaları kendisi yapmak zorunda değildir.

Bu, mimarinin önemli farklarından biridir.

---

# 4. FAPU

FAPU, CPU'nun yapamadığı işleri yapmak için eklenmiş klasik bir yardımcı işlemci değildir.

FAPU'nun amacı CPU üzerinde pahalı veya özel işlem gerektiren hesaplamaları kendi çalışma alanına almaktır.

FAPU içerisinde zaman içerisinde farklı hesaplama sınıfları bulunabilir:

```text
FAPU
 │
 ├── yüksek hassasiyetli matematik
 ├── paralel hesaplama
 ├── özel sayısal işlemler
 ├── kriptografik işlemler
 └── uygulamaya özel hesaplama
```

Böylece şifreleme için ayrıca tamamen bağımsız bir kripto işlemcisi zorunlu değildir.

Kriptografik algoritmalar FAPU'nun yüksek hızlı hesaplama kabiliyetlerinden yararlanabilir.

Bu yaklaşım, çok sayıda küçük özel işlemci yerine **daha genel yetenekli bir yardımcı işlemci** kullanır.

---

# 5. NPU — Sistem Öğrenme Birimi

NEXSUS sistemindeki NPU'nun temel görevi klasik anlamda AI uygulamalarını çalıştırmak değildir.

NPU daha küçük ve daha özel bir öğrenme sistemi olarak tasarlanabilir.

Temel amacı:

> **bilgisayarın çalışma alışkanlıklarını öğrenmek ve gelecekteki davranışları öngörerek sistemi optimize etmek.**

Örneğin NPU zaman içerisinde:

- hangi uygulamaların birlikte kullanıldığını,
- hangi uygulamaların hangi saatlerde çalıştırıldığını,
- hangi dosyaların sık kullanıldığını,
- hangi işlemlerin tekrarladığını,
- hangi kaynakların ne zaman gerektiğini

öğrenebilir.

Bunun sonucunda:

```text
Kullanıcı davranışı
        ↓
       NPU
        ↓
Örüntü / tahmin
        ↓
Sistem optimizasyonu
        ↓
CPU / FAPU / MOSRAM / M-SSD
```

oluşabilir.

Bu nedenle NPU'nun sistemdeki görevi doğrudan işlem gücü eklemekten çok **bilgisayarın zaman içerisinde kullanıcıya uyum sağlamasıdır.**

Kişisel bilgisayarda bu yaklaşım özellikle anlamlıdır; çünkü öğrenilen model belirli bir kullanıcının kullanım alışkanlıklarına göre oluşur.

---

# 6. MOSRAM

MOSRAM sistemin ana çalışma belleği olarak düşünülmektedir.

MOSRAM'ın temel yaklaşımı MOSFET gate bölgesindeki elektriksel yük/gerilim durumunu veri saklama mekanizmasının parçası olarak kullanmaktır.

Önerilen yapının önemli özelliği, bellek erişiminin yüksek paralelliğe uygun olmasıdır.

Bu nedenle klasik bellek mimarisindeki veri taşıma darboğazlarının önemli bir kısmı farklı şekilde ele alınabilir.

MOSRAM:

```text
              MOSRAM
                 │
       ┌─────────┼─────────┐
       │         │         │
      CPU       FAPU      NPU
       │         │         │
       └─────────┼─────────┘
```

şeklinde ortak çalışma alanı oluşturabilir.

Burada ayrıca büyük bir veri taşıma işlemcisi kullanmak zorunlu olmayabilir.

Bunun yerine MOSRAM'ın fiziksel yapısından yararlanılarak **bank paralelliği ve eşzamanlı erişim** ön plana çıkarılabilir.

Bu, MOSRAM'ın yalnızca daha hızlı RAM olması yerine sistem mimarisini değiştiren bir bileşen olmasını sağlayabilir.

---

# 7. M-SSD

MOSRAM kısa/orta süreli çalışma belleği ise M-SSD kalıcı depolama katmanıdır.

M-SSD'nin amacı mevcut SSD teknolojisini yalnızca daha hızlı hale getirmek değil, MOSRAM ve NEXSUS mimarisine doğal şekilde bağlanan yeni bir kalıcı bellek sistemi oluşturmaktır.

```text
              NEXSUS
                 │
              MOSRAM
                 │
               M-SSD
```

Bu yapı klasik:

```text
CPU → RAM → SATA/NVMe → SSD
```

modelinden farklı bir bellek/depolama hiyerarşisine dönüşebilir.

M-SSD'nin kendi veri yapısı, erişim modeli ve yönetim sistemi NEXSUS mimarisine göre tasarlanabilir.

Bu nedenle taşınabilir depolama cihazları ve USB bellekler için de yeni bir protokol ailesi oluşturulabilir.

---

# 8. SCP — System Control Processor

NEXSUS anakartında ayrıca küçük fakat bağımsız bir sistem kontrol işlemcisi bulunabilir.

**SCP — System Control Processor**

ana CPU'nun yerine geçmez.

Görevi bilgisayarın fiziksel sistem durumunu yönetmektir.

Örneğin:

- güç açma/kapatma,
- reset,
- sıcaklık izleme,
- fan kontrolü,
- güç yönetimi,
- donanım başlatma,
- hata izleme,
- firmware işlemleri,
- çevre birimlerinin keşfi

SCP tarafından gerçekleştirilebilir.

Böylece ana CPU işletim sistemi çalıştırırken anakartın temel yönetimi başka bir işlemci tarafından gerçekleştirilebilir.

```text
              NEXSUS CPU
                  │
             normal çalışma
                  │
────────────────────────────────
                  │
                  │
                 SCP
                  │
       fiziksel sistem yönetimi
```

Bu yaklaşım modern SoC'lerde bulunan platform yönetim denetleyicileriyle aynı genel ihtiyaca cevap verir; ancak NEXSUS'ta baştan tasarlanan bütünsel sistem mimarisinin parçasıdır. Güncel SoC'lerde de platform yönetim kontrolcüleri, yüksek hızlı I/O ve işlem birimleri aynı sistem içinde bütünleştirilebilmektedir.

---

# 9. Yeni Firmware Sistemi

NEXSUS'ta klasik BIOS kavramının doğrudan kullanılmasına gerek yoktur.

Modern sistemlerde BIOS kavramının yerini büyük ölçüde UEFI tabanlı firmware almış durumdadır; UEFI zaten işletim sistemi ile platform firmware'i arasında standart bir arayüz sağlar.

Ancak NEXSUS için daha temiz bir yaklaşım:

**NEXSUS System Firmware — NSF**

olabilir.

Firmware'in görevi:

```text
Power ON
   ↓
SCP
   ↓
Hardware discovery
   ↓
MOSRAM initialization
   ↓
M-SSD discovery
   ↓
NEXSUS CPU initialization
   ↓
Peripheral discovery
   ↓
System configuration
   ↓
OS loader
```

olur.

Firmware sabit bir anakart listesini takip etmek yerine sistemde bulunan donanımları keşfedebilir.

Bu yaklaşım güncel firmware tasarımlarındaki modülerlik eğilimiyle de uyumludur; örneğin Intel'in USF yaklaşımı SoC, platform ve OS payload katmanları arasında daha açık sınırlar ve modüler firmware arayüzleri hedeflemektedir.

---

# 10. BIOS'un Ortadan Kalkması

Buradaki amaç sadece BIOS'un adını değiştirmek değildir.

Eski PC mimarisinden kalan varsayımlar da mümkün olduğunca kaldırılır.

Yeni firmware:

- CPU'yu başlatır,
- belleği tanır,
- depolamayı tanır,
- çevre birimlerini keşfeder,
- sistem kaynaklarını düzenler,
- güvenlik kontrollerini yapar,
- işletim sistemini yükler.

Böylece firmware doğrudan NEXSUS donanım modelinin bir parçası olur.

---

# 11. Kablolu Çevre Birimi Sistemi

NEXSUS için fiziksel bağlantı standardı olarak USB-C benzeri küçük ve ters çevrilebilir bir konnektör kullanılabilir.

Ancak burada USB-C yalnızca **fiziksel bağlantı biçimi** olabilir.

Üzerinde çalışan protokol NEXSUS'a özel olabilir.

Örneğin:

**NPI — NEXSUS Peripheral Interface**

```text
NEXSUS PORT
    │
    ├── Keyboard
    ├── Mouse
    ├── Headset
    ├── Microphone
    ├── Phone
    ├── Display
    ├── Storage
    └── Other Devices
```

Aynı fiziksel bağlantı üzerinden farklı cihaz sınıfları çalışabilir.

Cihaz bağlandığında:

```text
Connect
   ↓
Device identification
   ↓
Capability discovery
   ↓
Interface selection
   ↓
Driver / service assignment
   ↓
Active
```

şeklinde otomatik tanımlanabilir.

USB Type-C günümüzde de host/device rolleri, güç yönetimi ve fiziksel yönlendirme gibi ayrı kontrol mekanizmaları gerektiren bir sistemdir. NEXSUS yaklaşımında bu işlevlerin daha bütünleşik bir platform protokolünde ele alınması hedeflenebilir.

---

# 12. Tek Alıcılı Kablosuz Çevre Birimi Sistemi

NEXSUS'un kablosuz tarafında Bluetooth'un doğrudan kopyalanması yerine yeni bir **çoklu cihaz bağlantı protokolü** düşünülebilir.

Temel fikir:

> Bir bilgisayara her cihaz için ayrı USB alıcı takmak gerekmemelidir.

Örneğin:

```text
                    NEXSUS WIRELESS
                         RECEIVER
                             │
       ┌─────────┬──────────┼──────────┬─────────┐
       │         │          │          │         │
     Mouse   Keyboard    Headset    Microphone  Phone
```

Tek alıcı aynı anda çok sayıda cihazla haberleşebilir.

Her cihazın fiziksel olarak ayrı kanal kullanması zorunlu değildir.

Bağlantı:

```text
Host
 │
 └── Wireless Link
       ├── HID channel
       ├── Audio channel
       ├── Microphone channel
       ├── Control channel
       └── Data channel
```

şeklinde mantıksal kanallara ayrılabilir.

Böylece kullanıcı açısından:

**bir cihaz = bir receiver**

yerine:

**bir bilgisayar = bir ortak kablosuz bağlantı alanı**

modeli oluşur.

---

# 13. Telefonun Sistemin Bir Parçası Haline Gelmesi

Bu sistemin daha ileri bir sonucu ortaya çıkar.

Telefon:

```text
NEXSUS Wireless Link
        │
       Phone
        │
        ├── Audio
        ├── Microphone
        ├── Camera
        ├── Notifications
        ├── File transfer
        └── Application services
```

şeklinde bilgisayarın harici bir çevre birimi gibi bağlanabilir.

Bu durumda telefon ve bilgisayar arasında klasik Bluetooth eşleştirmesinden daha yüksek seviyeli bir **cihaz oturumu** kurulabilir.

---

# 14. System Fabric

Bütün bu bileşenlerin birbirleriyle haberleşmesini sağlayan ortak bağlantı katmanı:

**NEXSUS System Fabric**

olarak düşünülebilir.

Bu yapı klasik anlamda tek bir bus olmak zorunda değildir.

Amacı:

- CPU,
- FAPU,
- NPU,
- MOSRAM,
- M-SSD,
- SCP,
- I/O

arasındaki veri ve kontrol iletişimini ortak bir sistem modeline taşımaktır.

```text
                     NEXSUS FABRIC
                          │
       ┌──────────┬───────┼───────┬──────────┐
       │          │       │       │          │
      CPU        FAPU    NPU    MOSRAM     M-SSD
       │
      SCP
       │
      I/O
```

Bu yapı klasik PC'deki CPU, bellek, PCH ve çeşitli bağımsız veri yollarının oluşturduğu daha parçalı modelin yerine daha bütünleşik bir sistem yaklaşımı getirebilir. Güncel bilgisayarlarda CPU, bellek, PCH, PCIe ve USB gibi farklı bağlantı katmanlarının bulunması bu tarihsel ayrışmanın tipik örneğidir.

---

# 15. Sistem Birimlerinin Çalışma Dağılımı

NEXSUS sisteminin temel çalışma modeli:

```text
                         PROGRAM
                            │
                       Nexus Flow
                            │
                         NEXSUS
                            │
              ┌─────────────┼─────────────┐
              │             │             │
           normal         özel         öğrenme
           işlem         hesaplama      / tahmin
              │             │             │
             CPU           FAPU           NPU
              │             │             │
              └─────────────┼─────────────┘
                            │
                         MOSRAM
                            │
                         M-SSD
```

Sistem yönetimi ise paralel yürür:

```text
SCP
 │
 ├── Power
 ├── Thermal
 ├── Reset
 ├── Hardware state
 ├── Firmware
 └── Peripheral management
```

Çevre birimleri:

```text
                NEXSUS I/O
                    │
          ┌─────────┴─────────┐
          │                   │
         NPI          NEXSUS Wireless
          │                   │
      wired devices       wireless devices
```

---

# 16. Eski Sistemden Çıkarılan Kavramlar

NEXSUS'un yeniliği yalnızca eklenen bileşenlerden oluşmaz.

Bazı eski kavramlar doğrudan gereksiz hale gelebilir.

### Ortadan kalkması hedeflenenler

- klasik BIOS yaklaşımı,
- tarihsel BIOS uyumluluk katmanları,
- klasik chipset/PCH merkezli organizasyon,
- ayrı USB receiver bağımlılığı,
- ayrı kablosuz alıcılar,
- SATA merkezli depolama modeli,
- klasik DRAM merkezli bellek varsayımı,
- CPU'nun bütün hesaplamaları tek başına üstlenmesi,
- çok sayıda birbirinden bağımsız küçük kontrolcü,
- çevre birimlerinin ayrı ayrı sistemlere bağlanması.

Burada “ortadan kalkması” fiziksel olarak her parçanın yok olması anlamında değil; **işlevin daha bütünleşik bir sistem tarafından üstlenilmesi** anlamındadır.

---

# 17. Yeni Sistemin Getirdiği Temel Yenilikler

NEXSUS mimarisinin temel yenilikleri birkaç başlıkta toplanabilir.

### 17.1. CPU merkezli olmayan bilgisayar

CPU hâlâ ana işlemcidir ancak bütün hesaplama yükünün sahibi değildir.

```text
CPU + FAPU + NPU
```

birlikte çalışır.

### 17.2. Belleğin mimari rolünün değişmesi

MOSRAM yalnızca RAM kapasitesi değildir.

Yüksek paralellik ve hızlı erişim sistemi işlem birimlerinin çalışma biçimini etkileyebilir.

### 17.3. Öğrenen sistem

NPU, uygulama çalıştırmak yerine bilgisayarın çalışma alışkanlığını öğrenebilir.

### 17.4. Anakartın kendi işlemcisi

SCP, sistem yönetimini ana CPU'dan ayırır.

### 17.5. Firmware'in yeniden tasarlanması

Firmware eski PC mirasını taşımak yerine NEXSUS donanımının doğal başlangıç ve yönetim katmanı olur.

### 17.6. Tek bağlantı yaklaşımı

Kablolu ve kablosuz çevre birimleri ayrı ayrı protokoller ve alıcılarla parçalanmak yerine ortak bir cihaz iletişim modeline yaklaşır.

### 17.7. Tek alıcı ile çoklu cihaz

Klavye, mouse, kulaklık, mikrofon, telefon ve diğer cihazlar aynı kablosuz sistem içerisinde aynı anda bulunabilir.

### 17.8. Depolama sisteminin yeniden düşünülmesi

M-SSD yalnızca daha hızlı SSD değildir; MOSRAM ile birlikte yeni bir bellek/depolama hiyerarşisinin parçasıdır.

---

# 18. Klasik PC ile NEXSUS'un Kavramsal Karşılaştırması

| Alan | Klasik PC yaklaşımı | NEXSUS yaklaşımı |
|---|---|---|
| Ana işlem | CPU | CPU + FAPU + NPU |
| Bellek | DRAM | MOSRAM |
| Kalıcı depolama | SSD/NVMe/SATA | M-SSD |
| Sistem kontrolü | chipset/EC vb. | SCP |
| Firmware | BIOS/UEFI | NEXSUS Firmware |
| Çevre birimleri | çoklu protokol | ortak NPI yaklaşımı |
| Kablosuz cihaz | çoğunlukla ayrı bağlantı/receiver modelleri | tek çoklu cihaz bağlantısı |
| Veri yolu | çok sayıda özel bağlantı | ortak System Fabric yaklaşımı |
| AI | uygulamaya bağlı GPU/NPU | küçük sistem öğrenme NPU'su |
| Kriptografi | ayrı donanım veya CPU talimatları | FAPU tabanlı yaklaşım |
| Anakart | çok sayıda kontrolcü | bütünleşik sistem kontrolü |
| Depolama erişimi | blok cihaz merkezli | NEXSUS/M-SSD odaklı model |
| Sistem optimizasyonu | büyük ölçüde yazılım kuralları | NPU destekli öğrenme |
| Tasarım yaklaşımı | geriye dönük uyumluluk ağırlıklı | sıfırdan bütünleşik tasarım |

---

# 19. Sonuç

NEXSUS'un temel iddiası:

> **Yeni bir bilgisayar yapmak için yalnızca daha hızlı bir CPU yapmak yeterli değildir.**

İşlemci, bellek, depolama, firmware, anakart kontrolü ve çevre birimleri aynı sistem düşüncesinin parçaları olarak yeniden ele alınmalıdır.

Bu nedenle NEXSUS platformunda:

**Nexus Flow** yazılımın doğal dili,

**NEXSUS CPU** genel işlem merkezi,

**FAPU** yüksek seviyeli özel hesaplama birimi,

**NPU** sistem davranışını öğrenen yardımcı işlemci,

**MOSRAM** yüksek hızlı çalışma belleği,

**M-SSD** yeni nesil kalıcı depolama,

**SCP** fiziksel sistem yöneticisi,

**NEXSUS Firmware** donanım ile işletim sistemi arasındaki başlangıç ve yönetim katmanı,

**NPI** kablolu çevre birimi sistemi,

**NEXSUS Wireless Link** ise çoklu cihaz kablosuz iletişim katmanı olarak görev yapar.

Bu mimarinin esas yeniliği tek tek bu parçaların varlığı değildir. Modern sistemlerde heterojen işlemciler, AI motorları, platform kontrolcüleri ve yüksek hızlı bağlantılar zaten farklı biçimlerde kullanılmaktadır.

NEXSUS'un özgün yaklaşımı, bunları **eski PC mimarisinin üzerine eklemek yerine, baştan birlikte tasarlanmış tek bir kişisel bilgisayar platformu olarak ele almaktır.**

Bu nedenle sonraki aşamada yapılması gereken en önemli çalışma, her bir yeni birimin teknik ayrıntılarını hemen belirlemek değil; **bu birimlerin çalışma prensiplerini tek tek tanımlamak ve aralarındaki görev sınırlarını kesinleştirmektir.**
---
