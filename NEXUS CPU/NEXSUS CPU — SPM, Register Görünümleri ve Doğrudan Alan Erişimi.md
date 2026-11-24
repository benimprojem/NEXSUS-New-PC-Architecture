# NEXSUS CPU — Register Views and Direct Workspaces

> Bu dosyanın eski dosya yolu geriye dönük bağlantılar için korunmuştur. Güncel çalışma alanı adları OW/TW'dir; eski SPM0–SPM7 modeli artık mimari referans değildir. Yetkili adresleme ve aktarım tanımı: [Workspace Addressing and Transfer](NEXSUS-CPU-WORKSPACE-ADDRESSING-AND-TRANSFER-001.md).

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

## 2. OW ve TW çalışma alanları

NEXSUS CPU, doğrudan byte-adreslenebilir iki genel amaçlı çalışma alanı sağlar:

| Alan | Kapasite | Sahiplik | Kullanım |
|---|---:|---|---|
| Operating-System Workspace (OW) | 8 KiB | OS | Kernel scratch, syscall/I/O exchange, OS kayıtları |
| Task Workspace (TW) | 8 KiB | Çalışan task | Task-local veri, register spill, geçici yapılar ve çalışma dosyaları |

OW ve TW, register bankı değildir. Her biri kendi 0–8191 byte offset aralığına sahiptir. TW zorunlu LIFO stack değildir; yazılım isterse stack frame, ister sabit offset'li kayıt, dizi, tablo veya geçici buffer olarak kullanabilir.

EB, OW/TW'den ayrıdır: EB 4 KiB çift bankalı instruction-fetch alanıdır ve yazılım tarafından adreslenemez. CP0–CP3 korumalı OS context pool; XW ise exception hardware'a özel alandır. Bu alanlar WLOAD/WSTORE ile genel amaçlı erişime açılmaz.

## 3. Workspace adresleme ve erişim modeli

Workspace offset'i byte cinsindendir. Doğrudan offset ve RA tabanlı displacement biçimleri desteklenir:

```asm
WLOAD.TW.W64  DA0, [0x120]
WSTORE.TW.W64 [0x120], DA0
WLOAD.TW.W64  DA1, [RA4 + 0x120]
WSTORE.OW.W64 [RA5 + 0x40], DA2
```

- Geçerli workspace aralığı 0–8191'dir; adres sarımı yoktur.
- WLOAD/WSTORE 8/16/32/64/128/256/512-bit erişimleri destekler.
- Erişimler doğal hizalı olmalıdır; tam erişim aralığı 8 KiB sınırları içinde kalmalıdır.
- WLOAD/WSTORE DA staging bankını kullanır. RA/FA/MA register banklarıyla veri alışverişi mevcut MOV.DA.RA / MOV.RA.DA, MOV.DA.FA / MOV.FA.DA ve MOV.DA.MA / MOV.MA.DA komutlarıyla açıkça yapılır.
- OW/TW ile L1–L4 Data RAM arasında büyük aralık aktarımı XFER.WS.MEM veya XFER.WS.START ile yapılır; XFER.WAIT asenkron aktarımın tamamlanmasını bekler.
- Workspace SRAM portu RAC register portu değildir; ancak WLOAD hedef DA yazmaları ve WSTORE kaynak DA okumaları ortak RAC 32R+32W bütçesinden sayılır. XFER.WS.MEM doğrudan blok yolu DA staging ve RAC register slotlarını kullanmaz. Workspace bank/port sayısı ve erişim bant genişliği ayrı mikro-mimari konudur.

Tam operand, fault, permission ve encoding kuralları [NEXSUS-CPU-WORKSPACE-ADDRESSING-AND-TRANSFER-001.md](NEXSUS-CPU-WORKSPACE-ADDRESSING-AND-TRANSFER-001.md) ve Instruction Encoding belgesinde tanımlıdır.

## 4. Register Bankları ve Görünümleri

NEXSUS CPU dört bağımsız register bankı kullanır:

| Bank | Kayıt aralığı | Kayıt sayısı | Fiziksel genişlik | Görev |
|---|---|---:|---:|---|
| RA | RA0–RA31 | 32 | 64 bit | Integer, adres ve scalar state |
| FA | FA0–FA31 | 32 | 64 bit | Floating-point state |
| DA | DA0–DA31 | 32 | 64 bit | Data staging / transfer |
| MA | MA0–MA31 | 32 | 256 bit | Vector / matrix operands |

### 4.1 RA alt genişlik görünümleri

RB/RC/RD yalnızca RA bankının aynı fiziksel kaydına ait alt-bit görünümleridir:

| Görünüm | Genişlik | Bit aralığı |
|---|---:|---|
| RA[n] | 64 bit | [63:0] |
| RB[n] | 32 bit | [31:0] |
| RC[n] | 16 bit | [15:0] |
| RD[n] | 8 bit | [7:0] |

Örneğin RA0, RB0, RC0 ve RD0 aynı fiziksel RA0 kaydını gösterir. RB/RC/RD, FA/DA/MA banklarına uygulanmaz.

- RA write: 64 bitin tamamını günceller.
- RB write: yalnızca [31:0] güncellenir; [63:32] korunur.
- RC write: yalnızca [15:0] güncellenir; [63:16] korunur.
- RD write: yalnızca [7:0] güncellenir; [63:8] korunur.

### 4.2 FA kayıtları ve FP128 pair

FA kayıtları 64-bit fiziksel genişliktedir. FP32 ve FP64 tek kayıt kullanır. FP128 iki ardışık FA kaydını birlikte kullanır; pair başlangıcı çift indisli olmalıdır:

- FA00:FA01 → FP128 pair 0
- FA02:FA03 → FP128 pair 1
- …
- FA30:FA31 → FP128 pair 15

İlk kayıt düşük 64-bit, sonraki kayıt yüksek 64-bit dilimdir. Pair kullanımında iki kayıt da aynı komutun kaynak/hedef bağımlılığına dahildir.

### 4.3 Register banklarının toplam kapasitesi

- RA: 32 × 64 bit = 256 byte
- FA: 32 × 64 bit = 256 byte
- DA: 32 × 64 bit = 256 byte
- MA: 32 × 256 bit = 1 KiB

Toplam fiziksel register kapasitesi **1.75 KiB**'tır. OW/TW kapasitesi bu toplama dahil değildir.
## 5. Workspace alan güncelleme semantiği

Workspace erişimleri byte offset ve WLOAD/WSTORE genişliği üzerinden yapılır. Bir struct alanını güncellemek için derleyici, alanın bulunduğu byte aralığını belirler ve gerekli okuma–maskeleme–birleştirme–yazma dizisini üretir.

Ayrı bir atomik bit-field workspace yazma komutu bu ISA sürümünde atanmış değildir. WSTORE yalnızca seçilen W bitini yazar; aynı 64-bit word içindeki diğer alanları korumak gerekiyorsa yazılım/derleyici read-modify-write yapmalıdır. Eşzamanlı güncelleme gerekiyorsa normal workspace erişimi tek başına atomicity sağlamaz; uygun synchronization gerekir.

Donanım destekli daha dar alan güncellemesi ileride ayrı opcode veya açık mask alanı olarak değerlendirilebilir; mevcut WLOAD/WSTORE semantiği değiştirilmeden eklenmelidir.

## 6. OW/TW erişim komutları

| Komut | İşlev |
|---|---|
| WLOAD.OW / WLOAD.TW | Workspace'ten DA staging bankına okuma |
| WSTORE.OW / WSTORE.TW | DA staging bankından workspace'e yazma |
| XFER.WS.MEM | Workspace ile L1–L4 Data RAM arasında senkron blok aktarımı |
| XFER.WS.START / XFER.WAIT | Asenkron workspace export ve tamamlanma |

Register bank save/restore, DA staging üzerinden açık MOV transferleriyle yapılır. Workspace ile register bankı arasında gizli alias veya implicit writeback yoktur. Numeric opcode ve bit alanları [Instruction Encoding](NEXSUS-CPU-INSTRUCTION-ENCODING-001.md) belgesinde tanımlıdır.

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

OW ve TW'nin kullanım alanları şunlardır:

- OW: işletim sistemi çalışma verileri, syscall/I/O exchange ve kernel bookkeeping.
- TW: task-local geçici hesaplama sonuçları, register spill, küçük yapılandırılmış veri nesneleri ve doğrudan adreslenebilir çalışma dosyaları.
- XFER.WS.MEM: OW/TW verisini Data RAM'e kalıcılaştırma veya Data RAM'den geri yükleme.

OW/TW çekirdek-yerel kaynaklardır. GPU, FAPU ve diğer düğümlere otomatik olarak ortak workspace görünümü verilmez; bu birimler kendi bellek erişim mekanizmalarını kullanır.

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

NEXSUS CPU'nun OW/TW ve register görünüm mimarisi, yazılımın veriyle doğrudan çalışmasını ve donanımın gereksiz ara adımları azaltmasını hedefler.

64 bitlik temel kayıt erişimi, değişken genişlikli veri alanları, sayfa kimliği–ofset adreslemesi ve donanım destekli kısmi yazma birlikte ele alınır.

Böylece NEXSUS, yığın kullanımını zorunlu kılmadan geçici verileri yönetebilir; Nexus Flow derleyicisi de uygun durumlarda daha kısa ve daha verimli kod üretebilir.
