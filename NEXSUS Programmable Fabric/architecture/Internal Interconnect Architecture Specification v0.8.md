# NEXSUS Chip Fabric — Internal Interconnect Architecture Specification

**Doküman Kodu:** NEXSUS-CHIP-FABRIC-008  
**Sürüm:** 0.9  
**Durum:** Mimari Taslak  
**Kapsam:** Programlanabilir NEXSUS çipinin dahili bağlantı ve veri aktarım mimarisi

---

## 1. Amaç

NEXSUS Chip Fabric, çip içerisindeki işlem birimleri, bellekler, denetleyiciler ve programlanabilir mantık kaynakları arasında veri aktarımını ve iletişimi sağlayan dahili bağlantı mimarisidir.

Temel amaç, CPU'nun bütün birimlerle doğrudan iletişim kurma ve her veri aktarımını ayrı ayrı yönetme zorunluluğunu ortadan kaldırmaktır.

CPU işlemleri başlatır ve gerekli komutları verir. Chip Fabric, birimler arasındaki iletişimi ve veri yollarını yönetir. DMA motorları, veri aktarımını CPU'dan bağımsız biçimde yürütebilir. İşlem birimleri de kendilerine atanan görevleri paralel olarak gerçekleştirebilir.

Bu yapı sayesinde çip içerisindeki kaynakların daha bağımsız, eşzamanlı ve verimli çalışması hedeflenir.

## 2. Temel Mimari İlkeler

1. Çip içerisindeki birimler, Chip Fabric üzerinden haberleşir.
2. CPU, her veri aktarımının bütün adımlarını yönetmek zorunda değildir.
3. Veri aktarımı ile işlem yürütme birbirinden ayrılır.
4. DMA, desteklenen veri aktarımlarını CPU'dan bağımsız olarak gerçekleştirir.
5. Programmable Fabric, Chip Fabric üzerinden diğer birimlerle iletişim kurar.
6. Bellek erişimleri, öncelikler ve kaynak paylaşımı merkezi kurallarla yönetilir.
7. Birimler arasında paralel çalışma desteklenir; ancak gerçek paralellik mevcut bant genişliği ve kaynak kapasitesiyle sınırlıdır.
8. Bağlantı mimarisi, P1–P5 ürün ailesinde ölçeklenebilir olacak şekilde tasarlanır.

## 3. Chip Fabric ve Programmable Fabric Ayrımı

Bu iki yapı farklı görevler üstlenir.

### 3.1. Chip Fabric

Chip Fabric, çipin dahili iletişim altyapısıdır.

Görevleri:

- Birimler arasında veri taşımak.
- İstekleri uygun hedeflere yönlendirmek.
- Birden fazla erişim isteğini sıraya almak.
- Ortak kaynaklara erişimi düzenlemek.
- Gerekli durumlarda öncelik ve hizmet kalitesi kurallarını uygulamak.
- Veri aktarımındaki tıkanıklıkları ve hata durumlarını yönetmek.

Chip Fabric'in temel bağlantı ve yönlendirme işlevlerinin normal çalışma sırasında kullanıcı tarafından yeniden yapılandırılması zorunlu değildir.

### 3.2. Programmable Fabric

Programmable Fabric, kullanıcı veya derleyici tarafından yapılandırılabilen işlem alanıdır.

İçerebileceği kaynaklar:

- LUT ve flip-flop blokları.
- Yerel ve blok bellekler.
- DSP/MAC işlem birimleri.
- FIFO tamponları.
- Özel mantık devreleri.
- Programlanabilir durum makineleri.
- Özel protokol ve veri işleme devreleri.

Programmable Fabric, Chip Fabric üzerinden bellek ve diğer çip içi birimlerle veri alışverişi yapar.

**Sonuç:** Chip Fabric bağlantıyı ve veri akışını yönetir; Programmable Fabric ise yapılandırılabilir işlem kaynaklarını sağlar.

## 4. Çip İçi Düğüm Modeli

Chip Fabric'e bağlanan her birim, mimari açıdan bir düğüm olarak ele alınır.

Bir düğümün destekleyebileceği arayüzler:

- **Control Interface:** Komut, durum, yapılandırma ve kontrol kayıtlarına erişim.
- **Data Interface:** Yüksek hacimli veri aktarımı.
- **Interrupt/Event Interface:** İşlem tamamlanması, hata veya olay bildirimi.
- **Memory Interface:** Destekleniyorsa bellek okuma ve yazma istekleri.
- **Stream Interface:** Sürekli veri akışları için kullanılan arayüz.

Her düğümün bütün arayüzleri desteklemesi gerekmez. Arayüzler, birimin görevine ve kaynak gereksinimlerine göre belirlenir.

### 4.1. Temel düğüm sınıfları

| Düğüm | Görevi |
|---|---|
| CPU | Komut yürütme, işlem başlatma ve sistem kararları |
| System Control | Yapılandırma, saat, sıfırlama ve genel denetim |
| Memory Controller | Bellek erişim zamanlaması ve bellek protokolü |
| DMA Engine | Bellek ve birimler arasında veri aktarımı |
| Programmable Fabric | Yapılandırılabilir mantık ve paralel işlem |
| DSP/MAC | Sayısal sinyal ve aritmetik işlemler |
| I/O Controller | Dijital giriş/çıkış ve çevre birimi bağlantıları |
| ADC/DAC Interface | Analog ve dijital veri yolları |
| Peripheral Engine | UART, SPI, I²C, CAN ve benzeri protokoller |
| Display Controller | Görüntü zamanlaması ve görüntü verisi aktarımı |
| Local Memory | Birime veya işlem alanına yakın bellek |
| FIFO/Buffer | Geçici veri depolama ve hız farklılıklarını dengeleme |

Bu tablo mantıksal düğüm sınıflarını tanımlar. Fiziksel olarak bazı sınıflar birleştirilebilir veya aynı donanım bloğu içerisinde uygulanabilir.

## 5. Kontrol ve Veri Yolları

Chip Fabric, iki mantıksal trafik sınıfını ayırt eder.

### 5.1. Kontrol Trafiği

Kontrol trafiği; komutları, yapılandırma kayıtlarını, durum bilgilerini ve erişim isteklerini kapsar.

Örnekler:

- DMA aktarımının başlatılması.
- ADC örnekleme ayarlarının değiştirilmesi.
- Bir işlem biriminin yapılandırılması.
- Bellek erişim isteğinin bildirilmesi.
- Kesme veya hata durumunun sorgulanması.

Kontrol trafiği düşük veri hacmine sahip olabilir; ancak gecikme ve erişim kuralları açısından önemlidir.

### 5.2. Veri Trafiği

Veri trafiği, işlem sırasında taşınan asıl verileri kapsar.

Örnekler:

- Bellekten DSP birimine veri aktarımı.
- ADC örneklerinin FIFO'ya yazılması.
- Programmable Fabric ile bellek arasında veri aktarımı.
- Görüntü tamponundan Display Controller'a veri okunması.
- DMA ile büyük bellek bloklarının kopyalanması.

Kontrol ve veri trafiği mantıksal olarak ayrıdır; bunların mutlaka iki fiziksel olarak bağımsız ağ üzerinde uygulanması gerekmez.

## 6. Bağlantı Topolojisi

Önerilen başlangıç yaklaşımı, hiyerarşik ve bölümlere ayrılmış bir bağlantı ağıdır.

### 6.1. Yerel Bağlantı

Birbirine yakın mantık kaynakları ve yerel bellekler arasındaki kısa mesafeli iletişimi sağlar.

Özellikle Programmable Fabric içerisindeki LUT, FF, yerel RAM ve komşu işlem kaynaklarının bağlantılarında kullanılır.

### 6.2. Bölgesel Bağlantı

Bir küme veya işlevsel blok içerisindeki kaynakları birbirine bağlar.

Örnekler:

- DSP/MAC grubu ile yerel FIFO'lar.
- ADC grubu ile örnek tamponları.
- Programmable Fabric kümesi ile blok bellek.
- Bir periferik denetleyici ile kendi veri tamponu.

### 6.3. Genel Çip İçi Bağlantı

CPU, bellek denetleyicisi, DMA ve farklı işlevsel bloklar arasındaki iletişimi sağlar.

Bütün veri trafiğinin tek bir fiziksel hat üzerinde taşınması zorunlu değildir. Uygun ürün seviyelerinde birden fazla bağlantı segmenti ve paralel veri yolu kullanılabilir.

**Tasarım hedefi:** Gereksiz veri geçişlerini, ortak hat üzerindeki tıkanıklıkları ve uzak kaynak erişimlerini azaltmak.

Kesin topoloji; silikon alanı, güç tüketimi, hedef saat frekansı, bağlantı gecikmesi ve eşzamanlı trafik gereksinimleri değerlendirildikten sonra belirlenmelidir.

## 7. CPU'nun Çalışma Modeli

CPU, Chip Fabric'in her veri hareketini tek tek yönetmek yerine görev ve aktarım tanımlarını ilgili birimlere iletir.

Örnek bir DMA işlemi:

1. CPU kaynak adresini, hedef adresini ve aktarım boyutunu belirler.
2. CPU, DMA Engine kayıtlarını yapılandırır.
3. DMA aktarımı başlatır.
4. Chip Fabric, ilgili veri isteklerini hedeflere yönlendirir.
5. DMA veriyi aktarır.
6. İşlem tamamlandığında DMA, durum bilgisini ve gerekirse bir kesmeyi bildirir.
7. CPU, aktarım sürerken bağımsız komutları yürütmeye devam edebilir.

Bu çalışma modeli, CPU'nun işlem başlatıldıktan sonra mutlaka beklemesini gerektirmez.

Ancak CPU'nun beklemeden devam edebilmesi; komutların bağımlılığına, senkronizasyon kurallarına ve kaynakların hazır olmasına bağlıdır. Fabric tek başına bütün beklemeleri ortadan kaldırmaz.

## 8. DMA ve Chip Fabric İlişkisi

DMA Engine ve Chip Fabric ayrı mimari bileşenlerdir.

**DMA Engine:**

- Aktarım kaynağını ve hedefini belirler.
- Veri boyutunu ve aktarım biçimini takip eder.
- Desteklenen bellek ve çevre birimi aktarımlarını yürütür.
- Aktarım tamamlanmasını ve hataları raporlar.

**Chip Fabric:**

- DMA'nın erişim isteklerini taşır.
- İstekleri hedef düğümlere yönlendirir.
- Ortak kaynaklara erişimi düzenler.
- Veri aktarımının bağlantı kaynaklarını kullanmasını sağlar.

DMA, veriyi yorumlamak veya her durumda işlemek zorunda değildir. Filtreleme, dönüştürme ya da protokol çözümleme gerekiyorsa bu görevler uygun işlem birimine atanır.

Bir DMA aktarımının başlatılabilmesi, ilgili kaynağa erişim izni bulunduğu ve gerekli hedefin hazır olduğu anlamına gelmelidir.

## 9. Bellek Erişim Modeli

Bellekler, Chip Fabric'e bağlanan hedefler veya belirli işlem birimlerine ait yerel kaynaklar olarak ele alınır.

Desteklenmesi öngörülen bellek sınıfları:

- CPU kayıtları.
- FIFO ve geçici tamponlar.
- Programmable Fabric dağıtık RAM'i.
- Programmable Fabric blok RAM'i.
- Çip içi SRAM.
- MOSRAM bellek denetleyicisi ve bellek alanı.
- MSSD kalıcı depolama denetleyicisi ve depolama alanı.

MOSRAM ve MSSD bu mimaride henüz fiziksel olarak doğrulanmış bellek teknolojileri değil, geliştirilmekte olan tasarım kavramlarıdır.

Her bellek hedefinin erişim özellikleri ayrıca tanımlanmalıdır:

- Hangi düğümlerin erişebildiği.
- Okuma ve yazma izinleri.
- Erişim gecikmesi.
- Sürdürülebilir bant genişliği.
- Eşzamanlı erişim desteği.
- Hata ve zaman aşımı davranışı.

Her düğümün her belleğe erişmesi zorunlu değildir.

## 10. Arbitraj ve Kaynak Paylaşımı

Birden fazla düğüm aynı anda aynı hedefe erişmek istediğinde arbitraj gerekir.

Değerlendirilecek politikalar:

- Round-robin.
- Sabit öncelik.
- Ağırlıklı öncelik.
- Gerçek zamanlı trafik için ayrılmış bant genişliği.
- Gecikme sınırlarına duyarlı zamanlama.

Tek bir politikanın bütün trafik türleri için en iyi sonucu vereceği varsayılmamalıdır.

Örneğin ADC veri akışı, görüntü aktarımı ve büyük bellek kopyaları farklı gecikme ve bant genişliği gereksinimlerine sahip olabilir.

Gerçek zamanlı trafik için yalnızca yüksek öncelik vermek yeterli değildir. Kuyruk uzunlukları, azami aktarım blokları ve hizmet garantileri de değerlendirilmelidir.

## 11. FIFO, Backpressure ve Hata Yönetimi

FIFO'lar, veri üreten ve tüketen birimlerin farklı hızlarda çalışabilmesini destekler.

Her veri yolunda aşağıdaki durumlar tanımlanmalıdır:

- FIFO boş.
- FIFO dolu.
- Veri hazır.
- Alıcı hazır değil.
- Aktarım durduruldu.
- Taşma veya veri kaybı.
- Zaman aşımı.
- Hedef erişim hatası.

Backpressure, alıcı tarafın geçici olarak veri kabul edemediğini üreticiye bildirebilmesini sağlar.

Üreticinin durdurulamadığı ADC veya sürekli veri üreten kaynaklarda, tampon kapasitesi ve veri kaybı politikası ayrıca belirlenmelidir.

Hata durumlarında sistemin veriyi sessizce kaybetmesi yerine, desteklenen ölçüde durum kaydı, hata bayrağı ve yazılıma bildirim sağlaması hedeflenir.

## 12. Bant Genişliği ve Performans

Chip Fabric'in performansı yalnızca toplam veri yolu genişliğiyle ölçülemez.

Değerlendirilmesi gereken ölçütler:

- Tepe bant genişliği.
- Sürdürülebilir bant genişliği.
- Ortalama ve en kötü durum gecikmesi.
- Aynı anda gerçekleşen aktarım sayısı.
- Arbitraj bekleme süresi.
- FIFO kapasitesi.
- Bellek denetleyicisinin kapasitesi.
- Fiziksel bağlantıların alan ve güç maliyeti.

Bir veri akışının talebi, ilgili yolun sürdürülebilir kapasitesinden düşük olmalıdır:

`R_demand < R_sustainable`

Aynı bağlantı kaynağını paylaşan birden fazla akış için toplam talep de kullanılabilir kapasiteyi aşmamalıdır.

Bu aşamada nihai veri yolu genişliği, saat frekansı veya bant genişliği değeri sabitlenmemektedir. Bunlar ürün seviyelerine, hedeflenen saat hızına, fiziksel tasarıma ve eşzamanlı trafik modeline göre hesaplanmalıdır.

## 13. P1–P5 Ölçeklenebilirliği

P1–P5 modelleri aynı temel Chip Fabric mimarisini paylaşabilir; ancak kaynak sayısı, bağlantı segmentleri, hedef frekans ve eşzamanlı trafik kapasitesi farklı olabilir.

| Özellik | Mimari yaklaşım |
|---|---|
| P1–P2 | Daha az düğüm ve daha sade bağlantı topolojisi |
| P3 | Daha fazla paralel birim ve genişleyen trafik gereksinimi |
| P4–P5 | Daha fazla bağlantı segmenti, daha yüksek eşzamanlılık ve daha gelişmiş arbitraj ihtiyacı |

Bu tablo nitel bir ölçeklendirme yaklaşımıdır. Her model için kesin düğüm sayıları, fiziksel bağlantı kaynakları ve performans değerleri henüz belirlenmemiştir.

## 14. Açık Tasarım Kararları

Sürüm 1.0 öncesinde aşağıdaki konular kesinleştirilmelidir:

1. Chip Fabric'in fiziksel topolojisi ve bağlantı segmentleri.
2. Her düğümün destekleyeceği kontrol ve veri arayüzleri.
3. Aynı anda desteklenecek bellek ve veri aktarımı sayısı.
4. DMA kanal sayısı ve aktarım tanımlama modeli.
5. Arbitraj politikaları ve gerçek zamanlı trafik garantileri.
6. FIFO derinlikleri ve backpressure davranışı.
7. Bellek erişim izinleri ve veri tutarlılığı kuralları.
8. Hata, zaman aşımı ve kesme bildirimleri.
9. P1–P5 için fiziksel alan, güç ve performans hedefleri.
10. Programmable Fabric ile genel Chip Fabric arasındaki kesin arayüz.

Bu kararlar verilmeden nihai silikon bağlantı şeması veya kesin performans iddiası oluşturulmamalıdır.

## 15. Sonuç

NEXSUS Chip Fabric, programlanabilir çip içerisindeki birimlerin birbirleriyle doğrudan ve verimli biçimde iletişim kurmasını sağlayan dahili bağlantı mimarisidir.

CPU'nun görevi komutları yürütmek, görevleri başlatmak ve sonuçları değerlendirmektir. Chip Fabric bağlantı ve kaynak paylaşımını yönetir. DMA veri aktarımını yürütür. Programmable Fabric ise kullanıcı tarafından yapılandırılabilen işlem kaynaklarını sağlar.

Bu ayrım, CPU'nun her veri hareketinin merkezinde bulunmasını önlemeyi ve çip içindeki kaynakların mümkün olduğunca bağımsız çalışmasını hedefler.

**Bir sonraki tasarım aşaması:** Chip Fabric düğüm ve arayüz matrisi. Her düğümün hangi kaynaklara erişeceği, hangi veri yollarını kullanacağı ve aynı anda kaç işlem yürütebileceği bu matriste tanımlanacaktır.

---
