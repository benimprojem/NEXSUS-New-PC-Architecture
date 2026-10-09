# NEXSUS Chip Fabric — Node & Interface Matrix Specification

**Doküman Kodu:** NEXSUS-CHIP-FABRIC-009  
**Sürüm:** 1.0-draft  
**Durum:** Mimari Taslak  
**Bağımlılık:** NEXSUS-CHIP-FABRIC-008  
**Kapsam:** Programlanabilir NEXSUS çipinin dahili düğümleri, arayüzleri ve erişim ilişkileri

---

## 1. Amaç

Bu doküman, NEXSUS Chip Fabric'e bağlanan mantıksal düğümleri ve bu düğümlerin desteklemesi gereken arayüzleri tanımlar.

Amaçlar:

- Çip içindeki birimlerin görev sınırlarını belirlemek.
- Kontrol ve veri trafiğini birbirinden ayırmak.
- Bellek erişim yetkilerini tanımlamak.
- CPU'nun gereksiz veri aktarım yükünü azaltmak.
- DMA ve işlem birimlerinin bağımsız çalışmasını desteklemek.
- P1–P5 modellerinde ölçeklenebilir bir bağlantı mimarisi oluşturmak.

Bu doküman mantıksal erişim modelini tanımlar. Fiziksel kablolama, kesin veri yolu genişliği, saat frekansı ve silikon alanı sonraki aşamalarda belirlenecektir.

## 2. Arayüz Tanımları

| Kısaltma | Arayüz | Görev |
|---|---|---|
| CI | Control Interface | Komut, yapılandırma ve durum kayıtları |
| DI | Data Interface | Genel veri aktarımı |
| MI | Memory Interface | Bellek okuma ve yazma istekleri |
| SI | Stream Interface | Sürekli veya akış tabanlı veri aktarımı |
| EI | Event/Interrupt Interface | Olay, tamamlanma ve hata bildirimi |
| LI | Local Interface | Birime yakın yerel kaynaklara erişim |

Bu arayüzler mantıksal arayüzlerdir. Fiziksel tasarımda birden fazla arayüz aynı bağlantı yapısını paylaşabilir veya bir arayüz birden fazla fiziksel kanala ayrılabilir.

## 3. Temel Düğüm Matrisi

| Düğüm | CI | DI | MI | SI | EI | LI |
|---|---|---|---|---|---|---|
| CPU | Evet | Evet | Evet | İsteğe bağlı | Evet | Evet |
| System Control | Evet | İsteğe bağlı | Hayır | Hayır | Evet | Evet |
| DMA Engine | Evet | Evet | Evet | Evet | Evet | İsteğe bağlı |
| Memory Controller | Evet | Evet | Hedef arayüzü | İsteğe bağlı | Evet | Evet |
| Programmable Fabric | Evet | Evet | Yapılandırılabilir | Evet | Evet | Evet |
| DSP/MAC | Evet | Evet | İsteğe bağlı | Evet | Evet | Evet |
| ADC Interface | Evet | Evet | İsteğe bağlı | Evet | Evet | Evet |
| DAC Interface | Evet | Evet | İsteğe bağlı | Evet | Evet | Evet |
| I/O Controller | Evet | Evet | İsteğe bağlı | Evet | Evet | Evet |
| Peripheral Engine | Evet | Evet | İsteğe bağlı | Evet | Evet | Evet |
| Display Controller | Evet | Evet | Evet | Evet | Evet | Evet |
| Local Memory | İsteğe bağlı | Evet | Hedef arayüzü | İsteğe bağlı | İsteğe bağlı | Evet |
| FIFO/Buffer | İsteğe bağlı | Evet | Hedef veya yerel erişim | Evet | İsteğe bağlı | Evet |

**Not:** “İsteğe bağlı” ifadesi, arayüzün mimari olarak zorunlu olmadığını belirtir. Gerçek uygulama, ilgili birimin işlevlerine göre belirlenmelidir.

## 4. Düğüm Sınıfları

Chip Fabric düğümleri üç temel sınıfa ayrılır.

### 4.1. Initiator — İstek Başlatan Düğümler

Bir kaynak üzerinde okuma, yazma veya veri aktarımı başlatabilen düğümlerdir.

Örnekler:

- CPU
- DMA Engine
- Programmable Fabric içindeki bellek erişim birimleri
- Display Controller'ın görüntü DMA birimi
- MI arayüzü bulunan DSP veya diğer işlem birimleri

Bir düğümün initiator olması, bütün bellek ve çevre birimlerine erişebileceği anlamına gelmez. Erişim yetkileri ayrıca tanımlanır.

### 4.2. Target — İstek Alan Düğümler

Erişim isteklerini kabul eden ve bunlara yanıt veren düğümlerdir.

Örnekler:

- SRAM
- MOSRAM Controller
- MSSD Controller
- FIFO/Buffer
- Peripheral Register Bank
- Programmable Fabric Block RAM
- Display Buffer

Bir target, birden fazla initiator tarafından kullanılabilir. Eşzamanlı erişimlerde arbitraj ve erişim kuralları uygulanır.

### 4.3. Processing Node — İşlem Düğümleri

Veri üzerinde hesaplama, dönüştürme veya kontrol işlemi gerçekleştiren düğümlerdir.

Örnekler:

- DSP/MAC
- Programmable Fabric
- ADC örnek işleme birimleri
- Filtreleme ve sinyal işleme motorları

İşlem düğümleri, veri arayüzü veya stream arayüzü üzerinden veri alıp sonuç üretebilir. Belleğe doğrudan erişim yalnızca bu özellik tasarımda destekleniyorsa sağlanır.

## 5. Mantıksal Erişim Matrisi

Aşağıdaki matris, ilk uygulama için önerilen erişim modelidir.

| Kaynak düğüm | Sistem belleği | Yerel bellek | FIFO/Buffer | Peripheral kayıtları |
|---|---|---|---|---|
| CPU | İzinli | İzinli | İzinli | İzinli |
| DMA Engine | İzin verilen bölgelerde | İzin verilen bölgelerde | İzin verilen hedeflerde | Yalnızca desteklenen uçlarda |
| Programmable Fabric | Yapılandırmaya bağlı | İzinli | İzinli | Yapılandırmaya bağlı |
| DSP/MAC | Yapılandırmaya bağlı | İzinli | İzinli | Normalde doğrudan gerekmez |
| ADC Interface | DMA veya desteklenen yerel yol üzerinden | İzinli | İzinli | Kendi kontrol kayıtları |
| Peripheral Engine | DMA veya desteklenen yerel yol üzerinden | İzinli | İzinli | Kendi kontrol kayıtları |
| Display Controller | Görüntü tamponu okuma izniyle | İzinli | İzinli | Kendi kontrol kayıtları |
| System Control | Normal veri erişimi gerekmez | Sınırlı | Sınırlı | İzinli |

Bu matris, bellek ve denetleyicilerin kesin yerleşimi belirlenene kadar geçici kabul edilir. “Sistem belleği” tek bir fiziksel teknoloji anlamına gelmez; SRAM, gelecekte doğrulanmış MOSRAM veya başka bir bellek denetleyicisi üzerinden erişilebilen alanları kapsayabilir.

## 6. CPU ve DMA Arasındaki İş Bölümü

CPU, veri aktarımının tanımını oluşturur; DMA ise aktarımı yürütür.

Örnek:

1. CPU, DMA kaynak ve hedef tanımlarını yazar.
2. DMA, aktarımın geçerliliğini kontrol eder.
3. DMA, Chip Fabric üzerinden kaynak ve hedef erişimlerini başlatır.
4. Arbitraj birimi, ortak bağlantı veya hedef kaynak için erişim sırasını belirler.
5. Veri aktarımı tamamlandığında DMA durum bilgisini günceller.
6. Gerekirse CPU'ya kesme gönderilir.

CPU'nun aktarım sürerken bağımsız işlere devam etmesi hedeflenir. Ancak aynı veriyi kullanacak sonraki bir işlem, aktarımın tamamlandığını doğrulamalıdır.

## 7. Programmable Fabric Arayüzü

Programmable Fabric'in genel Chip Fabric'e tek bir dar bağlantıyla bağlanması zorunlu tutulmamalıdır.

Önerilen mantıksal bağlantılar:

- **Configuration Path:** LUT, FF, DSP, bağlantı ve durum makinelerinin yapılandırılması.
- **Data Path:** İşlenen verilerin aktarılması.
- **Memory Path:** Desteklenen yerel veya sistem belleği erişimleri.
- **Stream Path:** Sürekli veri akışları.
- **Event Path:** İşlem tamamlanması, tetikleme ve hata bildirimleri.

Bu arayüzlerin tümü fiziksel olarak ayrı olmak zorunda değildir. Amaç, yapılandırma trafiğinin yüksek hacimli veri trafiğiyle gereksiz yere rekabet etmesini önlemektir.

## 8. Bellek ve FIFO Hedefleri

Her bellek veya FIFO hedefi aşağıdaki bilgileri tanımlamalıdır:

- Benzersiz hedef kimliği.
- Adres aralığı veya yerel adresleme biçimi.
- Okuma ve yazma yetkileri.
- Desteklenen erişim boyutları.
- Azami aktarım boyutu.
- Eşzamanlı erişim davranışı.
- FIFO dolu/boş davranışı.
- Hata ve zaman aşımı yanıtı.

Yerel bellekler, mümkün olduğunda kendi işlem birimlerine yakın tutulur. Bu yaklaşım genel bağlantı ağındaki trafiği azaltabilir. Bununla birlikte, yerel bellek kapasitesi ve bağlantı maliyeti ürün seviyesine göre belirlenmelidir.

## 9. Arbitraj ve Erişim Sırası

Birden fazla initiator aynı target'a erişmek istediğinde erişim sırası belirlenmelidir.

İlk tasarım için:

- Kontrol kayıtlarına erişim kısa ve sınırlı işlemlerle yürütülmelidir.
- Büyük veri aktarımları, uygun olduğu durumlarda burst işlemleriyle yapılmalıdır.
- Gerçek zamanlı akışlar için gecikme sınırları tanımlanmalıdır.
- Uzun süren bir aktarım diğer bütün düğümlerin süresiz beklemesine neden olmamalıdır.
- Aynı veri üzerinde bağımlı işlemler, açık senkronizasyon kurallarıyla sıralanmalıdır.

Arbitraj politikası hedefe göre farklılaşabilir. Tek bir global öncelik sıralaması bütün kaynaklar için zorunlu değildir.

## 10. Hata ve Durum Bildirimi

Her düğüm, desteklediği ölçüde aşağıdaki durumları raporlamalıdır:

- İşlem tamamlandı.
- İşlem devam ediyor.
- Kaynak veya hedef erişim hatası.
- Yetkisiz erişim.
- Zaman aşımı.
- FIFO taşması veya veri kaybı.
- Yapılandırma hatası.
- İşlem iptali.

Hata bildirimi bir durum kaydı, olay veya kesme yoluyla yapılabilir. Her olayın CPU'ya ayrı bir kesme üretmesi zorunlu değildir; olaylar birleştirilebilir veya durum kayıtlarında toplanabilir.

## 11. Açık Kararlar

Bir sonraki tasarım aşamasında aşağıdakiler kesinleştirilmelidir:

1. Her düğümün gerçek initiator ve target yetenekleri.
2. Hangi düğümlerin sistem belleğine doğrudan erişeceği.
3. Programmable Fabric'in bellek erişim modeli.
4. DMA motoru sayısı ve aktarım kuyruğu yapısı.
5. FIFO ve yerel bellek kaynaklarının hangi birimler arasında paylaşılacağı.
6. Arbitraj ve gerçek zamanlı trafik garantileri.
7. Adres alanı ve bellek eşleme kuralları.
8. Veri tutarlılığı ve senkronizasyon modeli.
9. P1–P5 için kaynak ölçeklendirme sınırları.

## 12. Sonuç

Bu matris, NEXSUS Chip Fabric'in hangi birimleri birbirine bağlayacağını ve bu birimlerin hangi erişim türlerini kullanacağını tanımlayan ilk mantıksal çerçevedir.

Temel tasarım kuralı şudur:

**Her düğüm yalnızca ihtiyaç duyduğu arayüzlere ve kaynaklara erişmelidir. Veri aktarımı, işlem yürütme ve kontrol birbirinden ayrılmalı; CPU'nun her veri hareketini yönetmesi gerekmemelidir.**

Bir sonraki aşama, bu mantıksal erişim modelini adresleme, bellek eşleme, senkronizasyon ve veri tutarlılığı kurallarıyla tamamlamaktır.
