# NEXSUS Security, Access Control & Fault Isolation Architecture Specification

**Doküman Kodu:** NEXSUS-SEC-017  
**Sürüm:** 1.0  
**Statü:** Mimari Taslak  
**Kapsam:** NEXSUS programlanabilir çip

---

## 1. Amaç

Bu belgenin amacı, NEXSUS içindeki işlem birimlerinin kaynaklara erişimini kontrol etmek ve bir birimde meydana gelen hatanın diğer birimlere kontrolsüz biçimde yayılmasını sınırlandırmaktır.

Mimari üç temel işlevi kapsar:

- **Access Control:** Hangi birimin hangi kaynağa erişebileceğini belirlemek.
- **Fault Isolation:** Bir hata veya arızanın etki alanını sınırlandırmak.
- **Recovery:** Hata sonrasında ilgili birimi veya sistemi kontrollü biçimde yeniden çalıştırmak.

Bu yapı yalnızca dışarıdan gelebilecek saldırılara karşı koruma sağlamayı değil, DMA hataları, yanlış adresleme, hatalı yapılandırma ve kontrol mantığı kusurları gibi durumların da etkisini azaltmayı hedefler.

## 2. Temel Güvenlik İlkeleri

NEXSUS güvenlik mimarisi şu ilkeleri izlemelidir:

1. Her donanım birimi, yalnızca ihtiyaç duyduğu kaynaklara erişebilmelidir.
2. Erişim yetkisi açıkça tanımlanmayan işlemler varsayılan olarak reddedilmelidir.
3. DMA gibi CPU'dan bağımsız çalışan birimler de erişim denetimine tabi olmalıdır.
4. Programlanabilir Fabric'in erişimleri, belirlenmiş sınırlar içinde tutulmalıdır.
5. Hata tespiti ile hata sonrasında uygulanacak kurtarma birbirinden ayrılmalıdır.
6. Güvenlik denetimi Chip Fabric ve bellek erişim yollarıyla uyumlu çalışmalıdır.
7. Güvenlik özellikleri, performans maliyetleri ölçülerek ve gerekli olduğu alanlarda uygulanmalıdır.

## 3. Korunacak Kaynaklar

Erişim denetimi aşağıdaki kaynak türlerini kapsayabilir:

| Kaynak | Koruma amacı |
|---|---|
| Bellek bölgeleri | Yetkisiz okuma ve yazmayı engellemek |
| CPU kayıtları ve kontrol kayıtları | Kritik durumların izinsiz değiştirilmesini önlemek |
| DMA kanalları | Transferlerin izin verilen aralıklarda kalmasını sağlamak |
| I/O denetleyicileri | Çevre birimlerine erişimi sınırlandırmak |
| Programlanabilir Fabric | Yapılandırma ve çalışma erişimlerini ayırmak |
| Yapılandırma denetleyicisi | Yetkisiz yeniden yapılandırmayı engellemek |
| Saat ve reset denetimleri | Kritik kontrol durumlarının korunmasını sağlamak |
| Kesme ve olay denetleyicisi | Bildirimlerin ve tetiklemelerin yetkili kaynaklardan gelmesini sağlamak |

Bu kaynakların tamamının aynı denetim mekanizmasını kullanması zorunlu değildir. Ancak erişim politikalarının birbiriyle tutarlı olması gerekir.

## 4. Erişim Yetkilendirme Modeli

### 4.1. Erişim yapan birimler

Erişim denetimine tabi olabilecek birimler:

- CPU.
- DMA kanalları.
- Programlanabilir Fabric'deki mantık blokları.
- Yapılandırma denetleyicisi.
- I/O ve çevre birimi motorları.
- Diğer bağımsız veri aktarım birimleri.

Her erişim isteği, kaynak birimle ilişkilendirilebilecek bir kimlik taşımalıdır.

Bu kimlik, erişim denetleyicisinin isteği doğru politikayla değerlendirmesini sağlar.

### 4.2. Erişim türleri

Temel erişim türleri şunlardır:

- Read — okuma.
- Write — yazma.
- Execute — komut yürütme.
- Configure — yapılandırma değiştirme.
- Control — kontrol kayıtlarını veya çalışma durumlarını değiştirme.

Her kaynak bütün erişim türlerini desteklemek zorunda değildir.

Örneğin bir bellek bölgesi CPU tarafından yürütülebilir fakat bir DMA kanalı tarafından yalnızca okunabilir olabilir.

### 4.3. İzin politikaları

Erişim politikaları, kaynak türüne göre farklılaştırılabilir.

Örnek:

| Kaynak | CPU | DMA | Programmable Fabric |
|---|---|---|---|
| Uygulama belleği | Yapılandırılmış izin | İzin verilen aralıklarla | İzin verilen aralıklarla |
| Kontrol kayıtları | Yetkiye bağlı | Varsayılan olarak sınırlı | Açıkça yetkilendirilmiş erişim |
| Yapılandırma alanı | Yetkili işlemler | Açıkça izin verilmedikçe engelli | Yapılandırma yetkisine bağlı |
| I/O kayıtları | İzin verilen erişim | Seçilmiş arayüzlerle | Yapılandırılmış arayüzlerle |

Bu tablo örnek bir politika modelidir; kesin erişim matrisi daha sonra tanımlanacaktır.

## 5. Bellek Erişim Denetimi

### 5.1. Bölgesel koruma

Bellek alanları, erişim özelliklerine göre mantıksal bölgelere ayrılabilir.

Her bölge için aşağıdaki özellikler tanımlanabilir:

- Başlangıç ve bitiş adresi.
- Okuma izni.
- Yazma izni.
- Komut yürütme izni.
- İzin verilen erişen birimler.
- Gerekirse özel güvenlik seviyesi.

Adres ve boyut doğrulaması, erişim isteği hedef belleğe ulaşmadan önce yapılmalıdır.

### 5.2. DMA koruması

DMA'nın CPU'dan bağımsız çalışması, ona sınırsız bellek erişimi verilmesini gerektirmez.

Her DMA kanalı için aşağıdaki denetimler değerlendirilebilir:

- İzin verilen bellek aralıkları.
- Okuma ve yazma yönü.
- Transfer boyutu sınırları.
- Adres taşması kontrolü.
- Hedef bölgenin erişim yetkisi.
- Transfer tamamlanmadan yapılandırmanın değiştirilmesine ilişkin kurallar.

Bir DMA isteği izin verilen sınırları aşıyorsa transfer engellenmeli ve hata durumu kaydedilmelidir.

### 5.3. Adres doğrulaması

Bellek erişimlerinde adres hesabının taşması da kontrol edilmelidir.

Örneğin başlangıç adresi geçerli olsa bile `başlangıç adresi + transfer uzunluğu` hesabı adres alanını aşabilir.

Bu nedenle yalnızca başlangıç adresinin kontrol edilmesi yeterli değildir; erişimin kapsadığı aralığın tamamı doğrulanmalıdır.

## 6. Programlanabilir Fabric Güvenliği

Programlanabilir Fabric, kullanıcı tarafından yapılandırılan mantığı çalıştırdığı için erişim sınırları açıkça tanımlanmalıdır.

### 6.1. Kaynak sınırları

Fabric mantığının hangi kaynakları kullanabileceği belirlenmelidir:

- Bellek aralıkları.
- DMA kanalları.
- I/O arayüzleri.
- Olay ve tetikleme kaynakları.
- Saat ve reset kontrol noktaları.
- Yapılandırma arayüzleri.

Her mantık bloğunun tüm kaynaklara otomatik olarak erişmesi zorunlu olmamalıdır.

### 6.2. Yapılandırma yetkisi

Normal çalışma sırasında veri işleyen bir mantık bloğunun, yapılandırma denetleyicisini sınırsız biçimde değiştirebilmesi güvenli bir varsayım değildir.

Yapılandırma erişimi ayrı bir yetki olarak ele alınmalıdır.

Bir yapılandırma isteği için hedef bölge, işlem türü ve kaynak yetkisi doğrulanmalıdır.

### 6.3. Hatalı mantığın sınırlandırılması

Programlanabilir mantık hatalı bir olay döngüsü oluşturabilir, aşırı sayıda istek gönderebilir veya beklenmeyen bir erişim düzeni üretebilir.

Uygun donanım desteği varsa şu korumalar kullanılabilir:

- İstek hızını sınırlama.
- Zaman aşımı.
- Kaynak başına kota.
- Hatalı işlemleri iptal etme.
- İlgili bölgeyi izole etme.

Bu mekanizmaların uygulanabilirliği, Fabric'in gerçek kaynak ve bağlantı mimarisine bağlıdır.

## 7. Chip Fabric Üzerinde Erişim Denetimi

Chip Fabric, CPU, DMA, bellek denetleyicisi ve diğer birimler arasındaki erişimleri taşır.

Erişim denetimi için iki temel yaklaşım vardır:

**Merkezi denetim:** İstekler ortak bir erişim denetleyicisinden geçirilir.

- Politikaların yönetimi kolaylaşabilir.
- Tek bir denetim noktası darboğaz oluşturabilir.

**Dağıtık denetim:** Kaynaklara yakın noktalarda erişim denetimleri yapılır.

- Yerel erişimlerin gecikmesi azaltılabilir.
- Politika tutarlılığının yönetimi daha karmaşık olabilir.

NEXSUS için hibrit yaklaşım değerlendirilebilir: ortak politika ve yetki tanımları, erişimin gerçekleştiği uygun noktalarda denetlenir.

Bu, her veri aktarımının mutlaka tek bir merkezi bloktan geçmesi gerektiği anlamına gelmez.

## 8. Fault Isolation — Hata İzolasyonu

### 8.1. Hata sınıfları

Hatalar aşağıdaki sınıflara ayrılabilir:

- **Access Violation:** Yetkisiz erişim.
- **Address Error:** Geçersiz adres veya adres taşması.
- **Protocol Error:** Veri yolu veya çevre birimi protokolü ihlali.
- **Timeout:** Beklenen yanıtın zamanında gelmemesi.
- **Configuration Error:** Geçersiz veya başarısız yapılandırma.
- **Execution Error:** Birimin tanımlı çalışma koşullarını ihlal etmesi.
- **Hardware Fault:** Donanımın beklenen biçimde çalışmaması.

Her hata türünün kurtarma yöntemi aynı olmak zorunda değildir.

### 8.2. Hata etki alanları

Bir hata meydana geldiğinde önce etkilenen alan belirlenmelidir.

Örnek etki alanları:

1. Tek işlem veya istek.
2. Tek DMA kanalı.
3. Tek çevre birimi.
4. Programlanabilir Fabric bölgesi.
5. Chip Fabric veya bellek erişim yolu.
6. Tüm çip.

Mümkün olduğunda hata, en küçük güvenli etki alanında tutulmalıdır.

### 8.3. Hata sonrası davranış

Bir hatanın ardından uygulanabilecek işlemler:

- İsteği reddetmek.
- İlgili durum kaydını güncellemek.
- CPU'ya kesme üretmek.
- Olay veya hata bildirimi göndermek.
- İlgili DMA kanalını durdurmak.
- Bir Fabric bölgesini izole etmek.
- Gerekirse yerel reset uygulamak.
- Kurtarma mümkün değilse sistem reseti başlatmak.

Sistem reseti, her hatada kullanılacak varsayılan çözüm olmamalıdır.

## 9. Hata Kaydı ve Tanılama

Hata yönetiminin etkili olabilmesi için yalnızca bir hata sinyali üretmek yeterli değildir.

Mümkün olduğunda aşağıdaki bilgiler saklanmalıdır:

- Hata türü.
- Hata üreten birimin kimliği.
- İlgili adres veya kaynak kimliği.
- İşlem türü.
- Hatanın meydana geldiği durum.
- Kurtarma işleminin sonucu.

İlk prototipte sınırlı sayıda hata kaydı yeterli olabilir.

Kayıtların üzerine yazılma politikası, birden fazla hatanın aynı anda meydana gelmesi ve kayıtların CPU tarafından temizlenmesi ayrıca tanımlanmalıdır.

## 10. Yetki ve Yapılandırma Değişiklikleri

Erişim politikaları çalışma sırasında değiştirilebiliyorsa, bu değişikliklerin tutarlı uygulanması gerekir.

Örneğin bir DMA kanalının erişim izni transfer devam ederken kaldırılırsa şu konular belirlenmelidir:

- Devam eden transfer hemen durdurulacak mı?
- Yalnızca yeni istekler mi engellenecek?
- Bekleyen istekler iptal edilecek mi?
- Değişiklik tamamlanmadan önce aktif işlemler bitirilecek mi?

İlk prototipte erişim politikalarının başlangıçta yapılandırılması ve normal çalışma sırasında sınırlı ölçüde değiştirilmesi daha basit bir yaklaşım olabilir.

## 11. İlk Prototip İçin Minimum Kapsam

İlk prototipte aşağıdaki özellikler önerilir:

- CPU ve DMA erişimlerinin ayrıştırılması.
- Bellek aralığı kontrolü.
- Okuma ve yazma izinleri.
- DMA adres taşması ve transfer sınırı kontrolü.
- Yetkisiz erişimlerin engellenmesi.
- Temel hata kayıtları.
- Hata durumunda kesme veya durum bildirimi.
- Gerektiğinde DMA kanalını veya çevre birimini durdurma.

Gelişmiş güvenlik seviyeleri, karmaşık güven alanları ve ayrıntılı kaynak kotaları, somut tehdit modeli ve performans gereksinimleri belirlendikten sonra tasarlanabilir.

## 12. Açık Tasarım Kararları

1. Erişim denetiminin merkezi ve dağıtık bölümleri.
2. Desteklenecek bellek bölgesi sayısı.
3. CPU, DMA ve Fabric için yetki modelinin ayrıntıları.
4. Kontrol kayıtlarının korunma yöntemi.
5. Programlanabilir Fabric'in erişim sınırları.
6. Hata kayıtlarının sayısı ve biçimi.
7. Hata durumlarında yerel reset ve izolasyon davranışı.
8. Çalışma sırasında yetki değiştirme kuralları.
9. Güvenli önyükleme ve yapılandırma doğrulama gereksinimleri.
10. İlk prototipin hedeflediği güvenlik tehditleri.

## 13. Sonuç

NEXSUS Security, Access Control & Fault Isolation mimarisi, çip içindeki kaynaklara erişimin açık kurallarla yönetilmesini ve hataların mümkün olduğunca sınırlı etki alanında tutulmasını hedefler.

**Mimari ilke:** Bağımsız çalışabilen her birim, bağımsız erişim yetkisi ve tanımlı hata davranışıyla birlikte tasarlanmalıdır. CPU'dan bağımsız çalışma, denetimsiz erişim anlamına gelmemelidir.

---

**Belge Sonu — NEXSUS-SEC-017 v1.0**