# NEXSUS Configuration & Reconfiguration Architecture Specification

**Doküman Kodu:** NEXSUS-CFG-016  
**Sürüm:** 1.0  
**Statü:** Mimari Taslak  
**Kapsam:** NEXSUS programlanabilir çip

---

## 1. Amaç

Bu belgenin amacı, NEXSUS Programlanabilir Fabric'in ilk yapılandırılmasını ve çalışma sırasında yeniden yapılandırılmasını tanımlamaktır.

Mimari aşağıdaki işlevleri kapsar:

- Yapılandırma verisinin alınması ve doğrulanması.
- Mantık hücrelerinin ve bağlantı kaynaklarının programlanması.
- Tam yapılandırma ve kısmi yeniden yapılandırma.
- Yapılandırma sırasında kaynakların güvenli yönetimi.
- CPU, DMA ve Chip Fabric ile koordinasyon.
- Başarısız yapılandırmalardan kurtarma.

Temel hedef, donanım kaynaklarının farklı görevler için yeniden kullanılabilmesini sağlamaktır.

## 2. Temel Kavramlar

### 2.1. Configuration

Configuration, Programlanabilir Fabric'in nasıl çalışacağını belirleyen yapılandırma verisidir.

Bu veri; mantık hücrelerini, kayıtlı mantığı, bağlantı yollarını ve desteklenen özel işlem bloklarının ayarlarını belirleyebilir.

### 2.2. Full Reconfiguration

Tam yeniden yapılandırmada, yapılandırılabilir bölgenin tamamı yeni bir tasarıma göre düzenlenir.

Bu işlem sırasında önceki tasarımın çalışma durumu korunacağı varsayılmamalıdır.

### 2.3. Partial Reconfiguration

Kısmi yeniden yapılandırmada yalnızca belirlenmiş bir bölge değiştirilir; diğer bölgelerin çalışmaya devam etmesi hedeflenir.

Bu özellik, ancak donanım yerleşimi, bağlantı mimarisi ve yapılandırma devreleri bunu destekleyecek şekilde tasarlanırsa uygulanabilir.

Kısmi yeniden yapılandırma, her FPGA veya programlanabilir mantık mimarisinde kendiliğinden mevcut olan bir özellik değildir.

## 3. Yapılandırma Veri Modeli

Yapılandırma verisi mantıksal olarak aşağıdaki bölümlerden oluşabilir:

| Bölüm | İşlev |
|---|---|
| Header | Biçim sürümü ve temel tanımlayıcılar |
| Device Information | Hedef çip ve donanım sürümü bilgisi |
| Resource Map | Kullanılması gereken kaynakların tanımı |
| Logic Configuration | Mantık hücreleri ve kayıtlı mantık ayarları |
| Routing Configuration | Programlanabilir bağlantıların ayarları |
| Special Blocks | DSP, MAC, FIFO ve benzeri desteklenen blokların ayarları |
| Integrity Data | Veri bütünlüğü kontrol bilgileri |
| Compatibility Information | Gerekli mimari ve yapılandırma sürümü bilgileri |

Bu bölümler, önerilen mantıksal veri modelidir. Nihai ikili dosya biçimi henüz tanımlanmamıştır.

İlk prototipte daha basit bir başlık, yapılandırma yükü ve bütünlük kontrol alanı yeterli olabilir.

## 4. Yapılandırma Yükleme Yolu

Yapılandırma verisi, tasarıma göre aşağıdaki kaynaklardan alınabilir:

- Çip içindeki kalıcı bellek.
- Harici kalıcı bellek.
- CPU üzerinden erişilen bellek.
- Özel yapılandırma arayüzü.
- Geliştirme ve test arayüzü.

Yapılandırma yükleme yolu ile normal veri aktarım yolu aynı fiziksel altyapıyı paylaşabilir; ancak bunların erişim yetkileri ve çalışma kuralları açıkça belirlenmelidir.

Özellikle yapılandırma işleminin CPU, DMA ve Chip Fabric üzerinde oluşturacağı yük dikkate alınmalıdır.

## 5. Yapılandırma Denetleyicisi

Yapılandırma denetleyicisi, yapılandırma işlemlerini yöneten mantıksal birimdir.

Temel görevleri:

1. Yapılandırma isteğini almak.
2. Hedef bölgenin uygunluğunu kontrol etmek.
3. Verinin biçimini ve bütünlüğünü doğrulamak.
4. Gerekli kaynakları ayırmak.
5. Yapılandırma verisini hedef bölgeye uygulamak.
6. Tamamlanma veya hata durumunu bildirmek.
7. Bölgeyi çalışmaya hazır hâle getirmek.

Yapılandırma denetleyicisinin ayrı bir işlemci olması gerekmez. İşlevleri özel donanım mantığıyla veya desteklenen bir kontrol birimiyle gerçekleştirilebilir.

## 6. Tam Yapılandırma İş Akışı

Önerilen tam yapılandırma sırası:

1. Yapılandırma isteğinin alınması.
2. Hedef tasarımın çiple uyumluluğunun kontrol edilmesi.
3. Yapılandırma verisinin bütünlüğünün doğrulanması.
4. Aktif işlemlerin tamamlanması veya kontrollü durdurulması.
5. Yapılandırılabilir bölgenin güvenli duruma alınması.
6. Yeni yapılandırmanın yüklenmesi.
7. Yapılandırma işleminin tamamlandığının doğrulanması.
8. Gerekli başlangıç durumlarının hazırlanması.
9. Yeni tasarımın etkinleştirilmesi.
10. İlgili birimlere hazır bildirimi gönderilmesi.

Tam yapılandırma sırasında eski mantığın durumunun korunacağı varsayılmamalıdır. Durumun korunması gerekiyorsa yeniden yapılandırma öncesinde açıkça saklanması gerekir.

## 7. Kısmi Yeniden Yapılandırma

### 7.1. Bölgesel yapılandırma

Kısmi yeniden yapılandırmayı desteklemek için Programlanabilir Fabric, yapılandırılabilir bölgeler veya başka bir eşdeğer izolasyon modeliyle tasarlanmalıdır.

Her bölgenin sınırları ve dış arayüzleri belirlenmelidir. Bir bölgenin değiştirilmesi, komşu bölgelerin iç durumlarını veya bağlantılarını geçersiz hâle getirmemelidir.

### 7.2. Bölge izolasyonu

Yeniden yapılandırılacak bölge, işlem sırasında güvenli bir duruma alınmalıdır.

Bu süreç şunları içerebilir:

- Yeni isteklerin durdurulması.
- Devam eden işlemlerin tamamlanması veya iptal edilmesi.
- Giriş ve çıkışların izolasyonu.
- Bölgeye ait olay ve kesmelerin kontrol edilmesi.
- Gerekliyse durum bilgilerinin saklanması.

İzolasyon mekanizmasının ayrıntıları, Programlanabilir Fabric'in fiziksel mimarisine bağlıdır.

### 7.3. Yeniden yapılandırma sırasında diğer bölgeler

Kısmi yeniden yapılandırmanın hedefi, değiştirilmemiş bölgelerin çalışmayı sürdürmesidir.

Bununla birlikte, bu davranış ancak aşağıdaki koşullar sağlandığında güvenilir olabilir:

- Bölgeler arası arayüzler sabit ve uyumlu olmalıdır.
- Değiştirilen bölgenin kullandığı kaynaklar doğru biçimde ayrılmalıdır.
- Ortak kaynakların erişimi kontrol edilmelidir.
- Chip Fabric üzerindeki bağımlılıklar korunmalıdır.
- Saat, reset ve olay yönlendirme kuralları yeniden yapılandırmayla uyumlu olmalıdır.

Dolayısıyla kısmi yeniden yapılandırma, yalnızca yapılandırma verisini bölümlere ayırmakla çözülemez; fiziksel ve mantıksal izolasyon tasarımın parçası olmalıdır.

## 8. CPU, DMA ve Chip Fabric ile Koordinasyon

Yeniden yapılandırma sırasında CPU'nun çalışmaya devam etmesi mümkün olabilir. Ancak bu, her yapılandırma işleminde otomatik olarak garanti edilmez.

Örnek akış:

1. CPU yeniden yapılandırma isteği oluşturur.
2. Yapılandırma denetleyicisi hedef bölgeyi belirler.
3. DMA, yapılandırma verisini aktarabilir.
4. Chip Fabric, gerekli bellek ve veri yolu erişimlerini sağlar.
5. Hedef bölge güvenli duruma alınır.
6. Yapılandırma uygulanır ve doğrulanır.
7. Bölge etkinleştirilir.
8. CPU'ya tamamlanma olayı veya kesmesi gönderilir.

CPU'nun yeniden yapılandırılan bölgeye bağımlı bir işlemi varsa bu işlem durdurulmalı, ertelenmeli veya başka bir kaynağa yönlendirilmelidir.

DMA'nın yapılandırma verisi taşıması bir tasarım seçeneğidir; yapılandırma denetleyicisinin DMA olmadan doğrudan veri alması da mümkündür.

## 9. Kaynak Yönetimi

Yapılandırma işlemi sırasında Programlanabilir Fabric kaynakları için bir kaynak yönetim modeli gerekir.

Yönetilebilecek kaynaklar:

- Mantık hücreleri.
- Flip-flop ve kayıtlı mantık.
- DSP ve MAC blokları.
- FIFO ve yerel bellek.
- Programlanabilir yönlendirme kaynakları.
- Harici I/O bağlantıları.
- Saat ve reset kaynakları.

Kaynak tahsisi, yapılandırmanın mevcut kaynak sınırlarını aşıp aşmadığını denetlemelidir.

İki yapılandırma aynı kaynağı eşzamanlı olarak kullanmaya çalışırsa çakışma engellenmelidir. Kısmi yeniden yapılandırmada ise ortak kaynakların ve sabit bağlantıların kullanım kuralları ayrıca tanımlanmalıdır.

## 10. Hata Yönetimi

Yapılandırma sırasında meydana gelebilecek hatalar:

- Geçersiz yapılandırma biçimi.
- Uyumsuz donanım veya yapılandırma sürümü.
- Bozuk yapılandırma verisi.
- Yetersiz donanım kaynağı.
- Yapılandırma aktarımının yarıda kalması.
- Hedef bölgenin güvenli biçimde izole edilememesi.
- Yapılandırma sonrası doğrulamanın başarısız olması.

Hata durumunda yapılandırılmamış veya doğrulanmamış bir bölge normal çalışmaya geçirilmemelidir.

Olası kurtarma seçenekleri:

- Yapılandırmayı yeniden denemek.
- Önceki yapılandırmaya geri dönmek.
- Güvenli bir varsayılan yapılandırma yüklemek.
- Hedef bölgeyi devre dışı bırakmak.
- CPU'ya hata kodu ve ayrıntılı durum bilgisi bildirmek.

Önceki yapılandırmaya dönüşün mümkün olması için gerekli yapılandırma verisinin saklanması ve geri yükleme yolunun tasarlanması gerekir. Bu özellik otomatik olarak varsayılmamalıdır.

## 11. Yapılandırma Güvenliği

Yapılandırma verisinin bütünlüğü ile kaynağının güvenilirliği ayrı konulardır.

CRC veya benzeri kontroller aktarım hatalarını tespit etmeye yardımcı olabilir. Güvenilmeyen yapılandırmaların engellenmesi gerekiyorsa ayrıca kimlik doğrulama ve erişim kontrolü değerlendirilmelidir.

Gerekli görüldüğünde:

- Yapılandırma kaynaklarına erişim sınırlandırılabilir.
- Yetkisiz yeniden yapılandırma istekleri engellenebilir.
- Yapılandırma sürümü denetlenebilir.
- Desteklenen bir güvenli önyükleme veya doğrulama mekanizmasıyla entegrasyon sağlanabilir.

Kriptografik doğrulama, ilk prototipte zorunlu bir özellik olarak kabul edilmemiştir. Gereksinimlere göre ayrıca tasarlanmalıdır.

## 12. İlk Prototip İçin Minimum Kapsam

İlk prototipte aşağıdaki yaklaşım önerilir:

- Tam yapılandırma desteği.
- Sabit ve belgelenmiş yapılandırma veri biçimi.
- Temel bütünlük kontrolü.
- Yapılandırma denetleyicisi.
- Yapılandırma tamamlanma ve hata bildirimi.
- Geçersiz yapılandırmanın etkinleştirilmesini engelleme.
- Basit reset ve yeniden başlatma yolu.

Kısmi yeniden yapılandırma, gelişmiş kaynak tahsisi, yapılandırma sürümleri arasında otomatik geri dönüş ve güvenli yapılandırma doğrulaması sonraki aşamalarda uygulanabilir.

Ancak kısmi yeniden yapılandırmanın ileride desteklenmesi isteniyorsa bölgesel izolasyon ve sabit arayüz gereksinimleri ilk fiziksel mimari tasarımında dikkate alınmalıdır.

## 13. Açık Tasarım Kararları

1. Yapılandırma dosyasının nihai ikili biçimi.
2. Yapılandırma verisinin saklanacağı bellek ve aktarım arayüzü.
3. Yapılandırma denetleyicisinin mimarisi.
4. Tam yapılandırma sırasında CPU'nun çalışma durumu.
5. Kısmi yeniden yapılandırma için bölge sayısı ve sınırları.
6. Bölgesel izolasyon yöntemi.
7. Kaynak tahsisi ve çakışma kontrolü.
8. Yapılandırma bütünlüğü ve kimlik doğrulama gereksinimleri.
9. Başarısız yapılandırmadan geri dönüş yöntemi.
10. Yapılandırma denetleyicisinin DMA ve Chip Fabric ile ilişkisi.

## 14. Sonuç

NEXSUS Configuration & Reconfiguration mimarisi, Programlanabilir Fabric'in yalnızca ilk açılışta değil, gerektiğinde çalışma sırasında da farklı görevler için yeniden düzenlenebilmesine yönelik temel yaklaşımı tanımlar.

**Mimari ilke:** Yapılandırma işlemi, kaynak tahsisi, izolasyon, doğrulama ve hata yönetimiyle birlikte tasarlanmalıdır. Kısmi yeniden yapılandırma isteniyorsa bunun gereksinimleri donanım mimarisinin başlangıcından itibaren gözetilmelidir.

---

**Belge Sonu — NEXSUS-CFG-016 v1.0**