# NEXSUS Memory Architecture & Controller Specification

**Doküman Kodu:** NEXSUS-MEM-010  
**Sürüm:** 0.9  
**Durum:** Mimari Taslak  
**Kapsam:** NEXSUS programlanabilir çipinin bellek hiyerarşisi ve bellek erişim mimarisi

---

## 1. Amaç

NEXSUS bellek mimarisi; CPU, Programmable Fabric, DMA ve diğer işlem birimlerinin ihtiyaç duyduğu verilerin saklanmasını ve erişimini düzenler.

Temel hedefler:

- İşlem birimlerinin ihtiyaç duyduğu veriye uygun gecikmeyle erişmesini sağlamak.
- Yerel bellekleri kullanarak gereksiz Chip Fabric trafiğini azaltmak.
- Bellek erişimi ile veri aktarımını birbirinden ayırmak.
- Birden fazla birimin belleğe erişmesini desteklemek.
- Farklı bellek teknolojilerinin aynı mimari altında kullanılabilmesini sağlamak.
- P1–P5 modellerinde ölçeklenebilir bir bellek altyapısı oluşturmak.

Bu belge mantıksal mimariyi tanımlar. MOSRAM ve MSSD gibi yeni bellek kavramlarının fiziksel uygulanabilirliği henüz doğrulanmış değildir.

## 2. Bellek Hiyerarşisi

NEXSUS bellek sistemi aşağıdaki katmanlardan oluşur:

| Katman | Bellek türü | Temel görev |
|---|---|---|
| 1 | CPU kayıtları | Anlık işlem verileri ve yürütme durumu |
| 2 | FIFO ve tamponlar | Geçici veri akışı ve hız dengeleme |
| 3 | Distributed RAM | Programmable Fabric içindeki küçük, yerel veri depoları |
| 4 | Block RAM | Fabric içerisinde daha büyük yerel veri blokları |
| 5 | SRAM | Genel amaçlı hızlı çalışma belleği |
| 6 | MOSRAM | Araştırılan alternatif çalışma belleği |
| 7 | MSSD | Araştırılan kalıcı depolama teknolojisi |

Bu katmanlar zorunlu olarak ayrı fiziksel bellek yongaları anlamına gelmez. Bazıları aynı çip üzerinde veya aynı bellek alt sisteminde uygulanabilir.

## 3. CPU Bellek ve Kayıt Modeli

NEXSUS CPU tasarımında uygulama kodu ve veri işlemleri mantıksal olarak ayrılır.

### 3.1. Kayıtlar

- `RA00–RA63`: Uygulama/kod tarafıyla ilişkili kayıt sınıfı.
- `DA00–DA63`: Veri işlemlerinde kullanılan kayıt sınıfı.
- `MA00–MA31`: Matris ve vektör işlemleri için tasarlanan kayıt sınıfı.

Bu kayıt sınıflarının kesin işlevleri, komut kümesi ve işlemci mikro mimarisi tasarlanırken netleştirilecektir.

### 3.2. Mantıksal ve fiziksel ayrım

Uygulama kodu ile veri belleğinin ayrılması, bunların mutlaka farklı fiziksel bellek yongalarında bulunmasını gerektirmez.

Mimari, ayrı adres alanlarını veya farklı erişim kurallarını destekleyebilir; fiziksel yerleşim ise performans, güvenlik, alan ve güç değerlendirmelerine göre seçilir.

## 4. Programmable Fabric Bellekleri

### 4.1. Distributed RAM

Distributed RAM, mantık kaynaklarına yakın küçük veri depoları için kullanılır.

Örnek kullanım alanları:

- Küçük tablolar.
- Yerel durum bilgileri.
- Kısa veri tamponları.
- Özel durum makinelerinin çalışma verileri.

Avantajı yerel erişim sağlayabilmesidir. Ancak kapasite ve yerleşim maliyeti, kullanılan mantık kaynaklarına bağlıdır.

### 4.2. Block RAM

Block RAM, Distributed RAM'den daha büyük ve yapılandırılmış veri depoları için kullanılır.

Örnek kullanım alanları:

- DSP çalışma tamponları.
- Paket tamponları.
- Yerel görüntü veya sinyal blokları.
- Büyük FIFO'lar.
- İşlem birimlerine ait çalışma tabloları.

Block RAM'in port sayısı, erişim genişliği, kapasitesi ve saat sınırları fiziksel uygulamada ayrıca belirlenmelidir.

### 4.3. Yerel bellek kullanımı

İşlem birimleri sık kullandıkları veriyi yerel bellekte tutabildiğinde, genel Chip Fabric üzerindeki trafik azalabilir.

Bu nedenle her veri için sistem belleğine gidilmesi yerine, uygun durumlarda yerel bellek ve FIFO kullanılması önerilir.

## 5. Genel Çalışma Belleği

SRAM, çip içindeki genel amaçlı çalışma belleği için başlangıç referansıdır.

Görevleri:

- CPU çalışma verilerini saklamak.
- DMA aktarım alanlarını sağlamak.
- İşlem birimleri arasında ortak veri paylaşımını desteklemek.
- FIFO ve yerel bellek kapasitesinin yetmediği durumlarda daha geniş veri alanları sunmak.

Gerçek kapasite, bellek portları, erişim gecikmesi ve sürdürülebilir bant genişliği ürün bazında belirlenecektir.

## 6. MOSRAM ve MSSD

### 6.1. MOSRAM

MOSRAM, MOSFET gate bölgesindeki yük veya gerilim durumunu kullanarak bilgi saklamayı ve kapasitif algılama yoluyla okumayı hedefleyen araştırma konseptidir.

Amaçlanan kullanım, doğrulanması hâlinde çalışma belleği sınıfındadır.

Ancak aşağıdaki özellikler henüz deneysel doğrulama gerektirir:

- Hücre kararlılığı ve veri tutma süresi.
- Okuma sinyalinin algılanabilirliği.
- Okuma sırasında oluşan bozucu etkiler.
- Yazma ve silme mekanizması.
- Hücreler arası elektriksel etkileşim.
- Üretim süreci ve ölçeklenebilirlik.

Bu nedenle MOSRAM, fiziksel olarak doğrulanmış bir bellek türü gibi ele alınmamalı; mevcut tasarımda değiştirilebilir bir bellek hedefi olarak tutulmalıdır.

### 6.2. MSSD

MSSD, kalıcı veri saklamayı hedefleyen ayrı bir araştırma konseptidir.

Çalışma belleği ile kalıcı depolamanın gereksinimleri farklı olduğundan, MSSD'nin arayüzü ve kontrol mekanizması MOSRAM'dan ayrı tasarlanabilir.

Kalıcı veri tutma, yazma dayanıklılığı, veri bütünlüğü ve hata düzeltme özellikleri doğrulanmadan MSSD için kesin performans iddiası yapılmamalıdır.

## 7. Memory Controller

Memory Controller, bağlı olduğu bellek teknolojisine erişimi yönetir.

Görevleri:

- Belleğin erişim protokolünü yürütmek.
- Okuma ve yazma isteklerini bellek gereksinimlerine uygun biçimde işlemek.
- Gerekli zamanlama ve erişim sırasını yönetmek.
- Destekleniyorsa hata algılama ve durum raporlama işlemlerini gerçekleştirmek.
- Bellek tarafındaki isteklerle Chip Fabric arayüzü arasında bağlantı sağlamak.

Memory Controller, DMA ile aynı bileşen değildir.

**Memory Controller belleğe erişimi yönetir; DMA ise veriyi bir kaynaktan hedefe aktarır. Chip Fabric, bu isteklerin ilgili birimlere ulaşmasını sağlar.**

## 8. Bellek Erişimi ve Veri Paylaşımı

CPU, DMA ve uygun işlem birimleri ortak bellek alanlarına erişebilir. Ancak her birimin bütün bellek bölgelerine erişmesi zorunlu değildir.

Önerilen temel yaklaşım:

- CPU, izin verilen çalışma belleği bölgelerine erişir.
- DMA, kendisine tanımlanmış kaynak ve hedef bölgelerinde aktarım yapar.
- Programmable Fabric, yerel belleklere ve izin verilen ortak veri alanlarına erişir.
- DSP ve diğer işlem birimleri öncelikle yerel tamponlardan yararlanır.
- Çevre birimleri verilerini FIFO veya desteklenen DMA yolları üzerinden aktarır.

Aynı veri üzerinde birden fazla birim çalışıyorsa, veri hazır olma durumu ve erişim sırası açık biçimde yönetilmelidir.

Başlangıç aşamasında karmaşık cache tutarlılığı zorunlu tutulmamalıdır. Bunun yerine açık tampon sahipliği, senkronizasyon ve gerekirse önbelleksiz erişim yaklaşımı değerlendirilebilir. Bu, henüz kesinleşmiş bir mimari kararı değildir.

## 9. Bellek Performansı

Bellek performansı yalnızca kapasiteyle belirlenmez.

Değerlendirilecek temel ölçütler:

- Okuma ve yazma gecikmesi.
- Sürdürülebilir bant genişliği.
- Eşzamanlı erişim kapasitesi.
- Port sayısı ve erişim genişliği.
- Bellek denetleyicisi kapasitesi.
- Chip Fabric üzerindeki trafik.
- Güç tüketimi ve fiziksel alan.

Birden fazla işlem birimi aynı belleği kullanıyorsa, toplam veri talebi belleğin ve bağlantı ağının sürdürülebilir kapasitesini aşmamalıdır.

Bu aşamada kesin bellek frekansı, veri yolu genişliği veya bant genişliği belirlenmemektedir.

## 10. Örnek: Görüntü Tamponu

1920 × 1080 çözünürlükte, piksel başına 24 bit RGB888 biçimindeki bir görüntünün sıkıştırılmamış boyutu yaklaşık 6,22 MB'dır.

İki tampon kullanıldığında yaklaşık 12,44 MB alan gerekir.

Bu yalnızca bir kapasite örneğidir. Tamponların tamamı ayrı bir fiziksel bellekte bulunmak zorunda değildir; bellek mimarisi, uygun kapasite ve erişim performansı sağlandığında farklı bellek bölgelerini kullanabilir.

## 11. Açık Tasarım Kararları

Sürüm 1.0 öncesinde aşağıdaki noktalar kesinleştirilmelidir:

1. CPU kayıt sınıflarının ve bellek alanlarının kesin anlamı.
2. SRAM kapasitesi ve port yapısı.
3. Distributed RAM ve Block RAM kaynaklarının ürünlere göre dağılımı.
4. Bellek denetleyicilerinin sayısı ve görev sınırları.
5. DMA ve diğer initiator'ların erişim izinleri.
6. Veri paylaşımı ve senkronizasyon modeli.
7. Cache kullanılıp kullanılmayacağı.
8. MOSRAM ve MSSD'nin fiziksel doğrulama sonuçları.
9. Bellek bant genişliği ve gecikme hedefleri.
10. P1–P5 modelleri için kapasite ve güç bütçesi.

## 12. Sonuç

NEXSUS bellek mimarisi; CPU kayıtlarını, yerel Fabric belleklerini, FIFO'ları ve genel çalışma belleğini görevlerine göre ayırır. Memory Controller belleğe erişimi yönetirken DMA veri aktarımını yürütür ve Chip Fabric birimler arasındaki iletişimi sağlar.

MOSRAM ve MSSD, mimaride gelecekte değerlendirilebilecek araştırma hedefleri olarak tutulur; fiziksel uygulanabilirlikleri doğrulanmadan temel sistemin çalışması bunlara bağımlı kılınmaz.

**Sonraki aşama:** DMA Engine ve aktarım planlayıcısının temel mimarisi. Amaç, bellek ile işlem birimleri arasındaki veri hareketlerini CPU'nun sürekli müdahalesine ihtiyaç duymadan gerçekleştirecek yapıyı tanımlamaktır.
