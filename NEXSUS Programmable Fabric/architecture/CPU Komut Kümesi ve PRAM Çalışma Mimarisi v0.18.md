# NEXSUS-ISA-018
## CPU Komut Kümesi ve PRAM Çalışma Mimarisi

**Sürüm:** 0.3  
**Statü:** Mimari taslak  
**Platform:** NEXSUS Programlanabilir Çip

---

### 1. Amaç ve tasarım ilkeleri

NEXSUS CPU, genel amaçlı bir bilgisayar işlemcisi olmaktan ziyade programlanabilir çipin kontrolünü, görev dağıtımını ve veri akışını yöneten bir işlem birimidir.

Bu nedenle mimari, gereksiz adres hesaplamalarını ve donanım karmaşıklığını azaltmayı hedefler.

Temel ilkeler:

- Ana kontrol CPU'su 32 bitlik bir mimari kullanır.
- Küçük kontrol işlemcileri 16 bit olabilir.
- Genel amaçlı kayıtçı sayısı en fazla 32'dir.
- Klasik stack yapısı zorunlu değildir.
- CPU içinde ayrı ve doğrudan erişilebilir PRAM birimleri bulunur.
- PRAM birimlerinin sayısı işlemci modeline göre ölçeklenebilir.
- Vektör ve matris işlemleri CPU'nun doğal işlem genişliğinden bağımsızdır.

### 2. CPU genel amaçlı kayıtçıları

Ana CPU için `R00–R31` aralığında en fazla 32 genel amaçlı kayıtçı öngörülür.

| Özellik | Tasarım |
|---|---|
| Kayıtçı adlandırması | R00–R31 |
| Kayıtçı genişliği | 32 bit |
| Toplam kayıtçı sayısı | En fazla 32 |
| Temel kullanım | Aritmetik, mantıksal işlemler, adresler ve kontrol verileri |

Küçük kontrol işlemcileri daha az sayıda kayıtçıyla tasarlanabilir. Kayıtçı sayısının bütün işlemci modellerinde aynı olması zorunlu değildir.

### 3. PRAM — Page Register RAM

PRAM, CPU'nun içinde bulunan, doğrudan erişilebilir ve genel amaçlı kayıtçılardan daha geniş çalışma alanı sağlayan yerel bellek birimidir.

PRAM, tek bir ortak belleğin sayfalarından oluşmaz. Her PRAM birimi fiziksel olarak ayrı bir çalışma bloğu şeklinde tasarlanır.

Örnek adlandırma:

- `PR0`
- `PR1`
- `PR2`
- `PR3`

Her isim bağımsız bir PRAM birimini temsil eder.

**Önemli:** `PR0`, `PR1` ve benzeri adlar tek tek veri hücrelerini değil, PRAM birimlerini belirtir. Birimlerin kendi içindeki veri alanları ayrıca düzenlenir.

### 4. Ayrı PRAM birimlerinin gerekçesi

Tek ve büyük bir PRAM yerine ayrı birimler kullanmanın hedeflenen avantajları şunlardır:

**4.1. Doğrudan birim seçimi**

CPU, hangi çalışma alanına erişeceğini PRAM biriminin kimliği üzerinden belirler. Her erişimde ortak bir belleğin sayfa adresini hesaplamak zorunda kalmaz.

**4.2. Bağımsız çalışma alanları**

Farklı PRAM birimleri farklı amaçlarla kullanılabilir. Örneğin biri görev bağlamını, diğeri geçici verileri, bir başkası da alt program durumunu tutabilir.

**4.3. Ölçeklenebilir donanım**

Küçük bir işlemci yalnızca `PR0` ile başlayabilir. Daha büyük bir işlemciye `PR1`, `PR2` ve ek birimler, ihtiyaç duyulan kaynaklar ölçüsünde eklenebilir.

**4.4. Daha sade kaynak yönetimi**

CPU ve derleyici, verinin hangi çalışma alanında bulunduğunu doğrudan bilir. Bu yaklaşım, tek bir büyük bellekte sürekli değişen sayfa adreslerini yönetme gereksinimini azaltabilir.

Bununla birlikte, PRAM birimlerinin bağımsız olması kendi başına daha yüksek hız garantisi vermez. Gerçek performans; birimlerin port sayısına, erişim gecikmesine ve CPU bağlantısına bağlıdır.

### 5. PRAM kapasitesi ve ölçeklenmesi

İlk tasarım hedefi, her PRAM birimi için 4 KB çalışma alanı kullanılmasıdır.

Bu değer başlangıç hedefidir; kesin donanım kararı değildir.

| İşlemci sınıfı | PRAM organizasyonu |
|---|---|
| Küçük kontrol işlemcisi | 1 birim: `PR0` |
| Standart kontrol işlemcisi | Gereksinime göre bir veya daha fazla birim |
| Büyük kontrol işlemcisi | Görev ve veri ihtiyacına göre birden fazla bağımsız birim |

Toplam PRAM kapasitesi, birim sayısı ve birim başına kapasiteyle ölçeklenir.

Örneğin iki adet 4 KB PRAM birimi, toplam 8 KB yerel çalışma belleği sağlar; ancak bunlar ortak bir adres alanı oluşturmak zorunda değildir.

### 6. PRAM erişim modeli

CPU, PRAM birimlerine doğrudan erişebilmelidir.

Kavramsal kullanım örneği:

- `PRLOAD PR0, R05` — PR0 içindeki belirli bir veri alanını R05'e yükleme.
- `PRSTORE PR1, R07` — R07 değerini PR1 içindeki belirli bir veri alanına yazma.
- `PRCOPY PR0, PR1` — PRAM birimleri arasında veri kopyalama.

Bu komutlar örnek gösterimdir; kesin sözdizimi ve operand alanları henüz belirlenmemiştir.

PRAM biriminin seçimi ile birim içindeki veri alanının seçimi birbirinden ayrılır. Ayrı blok mimarisi, birim seçimi için ortak bellek sayfalaması gereksinimini ortadan kaldırmayı hedefler; birimin içindeki veriye erişmek içinse yine bir konum veya alan tanımı gerekir.

### 7. PRAM kullanım alanları

PRAM birimleri farklı görevler için atanabilir:

- Görev ve yürütme durumu.
- Alt program dönüş adresleri.
- Kesme sırasında saklanan bağlam.
- Geçici veri ve ara sonuçlar.
- DMA görev tanımlayıcıları.
- Fabric işlem istekleri ve sonuçları.

Bu görev dağılımı sabit olmak zorunda değildir. İşletim modeli veya derleyici, işlemci yeteneklerine göre PRAM birimlerini farklı amaçlarla kullanabilir.

Bir PRAM birimine ihtiyaç duyulmayan durumlarda kaynak boşa ayrılmamalıdır; işlemci modeli yalnızca gerekli birimleri içerebilir.

### 8. Stack yerine PRAM

NEXSUS CPU'da klasik stack zorunlu değildir.

Alt program çağrılarında dönüş adresleri PRAM içinde saklanabilir veya özel bağlantı kayıtçıları kullanılabilir. Kesme ve iç içe çağrılar için gerekli bağlam da uygun PRAM alanlarında tutulabilir.

Ancak stack'in kaldırılması, çağrı durumlarının saklanması gereksinimini ortadan kaldırmaz. İç içe çağrıların, kesmelerin ve eşzamanlı görevlerin birbirlerinin durumlarını ezmemesi için ayrı alanlar veya açık bir bağlam yönetim yöntemi gerekir.

### 9. Temel komut grupları

Komut kümesi aşağıdaki grupları kapsayacak şekilde geliştirilecektir.

**Aritmetik ve mantıksal işlemler**

`MOV`, `LDI`, `ADD`, `SUB`, `MUL`, `DIV`, `AND`, `OR`, `XOR`, `NOT`, `SHL`, `SHR`, `CMP`

**Bellek erişimi**

`LOAD`, `STORE`, `LOADX`, `STOREX`

**Kontrol akışı**

`JMP`, `BRZ`, `BRNZ`, `BRCC`, `CALL`, `RET`

**PRAM erişimi**

`PRLOAD`, `PRSTORE`, `PRCOPY`

**Görev ve Fabric kontrolü**

`TASK`, `DMA_START`, `WAIT`, `FENCE`, `STATUS`

Bunlar mantıksal komut aileleridir. Son aşamada bunların bağımsız makine komutları mı, yoksa bazı durumlarda özel kontrol arayüzlerinin gösterimi mi olacağı belirlenecektir.

### 10. Vektör ve matris birimleri

CPU'nun 32 bitlik doğal işlem genişliği, Fabric içindeki vektör ve matris birimlerini sınırlandırmaz.

Öngörülen işlemler:

- Vektör toplama ve çarpma.
- Çarpma-toplama birleşik işlemleri.
- Geniş veri bloklarının aktarılması.
- DMA üzerinden veri besleme ve sonuç toplama.

256 bitlik vektör genişliği bir tasarım hedefidir. Gerçek kapasite ve paralellik, programlanabilir Fabric kaynaklarıyla birlikte belirlenecektir.

### 11. OCC derleyicisiyle ilişki

OCC, PRAM birimlerini işlemci modelinin tanımlı kaynakları olarak görmelidir.

Derleme sırasında:

1. Geçici veriler ve görev durumları için uygun PRAM birimi seçilir.
2. Birimlerin kapasite sınırları kontrol edilir.
3. Birimler arası veri aktarımı gerektiğinde uygun komut veya aktarım görevi üretilir.
4. Aynı PRAM alanının çakışan biçimde kullanılmasını önleyecek kaynak yönetimi yapılır.
5. Donanımda bulunmayan PRAM birimlerine erişim engellenir.

Böylece tek bir PRAM sayısına bağlı kalmadan farklı CPU modelleri için aynı mimari yaklaşım kullanılabilir.

### 12. Açık tasarım kararları

Bir sonraki aşamada şu konular netleştirilmelidir:

- Her PRAM biriminin kesin kapasitesi.
- PRAM'in bayt, 16 bit kelime veya 32 bit kelime üzerinden erişimi.
- Aynı çevrimde kaç PRAM erişiminin yapılabileceği.
- PRAM birimleri arasında doğrudan aktarım desteği.
- Çağrı, kesme ve görev bağlamlarının yerleşimi.
- PRAM birimlerinin donanım tarafından mı, OCC tarafından mı tahsis edileceği.
- PRAM erişimlerinin komut kodlaması.

### Sonuç

NEXSUS CPU, en fazla 32 adet 32 bit genel amaçlı kayıtçı ve ayrı, doğrudan erişilebilir PRAM birimleri temelinde tasarlanacaktır.

PRAM birimleri ortak bir büyük bellek içindeki sayfalar olarak değil, CPU içinde ayrı çalışma blokları olarak ele alınacaktır. Birim sayısı işlemci modeline göre ölçeklenebilecek; klasik stack zorunlu olmayacaktır.

Bu yaklaşım, NEXSUS'un modüler kontrol mimarisini ve farklı boyutlardaki programlanabilir çip modellerini desteklemeyi amaçlar.