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
| 1000–1111 | Reserved | Gelecek formatlar |

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

### 4.3 RI — Register + immediate

```text
63       56 55    52 51   47 46   42 41  39 38  36 35                 0
+----------+--------+-------+-------+------+-------+-------------------+
| OP (8)   |FMT (4) | D (5) | A (5) | W(3) | M (3) | IMM (36)          |
+----------+--------+-------+-------+------+-------+-------------------+
```

- IMM, varsayılan olarak signed 36-bit iki'nin tümleyeni immediate değeridir.
- Opcode signed/unsigned yorumunu veya shift-count gibi özel kullanımı açıkça belirtir.
- Daha geniş sabitler EXT formatı ile taşınır.

### 4.4 MEM — Bellek erişimi

```text
63       56 55    52 51   47 46   42 41  39 38  36 35             4 3   0
+----------+--------+-------+-------+------+-------+---------------+-----+
| OP (8)   |FMT (4) | D (5) | BASE(5)| W(3)| AM(3)| DISP (32)     | R(4)|
+----------+--------+-------+-------+------+-------+---------------+-----+
```

- D: LOAD için hedef DA selector; STORE için kaynak DA selector.
- BASE: RA bankından 64-bit adres tabanı selector'ı.
- W: veri erişim genişliği.
- AM: adresleme modu (ilk sürümde base + signed displacement; diğer kodlar ayrılmıştır).
- DISP: signed 32-bit byte displacement.
- R: reserved; sıfır olmalıdır.

Effective address:

`EA = RA[BASE] + sign_extend(DISP)`

64-bit adresin tamamı RA kaydında tutulur. Böylece 32-bit displacement, 64-bit adres alanını sınırlamaz.

### 4.5 XFER — Register bankları arası açık aktarım

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

### 4.6 BR — PC-relative branch

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

### 4.7 SYS — System ve kontrol komutları

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

Daha geniş LOAD/STORE ve SPM transferlerinde birden çok DA kaydının nasıl seçileceği, opcode başına transfer genişliği ve alignment kuralıyla ayrıca tanımlanacaktır.

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
LOAD   DA2, [RA4 + 0]
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
| `LOAD DA12, [RA20+16]` | MEM | D=12, BASE=20, W=64, DISP=16 |
| `MOV.FA.DA FA3, DA12` | XFER | DB=FA, DI=3, SB=DA, SI=12, W=64 |
| `MOV.MA.DA MA4, DA0:DA3` | XFER | DB=MA, DI=4, SB=DA, SI=0, W=256 |

## 12. Henüz dondurulmamış kararlar

1. OP ve FMT sayısal kodlarının nihai tablosu.
2. Komut sözcüğünün byte endianness ve bellek içi sıralaması.
3. EXT word'ün kesin bit alanları ve birden çok literal word gerekip gerekmediği.
4. MEM formatında LOAD/STORE genişliği, signed/unsigned load ve multi-DA transfer kuralları.
5. DA 256-bit grup hizalamasının kesinleştirilmesi.
6. MA/FA pair komutlarının opcode ve exception ayrıntıları.
7. Branch koşul kodları ve displacement'in PC'ye göre referans noktası (komut başlangıcı veya sonraki komut).
8. SYS formatının system register/privilege alanları.
9. Komutlarda predicate/condition alanı gerekip gerekmediği.
10. Reserved bitlerin gelecekteki uyumluluk politikası.

---

## 13. Tasarım özeti

- Temel instruction word: **64 bit**.
- Primary opcode: **8 bit**.
- Format selector: **4 bit**.
- Register selector: **5 bit** (her bankta 32 kayıt).
- Register bank kodu: **2 bit** (yalnızca genel XFER formatında).
- Immediate: temel RI formatında **signed 36 bit**.
- Memory displacement: **signed 32 bit**, 64-bit RA base ile.
- Branch displacement: **signed 32 bit**.
- Geniş literal: takip eden ek **64-bit word**.
- P0: 64-bit word kayıtları; iki word'lü komutlar iki P0 kaydı tüketir.

Bu belge, NEXSUS CPU instruction encoding için ilk ortak referanstır. Sayısal opcode değerleri ve açık kararlar kapatıldığında revizyon 1.0 olarak dondurulabilir.
