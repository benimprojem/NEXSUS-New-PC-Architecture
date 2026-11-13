# NEXSUS CPU — Instruction Encoding Specification

**Belge:** NEXSUS-CPU-INSTRUCTION-ENCODING-001  
**Durum:** Tasarım taslağı — 64-bit temel komut sözcüğü ve alan yerleşimi  
**Bağlı belgeler:**
- `NEXSUS-CPU-ISA-001.md` — mnemonic, operand ve execution-unit tanımları
- `Yeni Nesil Ayrıştırılmış Register Tabanlı CPU Mimarisi.md` — CPU ve bellek mimarisi
- `NEXSUS CPU — SPM, Register Görünümleri ve Doğrudan Alan Erişimi.md` — register/SPM ayrıntıları

> Bu belge, ISA mnemonic'lerini makine koduna dönüştürmek için ilk encoding modelini tanımlar. Alan genişlikleri ve format yapısı önerilen temel tasarımdır. Sayısal opcode atamaları, kesin endian/byte sıralaması ve bazı özel formatlar henüz dondurulmamıştır.

---

## 1. Tasarım hedefleri

1. Her temel instruction word tam **64 bit** olmalıdır.
2. P0 komut ön belleği 64-bit kayıtlar tuttuğundan komut sözcüğü P0 kayıt genişliğiyle birebir eşleşmelidir.
3. RA, FA, DA ve MA banklarının her birinde 32 kayıt bulunduğu için register seçimi **5 bit** olmalıdır.
4. Register bankları bağımsızdır; komut ailesi varsayılan operand bankını belirler.
5. Immediate, displacement ve register-transfer işlemleri tek bir ortak formata zorlanmamalıdır.
6. 64-bit adres alanı korunmalıdır. Büyük immediate/adres sabitleri gerektiğinde ek 64-bit literal word kullanılabilmelidir.
7. Decoder, komutun uzunluğunu ve formatını ilk 64-bit word üzerinden anlayabilmelidir.

## 2. Temel instruction word

Bütün temel komutlar 64-bit word olarak kodlanır. İlk taslakta üst bitler opcode ve formatı, kalan bitler operandları ve komuta özgü alanları taşır.

| Bit aralığı | Alan | Genişlik | Görev |
|---|---|---:|---|
| [63:56] | OP | 8 | Primary opcode |
| [55:52] | FMT | 4 | Instruction format |
| [51:0] | Payload | 52 | Formata göre register, width, mode, immediate veya displacement |

**OP + FMT**, decoder'ın komut ailesini ve payload yorumunu belirler. Aynı payload bitleri farklı formatlarda farklı anlamlara gelebilir.

### 2.1 Register selector

Her bank 32 kayıt içerir. Dolayısıyla her register operandı 5-bit selector ile kodlanır:

| Bank | Kod (taslak) | Selector |
|---|---:|---:|
| RA | 00 | 5 bit |
| FA | 01 | 5 bit |
| DA | 10 | 5 bit |
| MA | 11 | 5 bit |

Bu iki-bit bank kodları yalnızca bank alanı bulunan genel register-transfer formatlarında kullanılır. Normal ALU/FP/vector komutlarında bank, opcode ailesinden örtük olarak belirlenir; her operand için fazladan bank biti harcanmaz.

RA alt görünümleri:
- RA: 64-bit
- RB: RA'nın [31:0] görünümü
- RC: RA'nın [15:0] görünümü
- RD: RA'nın [7:0] görünümü

RB/RC/RD ayrı fiziksel bank veya ayrı selector alanı değildir. Komutun width/view alt alanı ve integer opcode semantiği ile seçilir.

## 3. Format kodları

FMT alanı için ilk öneri:

| FMT | Ad | Kullanım |
|---:|---|---|
| 0000 | R3 | Üç register operandlı ALU/FP/vector işlemleri |
| 0001 | R2 | İki register operandlı işlemler, unary ve compare |
| 0010 | RI | Register + immediate |
| 0011 | MEM | Load/store ve base + displacement adresleme |
| 0100 | XFER | Register bankları arasında açık transfer |
| 0101 | BR | Conditional/unconditional PC-relative branch |
| 0110 | SYS | System, control ve özel register komutları |
| 0111 | EXT | Takip eden 64-bit literal/extension word kullanan komut |
| 1000 | R4 | Dört register operandlı işlemler (FMA, VMACC, MADD vb.) |
| 1001–1111 | Reserved | Gelecek formatlar |

FMT kodları taslak değerlerdir; opcode tablosu dondurulurken sabitlenecektir.

## 4. Operand formatlarının bit yerleşimi

### 4.1 R3 — Üç register operandı

```text
63       56 55    52 51   47 46   42 41   37 36  34 33 32 31             0
+----------+--------+-------+-------+-------+------+-----+----------------+
| OP (8)   |FMT (4) | D (5) | A (5) | B (5) | W (3)| M(2)| AUX (32)       |
+----------+--------+-------+-------+-------+------+-----+----------------+
```

- D: hedef register selector
- A/B: kaynak register selector
- W: işlem genişliği veya element formatı
- M: komuta özgü kısa mod alanı
- AUX: komuta özgü ek alan; kullanılmıyorsa sıfır yazılır

Örnekler: `ADD RA3, RA1, RA2`, `FADD FA4, FA1, FA2`, `VADD.W32 MA8, MA4, MA12`.

Opcode ailesi operand bankını belirler:
- Integer R3 → RA
- Floating-point R3 → FA
- Vector/matrix R3 → MA

### 4.2 R2 — İki register operandı

```text
63       56 55    52 51   47 46   42 41  39 38  36 35                 0
+----------+--------+-------+-------+------+-------+-------------------+
| OP (8)   |FMT (4) | D (5) | A (5) | W(3) | M (3) | AUX (36)          |
+----------+--------+-------+-------+------+-------+-------------------+
```

Unary, compare, move veya iki register kullanan komutlarda kullanılır. Komutun tanımına göre D hedef olabilir veya kullanılmayabilir. Kullanılmayan alanlar sıfır olmalıdır.

### 4.3 R4 — Dört register operandı

```text
63       56 55    52 51   47 46   42 41   37 36   32 31  29 28  26 25       0
+----------+--------+-------+-------+-------+-------+------+-----+----------+
| OP (8)   |FMT (4) | D (5) | A (5) | B (5) | C (5) | W(3) | M(3)| AUX (26) |
+----------+--------+-------+-------+-------+-------+------+-----+----------+
```

- D: hedef veya accumulator/result register selector
- A/B/C: üç kaynak register selector'ı
- W: işlem veya element genişliği
- M: komuta özgü mod alanı
- AUX: ek komuta özgü alan; kullanılmıyorsa sıfır olmalıdır
- Operand bankı, R3 formatındaki gibi opcode ailesinden belirlenir.
- FP komutlarında FA, vector/matrix komutlarında MA bankı kullanılır. 128-bit FA ve 512-bit MA pair kuralları geçerlidir.

R4 örnekleri:
- `FMA FA4, FA1, FA2, FA3`
- `VMACC.W32 MA8, MA4, MA12, MA16`
- `MADD MA0:MA1, MA2:MA3, MA4:MA5, MA6:MA7` (512-bit pair biçimi; operand şekli ISA tarafından belirlenir)

Bu format, dört ayrı register operandını tek 64-bit instruction word içinde kodlar; komutun çok çevrimli çalışması encoding uzunluğunu değiştirmez.

### 4.4 R2 bit-field işlemleri — BEXT / BINS

BEXT ve BINS iki register ile iki küçük alan parametresi kullandığından R2 formatını kullanır. D/A register selector alanları korunur; AUX bit konumu ve alan genişliğini taşır.

**AUX alanı**

| AUX bitleri | Alan | Genişlik |
|---|---|---:|
| [35:30] | START | 6 |
| [29:23] | FIELD_WIDTH | 7 |
| [22:0] | RESERVED | 23 |

- START, register'ın en düşük anlamlı bitinden itibaren sıfır tabanlı konumdur (0–63).
- FIELD_WIDTH, 1–64 arası bit sayısıdır; 0 geçersizdir.
- `START + FIELD_WIDTH`, seçilen W genişliğini aşamaz.
- W yalnızca 8/16/32/64 olabilir; 128/256/512 bu scalar komutlarda geçersizdir.
- M=000 olmalıdır; RESERVED alan sıfır olmalıdır.

**BEXT**
- `BEXT D, A, START, FIELD_WIDTH`
- A içindeki seçili alanı çıkarır ve D'nin düşük FIELD_WIDTH bitine yerleştirir.
- D'nin seçilen W genişliğindeki kalan üst bitleri sıfırlanır.
- BEXT zero-extend eder; signed sonuç gerekiyorsa ayrıca sign-extension uygulanır.

**BINS**
- `BINS D, A, START, FIELD_WIDTH`
- A'nın düşük FIELD_WIDTH bitini D içindeki START konumuna yerleştirir.
- D'nin seçilen alan dışındaki bitleri korunur.
- Kaynak ve hedef aynı register olabilir; sonuç eski kaynak/hedef değerlerinden hesaplanır.
- FIELD_WIDTH, A'nın seçilen W genişliğini aşamaz; hedef aralığı W sınırları içinde kalmalıdır.

### 4.5 RI — Register + immediate

```text
63       56 55    52 51   47 46   42 41  39 38  36 35                 0
+----------+--------+-------+-------+------+-------+-------------------+
| OP (8)   |FMT (4) | D (5) | A (5) | W(3) | M (3) | IMM (36)          |
+----------+--------+-------+-------+------+-------+-------------------+
```

- IMM, varsayılan olarak signed 36-bit iki'nin tümleyeni immediate değeridir.
- Opcode signed/unsigned yorumunu veya shift-count gibi özel kullanımı açıkça belirtir.
- Daha geniş sabitler EXT formatı ile taşınır.

### 4.6 MEM — Bellek erişimi

```text
63       56 55    52 51   47 46   42 41  39 38  36 35             4 3   0
+----------+--------+-------+-------+------+-------+---------------+-----+
| OP (8)   |FMT (4) | D (5) | BASE(5)| W(3)| AM(3)| DISP (32)     | R(4)|
+----------+--------+-------+-------+------+-------+---------------+-----+
```

- D: LOAD için hedef DA başlangıç selector'ı; STORE için kaynak DA başlangıç selector'ı.
- BASE: RA bankından 64-bit adres tabanı selector'ı.
- W: erişim genişliği (8/16/32/64/128/256/512 bit).
- AM[2:1]: veri bellek domain'i.
- AM[0]: adresleme biçimi; ilk sürümde yalnızca **0 = base + signed displacement** geçerlidir.
- DISP: signed 32-bit byte displacement.
- R: reserved; sıfır olmalıdır.

**AM alanı**

| AM[2:1] | Domain | Hedef |
|---:|---|---|
| 00 | L1 | Yalnızca geçerli çekirdeğin özel L1 domain'i |
| 01 | L2 | İlgili iki çekirdeklik grubun ortak domain'i |
| 10 | L3 | İlgili dört çekirdeklik grubun ortak domain'i |
| 11 | L4 | İlgili sekizli veya daha geniş grubun ortak domain'i |

İlk adresleme biçimi için AM[0]=0 olmalıdır. Böylece geçerli AM değerleri L1=000, L2=010, L3=100, L4=110 olur. AM[0]=1 olan biçimler şimdilik reserved'dır. Domain, komutun gerçek veri erişim hedefidir; örtük cache fill veya başka Lx seviyesine kopyalama anlamına gelmez.

Effective address:

`EA = RA[BASE] + sign_extend(DISP)`

64-bit adresin tamamı RA kaydında tutulur. Böylece 32-bit displacement, 64-bit adres alanını sınırlamaz.

**DA kayıtlarına erişim dağılımı**

DA kayıtları 64-bit olduğundan erişim genişliğine göre gereken kayıt sayısı şöyledir:

| W | DA kayıt sayısı | Kullanılan kayıtlar |
|---:|---:|---|
| 8 / 16 / 32 / 64 | 1 | DA[D] |
| 128 | 2 | DA[D]–DA[D+1] |
| 256 | 4 | DA[D]–DA[D+3] |
| 512 | 8 | DA[D]–DA[D+7] |

- D her zaman kullanılan DA aralığının ilk kaydını gösterir.
- D + kayıt sayısı 32'yi aşamaz. Örneğin 512-bit erişim için D en fazla 24 olabilir.
- MEM erişimlerinde 128/256/512-bit DA grupları için ek bir selector hizalama şartı ilk taslakta konulmaz; yalnızca DA31 sınırı kontrol edilir. Gerçek bellek hizalaması ayrı bir konudur.
- 8/16/32-bit LOAD, ilgili DA kaydının düşük bitlerine veriyi yazar ve aynı kaydın kullanılmayan üst bitlerini sıfırlar. 64-bit LOAD kaydın tamamını yazar.
- 128/256/512-bit erişimlerde ardışık 64-bit parçalar artan bellek adresi sırasıyla artan DA selector'larına eşlenir. Her kaydın kendi içindeki byte sıralaması global endian kararıyla belirlenecektir.
- STORE yalnızca istenen W bitini bellek alanına yazar; son DA kaydındaki erişim genişliği dışında kalan bitler yazılmaz.
- LOAD/STORE ham bit aktarımı yapar. LOAD signed/unsigned yorumlama veya sign-extension yapmaz. Signed/unsigned yorum, DA'dan RA/FA'ya sonraki açık dönüşüm/transfer aşamasında yapılır.
- **Doğal hizalama zorunludur.** EA, erişim boyutunun byte karşılığına (W/8) tam bölünmelidir. Örnek: W=16 için 2-byte, W=64 için 8-byte, W=512 için 64-byte hizalama gerekir. W=8 için her byte adresi geçerlidir.
- İlk ISA sürümünde misaligned LOAD/STORE desteklenmez; hizalama ihlali `ALIGNMENT_FAULT` üretir. Donanım erişimi otomatik olarak birden fazla erişime bölmez. Gelecekte unaligned erişim gerekiyorsa ayrı opcode/mod ile açıkça tanımlanır.
- Erişim aralığı `[EA, EA + W/8 - 1]` 64-bit adres uzayını taşırırsa `ADDRESS_OVERFLOW_FAULT` oluşur. Aralığın seçilen L1/L2/L3/L4 domain'inde tamamen geçerli olması gerekir; domain sınırını aşmak `MEMORY_BOUNDS_FAULT` üretir.
- Erişim izni yoksa `MEMORY_PERMISSION_FAULT`; eşleme/erişim hedefi mevcut değilse `MEMORY_ACCESS_FAULT` oluşur. Hata, komutu başlatan çekirdeğe senkron olarak raporlanır.
- LOAD fault durumunda hedef DA kayıtlarının hiçbiri mimari olarak güncellenmez. STORE için tüm aralık, izin ve sınır kontrolleri yazma commit'inden önce tamamlanır; bu kontrollerden biri başarısızsa hiçbir byte yazılmaz.
- Başarılı 128/256/512-bit LOAD/STORE tek bir mimari komuttur; mikro-mimari bunu birden fazla beat'e bölebilir. Bu, başka çekirdeklerin aynı aralığa eşzamanlı erişimine karşı kendiliğinden atomicity garantisi vermez. Gerekli eşzamanlama/atomic davranış ayrı komutlarla sağlanır.

### 4.7 XFER — Register bankları arası açık aktarım

```text
63       56 55    52 51  50 49   45 44  43 42   38 37  35 34  32 31     0
+----------+--------+------+-------+------+-------+------+-------+--------+
| OP (8)   |FMT (4) | DB(2)| DI (5)| SB(2)| SI (5)| W(3) | M (3) | AUX(32)|
+----------+--------+------+-------+------+-------+------+-------+--------+
```

- DB/SB: hedef/kaynak bank kodu (RA=00, FA=01, DA=10, MA=11).
- DI/SI: hedef/kaynak başlangıç register selector'ı.
- W: taşınan veri genişliği.
- M/AUX: opcode'a özgü transfer alt türü ve gelecekteki genişletmeler.

Örnekler:
- `MOV.RA.DA RA5, DA12`
- `MOV.FA.DA FA3, DA12`
- `MOV.MA.DA MA4, DA0:DA3`
- `MOV.DA.MA DA4:DA7, MA8`

Register bankları arası aktarım bit kopyalama/paketleme işlemidir; integer↔float sayısal dönüşümü değildir. Sayısal dönüşüm FCONV gibi ayrı bir execution opcode'udur.

**XFER M alanı — ilk transfer alt türleri**

| M | İşlem | Geçerlilik |
|---:|---|---|
| 000 | BIT_COPY | Tanımlı bank çiftlerinde ham bit aktarımı |
| 001 | SIGN_EXTEND | Yalnızca DA → RA; W=8/16/32 |
| 010 | ZERO_EXTEND | Yalnızca DA → RA; W=8/16/32 |
| 011–111 | Reserved | İlk sürümde illegal encoding |

- SIGN_EXTEND ve ZERO_EXTEND için W kaynakta anlamlı bit genişliğidir. Kaynak, DA[SI] kaydının düşük W bitidir; hedef RA[DI] kaydının tamamı 64-bit olarak yazılır.
- SIGN_EXTEND, kaynak W-bit değerini signed iki'nin tümleyeni kabul ederek 64-bit'e genişletir.
- ZERO_EXTEND, kaynak W-bit değeri 64-bit'e sıfır genişletir.
- Bu iki işlemde hedef RA'nın eski üst bitleri korunmaz; hedefin 64 biti yeni sonuçla değiştirilir.
- W=64 için genişletme modu geçersizdir; W=64 ham aktarım için M=000 kullanılır.
- SIGN_EXTEND/ZERO_EXTEND başka bank çiftlerinde veya W=128/256/512 için geçersizdir.
- Bu kurallar LOAD'un kendisine signed/unsigned davranış eklemez. LOAD ham veriyi DA'ya getirir; tür yorumu bu açık XFER aşamasında yapılır.

Assembly gösterimi:
- `MOV.RA.DA.SX.W8 RA5, DA12`
- `MOV.RA.DA.SX.W16 RA5, DA12`
- `MOV.RA.DA.SX.W32 RA5, DA12`
- `MOV.RA.DA.ZX.W8 RA5, DA12`
- `MOV.RA.DA.ZX.W16 RA5, DA12`
- `MOV.RA.DA.ZX.W32 RA5, DA12`

Bu suffix'ler XFER opcode'unun M alanını ve W değerini seçen assembly gösterimleridir; ayrı opcode değerleri henüz atanmış değildir.

### 4.8 XFER tabanlı sayısal dönüşüm — FCONV

FCONV bit kopyalama yapmaz; kaynak sayısal değeri hedef türüne dönüştürür. XFER alan yerleşimini kullanır, ancak ayrı opcode ve dönüşüm alt alanlarına sahiptir.

**Bank kuralları**
- Kaynak ve hedef bank yalnızca RA veya FA olabilir.
- RA → FA: signed/unsigned integer'dan floating-point'e dönüşüm.
- FA → RA: floating-point'ten signed/unsigned integer'a dönüşüm.
- RA → RA ve FA → FA bu ilk FCONV tanımında geçersizdir.
- DB/DI hedef bank/selector'ını, SB/SI kaynak bank/selector'ını gösterir.

**XFER payload alanlarının FCONV yorumu**

| Alan | FCONV anlamı |
|---|---|
| DB / DI | Hedef bank ve register |
| SB / SI | Kaynak bank ve register |
| W | Hedef türün bit genişliği |
| M | Dönüşüm alt işlemi; yalnızca `000 = NUMERIC_CONVERT` |
| AUX[31:27] | SRC_TYPE (5 bit) |
| AUX[26:22] | DST_TYPE (5 bit) |
| AUX[21:19] | ROUND (3 bit) |
| AUX[18:16] | CONV_FLAGS (3 bit) |
| AUX[15:0] | RESERVED; sıfır |

Tür kodları:

| Kod | Tür | Genişlik |
|---:|---|---:|
| 00000 | I8 | 8 |
| 00001 | I16 | 16 |
| 00010 | I32 | 32 |
| 00011 | I64 | 64 |
| 00100 | U8 | 8 |
| 00101 | U16 | 16 |
| 00110 | U32 | 32 |
| 00111 | U64 | 64 |
| 01000 | F32 | 32 |
| 01001 | F64 | 64 |
| 01010 | F128 | 128 |
| 01011–11111 | Reserved | — |

ROUND kodları:
- `000`: round-to-nearest, ties-to-even (varsayılan)
- `001`: toward-zero
- `010`: toward-negative-infinity
- `011`: toward-positive-infinity
- `100–111`: reserved

CONV_FLAGS:
- bit 0: saturating integer conversion (yalnızca integer hedefte anlamlı)
- bit 1: invalid/overflow durumunda trap isteği
- bit 2: reserved, sıfır olmalıdır

W, DST_TYPE genişliğiyle aynı olmalıdır. F128 kaynak veya hedef, FA bankında çift indisli pair kullanır; selector pair'in ilk FA kaydını gösterir. Integer türleri RA'nın ilgili genişlik görünümünü kullanır. Küçük integer hedeflerinde DST_TYPE, yazılan bit sayısını ve signed/unsigned yorumunu belirler; RA görünümünün üst bitlerinin korunması/uzatılması register-view kuralıyla uyumlu uygulanır. NaN, sonsuzluk, taşma ve saturating/trap sonuçlarının kesin exception davranışı ayrıca sabitlenecektir. ROUND yalnızca floating-point sonuç üreten dönüşümlerde uygulanır.

Örnekler:
- `FCONV FA3, RA7, i64, f64`: DB=FA, DI=3, SB=RA, SI=7, SRC=I64, DST=F64, W=64.
- `FCONV RA7, FA3, f64, i32`: DB=RA, DI=7, SB=FA, SI=3, SRC=F64, DST=I32, W=32.
- `FCONV FA4:FA5, RA8, i64, f128`: hedef FA pair başlangıcı 4; DST=F128, W=128.

Normal MOV.* XFER komutlarında M/AUX alanları ilgili transfer opcode tanımına göre yorumlanır; FCONV alt alanları onlara uygulanmaz.

### 4.9 BR — PC-relative branch

```text
63       56 55    52 51   48 47                         16 15          0
+----------+--------+-------+-----------------------------+--------------+
| OP (8)   |FMT (4) |COND(4)| DISP (32)                   | RESERVED(16) |
+----------+--------+-------+-----------------------------+--------------+
```

- DISP signed 32-bit PC-relative displacement'tır.
- İlk taslakta displacement byte cinsindendir ve instruction boundary/alignment doğrulaması yapılır.
- COND, branch koşulunu belirler; koşul kodları ayrı tabloda tanımlanacaktır.
- Reserved alan sıfır olmalıdır.

### 4.10 SYS — System ve kontrol komutları

SYS formatı privilege, system state, interrupt, synchronization ve özel kontrol komutları için ayrılmıştır. Alt alan yerleşimi her komut sınıfı için ayrı tabloda tanımlanacaktır. Henüz system register bankı veya CSR sayısı kesinleştirilmemiştir.

## 5. Width alanı

W alanı 3 bit olduğundan sekiz kod sunar:

| W | Bit genişliği | Tipik kullanım |
|---:|---:|---|
| 000 | 8 | Byte / integer element |
| 001 | 16 | Halfword / integer element |
| 010 | 32 | Word / FP32 / vector element |
| 011 | 64 | Doubleword / FP64 |
| 100 | 128 | FP128 veya 128-bit data |
| 101 | 256 | MA register / 256-bit data |
| 110 | 512 | MA pair / 512-bit data |
| 111 | Reserved | Gelecek genişleme |

W alanının yorumu opcode ailesine bağlıdır. Örneğin FADD için W=010 FP32, W=011 FP64 ve W=100 FP128 anlamına gelir. VADD için W, vector element genişliğini belirtir; toplam MA register genişliği 256 bit olarak kalır. ME512 komutlarında W=110, 512-bit pair işlemini gösterebilir.

## 6. Register pair ve grup kuralları

### 6.1 FA / FP128

- FP32 ve FP64 tek FA kaydı kullanır.
- FP128 iki ardışık FA kaydı kullanır.
- Pair başlangıcı çift indisli olmalıdır: FA0:FA1, FA2:FA3, …, FA30:FA31.
- Encoding içindeki FA selector, pair'in ilk kaydını gösterir.
- FA pair komutunda selector'ın LSB biti 0 olmalıdır; aksi durumda illegal-instruction exception oluşur.

### 6.2 MA / 512-bit

- MA kayıtları 256-bit'tir.
- 512-bit ME512 işlemi iki ardışık MA kaydı kullanır.
- Pair başlangıcı çift indisli olmalıdır: MA0:MA1, MA2:MA3, …, MA30:MA31.
- Encoding içindeki MA selector, pair'in ilk kaydını gösterir.
- 512-bit pair komutunda selector'ın LSB biti 0 olmalıdır.

### 6.3 DA / 256-bit transfer grubu

- DA kayıtları 64-bit'tir.
- Tek MA kaydı ile 256-bit transfer, dört ardışık DA kaydını kullanır.
- Önerilen başlangıç hizalaması 4 kayıtlık gruba göredir: DA0:DA3, DA4:DA7, …, DA28:DA31.
- XFER formatında DA selector, grubun ilk kaydını gösterir.
- Bu grup hizalaması ilk encoding önerisidir; son ISA doğrulamasında kesinleştirilecektir.

LOAD/STORE için çoklu DA kayıt dağılımı bu bölümde tanımlanmıştır. Açık kalan konu, effective address için doğal hizalama ve misaligned erişimlerin desteklenme/exception davranışıdır; SPM hizalama kuralları kendi bölümünde ele alınır.

## 7. Immediate ve 64-bit literal genişletme

36-bit immediate, birçok sabit ve displacement ihtiyacı için temel formattır. 64-bit adres ve sabitler için 64-bit register genişliğini koruyan bir literal extension mekanizması gerekir.

İlk öneri:
1. EXT formatlı ilk word, hedef opcode/format ve hedef register bilgisini taşır.
2. Hemen ardından gelen ikinci 64-bit word, literal payload olarak yorumlanır.
3. Decoder ikinci word'ü opcode olarak decode etmez; ilk word'ün payload'ı olarak tüketir.
4. Bu iki word'lü komut P0'da iki adet 64-bit kayıt kullanır.
5. Branch hedefleri ve bellek adresleri yine 64-bit RA registerları üzerinden çalışır.

Örnek assembly gösterimi (sembolik):

```asm
MOVI64 RA4, 0x123456789ABCDEF0
LOAD.L1 DA2, [RA4 + 0]
```

İlk word'ün EXT alt format kodu ve ikinci word'ün byte sıralaması, opcode tablosu dondurulurken kesinleştirilecektir. Literal word, branch hedefi veya komut akışına atlanan normal bir instruction gibi yürütülmemelidir.

## 8. Opcode alanı ve ilk opcode haritası

OP alanı 8-bit olduğundan 256 primary opcode değeri sunar. İlk aşamada opcode numaralarını aileler halinde ayırmak önerilir:

| OP aralığı | Ayrılan aile | Durum |
|---|---|---|
| 0x00–0x0F | Control-flow / branch | Öneri |
| 0x10–0x2F | Integer / scalar ALU | Öneri |
| 0x30–0x3F | Bit / Boolean / shift | Öneri |
| 0x40–0x4F | Load/store / address | Öneri |
| 0x50–0x5F | Floating point / conversion | Öneri |
| 0x60–0x6F | Vector / Matrix / ME512 | Öneri |
| 0x70–0x7F | Register transfer / bank move | Öneri |
| 0x80–0x8F | SPM access / SPM control | Öneri |
| 0x90–0xAF | System / synchronization | Öneri |
| 0xB0–0xEF | Reserved / future extensions | Ayrılmış |
| 0xF0–0xFF | Escape / EXT / implementation-defined | Ayrılmış |

Bu aralıklar final opcode numaraları değildir. Primary opcode, FMT ile birlikte komut tanımını seçer; aynı aile içinde farklı formatlar kullanılabilir.

## 9. Decoder ve P0 akışı

- P0 her zaman 64-bit instruction word kayıtları tutar.
- Decoder ilk 64-bit word üzerinden OP ve FMT alanlarını çözer.
- Tek word komutlarda bir P0 kaydı tüketilir.
- EXT literal kullanan iki word komutlarda ilk word + literal word birlikte tüketilir.
- Literal word normal opcode olarak decode edilmez.
- Decode/dispatch sonrası komut uygun issue kuyruğuna gönderilir.
- P0 kapasitesi, fetch genişliği ve issue sayısı birbirinden farklı kavramlardır; 512-bit fetch bir çevrimde sekiz 64-bit word getirebilir ancak sekiz komutun aynı çevrimde yürütüleceği anlamına gelmez.

## 10. Exception ve illegal encoding ilkeleri

Aşağıdaki durumlar illegal instruction veya ilgili erişim exception'ı üretmelidir:

- Reserved FMT veya opcode kullanımı.
- Reserved alanlarda sıfır dışında değer bulunması.
- Register selector'ın 0–31 aralığı dışında olması (5-bit selector zaten bu aralığı sağlar; pair/group taşması ayrıca kontrol edilir).
- FP128 için tek numaralı FA pair başlangıcı.
- 512-bit ME512 için tek numaralı MA pair başlangıcı.
- DA 4-register group erişiminin DA31 sınırını aşması veya hizalama şartını ihlal etmesi.
- Komutun istediği register bankı ile kodlanan bankın uyuşmaması.
- EXT komutunun gerekli literal word'ünün kod belleği/P0 akışında bulunmaması.

Exception türleri, trap vector ve hata raporlama ayrıntıları ayrı system-control bölümünde tanımlanacaktır.

## 11. Örnek alan eşlemeleri

Aşağıdaki örnekler gerçek hexadecimal makine kodu değildir; opcode değerleri henüz atanmadığı için sembolik alan eşlemesidir.

| Assembly | Format | Alanların yorumu |
|---|---|---|
| `ADD RA3, RA1, RA2` | R3 | OP_ADD, FMT_R3, D=3, A=1, B=2, W=64 |
| `FADD FA4, FA1, FA2` | R3 | OP_FADD, FMT_R3, D=4, A=1, B=2, W=FP64 |
| `VADD.W32 MA8, MA4, MA12` | R3 | OP_VADD, FMT_R3, D=8, A=4, B=12, W=32 |
| `FMA FA4, FA1, FA2, FA3` | R4 | OP_FMA, FMT_R4, D=4, A=1, B=2, C=3, W=FP64 |
| `VMACC.W32 MA8, MA4, MA12, MA16` | R4 | OP_VMACC, FMT_R4, D=8, A=4, B=12, C=16, W=32 |
| `LOAD.L1 DA12, [RA20+16]` | MEM | D=12, BASE=20, W=64, AM=000 (L1), DISP=16 |
| `MOV.FA.DA FA3, DA12` | XFER | DB=FA, DI=3, SB=DA, SI=12, W=64 |
| `MOV.MA.DA MA4, DA0:DA3` | XFER | DB=MA, DI=4, SB=DA, SI=0, W=256 |

## 12. Henüz dondurulmamış kararlar

1. OP ve FMT sayısal kodlarının nihai tablosu.
2. Komut sözcüğünün byte endianness ve bellek içi sıralaması.
3. EXT word'ün kesin bit alanları ve birden çok literal word gerekip gerekmediği.
4. MEM erişimlerinde doğal hizalama ve misaligned erişimlerin desteklenme/exception davranışı.
5. DA 256-bit grup hizalamasının kesinleştirilmesi.
6. MA/FA pair komutlarının opcode ve exception ayrıntıları.
7. Branch koşul kodları ve displacement'in PC'ye göre referans noktası (komut başlangıcı veya sonraki komut).
8. SYS formatının system register/privilege alanları.
9. Komutlarda predicate/condition alanı gerekip gerekmediği.
10. Reserved bitlerin gelecekteki uyumluluk politikası.
11. FCONV için NaN, infinity, integer overflow ve saturating/trap durumlarının kesin exception sonuçları.

---

## 13. Tasarım özeti

- Temel instruction word: **64 bit**.
- Primary opcode: **8 bit**.
- Format selector: **4 bit**.
- Register selector: **5 bit** (her bankta 32 kayıt).
- Register bank kodu: **2 bit** (yalnızca genel XFER formatında).
- Immediate: temel RI formatında **signed 36 bit**.
- Memory displacement: **signed 32 bit**, 64-bit RA base ile.
- MEM domain seçimi: AM[2:1] ile L1/L2/L3/L4; AM[0]=0 base + displacement.
- LOAD/STORE erişim genişliği ve DA grup dağılımı: 8–512 bit; 1/2/4/8 ardışık DA kaydı.
- Branch displacement: **signed 32 bit**.
- Geniş literal: takip eden ek **64-bit word**.
- P0: 64-bit word kayıtları; iki word'lü komutlar iki P0 kaydı tüketir.

Bu belge, NEXSUS CPU instruction encoding için ilk ortak referanstır. Sayısal opcode değerleri ve açık kararlar kapatıldığında revizyon 1.0 olarak dondurulabilir.
