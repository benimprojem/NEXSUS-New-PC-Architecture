
# NEI — NEXSUS Expansion Interface
## Fiziksel Konektör, Lane Ölçekleme ve Güç Dağıtım Mimarisi

**Doküman Kodu:** NEXSUS-NEI-PHY-001  
**Konu:** NEI fiziksel bağlantı, lane grupları, kontrol hatları ve güç ölçekleme mimarisi  
**Statü:** Kavramsal / Teknik Tasarım  
**Mimari:** NEXSUS System Fabric Native

---

# 1. Amaç

NEI (NEXSUS Expansion Interface), NEXSUS System Fabric'in genişleme kartlarına doğrudan açılan fiziksel ve mantıksal bağlantı standardıdır.

NEI;

- GPU,
- FAPU,
- ağ işlemcileri,
- capture kartları,
- yüksek hızlı ağ kartları,
- özel hesaplama hızlandırıcıları,
- veri işleme kartları,
- gelecekte ortaya çıkabilecek yeni hızlandırıcılar

gibi cihazların NEXSUS System Fabric'e doğrudan bağlanmasını sağlar.

NEI'nin temel amacı yalnızca yüksek bant genişliği sağlamak değildir.

Temel hedef:

> **Cihazın gerçekten ihtiyaç duyduğu kadar veri hattı ve güç kapasitesi sağlamaktır.**

Bu nedenle NEI sabit x4/x8/x16/x32 sınıflarına bağlı değildir.

Temel genişleme birimi **4 lane**'dir.

---

# 2. Temel NEI Ölçekleme Prensibi

NEI'nin minimum fiziksel bağlantısı:

\[
x4
\]

olacaktır.

Her ilave bağlantı grubu:

\[
\Delta x = 4
\]

lane ekler.

Dolayısıyla desteklenen genişlikler:

\[
x4,\ x8,\ x12,\ x16,\ x20,\ x24,\ x28,\ x32
\]

şeklindedir.

Örneğin:

\[
x12 = 4+4+4
\]

\[
x20 = 4+4+4+4+4
\]

\[
x28 = 4+4+4+4+4+4+4
\]

şeklinde oluşur.

Bu yapı sayesinde 12 lane ihtiyacı olan bir cihaz için gereksiz yere 16 lane tahsis edilmesi gerekmez.

Aynı şekilde 24 lane isteyen bir cihaz için 32 lane bağlantısı zorunlu değildir.

---

# 3. NEI Lane Grubu

NEI'nin temel fiziksel birimi:

> **NEI Lane Group (NLG-4)**

olarak tanımlanır.

Bir NLG-4:

- 4 tam çift yönlü yüksek hızlı lane,
- gerekli GND referansları,
- ilgili güç dağıtım kapasitesi

içerir.

Her lane:

```text
TX+
TX-
RX+
RX-
```

şeklinde tam çift yönlü diferansiyel bağlantıdır.

Dolayısıyla dört lane:

```text
Lane 0 → TX/RX
Lane 1 → TX/RX
Lane 2 → TX/RX
Lane 3 → TX/RX
```

oluşturur.

---

# 4. Fiziksel Konektör Bölümleri

NEI edge connector fiziksel olarak şu sırayı kullanır:

```text
KART TAKILMA YÖNÜ →

┌──────┬──────────┬──────────┬──────────┬──────────┬───────┐
│ CTRL │ POWER-0  │  NLG-0   │  NLG-1   │  NLG-2   │ ...   │
└──────┴──────────┴──────────┴──────────┴──────────┴───────┘
         x4 BASE      +4         +4         +4
```

Bölümler:

1. **CTRL**
2. **POWER-0**
3. **NLG-0**
4. **POWER-1**
5. **NLG-1**
6. **POWER-2**
7. **NLG-2**
8. devam eden güç/lane grupları

Burada kontrol bağlantıları en önde bulunur.

Bu fiziksel yerleşim özellikle önemlidir.

---

# 5. Kontrol Bölgesi

Konektörün ilk bölümü kontrol ve yönetim sinyallerine ayrılır.

Konsept kontrol pinleri:

| Pin | Sinyal | Görev |
|---|---|---|
| C01 | PRESENCE | Kart mevcut algılama |
| C02 | RESET# | Kart reset |
| C03 | PWR_EN | Güç etkinleştirme |
| C04 | PWR_GOOD | Güç hazır |
| C05 | MGMT_TX | Yönetim verisi TX |
| C06 | MGMT_RX | Yönetim verisi RX |
| C07 | EVENT | Olay/interrupt bildirimi |
| C08 | CLK_REF | Referans/senkronizasyon |
| C09 | WAKE# | Uyandırma |
| C10 | CONFIG | Yapılandırma hattı |
| C11 | RESERVED | Gelecek kullanım |
| C12 | GND | Referans |

Bu pinlerin tam sayısı daha sonra elektriksel tasarım sırasında değişebilir.

Buradaki amaç mümkün olduğunca az kontrol piniyle tüm yönetim işlevlerini gerçekleştirmektir.

---

# 6. Kontrol Pinlerinin Önde Olmasının Avantajı

Kart takılırken sistem önce:

```text
PRESENCE
   ↓
CARD IDENTIFICATION
   ↓
POWER CAPABILITY
   ↓
POWER ENABLE
   ↓
POWER GOOD
   ↓
RESET RELEASE
   ↓
PHY TRAINING
   ↓
LANE DISCOVERY
   ↓
FABRIC DISCOVERY
```

aşamalarından geçebilir.

Böylece yüksek hızlı lane'lerin doğrudan aktif edilmesi gerekmez.

Özellikle yüksek güçlü kartlarda bu yapı önemlidir.

---

# 7. Lane Grubu Yapısı

Her NLG-4 dört lane içerir.

Örneğin ilk grup:

```text
NLG-0

Lane 0
Lane 1
Lane 2
Lane 3
```

İkinci grup:

```text
NLG-1

Lane 4
Lane 5
Lane 6
Lane 7
```

Üçüncü grup:

```text
NLG-2

Lane 8
Lane 9
Lane 10
Lane 11
```

şeklindedir.

Böylece:

```text
NLG-0 → x4
NLG-0 + NLG-1 → x8
NLG-0 + NLG-1 + NLG-2 → x12
NLG-0 ... NLG-3 → x16
```

şeklinde bağlantı genişletilir.

---

# 8. x32 Fiziksel Üst Sınır

NEI v1.x fiziksel konektörü:

\[
x32
\]

seviyesine kadar destekleyecek şekilde tasarlanır.

Toplam sekiz adet 4-lane grubu bulunabilir:

```text
NLG-0 → Lane 0–3
NLG-1 → Lane 4–7
NLG-2 → Lane 8–11
NLG-3 → Lane 12–15
NLG-4 → Lane 16–19
NLG-5 → Lane 20–23
NLG-6 → Lane 24–27
NLG-7 → Lane 28–31
```

Dolayısıyla:

\[
8\times4=32
\]

lane elde edilir.

---

# 9. Güç Mimarisi

NEI'de güç kapasitesi lane sayısından bağımsız düşünülmez.

Her ilave 4-lane grubu aynı zamanda ilave güç kapasitesi getirir.

Başlangıç teorik tasarım değeri:

\[
P_{group}=75W
\]

olarak alınabilir.

Böylece:

\[
P_{max}=75W\times N_{group}
\]

olur.

| NEI bağlantısı | Lane | 4-lane grubu | Teorik maksimum güç |
|---:|---:|---:|---:|
| x4 | 4 | 1 | **75 W** |
| x8 | 8 | 2 | **150 W** |
| x12 | 12 | 3 | **225 W** |
| x16 | 16 | 4 | **300 W** |
| x20 | 20 | 5 | **375 W** |
| x24 | 24 | 6 | **450 W** |
| x28 | 28 | 7 | **525 W** |
| x32 | 32 | 8 | **600 W** |

Bu değerler **teorik mimari güç bütçesidir**; nihai sürekli güç sınırı değildir.

Gerçek sınır;

- pin başına maksimum akım,
- toplam güç pin sayısı,
- kullanılan besleme gerilimi,
- PCB bakır kalınlığı,
- konektör sıcaklığı,
- temas direnci,
- kart termal tasarımı,
- güç dağıtım katmanları

ile doğrulanmalıdır.

PCIe'de de zaman içinde 75 W'tan yüzlerce watt seviyesine çıkan farklı güç sınıfları tanımlanmıştır; bu nedenle NEI'nin güç kapasitesini fiziksel konektörün bir parçası olarak ele alması gerçekçi bir tasarım yaklaşımıdır.

---

# 10. Güç Gruplarının Dağılımı

Gücün bütün konektörün tek bir noktasında toplanması yerine, lane grupları boyunca dağıtılması tercih edilir.

Örneğin:

```text
CTRL
 │
 ├── POWER-0
 │
 ├── NLG-0
 │
 ├── POWER-1
 │
 ├── NLG-1
 │
 ├── POWER-2
 │
 ├── NLG-2
 │
 ├── POWER-3
 │
 ├── NLG-3
 │
 └── ...
```

Böylece yüksek güçlü x24/x28/x32 kartlarda akım tek bir küçük temas bölgesine yüklenmez.

Güç pinleri arasında GND pinleri de dağıtılmalıdır.

---

# 11. Önerilen Güç Pin Grupları

Her güç bölgesi için kavramsal olarak:

```text
GND
PWR+
PWR+
GND
PWR_AUX
GND
```

gibi bir yapı kullanılabilir.

Burada:

- `PWR+` ana yüksek güçlü besleme,
- `PWR_AUX` düşük güçlü yardımcı besleme,
- `GND` güç dönüş yolu

olarak kullanılabilir.

Gerçek gerilim değerleri henüz sabitlenmemiştir.

Örneğin ileride:

```text
48 V
12 V
5 V
3.3 V
```

gibi birden fazla ray kullanılabilir.

Ancak NEI'nin sistem mimarisinde yüksek güçlü kartlara doğrudan yüksek gerilimli ana besleme verilecekse, kart üzerindeki VRM'nin bu gerilimi gerekli düşük gerilimlere dönüştürmesi daha verimli olabilir.

---

# 12. Güç ve Lane İlişkisi

NEI'de önemli kural:

> **Her +4 lane genişleme grubu, fiziksel olarak karşılık gelen ek güç kapasitesine sahip olmalıdır.**

Örneğin x12:

```text
              x12 CARD

CTRL
 │
POWER-0 ─── 75 W
 │
NLG-0 ──── Lane 0–3
 │
POWER-1 ─── +75 W
 │
NLG-1 ──── Lane 4–7
 │
POWER-2 ─── +75 W
 │
NLG-2 ──── Lane 8–11
```

Toplam teorik güç:

\[
75+75+75=225W
\]

olur.

---

# 13. x12 ile x16 Arasındaki Fark

Bu yaklaşımın önemli avantajlarından biri budur.

Bir kartın ihtiyacı:

\[
12\ lane
\]

ise:

```text
NEI-x12
```

kullanabilir.

Kartın:

```text
NEI-x16
```

kullanması zorunlu değildir.

Aynı şekilde:

\[
24\ lane
\]

ihtiyacı olan kart için:

```text
NEI-x24
```

yeterlidir.

x32 yalnızca gerçekten ihtiyaç varsa kullanılır.

Bu sayede:

- lane israfı,
- gereksiz konektör alanı,
- gereksiz güç kapasitesi,
- gereksiz PHY maliyeti

azaltılabilir.

---

# 14. Lane Negotiation

Kart ve anakart bağlantı kurarken kullanılabilecek maksimum genişliği belirler.

Örneğin kart:

```text
Maximum capability = x24
```

anakart slotu:

```text
Maximum capability = x32
```

ise bağlantı:

```text
Negotiated Link = x24
```

olabilir.

Benzer şekilde:

```text
Card = x12
Slot = x32

→ Active = x12
```

olabilir.

Dolayısıyla slotun fiziksel kapasitesi ile aktif link genişliği birbirinden ayrılır.

---

# 15. Aynı Fiziksel Slotta Farklı Kartlar

Örneğin bir x32 NEI slotu:

```text
┌───────────────────────────────────────────────┐
│ CTRL │ PWR │ x4 │ +4 │ +4 │ +4 │ +4 │ +4... │
└───────────────────────────────────────────────┘
```

şeklinde olabilir.

Aynı slot:

```text
x4  kart
x8  kart
x12 kart
x16 kart
x20 kart
x24 kart
x28 kart
x32 kart
```

ile kullanılabilir.

Bu, NEI'nin temel fiziksel uyumluluk prensibidir.

---

# 16. Kartın Fiziksel Uzunluğu

Lane sayısı ile kartın PCB uzunluğu birbirinden ayrılmalıdır.

Örneğin fiziksel olarak uzun bir kart:

```text
Fiziksel kart = büyük
Elektriksel bağlantı = x12
```

olabilir.

Ya da küçük bir kart:

```text
Fiziksel kart = küçük
Elektriksel bağlantı = x4
```

olabilir.

Dolayısıyla:

> **Kartın fiziksel boyutu, NEI link genişliğini belirlemez.**

Bu, farklı form faktörlerinin ileride oluşturulabilmesini sağlar.

---

# 17. Lane Gruplarında GND Dağılımı

Yüksek hızlı diferansiyel sinyaller arasında uygun referans düzlemi oluşturmak için GND pinleri düzenli aralıklarla dağıtılmalıdır.

Kavramsal örnek:

```text
GND
L0+
L0-
GND
L1+
L1-
GND
L2+
L2-
GND
L3+
L3-
GND
```

Gerçek pin dizilimi ise PCB empedansı ve konektör üretim teknolojisiyle birlikte optimize edilecektir.

Ama temel prensip:

> **Yüksek hızlı sinyal grupları arasında yeterli GND referansı bulunmalıdır.**

---

# 18. Güç ve Sinyal Ayrımı

NEI edge connector üzerinde üç temel fiziksel bölge bulunur:

```text
┌─────────────┬────────────────┬─────────────────────┐
│   CONTROL   │     POWER      │   HIGH-SPEED DATA   │
└─────────────┴────────────────┴─────────────────────┘
```

Bunun avantajları:

- güç hatlarının yüksek hızlı sinyallerden ayrılması,
- kontrol bağlantısının önce yapılması,
- güç sıralamasının yönetilebilmesi,
- lane genişlemesinin modüler olması,
- PCB routing'in kolaylaşması.

---

# 19. NEI Güç Sınıfları

İlk mimari tasarım için güç sınıfları:

| Sınıf | Link | Teorik güç |
|---|---:|---:|
| NEI-P1 | x4 | 75 W |
| NEI-P2 | x8 | 150 W |
| NEI-P3 | x12 | 225 W |
| NEI-P4 | x16 | 300 W |
| NEI-P5 | x20 | 375 W |
| NEI-P6 | x24 | 450 W |
| NEI-P7 | x28 | 525 W |
| NEI-P8 | x32 | 600 W |

Burada güç sınıfı ile lane sınıfı aynı olmak zorunda değildir.

Örneğin düşük güç tüketen bir cihaz:

```text
x24
75 W
```

kullanabilir.

Yüksek güç tüketen başka bir cihaz:

```text
x12
225 W
```

kullanabilir.

Bu nedenle **güç bütçesi ve link genişliği ayrı capability alanlarıdır.**

---

# 20. Daha Yüksek Güç İçin Harici Güç

600 W teorik konektör gücü NEI'nin temel hedefi olarak yeterlidir.

Ancak gelecekte:

```text
>600 W
```

gerektiren GPU veya hesaplama kartları çıkarsa, temel NEI veri bağlantısını değiştirmek yerine ayrı yardımcı güç bağlantısı kullanılabilir.

Örneğin:

```text
NEI x32
+
NEXSUS Auxiliary Power
```

şeklinde.

Bu durumda 32 lane sınırı korunurken kartın toplam güç bütçesi artırılabilir.

PCIe ekosisteminde de 300 W'ın üzerindeki güç bütçeleri için ilave güç yönetimi mekanizmaları geliştirilmiştir.

---

# 21. NEI Fiziksel Pin Grupları

İlk prototip için pinler fonksiyonel gruplar halinde tanımlanır.

### Grup A — Control

```text
C01  PRESENCE
C02  RESET#
C03  PWR_EN
C04  PWR_GOOD
C05  MGMT_TX
C06  MGMT_RX
C07  EVENT
C08  CLK_REF
C09  WAKE#
C10  CONFIG
C11  RESERVED
C12  GND
```

### Grup B — Base Power

```text
P01  GND
P02  PWR+
P03  PWR+
P04  GND
P05  PWR_AUX
P06  GND
```

### Grup C — NLG-0

```text
L00_TX+
L00_TX-
L00_RX+
L00_RX-

L01_TX+
L01_TX-
L01_RX+
L01_RX-

L02_TX+
L02_TX-
L02_RX+
L02_RX-

L03_TX+
L03_TX-
L03_RX+
L03_RX-
```

### Grup D — Power Extension

```text
PWR-1
GND
PWR-1
GND
PWR_AUX
GND
```

### Grup E — NLG-1

```text
L04
L05
L06
L07
```

ve aynı yapı devam eder.

---

# 22. x32 Toplam Fiziksel Organizasyon

Kavramsal olarak:

```text
┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────── ... ───────┐
│CTRL  │ PWR0 │ NLG0 │ PWR1 │ NLG1 │ PWR2 │ NLG2 │ ... │ NLG7 │
└──────┴──────┴──────┴──────┴──────┴──────┴──────┴─────── ... ───────┘
          │       │      │       │
          │       └ x4 ──┘       │
          └──── güç ─────────────┘
```

Burada her NLG:

\[
4\ lanes
\]

ve toplam:

\[
8\times4=32\ lanes
\]

olur.

---

# 23. NEI'nin NEXSUS System Fabric ile İlişkisi

NEI sadece fiziksel PCIe benzeri bir bağlantı değildir.

Kart bağlandıktan sonra:

```text
NEI PHY
   ↓
NEI Link
   ↓
NEI Transport
   ↓
System Fabric
   ↓
Fabric Address
   ↓
Device Resource
```

oluşur.

Kart doğrudan System Fabric düğümü haline gelir.

Örneğin:

```text
GPU
 │
NEI
 │
System Fabric
 │
 ├── Data MOSRAM
 ├── FAPU
 ├── M-SSD
 └── Display Controller
```

şeklinde bağlantılar mümkün olabilir.

CPU bütün veriyi kendisinden geçirmek zorunda değildir.

---

# 24. NEI'de Doğrudan Veri Yolları

Örneğin:

```text
M-SSD
  │
  ▼
System Fabric
  │
  ▼
GPU
```

veya:

```text
NPI Camera
     │
     ▼
System Fabric
     │
     ▼
GPU / FAPU
```

veya:

```text
GPU
 │
 ▼
Data MOSRAM
```

mümkündür.

Bu nedenle NEI'nin asıl avantajı yalnızca lane sayısı değildir.

Asıl avantaj:

> **Expansion card'ın System Fabric'in doğrudan bir parçası olmasıdır.**

---

# 25. Sonuç

NEI'nin fiziksel mimarisi şu temel prensiplere dayanır:

1. Minimum bağlantı genişliği **x4**.
2. Temel genişleme birimi **+4 lane**.
3. x4, x8, x12, x16, x20, x24, x28 ve x32 desteklenir.
4. x32 fiziksel üst sınır olarak baştan tasarlanır.
5. Kontrol pinleri konektörün en başında bulunur.
6. Güç bölgesi kontrol bölümünden sonra gelir.
7. Her +4 lane grubu ek güç kapasitesi getirir.
8. İlk teorik güç ölçeği +4 lane başına 75 W'dır.
9. x32 için teorik temel konektör gücü 600 W'tır.
10. Güç kapasitesi ve lane genişliği birbirinden bağımsız capability olarak raporlanabilir.
11. x12 isteyen karta x16 zorunlu değildir.
12. x24 isteyen karta x32 zorunlu değildir.
13. Link genişliği bağlantı kurulurken negotiate edilir.
14. Aynı fiziksel slot farklı NEI genişliklerini destekleyebilir.
15. Yüksek hızlı sinyaller GND referanslarıyla düzenlenir.
16. 600 W üzeri gelecek kullanım için yardımcı güç bağlantısı eklenebilir.
17. NEI doğrudan NEXSUS System Fabric'e bağlanır.
18. Expansion card, klasik anlamda yalnızca bir I/O cihazı değil, **Fabric node** olarak çalışır.

### Temel NEI modeli

```text
                 NEXSUS SYSTEM FABRIC
                          │
                         NEI
                          │
        ┌─────────────────┴──────────────────┐
        │                                    │
     CONTROL                              POWER
        │                                    │
        └─────────────────┬──────────────────┘
                          │
                    NLG-0  +4
                          │
                    NLG-1  +4
                          │
                    NLG-2  +4
                          │
                         ...
                          │
                    NLG-7  +4
                          │
                        x32
```

**NEI'nin temel felsefesi:**

\[
\boxed{\text{İhtiyaç kadar lane + ihtiyaç kadar güç}}
\]

Bu yaklaşım NEXSUS'un System Fabric felsefesiyle doğrudan uyumludur: gereksiz kaynak tahsisi yerine, bağlantının gerçek ihtiyacına göre ölçeklenmesi.
