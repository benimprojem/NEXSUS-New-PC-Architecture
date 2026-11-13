# NEXSUS CPU Instruction Set — Execution Unit Table

**Belge:** NEXSUS-CPU-ISA-001  
**Durum:** ISA taslak / komut aileleri ve kaynak eşlemesi  
**Bağlı mimari:** Yeni Nesil Ayrıştırılmış Register Tabanlı CPU Mimarisi

> Bu belge opcode bit kodlamasını henüz sabitlemez. Mnemonic'ler, operand rolleri ve execution-unit eşlemesi için başlangıç tablosudur. Opcode, instruction format, latency, exception ve kesin encoding sonraki ISA revizyonunda netleştirilecektir.

## 1. Çekirdek Execution Unit konfigürasyonu

| Birim | Çekirdek başına | İşlev |
|---|---:|---|
| ALU0 | 1 | Integer / logic |
| ALU1 | 1 | Integer / logic |
| ALU2 | Opsiyonel | 3-ALU çekirdek konfigürasyonu |
| FPU0 | 1 | Floating point |
| FPU1 | 1 | Floating point |
| FPU ekleri | Opsiyonel | 2'den fazla FPU yapılandırması |
| ME512 | 1 | 512-bit Matrix/Vector execution |

2 ALU temel çekirdek; 3 ALU genişletilmiş çekirdek konfigürasyonudur. FPU sayısı minimum 2'dir. ME512 her çekirdekte bir adet hedeflenir.

## 2. Register sınıfları

| Register | Fiziksel yapı | Rol |
|---|---|---|
| RA00–RA63 | 64 × 64-bit | Application/scalar state |
| RBn | RAn alt 32-bit görünümü | 32-bit erişim |
| RCn | RAn alt 16-bit görünümü | 16-bit erişim |
| RDn | RAn alt 8-bit görünümü | 8-bit erişim |
| DA00–DA63 | 64 × 64-bit | Data staging / transfer |
| MA00–MA31 | 32 × 256-bit | Vector/matrix operands |
| SPM0 | 32 KiB; 8 × 4 KiB | 64-bit kayıt-temelli çalışma alanı |
| SPM1 | Sayfalı, byte-addressed | Değişken genişlikli çalışma alanı |

RB/RC/RD yazmalarında etkilenmeyen üst bitlerin korunması mimari tercihidir. Register-view detayları SPM/register dokümanında tanımlanır.

## 3. Scalar / Integer / Logic komutları

| Mnemonic (taslak) | Operand biçimi | İşlev | Unit |
|---|---|---|---|
| MOV | dst, src | Register kopyalama | Register path |
| ADD | dst, src1, src2 | Integer toplama | ALU |
| SUB | dst, src1, src2 | Integer çıkarma | ALU |
| MUL | dst, src1, src2 | Integer çarpma | ALU / multiply pipeline |
| DIV | dst, src1, src2 | Integer bölme | ALU / divide pipeline |
| MOD | dst, src1, src2 | Kalan | ALU / divide pipeline |
| NEG | dst, src | İki'nin tümleyeni işaret değiştirme | ALU |
| INC | dst | +1 | ALU |
| DEC | dst | -1 | ALU |
| CMP | src1, src2 | Karşılaştırma durumu üretme | ALU |
| MIN | dst, src1, src2 | Minimum | ALU |
| MAX | dst, src1, src2 | Maksimum | ALU |
| ABS | dst, src | Mutlak değer | ALU |

## 4. Bit ve Boolean komutları

| Mnemonic | Operand | İşlev | Unit |
|---|---|---|---|
| AND | dst, a, b | Bitwise AND | ALU |
| OR | dst, a, b | Bitwise OR | ALU |
| XOR | dst, a, b | Bitwise XOR | ALU |
| NOT | dst, src | Bitwise NOT | ALU |
| SHL | dst, src, count | Logical left shift | ALU |
| SHR | dst, src, count | Logical right shift | ALU |
| SAR | dst, src, count | Arithmetic right shift | ALU |
| ROL | dst, src, count | Rotate left | ALU |
| ROR | dst, src, count | Rotate right | ALU |
| BSET | dst, bit | Bit set | ALU |
| BCLR | dst, bit | Bit clear | ALU |
| BTST | src, bit | Bit test | ALU |
| BEXT | dst, src, start, width | Bit-field extract | ALU |
| BINS | dst, src, start, width | Bit-field insert | ALU |

## 5. Data transfer ve adres komutları

| Mnemonic | Operand | İşlev | Unit / path |
|---|---|---|---|
| LOAD | dst, [addr] | DATA memory → register | Load/store |
| STORE | [addr], src | Register → DATA memory | Load/store |
| LEA | dst, [base+offset] | Adres hesaplama | ALU |
| MOV.DA | DA, RA/view | Scalar → data register | Register path |
| MOV.RA | RA/view, DA | Data → scalar register | Register path |
| MOV.MA | MA, DA/RA | Operand hazırlama | Matrix data path |
| MOV.DA.MA | MA, DA | Data → MA | Matrix data path |
| MOV.MA.DA | DA, MA | MA → data staging | Matrix data path |
| COPY | dst, src, length | Alan/blok kopyalama | Transfer engine (TBD) |

Memory adres genişliği 64-bit olabilir; register selector genişlikleri bundan bağımsızdır.

## 6. SPM komutları

SPM0 ve SPM1 adresleme birimleri farklıdır. Bu komut isimleri taslak mnemonic'lerdir.

| Mnemonic | Operand | İşlev | Etki |
|---|---|---|---|
| SPM.RD | dst, page, offset | SPM0 64-bit kayıt okuma | SPM → RA/DA |
| SPM.WR | page, offset, src | SPM0 64-bit kayıt yazma | RA/DA → SPM |
| SPM.GET | dst, addr, width, bit | Alan okuma | SPM → register |
| SPM.PUT | addr, src, width, bit | Alan güncelleme | Kısmi write |
| SPM.MASK | addr, mask, value | Maskeli güncelleme | Alan koruma |
| SPM.COPY | dst, src, length | SPM içi kopyalama | SPM transfer |

SPM0 page-id + 64-bit-record offset; SPM1 page-id + byte offset modelini kullanır. 64-bit kayıt içindeki alan güncellemesinde hardware partial-write hedeflenir.

## 7. Floating-point komutları

| Mnemonic | Operand | İşlev | Unit |
|---|---|---|---|
| FADD | dst, a, b | FP toplama | FPU |
| FSUB | dst, a, b | FP çıkarma | FPU |
| FMUL | dst, a, b | FP çarpma | FPU |
| FDIV | dst, a, b | FP bölme | FPU |
| FMA | dst, a, b, c | Fused multiply-add | FPU |
| FNEG | dst, src | FP işaret değiştirme | FPU |
| FABS | dst, src | FP mutlak değer | FPU |
| FSQRT | dst, src | Karekök | FPU |
| FMIN | dst, a, b | FP minimum | FPU |
| FMAX | dst, a, b | FP maksimum | FPU |
| FCMP | a, b | FP karşılaştırma | FPU |
| FCONV | dst, src, type | FP/integer dönüşüm | FPU / conversion path |

Başlangıç formatları FP32 ve FP64'tür. FP128 mimari tür desteği olarak planlanır; donanım desteği/performansı ayrı doğrulanır.

## 8. Vector ve Matrix komutları

MA registerları 256-bit fiziksel genişliktedir. ME512 512-bit yürütme yoludur; iki MA registerı veya tanımlı 512-bit birleşik operand biçimi kullanılabilir.

| Mnemonic | Operand | İşlev | Unit |
|---|---|---|---|
| VADD.W | dst, a, b | Element-wise toplama | ME512 / vector path |
| VSUB.W | dst, a, b | Element-wise çıkarma | ME512 / vector path |
| VMUL.W | dst, a, b | Element-wise çarpma | ME512 / vector path |
| VDIV.W | dst, a, b | Element-wise bölme | ME512 / vector path |
| VMIN.W | dst, a, b | Element-wise min | ME512 / vector path |
| VMAX.W | dst, a, b | Element-wise max | ME512 / vector path |
| VAND.W | dst, a, b | Vector bitwise AND | ME512 / vector path |
| VOR.W | dst, a, b | Vector bitwise OR | ME512 / vector path |
| VXOR.W | dst, a, b | Vector bitwise XOR | ME512 / vector path |
| VSHL.W | dst, a, count | Element shift | ME512 / vector path |
| VSHR.W | dst, a, count | Element shift | ME512 / vector path |
| VMACC.W | dst, a, b, acc | Vector multiply-accumulate | ME512 |
| MMUL | dst, a, b | Matrix multiplication | ME512 |
| MADD | dst, a, b, acc | Matrix multiply-add | ME512 |
| MTRANS | dst, src | Matrix transpose | ME512 / permute path |
| MREDUCE | dst, src, op | Reduction | ME512 |
| MDOT | dst, a, b | Dot product | ME512 |

`W` element width suffix'i 8/16/32/64/128/256-bit format seçimini ifade eder. Matrix operand shape, tile/packing ve accumulation precision ayrı instruction-format alanları olarak tanımlanacaktır.

## 9. Control-flow komutları

| Mnemonic | Operand | İşlev |
|---|---|---|
| JMP | target | Koşulsuz dallanma |
| JZ | target | Zero koşulunda dallanma |
| JNZ | target | Non-zero koşulunda dallanma |
| JC | target | Carry koşulunda dallanma |
| JN | target | Negative koşulunda dallanma |
| CALL | target | Fonksiyon/alt rutin çağrısı |
| RET | — | Çağrıdan dönüş |
| LOOP | counter, target | Döngü kontrolü (taslak) |
| TRAP | code | Trap/exception geçişi |

CALL/RET'nin return state ve parametre yönetimi RA/SPM/context mekanizmasıyla uyumlu kesin biçimi ayrıca tanımlanmalıdır; klasik RAM stack zorunlu kabul edilmez.

## 10. System / synchronization komutları

| Mnemonic | İşlev | Durum |
|---|---|---|
| NOP | İşlem yapmadan ilerleme | Taslak |
| FENCE | Bellek/işlem sıralama bariyeri | Semantik gerekli |
| WAIT | Event/interrupt bekleme | System |
| HALT | Çekirdek durdurma | Privileged |
| SYSCALL | OS/runtime geçişi | Privileged |
| RETSYS | OS/runtime dönüşü | Privileged |
| CSR.RD / CSR.WR | Control/status register erişimi | CSR tasarımı gerekli |
| PREFETCH | Önceden veri getirme | Hint/taslak |

Thread komutları (SPAWN, SEND, RECEIVE/LISTEN, DONE vb.) CPU çekirdek ISA'sına otomatik olarak eklenmez; Thread Runtime/Library ve system interface kapsamında ayrı tasarlanacaktır.

## 11. Instruction dispatch ve paralellik

- Integer/logic komutları ALU0/ALU1 (ve konfigürasyonda ALU2) üzerinde yürütülür.
- FP komutları FPU0/FPU1 (ve ek FPU'lar) üzerinde yürütülür.
- Vector/matrix komutları ME512'ye yönlendirilir.
- LOAD/STORE ve SPM komutları ilgili memory/register path'ine gider.
- Decoder/issue logic bağımsız komutları uygun kaynaklar müsaitse paralel dispatch edebilir.
- Aynı registera yazma, operand dependency, port sayısı ve memory conflict paralelliği sınırlar.

## 12. Açık kalan ISA kararları

1. Opcode ve instruction bit layout.
2. 3-operand/4-operand formatların encoding'i.
3. Flag register mı predicate register mı kullanılacağı.
4. Integer MUL/DIV'nin ALU içi veya ayrı pipeline olması.
5. FP rounding mode, exception ve NaN davranışları.
6. 512-bit ME operand eşleme (2×MA / paired register / özel format).
7. Matrix shape, tile ve accumulation precision.
8. LOAD/STORE alignment ve fault semantics.
9. Branch predictor, pipeline ve issue width.
10. CALL/RET, interrupt ve context-state modeli.
11. FENCE ve memory consistency modeli.
12. SPM erişim port/bank ve atomic/partial-write semantiği.

## 13. İlişkili belgeler

- [CPU ana mimarisi](Yeni%20Nesil%20Ayr%C4%B1%C5%9Ft%C4%B1r%C4%B1lm%C4%B1%C5%9F%20Register%20Tabanl%C4%B1%20CPU%20Mimarisi.md)
- [SPM ve register views](NEXSUS%20CPU%20%E2%80%94%20SPM,%20Register%20G%C3%B6r%C3%BCn%C3%BCmleri%20ve%20Do%C4%9Frudan%20Alan%20Eri%C5%9Fimi.md)
- [NEXSUS PC Architecture README](README.md)


---

## 14. ME512 operand eşleme ve register pair

ME512'nin veri yolu genişliği 512-bit, MA registerlarının fiziksel genişliği 256-bit olarak tanımlıdır. Bu nedenle ISA seviyesinde **MA pair** kullanılacaktır.

### 14.1 Pair kuralı

- `MA00:MA01` → 512-bit birleşik operand (pair index 0)
- `MA02:MA03` → pair index 1
- ...
- `MA30:MA31` → pair index 15
- Pair başlangıcı çift MA index olmalıdır.
- `MA[2p]` düşük 256-bit; `MA[2p+1]` yüksek 256-bit dilim olarak tanımlanır.
- 512-bit sonuç aynı pair'e yazılır.
- Pair içindeki registerlar bağımsız 256-bit işlemlerde de kullanılabilir; pair komutu yürürken pair'in iki registerı o komut tarafından rezerve edilir.

### 14.2 Pair operand biçimi

Matrix/Vector komutları için:
`M512p` = pair index (0..15), fiziksel olarak `MA[2p] + MA[2p+1]`.

Örnek:
`MMUL.M512 MA00:MA01, MA02:MA03, MA04:MA05`

Bu örnek sadece 512-bit operand/result register eşlemesini gösterir; matris shape ve element packing ayrıca opcode/format tarafından belirlenir.

### 14.3 ME512 kaynak kuralı

- Her çekirdekte bir ME512 bulunur; aynı anda bir ME512 komutu yürütür (ilk mikro-mimari hedef).
- Komut issue edildiğinde kaynak ve hedef MA pair'leri operand/result boyunca kilitlenir.
- Aynı pair'e scalar/vector write yapılması hazard çözülene kadar bekletilir.
- ME512 ile ALU/FPU komutları bağımsız register ve kaynaklar kullanıyorsa paralel ilerleyebilir.
- ME512'nin iç tile/accumulator kapasitesi 512-bit dış operand yolundan ayrı bir mikro-mimari konudur.

## 15. Scalar register bank portları ve paralel issue

İlk mikro-mimari için port sayıları **tasarım hedefi** olarak tanımlanır (final silikon gereksinimi değil):

| Register bank | Read port hedefi | Write port hedefi | Açıklama |
|---|---:|---:|---|
| RA (64-bit) | 6 | 3 | 2–3 ALU ve 2 FPU için operand besleme hedefi |
| DA (64-bit) | 4 | 2 | Load/store ve data staging |
| MA (256-bit) | 4 × 256-bit | 2 × 256-bit | ME512 pair ve vector data |
| SPM0 | 2 × 64-bit | 1 × 64-bit | 64-bit record access |
| SPM1 | 2 variable-width | 1 variable-width | Byte/field access; bank implementation TBD |

RA port hedefleri ideal koşulda 3 adet 2-source ALU komutu ve 2-source FPU komutlarını aynı çevrimde beslemeye tek başına yetmez; operand reuse, immediate, bypass ve dispatch sınırlaması gerekir. Bu nedenle tablo **azami port hedefi değil, ilk planlama değeridir**; issue scheduler port/operand kaynaklarına göre komut seçer. RA register rename/physical bank çoğaltma henüz kararlaştırılmadı.

MA'nın 4 read portu, 512-bit pair okumasında iki 256-bit register dilimini birlikte besleme hedefidir. Pair için 2 read port tüketimi varsayılır; iki pair operandı aynı anda okunduğunda 4 port kullanılır. ME512 sonucu pair'e yazarken iki 256-bit write portu tüketir.

## 16. İlk issue modeli (taslak)

- **Integer issue:** 2 komut/çevrim temel (ALU0 + ALU1); 3-ALU çekirdekte 3 komut/çevrim üst hedef.
- **FP issue:** 2 komut/çevrim hedef (FPU0 + FPU1); operand ve port çakışmaları halinde daha az.
- **Matrix issue:** 1 ME512 komut/çevrim; latency çok çevrimli olabilir, pipeline throughput ayrıca belirlenir.
- **Mixed issue:** Integer, FP ve Matrix komutları birbirinden bağımsızsa aynı çevrimde issue edilebilir.
- **Load/store ve SPM:** execution issue'dan bağımsız kaynak sınıfıdır; ancak register portları, address generation ve memory bank çatışmaları toplam throughput'u sınırlar.
- Issue sayıları komut bağımsızlığı, kaynak hazır olma, dependency ve port uygunluğu koşuluna bağlıdır; garanti edilen her-program throughput'u değildir.

## 17. Register conflict / hazard kuralları

1. Aynı çevrimde aynı register'a birden fazla yazma hedefi verilmez; arbitration veya issue rejection gerekir.
2. Bir komutun yazacağı register, aynı çevrimde bağımlı komutun kaynak operandı olarak kullanılamaz; forwarding varsa bypass ile çözülür.
3. RA/RB/RC/RD aynı fiziksel RA registerının görünümüdür; bir view'a yazma diğer view okumalarını günceller.
4. MA pair kullanan ME512 komutu, pair'in iki fiziksel MA registerını komut tamamlanana veya pipeline'ın güvenli release noktasına kadar rezerve eder.
5. SPM read/write port/bank conflict scheduler tarafından çözülür.
6. Load-use, FP dependency, matrix dependency ve memory ordering kuralları pipeline/ISA ayrıntı belgesinde genişletilecektir.

## 18. Açık karar / sonraki tasarım konusu

- RA register bankının multiport maliyeti; banked/replicated/renamed alternatifleri.
- FPU ve ALU operandlarının ortak RA portlarını nasıl kullanacağı; dedicated operand queue/bypass seçenekleri.
- MA pair komutlarının register allocation ve ABI'de nasıl temsil edileceği.
- SPM0/SPM1 fiziksel bank/port düzeni ve aynı cycle erişim.
- ME512 accumulator/tiling ve matrix shape formatı.
- Integer MUL/DIV ve FP DIV/SQRT latency/throughput.
- Precise exception, branch recovery, interrupt/context-save semantiği.


## 19. RA register view / partial-write kesinleştirme

RA, RB, RC ve RD ayrı fiziksel register bankları değildir; aynı 64-bit RA hücresinin genişlik görünümleridir.

| Görünüm | Genişlik | Bit aralığı |
|---|---:|---|
| RA[n] | 64-bit | [63:0] |
| RB[n] | 32-bit | [31:0] |
| RC[n] | 16-bit | [15:0] |
| RD[n] | 8-bit | [7:0] |

### 19.1 Write-mask davranışı

- RA write: 64 bitin tamamını günceller.
- RB write: yalnızca [31:0] güncellenir; [63:32] korunur.
- RC write: yalnızca [15:0] güncellenir; [63:16] korunur.
- RD write: yalnızca [7:0] güncellenir; [63:8] korunur.
- Küçük görünümden okuma, ilgili düşük bitleri zero-extend veya instruction tarafından belirtilen sign-extend ile üretir. Signed/unsigned yorumlama opcode/type bilgisinden gelir; register içeriğini değiştirmez.
- Aynı fiziksel RA hücresine aynı cycle içinde birden fazla view write yapılması yasaktır; scheduler tek yazmayı seçer veya komutları erteler.
- RA write ile aynı hücreye RB/RC/RD write çakışırsa tek sonuç üretilmelidir; öncelik kuralı yerine issue-time conflict rejection tercih edilir.

### 19.2 Operand ve forwarding

- Bir instruction operandını RA[n] üzerinden okur; RB/RC/RD kullanımı yalnızca operand genişliğini ve bit seçimini değiştirir.
- Sonuç yazımı, hedef görünümün write-mask'i ile RA hücresine uygulanır.
- Forwarding/bypass, fiziksel RA hücresine ve write-mask sonucuna göre yapılır; alias isimleri farklı olsa bile dependency aynı hücre üzerinden izlenir.
- Partial-write sonrası aynı RA hücresini okuyan komut, güncel 64-bit birleşik değeri görmelidir.
- Forwarding'in mask merge maliyeti ve latency'si pipeline tasarımında belirlenecek; ISA davranışı bu kurala bağlıdır.

### 19.3 Örnek davranış

Başlangıç: `RA05 = 0x1122334455667788`

- `MOV RB05, 0xAABBCCDD` → `RA05 = 0x11223344AABBCCDD`
- `MOV RC05, 0x1234` → `RA05 = 0x11223344AABB1234`
- `MOV RD05, 0xEF` → `RA05 = 0x11223344AABB12EF`

Bu örnekler little-endian memory byte sıralamasını değil, register bit dilimlerini tanımlar.

## 20. Issue scheduler için RA erişim kuralı

- Her scalar source operand, bir RA read slotu tüketir; immediate/constant operand RA portu tüketmez.
- Aynı RA hücresinin birden fazla komutta okunması, fiziksel read-port implementasyonu destekliyorsa broadcast/reuse ile tek porttan karşılanabilir; bu optimizasyon garanti değildir.
- Scalar destination write, RA bankında bir write slotu tüketir. RB/RC/RD write da aynı slotu tüketir ve maskeli güncelleme gerektirir.
- Aynı cycle içinde aynı RA hücresine iki destination yazılamaz.
- 6 read / 3 write ilk port hedefi sabit issue genişliği garantisi değildir. Scheduler; ALU/FPU komutlarını port sayısı, operand reuse, immediate, bypass ve hedef register çakışmasına göre seçer.
- Register bank replication, operand queue veya ek portlar ileride throughput artırımı için değerlendirilebilir; ISA'nın görünür RA semantiğini değiştirmez.


## 21. SPM erişim ve bank-conflict modeli (ilk taslak)

SPM0 ve SPM1, RA/DA/MA register banklarından ayrı erişim kaynaklarıdır. SPM komutu register operandı kullanıyorsa register portu tüketimi ayrıca hesaba katılır.

### SPM0

- 32 KiB alan, 8 adet 4 KiB page/bank olarak düzenlenir.
- Her page içinde 512 adet 64-bit record bulunur.
- Adres: `(page_id, record_offset)`; record_offset 0..511 aralığındadır.
- İlk erişim hedefi: cycle başına 2 adet 64-bit read ve 1 adet 64-bit write.
- Aynı bankaya aynı cycle içinde birden fazla erişim gelirse port kapasitesi aşan erişimler stall/issue ertelemesine girer.

### SPM1

- Byte-addressed ve değişken genişlikli alan erişimini destekler.
- 8/16/32/64/128-bit erişimlerde alignment ve sayfa sınırı davranışı ayrıca tanımlanacaktır.
- İlk hedef 2 read + 1 write erişimidir; gerçek paralellik bank dağılımına bağlıdır.
- Aynı byte/field üzerinde çakışan write'lar aynı cycle'da issue edilmez.
- Maskeli/partial update, ilgili alan dışındaki bitleri korur.

### Scheduler kuralları

1. SPM read/write port sayısı ve bank conflict, SPM komutlarını sınırlayabilir; ALU/FPU issue'dan bağımsız değildir.
2. SPM read sonucunun aynı cycle'da kullanılması, doğrudan combinational path garantisi değildir; latency/load-use kuralı mikro-mimariyle belirlenecektir.
3. SPM COPY/field işlemleri çok cycle veya transfer engine üzerinden yürüyebilir; tek cycle varsayılmaz.
4. SPM0/SPM1 bank sayısı ve interleave/hash adresleme henüz kesin değildir. Page sayısı ile fiziksel bank sayısı aynı kavram kabul edilmez.

Bu bölüm port hedeflerini tanımlar; kesin timing ve bank mapping sonraki mikro-mimari revizyonda sabitlenecektir.


## 22. Bellek alanı yerleşimi ve preload/residency komutları (taslak)

NEXSUS CPU, programın veriyi yalnızca demand-load ile getirmesine bağlı kalmamalıdır. Programcı belirli bir veri aralığının cache hiyerarşisinde önceden hazırlanmasını isteyebilmelidir. Bunun için L1–L4 hedefli komut ailesi önerilir.

### 22.1 Komut ailesi

| Mnemonic | Amaç | Semantik hedef |
|---|---|---|
| LOAD.L1 | Veri aralığını L1'e almayı iste | Hedef seviye L1 |
| LOAD.L2 | Veri aralığını L2'ye almayı iste | Hedef seviye L2 |
| LOAD.L3 | Veri aralığını L3'e almayı iste | Hedef seviye L3 |
| LOAD.L4 | Veri aralığını L4'e almayı iste | Hedef seviye L4 |
| PREFETCH.L1–L4 | Yakında kullanılacak veri için düşük öncelikli hazırlık | Hint; register sonucu üretmez |
| EVICT.L1–L4 | Belirtilen seviyeden çıkarılmasını iste | Policy/koherens kurallarına tabi |
| CACHE.WAIT | Önceki preload transaction'larının tamamlanmasını bekle | Fence/token ile kapsamlandırılır |

LOAD.Lx, normal LOAD komutunun register'a veri getiren davranışından ayrı bir **cache residency/preload** ailesi olarak ele alınmalıdır. Normal LOAD dst,[addr] ise register'a veri döndürür. Bu isim çakışmasını önlemek için nihai mnemonic'de LOAD.Lx yerine CACHE.LOAD.Lx veya CLLOAD.Lx seçeneği de değerlendirilmelidir; şimdilik LOAD.Lx taslak adıdır.

### 22.2 Operand biçimi

Önerilen soyut biçim:

`LOAD.Lx [base + offset], length, policy`

- base + offset: başlangıç adresi.
- length: hazırlanacak byte aralığı.
- policy: normal, retain, streaming, read-mostly gibi allocation/eviction davranışı.
- Hedef seviye komut suffix'iyle seçilir.

İşlem bir register'a veri döndürmez; cache controller'a bir range transaction gönderir. Tamamlanma durumu CACHE.WAIT veya transaction token üzerinden gözlenir.

### 22.3 Kurallar ve güvenlik

1. İstek cache line granularity'sine yuvarlanır; sınır taşması ve adres overflow kontrol edilir.
2. Range uzunluğu, outstanding transaction sayısı ve aynı anda preload edilebilecek byte miktarı donanım limitlerine tabidir.
3. Cache hierarchy'de istenen seviye bulunmuyorsa implementation-defined fallback uygulanır veya capability/status ile bildirilir; sessizce yanlış seviye garantisi verilmez.
4. L1/L2 çoğunlukla core-private, L3/L4 shared/system-level olabilir; gerçek yerleşim ürün konfigürasyonunda bildirilir.
5. Cache coherence korunur. Preload komutu dirty data'yı kaybetmez ve normal memory ordering kurallarını atlatamaz.
6. Yazılabilir data için başka core/device ile yarış varsa coherence ve ownership protokolü geçerlidir.
7. Preload işlemi normal load gibi architecturally visible register değerini değiştirmez; yalnızca veri hazırlama/placement isteğidir.
8. Bir range'in hedef seviyede kalacağına dair süre garantisi verilmez; kapasite baskısı, coherence, başka erişimler veya replacement policy veriyi çıkarabilir.
9. `CACHE.WAIT` yalnızca belirtilen token/önceki kapsam dahilindeki isteklerin tamamlandığını bildirir; tek başına memory fence yerine geçmez.
10. L2/L3/L4'ün fiziksel bellek organizasyonu ve erişim gecikmeleri sistem konfigürasyonunda tanımlanmalıdır; bunlar otomatik olarak klasik cache seviyeleriyle bire bir aynı kabul edilmez.

### 22.4 Area / Zone ile ilişki

NEXUS Flow'daki `area` ve `zone` tanımları, bu mekanizmanın compiler tarafındaki doğal karşılığı olabilir:

- `area`: yalnızca ilgili çekirdeğin özel L1 alanını hedefler; çekirdek-local çalışma alanı ve lifetime kapsamıdır.
- `zone`: yalnızca çekirdekler arası paylaşılan L2/L3/L4 bellek alanlarını hedefler. SPM veya L1, zone seviyesi olarak kabul edilmez.
- Compiler, scope/lifetime ve erişim örüntüsünden güvenli preload noktaları çıkarabilir.
- Programcı açıkça zone seçtiğinde compiler bunu uygun CACHE.LOAD/PREFETCH komutlarına dönüştürebilir; CPU runtime range ve cache seviyesini kontrol eder.
- `area`/`zone` bildirimi tek başına veri cache'e yüklenmiş demek değildir; gerçek preload, açık komut veya compiler'ın ürettiği operasyonla gerçekleşir.
- Cache seviyesine kalıcı pinning varsayılan davranış olmamalıdır. Gerekirse ayrı, kapasite sınırı olan ve açıkça serbest bırakılan pin/residency mekanizması tasarlanır.

Örnek ISA taslağı:

```asm
LOAD.L2 [RA10 + 0], 4096, RETAIN
CACHE.WAIT
```

Bu örnek 4 KiB aralığı L2'ye hazırlama isteğidir; RA10 base register örnektir. Komut encoding'i, token modeli, line size, maximum range ve policy kodları henüz kesinleşmemiştir.

### 22.5 Açık kararlar

- L1–L4 seviyelerinin NEXSUS platformlarında kesin fiziksel karşılığı.
- Komutun isimlendirmesi: LOAD.Lx mı CACHE.LOAD.Lx mı.
- Synchronous/asynchronous completion ve token sayısı.
- RETAIN/pin davranışı, quota ve release komutları.
- Cache line size, range limit, alignment ve fault reporting.
- Coherence domain ve DMA/device interaction.
- Compiler'ın area/zone bilgisini hangi durumlarda otomatik preload'a çevireceği.


### 22.6 Nexus Flow `area` ve `zone` için kesin görev ayrımı

Önceki genel yorum güncellenmiştir. Nexus Flow'da bu iki yapı aynı işi yapmaz:

| Yapı | Hedef | Kapsam | Temel amaç |
|---|---|---|---|
| `area` | L1 / core-local çalışma alanı | İlgili çekirdek | Çekirdeğin sık ve yakın kullanacağı veriyi yerel alanda tutmak |
| `zone` | L2/L3/L4 shared memory alanları | Birden fazla çekirdek | Çekirdekler arası ortak veri alanı ayırmak ve adres üzerinden paylaşmak |

- `area`, çekirdeğe ait L1 çalışma alanı için derleyiciye yerleşim/lifetime bilgisi verir. `area` başka çekirdeğin doğrudan sahip olduğu L1 alanına ortak bellek muamelesi yapmaz.
- `zone`, paylaşılan bellek hiyerarşisinde bir bölge ayırır. Hangi zone seviyesinin (L2/L3/L4) kullanılacağı açıkça veya politika ile belirlenir.
- Bir çekirdek zone içinde veriyi üretir/yazar; paylaşılabilir adresi diğer çekirdeğe iletir. Alıcı aynı adresi kullanarak veriye erişir. Her paylaşımda payload'ın çekirdek register'larından diğer çekirdeğe tekrar kopyalanması gerekmez.
- Bu model **zero-copy paylaşım / address handoff** yaklaşımıdır. Veri ilk kez zone'a yazılırken elbette bellek yazımı gerçekleşir; ortadan kaldırılan şey çekirdekler arası her seferinde yapılan ayrı payload kopyasıdır.
- Zone adresi, uzunluğu, hizalaması ve erişim hakları bir descriptor/handle ile taşınabilir. Descriptor'ın kendisi küçük bir metadata'dır; veri gövdesi ortak bölgede kalır.
- Zone tahsisi, veri ömrü ve serbest bırakma açık olmalıdır. Son tüketici tamamlamadan alan yeniden kullanılamaz.
- Üretici yazmayı bitirmeden tüketiciye hazır adres yayımlanmamalıdır. Publish/acquire veya eşdeğer release/acquire sıralama semantiği gerekir.
- Birden fazla çekirdek aynı zone'a yazacaksa disjoint range, atomic operation veya açık ownership/lock kuralı gerekir. Aynı byte aralığında kontrolsüz yazma veri yarışı sayılır.
- CPU cache'leri zone verisini cache'leyebilir; ancak çekirdekler arası görünürlük coherence veya açık cache-maintenance + memory-ordering protokolü ile sağlanmalıdır. Sadece adres paylaşmak tek başına yazma görünürlüğünü garanti etmez.
- `zone` paylaşımı veri kopyalamayı gerektirmez; fakat paylaşım güvenliği, lifetime, synchronization ve cache visibility kuralları zorunludur.

### 22.7 Örnek akış (temsili Nexus Flow fikri)

```nexus
area local_work {
    // L1/core-local çalışma verisi
}

zone shared_frame at L3 {
    // L2/L3/L4 paylaşılan bellek alanı; bu örnekte L3
}

// Producer: veriyi shared_frame içine yazar, sonra adres/handle yayımlar.
// Consumer: handle'ı alır ve aynı zone adresinden okur; payload kopyası yoktur.
```

Bu kod yalnızca kavramsal gösterimdir; Nexus Flow'un kesin grammar'ı değildir. CPU ISA tarafında zone allocate/publish/acquire/release ve memory-ordering operasyonlarının opcode/semantiği ayrıca tasarlanacaktır.

### 22.8 LOAD.Lx komut ailesinin yeniden yorumlanması

`LOAD.L1` çekirdek-local L1 area'ya preload/placement isteği olarak kalabilir. `LOAD.L2`, `LOAD.L3`, `LOAD.L4` ise yalnızca klasik cache prefetch komutları olarak değil, hedef shared memory domain'e veri aralığı yerleştirme/tahsis etme komutları olarak ele alınmalıdır. Zone tahsisi ve zone içi veri üretimi birbirinden ayrılmalıdır:

- `ZONE.ALLOC` / `ZONE.FREE`: shared zone alanı tahsis/serbest bırakma.
- `ZONE.PUBLISH`: üreticinin yazmayı bitirdiği aralığı tüketicilere görünür kılma.
- `ZONE.ACQUIRE`: tüketicinin yayımlanmış aralığı güvenli biçimde sahiplenmesi/okumaya hazır hale getirmesi.
- `ZONE.RELEASE`: tüketicinin kullanımını bitirdiğini bildirme; alanın yeniden kullanılabilmesini sağlar.
- `ZONE.ADDR`: descriptor/handle içinden ortak adres ve uzunluk bilgisini alma.

Bunlar şimdilik komut ailesi önerileridir. Normal LOAD/STORE ortak alana gerçek veri okuma/yazma işlemini yapar; ZONE komutları yaşam süresi, sahiplik ve görünürlük yönetir. `LOAD.L2/L3/L4` adlarının tahsis mi, placement mı, yoksa cache residency hint'i mi ifade edeceği bu ayrımla birlikte netleştirilecektir.


### 22.9 Çekirdek sayısına göre paylaşılan bellek topolojisi

Kullanıcının belirlediği temel paylaşım kuralı:

| Bellek seviyesi | Paylaşım kapsamı | Temel yerleşim |
|---|---:|---|
| L1 | 1 çekirdek | Her çekirdeğin kendine ait özel alanı; `area` hedefidir |
| L2 | 2 çekirdek | Her iki çekirdeğin ortak eriştiği zone |
| L3 | 4 çekirdek | Her dört çekirdeğin ortak eriştiği zone |
| L4 | 8 ve üzeri çekirdek | Geniş çekirdek gruplarının / sistemin ortak zone alanı |

- Bu tablo paylaşım kapsamını tanımlar; kapasite, bant genişliği ve gecikme değerleri henüz belirlenmemiştir.
- L2/L3/L4, bu mimaride yalnızca geleneksel cache seviyelerinin isimleri olarak değil, çekirdek gruplarına göre paylaşılan bellek domain'leri olarak ele alınır.
- Birden fazla L2 grubu, daha geniş L3 kapsamı altında; birden fazla L3 grubu da L4 kapsamı altında organize edilebilir. Böylece hiyerarşi, çekirdek sayısı büyüdükçe kademeli paylaşım sağlar.
- L4'ün sekiz çekirdekten daha büyük sistemlerdeki kesin kapsamı (tek global domain mi, birden fazla fabric domain mi) sistem topolojisiyle belirlenecektir.
- `zone` tahsisi hedef seviyeyi belirtir. Aynı zone adresi, o seviyenin erişim kapsamındaki çekirdekler tarafından paylaşılır; kapsam dışındaki çekirdekler için adres/handle aktarımı tek başına erişim yetkisi oluşturmaz.
- Çekirdekler arası veri paylaşımında payload kopyalanmaz; üretici ortak zone'a yazar ve handle/adresi yayımlar. Tüketici aynı ortak bellek konumuna erişir. Publish/acquire, ownership, lifetime ve memory visibility kuralları geçerlidir.
- Daha geniş kapsama ihtiyaç duyulduğunda veri uygun üst seviyedeki zone'a tahsis edilir veya kontrollü biçimde taşınır. Bu yer değiştirme, adresin paylaşılmasıyla otomatik gerçekleşmiş sayılmaz.
- Gerçek donanımda seviyeler ayrı fiziksel banklar, dağıtık bellek dilimleri veya cache destekli ortak domain'ler şeklinde uygulanabilir; ISA görünür semantiği aynı kalır.

Örnek kapsam: 8 çekirdekli bir yapılandırmada her çekirdeğin özel L1'i, çekirdek çiftleri için dört L2 paylaşım alanı, dört çekirdeklik gruplar için iki L3 alanı ve sekiz çekirdeğin erişebildiği bir L4 domain'i bulunabilir. Bu yalnızca topoloji örneğidir; fiziksel bank sayısı ve kapasiteyi sabitlemez.


### 22.10 Ayrık bellek seviyeleri ve kapasite hedefleri

L1/L2/L3/L4 birbirine otomatik bağlı, veriyi kendiliğinden aşağı/yukarı taşıyan tek bir cache zinciri değildir. Her seviye kendi bellek domain'idir. Seviyeler arasında otomatik veri göçü, otomatik cache fill veya donanımın gizli kopyalama davranışı varsayılmaz.

İlk kapasite hedefi, paylaşım domain'i başına:

| Seviye | Domain kapsamı | İlk kapasite hedefi | Not |
|---|---:|---:|---|
| L1 | 1 çekirdek | 128 KiB / çekirdek | En küçük ve en yakın çalışma alanı |
| L2 | 2 çekirdek | 1 MiB / ikili grup | L1'lerden büyük, dar paylaşım |
| L3 | 4 çekirdek | 8 MiB / dörtlü grup | Orta ölçekli ortak veri |
| L4 | 8 çekirdek | 64 MiB / sekizli grup | En büyük ortak domain |

Bu değerler ilk mimari hedeflerdir; nihai silikon kapasitesi değildir. Her basamakta domain başına kapasite 8 kat artırılmıştır. 8'den fazla çekirdekte L4 kapasitesi, sistem topolojisine göre sekizli gruplar veya daha geniş ortak domain'ler halinde ölçeklenebilir. L4'ün tek global domain olması zorunlu değildir.

### 22.11 Seviyeler arası veri aktarımı

- L1, L2, L3 ve L4 fiziksel/mantıksal olarak ayrı bellek domain'leridir; aralarında doğrudan bellek bağlantısı veya otomatik aktarım yolu varsayılmaz.
- Bir verinin bir seviyeden diğerine taşınması gerekiyorsa aktarımı CPU açıkça başlatır ve yönetir.
- Aktarımın kaynak seviyesi, kaynak adresi, hedef seviyesi, hedef adresi ve byte uzunluğu açıkça belirtilir.
- Aktarım tamamlanmadan hedefteki kopya geçerli kabul edilmez. Başarılı tamamlanma, hata ve kısmi aktarım davranışı ISA tarafından raporlanmalıdır.
- Kaynak ve hedef aralıklarının çakışma/alias durumu kontrol edilir. Aynı domain içindeki örtüşen aralıklar için COPY/MOVE semantiği ayrıca tanımlanır.
- Bu işlem çekirdekler arası zero-copy zone paylaşımından farklıdır: aynı zone adresini paylaşmak kopya gerektirmez; farklı Lx domain'ine taşımak ise gerçek bir CPU kontrollü veri aktarımıdır.
- İlk komut taslağı: `XFER dst_level:dst_addr, src_level:src_addr, length`. Komut CPU tarafından yürütülür; ayrı bir DMA motorunun otomatik aktarım yaptığı varsayılmaz. Uygulama bunu çok çevrimli bir CPU memory-operation olarak gerçekleştirebilir.
- İleride büyük aralıklar için isteğe bağlı asynchronous form ve `XFER.WAIT token` eklenebilir. Bu, aktarımın CPU tarafından başlatılması ve kontrol edilmesi ilkesini değiştirmez.

Örnek taslak:

```asm
XFER L3:RA20, L1:RA10, 4096
; 4 KiB veri L1 kaynak aralığından L3 hedef aralığına CPU tarafından taşınır.
```

Buradaki register gösterimleri yalnızca adres operandı örneğidir; kesin operand encoding'i ve transfer buffer/throughput tasarımı henüz sabitlenmemiştir.
