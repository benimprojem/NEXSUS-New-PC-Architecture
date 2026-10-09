# NEXSUS Boot, Configuration & Initialization Architecture Specification

**Doküman Kodu:** NEXSUS-BOOT-015  
**Sürüm:** 1.0  
**Statü:** Mimari Taslak  
**Kapsam:** NEXSUS programlanabilir çip

---

## 1. Amaç

Bu belgenin amacı, NEXSUS çipinin enerji verildiğinde hangi sırayla başlatılacağını, yapılandırma bilgilerinin nasıl yükleneceğini ve işlem birimlerinin ne zaman çalışmaya başlayacağını tanımlamaktır.

Başlangıç mimarisi şu işlevleri kapsar:

- Güç ve saat koşullarının doğrulanması.
- Reset durumundan kontrollü çıkış.
- Çipin başlangıç yapılandırmasının belirlenmesi.
- Programlanabilir Fabric'in yapılandırılması.
- CPU'nun çalışmaya hazır hâle getirilmesi.
- Bellek ve çevre birimlerinin başlatılması.
- Başlatma hatalarının tespit edilmesi ve kurtarma seçenekleri.

## 2. Başlangıç Mimarisi

NEXSUS başlangıç süreci üç mantıksal aşamaya ayrılır:

| Aşama | Görev |
|---|---|
| Stage 0 — Hardware Startup | Güç, saat ve reset koşullarının hazırlanması |
| Stage 1 — Chip Initialization | Temel donanımın ve yapılandırma kaynaklarının hazırlanması |
| Stage 2 — Execution Startup | CPU, Programlanabilir Fabric ve gerekli çevre birimlerinin çalıştırılması |

Bu aşamalar mantıksal görev ayrımlarıdır; ayrı işlemciler veya fiziksel birimler olmak zorunda değildir.

## 3. Stage 0 — Hardware Startup

Enerji verildiğinde çip, normal komut yürütmesine hemen başlamamalıdır.

İlk aşamada:

1. Power-on Reset etkinleşir.
2. Gerekli güç koşullarının sağlanması beklenir.
3. Referans saat kaynağı kontrol edilir.
4. Kullanılan saat üretim devrelerinin kararlı hâle gelmesi beklenir.
5. Temel reset sıralaması uygulanır.
6. Başlangıç denetim mantığı çalışmaya hazır hâle gelir.

Saat veya güç koşulları sağlanmazsa sistem, güvenli başlangıç durumunda kalmalıdır.

Bu aşamada CPU'nun tam çalışma frekansında çalışması veya Programlanabilir Fabric'in yapılandırılmış olması zorunlu değildir.

## 4. Stage 1 — Chip Initialization

Bu aşamada çipin temel kaynakları hazırlanır.

### 4.1. Başlangıç denetimi

Başlangıç denetimi, gerekli donanım bloklarının durumunu değerlendirir.

Kontrol edilebilecek birimler:

- Chip Fabric.
- Bellek denetleyicisi.
- CPU kontrol ve yürütme birimi.
- DMA.
- Kesme ve olay denetleyicisi.
- I/O denetleyicileri.
- Programlanabilir Fabric yapılandırma arayüzü.

Her birimin tüm testlerinin bu aşamada tamamlanması zorunlu değildir. Başlangıç için gerekli olanlar ile daha sonra çalıştırılabilecek tanılama işlemleri ayrılmalıdır.

### 4.2. Bellek hazırlığı

CPU'nun kullanacağı bellek ve yapılandırma kaynakları hazır hâle getirilmelidir.

Bu aşama, seçilecek bellek teknolojisine bağlıdır.

- SRAM gibi doğrudan kullanılabilir bir bellek, gerekli reset ve başlatma koşulları sağlandıktan sonra erişime açılabilir.
- Harici bellek kullanılması durumunda ek başlatma ve kalibrasyon gerekebilir.
- MOSRAM kullanılması hâlinde, bu bellek konseptinin elektriksel ve zamansal özellikleri doğrulanmadan başlangıç davranışı kesinleştirilemez.
- MSSD gibi kalıcı depolama seçenekleri kullanılırsa yapılandırma verilerinin nereden okunacağı ayrıca tanımlanmalıdır.

Bellek hazır değilse, ona bağımlı olan başlatma adımları yürütülmemelidir.

### 4.3. Başlangıç yapılandırmasının kaynağı

NEXSUS yapılandırması, tasarım seçimine bağlı olarak şu kaynaklardan gelebilir:

- Çip içindeki kalıcı yapılandırma belleği.
- Harici kalıcı bellek.
- Özel bir başlangıç arayüzü.
- Test veya geliştirme arayüzü.
- Önceden tanımlanmış varsayılan yapılandırma.

Bu seçeneklerin tamamının ilk sürümde bulunması gerekmez.

İlk prototip için tek ve basit bir yapılandırma kaynağı seçilmesi önerilir.

## 5. Stage 2 — Execution Startup

Temel kaynaklar hazır olduğunda yürütme aşamasına geçilir.

Önerilen sıra:

1. Gerekli bellek kaynaklarının hazır olduğunun doğrulanması.
2. Programlanabilir Fabric yapılandırmasının yüklenmesi.
3. Fabric yapılandırmasının doğrulanması.
4. Gerekli DMA, I/O ve çevre birimlerinin hazırlanması.
5. Kesme ve olay yönlendirme ayarlarının oluşturulması.
6. CPU'nun başlangıç yürütme adresinden çalıştırılması.
7. Yazılımın gerekli birimleri etkinleştirmesi ve normal çalışma düzenine geçmesi.

Bu sıra, tüm sistemler için mutlak bir sıra değildir. Örneğin bazı tasarımlarda CPU, Fabric yapılandırmasını kendisi yükleyebilir. Başka bir tasarımda ise CPU çalışmaya başlamadan önce yapılandırmayı ayrı bir başlangıç denetleyicisi yükleyebilir.

NEXSUS için bu iki model arasındaki seçim henüz açık bir tasarım kararıdır.

## 6. Programlanabilir Fabric Yapılandırması

Programlanabilir Fabric'in çalışması için gerekli mantık ve bağlantı yapılandırması yüklenmelidir.

### 6.1. Yapılandırma verisi

Yapılandırma verisi, tasarıma bağlı olarak şunları içerebilir:

- LUT ve mantık hücresi ayarları.
- Flip-flop ve kayıtlı mantık seçenekleri.
- Programlanabilir bağlantı ve yönlendirme bilgileri.
- DSP veya MAC bloklarının ayarları.
- FIFO ve yerel bellek yapılandırmaları.
- Seçilen I/O ve protokol motorlarının yapılandırması.

Kesin veri biçimi, yapılandırma mimarisi ve donanım hücreleri belirlendikten sonra tanımlanacaktır.

### 6.2. Yapılandırma doğrulaması

Yüklenen yapılandırmanın kullanılabilirliği doğrulanmalıdır.

Olası kontroller:

- Veri uzunluğu ve biçim doğrulaması.
- Bütünlük kontrolü.
- Desteklenen donanım sürümüyle uyumluluk.
- Gerekli kaynakların mevcut olması.
- Yapılandırma yükleme işleminin tamamlanması.

CRC gibi bir bütünlük kontrolü, verinin bozulmasını tespit etmeye yardımcı olabilir; ancak tek başına kaynağın güvenilir olduğunu veya yapılandırmanın güvenli olduğunu kanıtlamaz.

### 6.3. Yapılandırma başarısızlığı

Yapılandırma yüklenemezse sistem, geçersiz mantığı çalıştırmamalıdır.

Uygun davranışlar:

- Yeniden yüklemeyi denemek.
- Önceden tanımlı güvenli yapılandırmaya dönmek.
- CPU'yu başlatma hatası durumunda tutmak.
- Hata kodunu tanılama arayüzünden bildirmek.

Güvenli varsayılan yapılandırmanın fiziksel olarak mevcut olması zorunlu değildir. Bu özellik, tasarım gereksinimlerine göre seçilmelidir.

## 7. CPU Başlangıcı

CPU'nun çalışmaya başlaması için aşağıdaki koşulların sağlanması gerekir:

- CPU saatinin ve reset durumunun uygun olması.
- Başlangıç yürütme adresinin belirlenmesi.
- Gerekli komut ve veri erişim yollarının hazır olması.
- CPU'nun ihtiyaç duyduğu bellek kaynaklarının erişilebilir olması.
- Gerekliyse başlangıç yapılandırmasının tamamlanması.

CPU başlangıcında ilk yürütme adresinin hangi kaynaktan alınacağı ayrıca belirlenmelidir.

Olası modeller:

1. Sabit donanım başlangıç adresi.
2. Yapılandırılabilir başlangıç adresi.
3. Başlangıç denetleyicisi tarafından sağlanan adres.

Bu karar, NEXSUS komut kümesi ve adresleme mimarisiyle uyumlu olmalıdır.

## 8. Başlangıç Denetleyicisi ile CPU Arasındaki Görev Dağılımı

İki temel yaklaşım mümkündür.

### Model A — Donanım ağırlıklı başlangıç

Donanım denetleyicisi gerekli başlangıç adımlarını yürütür ve CPU'yu hazır olduğunda serbest bırakır.

**Avantajları:**

- CPU başlamadan önce gerekli kaynaklar hazırlanabilir.
- Başlangıç sıralaması daha öngörülebilir olabilir.

**Dezavantajları:**

- Donanım denetleyicisinin karmaşıklığı artabilir.
- Başlangıç mantığının değiştirilmesi daha sınırlı olabilir.

### Model B — CPU ağırlıklı başlangıç

Donanım yalnızca CPU'nun başlayabileceği minimum koşulları sağlar. Diğer kaynaklar CPU tarafından yazılım aracılığıyla hazırlanır.

**Avantajları:**

- Başlangıç davranışı yazılımla değiştirilebilir.
- Donanım başlangıç mantığı daha basit tutulabilir.

**Dezavantajları:**

- CPU, erişmesi gereken kaynaklar hazır olmadan başlatılmamalıdır.
- Yapılandırma yükleme yazılımına bağımlılık oluşabilir.

İlk prototip için hibrit model uygundur: donanım temel güç, saat, reset ve başlangıç erişimini sağlar; CPU ise daha üst düzey yapılandırma işlemlerini yürütür.

## 9. Hata Yönetimi ve Kurtarma

Başlangıç sürecinde şu hatalar meydana gelebilir:

- Saat kaynağının hazır olmaması.
- Bellek başlatma başarısızlığı.
- Yapılandırma verisinin bozuk olması.
- Programlanabilir Fabric yapılandırmasının tamamlanmaması.
- CPU başlangıç adresinin geçersiz olması.
- Gerekli birimlerin hazır duruma geçmemesi.

Her hata için en azından bir hata durumu veya kodu tanımlanmalıdır.

Sistemin hata sonrasında yeniden başlatılması, yapılandırmayı yeniden yüklemesi veya tanılama modunda kalması gerektiği belirlenmelidir.

Bir hata nedeniyle CPU başlatılamıyorsa, hatanın raporlanabilmesi için CPU'dan bağımsız en az bir tanılama yolu bulunması yararlı olacaktır. Bu yol ilk prototipte basit bir durum kaydı veya özel test arayüzü olabilir.

## 10. İlk Prototip İçin Minimum Kapsam

İlk NEXSUS prototipinde aşağıdaki kapsam önerilir:

- Power-on Reset ve temel saat hazırlığı.
- Sabit bir başlangıç akışı.
- Tek bir yapılandırma kaynağı.
- Temel bellek hazır kontrolü.
- Programlanabilir Fabric yapılandırma yüklemesi.
- Yapılandırma tamamlanma ve hata durumları.
- CPU başlangıç adresinin belirlenmesi.
- Basit hata kodları ve test arayüzü.

Gelişmiş çoklu yapılandırma profilleri, güvenli önyükleme zinciri, yapılandırma güncelleme mekanizması ve karmaşık kurtarma seçenekleri sonraki aşamalarda ele alınabilir.

## 11. Açık Tasarım Kararları

1. Yapılandırmanın saklanacağı bellek türü.
2. Yapılandırma verisinin fiziksel kaynağı ve aktarım arayüzü.
3. Başlangıç denetleyicisinin kapsamı.
4. CPU'nun hangi aşamada serbest bırakılacağı.
5. Fabric yapılandırmasının veri biçimi.
6. Yapılandırma bütünlüğünün nasıl doğrulanacağı.
7. Başlangıç yürütme adresinin nasıl belirleneceği.
8. Hata durumunda yeniden deneme ve kurtarma politikası.
9. İlk prototipte kullanılacak tanılama arayüzü.
10. İleride güvenli önyükleme veya yapılandırma doğrulama gereksinimi olup olmayacağı.

## 12. Sonuç

NEXSUS başlangıç mimarisi, çipin enerji verilmesinden normal yürütmeye geçişine kadar olan süreci kontrollü ve denetlenebilir bir sıraya yerleştirir.

**Mimari ilke:** CPU ve Programlanabilir Fabric, ihtiyaç duydukları kaynaklar hazır olmadan normal çalışmaya geçirilmemelidir. Başlangıç süreci hata durumlarını tespit edebilmeli ve tanımlı bir kurtarma davranışına sahip olmalıdır.

---

**Belge Sonu — NEXSUS-BOOT-015 v1.0**