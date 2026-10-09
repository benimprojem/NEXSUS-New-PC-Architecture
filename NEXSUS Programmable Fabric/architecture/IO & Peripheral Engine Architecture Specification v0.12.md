# NEXSUS I/O & Peripheral Engine Architecture Specification

**Doküman Kodu:** NEXSUS-IO-012  
**Sürüm:** 1.0  
**Durum:** Mimari Taslak  
**Kapsam:** NEXSUS programlanabilir çipinin giriş/çıkış, analog arayüz ve çevre birimi protokol altyapısı

---

## 1. Amaç

NEXSUS I/O sistemi, fiziksel giriş/çıkış bağlantılarını dahili işlem kaynaklarına bağlar ve harici cihazlarla veri alışverişini gerçekleştirir.

Temel hedefler:

- Fiziksel pinleri farklı işlevler için yapılandırabilmek.
- GPIO ve analog giriş/çıkış işlevlerini desteklemek.
- UART, SPI, I²C ve CAN gibi protokolleri donanım motorlarıyla yürütmek.
- Sensör verilerini CPU'ya sürekli müdahale gerektirmeden işlemek.
- DMA ve FIFO üzerinden yüksek hacimli veri aktarımını desteklemek.
- Programmable Fabric ile özel giriş/çıkış protokollerinin oluşturulmasını sağlamak.

I/O sistemi, Chip Fabric'in yerine geçmez. Fiziksel sinyallerin alınması, elektriksel arayüzlerin yönetilmesi ve protokollerin uygulanması I/O tarafının; verilerin çip içindeki diğer birimlere aktarılması ise Chip Fabric'in sorumluluğundadır.

## 2. I/O Alt Sisteminin Yapısı

I/O sistemi aşağıdaki mantıksal katmanlardan oluşur:

1. **Physical I/O:** Çipin dış bağlantı pinleri ve elektriksel arayüzleri.
2. **I/O Bank:** Pinlerin elektriksel yapılandırması ve grup yönetimi.
3. **I/O Router:** Pinlerin GPIO veya belirli çevre birimi işlevlerine atanması.
4. **Peripheral Engine:** Seri protokoller, zamanlayıcılar, sayaçlar ve yakalama işlevleri.
5. **Analog Interface:** ADC, DAC ve gerekli analog ön uç devreleri.
6. **FIFO/Buffer:** Giriş ve çıkış verilerinin geçici saklanması.
7. **Chip Fabric Interface:** Verilerin dahili işlem ve bellek birimlerine aktarılması.

Bu katmanlar mantıksal görev ayrımını ifade eder; fiziksel olarak ayrı bloklar olmaları zorunlu değildir.

## 3. I/O Bank ve Fiziksel Pinler

I/O Bank, fiziksel pinlerin elektriksel özelliklerini ve yapılandırmasını yönetir.

Desteklenmesi değerlendirilecek işlevler:

- Dijital giriş.
- Dijital çıkış.
- Çift yönlü GPIO.
- Pull-up ve pull-down.
- Açık drenaj (open-drain).
- Kenar algılama.
- Kesme üretimi.
- Zaman damgalı olay yakalama.
- Uygun pinlerde alternatif çevre birimi işlevleri.

Her pin bütün işlevleri desteklemek zorunda değildir. Analog ve yüksek hızlı dijital işlevlerin aynı pin üzerinde kullanılması, fiziksel tasarıma ve elektriksel sınırlara bağlıdır.

Pin gerilimleri, sürme kapasitesi, toleranslar ve koruma devreleri ayrıca elektriksel tasarım aşamasında belirlenmelidir.

## 4. I/O Router

I/O Router, fiziksel pinleri ilgili mantıksal işlevlere bağlar.

Örnek eşleştirmeler:

- Pin → GPIO girişi.
- GPIO çıkışı → Pin.
- Pin → UART RX.
- UART TX → Pin.
- Pin → SPI veya I²C işlevi.
- Pin → Timer Capture.
- Analog pin → ADC giriş yolu.

Pin eşleştirmeleri, her ürün modelinin fiziksel pin sayısına ve çevre birimi kaynaklarına göre belirlenir.

Bir pinin iki işlev tarafından aynı anda kullanılması mümkün değilse yapılandırma sistemi bu çakışmayı önlemelidir.

## 5. GPIO ve Zamanlama Birimleri

GPIO, genel amaçlı dijital giriş ve çıkış işlevlerini sağlar.

Ek zamanlama kaynakları şunları içerebilir:

- Timer.
- Counter.
- PWM Generator.
- Input Capture.
- Output Compare.
- Edge Detector.
- Debounce Logic.
- Trigger Generator.

Bu işlevler sensör ölçümü, motor kontrolü, zamanlama, olay sayımı ve dijital sinyal üretimi için kullanılabilir.

Zaman kritik işlemlerin doğrudan donanımda gerçekleştirilmesi, CPU kesme gecikmesine bağımlılığı azaltabilir.

## 6. ADC ve Analog Giriş

ADC alt sistemi analog sinyalleri dijital örneklere dönüştürür.

Mantıksal veri yolu:

`Analog Pin → Protection → Analog Front-End → Channel MUX → ADC → Sample FIFO → DMA/Fabric`

Temel bileşenler:

- Giriş koruması.
- Gerekli analog ön uç ve koşullandırma devreleri.
- Kanal seçici.
- ADC dönüşüm motoru.
- Örnek tamponu.
- Durum ve hata kayıtları.

Birden fazla fiziksel analog giriş, uygun bir kanal seçici aracılığıyla aynı ADC motorunu paylaşabilir. Ancak bu yöntem, bütün kanalların aynı anda örneklenmesini sağlamaz.

Eşzamanlı örnekleme gerekiyorsa yeterli sayıda bağımsız ADC motoru veya uygun eşzamanlı örnekleme donanımı gerekir.

Örnekleme frekansı, çözünürlük, analog bant genişliği ve toplam kanal kapasitesi fiziksel tasarımda birlikte değerlendirilmelidir.

## 7. DAC ve Analog Çıkış

DAC, dijital veriyi analog çıkış sinyaline dönüştürür.

Mantıksal veri yolu:

`Chip Fabric/Buffer → DAC → Analog Output Stage → Pin`

DAC verisi CPU tarafından tek tek yazılabileceği gibi, desteklenen uygulamalarda DMA ve FIFO üzerinden de aktarılabilir.

Gerekli çıkış sürücüsü, filtreleme, doğruluk ve gerilim aralığı ürünün elektriksel gereksinimlerine göre belirlenir.

## 8. Peripheral Engine

Peripheral Engine, belirli protokolleri ve zamanlama işlevlerini donanımda yürütür.

### 8.1. UART

Temel işlevler:

- TX/RX.
- Baud-rate üretimi.
- FIFO.
- Parite ve hata algılama.
- Kesme ve durum kayıtları.
- Destekleniyorsa DMA aktarımı.

### 8.2. SPI

Temel işlevler:

- SCLK, MOSI, MISO ve CS.
- SPI çalışma modları.
- Veri kaydırma motoru.
- FIFO.
- Aktarım durumu ve hata raporlama.
- Destekleniyorsa DMA.

### 8.3. I²C

Temel işlevler:

- SCL ve SDA kontrolü.
- Başlatma ve durdurma koşulları.
- ACK/NACK.
- Adresleme.
- Desteklenen uygulamalarda clock stretching ve arbitration.
- Hata ve zaman aşımı yönetimi.

I²C elektriksel yapısı uygun açık drenaj çıkışlarını ve harici pull-up gereksinimlerini dikkate almalıdır.

### 8.4. CAN

CAN desteği, protokol denetleyicisi ile fiziksel CAN transceiver'ını birbirinden ayırır.

Çip içinde CAN Controller bulunması, fiziksel CAN hattına bağlanmak için gereken transceiver'ın otomatik olarak çip içinde bulunduğu anlamına gelmez.

### 8.5. Özel Protokol Motoru

Programmable Fabric veya özel protokol mantığı üzerinden yapılandırılabilir protokoller uygulanabilir.

Olası kaynaklar:

- Durum makinesi.
- Zamanlayıcı.
- Veri eşleştirici.
- CRC veya checksum mantığı.
- FIFO.
- Olay ve tetikleme bağlantısı.

Özel bir protokolün desteklenmesi için protokol kurallarının açıkça tanımlanması ve mantığın yapılandırılması gerekir. Protokollerin kendiliğinden tanınması varsayılmaz.

## 9. FIFO, DMA ve Chip Fabric Entegrasyonu

I/O sisteminin yüksek hacimli veriler için CPU'ya bağımlı kalmaması hedeflenir.

Örnek ADC veri yolu:

1. ADC örneği üretir.
2. Örnek FIFO'ya yazılır.
3. DMA veriyi belleğe veya belirlenmiş bir hedefe aktarır.
4. Gerekirse Programmable Fabric veriyi filtreler veya dönüştürür.
5. CPU, tamamlanma veya eşik olayını değerlendirir.

Benzer yapı UART, SPI ve diğer veri üreten veya tüketen çevre birimleri için de uygulanabilir.

Her çevre birimi için DMA zorunlu değildir. Düşük hızlı veya basit işlevler doğrudan kayıt erişimiyle yürütülebilir.

## 10. Interrupt ve Event/Trigger Ayrımı

İki mekanizma farklı görevler üstlenir.

**Interrupt Matrix:**

- CPU'ya olay veya durum bildirir.
- Yazılımın bir işlemi ele almasını sağlar.
- Tamamlanma ve hata bildirimlerinde kullanılır.

**Event/Trigger Matrix:**

- Bir donanım olayını başka bir donanım işlevini başlatmak için kullanır.
- ADC örneklemesini tetikleyebilir.
- Timer, DMA veya Programmable Fabric işlemlerini başlatabilir.
- CPU müdahalesi olmadan donanım zincirleri oluşturabilir.

Her donanım olayının CPU kesmesine dönüşmesi gerekmez. Zaman kritik iş akışlarında doğrudan donanım tetikleme yolu tercih edilebilir.

## 11. Programmable Fabric ile İlişki

Programmable Fabric, özel I/O işleme ve protokol uygulamaları için kullanılabilir.

Örnekler:

- Özel seri protokol.
- Darbe genişliği ölçümü.
- Sensör veri filtreleme.
- Özel PWM üretimi.
- Birden fazla girişin donanım düzeyinde birleştirilmesi.
- Olay tabanlı veri yönlendirme.

Standart Peripheral Engine kaynakları genel kullanım için ayrılırken, Programmable Fabric uygulamaya özgü işlemlerin oluşturulmasını sağlar.

Böylece özel bir protokol için CPU'nun sürekli bit düzeyinde kontrol yapması gerekmez.

## 12. Ölçeklenebilirlik ve Ürün Sınırları

P1–P5 modellerinde pin sayısı, ADC motorları, Peripheral Engine sayısı ve FIFO kapasitesi farklı olabilir.

Önceki taslaklarda bulunan kaynak sayıları başlangıç hedefleridir; nihai fiziksel kaynak tahsisi değildir.

Her model için şu özellikler ayrı tanımlanmalıdır:

- Fiziksel dijital pin sayısı.
- Analog giriş sayısı.
- Eşzamanlı ADC kapasitesi.
- DAC sayısı ve özellikleri.
- UART/SPI/I²C/CAN motorları.
- Timer, PWM ve Capture kaynakları.
- DMA ile desteklenen uçlar.
- Özel protokol kapasitesi.
- Elektriksel gerilim ve sürme sınırları.

## 13. Sonuç

NEXSUS I/O ve Peripheral Engine mimarisi, fiziksel pinlerden alınan sinyallerin ve çevre birimlerinden gelen verilerin çip içerisindeki işlem kaynaklarına aktarılmasını sağlar.

I/O Bank elektriksel pin işlevlerini, I/O Router işlev eşleştirmesini, Peripheral Engine protokol yürütmesini, ADC/DAC analog dönüşümleri, DMA veri aktarımını ve Chip Fabric ise dahili bağlantıyı üstlenir.

Programmable Fabric, standart çevre birimi kaynaklarının kapsamadığı özel protokoller ve uygulamaya özgü donanım işlevleri için genişletilebilir işlem alanı sağlar.

**Sonraki aşama:** Saat, sıfırlama ve güç alanlarının temel mimarisi. Bu yapı, farklı çip birimlerinin doğru zamanda başlatılmasını, bağımsız saat alanlarının yönetilmesini ve düşük güç çalışma seçeneklerinin tanımlanmasını sağlayacaktır.
