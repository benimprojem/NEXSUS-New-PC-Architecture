# NEXSUS CPU — SPM, Register Görünümleri ve Doğrudan Alan Erişimi

## 1. Tasarım Amacı

NEXSUS CPU'nun bellek ve register mimarisi, uygulama geliştirme sırasında gereksiz talimat üretimini azaltmak amacıyla tasarlanır.

Geleneksel işlemci mimarilerinde register kapasitesinin yetersiz kaldığı durumlarda geçici değerler yığına (stack) aktarılabilir. Bu süreç; adres hesaplama, bellek yazma, yeniden yükleme ve yığın yönetimi gibi ek işlemler doğurabilir.

NEXSUS, bu işlemleri mümkün olduğunca azaltmak için şu özellikleri bir araya getirir:

- Doğrudan adreslenebilir CPU içi çalışma belleği.
- 64 bitlik temel register erişimi.
- Registerların farklı veri genişliklerinde kullanılabilmesi.
- Bellek alanlarının donanım destekli kısmi güncellenmesi.
- 4 KiB sayfalardan oluşan çalışma alanı.
- Derleyicinin veri yapılarının yerleşimini ve erişim genişliğini belirleyebilmesi.

Temel ilke:

**Aynı sonucu daha az talimatla ve daha az gereksiz veri hareketiyle elde etmek mümkünse, mimari bu yolu tercih etmelidir.**

## 2. System Page Memory (SPM)

SPM, NEXSUS CPU içerisinde bulunan, doğrudan adreslenebilir ve sayfalara ayrılmış çalışma belleğidir.

SPM0, CPU çalışırken yürütme aşamasında oluşan geçici komutsal durumun, ara değerlerin ve sonuçların saklandığı alandır. Stack benzeri geçici saklama işlevi görür; ancak zorunlu LIFO sırası yoktur ve doğrudan adreslenir. SPM1–SPM7 ise aynı doğrudan adreslenebilir modeli veri tarafında uygular; geçici veriler ve ara hesaplama değerleri için kullanılır.

SPM, geleneksel yığının bire bir karşılığı değildir. Veriler zorunlu bir LIFO sırasına göre değil, tanımlı adresleri ve alanları üzerinden yönetilir.

### 2.1 SPM0 — 256 adet 64-bit temel kayıt

SPM0, komutların kendisini veya fetch/dispatch kuyruğunu saklamaz. CPU çalışırken komutların yürütülmesi sonucunda oluşan geçici komutsal durumu, ara değerleri ve sonuçları tutar. Stack benzeri bir çalışma alanıdır; ancak veriler LIFO sırasına bağlı olmadan doğrudan adreslenebilir.

SPM0 kapasitesi 256 × 64 bit = 16.384 bit = 2 KiB olarak belirlenir.

| Özellik | Değer |
|---|---:|
| Toplam kapasite | 2 KiB |
| Temel kayıt sayısı | 256 |
| Temel kayıt genişliği | 64 bit |
| Temel kayıt genişliği | 64 bit |
| 8-bit byte erişimi | Desteklenir |
| Desteklenen erişim genişlikleri | 8/16/32/64/128/256/512 bit |

SPM0'ın sekiz sayfası PAGE 0–PAGE 7 olarak tanımlanır.

Her sayfa 4096 bayt fiziksel kapasiteye sahiptir ve 512 adet 64 bitlik kayıt eşdeğerine karşılık gelir.

SPM0'da 64 bitlik kayıt temel adreslenebilir birimdir. Daha küçük alanların kullanılması, kaydın fiziksel olarak ayrı belleklere bölünmesini gerektirmez.

SPM0'ın birincil görevi yürütme sırasında oluşan geçici komutsal durum, ara değerler ve sonuçlar için doğrudan adreslenebilir alan sağlamaktır. Genel geçici veri ve ara hesaplama değerleri SPM1–SPM7 alanlarında tutulur.

### 2.2 SPM1–SPM7 — Değişken genişlikli veri alanları

SPM1–SPM7, değişken boyutlu geçici veriler ve ara hesaplama değerleri için ayrılmış doğrudan adreslenebilir çalışma alanlarıdır. Her biri SPM sayfa/ofset modeliyle erişilir; yazılım ve derleyici ihtiyaç duyduğu alanı doğrudan adresleyebilir. Her alanın kapasitesi 8 KiB olarak belirlenmiştir; fiziksel bank/port düzeni mikro-mimari aşamasında belirlenecektir.

Desteklenmesi hedeflenen veri genişlikleri:

- 8 bit
- 16 bit
- 32 bit
- 64 bit
- 128 bit
- 256 bit
- 512 bit

SPM1–SPM7'nin her biri 8 KiB kapasitelidir; toplam kapasiteleri 56 KiB'tır. Byte adresleme sayesinde veri alanları doğal boyutlarına göre tanımlanabilir. SPM0–SPM7'nin tamamı 8/16/32/64/128/256/512-bit erişim genişliklerini destekler.

128/256/512-bit değerler tek bir mantıksal veri veya erişim genişliği olarak ele alınır; 64-bit temel kayıt mimarisinde gerektiğinde ardışık kayıtlar üzerinden birleştirilir.

SPM0–SPM7, mimaride ayrı işlevsel çalışma alanları olarak tanımlanır; fiziksel bellek dizileri, bank paylaşımı ve port düzeni donanım tasarımında kesinleştirilir. Bunların mutlaka ayrı fiziksel bellek dizileri olması gerekmez.

## 3. Sayfa Kimliği ve Ofset Adreslemesi

SPM erişimi, sayfa kimliği ve sayfa içi ofset kavramlarını kullanır.

Genel adresleme modeli:

`SPM_ADDRESS = PAGE_ID + OFFSET`

Bu ifade kavramsal bir gösterimdir; gerçek kodlama alanların bit düzeyindeki yerleşimiyle belirlenecektir.

SPM0 için sekiz sayfa ve her sayfada 512 adet 64 bitlik kayıt bulunduğundan, sayfa kimliği 3 bit ve kayıt ofseti 9 bit ile temsil edilebilir.

Bu iki alan toplam 12 bitlik mantıksal kayıt konumu oluşturur.

SPM1–SPM7'de byte adresleme kullanılır. 8 KiB alan içindeki byte konumunu belirlemek için 13 bitlik ofset yeterlidir.

SPM0 kayıt ofsetiyle, SPM1–SPM7 ise byte ofsetiyle adreslenir; tüm alanlarda geniş erişimler ardışık byte/kayıtları kapsayabilir.

## 4. Register Görünümleri

NEXSUS CPU'nun 64 bitlik registerları, farklı veri genişliklerinde kullanılabilecek mantıksal görünümler sunar.

Örnek gösterim:

| Görünüm | Genişlik |
|---|---:|
| RA | 64 bit |
| RB | 32 bit |
| RC | 16 bit |
| RD | 8 bit |

Sonundaki sayısal indis, register numarasını belirler.

Örneğin RA0, RB0, RC0 ve RD0 aynı fiziksel registerın farklı genişliklerdeki görünümleri olarak tasarlanabilir.

- RA0: Tam 64 bitlik değer.
- RB0: Alt 32 bit.
- RC0: Alt 16 bit.
- RD0: Alt 8 bit.

Bu modelde farklı genişliklerde erişim için ayrı fiziksel registerlar ayırmak zorunlu değildir.

Register görünümünün fiziksel register ile ilişkisi donanım tarafından tanımlanır. 32 bitlik bir yazmanın üst bitleri koruyup korumayacağı veya sıfırlayıp sıfırlamayacağı açık bir mimari kural olacaktır. NEXSUS için alan güncellemesi sırasında ilgisiz bitlerin korunması tercih edilir.

## 5. Donanım Destekli Kısmi Yazma

SPM, 64 bitlik kayıtların tamamını yeniden yazmak zorunda kalmadan seçilen alanları güncelleyebilecek biçimde tasarlanır.

Örneğin bir kayıt şu alanlardan oluşabilir:

| Alan | Veri türü | Genişlik |
|---|---|---:|
| a | f32 | 32 bit |
| b | i16 | 16 bit |
| c | u16 | 16 bit |
| **Toplam** | | **64 bit** |

Bu alanlar tek bir 64 bitlik kayıt içinde tutulabilir.

Bir program yalnızca `b` alanını güncellediğinde, donanım bu alanı değiştirmeli ve `a` ile `c` alanlarının değerlerini korumalıdır.

Bunun için kısmi yazma mekanizması şu bilgileri kullanabilir:

- Hedef sayfa ve ofset.
- Alanın başlangıç biti.
- Alan genişliği.
- Yazılacak değer.
- Gerekli erişim ve eşzamanlılık kuralları.

Donanım, seçilen alanın yazılmasını doğrudan desteklerse işlemci genel amaçlı bir oku–maskele–birleştir–yaz dizisini her defasında üretmek zorunda kalmaz.

Kısmi yazma, mimari düzeyde tek komutla temsil edilebilir. Bunun donanım içinde tek çevrimde tamamlanması zorunlu değildir.

## 6. SPM Erişim Komut Grubu

SPM için ayrı bir komut grubu tasarlanabilir.

Aşağıdaki adlar işlevleri açıklamak için kullanılan geçici gösterimlerdir; kesin ISA tanımları değildir.

| Komut ailesi | İşlev |
|---|---|
| SPM.RD | 64 bitlik kayıt okuma |
| SPM.WR | 64 bitlik kayıt yazma |
| SPM.GET | Bir kaydın seçilen alanını okuma |
| SPM.PUT | Bir kaydın seçilen alanını güncelleme |
| SPM.MASK | Maskeli alan güncelleme |
| SPM.COPY | Kayıt veya alan kopyalama |

Örnek kavramsal kullanım:

`SPM.RD RA01, PAGE_0, OFFSET_12`

Bu ifade, belirtilen SPM0 konumundaki 64 bitlik kaydın RA01'e alınmasını temsil eder.

`SPM.PUT PAGE_0, OFFSET_12, RB0, FIELD_B`

Bu ifade, RB0'daki 32 bitlik değerin tanımlı hedef alana yazılmasını temsil eder. Gerçek komut biçimi alan genişliğini ve başlangıç konumunu açıkça belirtmelidir.

Komutların gerçek operandları, kodlamaları, erişim gecikmeleri ve hata davranışları ISA tasarımı sırasında kesinleştirilecektir.

## 7. Nexus Flow ve Yapılandırılmış Veri

SPM, Nexus Flow'un yapılandırılmış veri türleriyle uyumlu çalışacak şekilde tasarlanır.

Örnek:

```text
struct p {
    a:!f32,
    b:i16,
    c:u16
}
```

Derleyici, yapının 64 bitlik bir kayda sığdığını belirleyebilir ve alan yerleşimini derleme zamanında hesaplayabilir.

Örnek mantıksal yerleşim:

- a: bit 0–31
- b: bit 32–47
- c: bit 48–63

Bu yerleşim, örnek bir paketleme kuralıdır. Gerçek dil tanımı alan sırasını, hizalamayı, işaretli türlerin yorumunu ve veri yerleşimini açıkça belirlemelidir.

Bir alanın güncellenmesi gerektiğinde derleyici, hedef donanımın kısmi yazma yeteneğini kullanabilir. Böylece gereksiz maskeleme, kaydırma ve geçici kayıt işlemlerinin azaltılması hedeflenir.

## 8. İşletim Sistemi ve Ara Hesaplama Desteği

SPM'nin kullanım alanları şunlardır:

- İşletim sistemi ile CPU arasındaki çalışma ve aktarım verileri.
- Geçici hesaplama sonuçları.
- Registerlarda tutulması uygun olmayan ara değerler.
- Küçük yapılandırılmış veri nesneleri.
- Doğrudan adreslenebilir geçici çalışma alanları.

SPM, işletim sisteminin yönetebildiği bir CPU içi kaynak olarak tasarlanır. GPU, FAPU ve diğer düğümler için ortak bir SPM oluşturulmaz; bu birimler kendi bellek erişim mekanizmalarını kullanmaya devam eder.

## 9. Tasarım Hedefleri ve Sınırlar

SPM ve register görünüm sisteminin başarısı yalnızca daha az kod üretmekle ölçülmez.

Değerlendirme ölçütleri:

1. Üretilen talimat sayısı.
2. Gereksiz bellek erişimlerinin sayısı.
3. Register spill ve yeniden yükleme sayısı.
4. Alan güncellemesi için gereken işlem sayısı.
5. Bellek erişim gecikmesi.
6. Kod boyutu ve toplam yürütme maliyeti.

SPM, registerların yerine geçmez. Registerlar en hızlı doğrudan işlem alanı olarak kalırken SPM, doğrudan adreslenebilir çalışma alanı sağlar.

Amaç, her uygulamada sabit oranda kod azaltımı vaat etmek değil; donanım ve derleyici desteğiyle gereksiz işlemleri sistematik biçimde azaltmaktır.

## 10. Sonuç

NEXSUS CPU'nun SPM ve register görünüm mimarisi, yazılımın veriyle doğrudan çalışmasını ve donanımın gereksiz ara adımları azaltmasını hedefler.

64 bitlik temel kayıt erişimi, değişken genişlikli veri alanları, sayfa kimliği–ofset adreslemesi ve donanım destekli kısmi yazma birlikte ele alınır.

Böylece NEXSUS, yığın kullanımını zorunlu kılmadan geçici verileri yönetebilir; Nexus Flow derleyicisi de uygun durumlarda daha kısa ve daha verimli kod üretebilir.
