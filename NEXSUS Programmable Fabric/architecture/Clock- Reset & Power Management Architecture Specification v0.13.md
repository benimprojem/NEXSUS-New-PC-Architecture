# NEXSUS Clock, Reset & Power Management Architecture Specification

**Doküman Kodu:** NEXSUS-CLK-013  
**Sürüm:** 1.0  
**Statü:** Mimari Taslak  
**Kapsam:** Yalnızca NEXSUS programlanabilir çip mimarisi

---

## 1. Amaç

Bu belgenin amacı NEXSUS çipindeki saat kaynaklarını, saat alanlarını, reset mekanizmalarını ve güç yönetimini tanımlamaktır.

Temel hedefler:

- Farklı birimlerin ihtiyaç duydukları hızlarda çalışabilmesi.
- CPU, DMA, Chip Fabric ve Programlanabilir Fabric işlemlerinin koordineli yürütülmesi.
- Saat alanları arasında veri bütünlüğünün korunması.
- Kullanılmayan birimlerin gereksiz enerji tüketiminin azaltılması.
- Hata durumlarında kontrollü kurtarma sağlanması.

Bu mimari, saat ve güç yönetimini tek bir kontrol noktasıyla yönetilebilir kılarken her birimin bağımsız çalışma ihtiyacını da korumayı amaçlar.

## 2. Saat Mimarisi

### 2.1. Saat alanları

NEXSUS içinde aşağıdaki mantıksal saat alanları tanımlanır:

| Saat alanı | Kapsadığı birimler |
|---|---|
| CPU Clock | CPU yürütme birimi ve ilişkili kontrol mantığı |
| Chip Fabric Clock | Dahili bağlantı, yönlendirme ve arbitraj mantığı |
| Programmable Fabric Clock | Programlanabilir mantık ve yapılandırılmış işlem blokları |
| Memory Clock | Bellek denetleyicisi ve ilgili arayüzler |
| DMA Clock | DMA kontrolü ve transfer mantığı |
| I/O Clock | Genel I/O denetleyicileri ve protokol motorları |
| Peripheral Clock | Zamanlayıcılar, sayaçlar ve diğer çevre birimleri |
| Auxiliary Clock | Gerektiğinde özel hızlı veya yavaş çalışan alt birimler |

Bu alanlar **mantıksal ayrımlardır**. Her alanın ayrı bir fiziksel saat kaynağına sahip olması zorunlu değildir.

Birden fazla birim aynı saat kaynağını paylaşabilir. Bağımsız frekans veya güç kontrolü gereken alanlar ise ayrı saat bölücülerine ya da uygun saat üretim devrelerine bağlanabilir.

### 2.2. Saat kaynakları

Olası saat kaynakları:

- Harici referans saat girişi.
- Dahili osilatör.
- PLL veya eşdeğer frekans üretim devresi.
- Saat bölücüler.
- Düşük güçte çalışan yardımcı saat kaynağı.

Kesin kaynak seçimi, hedef üretim teknolojisi ve çipin kullanım gereksinimleri belirlendikten sonra yapılacaktır.

### 2.3. Dinamik frekans yönetimi

Uygun donanım desteği sağlandığında bazı saat alanlarının frekansı çalışma sırasında değiştirilebilir.

Örneğin:

- CPU yoğun hesaplamalarda yüksek frekansta çalışabilir.
- I/O birimleri kendi protokol gereksinimlerini karşılayan saatlerde çalışabilir.
- Kullanılmayan Programlanabilir Fabric bölgeleri daha düşük etkinlik düzeyine geçirilebilir.

Frekans değişimi doğrudan ve kontrolsüz biçimde yapılmamalıdır. İlgili saat kaynağının kararlı olduğu doğrulanmalı ve saat alanındaki aktif işlemlerin güvenliği korunmalıdır.

**Not:** Dinamik frekans değiştirme, ilk prototip için zorunlu değildir. Sabit frekanslı bir başlangıç tasarımıyla başlanabilir.

## 3. Saat Alanları Arası Veri Aktarımı (CDC)

Farklı saat alanlarında çalışan birimler arasında veri aktarılırken Clock Domain Crossing (CDC) güvenliği sağlanmalıdır.

### 3.1. Tek bitlik kontrol sinyalleri

Uygun tek bitlik kontrol sinyalleri, metastabilite riskini azaltan senkronizatörlerden geçirilebilir.

Her sinyalin yapısına göre doğru senkronizasyon yöntemi seçilmelidir. Kısa süreli darbeler, sıradan bir senkronizatör zincirinden geçirilerek güvenli biçimde aktarılacak varsayılmamalıdır.

### 3.2. Çok bitli veri aktarımı

Çok bitli veri yollarında kullanılabilecek yöntemler:

- Asenkron FIFO.
- İstek/onay el sıkışma protokolü.
- Uygun veri kararlılığı garantilerine sahip özel CDC arayüzü.

Birden fazla bitin bağımsız senkronizatörlerden geçirilmesi, verinin aynı çevrimde ve tutarlı biçimde karşıya ulaştığını garanti etmez.

### 3.3. Chip Fabric ile ilişkisi

Chip Fabric, farklı saat alanlarındaki düğümler arasında veri ve istek taşınmasını desteklemelidir. Ancak saat alanları arasındaki güvenli aktarımın hangi katmanda uygulanacağı her arayüz için açıkça belirlenmelidir.

CDC mantığı, bağlantı protokolünün yerine geçmez; bağlantı protokolüyle birlikte çalışır.

## 4. Reset Mimarisi

### 4.1. Reset türleri

NEXSUS için aşağıdaki reset sınıfları önerilir:

| Reset türü | Amaç |
|---|---|
| Power-on Reset | İlk enerji verildiğinde başlangıç durumunu oluşturmak |
| Global Reset | Çipin büyük bölümünü bilinen başlangıç durumuna döndürmek |
| Local Reset | Belirli bir birimi diğerlerinden bağımsız sıfırlamak |
| Software Reset | Yazılım tarafından kontrollü reset başlatmak |
| Watchdog Reset | Sistem yanıt vermediğinde kurtarma başlatmak |

Tüm reset türlerinin ilk silikon sürümünde bulunması zorunlu değildir.

### 4.2. Reset alanları

Reset alanları, saat alanlarıyla ilişkili ancak onlardan bağımsız olarak tanımlanmalıdır.

Bir birimin resetlenmesi, başka bir birimin devam eden işlemini bozabilir. Bu nedenle reset kapsamı ve birimler arasındaki bağımlılıklar açıkça belirlenmelidir.

Örneğin, yalnızca bir çevre birimi resetlendiğinde CPU ve Chip Fabric çalışmaya devam edebilir. Bunun güvenli olması için ilgili birimin aktif transferleri sonlandırması, iptal etmesi veya yeniden başlatılabilir duruma getirmesi gerekir.

### 4.3. Reset sıralaması

Başlangıç sıralaması aşağıdaki mantığı izlemelidir:

1. Güç ve referans saat koşullarının uygun duruma gelmesi.
2. Gerekli saat üretim birimlerinin kararlı çalıştığının doğrulanması.
3. İlgili resetlerin kontrollü biçimde kaldırılması.
4. Bellek denetleyicisi ve temel bağlantı mantığının başlatılması.
5. CPU ve diğer birimlerin çalışmaya hazır hâle getirilmesi.
6. Yazılımın veya yapılandırma denetleyicisinin normal başlatma sürecine geçmesi.

Kesin sıra, seçilecek bellek ve yapılandırma mimarisine göre ayrıntılandırılacaktır.

## 5. Güç Yönetimi

### 5.1. Güç durumları

Birimlerin aşağıdaki mantıksal güç durumlarını desteklemesi hedeflenir:

| Durum | Açıklama |
|---|---|
| Active | Birim normal çalışır. |
| Idle | Birim etkin işlem yapmaz ancak hızlıca çalışmaya dönebilir. |
| Clock-Gated | Saat geçişleri durdurulur; birimin durumu korunur. |
| Power-Gated | Destekleniyorsa birimin güç beslemesi kesilir; durum kaybı oluşabilir. |

Her birimin tüm durumları desteklemesi şart değildir.

### 5.2. Clock gating

Clock gating, birim çalışmadığında saat geçişlerini durdurarak dinamik güç tüketimini azaltmayı amaçlar.

Bu yöntemde güç beslemesi kesilmez. Dolayısıyla durumun korunması genellikle daha kolaydır; ancak sızıntı akımı gibi diğer güç tüketimi bileşenleri devam eder.

Saat kapılama, saat sinyalinin güvenli biçimde kontrol edilmesini sağlayan uygun donanım yapılarıyla uygulanmalıdır.

### 5.3. Power gating

Power gating, desteklenen bölgelerin güç beslemesini keserek bekleme sırasındaki güç tüketimini daha fazla azaltabilir.

Buna karşılık:

- Birimin iç durumu kaybolabilir.
- Yeniden başlatma süresi gerekebilir.
- Durumun önceden saklanması gerekebilir.
- Güç adalarının giriş ve çıkışlarında ek kontrol mantığı gerekebilir.

Bu nedenle power gating, ilk sürümde zorunlu özellik olarak kabul edilmez. Fiziksel tasarım ve güç bütçesi değerlendirildikten sonra seçilmelidir.

## 6. CPU, DMA ve Fabric Bağımsızlığı

NEXSUS'un temel çalışma yaklaşımı, CPU'nun her veri hareketini sürekli yönetmek zorunda kalmamasıdır.

Örnek çalışma:

1. CPU bir DMA transferini yapılandırır.
2. DMA, Chip Fabric üzerinden veri aktarımını yürütür.
3. CPU, bağımsız bir işi yürütmeye devam edebilir.
4. Transfer tamamlandığında ilgili birim bir olay veya kesme üretebilir.

Bu çalışma biçiminin saat ve güç yönetimiyle uyumlu olması gerekir.

CPU'nun çalışmaya devam edebilmesi, diğer birimlerin mutlaka farklı frekanslarda çalışmasını gerektirmez. Aynı saat alanını paylaşan birimler de eşzamanlı iş yapabilir; bağımsız saat alanları ise farklı hızlarda çalışma esnekliği sağlar.

Bir saat alanının kapatılması veya yavaşlatılması, o alanda devam eden DMA transferlerini ve bekleyen istekleri dikkate almalıdır.

## 7. Düşük Güçte Uyanma

Gerekli görülürse çipte sınırlı bir kontrol bölgesi sürekli etkin tutulabilir.

Bu bölge:

- Zamanlayıcı olaylarını izleyebilir.
- Desteklenen dış kesme veya uyandırma sinyallerini algılayabilir.
- Uyku durumundaki birimlerin yeniden etkinleştirilmesini başlatabilir.
- Güç ve saat durumlarını yönetebilir.

Bu bölgenin fiziksel olarak ayrı bir güç adası olması zorunlu değildir. İlk sürümde daha basit bir denetim mantığı yeterli olabilir.

Uyandırma kaynakları, ilgili çevre birimlerinin gerçek yetenekleri belirlendikten sonra tanımlanacaktır.

## 8. Hata Yönetimi

Saat, reset ve güç yönetimi aşağıdaki hata durumlarını ele alabilecek şekilde tasarlanmalıdır:

- Saat kaynağının kararsızlaşması veya kaybolması.
- PLL kilitlenmesinin başarısız olması.
- Birimin reset sonrasında hazır duruma geçememesi.
- Güç durumundan dönüşün tamamlanamaması.
- Beklenen yanıtın zaman aşımına uğraması.
- Saat alanları arasındaki aktarımın tamamlanmaması.

Olası tepkiler; ilgili birimi resetlemek, daha güvenli bir saat kaynağına geçmek, hatayı yazılıma bildirmek veya destekleniyorsa kontrollü sistem reseti başlatmaktır.

Her hata için otomatik sistem reseti uygulanmamalıdır. Yerel olarak kurtarılabilecek hatalar, mümkün olduğunda yalnızca ilgili birimi etkilemelidir.

## 9. İlk Prototip İçin Uygulama Sınırı

İlk prototipte karmaşıklığı sınırlamak amacıyla şu yaklaşım önerilir:

- Sabit referans saat ve basit saat dağıtımı.
- Gerekli olmayan dinamik frekans değişiminin ertelenmesi.
- Global ve yerel reset mekanizmalarının temel düzeyde uygulanması.
- Farklı saat alanları kullanıldığında CDC güvenliğinin zorunlu tutulması.
- Kullanılmayan bloklar için clock gating desteğinin değerlendirilmesi.
- Power gating'in sonraki tasarım aşamasına bırakılması.

Bu yaklaşım, daha sonra gelişmiş güç yönetimine geçişi engellemez.

## 10. Açık Tasarım Kararları

Aşağıdaki noktalar henüz kesinleştirilmemiştir:

1. Referans saat kaynağı ve frekansı.
2. PLL sayısı ve saat bölme seçenekleri.
3. Hangi birimlerin bağımsız saat alanına ihtiyaç duyduğu.
4. Saat alanları arasındaki FIFO ve el sıkışma standartları.
5. Global ve yerel reset kapsamları.
6. Watchdog mekanizmasının kapsamı.
7. İlk sürümde clock gating desteğinin sınırları.
8. Power gating'in hangi bölgelerde uygulanabilir olduğu.
9. Uyandırma kaynakları ve düşük güçte kontrol mantığının kapsamı.
10. Saat veya güç hataları için kurtarma politikası.

Bu kararlar, CPU yürütme modeli, Chip Fabric bağlantıları, bellek denetleyicisi ve I/O gereksinimleriyle birlikte kesinleştirilmelidir.

## 11. Sonuç

NEXSUS Clock, Reset & Power Management mimarisi; farklı işlem birimlerinin güvenilir biçimde çalışmasını, gerektiğinde bağımsız hızlarda işlem yapmasını ve kullanılmayan kaynakların daha verimli yönetilmesini sağlayacak temel kontrol katmanını tanımlar.

**Mimari ilke:** Saat, reset ve güç yönetimi tüm çipi tek bir çalışma durumuna zorlamamalı; bağımsız birimlerin güvenli çalışmasını korurken gerekli koordinasyonu sağlamalıdır.

---

**Belge Sonu — NEXSUS-CLK-013 v1.0**