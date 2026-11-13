# NEXSUS CPU — Instruction Encoding Specification

**Belge:** NEXSUS-CPU-INSTRUCTION-ENCODING-001  
**Durum:** Tasarım taslağı — 64-bit temel komut sözcüğü ve alan yerleşimi  
**Bağlı belgeler:**
- `NEXSUS-CPU-ISA-001.md` — mnemonic, operand ve execution-unit tanımları
- `Yeni Nesil Ayrıştırılmış Register Tabanlı CPU Mimarisi.md` — CPU ve bellek mimarisi
- `NEXSUS CPU — SPM, Register Görünümleri ve Doğrudan Alan Erişimi.md` — register/SPM ayrıntıları

> Bu belge, ISA mnemonic'lerini makine koduna dönüştürmek için ilk encoding modelini tanımlar. Alan genişlikleri ve format yapısı önerilen temel tasarımdır. Sayısal opcode atamaları ve bazı özel formatlar henüz dondurulmamıştır. Bellek ve komut sözcüğü byte sıralaması little-endian olarak kararlaştırılmıştır.

---

## 3. Little-endian byte ve word sıralaması

NEXSUS CPU'nun bellek byte sıralaması **little-endian**'dır. Bu karar veri belleği, SPM byte erişimleri, komut sözcüklerinin bellekte/P0'da temsil edilmesi ve çok sözcüklü literal dizileri için geçerlidir.

- Birden fazla byte içeren scalar değerlerde en düşük bellek adresi en düşük anlamlı byte'ı (LSB) taşır.
- 64-bit bir değer bellekte `A` adresinden başlıyorsa bit[7:0] `A`, bit[15:8] `A+1` ... bit[63:56] `A+7` adresindedir.
- 128/256/512-bit LOAD/STORE'da en düşük adresli 64-bit parça ilk DA kaydına yazılır; sonraki 64-bit parçalar artan adres sırasıyla artan DA selector'larına gider. Her DA kaydının iç byte sırası da little-endian'dır.
- FA128 gibi register pair'lerinde düşük anlamlı 64-bit parça çift indisli ilk FA kaydında, yüksek anlamlı parça sonraki FA kaydındadır.
- 512-bit MA pair aktarımında düşük anlamlı 256-bit parça ilk MA kaydında, yüksek anlamlı parça sonraki MA kaydındadır. DA grubu kullanılıyorsa DA'nın en düşük selector'ı en düşük anlamlı 64-bit parçayı tutar.
- Her 64-bit instruction word bellekte/P0'a little-endian byte sırasıyla yerleştirilir: word bit[7:0] en düşük byte adresindedir.
- EXT gibi çok sözcüklü komutlarda extension/literal word, ana komut word'ünü izleyen daha yüksek adresli 64-bit word'dür. Literal word'ün kendi byte sırası da little-endian'dır. Bu kural literal'in opcode olarak decode edilmesi anlamına gelmez.

Little-endian, bit alanlarının instruction word içindeki konumunu değiştirmez; encoding tablolarındaki bit numaraları mantıksal 64-bit word üzerindedir.

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
| 1001 | MEMX | Indexed load/store: base + index × scale + displacement |
| 1010 | MEMUPD | Load/store with base-register pre/post increment/decrement |
| 1011 | MEMXUPD | Indexed load/store with base-register pre/post increment/decrement |
| 1100 | ATOM | Atomic scalar memory operations (load/store/CAS/RMW) |
| 1101–1111 | Reserved | Gelecek formatlar |

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
- AM[0]: adresleme biçimi: **0 = base register + displacement**, **1 = absolute domain address**.
- DISP: normal formda signed 32-bit byte displacement. EXT paketinde sıfır olmalıdır; genişletilmiş displacement/adres literal word'den alınır.
- R: reserved; sıfır olmalıdır.

**AM alanı**

| AM[2:1] | Domain | Hedef |
|---:|---|---|
| 00 | L1 | Yalnızca geçerli çekirdeğin özel L1 domain'i |
| 01 | L2 | İlgili iki çekirdeklik grubun ortak domain'i |
| 10 | L3 | İlgili dört çekirdeklik grubun ortak domain'i |
| 11 | L4 | İlgili sekizli veya daha geniş grubun ortak domain'i |

AM[0]=0, base-register adreslemesidir. EXT kullanılmayan komutta geçerli domain kodları L1=000, L2=010, L3=100, L4=110 olur; bu biçimde EA, RA[BASE] ile signed DISP32 toplamıdır. EXT formunda DISP=0 zorunludur; literal RAW_LITERAL/COUNT=1 olmalıdır ve signed 64-bit byte displacement olarak yorumlanır: `EA = RA[BASE] + sign_extend(LITERAL64)`. Toplama 64-bit adres alanında taşma veya negatif yönde alt-taşma oluşturursa `ADDRESS_OVERFLOW_FAULT` oluşur.

AM[0]=1, yalnızca EXT formunda kullanılabilen absolute domain address biçimidir. BASE=0 ve DISP=0 zorunludur; literal word unsigned 64-bit domain adresidir ve doğrudan EA olarak kullanılır. EXT olmadan AM[0]=1 illegal encoding'dir. Bu adres, seçilen L1/L2/L3/L4 domain'inin adres uzayında yorumlanır; fiziksel adres olduğu varsayılmaz.

Her iki EXT biçiminde de paket sırası EXT prefix (RAW_LITERAL, COUNT=1) → MEM instruction word → 64-bit literal word'dür. Domain, komutun gerçek veri erişim hedefidir; örtük cache fill veya başka Lx seviyesine kopyalama anlamına gelmez.

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
- MEM erişimlerinde 128/256/512-bit DA grupları için ek selector hizalaması aranmaz; yalnızca DA31 sınırı kontrol edilir. Bellek adresinin doğal hizalaması ise zorunludur ve aşağıdaki fault kurallarıyla denetlenir.
- 8/16/32-bit LOAD, ilgili DA kaydının düşük bitlerine veriyi yazar ve aynı kaydın kullanılmayan üst bitlerini sıfırlar. 64-bit LOAD kaydın tamamını yazar.
- 128/256/512-bit erişimlerde ardışık 64-bit parçalar artan bellek adresi sırasıyla artan DA selector'larına eşlenir. Her DA kaydının kendi içindeki byte sıralaması little-endian'dır: en düşük bellek adresi kaydın en düşük anlamlı byte'ına karşılık gelir.
- STORE yalnızca istenen W bitini bellek alanına yazar; son DA kaydındaki erişim genişliği dışında kalan bitler yazılmaz.
- LOAD/STORE ham bit aktarımı yapar. LOAD signed/unsigned yorumlama veya sign-extension yapmaz. Signed/unsigned yorum, DA'dan RA/FA'ya sonraki açık dönüşüm/transfer aşamasında yapılır.
- **Doğal hizalama zorunludur.** EA, erişim boyutunun byte karşılığına (W/8) tam bölünmelidir. Örnek: W=16 için 2-byte, W=64 için 8-byte, W=512 için 64-byte hizalama gerekir. W=8 için her byte adresi geçerlidir.
- İlk ISA sürümünde misaligned LOAD/STORE desteklenmez; hizalama ihlali `ALIGNMENT_FAULT` üretir. Donanım erişimi otomatik olarak birden fazla erişime bölmez. Gelecekte unaligned erişim gerekiyorsa ayrı opcode/mod ile açıkça tanımlanır.
- Erişim aralığı `[EA, EA + W/8 - 1]` 64-bit adres uzayını taşırırsa `ADDRESS_OVERFLOW_FAULT` oluşur. Aralığın seçilen L1/L2/L3/L4 domain'inde tamamen geçerli olması gerekir; domain sınırını aşmak `MEMORY_BOUNDS_FAULT` üretir.
- Erişim izni yoksa `MEMORY_PERMISSION_FAULT`; eşleme/erişim hedefi mevcut değilse `MEMORY_ACCESS_FAULT` oluşur. Hata, komutu başlatan çekirdeğe senkron olarak raporlanır.
- LOAD fault durumunda hedef DA kayıtlarının hiçbiri mimari olarak güncellenmez. STORE için tüm aralık, izin ve sınır kontrolleri yazma commit'inden önce tamamlanır; bu kontrollerden biri başarısızsa hiçbir byte yazılmaz.
- Başarılı 128/256/512-bit LOAD/STORE tek bir mimari komuttur; mikro-mimari bunu birden fazla beat'e bölebilir. Bu, başka çekirdeklerin aynı aralığa eşzamanlı erişimine karşı kendiliğinden atomicity garantisi vermez. Gerekli eşzamanlama/atomic davranış ayrı komutlarla sağlanır.

### 4.7 MEMX — İndeksli bellek erişimi

MEMX, MEM formatının register-indirect adreslemesini genişletir. D, W ve AM alanlarının anlamı MEM ile aynıdır; ek olarak bir INDEX register'ı ve SCALE alanı bulunur.

```text
63       56 55    52 51   47 46   42 41   37 36  34 33  31 30  28 27             0
+----------+--------+-------+-------+-------+------+-------+------+----------------+
| OP (8)   |FMT (4) | D (5) | BASE(5)| INDEX(5)| W(3)| AM(3)|SCALE | DISP (28)      |
+----------+--------+-------+-------+-------+------+-------+------+----------------+
```

Bit alanı tanımı (payload bitleri):
- D[51:47]: LOAD hedefi / STORE kaynağı DA başlangıç selector'ı.
- BASE[46:42]: RA bankında taban adres register selector'ı.
- INDEX[41:37]: RA bankında indeks register selector'ı.
- W[36:34]: erişim genişliği; MEM ile aynı 8/16/32/64/128/256/512-bit kodları.
- AM[33:31]: domain alanı; AM[0]=0 zorunludur. MEMX absolute adresleme desteklemez.
- SCALE[30:28]: indeks çarpanı.
- DISP[27:0]: normal formda signed 28-bit byte displacement.
- FMT=1001, MEMX formatını belirtir; bu formatta kullanılmayan/reserved bit yoktur.

**SCALE kodları**

| SCALE | Çarpan |
|---:|---:|
| 000 | 1 |
| 001 | 2 |
| 010 | 4 |
| 011 | 8 |
| 100 | 16 |
| 101–111 | Reserved; illegal encoding |

**Adres hesaplama**

Normal MEMX formunda:

`EA = RA[BASE] + (signed(RA[INDEX]) × SCALE) + sign_extend(DISP28)`

- BASE ve INDEX birbirinden bağımsız RA selector'larıdır; aynı selector kullanılabilir.
- INDEX, signed two's-complement 64-bit tamsayı olarak yorumlanır. Negatif indeksler desteklenir.
- SCALE çarpanı yalnızca indeks terimine uygulanır; DISP byte cinsindendir ve ölçeklenmez.
- Ara hesaplama taşması sessizce sarılmaz. Matematiksel sonuç 0…2^64−1 aralığının dışındaysa `ADDRESS_OVERFLOW_FAULT` oluşur.
- EXT formunda DISP28=0 zorunludur ve literal signed 64-bit byte displacement olarak kullanılır:

`EA = RA[BASE] + (signed(RA[INDEX]) × SCALE) + signed(LITERAL64)`

- MEMX ile EXT paket sırası EXT prefix (`RAW_LITERAL/COUNT=1`) → MEMX instruction word → 64-bit literal word'dür.
- MEMX yalnızca base + indexed addressing içindir. Absolute adresleme MEM formatındaki EXT + AM[0]=1 biçimiyle yapılır; MEMX absolute mod taşımaz.
- Domain seçimi, doğal hizalama, DA selector sınırı, izin, bounds ve fault davranışları MEM ile aynıdır.
- EXT kullanılmayan MEMX komutu tek 64-bit word'dür. EXT kullanılan MEMX paketi üç 64-bit word'dür.

Örnek assembly gösterimleri:

```asm
LOAD.L1.W64 DA4, [RA10 + RA11*1 + 8]
LOAD.L2.W128 DA8:DA9, [RA12 + RA13*4 - 16]
STORE.L3.W256 [RA20 + RA21*8 + 32], DA12:DA15

; Geniş displacement: EXT literal signed 64-bit byte offset
LOAD.L1.W64 DA2, [RA4 + RA5*2 + disp64(0x100000000)]
```

`disp64(value)` assembler gösterimidir; MEMX.DISP alanı sıfır kodlanır ve literal EXT paketinden alınır. İndeks ölçeği ve register selector'ları normal MEMX word'ünde kalır.

### 4.8 MEMUPD — Otomatik taban register güncellemeli bellek erişimi

MEMUPD, MEM'in base + displacement adreslemesini korur ve başarılı LOAD/STORE ile birlikte BASE register'ını erişim genişliği kadar artırır veya azaltır.

```text
63       56 55    52 51   47 46   42 41  39 38  36 35  34 33                 0
+----------+--------+-------+-------+------+-------+------+-------------------+
| OP (8)   |FMT (4) | D (5) | BASE(5)| W(3)| AM(3)|MODE(2)| DISP (34)         |
+----------+--------+-------+-------+------+-------+------+-------------------+
```

Payload alanları toplam 52 bittir:
- D: LOAD hedefi / STORE kaynağı DA başlangıç selector'ı.
- BASE: güncellenecek RA taban register selector'ı.
- W: MEM ile aynı erişim genişliği kodları (8/16/32/64/128/256/512).
- AM: MEM domain alanı; AM[0]=0 zorunludur. Absolute adresleme bu formatta desteklenmez.
- MODE: güncelleme yönü ve zamanı.
- DISP: normal formda signed 34-bit byte displacement; EXT formunda sıfır olmalıdır.

**MODE kodları**

| MODE | İşlem | Effective address ve güncelleme |
|---:|---|---|
| 00 | POSTINC | EA eski BASE + DISP; başarılı erişimden sonra BASE += W/8 |
| 01 | PREINC | EA eski BASE + W/8 + DISP; başarılı erişimle BASE += W/8 |
| 10 | POSTDEC | EA eski BASE + DISP; başarılı erişimden sonra BASE -= W/8 |
| 11 | PREDEC | EA eski BASE - W/8 + DISP; başarılı erişimle BASE -= W/8 |

- Artış/azalış miktarı erişim genişliğinin byte karşılığıdır. Örnek: W=64 → 8 byte; W=128 → 16 byte; W=512 → 64 byte.
- PRE/POST yalnızca BASE güncellemesinin erişim adresine göre sırasını belirler. DISP her iki modda da byte cinsinden eklenir.
- Normal biçimde EA, base_term + signed DISP34 olur. PRE modlarında base_term, eski BASE'in ± W/8 uygulanmış değeridir; POST modlarında eski BASE değeridir.
- EXT biçiminde DISP34=0 zorunludur; literal signed 64-bit byte displacement olur.
- BASE güncellemesi ve LOAD/STORE tek bir mimari komut olarak commit edilir. Adres taşması, alignment, bounds, permission veya access fault oluşursa BASE ve LOAD hedefi DA kayıtları değişmeden kalır; faulting STORE hiçbir byte yazmaz.
- PRE modunda BASE ± W/8 işleminin kendisi 64-bit adres uzayını taşırırsa ADDRESS_OVERFLOW_FAULT oluşur. POST modunda erişim başarılı olsa bile yeni BASE değeri 0…2^64−1 aralığının dışına çıkacaksa komut commit edilmez ve aynı fault oluşur.
- Domain seçimi, doğal hizalama, DA selector sınırı, erişim izinleri ve fault kodları MEM ile aynıdır.

### 4.9 MEMXUPD — İndeksli ve otomatik taban güncellemeli bellek erişimi

MEMXUPD, MEMX'in base + index × scale + displacement adres hesaplamasını korur ve başarılı erişimle BASE register'ını W/8 kadar günceller.

```text
63       56 55    52 51   47 46   42 41   37 36  34 33  31 30  28 27 26 25          0
+----------+--------+-------+-------+-------+------+-------+------+-----+------------+
| OP (8)   |FMT (4) | D (5) | BASE(5)| INDEX(5)| W(3)| AM(3)|SCALE |MODE | DISP (26)  |
+----------+--------+-------+-------+-------+------+-------+------+-----+------------+
```

Payload alanları toplam 52 bittir:
- D: LOAD hedefi / STORE kaynağı DA başlangıç selector'ı.
- BASE ve INDEX: RA bankı selector'ları; aynı selector kullanılabilir.
- W ve AM: MEMX ile aynı anlam ve kısıtlar; AM[0]=0 zorunludur.
- SCALE: MEMX ile aynı çarpan kodları (×1/×2/×4/×8/×16); 101–111 reserved.
- MODE: MEMUPD ile aynı POSTINC/PREINC/POSTDEC/PREDEC kodları.
- DISP: normal formda signed 26-bit byte displacement; EXT formunda sıfır olmalıdır.

**Adres ve update semantiği**
- INDEX, komut başlangıcındaki eski RA[INDEX] değerinden signed 64-bit olarak okunur. BASE=INDEX olsa bile indeks terimi eski register değerinden alınır.
- POST modlarında EA = old_BASE + (signed(old_INDEX) × SCALE) + DISP; başarılı erişimden sonra BASE, W/8 kadar artırılır/azaltılır.
- PRE modlarında EA = (old_BASE ± W/8) + (signed(old_INDEX) × SCALE) + DISP; başarılı erişimle BASE, aynı ± W/8 güncellemesini alır.
- EXT biçiminde DISP26=0 zorunludur; literal signed 64-bit byte displacement olarak DISP teriminin yerini alır.
- İndeks çarpımı, displacement ekleme, effective address ve BASE güncellemesi matematiksel olarak 64-bit unsigned adres aralığında kalmalıdır; taşma/sarım yoktur.
- BASE update ve bellek erişimi tek mimari commit'tir. Herhangi bir fault durumunda BASE ve LOAD hedef DA kayıtları değişmeden kalır; STORE hiçbir byte yazmaz.
- Diğer tüm domain, alignment, DA sınırı, izin ve fault kuralları MEM/MEMX ile aynıdır.
- Otomatik update miktarı W/8'dir. Farklı stride gereken yapılar için ayrı ADD/ADDI ile BASE açıkça değiştirilir; bu komutlar keyfi stride register'ı taşımaz.

**Assembly gösterimi**
```asm
LOAD.POSTINC.L1.W64 DA0, [RA10]
LOAD.PREDEC.L2.W128 DA4:DA5, [RA12 - 16]
STORE.POSTINC.L3.W256 [RA20], DA8:DA11
LOAD.POSTINC.L1.W64 DA2, [RA4 + RA5*2 + 8]
```

POSTINC/PREINC/POSTDEC/PREDEC suffix'leri MEMUPD veya MEMXUPD MODE alanını seçen assembler gösterimleridir; bağımsız opcode numaraları henüz atanmış değildir. Bu biçimlerde EXT kullanıldığında literal signed 64-bit displacement sağlar ve ilgili DISP alanı sıfır kodlanır.
### 4.10 ATOM — Atomic scalar memory işlemleri

ATOM formatı, seçilen L1–L4 domain'inde doğal hizalı 8/16/32/64-bit atomic load/store ve read-modify-write işlemleri için kullanılır.

```text
63       56 55    52 51   47 46   42 41   37 36   32 31  29 28  26 25  23 22          0
+----------+--------+-------+-------+-------+-------+------+-------+-------+------------+
| OP (8)   |FMT (4) | D (5) | BASE(5)| A (5) | B (5) | W(3)| AM(3)|ORDER(3)| DISP (23)  |
+----------+--------+-------+-------+-------+-------+------+-------+-------+------------+
```

Payload toplamı 52 bittir:
- D: atomic LOAD/RMW sonucunda bellek konumundan okunan eski değerin yazılacağı DA selector'ı.
- BASE: effective address için RA selector'ı.
- A: CAS için beklenen (expected) değeri tutan DA selector'ı; CAS dışındaki işlemlerde sıfır olmalıdır.
- B: STORE/RMW kaynak operandını tutan DA selector'ı. LOAD için sıfır olmalıdır.
- W: yalnızca 8/16/32/64-bit atomic genişlikleri geçerlidir. 128/256/512 ve reserved width kodları illegal encoding'dir.
- AM: MEM ile aynı domain kodlaması; AM[0]=0 zorunludur. AM[2:1] L1/L2/L3/L4 seçer.
- ORDER: memory ordering modeli.
- DISP: normal biçimde signed 23-bit byte displacement. EXT biçiminde DISP=0 zorunludur ve literal signed 64-bit displacement olarak kullanılır.

Effective address normal biçimde `RA[BASE] + sign_extend(DISP23)`; EXT biçiminde `RA[BASE] + signed(LITERAL64)` olarak hesaplanır. 64-bit adres aralığı dışına taşma `ADDRESS_OVERFLOW_FAULT` üretir. Absolute ve indexed adresleme bu ilk ATOM formatında yoktur; gerekirse önce LEA ile adres RA register'ında hazırlanır.

**ORDER kodları**

| ORDER | Semantik |
|---:|---|
| 000 | RELAXED | Atomicity vardır; ek sıralama garantisi yoktur |
| 001 | ACQUIRE | Bu işlemden sonraki bellek işlemleri acquire sıralamasına tabidir |
| 010 | RELEASE | Bu işlemden önceki bellek işlemleri release sıralamasına tabidir |
| 011 | ACQ_REL | Hem acquire hem release sıralaması |
| 100 | SEQ_CST | Sequentially consistent atomic sıralama |
| 101–111 | Reserved | Illegal encoding |

- Atomic LOAD için RELAXED, ACQUIRE veya SEQ_CST geçerlidir; RELEASE ve ACQ_REL geçersizdir.
- Atomic STORE için RELAXED, RELEASE veya SEQ_CST geçerlidir; ACQUIRE ve ACQ_REL geçersizdir.
- CAS ve diğer read-modify-write işlemleri beş geçerli ordering değerinin tümünü kullanabilir.

**Operand kullanımı ve işlemler**

| İşlem | D | A | B | Sonuç / etki |
|---|---|---|---|---|
| ATOM.LOAD | Sonuç | 0 | 0 | Bellekteki eski değeri D'ye getirir |
| ATOM.STORE | 0 | 0 | Kaynak | B'nin düşük W bitini belleğe yazar |
| CAS | Eski değer | Expected | Desired | Bellek yalnızca eski değer Expected ile eşitse Desired olur |
| SWAP | Eski değer | 0 | Yeni değer | Bellekteki değeri B ile değiştirir |
| FETCH_ADD / FETCH_SUB | Eski değer | 0 | Operand | Eski değeri döndürür; belleği toplama/çıkarma sonucu ile günceller |
| FETCH_AND / FETCH_OR / FETCH_XOR | Eski değer | 0 | Operand | Eski değeri döndürür; belleği bitwise sonuç ile günceller |

- RMW işlemleri (CAS, SWAP, FETCH_*) hedef konumun eski değerini D'ye yazar. W<64 olduğunda D'nin üst bitleri sıfırlanır.
- Kaynak operandlar komut başlangıcında snapshot edilir. D ile B aynı DA selector'ı olabilir. CAS için D ve A farklı selector olmalıdır; böylece döndürülen eski değer expected operandını ezmez.
- CAS başarısı, döndürülen D değerinin A'daki expected değerle eşit karşılaştırılmasıyla belirlenir. İlk sürümde ayrı success flag/status register üretilmez.
- FETCH_ADD/FETCH_SUB sonucu W-bit modulo arithmetic olarak hesaplanır; taşma wrap-around'dur ve arithmetic fault üretmez. FETCH_AND/OR/XOR bitwise W-bit işlemleridir.
- ATOM.LOAD/STORE ve RMW işlemleri yalnızca tek bir scalar bellek konumu üzerinde atomic'tir. 128/256/512-bit atomic işlem desteklenmez.

**Atomicity, domain ve fault kuralları**
- Atomic erişim effective address'in W/8 byte'a doğal hizalı olmasını gerektirir; misalignment `ALIGNMENT_FAULT` üretir.
- Atomic işlem, seçilen domain'deki aynı adres ve W genişliğine yönelik diğer atomic işlemlere karşı indivisible/linearizable olmalıdır.
- L1 çekirdeğe özel olduğundan L1 atomic işlemleri çekirdek içi senkronizasyon kapsamındadır. L2, L3 ve L4 atomic işlemleri ilgili paylaşım grubundaki tüm çekirdekler için aynı serialization domain'ine katılmalıdır.
- Atomic ordering, yalnızca aynı adrese değil, mimari memory-order kurallarına uygun olarak çekirdeğin ilgili bellek işlemlerine uygulanır. Ordering, farklı L1–L4 domain'leri arasında veri kopyalama veya otomatik coherence oluşturmaz.
- Aynı bellek konumuna atomic ve non-atomic erişimlerin eşzamanlı karıştırılması, ayrıca senkronizasyonla korunmadıkça data race kabul edilir.
- Bounds, permission, mapping, alignment veya address overflow fault'unda bellek değişmez; LOAD/RMW hedefi D de değişmeden kalır. Faulting STORE/RMW hiçbir kısmi yazma yapamaz.
- Atomic serialization, bellek domain'inin uygulama düzeyindeki coherence/visibility protokolünü gerektirir. Fiziksel arbiter, bank locking ve cache-coherence uygulaması mikro-mimari aşamasında belirlenir.

Assembly örnekleri:

```asm
ATOM.LOAD.ACQUIRE.L2.W64 DA0, [RA10]
ATOM.STORE.RELEASE.L2.W64 [RA10], DA1
CAS.ACQ_REL.L2.W64 DA2, [RA10], DA3, DA4
SWAP.SEQ_CST.L3.W32 DA5, [RA12], DA6
FETCH_ADD.RELAXED.L1.W64 DA7, [RA14], DA8
FETCH_AND.ACQ_REL.L4.W64 DA9, [RA20], DA10
```

Bu mnemonic'ler ATOM formatını ve ORDER alanını seçen assembly gösterimleridir; numeric opcode değerleri henüz atanmış değildir.

### 4.11 XFER — Register bankları arası açık aktarım

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

### 4.12 XFER tabanlı sayısal dönüşüm — FCONV

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

### 4.13 BR — PC-relative branch

```text
63       56 55    52 51   48 47   43 42                 32 31          0
+----------+--------+-------+-------+---------------------+--------------+
| OP (8)   |FMT (4) |COND(4)| TEST(5)| RESERVED(11)       | DISP (32)    |
+----------+--------+-------+-------+---------------------+--------------+
```

- TEST, koşullu branch'in okuduğu RA register selector'ıdır. JMP / koşulsuz biçimde TEST alanı ve COND ile ilgili kullanılmayan alanlar sıfır olmalıdır.
- DISP signed 32-bit PC-relative displacement'tır; byte cinsindendir ve komut paketinin ilk word adresine göre yorumlanır. Hedef adres hesaplaması taşma kontrolüne tabidir.
- İlk branch koşulları: ALWAYS, ZERO, NONZERO, SIGNED_LT_ZERO, SIGNED_GE_ZERO. Ayrılmış COND kodları illegal encoding üretir.
- BR.Z ve BR.NZ, TEST register'ının tüm 64-bit değerini sıfırla karşılaştırır. Signed/unsigned zero koşulları aynı bit deseninde eşdeğerdir; ayrı kodlara gerek yoktur.
- Karşılaştırma komutları global flags/condition-code register'ı değiştirmez. CMP.* sonucu hedef RA register'ına 64-bit 0 veya 1 yazar; branch bu register'ı açık operand olarak okur. Bu tasarım multi-issue sırasında global flag write/read çakışmalarını önler.
- TEST selector'ı RA0–RA31 aralığındadır. JMP için TEST=0 ve COND=ALWAYS zorunludur.
### 4.14 SYS — System ve kontrol komutları

SYS formatı privilege, system state, interrupt, synchronization ve özel kontrol komutları için ayrılmıştır. Alt alan yerleşimi her komut sınıfı için ayrı tabloda tanımlanacaktır. Henüz system register bankı veya CSR sayısı kesinleştirilmemiştir.

#### 4.14.1 FENCE — Bellek sıralama bariyeri

FENCE, SYS formatını kullanır. İlk sürümde yalnızca veri bellek domain'lerindeki (L1–L4) normal LOAD/STORE ve ATOM erişimlerini sıralar; P0 komut fetch'i, SPM erişimleri, register işlemleri ve device/MMIO sıralaması bu komutun kapsamı dışındadır.

```text
63       56 55    52 51       44 43    41 40    38 37                 0
+----------+--------+-----------+--------+--------+-------------------+
| OP (8)   |FMT (4) | SYSOP (8) |SCOPE(3)|ORDER(3)| RESERVED (38)     |
+----------+--------+-----------+--------+--------+-------------------+
```

Payload toplamı 52 bittir:
- SYSOP: SYS alt komutunu seçer. FENCE için sembolik alt komut adı `FENCE`; numeric SYSOP değeri henüz atanmadı.
- SCOPE: bariyerin sıraladığı veri bellek domain kapsamı.
- ORDER: bariyer yönü ve ordering strength.
- RESERVED: 38 bitin tamamı sıfır olmalıdır.

**SCOPE kodları**

| SCOPE | Kapsam |
|---:|---|
| 000 | L1 — yalnızca issuing core'un private L1 domain'i |
| 001 | L2 — issuing core'un bağlı olduğu iki-core shared domain |
| 010 | L3 — issuing core'un bağlı olduğu dört-core shared domain |
| 011 | L4 — issuing core'un bağlı olduğu sekizli/geniş shared domain |
| 100 | SYSTEM — issuing core'un erişebildiği tüm L1–L4 data domain'leri |
| 101–111 | Reserved; illegal encoding |

Bir L2/L3/L4 fence, yalnızca seçilen domain'deki erişimleri sıralar; farklı seviyedeki domain'ler arasında sıralama kurmaz. SYSTEM kapsamı birden fazla domain'i kapsayan publish/consume veya koordinasyon akışları içindir ve daha yüksek maliyetli olabilir. Scope, erişim yetkisi veya domain paylaşımını değiştirmez.

**ORDER kodları**

| ORDER | Semantik |
|---:|---|
| 000 | Reserved; RELAXED fence anlamsız olduğundan illegal |
| 001 | ACQUIRE — bariyerden sonraki erişimler, bariyerden önceye taşınamaz |
| 010 | RELEASE — bariyerden önceki erişimler, bariyerden sonraya taşınamaz |
| 011 | ACQ_REL — hem acquire hem release yönü |
| 100 | SEQ_CST — seçilen scope içinde sequentially consistent ordering |
| 101–111 | Reserved; illegal encoding |

- ACQUIRE, bariyerden önceki normal bellek işlemlerini geriye dönük sıralamaz; bariyerden sonraki işlemleri önceye taşımaz.
- RELEASE, bariyerden önceki normal bellek işlemlerinin bariyerden sonraki işlemlerin arkasına taşınmasını engeller.
- ACQ_REL iki yönü de uygular.
- SEQ_CST, seçilen scope içindeki SEQ_CST fence ve SEQ_CST atomic işlemler için tek bir tutarlı sıralama noktası sağlar. Farklı scope'lar arasında ortak bir total order oluşturmaz.
- FENCE atomic değildir; bir bellek konumunu okumaz/yazmaz ve kilit/ownership üretmez.
- FENCE veri kopyalamaz, domain'ler arasında migration yapmaz ve tek başına cache coherence veya erişim izni oluşturmaz. Paylaşılan domain'in visibility/coherence mekanizması ayrıca mimari sözleşmeyi karşılamalıdır.
- FENCE bir bellek erişimi fault'unu geriye dönük olarak değiştirmez; kendi başına adres operandı veya memory access üretmez.

Assembly gösterimi:

```asm
FENCE.ACQUIRE.L2
FENCE.RELEASE.L3
FENCE.ACQ_REL.L4
FENCE.SEQ_CST.SYSTEM
```

Mnemonic suffix'leri SYSOP=FENCE, SCOPE ve ORDER alanlarını belirler. Numeric opcode/SYSOP değerleri opcode tablosu dondurulurken atanacaktır.


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

### 6.1.1 FP komutlarının register bank eşlemesi

- FADD, FSUB, FMUL, FDIV, FMIN ve FMAX gibi üç operandlı scalar FP komutları R3 kullanır; D/A/B alanları FA selector'larıdır.
- FMA dört FA operandı nedeniyle R4 kullanır; D/A/B/C alanları FA selector'larıdır.
- FP32 için W=010, FP64 için W=011, FP128 için W=100 kullanılır. FP128'de her FA selector çift indisli pair başlangıcını göstermelidir.
- FCMP R3 kullanır ancak bank eşlemesi karma ve sabittir: D alanı hedef RA selector'ı, A ve B alanları kaynak FA selector'larıdır. FCMP hedefi 64-bit RA'ya 0 veya 1 yazar; global condition flag yoktur.
- FCMP koşul çeşidi opcode/mnemonic varyantıyla (EQ, NE, LT, LE, GT, GE, ORD, UNORD) belirlenir; R3 içindeki W, karşılaştırılan FP biçimini (FP32/64/128) belirtir.
- FNEG, FABS ve FSQRT tek kaynaklı FP komutlarıdır; ilgili opcode tanımına göre R2 formatı kullanır ve D/A alanları FA selector'larıdır.
- İlk sürümde FADD/FSUB/FMUL/FDIV/FMA/FSQRT/FMIN/FMAX için yuvarlama roundTiesToEven'dır. FCONV'nin kendi ROUND alanı yalnızca dönüşüm işlemini kontrol eder.


### 6.2 MA / 512-bit

- MA kayıtları 256-bit'tir.
- 512-bit ME512 işlemi iki ardışık MA kaydı kullanır.
- Pair başlangıcı çift indisli olmalıdır: MA0:MA1, MA2:MA3, …, MA30:MA31.
- Encoding içindeki MA selector, pair'in ilk kaydını gösterir.
- 512-bit pair komutunda selector'ın LSB biti 0 olmalıdır.

### 6.3 DA / 256-bit transfer grubu

- DA kayıtları 64-bit'tir. XFER içindeki DA selector, çok kayıtlı transferde grubun ilk kaydını gösterir.
- **256-bit DA↔MA transferi:** bir MA kaydı ile dört ardışık DA kaydı kullanılır. DA başlangıcı 4'ün katı olmalıdır: DA0:DA3, DA4:DA7, …, DA28:DA31.
- **512-bit DA↔MA transferi:** çift indisli MA pair'i ve sekiz ardışık DA kaydını kullanır. MA pair başlangıcı çift; DA başlangıcı 8'in katı olmalıdır: DA0:DA7, DA8:DA15, DA16:DA23 veya DA24:DA31.
- 256-bit transferde DA selector 0,4,8,12,16,20,24 veya 28 olabilir. 512-bit transferde yalnızca 0,8,16 veya 24 olabilir.
- Bu grup hizalama kuralları yalnızca XFER ile tam MA register/pair aktarımı içindir. MEM LOAD/STORE için DA selector hizalaması gerektirilmez; orada yalnızca DA31 sınırı kontrol edilir.
- 128-bit ve daha küçük scalar/register transferleri bu MA grup kuralına tabi değildir.

### 6.4 Vector lane encoding

- VADD/VSUB/VMUL/VAND/VOR/VXOR/VSHL/VSHR ve vector compare komutları R3 kullanır; D/A/B alanları MA selector'larıdır.
- VMACC R4 kullanır; D/A/B/C alanları MA selector'larıdır. D accumulator/result register'ıdır; A/B çarpılan lane kaynakları, C accumulator kaynağıdır.
- Vector lane genişliği W alanında kodlanır: W=000/001/010/011/100/101 sırasıyla 8/16/32/64/128/256-bit lane demektir. Bir MA register'ındaki lane sayısı 256/W'dir.
- W=110, normal 256-bit MA vector komutlarında lane genişliği olarak kullanılmaz; 512-bit aggregate/pair komutlarına ayrılmıştır.
- Signed/unsigned karşılaştırma ve bölme varyantları opcode/mnemonic varyantıyla seçilir; register alanlarının yorumu değişmez.
- Vector compare komutlarında D hedef MA, A/B kaynak MA'dır. Sonuç her lane için all-ones/zero mask olarak yazılır.
- Vector bitwise VAND/VOR/VXOR, W alanından bağımsız olarak 256-bit MA register'ının tüm bitlerine uygulanır; assembler W alanını 256-bit (101) kodlar.
- Vector shift komutlarında A kaynak, B lane başına shift-count kaynağıdır; count her lane'in düşük log2(W) bitlerinden değil, lane değerinin düşük bitlerinden alınır ve count >= W ise sonuç sıfırdır.
- Numeric opcode değerleri henüz atanmadı; opcode-family haritası yalnızca önerilen aralıkları gösterir.


### 6.5 Matrix komutlarının encoding eşlemesi

Matrix tile şekli, formatın M alanında; eleman genişliği W alanında kodlanır. D/A/B/C alanları MA tile gruplarının **ilk register selector'larını** taşır. Tile grubunun uzunluğu N ve W'den ISA'da tanımlanan formülle türetilir.

**Tile shape kodları**

| Tile şekli | R3 M[1:0] | R4 M[2:0] |
|---|---|---|
| 2×2 | 00 | 000 |
| 4×4 | 01 | 001 |
| 8×8 | 10 | 010 |
| Ayrılmış | 11 | 011–111 |

**Eleman genişliği W kodları**

| W | Eleman genişliği |
|---|---:|
| 000 | 8 bit |
| 001 | 16 bit |
| 010 | 32 bit |
| 011 | 64 bit |
| 100–111 | Matrix komutlarında ayrılmış |

- 8×8 matrix komutlarında W=011 (64-bit) geçersizdir.
- MMUL.S/U R3 kullanır: D/A/B tile başlangıç selector'larıdır; W eleman genişliğini, M tile şeklini seçer.
- MMAC.S/U R4 kullanır: D/A/B/C tile başlangıç selector'larıdır; W eleman genişliğini, M tile şeklini seçer.
- Signed/unsigned yorumu ayrı opcode varyantıyla seçilir; ek signedness biti kullanılmaz.
- AUX alanı ilk sürümde sıfır olmalıdır. Ayrılmış M/W kodları, sıfır olmayan AUX veya ISA'daki MA grup sınır/alignment kurallarının ihlali illegal operand/encoding fault üretir.
- Register grup uzunluğu `ceil(N × N × W / 256)` MA register'dır. Her başlangıç selector'ı bu grup uzunluğunun katı olmalı ve grup MA31'i aşmamalıdır.
- Operandların aynı tile'ı kullanması tam alias olarak geçerlidir (ör. A=B veya D=A). Kısmi/örtüşen ama eşit olmayan tile grupları geçersizdir.
- Numeric opcode değerleri henüz atanmadı; bu eşleme yalnızca format/operand kodlamasını tanımlar.

Örnek sembolik gösterimler:

```asm
MMUL.S.N4.W16 MA8, MA0, MA4
MMUL.U.N8.W16 MA16, MA0, MA4
MMAC.S.N8.W32 MA24, MA0, MA8, MA16
```

### 6.6 Vector reduction ve matrix transpose encoding

- `VSUM.S/U.W` ve `VDOT.S/U.W` R3 kullanır. D/A/B MA selector'larıdır; W lane genişliğini seçer; M=000 ve AUX=0 zorunludur. VSUM W=8/16/32/64/128/256, VDOT W=8/16/32/64 kabul eder. Signedness opcode varyantıyla belirlenir.
- VSUM ve VDOT sonucu D MA'nın tamamına 256-bit accumulator sonucu olarak yazılır. Signed sonuç sign-extend, unsigned sonuç zero-extend edilir.
- `MTRANS.N2/N4/N8.W` R2 kullanır. D/A tile başlangıç selector'larıdır; W eleman genişliğini, M tile şeklini seçer; AUX=0 zorunludur.
- MTRANS için M=000/001/010 sırasıyla 2×2/4×4/8×8 anlamına gelir. W=000/001/010/011 sırasıyla 8/16/32/64-bit eleman genişliğidir; 8×8 için W=011 geçersizdir.
- MTRANS register grup uzunluğu `ceil(N × N × W / 256)` ile hesaplanır. D/A başlangıç selector'ları bu uzunluğun katı olmalı, grup MA31'i aşmamalıdır. D=A tam alias geçerlidir; kısmi örtüşme geçersizdir.
- Numeric opcode değerleri henüz atanmamıştır.

### 6.7 Matrix reduction encoding

- `MREDUCE.S/U.ROWS/COLS.Nx.Wy` R2 kullanır: D çıktı register grubu başlangıcı, A kaynak matrix tile grubu başlangıcıdır.
- W, kaynak matrix eleman genişliğini; M, N=2/4/8 tile şeklini seçer. M kodları MTRANS ile aynıdır: 000=2×2, 001=4×4, 010=8×8.
- AUX[35] axis alanıdır: 0=ROWS, 1=COLS. AUX[34:0] sıfır olmalıdır. Signedness S/U opcode varyantıyla seçilir.
- Kaynak A register sayısı `ceil(N × N × W / 256)`; hedef D register sayısı `ceil(N × (W + ceil(log2(N))) / 256)` olarak türetilir.
- D ve A grupları kendi uzunluklarına göre hizalanır, MA31'i aşamaz ve birbirleriyle çakışamaz.
- MREDUCE için W=8/16/32/64 geçerlidir; 8×8 için W=64 ayrılmıştır. AUX reserved bit ihlali, geçersiz M/W veya grup sınır/alignment ihlali illegal operand/encoding fault üretir.
- Numeric opcode değerleri henüz atanmadı.

## 7. EXT prefix ve literal genişletme

EXT, bağımsız bir işlem veya hedef opcode'u taşıyan alternatif komut formatı değildir. Normal bir komutun önüne gelen **genişletme prefix'idir**. Bu yaklaşım, aynı literal taşıma mekanizmasının farklı opcode ailelerinde kullanılmasını sağlar.

### 7.1 Komut akışı ve yerleşim

Genişletilmiş komut akışı şu sıradadır:

1. EXT prefix word
2. Normal instruction word (R3, R2, RI, MEM, XFER, BR, SYS veya R4)
3. EXT başlığında belirtilen sayıda 64-bit literal word

Decoder önce EXT başlığını tanır, ardından normal komut word'ünü ve literal word dizisini birlikte toplar. Normal komutun operand alanları hedef register, base register, width ve diğer işlem parametrelerini taşımaya devam eder; literal yalnızca opcode'un tanımladığı immediate/displacement/adres alanını genişletir.

### 7.2 EXT prefix bit yerleşimi

EXT prefix için taslak bit yerleşimi:

```text
63       56 55    52 51    48 47    44 43    40 39                 0
+----------+--------+--------+--------+--------+--------------------+
| OP (8)   | FMT(4) | KIND(4)| COUNT(4)| FLAGS(4)| RESERVED (40)     |
+----------+--------+--------+--------+--------+--------------------+
```

- OP: ayrılmış EXT escape opcode değeri; numeric opcode henüz atanmadı.
- FMT: `0111` (EXT).
- KIND: literal genişletme türü. İlk uygulamada `0000 = RAW_LITERAL`; diğer değerler ayrılmıştır.
- COUNT: takip eden literal word sayısı. `0001` bir adet 64-bit literal word anlamına gelir; `0000` ve henüz tanımlanmamış değerler geçersizdir.
- FLAGS: ilk sürümde sıfır olmalıdır; diğer bit desenleri ayrılmıştır.
- RESERVED: tamamı sıfır olmalıdır.

İlk uygulama tek literal word (`COUNT=1`) ile başlar. Alanın 4 bit olması gelecekte birden fazla literal word desteği için kod alanı bırakır; ancak çoklu literal semantiği henüz tanımlı değildir ve ilk sürümde COUNT=1 dışındaki değerler geçersizdir.

### 7.3 Literal'in yorumlanması

- Literal word, EXT prefix'ini izleyen normal instruction word'ünün ardından gelir.
- Literal word little-endian 64-bit payload'dır; opcode olarak decode edilmez.
- Normal instruction hangi operand alanının literal ile genişletileceğini kendi opcode tanımıyla belirler.
- Literal'in signed/unsigned yorumu, kaydırılması, birleştirilmesi ve hedef genişliği opcode semantiğinde açıkça belirtilmelidir. EXT tek başına bu yorumları belirlemez.
- EXT kullanılmayan normal komutlar mevcut tek-word davranışını korur.
- İlk sürümde her EXT prefix tam olarak bir normal instruction word'üne bağlanır; araya başka prefix veya komut giremez.

### 7.4 Örnek

```asm
; Akışta: EXT prefix, MOVI komutu, 64-bit literal
MOVI64 RA4, 0x123456789ABCDEF0

; Normal tek-word komut
LOAD.L1 DA2, [RA4 + 0]
```

MOVI64 sembolik assembly gösterimidir; temel MOVI opcode'unun literal destekleyen biçimde EXT ile eşleştiğini ifade eder. Bu örnek henüz numeric opcode ataması yapmaz.

### 7.5 Decoder ve kontrol akışı kuralları

- EXT prefix görüldüğünde decoder, takip eden normal instruction word'ünü ve COUNT kadar literal word'ü tek bir komut paketi olarak toplar.
- Komut paketi tamamlanmadan issue aşamasına gönderilmez.
- Literal word'ler instruction olarak decode edilmez ve branch hedefi olarak değerlendirilmez.
- Branch/call/exception dönüş adresi, genişletilmiş paketin son word'ünden sonraki 64-bit komut adresidir.
- EXT prefix, normal instruction veya gerekli literal word'ler kod akışında eksikse komut tamamlanamaz ve instruction-fetch/decode fault oluşur.
- EXT prefix'ten sonra başka bir EXT prefix gelmesi, normal instruction gelmemesi veya ayrılmış alanların sıfır olmaması illegal encoding fault üretir.
- İlk sürümde COUNT yalnızca 1 olabilir.


### 7.6 MOVI — 64-bit immediate yükleme

İlk EXT kullanan opcode örneği olarak `MOVI` seçilir. Komut RI formatını kullanır; EXT'siz ve EXT'li biçimleri aynı mnemonic ailesinin iki kodlama biçimidir.

**RI alan kısıtları**

| Alan | Kural |
|---|---|
| D | Hedef RA0–RA31 selector'ı |
| A | 0 olmalıdır (kullanılmıyor) |
| W | İlk sürümde 64-bit kodu; diğer genişlikler ayrılmıştır |
| M | `000` olmalıdır |
| IMM | EXT yoksa signed 36-bit immediate; EXT varsa sıfır olmalıdır |

**EXT'siz biçim**

- Akış tek RI word'dür.
- IMM, signed 36-bit iki'nin tümleyeni olarak yorumlanır ve 64-bit'e sign-extend edilerek RA[D]'ye yazılır.
- Örnek: `MOVI RA4, -17`.

**EXT'li biçim**

- Akış: EXT prefix (`KIND=RAW_LITERAL`, `COUNT=1`) → MOVI RI word → 64-bit literal word.
- RI word içindeki IMM alanı sıfır olmalıdır; immediate değerin tamamı literal word'dedir.
- Literal, signed sayı olarak yeniden yorumlanmaz veya sign-extend edilmez. 64-bit ham bit deseni doğrudan RA[D]'ye yazılır.
- Bu nedenle literal hem signed hem unsigned yorumlanan değerleri ve tüm 64-bit bit desenlerini kayıpsız temsil eder.
- Örnek: `MOVI RA4, 0x123456789ABCDEF0`; assembler bunu EXT'li üç-word paket olarak üretir. `MOVI64` yazımı, aynı kodlamanın isteğe bağlı açık-genişlik alias'ıdır; ayrı opcode değildir.

Geçersiz durumlar: A≠0, W≠64, M≠000, EXT'li biçimde IMM≠0 veya desteklenmeyen EXT KIND/COUNT kullanımı illegal encoding fault üretir. Fault durumunda hedef RA kaydı değişmeden kalır.


## 8. Opcode alanı ve ilk opcode haritası

OP alanı 8-bit olduğundan 256 primary opcode değeri sunar. İlk aşamada opcode numaralarını aileler halinde ayırmak önerilir:

| OP aralığı | Ayrılan aile | Durum |
|---|---|---|
| 0x00–0x0F | Control-flow / branch | Aile aralığı ayrıldı; bireysel atamalar açık |
| 0x10–0x2F | Integer / scalar ALU | Aile aralığı ayrıldı; bireysel atamalar açık |
| 0x30–0x3F | Bit / Boolean / shift | Aile aralığı ayrıldı; bireysel atamalar açık |
| 0x40–0x4F | Load/store / address | Aile aralığı ayrıldı; bireysel atamalar açık |
| 0x50–0x5F | Floating point / conversion | Aile aralığı ayrıldı; bireysel atamalar açık |
| 0x60–0x83 | Vector / Matrix / ME512 | Alt aile aralığı ayrıldı; aşağıda 0x60–0x82 atandı |
| 0x84–0x93 | Register transfer / bank move | Aile aralığı ayrıldı; bireysel atamalar açık |
| 0x94–0xA3 | SPM access / SPM control | Aile aralığı ayrıldı; bireysel atamalar açık |
| 0xA4–0xC3 | System / synchronization | Aile aralığı ayrıldı; bireysel atamalar açık |
| 0xC4–0xEF | Reserved / future extensions | Ayrılmış |
| 0xF0–0xFF | Escape / EXT / implementation-defined | Ayrılmış; EXT için bireysel değer açık |

Primary opcode, FMT ile birlikte komut tanımını seçer. Aşağıda sayısal değer verilen Vector/Matrix komutları bu revizyonda atanmıştır; diğer ailelerin aralıkları yalnızca rezerve edilmiştir.

### 8.1 Vector ve Matrix primary opcode atamaları

Aşağıdaki değerler bu revizyonla atanmıştır. Her mnemonic varyantı ayrı 8-bit primary opcode kullanır; operand formatı ve W/M alanları ilgili encoding kurallarına göre yorumlanır.

**Vector — 0x60–0x7B**

| OP | Mnemonic | Format | Açıklama |
|---:|---|---|---|
| 0x60 | VADD | R3 | Lane toplama |
| 0x61 | VSUB | R3 | Lane çıkarma |
| 0x62 | VMUL | R3 | Düşük W-bit lane çarpımı |
| 0x63 | VMACC | R4 | Lane çarp-topla |
| 0x64 | VMIN.S | R3 | Signed lane minimum |
| 0x65 | VMIN.U | R3 | Unsigned lane minimum |
| 0x66 | VMAX.S | R3 | Signed lane maximum |
| 0x67 | VMAX.U | R3 | Unsigned lane maximum |
| 0x68 | VAND | R3 | 256-bit bitwise AND |
| 0x69 | VOR | R3 | 256-bit bitwise OR |
| 0x6A | VXOR | R3 | 256-bit bitwise XOR |
| 0x6B | VSHL | R3 | Lane logical left shift |
| 0x6C | VSHR | R3 | Lane logical right shift |
| 0x6D | VSHR.S | R3 | Lane arithmetic right shift |
| 0x6E | VDIV.S | R3 | Signed lane division |
| 0x6F | VDIV.U | R3 | Unsigned lane division |
| 0x70 | VMOD.S | R3 | Signed lane remainder |
| 0x71 | VMOD.U | R3 | Unsigned lane remainder |
| 0x72 | VCMPEQ | R3 | Lane equality mask |
| 0x73 | VCMPNE | R3 | Lane inequality mask |
| 0x74 | VCMPLT.S | R3 | Signed lane less-than mask |
| 0x75 | VCMPLT.U | R3 | Unsigned lane less-than mask |
| 0x76 | VCMPLE.S | R3 | Signed lane less-or-equal mask |
| 0x77 | VCMPLE.U | R3 | Unsigned lane less-or-equal mask |
| 0x78 | VSUM.S | R3 | Signed lane reduction |
| 0x79 | VSUM.U | R3 | Unsigned lane reduction |
| 0x7A | VDOT.S | R3 | Signed lane dot product |
| 0x7B | VDOT.U | R3 | Unsigned lane dot product |

**Matrix — 0x7C–0x82**

| OP | Mnemonic | Format | Açıklama |
|---:|---|---|---|
| 0x7C | MMUL.S | R3 | Signed matrix multiply |
| 0x7D | MMUL.U | R3 | Unsigned matrix multiply |
| 0x7E | MMAC.S | R4 | Signed matrix multiply-accumulate |
| 0x7F | MMAC.U | R4 | Unsigned matrix multiply-accumulate |
| 0x80 | MTRANS | R2 | Tile transpose |
| 0x81 | MREDUCE.S | R2 | Signed row/column reduction |
| 0x82 | MREDUCE.U | R2 | Unsigned row/column reduction |

- 0x83 Vector/Matrix ailesi için ayrılmış genişletme değeridir; ilk sürümde illegal/reserved kabul edilir.
- Vector ve Matrix opcode'larında bank seçimi ayrıca kodlanmaz; operand alanları ISA tanımına göre MA register selector'larıdır.
- MREDUCE için ROWS/COLS seçimi R2 AUX[35] bitindedir; MTRANS için AUX sıfırdır.
- Signed/unsigned varyantlar ayrı primary opcode olduğundan M alanı tile shape, W alanı eleman genişliği için kullanılmaya devam eder.
- Numeric opcode tablosunda bulunmayan bir mnemonic alias yeni opcode oluşturmaz. Alias yalnızca aynı opcode ve operand alanlarına assembler düzeyinde çevrilebilir.
- Bu tablo primary opcode atamasıdır; execution latency, issue portu veya ME512'nin çevrim başına tamamlayacağı iş miktarını belirlemez.

## 9. Decoder ve P0 akışı

- P0 her zaman 64-bit instruction word kayıtları tutar.
- Decoder ilk 64-bit word üzerinden OP ve FMT alanlarını çözer.
- Tek word komutlarda bir P0 kaydı tüketilir.
- EXT kullanan komutlarda prefix, normal instruction ve belirtilen literal word'ler birlikte tüketilir.
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
- EXT paketinin normal instruction word'ünün veya gerekli literal word'lerinin kod belleği/P0 akışında bulunmaması.

Exception türleri, trap vector ve hata raporlama ayrıntıları ayrı system-control bölümünde tanımlanacaktır.

## 11. Örnek alan eşlemeleri

Aşağıdaki örnekler gerçek hexadecimal makine kodu değildir; opcode değerleri henüz atanmadığı için sembolik alan eşlemesidir.

| Assembly | Format | Alanların yorumu |
|---|---|---|
| `ADD RA3, RA1, RA2` | R3 | OP_ADD, FMT_R3, D=3, A=1, B=2, W=64 |
| `FADD FA4, FA1, FA2` | R3 | OP_FADD, FMT_R3, D=4, A=1, B=2, W=FP64 |
| `FCMP.LT RA6, FA1, FA2` | R3 | OP_FCMP_LT, FMT_R3, D=RA6, A=FA1, B=FA2, W=FP64 |
| `VADD.W32 MA8, MA4, MA12` | R3 | OP_VADD, FMT_R3, D=8, A=4, B=12, W=32 |
| `FMA FA4, FA1, FA2, FA3` | R4 | OP_FMA, FMT_R4, D=4, A=1, B=2, C=3, W=FP64 |
| `VMACC.W32 MA8, MA4, MA12, MA16` | R4 | OP_VMACC, FMT_R4, D=8, A=4, B=12, C=16, W=32 |
| `LOAD.L1 DA12, [RA20+16]` | MEM | D=12, BASE=20, W=64, AM=000 (L1), DISP=16 |
| `MOV.FA.DA FA3, DA12` | XFER | DB=FA, DI=3, SB=DA, SI=12, W=64 |
| `MOV.MA.DA MA4, DA0:DA3` | XFER | DB=MA, DI=4, SB=DA, SI=0, W=256 |
| `CAS.ACQ_REL.L2.W64 DA2, [RA10], DA3, DA4` | ATOM | D=2, BASE=10, A=3, B=4, W=64, AM=L2, ORDER=ACQ_REL |

## 12. Henüz dondurulmamış kararlar

- MEMUPD/MEMXUPD ve ATOM opcode numaraları ile assembler mnemonic alias tablosu henüz atanmadı.
- ATOM ordering, scalar 8/16/32/64-bit işlemler ve CAS/SWAP/FETCH_* operand semantiği taslak olarak tanımlandı; fiziksel coherence, arbitration ve bank locking mikro-mimari aşamasında belirlenecek.

1. OP ve FMT sayısal kodlarının nihai tablosu.
3. EXT opcode'unun numeric değeri ve gelecekte COUNT>1 çoklu literal semantiği.
4. DA↔MA 256/512-bit grup hizalaması ISA/encoding düzeyinde tanımlandı; mikro-mimari transfer portları ve timing'i açık.
6. MA/FA pair komutlarının opcode ve exception ayrıntıları.
7. Branch koşul kodları ve displacement'in PC'ye göre referans noktası (komut başlangıcı veya sonraki komut).
8. SYS formatının system register/privilege alanları.
9. Komutlarda predicate/condition alanı gerekip gerekmediği.
10. Reserved bitlerin gelecekteki uyumluluk politikası.
11. FCONV için NaN, infinity, integer overflow ve saturating/trap durumlarının kesin exception sonuçları.
12. FP exception sticky flag'lerinin (FPSR) mimari görünürlüğü ve SYS üzerinden okuma/temizleme komutları.
13. FCMP koşul varyantlarının sayısal opcode ataması; R3 içindeki D=RA, A/B=FA karma bank eşlemesi korunmalıdır.

---

## 13. Tasarım özeti

- Temel instruction word: **64 bit**.
- Primary opcode: **8 bit**.
- Format selector: **4 bit**.
- Register selector: **5 bit** (her bankta 32 kayıt).
- Register bank kodu: **2 bit** (yalnızca genel XFER formatında).
- Immediate: temel RI formatında **signed 36 bit**.
- Memory displacement: MEM için **signed 32 bit**, MEMUPD için **signed 34 bit**, MEMX için **signed 28 bit**, MEMXUPD için **signed 26 bit**, 64-bit RA base ile.
- Otomatik adres güncelleme: MEMUPD/MEMXUPD, POST/PRE increment/decrement; miktar W/8 byte, yalnızca başarılı bellek erişiminde commit.
- MEM domain seçimi: AM[2:1] ile L1/L2/L3/L4; AM[0]=0 base + displacement.
- LOAD/STORE erişim genişliği ve DA grup dağılımı: 8–512 bit; 1/2/4/8 ardışık DA kaydı.
- Branch displacement: **signed 32 bit**.
- Geniş literal: EXT prefix + normal komut + COUNT adet **64-bit literal word**; ilk sürüm COUNT=1.
- P0: 64-bit word kayıtları; EXT paketleri prefix, normal instruction ve COUNT kadar literal word tüketir.

Bu belge, NEXSUS CPU instruction encoding için ilk ortak referanstır. Sayısal opcode değerleri ve açık kararlar kapatıldığında revizyon 1.0 olarak dondurulabilir.