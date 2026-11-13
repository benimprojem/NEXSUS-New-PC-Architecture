# NEXSUS CPU — Special Register Architecture (SRA)

**Belge:** NEXSUS-CPU-SRA-001  
**Durum:** Mimari taslak  
**Kapsam:** CPU'nun ISA tarafından görülebilen özel register'ları ve donanım içi kontrol register'ları.

## 1. Amaç ve sınıflandırma

RA/DA/MA genel amaçlı register banklarıdır. Bunlardan ayrı olarak CPU'nun adresleme, komut yürütme, bellek erişimi ve durum takibi için özel register'lara ihtiyacı vardır.

İki sınıf ayrılır:

1. **Architectural Special Registers (ASR):** ISA'nın tanımladığı, programın özel komutlar veya belirlenmiş operand biçimleriyle okuyabildiği/yazabildiği register'lar.
2. **Internal Microarchitectural Registers (IMR):** Pipeline, decoder, cache controller ve execution unit içinde kullanılan; ISA tarafından görünür olması gerekmeyen donanım durumları.

Bir register'ın özel olması, mutlaka programcı tarafından yazılabilir olması anlamına gelmez. Bazıları salt okunur, bazıları kontrollü yazılabilir, bazıları tamamen donanım içidir.

## 2. Architectural Special Register adayları

| Register | İşlev | Program erişimi | Not |
|---|---|---|---|
| PC | Sonraki komut adresi | Kontrollü/özel | Branch/call/return mekanizması günceller |
| SR | Aritmetik ve karşılaştırma durumları | Okuma; sınırlı yazma | Flag/predicate alt yapısı kararlaştırılacak |
| CR | CPU çalışma ve kontrol durumu | Ayrıcalıklı/özel | OS'ye özgü olmayan donanım kontrol alanları da içerebilir |
| SPR | SPM0 page seçimi | Normal kodda erişilebilir | SPM0 erişim bağlamı |
| SPO | SPM0 record offset | Normal kodda erişilebilir | Page içindeki 64-bit record index'i |
| SPB | SPM1 byte address/page context | Normal kodda erişilebilir | SPM1 byte-addressed erişim |
| AG0, AG1 | Adres üretim birimi için base/index state | Normal kodda erişilebilir | Load/store adres üretiminde kullanılabilir |
| MAR0, MAR1 | Başlatılmış memory transaction adresi | Donanım kontrollü | Programın doğrudan yazması şart değil |
| MDR0, MDR1 | Memory transaction veri tamponu | Donanım kontrollü | DA/register path ile aktarım |
| CAUSE | Son trap/fault nedeni | Salt okunur/özel | Fault modeliyle birlikte tanımlanacak |
| EPC | Trap/fault dönüş komut adresi | Özel | Kontrol akışı tasarımına bağlı |

PC, SR, CR, SPR/SPO/SPB ve AG0/AG1 mimari adaylardır. MAR/MDR, CAUSE/EPC'nin bir kısmı donanım kontrollü veya implementation-defined olabilir. Nihai erişim yetkileri privilege modelinden bağımsız olarak ISA'da açıkça tanımlanmalıdır.

## 3. SPM adres register'ları

### 3.1 SPM0

SPM0, page + record-offset modelini kullanır:

- SPR: seçili page kimliği.
- SPO: seçili page içindeki 64-bit record offset'i (0..511).
- Birleşik adres gösterimi: [SPR:SPO].
- SPR/SPO yazımı yalnızca adresleme state'ini değiştirir; SPM içeriğine erişmez.
- SPM erişim komutu adres register'larının o anki değerini transaction başlangıcında örnekler. Sonraki SPR/SPO değişikliği devam eden transaction'ın adresini değiştirmez.

Örnek taslak:

```asm
MOV SPR, 3
MOV SPO, 128
SPM.RD RA05, [SPR:SPO]
```

### 3.2 SPM1

SPM1 byte-addressed olduğundan SPB bir byte offset veya page+byte-offset bileşimini temsil eder. SPM1 kapasitesi, page boyutu ve fiziksel bank mapping henüz sabitlenmediği için SPB bit genişliği/alanları daha sonra belirlenir.

SPM0 ve SPM1 adres register'ları ayrı tutulur; böylece bir SPM alanına erişim hazırlanırken diğerinin adres bağlamı bozulmaz.

## 4. Address Generation Unit (AGU)

- AG0 ve AG1, iki bağımsız adres üretim akışının base/index/offset state'ini tutmak için önerilir.
- AGU, base + index × scale + displacement benzeri adresleri load/store için hesaplar.
- AG0/AG1 register'larının kesin alanları (base, index, stride, bounds) ISA formatı aşamasında kararlaştırılır.
- AGU register'ları RA register'larının yerine geçmez; sık kullanılan adres hesaplarını ve memory issue yolunu ayırır.
- AGU sayısı iki önerisidir; port/throughput analiziyle doğrulanacaktır.

## 5. CPU durum ve kontrol register'ları

- SR: ALU/compare durumunu taşır. Flag yerine predicate register kullanımı ayrıca değerlendirilecektir.
- CR: CPU kontrol durumudur. Cache policy, execution mode ve koruma kontrolleri gibi alanların hangilerinin mimari görünür olacağı ayrıca belirlenir.
- CAUSE/EPC: trap/fault modelinin parçasıdır; OS context register'ı olarak tasarlanmaz, CPU'nun kontrol akışını güvenli biçimde yeniden başlatmasına hizmet eder.

## 6. Internal Microarchitectural Registers

Aşağıdakiler ISA'nın zorunlu görünür register'ları değildir:

- IR: decode edilen komut veya micro-op bilgisi.
- Pipeline stage register'ları.
- Cache tag/data pipeline state.
- Load/store queue entry'leri ve replay state.
- Internal MAR/MDR kopyaları ve transaction ID'leri.
- Branch prediction / recovery state.
- Execution unit ara sonuçları ve forwarding buffer'ları.

Bunların sayısı, genişliği ve yerleşimi mikro-mimariye bırakılır.

## 7. Erişim ve koruma ilkeleri

1. Genel amaçlı kodun değiştirmemesi gereken register'lar donanım tarafından salt okunur veya özel komutla erişilebilir yapılır.
2. SPM adres register'ları normal program akışında kullanılabilir; bunlar OS'ye ayrılmış register değildir.
3. Bir memory/SPM transaction başladığında adres ve kontrol alanları transaction'a latch edilir.
4. Birden fazla in-flight transaction için tek MAR/MDR çifti yeterli olmayabilir; gerçek tasarımda queue/entry tabanlı internal state tercih edilebilir.
5. Özel register erişim komutları, privilege/exception semantiğiyle çakışmayacak şekilde tanımlanır.
6. Register numaraları, bit alanları ve tam opcode encoding henüz sabit değildir.

## 8. İlişkili belgeler

- [CPU ISA-001](NEXSUS-CPU-ISA-001.md)
- [CPU ana mimarisi](Yeni%20Nesil%20Ayr%C4%B1%C5%9Ft%C4%B1r%C4%B1lm%C4%B1%C5%9F%20Register%20Tabanl%C4%B1%20CPU%20Mimarisi.md)
- [SPM ve register views](NEXSUS%20CPU%20%E2%80%94%20SPM,%20Register%20G%C3%B6r%C3%BCn%C3%BCmleri%20ve%20Do%C4%9Frudan%20Alan%20Eri%C5%9Fimi.md)
