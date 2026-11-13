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
