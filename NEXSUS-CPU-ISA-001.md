# NEXSUS CPU Instruction Set — Execution Unit Table

**Belge:** NEXSUS-CPU-ISA-001  
**Durum:** ISA taslak / komut aileleri ve kaynak eşlemesi  
**Bağlı mimari:** Yeni Nesil Ayrıştırılmış Register Tabanlı CPU Mimarisi

> Bu belge mnemonic'leri, operand rollerini ve execution-unit eşlemesini tanımlar. 64-bit komut sözcüğü ve operand alanlarının ilk encoding taslağı ayrı [Instruction Encoding Specification](NEXSUS-CPU-INSTRUCTION-ENCODING-001.md) belgesindedir. Sayısal opcode atamaları ve bazı açık mikro-mimari kararlar henüz dondurulmamıştır. Bellek byte sıralaması little-endian'dır.

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
| RA0–RA31 | 32 × 64-bit | Integer, adres ve scalar state |
| FA0–FA31 | 32 × 64-bit | Floating-point state; FP32/FP64 ve eşli FP128 |
| DA0–DA31 | 32 × 64-bit | Data staging / transfer |
| MA0–MA31 | 32 × 256-bit | Vector/matrix operands |
| RBn | RAn alt 32-bit görünümü | 32-bit integer erişim |
| RCn | RAn alt 16-bit görünümü | 16-bit integer erişim |
| RDn | RAn alt 8-bit görünümü | 8-bit integer erişim |
| SPM0 | 2 KiB; 256 × 64-bit kayıt | Doğrudan adreslenebilir geçici yürütme durumu/sonuç alanı; 8–512-bit erişim |
| SPM1–SPM7 | 8 KiB × 7; byte-addressed | Her biri 8–512-bit erişimli geçici veri alanı |

RA/RB/RC/RD aynı RA fiziksel kaydının alt-bit görünümleridir; küçük görünüm yazmalarında etkilenmeyen üst bitler korunur. FA ayrı fiziksel banktır ve RA view alias'ı değildir. FA'nın FP128 işlemleri çift numaralı başlangıç kaydından başlayan iki kayıtlı pair kullanır. Register ayrıntıları SPM/register dokümanında tanımlanır.

### 2.1 Register bank ve operand kuralları

- RA0–RA31: integer/scalar/address operandları; integer ve bitwise komutların varsayılan bankı.
- FA0–FA31: floating-point operandları; FP32/FP64 tek kayıt, FP128 çift kayıt.
- DA0–DA31: load/store staging ve açık register-bank transferleri.
- MA0–MA31: 256-bit vector/matrix operandları; 512-bit ME512 işlemlerinde çift MA kaydı.
- RBn/RCn/RDn: yalnızca RAn kayıtlarının 32/16/8-bit alt görünümleri; FA/DA/MA için alias değildir.
- Komut mnemonic'i ve operand bankı birlikte operand türünü belirler. Bir bankın operandı başka bankın operandı yerine örtük kullanılamaz.
- FCONV sayısal integer↔floating dönüşümünü yapar; MOV.* transferleri yalnızca tanımlı register bit aktarımı/paketleme işlevlerini yapar.

## 3. Scalar / Integer / Logic komutları

Bu bölümdeki scalar/integer komutlarının kaynak ve hedef operandları RA0–RA31 bankındadır. RB/RC/RD, ilgili RA kaydının 32/16/8-bit alt görünümünü seçer. FA, DA ve MA operandları bu komutların örtük alternatifleri değildir.

| Mnemonic (taslak) | Operand biçimi | İşlev | Unit |
|---|---|---|---|
| MOV | dst, src | Register kopyalama | Register path |\n| MOVI | dst, imm | Signed 36-bit immediate veya EXT ile tam 64-bit literal yükleme | ALU / immediate path |
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
| BEXT | dst, src, start, width | Seçilen bit aralığını çıkarır; sonuç zero-extend edilir | ALU |
| BINS | dst, src, start, width | Kaynağın düşük bitlerini hedefte seçilen aralığa yerleştirir; diğer bitleri korur | ALU |

### 4.1 BEXT / BINS bit-field semantiği

- `start` sıfır tabanlı bit konumudur; `width` 1–64 arası bit sayısıdır.
- `start + width`, seçilen RA görünüm genişliğini (8/16/32/64) aşamaz.
- `BEXT dst, src, start, width`, kaynak alanı hedefin düşük bitlerine çıkarır ve hedefin seçili görünümündeki kalan üst bitleri sıfırlar. İşlem zero-extend eder.
- `BINS dst, src, start, width`, kaynağın düşük `width` bitini hedefte `start` konumuna yerleştirir; hedefin alan dışındaki bitleri korunur.
- Her iki komut R2 formatını kullanır; START ve FIELD_WIDTH, AUX alanındadır. Bit yerleşimi encoding belgesinde tanımlıdır.

## 5. Data transfer ve adres komutları

LOAD ve STORE veri belleği ile DA bankı arasında çalışır. Bellek domain'i her komutta açıkça seçilir; **area** L1'i, **zone** ise paylaşılan L2/L3/L4 alanlarını hedefleyen üst seviye yerleşim/paylaşım kavramlarıdır. LOAD/STORE bir domain'den gerçek veri okur veya yazar; domain'ler arasında otomatik kopyalama yapmaz. Scalar hesaplama için DA'dan RA'ya, floating-point hesaplama için DA'dan FA'ya açık register-transfer komutları kullanılır. FA ile RA arasında sayısal tür dönüşümü FCONV ile yapılır.

| Mnemonic | Operand | İşlev | Unit / path |
|---|---|---|---|
| LOAD.L1 / LOAD.L2 / LOAD.L3 / LOAD.L4 | DA, [addr] | Seçilen veri domain'inden DA register grubuna ham bit okuma | Load/store |
| STORE.L1 / STORE.L2 / STORE.L3 / STORE.L4 | [addr], DA | DA register grubundan seçilen veri domain'ine ham bit yazma | Load/store |
| LEA | RA, [base+offset] | Adres hesaplama | ALU |
| MOV.RA.DA | RA, DA | DA'dan integer/scalar registera açık 64-bit bit aktarımı | Register path |
| MOV.RA.DA.SX / MOV.RA.DA.ZX | RA, DA, W=8/16/32 | DA düşük W bitini RA'nın tam 64-bit değerine signed / zero-extend ederek aktarır | Register path |
| MOV.DA.RA | DA, RA | RA'dan DA staging'e 64-bit aktarım | Register path |
| MOV.FA.DA | FA, DA | DA bitlerini FA kayıt konteynerine aktarma | Register path |
| MOV.DA.FA | DA, FA | FA kayıt bitlerini DA staging'e aktarma | Register path |
| MOV.MA.DA | MA, DA group | 256-bit (1 MA + 4 DA) veya 512-bit (MA pair + 8 DA) veriyi MA'ya yükleme | Matrix data path |
| MOV.DA.MA | DA group, MA | MA'daki 256/512-bit veriyi sırasıyla 4/8 DA kaydına alma | Matrix data path |
| COPY | dst, src, length | Bellek alanı/blok kopyalama | Transfer path (TBD) |

DAx:DAx+3 dört ardışık 64-bit DA kaydını, toplam 256-bit grubu ifade eder. XFER ile 256-bit MA aktarımında DA başlangıç selector'ı 4'ün katı olmalıdır (0,4,…,28). 512-bit MA pair aktarımında sekiz DA kaydı kullanılır; DA başlangıcı 8'in katı olmalıdır (0,8,16,24) ve MA pair başlangıcı çift selector olmalıdır. Bu hizalama yalnızca tam MA register/pair XFER işlemleri içindir. LOAD/STORE'da DA selector ilk kaydı gösterir; W=8/16/32/64 için 1, W=128 için 2, W=256 için 4, W=512 için 8 kayıt kullanılır. MEM erişimlerinde DA başlangıcı için ek selector hizalaması aranmaz; DA aralığının DA31'i aşmaması yeterlidir.

## 5.3 Little-endian bellek ve register-grup sıralaması

NEXSUS CPU, veri belleği ve SPM byte erişimlerinde **little-endian** kullanır. En düşük bellek adresi, çok byte'lı değerin en düşük anlamlı byte'ını taşır.

- 64-bit değerin bit[7:0] alanı en düşük adreste, bit[63:56] alanı en yüksek adreste bulunur.
- 128/256/512-bit LOAD işlemlerinde en düşük adresli 64-bit parça ilk DA kaydına yazılır; sonraki parçalar artan adres sırasıyla artan DA selector'larına yerleştirilir. STORE ters yönde aynı eşlemeyi kullanır.
- FA128 pair'inde düşük anlamlı 64 bit çift indisli ilk FA kaydında, yüksek anlamlı 64 bit sonraki FA kaydındadır.
- 512-bit MA pair'inde düşük anlamlı 256 bit ilk MA kaydında, yüksek anlamlı 256 bit sonraki MA kaydındadır. DA grubu kullanılıyorsa en düşük DA selector'ı en düşük anlamlı 64-bit parçayı tutar.
- 64-bit instruction word'leri bellekten/P0'a little-endian byte sırasıyla alınır. EXT çok sözcüklü komutunda literal word, ana word'ü izleyen daha yüksek adresli word'dür; literal'in byte sıralaması da little-endian'dır.
- Little-endian, register bit numaralandırmasını veya encoding alanlarının mantıksal word içindeki bit konumlarını değiştirmez.

Bu sıralama ISA düzeyinde sabittir; bellek denetleyicisi ve bus byte-lane eşlemesi mikro-mimari uygulama ayrıntısıdır.

### 5.2 DA↔MA çoklu kayıt XFER kuralları

- 256-bit aktarımda bir MA kaydı ile dört DA kaydı eşleşir. DA başlangıcı 4'ün katı olmalıdır: DA0:DA3, DA4:DA7, …, DA28:DA31.
- 512-bit aktarımda çift indisli MA pair'i ile sekiz DA kaydı eşleşir. DA başlangıcı 8'in katı olmalıdır: DA0:DA7, DA8:DA15, DA16:DA23 veya DA24:DA31.
- 256-bit transfer için DA selector değerleri 0,4,8,12,16,20,24,28; 512-bit için 0,8,16,24 ile sınırlıdır.
- 512-bit transferde MA selector pair'in ilk kaydını gösterir ve çift olmalıdır. DA ve MA aralıklarının sonu kendi bank sınırlarını aşamaz.
- Kaynak/hedef yönü hizalama kuralını değiştirmez; hem MOV.MA.DA hem MOV.DA.MA aynı grup kurallarını uygular.
- Bu selector hizalaması LOAD/STORE'a uygulanmaz. Bellek erişiminde doğal byte hizalaması ile DA aralık sınırı ayrı kurallardır.

### 5.1 LOAD/STORE genişlik ve domain semantiği

- W, bellekten okunacak veya belleğe yazılacak tam bit sayısını belirler: 8, 16, 32, 64, 128, 256 veya 512.
- Domain suffix'i hedefi belirler: .L1, .L2, .L3 veya .L4. Bu seçim encoding'de MEM.AM[2:1] alanına karşılık gelir.
- MEM.AM[0]=0, ilk sürümdeki base + signed displacement adresleme biçimidir; diğer adresleme biçimleri ayrılmıştır.
- LOAD ham bitleri DA'ya getirir. 8/16/32-bit yüklemelerde DA kaydının kullanılmayan üst bitleri sıfırlanır; 64-bit ve daha geniş erişimler DA kayıtlarını tam doldurur.
- STORE yalnızca W kadar bit yazar. Son DA kaydında erişim genişliğinin dışında kalan bitler belleğe aktarılmaz.
- LOAD sign-extension yapmaz ve signed/unsigned tür seçmez. DA bir staging bankıdır; scalar tamsayı yorumu gerektiğinde MOV.RA.DA.SX veya MOV.RA.DA.ZX ile açıkça yapılır. SX/ZX kaynak genişliği 8/16/32 bittir ve hedef RA'nın tam 64 bitini yazar; diğer dönüşümler için FCONV kullanılır.
- Geniş erişimlerde ardışık bellek parçaları artan adres sırasıyla ardışık DA selector'larına yerleştirilir. Her 64-bit DA kaydının iç byte sırası little-endian'dır: en düşük adres en düşük anlamlı byte'a karşılık gelir.
- 64-bit effective address, RA[BASE] + signed 32-bit DISP ile hesaplanır. Domain erişim izni, sınır ve hata kontrolleri geçerlidir.
- **Doğal hizalama zorunludur:** effective address, W/8 byte değerine tam bölünmelidir. W=8 her byte adresinde; W=16 2-byte, W=32 4-byte, W=64 8-byte, W=128 16-byte, W=256 32-byte ve W=512 64-byte hizalamada erişilebilir.
- İlk ISA sürümünde misaligned LOAD/STORE desteklenmez ve otomatik split erişim yapılmaz; hizalama ihlali `ALIGNMENT_FAULT` üretir. Unaligned erişim ileride gerekiyorsa ayrı bir opcode/mod olarak tasarlanır.
- `EA + W/8 - 1` 64-bit adres uzayını aşarsa `ADDRESS_OVERFLOW_FAULT`; erişim aralığı seçilen L1/L2/L3/L4 domain sınırını aşarsa `MEMORY_BOUNDS_FAULT` oluşur.
- Erişim izni yoksa `MEMORY_PERMISSION_FAULT`, geçerli bir erişim hedefi/eşlemesi bulunmuyorsa `MEMORY_ACCESS_FAULT` oluşur. Fault komutu başlatan çekirdeğe senkron olarak raporlanır.
- LOAD fault olduğunda hedef DA kayıtları değişmeden kalır. STORE, tüm aralığın sınır ve izin kontrolleri tamamlanmadan commit edilmez; bu kontrollerden biri başarısızsa hiçbir byte yazılmaz.
- 128/256/512-bit erişim tek mimari komuttur; mikro-mimari bunu çoklu beat ile gerçekleştirebilir. Bu durum başka çekirdeklerin eşzamanlı erişimlerine karşı atomicity sağlamaz; gerekli senkronizasyon ayrıca yapılır.

Örnekler (W ve AM alanları semboliktir; gerçek opcode değerleri henüz atanmadı):

~~~asm
LOAD.L1 DA4, [RA10 + 0]       ; 64-bit, DA4
LOAD.L2.W128 DA8:DA9, [RA12 + 16]
LOAD.L3.W256 DA12:DA15, [RA14 + 0]
LOAD.L4.W512 DA16:DA23, [RA18 + 64]

STORE.L1.W32 [RA20 + 4], DA2
STORE.L3.W256 [RA22 + 0], DA12:DA15
~~~

Örnek bank akışı:

```asm
LOAD.L1 DA12, [RA20 + 0]
MOV.RA.DA RA05, DA12
ADD RA06, RA05, RA02

MOV.FA.DA FA03, DA12
FADD FA04, FA03, FA02
FCONV RA07, FA04, i64

MOV.MA.DA MA04, DA00:DA03
VADD.W32 MA08, MA04, MA12
MOV.DA.MA DA04:DA07, MA08
STORE.L1 [RA21 + 0], DA04
```

Bu örnek operand banklarını ve açık transferleri gösterir; kesin opcode encoding'i, erişim genişlikleri ve alignment kuralları ayrı ISA aşamasında sabitlenecektir.

Memory adres genişliği 64-bit olabilir; register selector genişlikleri bundan bağımsızdır.

## 6. SPM komutları

SPM0 kayıt-ofsetiyle, SPM1–SPM7 byte-ofsetiyle adreslenir. Bu komut isimleri taslak mnemonic'lerdir.

| Mnemonic | Operand | İşlev | Etki |
|---|---|---|---|
| SPM.RD | dst, addr | SPM alanından genişliği belirtilen veri okuma | SPM → RA/FA/DA/MA (uygun genişlikte) |
| SPM.WR | addr, src, width | SPM alanına 8–512-bit veri yazma | RA/FA/DA/MA → SPM (uygun genişlikte) |
| SPM.GET | dst, addr, width, bit | Alan okuma | SPM → register |
| SPM.PUT | addr, src, width, bit | Alan güncelleme | Kısmi write |
| SPM.MASK | addr, mask, value | Maskeli güncelleme | Alan koruma |
| SPM.COPY | dst, src, length | SPM içi kopyalama | SPM transfer |

SPM0, 256 adet 64-bit temel kayıt üzerinden doğrudan adreslenir; SPM1–SPM7 ise her biri 8 KiB byte-addressed alandır. Tüm SPM alanları 8/16/32/64/128/256/512-bit veri erişimlerini destekler. Geniş erişimler gerektiğinde ardışık temel kayıtları veya byte konumlarını kapsar; alignment ve sınır davranışı mimari kurallarla denetlenir.

## 7. Floating-point komutları

Bu bölümdeki tüm FP kaynak ve hedef operandları FA0–FA31 bankındadır. FP32 ve FP64 değerler tek FA kaydında tutulur. FP128 değerler iki ardışık FA kaydını kullanır; pair başlangıcı çift indisli olmalıdır (FA00:FA01, FA02:FA03, …, FA30:FA31). Pair'in düşük 64 biti ilk kayıtta, yüksek 64 biti sonraki kayıttadır. Tek FA kaydına yazan FP32/FP64 işlemleri pair'in diğer kaydını etkilemez.

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
| FCONV | dst, src, src_type, dst_type | RA ↔ FA arasında sayısal integer/floating dönüşümü; türler açıkça belirtilir | FPU / conversion path |

FCONV, RA'daki integer değeri FA formatına veya FA'daki floating-point değeri RA integer formatına dönüştürür; kaynak/hedef bankı operandlarda açıkça belirtilir. Başlangıç formatları FP32 ve FP64'tür. FP128, FA pair biçimiyle ISA'da desteklenir; gerçek FPU throughput ve latency mikro-mimari doğrulamasına tabidir.

## 8. Vector ve Matrix komutları

Bu bölümdeki vektör/matris kaynak ve hedef operandları MA0–MA31 bankındadır. DA yalnızca açık veri hazırlama/çıkarma transferinde kullanılır.

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

### 11.1 Dört register operandlı komutların encoding eşlemesi

Aşağıdaki komutlar tek instruction word içinde `R4` formatını kullanır; dördüncü operandı kaybetmek veya komutu yazılımsal olarak iki komuta bölmek gerekmez:

| Komut | Encoding | Operand eşlemesi |
|---|---|---|
| `FMA dst, a, b, c` | R4 | D=dst, A=a, B=b, C=c (FA bankı) |
| `VMACC.W dst, a, b, acc` | R4 | D=dst, A=a, B=b, C=acc (MA bankı) |
| `MADD dst, a, b, acc` | R4 | D=dst, A=a, B=b, C=acc (MA bankı) |

R4 alan yerleşimi ve FMT kodu `NEXSUS-CPU-INSTRUCTION-ENCODING-001.md` belgesinde tanımlanır. Pair kullanan MA/FA operandlarında selector, pair'in ilk (çift indisli) kaydını gösterir. R4 kullanılması komutun tek çevrimde tamamlanacağı anlamına gelmez.

### 7.1 FCONV register ve tür eşlemesi

`FCONV` kaynak ve hedef register banklarını encoding içinde açıkça belirtir. Kaynak/hedef bank yalnızca RA veya FA olabilir:

- `FCONV FA3, RA7, i64, f64`: RA7'deki signed 64-bit integer değerini FA3'e FP64 olarak dönüştürür.
- `FCONV RA7, FA3, f64, i32`: FA3'teki FP64 değeri signed 32-bit integer'a dönüştürerek RA7'nin alt 32-bit görünümüne yazar.
- `FCONV FA4:FA5, RA8, i64, f128`: RA8'deki signed 64-bit integer değerini FP128'e dönüştürüp FA4:FA5 pair'ine yazar.

`FCONV` bir bit aktarımı değildir; `MOV.RA.DA` veya `MOV.FA.DA` ile aynı semantiğe sahip değildir. Encoding alanları, tür kodları, rounding ve conversion flags `NEXSUS-CPU-INSTRUCTION-ENCODING-001.md` içindeki FCONV alt bölümünde tanımlanır. FP128 kullanıldığında FA pair başlangıcı çift indisli olmalıdır.

## 12. Açık kalan ISA kararları

1. Numeric opcode atamaları ve instruction bit layout'unun dondurulması.
2. R4 dışındaki özel/karma operandların (özellikle FCONV, bit-field ve system komutları) kesin encoding'i.
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

- [Instruction Encoding Specification — 64-bit komut kodlaması](NEXSUS-CPU-INSTRUCTION-ENCODING-001.md)
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

## 15. Register bank portları ve paralel issue

İlk mikro-mimari için port sayıları **tasarım hedefi** olarak tanımlanır (final silikon gereksinimi değil):

| Register bank | Read port hedefi | Write port hedefi | Açıklama |
|---|---:|---:|---|
| RA (32 × 64-bit) | 4 × 64-bit | 2 × 64-bit | Integer ALU operandları ve scalar/adres state |
| FA (32 × 64-bit) | 4 × 64-bit | 2 × 64-bit | İki FPU için FP operandları; FP128 pair iki kayıt dilimi tüketir |
| DA (32 × 64-bit) | 4 × 64-bit | 2 × 64-bit | Load/store ve açık data staging |
| MA (32 × 256-bit) | 4 × 256-bit | 2 × 256-bit | ME512 pair ve vector data |
| SPM0 | 2 × 64-bit | 1 × 64-bit | 64-bit temel kayıt erişimi; 8–512-bit geniş erişimler çok kayıtlı olabilir |
| SPM1–SPM7 | 2 variable-width | 1 variable-width | 8–512-bit byte/field access; bank implementation TBD |

RA ve FA artık ayrı fiziksel banklardır; FPU operandları FA'dan, ALU operandları RA'dan beslenir. Her bank için 4 read / 2 write portu ilk planlama hedefidir; bu değer sabit issue garantisi değildir. Scheduler operand sayısı, pair erişimi, bypass ve hedef çakışmalarına göre komut seçer. Fiziksel bank çoğaltma/rename henüz kararlaştırılmadı.

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
3. RA/RB/RC/RD aynı fiziksel RA registerının görünümüdür; bir view'a yazma diğer view okumalarını günceller. FA ayrı banktır; FA pair işlemleri iki FA kaydına bağımlılık ve write-hazard oluşturur.
4. MA pair kullanan ME512 komutu, pair'in iki fiziksel MA registerını komut tamamlanana veya pipeline'ın güvenli release noktasına kadar rezerve eder.
5. SPM read/write port/bank conflict scheduler tarafından çözülür.
6. Load-use, FP dependency, matrix dependency ve memory ordering kuralları pipeline/ISA ayrıntı belgesinde genişletilecektir.

## 18. Açık karar / sonraki tasarım konusu

- RA ve FA banklarının multiport maliyeti; banked/replicated/renamed alternatifleri.
- FA pair erişimlerinin port, hizalama ve forwarding maliyeti.
- MA pair komutlarının register allocation ve ABI'de nasıl temsil edileceği.
- SPM0/SPM1–SPM7 fiziksel bank/port düzeni ve aynı cycle erişim.
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

SPM0 ve SPM1–SPM7, RA/DA/MA register banklarından ayrı erişim kaynaklarıdır. SPM komutu register operandı kullanıyorsa register portu tüketimi ayrıca hesaba katılır.

### SPM0

- Toplam kapasite 2 KiB'tır ve 256 adet 64-bit temel kayıt içerir.
- Adresleme doğrudan kayıt ofsetiyle yapılır: `record_offset` 0..255.
- 8/16/32-bit alan erişimleri 64-bit temel kayıt içindeki byte/bit alanlarını; 128/256/512-bit erişimler ise gerektiğinde ardışık temel kayıtları kapsar.
- İlk erişim hedefi: cycle başına 2 adet 64-bit read ve 1 adet 64-bit write.
- Aynı bankaya aynı cycle içinde birden fazla erişim gelirse port kapasitesi aşan erişimler stall/issue ertelemesine girer.

### SPM1–SPM7

- Her alan 8 KiB kapasitelidir; yedi alanın toplamı 56 KiB'tır.
- Byte-addressed ve değişken genişlikli alan erişimini destekler.
- 8/16/32/64/128/256/512-bit erişimlerde alignment ve alan sınırı davranışı ayrıca tanımlanacaktır.
- İlk hedef 2 read + 1 write erişimidir; gerçek paralellik bank dağılımına bağlıdır.
- Aynı byte/field üzerinde çakışan write'lar aynı cycle'da issue edilmez.
- Maskeli/partial update, ilgili alan dışındaki bitleri korur.

### Scheduler kuralları

1. SPM read/write port sayısı ve bank conflict, SPM komutlarını sınırlayabilir; ALU/FPU issue'dan bağımsız değildir.
2. SPM read sonucunun aynı cycle'da kullanılması, doğrudan combinational path garantisi değildir; latency/load-use kuralı mikro-mimariyle belirlenecektir.
3. SPM COPY/field işlemleri çok cycle veya transfer engine üzerinden yürüyebilir; tek cycle varsayılmaz.
4. SPM0/SPM1–SPM7 bank sayısı ve interleave/hash adresleme henüz kesin değildir. Mantıksal kayıt/byte adresleri fiziksel bank sayısıyla aynı kavram kabul edilmez.

Bu bölüm port hedeflerini tanımlar; kesin timing ve bank mapping sonraki mikro-mimari revizyonda sabitlenecektir.


## 22. Ayrık veri bellekleri, yerleşim ve aktarım komutları (taslak)

NEXSUS CPU, programın veriyi yalnızca demand-load ile getirmesine bağlı kalmamalıdır. Programcı belirli bir veri aralığının cache hiyerarşisinde önceden hazırlanmasını isteyebilmelidir. Bunun için L1–L4 hedefli komut ailesi önerilir.

### 22.1 Bellek alanlarının komut modeli

L1–L4, klasik otomatik cache zinciri değil, birbirinden ayrı veri belleği domain'leridir. Bu nedenle eski `LOAD.Lx`, `PREFETCH.Lx` ve `EVICT.Lx` taslağı otomatik cache doldurma/boşaltma anlamında kullanılmayacaktır.

- `LOAD` ve `STORE`, komutun adreslediği bellek domain'inde gerçek veri okuma/yazma işlemini yapar.
- `XFER`, iki ayrı domain arasında CPU tarafından açıkça istenen veri aktarımıdır.
- `area` ve `zone`, programlama dili/derleyici düzeyinde yerleşim ve paylaşım kapsamını belirtir; kendi başlarına gizli veri kopyalama başlatmaz.
- Bellek domain'leri arasında otomatik terfi, düşürme, cache fill veya migration yoktur.

### 22.2 Bellek adresleme biçimi

Bellek operandı, hedef domain'i ve o domain içindeki adresi açıkça belirtir. Örnek gösterim:

```text
LOAD.L1 DA4, [RA10 + 0]
STORE.L2 [RA20 + 0], DA4
```

Burada RA10/RA20 ilgili bellek adresini tutan register'lardır; köşeli parantez bellek erişimini ifade eder. Kesin makine kodu alanları ve adresleme modları kodlama aşamasında belirlenecektir.

### 22.3 Ayrık domain kuralları

1. L1 her çekirdeğe özel, L2 iki çekirdeğe, L3 dört çekirdeğe ve L4 sekiz veya daha geniş çekirdek grubuna açık domain'dir.
2. L1–L4 arasında doğrudan bellekten belleğe otomatik bağlantı veya otomatik aktarım varsayılmaz.
3. Bir domain'deki adres başka bir domain'de aynı içeriğin bulunduğu anlamına gelmez.
4. Domain'ler arası kopyalama CPU tarafından yürütülen açık bir `XFER` işlemiyle yapılır.
5. Paylaşılan domain'lerde senkronizasyon, erişim izni, sahiplik ve veri görünürlüğü kuralları ayrıca geçerlidir.
6. Program komut belleği P0, veri belleklerinden ayrıdır; komut fetch yolu P0'a, normal veri LOAD/STORE yolları ise seçilen veri domain'ine yönelir.
7. P0 ile L1–L4 arasında da otomatik kopyalama veya veri göçü yoktur. Kodun veri alanına veya verinin komut alanına taşınması gerekiyorsa açık CPU talimatlarıyla yapılır.

### 22.4 Area / Zone ile ilişki

NEXUS Flow'daki `area` ve `zone` tanımları, bu mekanizmanın compiler tarafındaki doğal karşılığı olabilir:

- `area`: yalnızca ilgili çekirdeğin özel L1 alanını hedefler; çekirdek-local çalışma alanı ve lifetime kapsamıdır.
- `zone`: yalnızca çekirdekler arası paylaşılan L2/L3/L4 bellek alanlarını hedefler. SPM veya L1, zone seviyesi olarak kabul edilmez.
- Compiler, scope/lifetime ve erişim örüntülerini yerleşim ve kod optimizasyonu için kullanabilir; bu bilgi tek başına bellek aktarımı başlatmaz.
- `area`/`zone` bildirimi veriyi otomatik olarak L1–L4'e taşımaz veya LOAD işlemi üretmez.
- Programın açıkça istediği veri okuma/yazma işlemi LOAD/STORE ile; farklı domain'e gerçek kopyalama ise XFER ile gerçekleştirilir. Compiler yalnızca bu açık semantiği koruyan komutlar üretir.
- Cache seviyesine kalıcı pinning varsayılan davranış olmamalıdır. Gerekirse ayrı, kapasite sınırı olan ve açıkça serbest bırakılan pin/residency mekanizması tasarlanır.

Örnek ISA taslağı:

```asm
LOAD.L2 [RA10 + 0], 4096, RETAIN
CACHE.WAIT
```

Bu örnek 4 KiB aralığı L2'ye hazırlama isteğidir; RA10 base register örnektir. Komut encoding'i, token modeli, line size, maximum range ve policy kodları henüz kesinleşmemiştir.

### 22.5 Açık kararlar

- L1–L4 seviyelerinin NEXSUS platformlarında kesin fiziksel karşılığı.
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

### 22.8 Eski preload komutlarının durumu

Önceki taslaktaki `LOAD.Lx [addr], length, RETAIN` biçimindeki range-preload işlemi ile `PREFETCH.Lx` ve `EVICT.Lx` residency komutları ISA kapsamından çıkarılmıştır. Bunlar, burada tanımlanan `LOAD.L1–L4 DA, [addr]` gerçek veri okuma komutlarıyla aynı işlem değildir. Gerçek LOAD/STORE yalnızca seçilen domain'e erişir; başka bir domain'e kopyalama gerekiyorsa açık `XFER` kullanılır.

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

### 22.11 Bellek domain'leri arasında CPU kontrollü veri aktarımı

- L1, L2, L3 ve L4 fiziksel/mantıksal olarak ayrı bellek domain'leridir; aralarında doğrudan bellek bağlantısı veya otomatik aktarım yolu varsayılmaz.
- Bir verinin bir seviyeden diğerine taşınması gerekiyorsa aktarımı CPU açıkça başlatır ve yönetir.
- Aktarımın kaynak seviyesi, kaynak adresi, hedef seviyesi, hedef adresi ve byte uzunluğu açıkça belirtilir.
- Aktarım tamamlanmadan hedefteki kopya geçerli kabul edilmez. Başarılı tamamlanma, hata ve kısmi aktarım davranışı ISA tarafından raporlanmalıdır.
- Kaynak ve hedef aralıklarının çakışma/alias durumu kontrol edilir. Aynı domain içindeki örtüşen aralıklar için COPY/MOVE semantiği ayrıca tanımlanır.
- Bu işlem çekirdekler arası zero-copy zone paylaşımından farklıdır: aynı zone adresini paylaşmak kopya gerektirmez; farklı Lx domain'ine taşımak ise gerçek bir CPU kontrollü veri aktarımıdır.
- `XFER`, CPU'nun başlattığı çok çevrimli bir aktarım işlemidir. Aktarım sabit boyutlu/ sınırlı beat'ler halinde ilerler; tek çevrimde tüm aralığın taşınması gerekmez.
- CPU, aktarım beat'lerini kaynak domain'den okuyup hedef domain'e yazar. Ayrı ve bağımsız bir DMA motoru varsayılmaz.
- Aktarım devam ederken kaynakları çakışmayan ALU/FPU/ME işlemleri yürütülebilir. Bellek portu, register veya bağımlılık çakışması varsa ilgili işlem bekler.
- Büyük/asenkron aktarım için `XFER.START` bir token üretir; `XFER.WAIT token` ilgili aktarım tamamlanana kadar bekler. Bağımlı kod, aktarım tamamlanmadan hedef veriyi kullanmamalıdır.

Örnek taslak:

```asm
XFER L3:[RA20], L1:[RA10], 4096
; RA10 kaynak adresini, RA20 hedef adresini tutar.
; 4 KiB veri L1'den L3'e CPU kontrollü olarak aktarılır.
```

Buradaki register gösterimleri yalnızca adres operandı örneğidir; kesin operand encoding'i ve transfer buffer/throughput tasarımı henüz sabitlenmemiştir.


### 22.12 P0 program komut ön belleği ve sabit komut genişliği

P0, App RAM'deki program kodundan komutları instruction-fetch birimine hazır tutan, L1–L4 veri belleklerinden ayrı bir **komut ön belleği (instruction cache)** domain'idir. Programın ana kodu App RAM'de bulunur; P0 yürütülmekte olan bölümü yakın ve hızlı erişim için tutar. Uygulama verileri ayrı Data RAM alanındadır.

- P0 kayıt genişliği **her zaman 64 bit**tir. Her kayıt tek bir 64-bit komut sözcüğüdür; komut adresleri 8-byte hizalıdır.
- Standart kapasite **8 KiB / çekirdek**tir: 1.024 komut kaydı.
- Donanım yapılandırmasıyla **16 KiB / çekirdeğe genişletilebilir**: 2.048 komut kaydı. 8 KiB temel, 16 KiB genişletilmiş konfigürasyondur.
- App RAM'den P0'a komut getirme/refill işlemini instruction-fetch donanımı yapar. Programın tamamının P0'a sığması gerekmez; komut akışı ihtiyaç oldukça beslenir.
- P0 miss olduğunda gerekli komut sözcüğü veya komut bloğu App RAM'den getirilir. Fetch line/block boyutu mikro-mimari aşamasında belirlenir.
- Dallanma, çağrı/dönüş veya exception sonrasında fetch yeni adrese yöneltilir. Yanlış yoldan getirilmiş, henüz yürütülmemiş komutlar iptal edilir; P0'daki tüm geçerli içeriğin silinmesi zorunlu değildir.
- P0, L1–L4 veri belleğinin parçası değildir ve normal veri LOAD/STORE alanı olarak kullanılamaz.
- App RAM kod alanı ile Data RAM ayrıdır. Çalışma sırasında kod değişikliği için P0 tutarlılığı, yürütme izni ve fetch senkronizasyonu ayrıca korunmalıdır.

### 22.13 P0 ve SPM0 görev ayrımı

P0 ile SPM0 farklı aşamalara hizmet eder ve birbirinin yerine geçmez:

| Bellek | İşlev | Kayıt genişliği | Kapasite |
|---|---|---:|---:|
| P0 | App RAM'den komut fetch eden ön bellek | 64 bit sabit | 8 KiB standart; 16 KiB genişletilebilir / çekirdek |
| SPM0 | Yürütme sırasında oluşan geçici komutsal durum, ara değerler ve sonuçlar | 64-bit temel kayıt; 8–512-bit erişim | 2 KiB / çekirdek |

- P0, sıradaki komutları fetch aşamasında hazır tutar.
- SPM0, CPU çalışırken yürütme sırasında oluşan geçici komutsal durumu, ara değerleri ve sonuçları tutar. Stack benzeri geçici saklama alanıdır; ancak zorunlu LIFO düzeni yoktur ve doğrudan adreslenir.
- SPM0 toplam 2 KiB'tır; 256 adet 64-bit temel kayıt içerir. 8–512-bit erişimler gerektiğinde bir veya daha fazla temel kaydı kapsayabilir.
- SPM1–SPM7, her biri 8 KiB olmak üzere toplam 56 KiB doğrudan adreslenebilir veri çalışma alanı sağlar; geçici veriler ve ara hesaplama değerlerini tutar.
- P0 yalnızca App RAM'den komut fetch eder; SPM0'a komut kuyruğu veya komut kopyası aktarılmaz.

Fetch genişliği, branch davranışı, miss oranı ve komut besleme bant genişliği ölçüldükten sonra P0'ın bank sayısı, line size, refill genişliği ve portları mikro-mimari aşamasında belirlenecektir.


### 22.14 P0 fetch bant genişliği ve komut besleme hedefi

Komut kaydı genişliği ile P0'ın fetch veri yolu genişliği birbirinden ayrıdır:

- Tek komut kaydı 64 bit olarak kalır.
- İlk mikro-mimari hedefi P0 ile fetch/decode tarafı arasında **512-bit (8 komut sözcüğü) tepe okuma genişliği** sağlamaktır.
- Bu genişlik her çevrimde sekiz komutun yürütüleceği anlamına gelmez. Issue scheduler, ilk hedefte en fazla 2 ALU + 2 FPU + 1 ME512 olmak üzere beş bağımsız execution komutunu aynı çevrimde dağıtabilir; gerçek sayı bağımlılık ve kaynak uygunluğuna bağlıdır.
- Fetch tarafındaki fazla komutlar decode/dispatch akışında sıraya alınır; SPM0 yürütme tarafındaki geçici komut kayıtlarını tutar.
- 512-bit hedef, P0'ın her çevrim mutlaka tam dolu okunacağı garantisi değildir. Branch, P0 miss, hizalama, port ve App RAM gecikmesi gerçek besleme hızını etkiler.
- 512-bit fetch genişliği ilk tasarım hedefidir; güç/alan/performans analizleriyle daraltılabilir veya artırılabilir. P0 kapasitesi ve 64-bit kayıt biçimi bundan bağımsızdır.


### 22.15 EXT prefix ve genişletilmiş komut paketi

EXT, normal komutun önüne gelen bir prefix'tir; hedef opcode'un veya operandların yerine geçmez. Genişletilmiş komut akışı sırasıyla EXT prefix word, normal instruction word ve prefix'te belirtilen literal word dizisinden oluşur.

- EXT prefix, literal türünü ve literal word sayısını bildirir. İlk sürümde yalnızca bir adet 64-bit literal word desteklenir.
- Normal instruction word hedef register, kaynak register, width, addressing mode ve opcode'a ait diğer alanları taşır.
- Literal word, normal komutun opcode semantiğinde tanımlanan immediate, displacement veya adres bileşenini genişletir. Signed/unsigned yorum ve literal'in operandla birleştirilme kuralı ilgili opcode tarafından belirlenir.
- Decoder tüm paketi toplamadan komutu issue aşamasına göndermez. Literal word hiçbir koşulda bağımsız instruction olarak decode edilmez.
- Paket içindeki son literal word'den sonraki adres, sıradaki komut adresidir. Branch/call/exception dönüş adresi bu paket sonuna göre hesaplanır.
- Prefix, normal komut veya literal eksikse instruction-fetch/decode fault oluşur. Ayrılmış alanların sıfır olmaması, geçersiz COUNT veya prefix'in ardından başka bir EXT prefix gelmesi illegal encoding fault üretir.
- EXT kullanılmayan komutlar tek 64-bit word olarak kalır; normal komutların kodlanması ve yürütülmesi değişmez.

Bu mekanizma MOVI64 gibi geniş sabit yükleme işlemlerinin yanı sıra, ileride opcode bazında tanımlanacak geniş displacement ve adres operandları için de ortak taşıma yolu sağlar. Numeric EXT opcode değeri ve opcode başına literal yorumları ISA taslağında henüz dondurulmamıştır.


### 3.1 MOVI immediate yükleme semantiği

`MOVI RA[d], imm`, RA hedef register'ına sabit değer yükler.

- EXT kullanılmayan biçimde RI formatındaki signed 36-bit immediate 64-bit'e sign-extend edilir.
- Tam 64-bit sabit gerektiğinde assembler, `EXT → MOVI RI → 64-bit literal` paketini üretir. EXT prefix `RAW_LITERAL` ve `COUNT=1` kullanır.
- EXT'li biçimde RI.IMM alanı sıfırdır ve literal'in 64-bit ham bit deseni doğrudan hedef RA register'ına yazılır; sign-extension veya numeric reinterpretation yapılmaz.
- `MOVI64`, `MOVI` için assembler alias'ıdır; ayrı bir opcode değildir.
- Her iki biçimde de hedef register yalnızca komut paketi başarıyla decode edilip yürütüldüğünde güncellenir. Illegal encoding/fetch fault durumunda hedef register korunur.

Örnek:

```asm
MOVI RA1, -17
MOVI64 RA4, 0x123456789ABCDEF0
```

İkinci örnek üç 64-bit word tüketir: EXT prefix, MOVI instruction ve literal. Numeric opcode ataması henüz yapılmamıştır.
