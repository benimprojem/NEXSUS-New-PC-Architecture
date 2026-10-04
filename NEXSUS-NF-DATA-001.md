
# Nexus Flow ve NEXSUS Veri Adresi Mimarisi
## Verinin Taşınması Yerine Konumunun Taşınması

**Doküman Kodu:** NEXSUS-NF-DATA-001  
**Konu:** Nexus Flow veri modeli, CPU–GPU görev modeli, NEI veri hareketi ve System Fabric entegrasyonu  
**Statü:** Kavramsal Teknik Mimari

---

## 1. Temel İlke

NEXSUS mimarisinde işlemciler arasındaki büyük veri hareketinin doğrudan CPU tarafından gerçekleştirilmesi temel çalışma modeli değildir.

CPU'nun görevi verinin kendisini başka bir işlemciye taşımak yerine:

- hangi kodun çalıştırılacağını,
- hangi verinin kullanılacağını,
- verinin nerede bulunduğunu,
- verinin boyutunu,
- sonucun nereye yazılacağını

tanımlamaktır.

Böylece temel iletişim:

```text
VERİ
```

değil,

```text
VERİNİN ADRESİ
```

üzerinden gerçekleştirilir.

Nexus Flow açısından bu yaklaşım daha da temel bir anlam taşır:

> **Veri bir işlemcinin içine taşınması gereken bir nesne olmak zorunda değildir. Veri, sistem belleğinde belirli bir konuma sahip bir kaynaktır.**

İşlemci bu kaynağa ihtiyaç duyduğunda onun konumunu bildirir.

---

# 2. Klasik Model

Geleneksel bir CPU–GPU modelinde işlem akışı çoğu zaman şu şekilde düşünülebilir:

```text
CPU
 │
 │ veri kopyala
 ▼
GPU
 │
 │ hesapla
 ▼
GPU sonucu
 │
 │ sonucu kopyala
 ▼
CPU
```

Örneğin CPU'nun elinde 512 MB veri olduğunu düşünelim.

CPU:

```text
512 MB → GPU belleğine kopyala
```

GPU:

```text
512 MB üzerinde hesapla
```

Sonuç:

```text
GPU → CPU belleğine kopyala
```

Bu modelde CPU yalnızca program kontrolünü değil, büyük veri hareketinin yönetimini de üstlenebilir.

Bu durum özellikle büyük veri kümelerinde gereksiz işlem ve bağlantı trafiği oluşturabilir.

---

# 3. NEXSUS Modeli

NEXSUS'ta CPU'nun GPU'ya göndermesi gereken temel bilgi büyük verinin kendisi değildir.

CPU örneğin:

```text
CODE_ADDRESS
DATA_ADDRESS
DATA_SIZE
ENTRY_POINT
OUTPUT_ADDRESS
OUTPUT_SIZE
```

bilgilerini içeren bir görev tanımı oluşturabilir.

Örneğin:

```text
CODE_ADDRESS  = 0x12000000
DATA_ADDRESS  = 0x8A000000
DATA_SIZE     = 32 MB

ENTRY_POINT   = 0x12004000

OUTPUT_ADDRESS = 0x92000000
OUTPUT_SIZE    = 16 MB
```

Burada CPU GPU'ya 32 MB veriyi göndermemiştir.

CPU yalnızca:

> "Çalıştıracağın kod burada, kullanacağın veri burada, sonucu yazacağın alan burada."

demiştir.

---

# 4. CPU'nun Yeni Rolü

Bu mimaride CPU'nun görevi:

```text
PROGRAM ANALİZİ
      │
      ▼
GÖREV TANIMLAMA
      │
      ▼
ADRES + BOYUT + İŞLEM
      │
      ▼
GPU
```

şeklindedir.

CPU:

- veriyi taşımaz,
- GPU belleğini gereksiz yere doldurmaz,
- sonuç verisini kendisine kopyalatmaz,
- büyük veri transferini polling ile takip etmek zorunda kalmaz.

CPU esas olarak **işin ne olduğunu** belirler.

---

# 5. GPU'nun Rolü

GPU görevi aldıktan sonra kendisine verilen adresleri kaynak olarak kullanır.

Örneğin:

```text
TASK

CODE  = 0x12000000
DATA  = 0x8A000000
SIZE  = 32 MB
OUT   = 0x92000000
```

GPU:

```text
"32 MB veriye ihtiyacım var."
```

diyerek NEI üzerinden kaynak talep eder.

Burada GPU'nun görevi veriyi CPU'dan istemek değildir.

GPU:

```text
RESOURCE REQUEST
```

oluşturur.

Örneğin:

```text
SOURCE      = 0x8A000000
SIZE        = 32 MB
DESTINATION = GPU_LOCAL_BUFFER
```

---

# 6. NEI'nin Rolü

Bu noktada NEXSUS'un önemli mimari farklarından biri ortaya çıkar.

GPU:

```text
"Bu veriye ihtiyacım var."
```

der.

NEI:

```text
"Tamam."
```

der ve veri hareketini kendisi gerçekleştirir.

Akış:

```text
GPU
 │
 │ RESOURCE REQUEST
 │
 ▼
NEI
 │
 ▼
System Fabric
 │
 ▼
Data MOSRAM
 │
 │
 │ 32 MB
 ▼
System Fabric
 │
 ▼
NEI
 │
 ▼
GPU Local Memory
```

CPU bu veri yolunun üzerinde değildir.

---

# 7. System Fabric'in Görevi

System Fabric burada yalnızca bir bağlantı mekanizması değildir.

Verinin sistem içerisindeki gerçek hareket yolunu belirleyen altyapıdır.

Örneğin:

```text
Data MOSRAM
     │
     ▼
System Fabric
     │
     ▼
NEI
     │
     ▼
GPU
```

veya başka bir durumda:

```text
M-SSD
 │
 ▼
System Fabric
 │
 ▼
Data MOSRAM
```

olabilir.

Daha ileri bir durumda:

```text
M-SSD
 │
 ▼
System Fabric
 │
 ▼
NEI
 │
 ▼
GPU
```

şeklinde CPU'yu tamamen devreden çıkaran bir veri yolu da kullanılabilir.

---

# 8. CPU → GPU İletişimi ile Veri İletişiminin Ayrılması

NEXSUS'ta CPU → GPU iletişimi iki farklı sınıfa ayrılır.

### Kontrol trafiği

```text
CPU → GPU
```

küçük görev bilgileri:

```text
CODE_ADDRESS
DATA_ADDRESS
SIZE
ENTRY_POINT
OUTPUT_ADDRESS
FLAGS
```

### Veri trafiği

```text
MOSRAM ↔ System Fabric ↔ NEI ↔ GPU
```

büyük miktarda gerçek veri.

Bu iki trafiğin aynı şey olmadığı özellikle korunmalıdır.

```text
CPU → GPU
       │
       └── küçük CONTROL trafiği

MOSRAM → NEI → GPU
       │
       └── büyük DATA trafiği
```

Böylece CPU'nun veri hacmi ile hesaplama veri hacmi birbirinden bağımsız hale gelir.

---

# 9. Hesaplama Sonucunun Geri Dönüşü

Hesaplama tamamlandığında daha önemli bir optimizasyon ortaya çıkar.

GPU sonucu CPU'ya göndermek zorunda değildir.

GPU:

```text
RESULT
```

verisini doğrudan hedef adrese yazdırabilir.

Örneğin:

```text
OUTPUT_ADDRESS = 0x92000000
```

GPU sonucu üretir:

```text
GPU
 │
 │ RESULT
 ▼
NEI
 │
 ▼
System Fabric
 │
 ▼
Data MOSRAM
```

Sonuç artık doğrudan sistem belleğindedir.

CPU'ya yüzlerce MB veri geri taşınmaz.

---

# 10. Sonuç Yazma Onayı

NEI veri yazma işlemini tamamladığında GPU'ya bir tamamlanma bilgisi gönderebilir.

Örneğin:

```text
WRITE_COMPLETE

ADDRESS = 0x92000000
SIZE    = 16 MB
STATUS  = OK
```

GPU:

```text
"Sonuç belleğe yazıldı."
```

bilgisini alır.

Bu yaklaşım modern DMA mimarilerindeki descriptor ve completion event kavramlarıyla uyumludur; örneğin güncel AMD DMA belgelerinde descriptor'ların kaynak, hedef ve transfer uzunluğunu tanımladığı, tamamlanma durumunun ise event/interrupt veya writeback ile bildirilebildiği belirtilmektedir.

Ancak NEXSUS'ta bunun amacı yalnızca DMA gerçekleştirmek değildir.

Buradaki amaç:

> **CPU'nun veri taşıma işinden tamamen ayrılmasıdır.**

---

# 11. Tam NEXSUS CPU–GPU Akışı

Genel işlem:

```text
                         CPU
                          │
                          │ TASK
                          │
                          │ code address
                          │ data address
                          │ size
                          │ output address
                          ▼
                         GPU
                          │
                          │ RESOURCE REQUEST
                          ▼
                         NEI
                          │
                          ▼
                    SYSTEM FABRIC
                     /           \
                    /             \
                   ▼               ▼
        Application MOSRAM      Data MOSRAM
                   │               │
                   └──────┬────────┘
                          │
                          ▼
                         NEI
                          │
                          ▼
                    GPU LOCAL MEMORY
                          │
                          ▼
                      GPU COMPUTE
                          │
                          ▼
                        RESULT
                          │
                          ▼
                         NEI
                          │
                          ▼
                    SYSTEM FABRIC
                          │
                          ▼
                      DATA MOSRAM
                          │
                          │ WRITE COMPLETE
                          ▼
                         GPU
```

Bu sistemde CPU yalnızca başlangıçtaki görev tanımında ve gerektiğinde sonuç durum bilgisinde bulunur.

Büyük veri CPU üzerinden dolaşmak zorunda değildir.

---

# 12. Nexus Flow Açısından Temel Değişim

Bu mimari Nexus Flow dilinin veri modelini doğrudan etkileyebilir.

Klasik bir programlama modelinde:

```text
result = gpu_compute(data)
```

gibi bir ifade düşünülebilir.

Nexus Flow'un altında ise bunun fiziksel karşılığı:

```text
DATA_ADDRESS
      ↓
RESOURCE_REQUEST
      ↓
GPU
      ↓
RESULT_ADDRESS
```

olabilir.

Yani:

```text
data
```

aslında yalnızca bir değer değildir.

NEXSUS açısından:

```text
data = location + size + type + ownership/state
```

gibi daha zengin bir kaynak tanımına dönüşebilir.

---

# 13. Veri ile Adresin Ayrılması

Buradaki temel düşünce:

```text
DATA ≠ TRANSFER
```

şeklinde ifade edilebilir.

Bir programın bir veriye erişmesi, verinin mutlaka işlemcinin bulunduğu fiziksel belleğe taşınması anlamına gelmez.

Daha doğru ifade:

```text
DATA → LOCATION
```

ve işlem:

```text
PROCESS(LOCATION)
```

üzerinden gerçekleştirilebilir.

Bu nedenle Nexus Flow'da ileride şu tür kavramların oluşması mümkündür:

```text
address
buffer
region
resource
stream
view
```

Bunların hepsi gerçek verinin kendisi olmak zorunda değildir.

Bir kısmı verinin sistem içerisindeki **konumunu ve kullanım hakkını** temsil edebilir.

---

# 14. Adres Değişimi

Bu nedenle NEXSUS'ta işlemciler arasındaki temel iletişimlerden biri:

> **veri değişimi değil, adres değişimi**

olabilir.

Örneğin:

```text
CPU:
DATA = 0x8A000000
```

GPU'ya:

```text
0x8A000000
```

adresini bildirir.

GPU'nun ihtiyacı olan veri için:

```text
NEI:
SOURCE = 0x8A000000
SIZE   = 32 MB
```

talebi oluşturulur.

Sonuç için:

```text
GPU:
OUTPUT = 0x92000000
```

belirlenir.

Sonrasında sistem:

```text
0x8A000000
      │
      ▼
    GPU
      │
      ▼
0x92000000
```

ilişkisini gerçekleştirir.

Gerçek 32 MB verinin CPU tarafından taşınması gerekmez.

---

# 15. Adresin Kendisi de Veri Haline Gelir

Bu modelin daha ileri bir sonucu vardır.

CPU'nun GPU'ya gönderdiği bilgi:

```text
32 MB veri
```

değil,

```text
64-bit ADDRESS
32-bit SIZE
ENTRY POINT
FLAGS
```

gibi çok küçük bir görev tanımıdır.

Örneğin:

```text
TASK_SIZE ≪ DATA_SIZE
```

olur.

32 MB veri için belki birkaç düzine byte görev tanımı yeterlidir.

Bu nedenle kontrol trafiği ile veri trafiği arasındaki oran dramatik biçimde değişir.

---

# 16. Veri Taşımayan CPU

Bu mimarinin en önemli sonucu CPU'nun çalışma karakterinin değişmesidir.

CPU:

```text
hesaplama
+
program kontrolü
+
görev dağıtımı
```

yapar.

Fakat:

```text
büyük veri kopyalama
```

CPU'nun temel görevlerinden biri olmaktan çıkar.

Örneğin:

```text
CPU
 │
 ├── TASK → GPU
 │
 ├── TASK → FAPU
 │
 └── TASK → başka hızlandırıcı
```

gibi bir yapı mümkündür.

Gerçek veri ise:

```text
MOSRAM
 │
 ├──→ GPU
 ├──→ FAPU
 ├──→ NPU
 └──→ başka Fabric node
```

yollarından geçebilir.

---

# 17. GPU'nun Veriye Yaklaşımı

GPU kendisine verilen bütün veri kümesini almak zorunda değildir.

Örneğin:

```text
DATA = 4 GB
```

olsun.

GPU yalnızca:

```text
0–32 MB
```

bölümüne ihtiyaç duyuyorsa:

```text
RESOURCE REQUEST
ADDRESS = A
SIZE = 32 MB
```

yeterlidir.

Daha sonra:

```text
ADDRESS = B
SIZE = 32 MB
```

isteyebilir.

Böylece 4 GB veri kümesinin tamamını GPU belleğine taşımak yerine ihtiyaç duyulan parçalar getirilebilir.

Bu model özellikle büyük veri kümeleri için önemlidir.

---

# 18. Kod İçin de Aynı Model

Aynı prensip yalnızca veri için değil, kod için de uygulanabilir.

CPU:

```text
CODE_ADDRESS = 0x12000000
ENTRY_POINT  = 0x12004000
```

bilgisini GPU'ya verir.

GPU bütün programı almak zorunda olmayabilir.

Örneğin yalnızca:

```text
0x12004000 – 0x1200C000
```

arasındaki gerekli kod bölümünü isteyebilir.

Böylece:

```text
Application MOSRAM
        │
        ▼
System Fabric
        │
        ▼
NEI
        │
        ▼
GPU Instruction Buffer
```

akışı oluşur.

Bu, Application MOSRAM'ın CPU'ya yakın konumlandırılmasıyla da uyumludur.

---

# 19. Sonuç Belleğinin Önceden Belirlenmesi

Görevin başında sonuç alanı belirlenebilir:

```text
INPUT:
0x8A000000

OUTPUT:
0x92000000
```

Böylece GPU hesaplama sırasında:

```text
"Sonucu nereye koyacağım?"
```

sorusunu tekrar CPU'ya sormaz.

Görev tanımı zaten hedefi belirtmiştir.

Sonuç:

```text
GPU → NEI → System Fabric → OUTPUT_ADDRESS
```

üzerinden doğrudan yazılır.

---

# 20. CPU'nun "İşim Bitti" Noktası

Bu mimarinin en sade ifadesi aslında kullanıcının tarif ettiği modeldir:

```text
CPU:

"Benim işim bitti.

Kod burada.
Girdi verisi burada.
Verinin boyutu bu.
Sonuç için ayrılan alan burada.

Devamını siz halledin."
```

Sonrasında:

```text
GPU:

"Veriyi aldım."

...

"İşlem bitti."

NEI:

"Sonucu belirtilen adrese yazıyorum."

...

"Yazma tamamlandı."

GPU:

"Tamam."
```

CPU'nun tekrar büyük veriyle uğraşmasına gerek yoktur.

---

# 21. Kontrol, Veri ve Durum Trafiği

Bu mimari NEXSUS System Fabric'in üç temel trafik sınıfıyla doğrudan örtüşür.

### CONTROL

```text
CPU → GPU

TASK
ADDRESS
SIZE
ENTRY
FLAGS
```

### DATA

```text
MOSRAM ↔ NEI ↔ GPU
```

### STATUS

```text
NEI → GPU
GPU → CPU
```

Örneğin:

```text
CONTROL
CPU ───────────────→ GPU

DATA
MOSRAM ─→ Fabric ─→ NEI ─→ GPU

STATUS
NEI ───────────────→ GPU
GPU ───────────────→ CPU
```

Böylece büyük veri trafiği küçük kontrol mesajlarının önüne geçmez.

---

# 22. CPU'nun Sonucu Okuması

CPU gerçekten sonucun içeriğine ihtiyaç duyuyorsa yine doğrudan bellek adresinden okuyabilir:

```text
GPU
 │
 ▼
NEI
 │
 ▼
Data MOSRAM
 │
 │
 ▼
CPU
```

Ancak burada kritik fark şudur:

CPU'nun okuması:

```text
"sonucu GPU'dan geri al"
```

değildir.

CPU:

```text
"sonuç zaten bellekte."
```

der ve ilgili bellek alanına erişir.

---

# 23. Aynı Sonuç Başka Bir Birime de Verilebilir

Bu modelin önemli avantajlarından biri de sonucun CPU'ya ait olmak zorunda olmamasıdır.

Örneğin GPU sonucu:

```text
Data MOSRAM
```

yerine başka bir Fabric node'unun kullanacağı alana yazabilir.

Örneğin:

```text
GPU
 │
 ▼
NEI
 │
 ▼
System Fabric
 │
 ├──→ Data MOSRAM
 ├──→ FAPU
 ├──→ NPU
 └──→ başka accelerator
```

Böylece:

```text
GPU → CPU → FAPU
```

yerine:

```text
GPU → Fabric → FAPU
```

mümkün hale gelir.

Bu, NEXSUS'un CPU-merkezli olmayan mimarisinin doğrudan sonucudur.

---

# 24. Nexus Flow İçin Yeni Soyutlama

Buradan Nexus Flow açısından daha genel bir model ortaya çıkar:

```text
RESOURCE
   │
   ├── LOCATION
   ├── SIZE
   ├── TYPE
   ├── ACCESS
   └── STATE
```

Bir işlem:

```text
COMPUTE(resource)
```

şeklinde ifade edilebilir.

Derleyici ve çalışma zamanı sistemi bunun altında:

```text
resource.location
resource.size
resource.type
```

bilgilerini kullanarak uygun Fabric işlemlerini oluşturabilir.

Böylece Nexus Flow kaynak kodu donanımın fiziksel veri taşıma ayrıntılarını bilmek zorunda kalmaz.

---

# 25. Derleyicinin Rolü

Nexus Flow derleyicisi daha sonra kodun hangi bölümlerinin hangi işlem birimlerinde çalıştırılabileceğini belirleyebilir.

Örneğin:

```text
CPU:
    control-heavy section

GPU:
    massively parallel section

FAPU:
    specialized computation

NPU:
    prediction / behavior optimization
```

Derleyici veya runtime:

```text
TASK
CODE_ADDRESS
DATA_ADDRESS
OUTPUT_ADDRESS
```

üretir.

Fakat gerçek veri hareketini kendisi yapmak zorunda değildir.

Bu iş:

```text
NEI
+
System Fabric
+
Memory Controller
```

tarafından gerçekleştirilir.

---

# 26. Veri Hareketinin Donanıma Devredilmesi

Mimari olarak:

```text
Nexus Flow
     │
     ▼
Compiler / Runtime
     │
     ▼
TASK DESCRIPTOR
     │
     ▼
Compute Unit
     │
     ▼
Resource Request
     │
     ▼
NEI
     │
     ▼
System Fabric
     │
     ▼
Memory
```

şeklinde bir katmanlaşma oluşur.

Bu ayrım sayesinde programlama dili:

> **"veriyi nasıl taşıyacağım?"**

sorusuyla uğraşmak yerine:

> **"hangi veriyi, hangi işlemde kullanacağım?"**

sorusuna odaklanır.

---

# 27. Adres Değişimi Neden Önemli?

NEXSUS'un yüksek bant genişlikli mimarisinde veri miktarı büyüdükçe CPU'nun veri taşıması daha pahalı hale gelir.

Örneğin:

```text
1 GB veri
```

için CPU'nun yalnızca:

```text
ADDRESS + SIZE
```

bilgisini aktarması ile 1 GB verinin kendisini aktarması arasında büyük fark vardır.

Bu nedenle:

\[
T_{control} \ll T_{data}
\]

ve NEXSUS mümkün olduğunca:

\[
CPU\rightarrow GPU \approx CONTROL
\]

olmasını,

\[
MOSRAM\rightarrow GPU \approx DATA
\]

olmasını hedefler.

---

# 28. Adres Tabanlı Veri Akışının Genel Modeli

NEXSUS için genel veri akışı:

```text
                    ┌──────────────┐
                    │     CPU      │
                    └──────┬───────┘
                           │
                     TASK / ADDRESS
                           │
                           ▼
                    ┌──────────────┐
                    │     GPU      │
                    └──────┬───────┘
                           │
                     RESOURCE REQUEST
                           │
                           ▼
                    ┌──────────────┐
                    │     NEI      │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │System Fabric │
                    └──────┬───────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
             Application      Data MOSRAM
                MOSRAM
                    │             │
                    └──────┬──────┘
                           ▼
                          GPU
                           │
                        COMPUTE
                           │
                         RESULT
                           │
                           ▼
                          NEI
                           │
                           ▼
                    System Fabric
                           │
                           ▼
                     Data MOSRAM
                           │
                    WRITE COMPLETE
                           │
                           ▼
                          GPU
```

---

# 29. NEXSUS'un Temel Kuralı

Bu mimariden şu temel kural çıkarılabilir:

> **Bir işlemcinin başka bir işlemciye veri göndermesi gerekiyorsa, ilk tercih verinin işlemci tarafından taşınması değil, verinin adresinin ve erişim gereksiniminin bildirilmesidir.**

Ardından veriyi fiziksel olarak taşıması gereken birim belirlenir.

Bu birim:

- NEI,
- System Fabric,
- Memory Controller,
- M-SSD Controller,
- NPI Controller

veya gelecekteki başka bir Fabric node olabilir.

---

# 30. Adres Değişimi Birinci Sınıf İşlem

Nexus Flow ve NEXSUS mimarisinde ileride özel bir kavram olarak:

```text
ADDRESS EXCHANGE
```

veya daha genel olarak:

```text
RESOURCE EXCHANGE
```

tanımlanabilir.

Örneğin:

```text
CPU → GPU

RESOURCE:
    CODE    = A
    INPUT   = B
    OUTPUT  = C
```

Burada:

```text
A, B, C
```

verinin kendisi değildir.

Verinin bulunduğu **kaynak konumlarıdır**.

Bu nedenle sistem:

```text
DATA EXCHANGE
```

yerine:

```text
RESOURCE / ADDRESS EXCHANGE
```

gerçekleştirir.

---

# 31. Sonuç

NEXSUS ve Nexus Flow birlikte değerlendirildiğinde yeni bir bilgisayar mimarisi anlayışı ortaya çıkmaktadır.

Geleneksel yaklaşım:

```text
İşlemci → Veri → İşlemci
```

iken NEXSUS yaklaşımı:

```text
İşlemci
   │
   │ adres + görev
   ▼
İşlem birimi
   │
   │ kaynak talebi
   ▼
Fabric
   │
   │ veri
   ▼
İşlem birimi
```

şeklindedir.

Sonuç da aynı şekilde doğrudan hedef belleğe yazılır:

```text
GPU
 │
 ▼
NEI
 │
 ▼
System Fabric
 │
 ▼
Data MOSRAM
```

CPU'ya geri kopyalanması zorunlu değildir.

Dolayısıyla NEXSUS'ta:

> **CPU işi tanımlar.**

> **GPU işi gerçekleştirir.**

> **NEI veriyi taşır.**

> **System Fabric verinin yolunu oluşturur.**

> **MOSRAM veriyi tutar.**

> **CPU sonucu gerektiğinde adresinden okur.**

Bunun Nexus Flow'daki temel karşılığı ise:

> **Veriyi taşımak yerine verinin adresini taşımak.**

Bu yaklaşım, NEXSUS'un CPU-merkezli veri hareketinden uzaklaşmasının ve System Fabric'i gerçek bir sistem omurgası haline getirmesinin temel ilkelerinden biridir.
---