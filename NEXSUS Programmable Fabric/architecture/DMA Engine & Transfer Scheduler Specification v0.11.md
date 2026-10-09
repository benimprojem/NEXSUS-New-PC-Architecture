# NEXSUS DMA Engine & Transfer Scheduler Specification

**Doküman Kodu:** NEXSUS-DMA-011  
**Sürüm:** 1.0  
**Durum:** Mimari Taslak  
**Kapsam:** NEXSUS programlanabilir çipinde bağımsız veri aktarımı ve aktarım planlama sistemi

---

## 1. Amaç

NEXSUS DMA (Direct Memory Access) sistemi, CPU'nun her veri aktarımını doğrudan yönetmesine gerek kalmadan bellekler ve desteklenen işlem birimleri arasında veri taşımak için tasarlanır.

DMA'nın temel hedefleri:

- CPU üzerindeki veri kopyalama yükünü azaltmak.
- Bellek ve çevre birimleri arasındaki veri akışını otomatikleştirmek.
- Programmable Fabric ve DSP/MAC gibi işlem birimlerinin veri ihtiyaçlarını karşılamak.
- Sürekli veri üreten ADC ve benzeri birimlerin verilerini tamponlara aktarmak.
- Eşzamanlı aktarım taleplerini düzenlemek.
- Aktarım tamamlanmasını CPU'ya bildirmek.

DMA bir hesaplama birimi değil, veri aktarım birimidir. Veri üzerinde filtreleme, matematiksel işlem veya protokol çözümleme gibi görevler ayrı işlem birimlerine aittir.

## 2. Temel Mimari

DMA sistemi üç mantıksal bileşenden oluşur:

| Bileşen | Görev |
|---|---|
| DMA Engine | Veri aktarımını yürütür |
| Transfer Queue | Bekleyen aktarım taleplerini tutar |
| Transfer Scheduler / Arbiter | Aktarım sırasını ve kaynak paylaşımını yönetir |

Bu bileşenlerin fiziksel olarak ayrı donanım blokları olması zorunlu değildir. Küçük modellerde bazı görevler birleştirilebilir; yüksek kapasiteli modellerde daha fazla bağımsızlık sağlanabilir.

DMA sistemi Chip Fabric üzerinden bellek denetleyicilerine ve desteklenen çevre birimlerine erişir.

## 3. Aktarım Modeli

Bir DMA aktarımı genel olarak aşağıdaki bilgileri içerir:

- Kaynak adresi veya kaynak birim.
- Hedef adresi veya hedef birim.
- Aktarılacak veri miktarı.
- Aktarım yönü.
- Kaynak ve hedef veri biçimi.
- Başlatma koşulu.
- Tamamlanma ve hata durumu.

Bir aktarım aşağıdaki durumları izleyebilir:

1. **Configured:** Aktarım tanımlandı.
2. **Queued:** Aktarım kuyruğa alındı.
3. **Running:** Aktarım devam ediyor.
4. **Completed:** Aktarım başarıyla tamamlandı.
5. **Error:** Aktarım sırasında hata oluştu.
6. **Cancelled:** Destekleniyorsa aktarım iptal edildi.

Bu durumlar mantıksal modeldir; kesin kayıt alanları ve komut biçimi daha sonra belirlenebilir.

## 4. CPU ile İş Bölümü

CPU, aktarımın ne zaman ve hangi kaynaklar arasında gerçekleşeceğini tanımlar. DMA, tanımlanan aktarımı yürütür.

Örnek iş akışı:

1. CPU, kaynak ve hedefi belirler.
2. CPU, aktarım boyutunu ve gerekli parametreleri ayarlar.
3. DMA, isteği doğrular ve kuyruğa alır.
4. Scheduler, uygun kaynakları değerlendirerek aktarımı başlatır.
5. DMA, Chip Fabric üzerinden veriyi taşır.
6. DMA, tamamlanma veya hata durumunu kaydeder.
7. Gerekirse CPU'ya kesme gönderilir.

CPU, aktarım sürerken bağımsız komutları yürütmeye devam edebilir. Ancak sonraki komutlar aktarılan veriye bağlıysa tamamlanma veya senkronizasyon koşulu beklenmelidir.

## 5. Desteklenen Aktarım Türleri

### 5.1. Bellekten Belleğe

Bir bellek bölgesindeki verinin başka bir bölgeye aktarılması.

Kullanım alanları:

- Veri kopyalama.
- Tampon değiştirme.
- İşlem öncesi veri hazırlama.
- Büyük blokların taşınması.

### 5.2. Çevre Biriminden Belleğe

ADC, UART, SPI veya benzeri birimin ürettiği verinin bellek veya tampon alanına aktarılması.

Kullanım alanları:

- Sensör verisi toplama.
- Sürekli örnekleme.
- Paket ve seri iletişim alımı.

### 5.3. Bellekten Çevre Birimine

Bellekteki verinin bir çıkış birimine aktarılması.

Kullanım alanları:

- DAC veri akışı.
- SPI/UART gönderimi.
- Desteklenen ekran veya protokol veri yolları.

### 5.4. Bellek ile İşlem Birimi Arasında

DSP/MAC veya Programmable Fabric gibi birimlerin veri alıp sonuç üretmesine yönelik aktarım.

İşlem biriminin doğrudan bellek erişimi yoksa DMA, veriyi yerel FIFO veya tampon üzerinden aktarabilir.

Her aktarım türü bütün ürünlerde zorunlu değildir; donanım kaynaklarına ve ilgili birimlerin arayüzlerine bağlıdır.

## 6. Transfer Scheduler ve Arbitraj

Birden fazla aktarım aynı anda talep edildiğinde Scheduler, hangi aktarımın hangi kaynakları kullanacağını belirler.

Değerlendirilecek politikalar:

- Round-robin.
- Öncelik tabanlı zamanlama.
- Ağırlıklı paylaşım.
- Gerçek zamanlı aktarım için gecikme hedefleri.
- Kaynak veya hedef bazında erişim sıralaması.

Scheduler'ın görevi yalnızca sıradaki aktarımı seçmek değildir. Ortak belleğin ve Chip Fabric bağlantılarının kapasitesini de dikkate alması gerekir.

Yüksek öncelik, tek başına kesin gecikme garantisi sağlamaz. Gerçek zamanlı akışlar için aktarım büyüklüğü, kuyruk sınırları ve ayrılmış kaynaklar da değerlendirilmelidir.

## 7. Burst ve Sürekli Veri Akışı

DMA, uygun bellek ve arayüzler desteklediğinde verileri bloklar hâlinde aktarabilir.

**Burst aktarımı**, her veri öğesi için ayrı bir kontrol işlemi gereksinimini azaltabilir.

Sürekli veri üreten kaynaklarda DMA, FIFO doluluk seviyesine veya bir olay/tetikleme sinyaline göre çalışabilir.

Bu model özellikle ADC örnekleri ve yüksek hacimli veri akışları için önemlidir.

Aktarım bloklarının büyüklüğü; gecikme, bellek verimliliği, FIFO kapasitesi ve diğer düğümlerin erişim gereksinimleri arasında dengelenmelidir.

## 8. FIFO ve Backpressure

DMA, veri üreten ve tüketen birimlerin farklı hızlarda çalışmasını desteklemek için FIFO'larla birlikte kullanılabilir.

- Kaynak hazır değilse aktarım bekleyebilir.
- Hedef veri kabul edemiyorsa aktarım duraklatılabilir.
- FIFO dolarsa üretici destekliyorsa durdurulabilir veya yavaşlatılabilir.
- Üretici durdurulamıyorsa taşma politikası uygulanmalıdır.

Veri kaybının kabul edilemediği uygulamalarda FIFO kapasitesi ve en kötü durum hizmet gecikmesi birlikte hesaplanmalıdır.

## 9. Tamamlanma ve Senkronizasyon

DMA işleminin tamamlanması, verinin hedef tarafından güvenle kullanılabileceği anlamına gelecek şekilde tanımlanmalıdır.

Bunun için sistem:

- Aktarım durumunu raporlamalı.
- Gerekli bellek yazmalarının tamamlandığını belirtmeli.
- İşlem birimleri arasındaki veri bağımlılıklarını yönetmeli.
- Gerektiğinde olay veya kesme üretmeli.

Bellek yazmalarının hangi noktada tamamlanmış sayılacağı ve veri tutarlılığı kuralları, kullanılan bellek ve bağlantı mimarisine bağlıdır.

CPU, DMA tamamlanma bildirimi almadan aktarım sonucunu kullanmamalıdır; yalnızca bir isteğin kuyruğa alınmış olması tamamlandığı anlamına gelmez.

## 10. Hata Yönetimi

DMA aşağıdaki hata türlerini raporlayabilmelidir:

- Geçersiz kaynak veya hedef.
- Yetkisiz bellek erişimi.
- Erişilemeyen hedef.
- Zaman aşımı.
- FIFO taşması veya veri kaybı.
- Aktarım sırasında iptal.
- Desteklenmeyen aktarım biçimi.

Hata durumunda aktarımın durdurulması, kısmi aktarım miktarının kaydedilmesi ve yazılıma bildirim sağlanması değerlendirilmelidir.

Hata sonrasında otomatik yeniden deneme yalnızca ilgili aktarım türü için güvenli olduğunda kullanılmalıdır.

## 11. DMA ve Diğer Birimler

| Birim | DMA ile ilişki |
|---|---|
| CPU | Aktarımları tanımlar ve sonuçları değerlendirir |
| Chip Fabric | Veri isteklerini taşır ve kaynak paylaşımını sağlar |
| Memory Controller | Bellek erişimini yürütür |
| ADC Interface | Örnekleri FIFO veya bellek alanına aktarabilir |
| Peripheral Engine | Gelen ve giden veri akışlarını destekler |
| DSP/MAC | İşlem için veri alabilir ve sonuç aktarabilir |
| Programmable Fabric | FIFO, yerel bellek veya desteklenen bellek yollarını kullanabilir |
| Display Controller | Görüntü tamponundan veri okumak için DMA benzeri bir aktarım motoru kullanabilir |

Display Controller içinde ayrı bir DMA motoru bulunması zorunlu değildir. Genel DMA ile ortak bir aktarım motoru veya ayrı bir görüntü aktarım birimi seçenekleri sonraki tasarımda karşılaştırılabilir.

## 12. Ürün Ölçeklendirmesi

P1–P5 ailesinde DMA kapasitesi, eşzamanlı veri akışları ve fiziksel kaynak bütçesine göre ölçeklenmelidir.

Önceki taslaklarda belirtilen DMA kanal sayıları yalnızca başlangıç hedefleridir; nihai değerler olarak kabul edilmemelidir.

Ürün bazında belirlenmesi gerekenler:

- Bağımsız DMA Engine sayısı.
- Aynı anda yürütülebilen aktarım sayısı.
- Aktarım kuyruğu kapasitesi.
- Desteklenen veri yolları.
- Burst ve sürekli akış desteği.
- Öncelik ve gecikme kuralları.
- Alan ve güç maliyeti.

## 13. Sonuç

NEXSUS DMA sistemi, CPU'nun her veri hareketini bizzat yürütme zorunluluğunu azaltan bağımsız aktarım altyapısıdır.

Chip Fabric iletişimi ve kaynak paylaşımını, Memory Controller bellek erişimini, DMA ise aktarımın yürütülmesini üstlenir. Bu ayrım, veri taşıma ile hesaplamanın birbirinden bağımsız ilerlemesini sağlar.

**Bir sonraki aşama:** Çip içindeki I/O ve Peripheral Engine mimarisini DMA ve Chip Fabric ile ilişkilendirmek. Böylece ADC, GPIO, seri protokoller ve diğer giriş/çıkış kaynaklarının veri akışı aynı genel mimari içerisinde tamamlanabilir.
