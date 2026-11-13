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
| SPR | SPM0 page seçimi | Yazılım erişimi yok; CPU-internal | CPU'nun özel SPM0 erişim bağlamı |
| SPO | SPM0 record offset | Yazılım erişimi yok; CPU-internal | Page içindeki 64-bit record index'i; yalnızca CPU donanımı kullanır |
| SPB | SPM1 byte address/page context | PL0 erişemez; PL1/PL2 kontrollü OS erişimi | OS-owned SPM1 byte-addressed erişim |
| AG0, AG1 | Adres üretim birimi için base/index state | Normal kodda erişilebilir | Load/store adres üretiminde kullanılabilir |
| MAR0, MAR1 | Başlatılmış memory transaction adresi | Donanım kontrollü | Programın doğrudan yazması şart değil |
| MDR0, MDR1 | Memory transaction veri tamponu | Donanım kontrollü | DA/register path ile aktarım |
| CAUSE | Son trap/fault nedeni | Salt okunur/özel | Fault modeliyle birlikte tanımlanacak |
| EPC | Trap/fault dönüş komut adresi | Özel | Kontrol akışı tasarımına bağlı |

PC, SR, CR, SPB ve AG0/AG1 mimari adaylardır. SPR/SPO CPU-internal durumdur ve yazılıma açık değildir. MAR/MDR, CAUSE/EPC'nin bir kısmı donanım kontrollü veya implementation-defined olabilir. SPM erişim yetkileri NEXSUS-CPU-SPM-ACCESS-PROTECTION-001.md ile uyumlu uygulanır.

## 3. SPM adres register'ları

### 3.1 SPM0

SPM0, page + record-offset modelini CPU donanımı içinde kullanır:

- SPR: seçili page kimliği.
- SPO: seçili page içindeki 64-bit record offset'i (0..511).
- Birleşik adres gösterimi: [SPR:SPO].
- SPR/SPO yalnızca CPU-internal adresleme state'idir; PL0, PL1 ve PL2 yazılımı bunları okuyamaz, yazamaz veya SPM0'a doğrudan erişemez.
- SPM0 üzerindeki bütün okuma/yazma işlemlerini yalnızca CPU donanımı gerçekleştirir. Bu alan için yazılıma açık SPM.RD/SPM.WR yolu yoktur.

### 3.2 SPM1

SPM1 byte-addressed olduğundan SPB bir byte offset veya page+byte-offset bileşimini temsil eder. SPM1 kapasitesi, page boyutu ve fiziksel bank mapping henüz sabitlenmediği için SPB bit genişliği/alanları daha sonra belirlenir.

SPB yalnızca OS'nin kontrollü PL1/PL2 çalışma bağlamında kullanılabilir; PL0 doğrudan okuyamaz veya yazamaz. SPM0'ın CPU-internal SPR/SPO state'i ile SPM1'in OS-controlled SPB state'i birbirinden ayrıdır.

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
- Bellek-domain transferlerinin aktif transaction/descriptor, beat ilerleme ve completion state'i.
- XFER.START tarafından üretilen, WAIT tüketene kadar yaşayan çekirdek-yerel token kayıtları.

Bunların sayısı, genişliği ve yerleşimi mikro-mimariye bırakılır.

### 6.1 Memory-domain transfer kaynakları

- XFER.MEM ve XFER.START, mevcut bellek-domain/Fabric transaction ve arbitration yollarını kullanır; ayrı bir transfer register bankı veya yeni ISA-visible queue gerektirmez.
- Aktif transfer, yalnızca çalıştığı süre boyunca gerekli transaction/descriptor ve beat kaynaklarını kullanır. Transfer tamamlandığında bu yürütme kaynakları serbest bırakılabilir.
- XFER.START token kaydı ise transfer tamamlanmış olsa bile başarılı veya hatalı XFER.WAIT token'ı tüketene kadar ayrılmış kalır. Token kaydı ile aktif transfer kuyruğu kaydı aynı ömürlü kaynak değildir.
- Token kayıtlarının sayısı sonlu ve implementation-defined'dır; platform/OS capability bilgisiyle bildirilir. Kayıt bulunmuyorsa START bekletilmez: MEMORY_ACCESS_FAULT / TRANSFER_RESOURCE_UNAVAILABLE üretir, transferi kabul etmez ve TRA'yı değiştirmez. Bu retry edilebilir kaynak hatasıdır.
- Token kayıtları ve transaction state'i Internal Microarchitectural Registers kapsamındadır; yeni bir mimari register bankı, CSR veya yazılıma açık token-slot adresi oluşturulmaz.


### 6.2 Bellek arbitration ve adil servis politikası

CPU'nun L1–L4 bellek istekleri, her domain'in kendi controller/bank kaynaklarında bağımsız arbitration görür. Tek bir global bellek kilidi veya tüm domain'leri durduran ortak FIFO kullanılmaz.

**Servis sınıfları**

- **URGENT:** CPU'nun exception/IRQ işleyicisi aktifken gerekli context-frame ve handler veri erişimleri. Bu sınıf CPU hardware tarafından işaretlenir; PL0 yazılımı doğrudan URGENT sınıfı talep üretemez.
- **CPU-DEMAND:** Normal CPU LOAD/STORE ve ATOM istekleri. Kritik handler erişimleri URGENT, diğer tüm CPU erişimleri bu sınıftadır.
- **LATENCY-SENSITIVE:** Gecikme hedefi olan yetkili Fabric/Node talepleri.
- **BULK:** MEMXFER beat/chunk işlemleri ve büyük DMA/Fabric payload akışları.
- **BACKGROUND:** Ertelenebilir düşük öncelikli bakım veya arka plan transferleri.

**Arbitration algoritması**

1. Her domain/bank, yalnızca kendisine ulaşan ve erişim doğrulamasını geçmiş istekler arasında kendi kuyruğunu/arbitration durumunu tutar.
2. URGENT istekler için sınırlı bir servis bütçesi/slot rezervasyonu bulunur. Bütçe dolduğunda bekleyen diğer sınıflara servis verilir; URGENT sınıfı diğer trafiği sınırsız biçimde bloke edemez.
3. Kalan servis ağırlıklı adil sıra (weighted round-robin veya eşdeğer deficit-based scheduler) ile dağıtılır. Ağırlıklar ürün konfigürasyonuna göre değişebilir; hiçbir aktif sınıf sıfır ağırlık alamaz.
4. Bir isteğin bekleme yaşı arttıkça etkin önceliği yükselir. Bu aging mekanizması, düşük ağırlıklı veya uzun süredir bekleyen isteğin sürekli yeni gelen trafik tarafından geçilmesini engeller.
5. Büyük istekler sınırlı beat/chunk quantum'larına bölünür. BULK/XFER transferi quantum sınırında duraklatılabilir ve daha sonra kaldığı yerden devam eder; tek bir uzun transfer arbitration'ı süresiz elinde tutamaz.
6. Atomik RMW işlemi kendi atomic serialization noktasına kadar indivisible kalır; ancak bankaya girişte sınırsız öncelik kazanmaz. ATOM'un beklemesi, aynı granüldeki normal ve atomic erişimlerin tanımlı sıralamasını bozmaz.
7. Aynı bankada çakışmayan adresler fiziksel bank/port imkânı elverdiği ölçüde paralel işlenebilir. Banka veya port çatışması varsa yalnızca çakışan kaynaklar sıraya girer.

**IRQ/exception gecikmesi**

- URGENT sınıfı yalnızca CPU'nun aktif exception/IRQ durumundan kaynaklanan, donanım tarafından tanınan handler/context erişimlerine uygulanır. IRQ'nun gelmesi tek başına bellek erişimi veya memory synchronization değildir.
- URGENT servis bütçesi, handler'ın gerekli bellek erişimlerini gecikme açısından öne alır; ancak normal CPU, Fabric veya BULK trafiğini sonsuza kadar durdurmaz.
- SPM7 exception-entry workspace doğrudan CPU-internal exception yolu olduğundan normal L1–L4 bank arbitration kuyruğuna sokulmaz. Protected Data RAM context-frame erişimleri ilgili Data RAM bankasının URGENT kuyruğuna girebilir.

Kesin ağırlıklar, servis quantum boyutu, URGENT bütçesi ve cycle cinsinden gecikme garantileri saat, bank sayısı ve port genişlikleri belirlendikten sonra mikro-mimari/performans doğrulama aşamasında seçilir. Mimari zorunluluk; bounded burst, sınıf adaleti, aging ve bağımsız bank paralelliğidir.
## 7. Erişim ve koruma ilkeleri

1. Genel amaçlı kodun değiştirmemesi gereken register'lar donanım tarafından salt okunur veya özel komutla erişilebilir yapılır.
2. SPM0 adres state'i tamamen CPU-internal'dir ve hiçbir privilege seviyesindeki yazılıma açılmaz. SPM1 SPB ise yalnızca yetkili PL1/PL2 OS kodu tarafından kontrollü biçimde kullanılabilir; PL0 erişimi yasaktır.
3. Bir memory/SPM transaction başladığında adres ve kontrol alanları transaction'a latch edilir.
4. Birden fazla in-flight transaction için tek MAR/MDR çifti yeterli olmayabilir; gerçek tasarımda queue/entry tabanlı internal state tercih edilebilir.
5. Özel register erişim komutları, privilege/exception semantiğiyle çakışmayacak şekilde tanımlanır.
6. Register numaraları, bit alanları ve tam opcode encoding henüz sabit değildir.

## 8. İlişkili belgeler

- [CPU ISA-001](NEXSUS-CPU-ISA-001.md)
- [CPU ana mimarisi](Yeni%20Nesil%20Ayr%C4%B1%C5%9Ft%C4%B1r%C4%B1lm%C4%B1%C5%9F%20Register%20Tabanl%C4%B1%20CPU%20Mimarisi.md)
- [SPM ve register views](NEXSUS%20CPU%20%E2%80%94%20SPM,%20Register%20G%C3%B6r%C3%BCn%C3%BCmleri%20ve%20Do%C4%9Frudan%20Alan%20Eri%C5%9Fimi.md)


## 9. Memory access-control integration

AGU address generation and the existing load/store transaction path participate in the validation contract defined by `NEXSUS-CPU-MEMORY-ACCESS-CONTROL-001.md`. Address generation, full-range validation, ownership/permission checks, and request issue must complete before architectural commit. This does not make AG0/AG1 or MAR/MDR new architectural requirements; their exact implementation remains subject to the SRA/microarchitecture decision.


### 6.3 Fiziksel bank, port ve read/write yön değiştirme modeli

Bu bölümdeki **L1–L4 domain** kavramı ile fiziksel RAM bankası aynı şey değildir. Domain; erişim kapsamı, paylaşım ve görünürlük kurallarını tanımlar. Bank ise belirli bir fiziksel bellek kaynağının bağımsız servis edilebilen bölümüdür. Controller, port, lane ve cache-line/transfer granülü de ayrı kaynak kavramlarıdır. Bir domain bir veya daha fazla fiziksel bankaya eşlenebilir; bu eşleme kapasiteye ve uygulamaya bağlıdır.

**Bank dağıtımı ve paralellik**

- Ardışık adreslerin tek bankada yığılmasını önlemek için adresler, uygulamanın seçtiği interleave granülü üzerinden birden fazla bankaya dağıtılabilir. Bank seçimi için kullanılacak kesin adres bitleri/hash fonksiyonu; fiziksel kapasite, bank sayısı ve erişim granülü kesinleşince belirlenir.
- Farklı bankalara giden ve bağımlılığı bulunmayan istekler aynı anda servis edilebilir. Aynı bankanın aynı anda kullanılamayan portuna gelen istekler yalnızca o bankada sıraya girer.
- Aynı bankada birden fazla bağımsız port veya gerçek multiport hücre yapısı varsa, portların çakışmayan erişimleri paralel yürüyebilir. Mimari, her bankanın zorunlu olarak dual-port olmasını şart koşmaz.
- Bank içi paralellik, aynı byte aralığına ilişkin NDC sıralama, ATOM serialization ve MEMXFER reservation kurallarını gevşetmez.

**Read/write port ve turnaround**

- Bir bankanın read ve write işlemlerini aynı çevrimde kabul edip edememesi fiziksel bellek hücresi, sense/write devresi ve port organizasyonuna bağlı bir uygulama kararıdır. Mimari, desteklenmeyen eşzamanlı read/write işlemini varmış gibi kabul etmez.
- Tek yönlü veya paylaşılan portta READ↔WRITE geçişi gerekiyorsa controller gerekli turnaround süresini uygular; bu sırada yalnızca ilgili port/bank etkilenir, bağımsız bankalar çalışmaya devam eder.
- Controller, uygun olduğunda aynı yönlü istekleri sınırlı gruplar halinde birleştirerek yön değiştirme maliyetini azaltabilir. Ancak read-drain veya write-drain sınırsız olamaz: karşı yönde bekleyen isteklerin yaşı arttıkça servis önceliği yükselir ve bounded batch/aging kuralları uygulanır.
- Yazma kuyruğu boşaltma eşiği, read latency hedefi ve turnaround çevrim sayısı mikro-mimari parametrelerdir. Hiçbir aktif yönde süresiz starvation oluşmaması mimari gerekliliktir.
- Aynı domain coherence order içindeki read-after-write davranışı korunur. Henüz tamamlanmamış bir STORE'un ardından gelen ve aynı sıralamaya tabi LOAD, eski veriyi gözlemleyemez; controller gerekli forwarding veya sıralı servis mekanizmasını uygular.

**Ayrı App RAM ve Data RAM yolları**

- App RAM komut kaynağıdır ve P0 refill/fetch yoluna hizmet eder. Data RAM, LOAD/STORE, task payload ve korumalı context-frame erişimlerine hizmet eder.
- App RAM ve Data RAM fiziksel olarak ayrı bellek kaynakları ve bağımsız controller/erişim yolları olarak tasarlanır. Bu nedenle App RAM instruction fetch ile Data RAM data access, kendi kaynakları elverdiği sürece birbirinden bağımsız ilerleyebilir.
- Bu bağımsızlık, tek bir RAM bankasının sınırsız port sunduğu anlamına gelmez; her fiziksel kaynak kendi bank/port arbitration'ını uygular.
- App RAM ve Data RAM arasındaki ayrım, L1–L4 domain isimlerini fiziksel RAM bank numarası olarak yorumlama gerekçesi değildir.

Kesin bank sayısı, interleave granülü, port sayısı, read/write turnaround süresi, queue derinliği ve yön değiştirme eşiği fiziksel bellek teknolojisi ile controller tasarımı belirlendikten sonra seçilecektir. Mimari gereklilik; bağımsız bank paralelliği, yerel çatışma çözümü, iki yönde starvation koruması ve App/Data RAM yollarının bağımsızlığının korunmasıdır.
