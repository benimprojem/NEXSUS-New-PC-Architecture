# Yeni Nesil Ayrıştırılmış Register Tabanlı CPU Mimarisi

## 1. Giriş

Bu CPU mimarisinin temel amacı, klasik işlemci tasarımlarında farklı görevler için aynı register ve bellek yapılarının kullanılmasından kaynaklanan veri erişim darboğazlarını azaltmak ve işlemcinin farklı işlem türlerini fiziksel olarak ayrıştırmaktır.

Mimari üç temel register alanı üzerine kuruludur:

- **RA00–RA63:** Application / Scalar Register Bank
- **DA00–DA63:** Data Register Bank
- **MA00–MA31:** Matrix / Vector Register Bank

Bunlara ek olarak kod belleği ve veri belleği birbirinden fiziksel ve mantıksal olarak ayrılır.

Temel yapı:

```text
                         CPU
                          │
              ┌───────────┴───────────┐
              │ Instruction / Control │
              │       Unit            │
              └───────────┬───────────┘
                          │
              ┌───────────┴───────────┐
              │    Instruction        │
              │       Decode          │
              └───────┬───────┬───────┘
                      │       │
                Scalar Path   Vector/Matrix Path
                      │       │
              ┌───────▼───┐ ┌─▼────────────┐
              │ RA00-RA63 │ │ MA00-MA31    │
              │ 64 × 64b  │ │ 32 × 256b   │
              └───────┬───┘ └──────┬───────┘
                      │            │
                   Scalar ALU   Matrix/Vector ALU
                      │            │
              ┌───────▼───┐        │
              │ DA00-DA63 │◄───────┘
              │ 64 × 64b  │
              └───────┬───┘
                      │
                 Load / Store
                      │
                ┌─────▼─────┐
                │ DATA RAM  │
                └───────────┘
```

Buradaki temel prensip, **instruction, application state, data ve vector/matrix işlemlerinin aynı kaynak için birbirleriyle yarışmasını mümkün olduğunca önlemektir.**

---

# 2. Bellek Mimarisi

Mimari iki temel bellek alanını birbirinden ayırır.

## 2.1. CODE Memory

CODE memory yalnızca veya ağırlıklı olarak program kodlarının tutulduğu alandır.

Önerilen mimari kapasite:

```text
Normal hedef:       ~4 GB
Mimari üst sınır:   ~8 GB
```

Buradaki 4–8 GB değeri tek bir programın mutlaka bu kadar kod kullanacağı anlamına gelmez. Amaç, sistemin toplam aktif uygulama/kod alanı açısından geniş bir adresleme kapasitesine sahip olmasıdır.

CODE memory'nin temel özelliği:

- Instruction Fetch için kullanılır.
- Data RAM ile aynı fiziksel erişim yolunu paylaşmaz.
- Çoğunlukla read ağırlıklıdır.
- Instruction pipeline tarafından sürekli okunabilir.

Temel akış:

```text
CODE MEMORY
     │
     ▼
Instruction Fetch
     │
     ▼
Instruction Decode
     │
     ├──────────► RA / Scalar
     ├──────────► DA / Data
     └──────────► MA / Vector-Matrix
```

Bu ayrım sayesinde işlemci veri belleğine erişirken instruction fetch işleminin aynı kaynağı beklemesi gerekmez.

---

# 3. DATA Memory

DATA memory uygulamanın çalışma sırasında kullandığı değişkenler, büyük veri kümeleri, dosya tamponları ve diğer çalışma verileri için kullanılır.

Başlangıç mimarisi:

```text
Minimum:       8 GB
Genişleme:     16 GB
               32 GB
               64 GB
               128 GB+
```

CODE memory sabit veya büyük ölçüde sabit tutulurken DATA memory sistem tasarımına göre genişletilebilir.

Bu ayrım özellikle büyük veri kullanan uygulamalarda önemlidir.

Örneğin:

```text
CODE
4 GB
│
├── Program A
├── Program B
├── Program C
└── System Code

DATA
64 GB
│
├── Application Data
├── Buffers
├── Images
├── Models
├── Databases
└── Runtime Data
```

Dolayısıyla büyük veri kullanan bir uygulamanın veri ihtiyacı arttığında kod alanının değiştirilmesi gerekmez.

---

# 4. RA Register Bank

RA register bankı işlemcinin ana application/scalar state alanıdır.

```text
RA00
RA01
RA02
...
RA61
RA62
RA63
```

Toplam:

$$\[
64 \times 64 = 4096\text{ bit}
\]$$

yani toplam **512 byte** fiziksel register kapasitesi bulunur.

Her RA registerı 64 bittir.

RA registerlarının görevleri:

- Arithmetic işlemleri
- Pointer değerleri
- Fonksiyon parametreleri
- Return değerleri
- Local state
- Geçici değerler
- Adres hesaplamaları
- Kontrol değerleri

gibi işlemleri gerçekleştirmektir.

Önemli nokta:

**RA00–RA63 bir adres değeri taşıyan registerlar değildir.**

Bunların kendileri CPU içindeki fiziksel register seçimleridir.

Örneğin:

```text
ADD RA03, RA07, RA12
```

şu anlama gelir:

$$\[
RA12 = RA03 + RA07
\]$$

CPU instruction decoder doğrudan RA03, RA07 ve RA12 fiziksel registerlarını seçer.

Arada:

```text
RA03 → başka register → RA03'ün adresi
```

gibi ikinci bir register adresleme katmanı bulunmaz.

---

# 5. DA Register Bank

DA register bankı doğrudan veri yolu ile ilişkili register alanıdır.

```text
DA00
DA01
...
DA62
DA63
```

Toplam:

$$\[
64 \times 64 = 4096\text{ bit}
\]$$

kapasiteye sahiptir.

Her register:

$$\[
64\text{ bit}
\]$$

genişliğindedir.

DA registerları özellikle DATA memory ile CPU arasındaki yüksek hızlı veri transferinde kullanılır.

Örneğin:

```text
DATA RAM
   │
   ▼
LOAD
   │
   ▼
DA12
```

veya:

```text
DA12
  │
  ▼
STORE
  │
  ▼
DATA RAM
```

Bu nedenle DA bankı, RA bankından mantıksal olarak ayrılmış bir **data staging / processing register alanı** oluşturur.

---

# 6. MA Register Bank

Mimarinin en önemli farklılıklarından biri MA register bankıdır.

```text
MA00
MA01
...
MA30
MA31
```

Toplam:

$$\[
32 \times 256 = 8192\text{ bit}
\]$$

yani:

$$\[
1024\text{ byte}
\]$$

register kapasitesi vardır.

Her MA registerı fiziksel olarak **256 bit** genişliğindedir.

Ancak bu 256 bitin tek bir 256-bit sayı olarak kullanılması zorunlu değildir.

MA registerları değişken element genişliğine sahiptir.

| İşlem genişliği | Bir MA registerındaki element sayısı |
|---:|---:|
| 8 bit | 32 |
| 16 bit | 16 |
| 32 bit | 8 |
| 64 bit | 4 |
| 128 bit | 2 |
| 256 bit | 1 |

Örneğin 8-bit modunda:

```text
MA00
┌──┬──┬──┬──┬──┬──┬──┬──┬──────┐
│8 │8 │8 │8 │8 │8 │8 │8 │ ...  │
└──┴──┴──┴──┴──┴──┴──┴──┴──────┘
              32 × 8 bit
```

64-bit modunda:

```text
MA00
┌────────┬────────┬────────┬────────┐
│ 64 bit │ 64 bit │ 64 bit │ 64 bit │
└────────┴────────┴────────┴────────┘
```

256-bit modunda ise register tek bir veri olarak kullanılabilir.

Bu yapı MA bankını klasik scalar registerlardan ayırarak doğal bir SIMD/vector/matrix işlem alanı oluşturur.

---

# 7. Variable Width İşlem Sistemi

MA registerlarının fiziksel genişliği sabit:

$$\[
W_{MA}=256\text{ bit}
\]$$

ancak işlem genişliği:

$$\[
W_{op}\in\{8,16,32,64,128,256\}
\]$$

olabilir.

Dolayısıyla aynı donanım farklı veri tiplerinde çalışabilir.

Örneğin:

```text
MADD.8
MADD.16
MADD.32
MADD.64
MADD.128
MADD.256
```

Buradaki `.8`, `.16`, `.32` vb. değerler register genişliğini değil **işlem element genişliğini** belirtir.

Bu özellikle AI, görüntü işleme, sinyal işleme, fiziksel simülasyon ve matris hesaplamaları için önemlidir.

---

# 8. Scalar ve Vector/Matrix İşlemlerinin Ayrılması

CPU içerisinde iki temel hesaplama yolu bulunur.

### Scalar Path

```text
RA
 │
 ▼
Scalar ALU
 │
 ▼
RA / DA
```

### Vector / Matrix Path

```text
MA
 │
 ▼
Vector / Matrix ALU
 │
 ├──► MA
 └──► DA
```

Böylece aynı işlemci içerisinde:

```text
RA → scalar arithmetic
DA → data processing
MA → vector/matrix arithmetic
```

ayrı kaynaklardan yürütülebilir.

---

# 9. Instruction Decoder

Instruction decoder mimarinin merkezi kontrol noktasıdır.

Instruction CODE memory'den getirildikten sonra decoder:

1. Opcode'u çözer.
2. İşlem tipini belirler.
3. Kaynak registerları seçer.
4. Hedef registerı seçer.
5. İşlem genişliğini belirler.
6. İlgili execution unit'e komut gönderir.

Örneğin:

```text
ADD RA03, RA07, RA12
```

decoder:

```text
Opcode      = ADD
Source 1    = RA03
Source 2    = RA07
Destination = RA12
Mode        = scalar
```

olarak çözer.

Başka bir instruction:

```text
MADD.32 MA04, MA08, MA12
```

şeklinde olabilir.

Decoder:

```text
Opcode      = MADD
Source 1    = MA04
Source 2    = MA08
Destination = MA12
Element     = 32-bit
Unit        = Matrix/Vector ALU
```

olarak çözer.

---

# 10. İç Register Adresleme ve RAM Adresleme Ayrımı

Bu mimaride kritik bir tasarım prensibi vardır:

**CPU içindeki register seçimi ile dış bellek adreslemesi aynı şey değildir.**

RA register bankı için:

$$\[
64=2^6
\]$$

dolayısıyla register seçimi için:

\[
6\text{ bit}
\]

yeterlidir.

DA için de:

$$\[
6\text{ bit}
\]$$

gerekir.

MA için:

$$\[
32=2^5
\]$$

olduğundan:

$$\[
5\text{ bit}
\]
$$
yeterlidir.

Buna karşılık external memory adresleme 64-bit olabilir.

```text
CPU INTERNAL
─────────────
RA selector → 6 bit
DA selector → 6 bit
MA selector → 5 bit

EXTERNAL MEMORY
───────────────
RAM Address → 64 bit
```

Bu nedenle işlemci instructionlarının register seçim alanlarının tamamının 64-bit olması gerekmez.

Bu yaklaşım instruction encoding açısından önemli bir alan tasarrufu sağlayabilir.

---

# 11. Klasik Stack Belleğinin Kaldırılması

Bu mimaride klasik RAM tabanlı stack yapısının zorunlu olması hedeflenmemektedir.

Geleneksel sistemlerde:

```text
CALL
 ↓
STACK
 ↓
Push parameters
Push registers
Push return state
```

gibi işlemler yapılabilir.

Yeni mimaride ise application state'in önemli bölümü RA register bankında tutulabilir.

Örneğin:

```text
RA00–RA15 → parameters
RA16–RA31 → local state
RA32–RA47 → temporaries
RA48–RA55 → pointers
RA56–RA63 → return / control state
```

Bu yalnızca örnek bir register allocation modelidir; registerların sabit görevlerle sınırlandırılması zorunlu değildir.

Ama temel prensip şudur:

> Fonksiyon çağrısı için her geçici değerin RAM üzerindeki stack'e taşınması zorunlu olmamalıdır.

Bu yaklaşım stack erişiminin neden olduğu memory traffic'i azaltabilir.

Daha ileri bir uygulamada recursion, interrupt ve context switching için fiziksel register banklarının donanımsal context yönetimi veya register window mekanizması kullanılabilir.

---

# 12. Paralel Çalışma Prensibi

Mimarinin temel avantajlarından biri farklı kaynakların aynı zaman diliminde kullanılabilmesidir.

Örneğin:

```text
             CODE MEMORY
                  │
                  ▼
           Instruction Fetch
                  │
                  ▼
           Instruction Decode
             │          │
             │          │
             ▼          ▼
          RA / ALU     MA / ALU
             │          │
             │          │
             ▼          ▼
            DA       Matrix Data
             │
             ▼
          DATA RAM
```

Bir instruction fetch işlemi sürerken DATA RAM'den veri transferi yapılabilir.

Aynı zamanda MA bir vector/matrix işlemi gerçekleştirebilir.

Dolayısıyla ideal durumda:

$$\[
Instruction\ Fetch
\parallel
Data\ Access
\parallel
Vector\ Computation
\]$$

şeklinde bir çalışma mümkün olabilir.

Elbette gerçek paralellik execution unit sayısı, pipeline tasarımı, memory bandwidth ve dependency yönetimine bağlı olacaktır.

---

# 13. Örnek İşlem Akışı

Bir programın aşağıdaki işlemleri yaptığını düşünelim:

```text
1. CODE'dan instruction getir
2. DATA RAM'den veri oku
3. Scalar hesaplama yap
4. Verileri MA registerlarına aktar
5. Matrix işlemi gerçekleştir
6. Sonucu DATA RAM'e yaz
```

Mimaride:

```text
CODE
 │
 ▼
FETCH
 │
 ▼
DECODE
 │
 ├──────────────► RA
 │                 │
 │                 ▼
 │              Scalar ALU
 │
 └──────────────► DA ◄──────── DATA RAM
                   │
                   ▼
                 MA
                   │
                   ▼
             Matrix ALU
                   │
                   ▼
                  DA
                   │
                   ▼
                DATA RAM
```

Burada CODE memory instruction üretirken DATA memory ayrı bir veri yolu üzerinden çalışabilir.

---

# 14. Örnek Instruction Set

Mimari için örnek bir instruction biçimi:

```text
ADD RA03, RA07, RA12
SUB RA04, RA08, RA10
MUL RA02, RA05, RA09

LOAD RA05, DA12
STORE DA12, RA05

MADD.8  MA04, MA08, MA12
MADD.16 MA04, MA08, MA12
MADD.32 MA04, MA08, MA12
MADD.64 MA04, MA08, MA12

MOV MA04, DA12
MOV DA12, MA04
```

Bunlar nihai ISA değildir; mimarinin register mantığını göstermek için örneklerdir.

---

# 15. Fiziksel Register Organizasyonu

CPU'nun temel register alanı:

```text
┌──────────────────────────────────────────┐
│              REGISTER FILE               │
├──────────────────────────────────────────┤
│                                          │
│  RA BANK                                 │
│  64 × 64 bit                             │
│                                          │
├──────────────────────────────────────────┤
│                                          │
│  DA BANK                                 │
│  64 × 64 bit                             │
│                                          │
├──────────────────────────────────────────┤
│                                          │
│  MA BANK                                 │
│  32 × 256 bit                            │
│  Variable element width                  │
│                                          │
└──────────────────────────────────────────┘
```

Toplam fiziksel register kapasitesi:

RA:

$$\[
64\times64=4096\text{ bit}
\]$$

DA:

\[
64\times64=4096\text{ bit}
\]

MA:

$$\[
32\times256=8192\text{ bit}
\]$$

Toplam:

$$\[
4096+4096+8192=16384\text{ bit}
\]$$

yani:

$$\[
\boxed{2048\text{ byte}=2\text{ KiB}}
\]$$

register storage bulunur.

Bu değer yalnızca register file kapasitesidir; cache, local buffer, pipeline registerları ve diğer mikro-mimari depolama alanları buna dahil değildir.

---

# 16. Cache ve Yerel Bellek Konusu

Bu mimaride stack'in kaldırılması, bütün küçük ve geçici verilerin mutlaka RA/DA/MA içinde tutulması gerektiği anlamına gelmez.

Büyük veri kümeleri DATA memory'de bulunabilir.

CPU ile DATA memory arasındaki hız farkını azaltmak için ilerleyen tasarım aşamasında:

```text
CPU
 │
 ├── Register File
 │
 ├── Local Buffer
 │
 ├── L1/L2 benzeri cache
 │
 └── DATA Memory
```

şeklinde bir hiyerarşi eklenebilir.

Ancak bu cache sistemi stack'in yerine geçmek zorunda değildir.

Stack mantığı ile cache mantığı farklı problemlerdir.

---

# 17. CODE Memory ile DATA Memory'nin Fiziksel Ayrılması

Bu mimarinin daha ileri bir donanım uygulamasında CODE ve DATA memory farklı fiziksel bellek teknolojileriyle üretilebilir.

Örneğin:

```text
CODE
└── yüksek yoğunluklu / read optimized memory

DATA
└── yüksek yazma performanslı / expandable memory
```

Böyle bir ayrım gelecekte farklı bellek teknolojilerinin aynı CPU mimarisinde kullanılmasına olanak sağlayabilir.

Özellikle yeni nesil transistor tabanlı bellek teknolojileri açısından CODE ve DATA taraflarının aynı fiziksel hücre yapısını kullanması zorunlu değildir.

---

# 18. MOSRAM ile Olası Entegrasyon

Geliştirilmekte olan MOSRAM benzeri transistor-gate tabanlı bir bellek teknolojisi ileride bu mimariyle birlikte değerlendirilebilir.

Örneğin teorik olarak:

```text
CPU
 │
 ├────────────── CODE MEMORY
 │
 │                 MOSRAM / başka teknoloji
 │
 └────────────── DATA MEMORY
                   │
                   └── MOSRAM / başka teknoloji
```

Ancak bu aşamada MOSRAM'ın CPU mimarisinin zorunlu bir parçası olduğu kabul edilmemelidir.

CPU mimarisi bellek teknolojisinden bağımsız olarak tanımlanabilir.

Bu ayrım önemlidir:

$$\[
\text{ISA/Mimari} \neq \text{Bellek Hücresi Teknolojisi}
\]$$

Bellek teknolojisi değişebilirken register mimarisi ve instruction set korunabilir.

---

# 19. Mimarinin Temel Tasarım İlkeleri

Bu CPU'nun temel prensipleri şu şekilde özetlenebilir:

### 1. Kod ve veri ayrımı

```text
CODE ≠ DATA
```

Instruction fetch ve data access farklı yollar üzerinden yürütülür.

### 2. Register görev ayrımı

```text
RA → Application / Scalar
DA → Data
MA → Vector / Matrix
```

### 3. Doğrudan register seçimi

```text
RA03
RA07
RA12
```

CPU tarafından doğrudan fiziksel register seçimi olarak yorumlanır.

### 4. Değişken işlem genişliği

MA:

```text
8 → 16 → 32 → 64 → 128 → 256 bit
```

işlem modlarına sahip olabilir.

### 5. Harici bellek için geniş adresleme

External memory:

$$\[
64\text{-bit addressing}
\]$$

kullanabilir.

### 6. Klasik stack zorunlu değildir

Application state register banklarında tutulabilir.

### 7. Paralel işlem yolları

```text
Instruction Fetch
        ∥
Data Access
        ∥
Vector / Matrix Processing
```

aynı anda yürütülebilecek şekilde tasarlanır.

---

# 20. Mimari Blok Diyagram

Genel sistem şu şekilde özetlenebilir:

```text
                         ┌───────────────────────┐
                         │      CODE MEMORY      │
                         │       4–8 GB          │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │  INSTRUCTION FETCH    │
                         └───────────┬───────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │      INSTRUCTION DECODER       │
                    │       + CONTROL UNIT           │
                    └───────┬────────┬────────┬──────┘
                            │        │        │
                            ▼        ▼        ▼
                       ┌────────┐ ┌────────┐ ┌────────────┐
                       │RA00-63 │ │DA00-63 │ │ MA00-31    │
                       │64×64b  │ │64×64b  │ │32×256b     │
                       └────┬───┘ └────┬───┘ └─────┬──────┘
                            │           │            │
                            ▼           │            ▼
                       ┌────────┐       │      ┌────────────┐
                       │Scalar  │       │      │Vector /    │
                       │ALU     │       │      │Matrix ALU  │
                       └────┬───┘       │      └─────┬──────┘
                            │           │            │
                            └───────────┼────────────┘
                                        │
                                        ▼
                                  ┌───────────┐
                                  │ DA / DATA │
                                  │ INTERFACE │
                                  └─────┬─────┘
                                        │
                                        ▼
                         ┌─────────────────────────┐
                         │       DATA MEMORY       │
                         │ 8 GB → 16 → 32 → 64 → │
                         │       128+ GB          │
                         └─────────────────────────┘
```

---

# 21. Sonuç

Bu mimari, CPU içindeki kaynakları tek bir genel amaçlı register ve tek bir bellek yolu etrafında toplamak yerine görevlerine göre ayırmayı hedeflemektedir.

Temel yapı:

$$\[
\boxed{
CODE
+
RA
+
DA
+
MA
+
DATA
}
\]$$

şeklinde özetlenebilir.

RA application/scalar state'i, DA veri hareketini, MA ise yüksek genişlikli vector/matrix işlemlerini üstlenir.

Fiziksel register genişliği ile işlem genişliği birbirinden ayrılır. Özellikle MA registerlarının 256-bit fiziksel genişliğe sahip olup 8-bit'ten 256-bit'e kadar farklı element genişliklerinde kullanılabilmesi, aynı register mimarisinin hem küçük integer işlemlerinde hem de geniş vector/matrix işlemlerinde kullanılmasını sağlar.

Bunun yanında CODE memory ile DATA memory'nin ayrılması, instruction fetch ile data access işlemlerinin birbirinden bağımsız ilerleyebilmesine olanak sağlayan temel mimari prensiptir.

CPU içindeki register seçimleri küçük selector alanlarıyla gerçekleştirilirken external memory için 64-bit adresleme kullanılabilir. Böylece CPU'nun her iç adresinin 64-bit olması gerekmez.

Mimarinin nihai amacı yalnızca daha fazla register eklemek değildir. Asıl amaç:

$$\[
\boxed{
\text{Kod}
\rightarrow
\text{Kontrol}
\rightarrow
\text{Scalar}
\rightarrow
\text{Data}
\rightarrow
\text{Vector/Matrix}
}
\]$$

işlem yollarını birbirinden mümkün olduğunca ayırarak **daha düşük memory traffic, daha az gereksiz veri kopyalama ve daha yüksek doğal paralellik** elde etmektir.

Bu nedenle mimari klasik stack-merkezli ve tek tip register yaklaşımından farklı olarak, **ayrıştırılmış register bankları + ayrıştırılmış bellek + paralel execution path** prensibine dayanmaktadır.
----

---

# 22. Çoklu Execution Unit Yapısı

CPU çekirdeği tek bir ALU ve tek bir scalar işlem yoluna bağlı kalmaz. Her çekirdekte birbirinden bağımsız yürütme birimleri bulunur.

## 22.1 ALU kümesi

Her çekirdeğin temel yapılandırması **2 ALU** olacak; tasarım/ürün varyantında **3 ALU** seçeneği desteklenecektir.

- ALU0 ve ALU1: temel paralel integer/mantıksal yürütme.
- ALU2: 3-ALU yapılandırmasında ek integer yürütme kapasitesi.
- ALU'lar mümkün olduğunca bağımsız komutları aynı anda işleyebilir.
- Operand bağımlılığı, register portları veya kaynak çakışması paralelliği sınırlayabilir.
- ALU sayısı komut sayısının otomatik olarak aynı oranda hızlanacağı anlamına gelmez.

ALU işlem kapsamı: toplama/çıkarma, çarpma-bölme (uygulama seçimine göre ayrı çok çevrimli birim olabilir), karşılaştırma, mantıksal işlemler, bit işlemleri, shift/rotate ve adres hesaplamaları.

## 22.2 FPU kümesi

Her çekirdekte **en az 2 bağımsız FPU** bulunacaktır.

- FPU0 ve FPU1, floating-point komutlarını ayrı yürütme kaynakları olarak kabul edilir.
- FP32 ve FP64 temel işlem biçimleridir.
- FP128 desteği ISA/type sisteminde tanımlanabilir; fiziksel throughput ve latency ayrıca mikro-mimari kararla belirlenir.
- FPU sayısı, aynı çekirdekte bağımsız FP komutlarının eşzamanlı yürütülmesini hedefler.
- FPU'lar ALU'ların yerine geçmez; integer ve floating-point yürütme yolları ayrıdır.

## 22.3 512-bit Matrix Engine

Her çekirdeğe **1 adet 512-bit Matrix Engine (ME)** eklenir.

- ME, scalar ALU ve FPU'lardan ayrı yürütme birimidir.
- 512-bit, motorun veri/işlem yolu genişliğini belirtir.
- MA register bankı 256-bit fiziksel registerlardan oluştuğu için 512-bit operand/sonuç, iki MA registerı veya tanımlı birleşik operand biçimiyle taşınabilir.
- 512-bit motorun tek komutta 512-bit veri alması, iki 256-bit registerın eşleştirilmesi veya özel operand formatıyla sağlanabilir; encoding/port tasarımı ISA aşamasında netleştirilecektir.
- Element genişliği ve matris şekli opcode/format tarafından belirlenir; 512-bit yol tek başına sabit 512×512 matris anlamına gelmez.
- Matrix multiply, multiply-accumulate ve uygun vector/matrix işlemleri bu birimin hedef kapsamıdır.

## 22.4 Çekirdek başına başlangıç kaynak tablosu

| Execution Unit | Çekirdek başına | Durum |
|---|---:|---|
| Integer / Logic ALU | 2 | Temel |
| Integer / Logic ALU | 3. ALU | Opsiyonel genişletme |
| FPU | 2 veya daha fazla | Minimum 2 |
| Matrix Engine | 1 × 512-bit | Temel hedef |

## 22.5 Register ve SPM bağlantısı

- RA/RB/RC/RD görünümleri scalar ALU'ların operand ve sonuç alanıdır.
- DA bankı data transfer ve staging görevini sürdürür.
- MA bankı vector/matrix operand ve sonuçlarını taşır.
- SPM0/SPM1, register pressure ve ara değerler için doğrudan adreslenebilir çalışma alanıdır.
- SPM erişimi execution unit'lere ortak bir kaynak olarak sunulur; aynı çevrimdeki erişim sayısı port/bank tasarımıyla belirlenecektir.

## 22.6 Paralel yürütme ilkesi

Bağımsız komutlar, kaynaklar uygun olduğunda aşağıdaki birimlerde eşzamanlı ilerleyebilir:

```text
Core
 ├─ ALU0 ─┐
 ├─ ALU1 ──┼─ Integer / Logic
 ├─ ALU2* ─┘
 ├─ FPU0 ──┐
 ├─ FPU1 ──┴─ Floating Point
 └─ ME512 ──── Matrix / Vector
```

`ALU2*` yalnızca 3-ALU yapılandırmasında bulunur. Gerçek issue width, register portları, forwarding, dependency çözümü ve execution latency sonraki mikro-mimari belgesinde tanımlanacaktır.

## 22.7 Instruction Set belgesi

Komut aileleri ve ilk operand tablosu için:
**[NEXSUS CPU Instruction Set — Execution Unit Table](NEXSUS-CPU-ISA-001.md)**

SPM adresleme, kısmi yazma ve register görünüm ayrıntıları:
**[NEXSUS CPU — SPM ve Register Görünümleri](NEXSUS%20CPU%20%E2%80%94%20SPM,%20Register%20G%C3%B6r%C3%BCn%C3%BCmleri%20ve%20Do%C4%9Frudan%20Alan%20Eri%C5%9Fimi.md)**


---

# 23. İlk Paralel Issue ve Port Planı

ISA-001 belgesinde ilk kaynak/port hedefleri ve ME512 register pair eşlemesi tanımlanmıştır. Bu bölüm mimari özeti verir.

- 2-ALU çekirdek: temel integer issue hedefi 2 bağımsız komut/çevrim.
- 3-ALU konfigürasyonu: 3 bağımsız integer komut/çevrim hedefi.
- FPU: en az 2 bağımsız FP komut kaynağı.
- ME512: bir matrix/vector komut kaynağı; pipeline throughput ve latency ayrı belirlenir.
- Integer + FP + matrix komutları operand bağımsızlığı ve kaynak uygunluğu varsa aynı çevrimde birlikte issue edilebilir.
- MA00:MA01, MA02:MA03, ... MA30:MA31 biçiminde 16 adet 512-bit pair tanımlanır.
- Pair komutu ilgili iki MA registerını operand/result süresince rezerve eder.
- Register view alias ve write hazard kuralları scheduler/forwarding tarafından korunur.
- Register portları, bank çatışmaları ve data-path arbitration kesin throughput'u sınırlar.

Detaylı tablo: [NEXSUS-CPU-ISA-001.md](NEXSUS-CPU-ISA-001.md)


# 24. Register Alias ve Operand Scheduling İlkeleri

RA/RB/RC/RD aynı 64-bit fiziksel register hücresinin genişlik görünümleridir. RB/RC/RD yazmaları yalnızca düşük bit alanını değiştirir; üst bitler korunur. Böylece scalar register alanı büyümeden 8/16/32/64-bit erişim sağlanır.

- RA write 64-bit tam güncelleme yapar.
- RB write [31:0], RC write [15:0], RD write [7:0] alanlarını günceller.
- View alias'ları ayrı register gibi değil, aynı fiziksel RA index'i üzerinden dependency/hazard takibine girer.
- Aynı RA hücresine aynı cycle'da iki yazma issue edilmez.
- Forwarding, partial-write mask merge sonrasındaki güncel register değerini sağlamalıdır.

Scalar issue planında her register kaynak operandı RA read slotu tüketir; immediate operand port tüketmez. Aynı RA değerinin tekrar kullanılması broadcast/reuse ile optimize edilebilir, ancak bu ilk sürümde throughput garantisi değildir. ALU ve FPU'ların bağımsız execution unit olması, tüm birimlerin her cycle tam dolacağı anlamına gelmez: issue scheduler register portu, operand dependency, destination conflict ve bypass uygunluğunu birlikte değerlendirir.

**İlk hedef:** 6 RA read / 3 RA write slotu. Bu değer sabit maksimum issue genişliği değil, başlangıç register-file tasarım hedefidir. Port çoğaltma, bank replication veya operand queue ileride mikro-mimari optimizasyon olarak ele alınabilir.

ISA davranışının ayrıntısı: [NEXSUS-CPU-ISA-001.md — §19–20](NEXSUS-CPU-ISA-001.md).

## 24.1 ME512 accumulator ve tile ayrımı

ME512'nin dış operand yolu 512-bit'tir; bu değer iç matrix accumulator genişliğini veya matris boyutunu belirlemez. MA pair'leri operand/result transfer biçimidir. Matrix shape, element packing, tile boyutu, accumulation precision ve iç accumulator kapasitesi ayrı mikro-mimari parametreler olarak kalır. Bu kararlar benchmark/iş yükü ve alan-güç hedefleriyle birlikte verilecektir; ISA'da şimdilik tek bir accumulator genişliği sabitlenmez.


# 25. `area` / `zone` bellek yerleşim modeli

Bu bölüm CPU'nun genel RAM ve cache/shared-memory organizasyonunu tanımlar; belirli bir fiziksel RAM teknolojisini varsaymaz.

- **`area` → L1 / core-local:** Çekirdeğe ait yerel çalışma alanı. Sık erişilen, kısa ömürlü veya çekirdek içinde yoğun kullanılan veriler için ayrılır. Başka çekirdeklerin bu alanı ortak bellek gibi kullanması hedeflenmez.
- **`zone` → L2/L3/L4 / shared memory:** Birden fazla çekirdeğin erişebildiği ortak bellek alanı. Çekirdekler payload'ı birbirine kopyalamak yerine zone içindeki adresi veya handle'ı paylaşır.
- Üretici veriyi zone'a bir kez yazar ve publish eder. Tüketici aynı adresi acquire ederek okur. Böylece çekirdekler arasında tekrarlanan payload kopyaları ortadan kalkar; adres/descriptor aktarımı yeterli olur.
- Zone descriptor en azından base address, length, alignment, target level ve access/ownership metadata'sını temsil etmelidir. Descriptor küçük bir kontrol verisidir; asıl payload ortak RAM bölgesinde kalır.
- Zone tahsisi ve serbest bırakılması lifetime ile yönetilir. Tüketici kullanımını bitirmeden üretici aynı alanı yeniden kullanamaz.
- Publish/acquire işlemleri memory ordering ve cache visibility kurallarına uymalıdır. Adresin paylaşılması tek başına cache coherence veya yazma görünürlüğü sağlamaz.
- Aynı zone aralığına çoklu yazma için açık ownership, atomik işlem veya senkronizasyon gerekir.

Bu yaklaşım **address handoff / zero-copy inter-core sharing** modelidir. Verinin ilk kez ortak RAM'e yazılması devam eder; kaldırılan işlem, çekirdekler arasında aynı payload'ın tekrar tekrar kopyalanmasıdır.

İlgili ISA komut taslağı ve kurallar: [NEXSUS-CPU-ISA-001.md — §22.6–22.8](NEXSUS-CPU-ISA-001.md).


## 26. Çekirdek sayısına göre L1–L4 bellek paylaşım topolojisi

Bellek paylaşım kapsamı çekirdek gruplarına göre kademelendirilir:

| Seviye | Paylaşım kapsamı | Tanım |
|---|---:|---|
| L1 | 1 çekirdek | Her çekirdeğin kendine ait özel yerel alanı; Nexus Flow `area` hedefi |
| L2 | 2 çekirdek | Her iki çekirdeğin ortak eriştiği bellek alanı; `zone` hedefi |
| L3 | 4 çekirdek | Her dört çekirdeğin ortak eriştiği bellek alanı; `zone` hedefi |
| L4 | 8 ve üzeri çekirdek | Daha geniş çekirdek grubunun / sistemin ortak bellek alanı; `zone` hedefi |

- L2, L3 ve L4'ün paylaşım grupları iç içe kademelenebilir: çekirdek çiftleri L2, dört çekirdekli kümeler L3, sekiz ve üzeri kapsam ise L4 domain'i oluşturur.
- Örneğin 8 çekirdekte 8 özel L1, 4 adet iki çekirdekli L2 grubu, 2 adet dört çekirdekli L3 grubu ve 8 çekirdeğin eriştiği bir L4 domain'i bulunabilir.
- Bu sayılar paylaşım kapsamını belirtir; bellek kapasitesi, bant genişliği, gecikme ve fiziksel bank sayısı henüz sabitlenmemiştir.
- `area` yalnızca çekirdeğin kendi L1 alanına tahsis yapar. `zone` ise seçilen L2/L3/L4 paylaşım domain'inde ortak alan ayırır.
- Zone içindeki veri bir kez yazılır; diğer çekirdekler aynı adres/handle üzerinden erişir. Böylece çekirdekler arasında payload kopyalama yerine adres/descriptor paylaşımı yapılır.
- Bir handle yalnızca ilgili zone domain'ine erişim yetkisi olan çekirdeklerde geçerlidir. Publish/acquire, ownership, lifetime ve cache visibility/synchronization kuralları korunur.
- Daha geniş paylaşım kapsamı gerektiğinde veri uygun üst seviyedeki zone'a tahsis edilir veya kontrollü biçimde taşınır; yalnızca handle göndermek veriyi başka seviyeye taşımaz.
- L2/L3/L4'ün fiziksel olarak cache, dağıtık RAM bankları veya fabric üzerinden erişilen bellek dilimleriyle gerçekleştirilmesi uygulama kararıdır; mimari sözleşme paylaşım kapsamını tanımlar.

Bu topoloji CPU bellek mimarisinin paylaşım modelidir; belirli bir RAM hücre teknolojisini varsaymaz. Kesin kapasite ve timing değerleri çekirdek sayısı, fabric bant genişliği ve ürün hedefleri belirlendikten sonra eklenecektir.

ISA ayrıntısı: [NEXSUS-CPU-ISA-001.md — §22.9](NEXSUS-CPU-ISA-001.md).


## 27. L1–L4 bellek kapasitesi ve açık aktarım modeli

L1/L2/L3/L4 ayrı bellek domain'leridir. Birbirlerine otomatik bağlı bir cache zinciri oluşturmazlar; verinin bir seviyeden diğerine kendiliğinden taşınması veya otomatik kopyalanması beklenmez.

### 27.1 İlk kapasite hedefleri

| Seviye | Paylaşım kapsamı | Domain başına hedef kapasite |
|---|---:|---:|
| L1 | 1 çekirdek | 128 KiB |
| L2 | 2 çekirdek | 1 MiB |
| L3 | 4 çekirdek | 8 MiB |
| L4 | 8 çekirdek | 64 MiB |

Kapasite her üst seviyede domain başına 8 kat büyür. Bu değerler başlangıç tasarım hedefidir; gecikme, bant genişliği, port sayısı ve fiziksel bellek yerleşimi ölçümlerden sonra kesinleştirilecektir. 8'den fazla çekirdekli sistemlerde L4, sekizli gruplar veya daha geniş bir sistem domain'i olarak ölçeklenebilir.

### 27.2 Bellek domain'lerinin ayrılığı

- Her çekirdeğin L1'i özeldir.
- L2 iki çekirdeğin, L3 dört çekirdeğin, L4 ise sekiz ve üzeri çekirdeğin erişebildiği paylaşımlı domain'dir.
- L1–L4 arasında otomatik aktarım/terfi/düşürme yapılmaz.
- Bir domain'de bulunan veri başka seviyede otomatik olarak görünür hale gelmez.
- Aynı zone adresinin paylaşılması, o zone'un erişim kapsamındaki çekirdekler arasında payload kopyalamadan iletişim sağlar. Farklı seviyeye geçiş ise ayrı bir veri taşıma işlemidir.

### 27.3 CPU kontrollü seviye aktarımı

Bir verinin başka bir Lx domain'ine alınması gerektiğinde CPU talimatı ile açık aktarım yapılır. Kaynak seviye/adres, hedef seviye/adres ve uzunluk komutta belirtilir. CPU aktarımı yürütür ve tamamlanma/hata durumunu denetler. Donanımın Lx seviyeleri arasında kendiliğinden kopyalama yaptığı varsayılmaz.

ISA için ilk komut taslağı:

```asm
XFER L3:destination, L1:source, 4096
```

Bu örnek 4096 byte veriyi L1'den L3'e CPU kontrolünde taşır. Büyük transferler çok çevrimli olabilir. İleride asenkron başlatma ve bekleme/token biçimi eklenebilir; ancak aktarımın açıkça CPU tarafından istenmesi temel kuraldır.

Ayrıntılı ISA semantiği: [NEXSUS-CPU-ISA-001.md — §22.10–22.11](NEXSUS-CPU-ISA-001.md).


## 28. P0 program komut belleği ve kod/veri ayrımı

NEXSUS CPU'da program komutları ile uygulama verileri farklı bellek domain'lerinde tutulur. Bu amaçla P0, komut belleği olarak L1–L4 veri belleklerinden ayrı tanımlanır.

| Bellek | Görev | Erişim modeli |
|---|---|---|
| P0 | Program komutları ve yürütülebilir kod | Instruction fetch |
| L1 | Çekirdeğe özel veri belleği | Yerel veri LOAD/STORE |
| L2 | İki çekirdek için paylaşılan veri belleği | Paylaşılan veri erişimi |
| L3 | Dört çekirdek için paylaşılan veri belleği | Paylaşılan veri erişimi |
| L4 | Sekiz veya daha geniş çekirdek grubu için veri belleği | Geniş paylaşımlı veri erişimi |

### 28.1 P0'ın mimari kuralları

- P0 yalnızca program komutlarını/kodunu barındıran program belleği domain'idir.
- Instruction fetch yolu P0'a yönelir; normal uygulama verisi L1–L4 domain'lerinde tutulur.
- P0, L1'in parçası veya L1–L4 cache hiyerarşisinin bir seviyesi değildir.
- P0 ile L1–L4 arasında otomatik veri/kod kopyalama veya migration yapılmaz.
- Program yükleme ve kod güncelleme işlemleri CPU tarafından açıkça kontrol edilir.
- P0'a yazma, kod yürütme izni ve değiştirilmiş komutların fetch birimine görünür olması ayrı koruma ve senkronizasyon kuralları gerektirir.

### 28.2 Kod/veri ayrımının sonucu

Bu modelde uygulama kodu ve uygulama verisi ayrı bellek alanlarında yaşar. Böylece veri belleğinin kapasitesi program koduyla tüketilmez; komut fetch ve veri erişimi de farklı bellek yolları/domain'leri üzerinden tasarlanabilir. P0 kapasitesi, gecikmesi, bant genişliği ve bank sayısı henüz belirlenmemiştir; bunlar sonraki bellek bant genişliği ve çekirdek ölçekleme çalışmasında netleştirilecektir.

### 28.3 Domain'ler arası aktarım

P0 dahil farklı bellek domain'leri arasında veri veya kod taşınması gerektiğinde aktarım CPU tarafından açıkça başlatılır. `XFER` çok çevrimli ve parçalara bölünmüş çalışır. Aktarım sürerken bağımsız ALU/FPU/ME işleri, bellek ve yürütme kaynakları çakışmadığı sürece ilerleyebilir. Asenkron kullanımda `XFER.START` token üretir ve `XFER.WAIT token` tamamlanmayı bekler.

ISA komut semantiği: [NEXSUS-CPU-ISA-001.md — §22.11–22.12](NEXSUS-CPU-ISA-001.md).
