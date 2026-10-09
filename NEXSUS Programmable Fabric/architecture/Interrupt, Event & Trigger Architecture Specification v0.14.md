# NEXSUS Interrupt, Event & Trigger Architecture Specification

**Doküman Kodu:** NEXSUS-IRQ-014  
**Sürüm:** 1.0  
**Statü:** Mimari Taslak  
**Kapsam:** NEXSUS programlanabilir çip

---

## 1. Amaç

Bu belgenin amacı, NEXSUS içindeki işlem birimlerinin tamamlanma, hata, veri hazır olma ve harici sinyal gibi durumları birbirlerine nasıl bildireceğini tanımlamaktır.

Tasarım üç ayrı mekanizmaya dayanır:

- **Interrupt (Kesme):** CPU'nun veya belirlenmiş bir kontrol biriminin müdahalesini gerektiren durum bildirimi.
- **Event (Olay):** Bir birimin meydana gelen durumu diğer birimlere bildirmesi.
- **Trigger (Tetikleme):** Bir olayın başka bir birimde belirli bir işlemi başlatması.

Bu mekanizmaların ayrılması, CPU'nun her işlem adımını takip etme zorunluluğunu azaltmayı ve paralel çalışan birimlerin koordinasyonunu kolaylaştırmayı amaçlar.

## 2. Mimari İlkeler

NEXSUS kesme ve olay sistemi aşağıdaki ilkeleri izlemelidir:

1. Her olayın CPU'ya kesme üretmesi zorunlu olmamalıdır.
2. DMA ve çevre birimleri, uygun durumlarda başka birimleri doğrudan tetikleyebilmelidir.
3. Bir olayın birden fazla hedefe yönlendirilmesi mümkün olmalıdır.
4. Gerektiğinde bir olayın birden fazla kez meydana gelmesi kaybolmadan izlenebilmelidir.
5. Kesme öncelikleri ve maskeleme davranışları açıkça tanımlanmalıdır.
6. Saat alanları arasındaki olay aktarımı güvenli olmalıdır.
7. Hata ve tamamlanma bildirimleri, normal veri transferinden bağımsız yönetilebilmelidir.

Olay yönlendirme mekanizması, Chip Fabric ile birlikte çalışır; ancak olayların kontrol semantiği normal bellek ve veri transferi isteklerinden ayrı tanımlanır.

## 3. Interrupt — Kesme Sistemi

### 3.1. Kesme kaynakları

Kesme üretebilecek kaynaklara örnekler:

| Kaynak | Örnek durum |
|---|---|
| DMA | Transfer tamamlandı veya hata oluştu |
| Memory Controller | Bellek işlemi hatası veya kritik durum |
| I/O Engine | Veri alımı tamamlandı veya protokol hatası |
| Timer/Counter | Sayaç karşılaştırması gerçekleşti |
| Programmable Fabric | Yapılandırılmış mantık kesme isteği üretti |
| Watchdog | Zaman aşımı oluştu |
| Harici giriş | Yapılandırılmış bir sinyal algılandı |
| CPU kontrol birimi | İç hata veya özel durum oluştu |

Bunlar olası kaynaklardır. Her kaynağın ayrı fiziksel kesme hattına sahip olması gerekmez.

### 3.2. Kesme denetleyicisi

Kesme denetleyicisi aşağıdaki işlevleri sağlamalıdır:

- Kesme kaynaklarını tanımlama.
- Kaynakları etkinleştirme veya maskeleme.
- Öncelik belirleme.
- Bekleyen kesmeleri izleme.
- CPU'ya veya destekleniyorsa başka bir kontrol hedefine bildirim gönderme.
- Kesme kaynağının temizlenme ve yeniden etkinleşme davranışını yönetme.

Kesme denetleyicisi merkezi bir birim olarak tasarlanabilir. İhtiyaç büyürse dağıtık veya hiyerarşik bir yapı da değerlendirilebilir.

### 3.3. Öncelik yönetimi

Birden fazla kesme aynı anda beklediğinde denetleyici, tanımlanmış öncelik politikasına göre seçim yapmalıdır.

Öncelik seviyeleri donanımda sabitlenebilir veya yapılandırılabilir olabilir. İlk prototipte sabit öncelik tablosu daha basit bir başlangıç sağlar.

Örnek öncelik sınıfları:

1. Kritik donanım hataları.
2. Bellek veya bağlantı hataları.
3. Zaman kritik çevre birimi olayları.
4. DMA tamamlanma bildirimleri.
5. Genel zamanlayıcı ve yazılım bildirimleri.

Bu sıra bir örnektir; kesin öncelik sıralaması kullanım gereksinimlerine göre belirlenmelidir.

### 3.4. Kesme davranışı

Bir kesme kaynağı en azından şu bilgileri temsil edebilmelidir:

- Kaynak kimliği.
- Kesmenin beklemede olup olmadığı.
- Kesmenin etkinleştirilip etkinleştirilmediği.
- Önceliği.
- Kaynağın nasıl temizleneceği.

Seviyeye bağlı kesmelerde kaynak etkin kaldığı sürece kesme isteği devam edebilir. Darbe tabanlı kesmelerde ise kısa süreli isteğin kaybolmaması için uygun yakalama veya bekleyen durum mantığı gerekir.

Kesmenin temizlenmesi, kaynağın durumunu temizlemekten ayrı olabilir. Örneğin DMA tamamlanma kesmesi temizlense bile transfer sonucu, yazılım tarafından okunana kadar durum kayıtlarında tutulabilir.

## 4. Event — Olay Sistemi

### 4.1. Olay kavramı

Olay, bir birimin belirli bir durumun meydana geldiğini bildirmesidir.

Olay üreticileri arasında DMA, I/O motorları, zamanlayıcılar, Programlanabilir Fabric ve bellek denetleyicisi bulunabilir.

Olay tüketicileri ise CPU kontrol mantığı, DMA, başka bir çevre birimi veya Programlanabilir Fabric içindeki bir mantık bloğu olabilir.

Bir olayın tüketilmesi için CPU'nun devreye girmesi zorunlu değildir.

### 4.2. Olay yönlendirme

Olay yönlendirme mantığı, olay kaynağını bir veya daha fazla hedefle ilişkilendirebilir.

Örnek:

`Timer Event → DMA Start`

Bu durumda zamanlayıcı olayı DMA işlemini başlatır. CPU'nun her tetikleme anında komut vermesi gerekmez.

Başka bir örnek:

`I/O Data Ready → Programmable Fabric Processing`

Bir I/O birimi yeni veri aldığında, ilgili veri işleme akışı tetiklenebilir.

### 4.3. Olay türleri

Olaylar mantıksal olarak şu sınıflara ayrılabilir:

- **Durum olayı:** Bir durumun meydana geldiğini bildirir.
- **Tamamlanma olayı:** Bir işlemin sona erdiğini bildirir.
- **Veri olayı:** Veri girişinin veya çıkışının hazır olduğunu bildirir.
- **Hata olayı:** Bir işlemin beklenen biçimde tamamlanmadığını bildirir.
- **Zamanlama olayı:** Belirli bir zaman veya sayaç koşulunu bildirir.

Bu sınıflandırma, olay yönlendirme kurallarının anlaşılır olmasını sağlar.

## 5. Trigger — Tetikleme Sistemi

### 5.1. Temel işlev

Tetikleme sistemi, belirli bir olayın ardından bir işlemin otomatik olarak başlatılmasını sağlar.

Tetikleme hedefleri şunlar olabilir:

- DMA transferini başlatmak.
- Bir çevre biriminde örnekleme başlatmak.
- Programlanabilir mantık bloğunu etkinleştirmek.
- Bir sayaç veya zamanlayıcı işlemini başlatmak.
- Önceden yapılandırılmış bir işlem zincirinin sonraki adımına geçmek.

Tetikleme, işlem tanımının yerine geçmez. İşlemin ne yapacağı önceden yapılandırılmış olmalı; tetikleme yalnızca ne zaman başlayacağını belirlemelidir.

### 5.2. Tetikleme zinciri

Birden fazla tetikleme adımı bir zincir oluşturabilir.

Örnek akış:

1. Zamanlayıcı olay üretir.
2. DMA veri bloğunu belleğe aktarır.
3. DMA tamamlanma olayı üretir.
4. Programlanabilir mantık bloğu veri işleme işlemini başlatır.
5. İşlem sonucu hazır olduğunda yeni bir olay üretilir.
6. Sonuç gerekiyorsa CPU'ya kesme bildirilir.

Bu modelde CPU yalnızca başlangıç yapılandırmasını yapabilir ve sonuçları takip edebilir. Ara adımlar donanım tarafından yürütülebilir.

Ancak zincirin her adımı için kaynak, hedef, veri bağımlılığı ve hata davranışı tanımlanmalıdır.

### 5.3. Döngü ve yeniden tetikleme kontrolü

Olay yönlendirmesinin kontrolsüz döngüler oluşturması engellenmelidir.

Örneğin A olayının B işlemini, B işleminin de tekrar A olayını üretmesi sonsuz bir tetikleme döngüsü oluşturabilir.

Gerekli olduğunda şu korumalar uygulanabilir:

- Tetikleme sayacı.
- Maksimum zincir uzunluğu.
- Tek seferlik çalışma modu.
- Yeniden tetikleme engeli.
- Zaman aşımı.
- Yazılım tarafından durdurma.

İlk prototipte en azından tetikleme döngülerini tespit edilebilir veya sınırlandırılabilir kılmak gerekir.

## 6. DMA ile Entegrasyon

DMA, kesme ve olay sisteminin önemli kullanıcılarından biridir.

DMA başına en azından şu bildirimler tanımlanmalıdır:

- Transfer başlatıldı.
- Transfer tamamlandı.
- Transfer hatayla sonuçlandı.
- İsteğe bağlı olarak belirli bir blok veya eşik tamamlandı.

Transfer tamamlandığında iki farklı işlem yapılabilmelidir:

1. CPU'ya kesme üretmek.
2. Başka bir birime olay göndererek sonraki işlemi başlatmak.

Bu seçenekler ayrı ayrı veya uygun durumlarda birlikte etkinleştirilebilir.

Böylece CPU'nun transferin her aşamasını takip etmesi gerekmez.

## 7. Programlanabilir Fabric ile Entegrasyon

Programlanabilir Fabric içindeki yapılandırılmış mantık, belirlenmiş olayları üretebilmeli ve alabilmelidir.

Olası kullanımlar:

- Harici bir sinyalle örnekleme başlatma.
- Birden fazla koşul gerçekleştiğinde işlem tetikleme.
- Veri bloğu tamamlandığında sonraki mantık aşamasını etkinleştirme.
- Bir hata koşulunda bildirim üretme.

Programlanabilir Fabric içindeki tetiklemelerin CPU'ya yönlendirilmesi zorunlu değildir.

Bununla birlikte, hangi olayların Fabric içindeki özel mantıkla yönlendirileceği ve hangilerinin ortak olay denetleyicisinden geçeceği, kaynak ve gecikme gereksinimlerine göre belirlenmelidir.

## 8. Olay Kaybı ve Kuyruklama

Olayların her zaman tek bir anlık sinyal olarak temsil edilmesi yeterli değildir.

Aynı olay çok hızlı tekrarlanıyorsa veya hedef birim meşgulse, olay sayısının korunması gerekebilir.

Bu nedenle olay kaynakları için farklı davranışlar desteklenebilir:

- **Durum biti:** Olayın en az bir kez meydana geldiğini gösterir.
- **Sayaç:** Olayın kaç kez gerçekleştiğini izler.
- **FIFO/kuyruk:** Birden fazla olayı sıralı biçimde saklar.
- **Darbe:** Olayı anlık bildirim olarak iletir; kaybolmaması için hedefin ve aktarım mekanizmasının uygun olması gerekir.

Her kaynak için aynı yöntem zorunlu değildir. Seçim, olayın niteliğine göre yapılmalıdır.

## 9. Saat Alanları ve Reset Uyumluluğu

Farklı saat alanları arasında olay aktarılırken CDC kuralları uygulanmalıdır.

Bir olayın darbe şeklinde aktarılması, hedef saat alanının o darbeyi algılayacağını tek başına garanti etmez. Gerekli durumlarda el sıkışma, senkronize olay yakalama veya asenkron FIFO kullanılmalıdır.

Reset sırasında ise:

- Bekleyen olayların korunup korunmayacağı belirlenmelidir.
- Resetlenen birimin eski olayları yeniden işlemesi engellenmelidir.
- Devam eden tetikleme zincirleri için iptal veya kurtarma davranışı tanımlanmalıdır.

Olay kuyruğunun temizlenmesi ile olay kaynağının gerçek durumunun temizlenmesi ayrı işlemler olabilir.

## 10. İlk Prototip İçin Minimum Kapsam

İlk prototip için aşağıdaki özellikler yeterli bir başlangıç oluşturur:

- Temel kesme denetleyicisi.
- Kesme etkinleştirme ve maskeleme.
- Bekleyen kesme durumlarının izlenmesi.
- DMA tamamlanma ve hata bildirimleri.
- Temel olay yönlendirme.
- DMA ve seçili çevre birimleri için donanım tetikleme.
- Gerekli saat alanları arasında güvenli olay aktarımı.
- Temel tetikleme döngüsü ve zaman aşımı korumaları.

Gelişmiş öncelik katmanları, uzun olay kuyrukları ve karmaşık tetikleme grafikleri sonraki sürümlere bırakılabilir.

## 11. Açık Tasarım Kararları

1. Kesme kaynağı sayısı ve kimlik alanı genişliği.
2. Kesme öncelik seviyelerinin sayısı.
3. Kesme vektörleme ve CPU'ya bildirim yöntemi.
4. Olay yönlendirme tablosunun yapılandırma yöntemi.
5. Olay başına hedef sayısı.
6. Hangi olaylarda sayaç veya FIFO gerektiği.
7. Desteklenecek tetikleme zinciri uzunluğu.
8. Tetikleme döngülerinin donanımda nasıl sınırlandırılacağı.
9. Reset sırasında olayların korunma politikası.
10. Programlanabilir Fabric'in ortak olay denetleyicisine hangi arayüzle bağlanacağı.

Bu kararlar, CPU'nun kesme modeli ve Programlanabilir Fabric'in yapılandırma mimarisiyle birlikte kesinleştirilecektir.

## 12. Sonuç

NEXSUS Interrupt, Event & Trigger mimarisi, kesmeleri, olayları ve tetiklemeleri birbirinden ayırarak CPU ile bağımsız işlem birimleri arasındaki koordinasyonu tanımlar.

Temel hedef, CPU'nun tüm veri hareketlerini ve işlem aşamalarını sürekli yönetmek zorunda kalmadığı, ancak gerekli durumlarda sistem üzerinde kontrolünü koruduğu bir mimari oluşturmaktır.

**Mimari ilke:** Her olay kesme üretmek zorunda değildir; her tetikleme için CPU müdahalesi gerekmez; fakat tüm otomatik işlem zincirleri tanımlı ve denetlenebilir olmalıdır.

---

**Belge Sonu — NEXSUS-IRQ-014 v1.0**