# NEXSUS System Fabric
## Merkezi Sistem İletişim, Veri Akışı ve Zamanlama Mimarisi

**Doküman Türü:** Teknik Mimari Makale  
**Proje:** NEXSUS  
**Bileşen:** System Fabric (S.Fabric)  
**Durum:** Kavramsal / Mimari Tasarım  
**Sürüm:** 1.0

---

## 1. Genel Bakış

NEXSUS mimarisinde System Fabric (S.Fabric), klasik anlamdaki bir bus veya yalnızca cihazlar arasında veri taşıyan bir bağlantı sistemi değildir.

S.Fabric, sistemdeki işlem, bellek, depolama ve I/O düğümlerinin birbirleriyle iletişimini, veri aktarım zamanlamasını ve bağlantı kaynaklarının kullanımını yöneten **merkezi sistem altyapısıdır**.

NEXSUS'ta CPU, GPU, FAPU, NPU, MOSRAM, MSSD ve I/O birimleri Fabric üzerinde çalışan bağımsız düğümlerdir.

Bu nedenle NEXSUS mimarisinde sistemin merkezi CPU değil, **System Fabric** olarak kabul edilir.

Temel yaklaşım:

> **Düğümler kendi çalışma frekanslarında çalışır; System Fabric ise bu farklı çalışma alanlarını yüksek hızlı ortak bir iletişim ve zamanlama altyapısında birleştirir.**

---

# 2. Mimari Temel İlke

Geleneksel bilgisayar mimarisinde CPU çoğu zaman sistemin merkezinde bulunur.

Veri akışı çoğunlukla:

```text
CPU
 │
 ├── RAM
 ├── GPU
 ├── Storage
 └── I/O
```

şeklinde düşünülür.

NEXSUS'ta ise yapı:

```text
                 CPU
                  │
GPU ──────────────┼────────────── FAPU
                  │
NPU ──────────────┼────────────── I/O
                  │
MOSRAM ───────────┼────────────── MSSD
                  │
            SYSTEM FABRIC
```

şeklinde ele alınır.

Burada CPU, diğer düğümlerin üzerinden geçmek zorunda değildir.

Örneğin:

```text
MSSD → GPU
MSSD → NPU
MOSRAM → GPU
GPU → MSSD
FAPU → MOSRAM
```

gibi doğrudan düğüm-düğüm veri akışları gerçekleştirilebilir.

CPU yalnızca gerçekten gerekli olduğu durumlarda veri yoluna dahil olur.

---

# 3. S.Fabric'in Temel Görevleri

System Fabric aşağıdaki temel görevleri üstlenir:

1. Veri yönlendirme
2. Dinamik lane tahsisi
3. Veri transferlerinin zamanlanması
4. Farklı clock domain'lerinin yönetimi
5. Trafik interleaving
6. Arbitration
7. QoS ve öncelik yönetimi
8. Akış kontrolü
9. Hata tespiti
10. Yeniden iletim / recovery
11. Congestion yönetimi
12. Doğrudan node-to-node iletişim
13. Kaynakların dinamik paylaşımı
14. Sistem genelinde iletişim sürekliliğinin sağlanması

Bu nedenle Fabric Controller, basit bir bus controller değil, **aktif sistem iletişim yöneticisi** olarak tasarlanır.

---

# 4. Bağımsız Clock Domain'leri

NEXSUS düğümlerinin aynı clock frekansında çalışması gerekli değildir.

Örneğin bir sistemde:

```text
CPU       = 5 GHz
GPU       = 2 GHz
FAPU      = 4 GHz
NPU       = 3 GHz
MOSRAM    = 6 GHz
MSSD      = farklı çalışma frekansı
I/O       = farklı çalışma frekansı
```

olabilir.

Bu frekansların birbirine eşitlenmesi gerekmez.

Temel prensip:

> **Node Clock ≠ Fabric Clock ≠ Memory Clock**

Her düğüm kendi işlem ve veri kabul kapasitesine göre çalışır.

System Fabric ise bu farklı clock domain'leri ortak bir yüksek çözünürlüklü iletişim zaman tabanında birbirine bağlar.

---

# 5. Fabric Clock

S.Fabric'in kendi çalışma zaman tabanı bulunur.

Bu clock, CPU veya GPU'nun çalışma clock'u değildir.

Fabric Clock'un temel amacı:

- veri transferlerini küçük zaman dilimlerine ayırmak,
- düğümlerin veri kabul pencerelerini yönetmek,
- farklı clock domain'leri arasında transferleri koordine etmek,
- aynı anda gelen talepleri interleave etmek,
- Fabric kaynaklarının mümkün olduğunca sürekli kullanılmasını sağlamaktır.

Dolayısıyla Fabric Clock'un başarısı yalnızca frekansıyla değil, **zamanlama çözünürlüğü ve transfer gecikmesi** ile değerlendirilir.

---

# 6. Veri Kabul Pencereleri

Bir düğüm veri istediğinde veya veri yazacağını bildirdiğinde Fabric bu isteği kuyruğa alır.

Ancak klasik bir FIFO yaklaşımı kullanılmaz.

Örneğin:

```text
CPU → READ
NPU → WRITE
MOSRAM → READ/WRITE
GPU → READ
FAPU → WRITE
```

talepleri aynı anda gelebilir.

Fabric Controller bunları tek tek tamamlamayı beklemek yerine, her transferi uygun zaman dilimlerine yerleştirir.

Örneğin:

```text
Fabric Cycle

01 → CPU
02 → CPU
03 → NPU
04 → NPU
05 → MOSRAM
06 → MOSRAM
07 → GPU
08 → FAPU
09 → CPU
10 → GPU
11 → MOSRAM
12 → NPU
```

Bu sıra sabit değildir.

Trafik değiştiğinde anında değişebilir.

---

# 7. Dynamic Time-Slot Interleaving

S.Fabric'in önemli özelliklerinden biri **Dynamic Time-Slot Interleaving** mekanizmasıdır.

Amaç:

> Bir düğümün beklemesi gerekiyorsa Fabric'in de beklememesidir.

Örneğin CPU'nun veri kabul penceresi henüz uygun değilse:

```text
CPU bekliyor
```

ancak Fabric:

```text
GPU
NPU
FAPU
MOSRAM
MSSD
I/O
```

transferlerini yürütmeye devam eder.

Böylece:

> **Bekleyen düğüm ≠ bekleyen Fabric**

olur.

Bu yapı sistem kaynaklarının boşta kalmasını önemli ölçüde azaltabilir.

---

# 8. Dynamic Lane Allocation

S.Fabric'in fiziksel bağlantı kapasitesi düğümlere sabit olarak bölüştürülmez.

Örneğin toplam:

```text
1024 fiziksel sinyal hattı
```

bulunuyorsa bunlar örneğin:

```text
512 Full-Duplex Lane
```

olarak kullanılabilir.

Ancak bu 512 lane'in:

```text
CPU = 64
GPU = 128
NPU = 64
FAPU = 64
...
```

şeklinde kalıcı olarak bölüştürülmesi gerekmez.

Lane'ler ortak kaynak havuzudur.

Örneğin bir anda:

```text
CPU  → MSSD       16 lane
GPU  → MOSRAM    256 lane
NPU  → MOSRAM     96 lane
FAPU → MSSD       64 lane
I/O                32 lane
```

kullanılabilir.

Başka bir anda:

```text
CPU  → MSSD       64 lane
GPU  → MOSRAM    128 lane
NPU  → MSSD      192 lane
FAPU → MOSRAM     96 lane
I/O                32 lane
```

olabilir.

Fabric Controller lane kapasitesini anlık trafik gereksinimine göre yeniden dağıtır.

---

# 9. Lane Sayısı Sabit Mimari Sınır Değildir

512 lane, NEXSUS mimarisinin zorunlu maksimumu olarak kabul edilmemelidir.

Aynı Fabric mimarisi:

```text
128 lane
256 lane
512 lane
1024 lane
2048+ lane
```

gibi farklı sistem ölçeklerinde uygulanabilir.

Dolayısıyla Fabric protokolü fiziksel bağlantı genişliğinden bağımsız olarak tasarlanmalıdır.

Bu yaklaşım küçük sistemlerden yüksek performanslı sistemlere kadar aynı mimarinin ölçeklenmesini sağlar.

---

# 10. Node Clock ile Veri Transfer Clock'unun Ayrılması

CPU'nun 5 GHz çalışması, Fabric'in de 5 GHz çalışmasını gerektirmez.

Aynı şekilde GPU'nun 2 GHz olması, GPU'nun Fabric üzerinden yalnızca 2 GHz hızında veri alabileceği anlamına gelmez.

Düğümün kendi clock'u:

```text
işlem hızı
```

ile ilgilidir.

Fabric Clock ise:

```text
sistemler arası veri transferinin zaman çözünürlüğü
```

ile ilgilidir.

Bu nedenle:

```text
CPU     5 GHz
GPU     2 GHz
MOSRAM  6 GHz
```

gibi farklı sistemlerin aynı Fabric üzerinde çalışması mümkündür.

---

# 11. Veri Transferinin Küçük Birimlere Ayrılması

Büyük bir veri transferinin tek parça halinde Fabric'i uzun süre işgal etmesi yerine transferler daha küçük işlem birimlerine bölünebilir.

Örneğin:

```text
CPU → MSSD
8 KB READ
```

isteği geldiğinde CPU'nun 512 lane kullanması gerekmez.

Fabric ihtiyaca göre örneğin 8 veya 16 lane tahsis edebilir.

Kalan kaynak:

```text
GPU
NPU
FAPU
MOSRAM
I/O
```

tarafından kullanılabilir.

Büyük bir GPU veri transferi ise aynı anda yüzlerce lane kullanabilir.

---

# 12. Interleaving ile Kaynakların Birleştirilmesi

Fabric'in amacı transferleri katı bir sıraya koymak değildir.

Örneğin gelen talepler:

```text
CPU  → MSSD
GPU  → MOSRAM
NPU  → MOSRAM
FAPU → MSSD
```

ise:

```text
CPU
GPU
NPU
GPU
FAPU
NPU
CPU
GPU
...
```

şeklinde küçük transfer parçaları birbirine kaynaştırılabilir.

Aynı zamanda farklı lane grupları paralel çalışabilir.

Böylece tek bir transferin tamamlanması diğer bütün transferlerin başlamasını engellemez.

---

# 13. Doğrudan Node-to-Node İletişim

NEXSUS'ta CPU sistemin zorunlu veri aracısı değildir.

Örneğin klasik yaklaşım:

```text
MSSD
 ↓
CPU
 ↓
RAM
 ↓
GPU
```

olabilir.

NEXSUS'ta ise:

```text
MSSD ─────────→ GPU
```

veya:

```text
MSSD → MOSRAM → GPU
```

mümkündür.

Benzer şekilde:

```text
FAPU → MOSRAM
GPU  → MSSD
NPU  → MSSD
MSSD → NPU
GPU  → FAPU
```

gibi doğrudan veri akışları desteklenir.

Bu yaklaşım CPU üzerindeki veri taşıma yükünü azaltır.

---

# 14. MSSD'nin Fabric İçindeki Konumu

MSSD, klasik anlamda CPU'ya bağlı bir SSD değildir.

MSSD, System Fabric üzerinde **birinci sınıf veri düğümü** olarak konumlandırılır.

Örneğin:

```text
CPU  → MSSD
GPU  → MSSD
FAPU → MSSD
NPU  → MSSD
```

erişimleri CPU aracılığı olmadan gerçekleşebilir.

MSSD'nin bu şekilde konumlandırılması, kalıcı veri katmanının bütün sistem tarafından ortak kullanılmasını sağlar.

---

# 15. MOSRAM'ın Fabric İçindeki Konumu

MOSRAM da yalnızca CPU'nun RAM'i olarak düşünülmez.

Fabric üzerinde doğrudan erişilebilir bir bellek düğümüdür.

Örneğin:

```text
GPU  → MOSRAM
NPU  → MOSRAM
FAPU → MOSRAM
CPU  → MOSRAM
```

erişimleri eş zamanlı olarak gerçekleştirilebilir.

Fabric Controller, aynı MOSRAM bölgesine gelen çakışan erişimleri yönetir.

Bağımsız bellek bölgelerine yapılan erişimler mümkün olduğunca paralel yürütülür.

---

# 16. Arbitration

Birden fazla düğüm aynı anda aynı kaynağa erişmek istediğinde Fabric Controller arbitration gerçekleştirir.

Ancak arbitration yalnızca:

> "Önce kim?"

sorusu değildir.

Şunlar birlikte değerlendirilir:

- Transfer boyutu
- Öncelik
- Gecikme toleransı
- Veri bağımlılığı
- Mevcut lane kullanımı
- Hedef düğümün kabul kapasitesi
- Kaynak düğümün üretim hızı
- Diğer transferlerin etkilenme derecesi

Amaç tek bir düğümü maksimum hızda çalıştırmak değil, **sistem genelinde dengeli veri akışı sağlamaktır.**

---

# 17. QoS ve Öncelik

Her veri transferi aynı öneme sahip değildir.

Örneğin:

```text
Gerçek zamanlı video
        ↓
yüksek öncelik
```

iken:

```text
arka plan veri aktarımı
        ↓
düşük öncelik
```

olabilir.

Fabric Controller gerekli durumlarda yüksek öncelikli trafiğe daha fazla lane veya daha sık zaman dilimi tahsis edebilir.

Ancak düşük öncelikli trafik tamamen bloke edilmemelidir.

Bu nedenle QoS mekanizması starvation önleme kurallarına sahip olmalıdır.

---

# 18. Hata Yönetimi

Fiziksel sistemlerde mutlak anlamda "sıfır hata" garanti edilemez.

Bu nedenle hedef:

> **Hatanın sistem tarafından görünür bir veri bozulmasına dönüşmesini engellemek.**

olmalıdır.

Transfer paketlerinde örneğin:

```text
HEADER
SOURCE
DESTINATION
ADDRESS
LENGTH
SEQUENCE
DATA
CRC/ECC
```

gibi alanlar bulunabilir.

Alıcı hata tespit ederse:

```text
ERROR
 ↓
RETRY / REPLAY
 ↓
TRANSFER CONTINUE
```

gerçekleştirilir.

Gerekli durumlarda problemli lane devre dışı bırakılarak trafik başka lane'lere yönlendirilebilir.

---

# 19. Congestion Management

Bir hedef düğümün veri kabul kapasitesi dolduğunda Fabric yeni veriyi zorla göndermemelidir.

Bunun yerine:

```text
Backpressure
Queue
Lane Redistribution
Priority Adjustment
```

mekanizmaları kullanılmalıdır.

Örneğin GPU geçici olarak veri kabul edemiyorsa GPU'ya ayrılmış lane'lerin bir bölümü başka düğümlere aktarılabilir.

GPU tekrar hazır olduğunda kapasite yeniden artırılır.

---

# 20. Fabric Controller

Bütün bu işlemlerin merkezi bileşeni **Fabric Controller** veya **Fabric Controller/Router** olarak tanımlanır.

Bu bileşen:

```text
                  FABRIC CONTROLLER
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
    Routing          Scheduling        Arbitration
       │                 │                 │
 Lane Allocation   Time Interleave       QoS
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                 Error / Recovery
```

fonksiyonlarını gerçekleştirir.

Bu nedenle Fabric Controller, NEXSUS anakartının en kritik kontrol bileşenlerinden biridir.

---

# 21. Fabric'in Merkezi Rolü

NEXSUS'ta:

```text
CPU      = İşlem düğümü
GPU      = Paralel işlem düğümü
FAPU     = Yardımcı işlem düğümü
NPU      = AI/özel işlem düğümü
MOSRAM   = Çalışma belleği düğümü
MSSD     = Kalıcı veri düğümü
I/O      = Harici iletişim düğümleri

SYSTEM FABRIC = Ortak sistem altyapısı
```

Bu nedenle System Fabric'i yalnızca bir bus olarak tanımlamak doğru değildir.

Daha doğru tanım:

> **System Fabric, NEXSUS sisteminin merkezi iletişim, kaynak dağıtım ve veri zamanlama altyapısıdır.**

---

# 22. Temel Mimari Hedef

NEXSUS System Fabric'in temel hedefi maksimum teorik bant genişliğinden daha geniştir.

Asıl hedef:

> **Sistemdeki farklı hızlarda çalışan düğümlerin veri ihtiyaçlarını mümkün olan en düşük bekleme süresiyle karşılamak ve bir düğümün bekleme durumunun diğer düğümlerin çalışmalarını gereksiz yere durdurmasını önlemek.**

Bu nedenle performans:

```text
Fabric Bandwidth
+
Fabric Clock
+
Lane Count
+
Latency
+
Interleaving Efficiency
+
Node Acceptance Timing
+
Routing Efficiency
+
Error Recovery
```

birlikte değerlendirilmelidir.

---

# 23. Referans Mimari

İlk yüksek performanslı NEXSUS tasarımı için referans hedef:

```text
SYSTEM FABRIC
────────────────────────────────

Fabric Controller
Dynamic Lane Allocation
Dynamic Time-Slot Interleaving
Direct Node-to-Node Communication

Reference Width:
1024 Full-Duplex Lane hedefi

Scalable:
128 / 256 / 512 / 1024 / 2048+

Independent Clock Domains:
CPU
GPU
FAPU
NPU
MOSRAM
MSSD
I/O

Core Functions:
Routing
Arbitration
Scheduling
QoS
Flow Control
CRC/ECC
Retry
Recovery
Backpressure
```

1024 lane burada mimarinin zorunlu sınırı değil, yüksek performanslı referans sistem için başlangıç hedefidir.

---

# 24. Sonuç

NEXSUS System Fabric'in temel amacı yalnızca cihazlar arasında yüksek hızlı veri taşımak değildir.

Fabric:

- farklı clock domain'lerini birleştirir,
- düğümlerin veri kabul zamanlarını koordine eder,
- kullanılmayan bağlantı kapasitesini başka düğümlere aktarır,
- veri transferlerini küçük zaman dilimlerine böler,
- transferleri birbirleriyle interleave eder,
- doğrudan node-to-node iletişim sağlar,
- MSSD ve MOSRAM'ı sistemin ortak veri altyapısına dahil eder,
- hata ve congestion durumlarını yönetir,
- sistem kaynaklarının mümkün olduğunca sürekli kullanılmasını sağlar.

Bu nedenle NEXSUS mimarisinde System Fabric, klasik bir bus'ın geliştirilmiş biçimi olarak değil, **anakartın merkezi sistem altyapısı** olarak ele alınmalıdır.

Temel mimari ifade:

> **CPU sistemi çalıştıran ana işlem düğümüdür; System Fabric ise sistemin bütün düğümlerinin birlikte ve uyumlu çalışmasını sağlayan merkezi altyapıdır.**

NEXSUS'un ölçeklenebilirliği yalnızca işlemci performansından değil, **Fabric'in sistemdeki bütün kaynakları ne kadar etkin bir şekilde birbirine bağlayabildiğinden** gelecektir.
