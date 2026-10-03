# MOSRAM Teknik Dokümantasyonu
**Doküman Kodu:** MOSRAM-PHY-2026-001  
**Konu:** 5 nm / 7 nm Üretim Teknolojileri ile MOSRAM Hücre Geometrisi, Kapasitif Okuma ve Fiziksel Hız Modeli  
**Statü:** Teknik Araştırma / Ön Fiziksel Model

---

# 1. Amaç

Bu çalışmanın amacı, MOSRAM mimarisinin tek bir bellek hücresinden başlayarak 64-bit paralel okuma bloğuna kadar fiziksel hız sınırını sayısallaştırmaktır.

Temel mimari:

\[
\boxed{
1T\ MOSFET+
Q_{gate}\ depolama+
dikey\ kapasitif\ prob+
tahribatsız\ okuma
}
\]

olarak kabul edilir.

MOSRAM hücresinde veri, MOSFET gate'inde bulunan elektriksel yük ile temsil edilir.

\[
0\rightarrow Q_G\approx0
\]

\[
1\rightarrow Q_G>0
\]

Okuma sırasında gate yeniden sürülmez ve drain-source kanalından okuma akımı geçirilmez.

Dolayısıyla temel okuma işlemi:

\[
\boxed{
Q_G
\rightarrow
V_G
\rightarrow
E_{field}
\rightarrow
V_{probe}
\rightarrow
Sense
}
\]

şeklindedir.

Bu nedenle okuma işlemi hücrenin durumunu değiştirmemelidir:

\[
\boxed{
READ(Q_G)=Q_G
}
\]

Bu özellik sağlanabilirse DRAM'deki destructive-read/restore yaklaşımına ihtiyaç kalmaz.

---

# 2. Üretim yaklaşımı

MOSRAM'ın bütün fiziksel boyutlarının 5 nm olması gerekli değildir.

Burada iki farklı ölçek kullanılmalıdır:

### Kontrol elektroniği

\[
\boxed{5-7\,nm}
\]

- sense amplifier
- decoder
- latch
- timing logic
- word controller
- I/O
- veri yolu sürücüleri

### MOSRAM bellek hücresi

\[
\boxed{5-30\,nm\ aralığında\ optimize\ edilebilir}
\]

MOSFET'in fiziksel olarak 5 nm sınıfında olması zorunlu değildir.

Hatta bellek hücresini biraz büyütmek, depolanabilir yük miktarını ve prob sinyalini artırıyorsa toplam performansı iyileştirebilir.

Bu yaklaşım özellikle önemlidir çünkü modern FinFET'lerde transistor boyutu ile etkin kanal genişliği birbirinden tamamen aynı şey değildir; FinFET geometrisi, alan ve transistor etkin genişliği arasında ek tasarım serbestliği sağlar.

TSMC'nin N5 sürecinde 0.021 µm² SRAM hücresinin gösterilmiş olması, 5 nm sınıfı üretim ortamında çok küçük bellek hücrelerinin üretilebilirliğine somut bir referans sağlar.

---

# 3. Önerilen temel MOSRAM hücresi

İlk fiziksel model için MOSFET'in minimum geometrisini zorlamak yerine orta büyüklükte bir hücre seçmek daha güvenlidir.

Önerilen başlangıç:

\[
A_G=20\times20\,nm^2
\]

ve alternatif:

\[
A_G=30\times30\,nm^2
\]

olabilir.

Bu hücreler 5/7 nm kontrol elektroniği ile birlikte kullanılabilir.

Temel yapı:

```text
                 READ PROBE
              ┌─────────────┐
              │   METAL     │
              └──────┬──────┘
                     │
             dielectric
                     │
              ┌──────┴──────┐
              │  Q_GATE     │
              │  1 / 0      │
              └──────┬──────┘
                     │
                 gate oxide
                     │
              ┌─────────────┐
              │  MOSFET     │
              │   CHANNEL   │
              └─────────────┘
                 │       │
                 S       D
```

Burada üst prob gate ile elektriksel olarak temas etmez.

Dolayısıyla:

\[
I_{probe\rightarrow gate}=0
\]

olması hedeflenir.

Prob yalnızca elektrik alan üzerinden gate durumunu algılar.

---

# 4. Gate üzerinde depolanabilecek yük

Bir gate'in kapasitesi:

\[
C_G
\]

olarak tanımlansın.

Gate üzerinde \(N_e\) elektron bulunduğunda:

\[
Q_G=N_e e
\]

olur.

Gate gerilim değişimi:

\[
\Delta V_G=
\frac{Q_G}{C_G}
=
\frac{N_e e}{C_G}
\]

şeklindedir.

Bu denklem MOSRAM'ın temel denklemidir.

---

# 5. Tek elektron sınırı

Tek elektron için:

\[
N_e=1
\]

ve:

\[
\Delta V_G=\frac{e}{C_G}
\]

olur.

Örneğin:

\[
C_G=10\,aF
\]

ise:

\[
\Delta V_G
=
\frac{1.602\times10^{-19}}
{10\times10^{-18}}
\]

\[
\boxed{\Delta V_G\approx16\,mV}
\]

çıkar.

Eğer:

\[
C_G=5\,aF
\]

olursa:

\[
\boxed{\Delta V_G\approx32\,mV}
\]

olur.

Dolayısıyla tek elektron prensipte ölçülebilir bir gate potansiyel değişimi oluşturabilir.

Ancak burada önemli bir ayrım vardır:

\[
\boxed{
\text{tek elektron algılama sınırı}
\neq
\text{normal çalışma yükü}
}
\]

MOSRAM'ın gerçek çalışma durumunda tek elektronla sınırlanmak zorunda değiliz.

Örneğin:

\[
N_e=10
\]

ise sinyal yaklaşık 10 kat büyür.

---

# 6. Gate alanının etkisi

Gate alanı büyüdükçe gate kapasitesi de artar.

Basitleştirilmiş olarak:

\[
C_G\propto A_G
\]

olduğundan:

\[
\Delta V_G=
\frac{N_e e}{C_G}
\]

nedeniyle büyük gate:

\[
\Delta V_G\downarrow
\]

oluşturur.

Fakat büyük gate'in avantajı:

\[
N_{max}\uparrow
\]

ve:

\[
\text{yük toleransı}\uparrow
\]

olmasıdır.

Bu nedenle MOSRAM için optimum nokta:

\[
\boxed{
\text{minimum gate alanı}
}
\]

değil,

\[
\boxed{
\text{yeterli sinyal + yeterli üretim marjı + düşük parazit}
}
\]

veren gate alanıdır.

Bu nedenle ilk prototipte 5 nm fiziksel sınıra zorlanmış gate yerine 20–30 nm sınıfı hücre araştırmaya daha uygundur.

---

# 7. Gate-prob kapasitesi

Prob ile gate arasındaki kapasite:

\[
C_{GP}
=
\frac{\epsilon_0\epsilon_r A_{probe}}{d}
\]

ile yaklaşık olarak modellenebilir.

Burada:

- \(A_{probe}\): etkin prob alanı
- \(d\): gate-prob yalıtkan kalınlığı
- \(\epsilon_r\): yalıtkanın bağıl dielektrik sabiti

dir.

Örnek:

\[
A_{probe}=20\times20\,nm^2
\]

\[
d=5\,nm
\]

\[
\epsilon_r=7
\]

alınırsa:

\[
C_{GP}\approx4.96\,aF
\]

elde edilir.

Bu değer gate'in tamamının kapasitansı değil, **gate-prob kuplaj kapasitesidir.**

---

# 8. Parazit kapasite

Gerçek çipte:

\[
C_{total}\neq C_{GP}
\]

olacaktır.

Daha gerçekçi model:

\[
\boxed{
C_{sense}
=
C_{GP}
+
C_{fringe}
+
C_{via}
+
C_{metal}
+
C_{neighbor}
+
C_{input}
}
\]

şeklindedir.

Burada özellikle:

\[
C_{neighbor}
\]

önemlidir.

Çünkü 64 bit paralel hücre dizisinde bir probun komşu hücreleri görmeye başlaması cross-talk oluşturabilir.

Bu nedenle ilk tasarım hedefi:

\[
\boxed{
C_{neighbor}\ll C_{GP}
}
\]

olmalıdır.

---

# 9. Prob sinyali

Gate'teki gerilim değişiminin probda tamamı görülmez.

Kuplaj katsayısını:

\[
\alpha
\]

olarak tanımlayalım.

\[
0<\alpha<1
\]

olur.

Yaklaşık prob sinyali:

\[
\boxed{
\Delta V_{probe}
\approx
\alpha
\frac{N_e e}{C_G}
}
\]

şeklindedir.

Örneğin:

\[
C_G=10\,aF
\]

\[
N_e=10
\]

\[
\alpha=0.2
\]

ise:

\[
\Delta V_{probe}
\approx
0.2\times160\,mV
\]

\[
\boxed{
\Delta V_{probe}\approx32\,mV
}
\]

olur.

Bu artık sense amplifier açısından çok daha rahat bir sinyaldir.

---

# 10. Termal gürültü

Kapasitif sistemlerde temel termal gürültü ölçeği:

\[
V_n\approx
\sqrt{\frac{kT}{C}}
\]

ile ifade edilebilir.

300 K'de:

\[
kT\approx4.14\times10^{-21}J
\]

olduğundan, örneğin:

\[
C=0.5\,fF
\]

için:

\[
V_n
\approx
2.9\,mV
\]

civarındadır.

Bu nedenle 32 mV seviyesinde bir sinyal:

\[
SNR\approx11
\]

mertebesinde olabilir.

Bu yalnızca termal \(kT/C\) gürültüsünü içeren idealize edilmiş bir tahmindir.

Gerçek sistemde:

- transistor noise
- sense amplifier noise
- substrate noise
- clock coupling
- neighboring-cell coupling
- supply noise

eklenir.

Dolayısıyla gerçek SNR bundan daha düşük olacaktır.

---

# 11. Tek elektron için SNR

Tek elektron:

\[
N_e=1
\]

olduğunda:

\[
\Delta V_{probe}
=
\alpha\frac{e}{C_G}
\]

olur.

Örneğin:

\[
C_G=10\,aF
\]

\[
\alpha=0.2
\]

ise:

\[
\Delta V_{probe}\approx3.2\,mV
\]

çıkar.

Bu değer 0.5 fF toplam sense kapasitesindeki yaklaşık 2.9 mV termal gürültüyle aynı mertebededir.

Dolayısıyla:

\[
\boxed{
1\ elektron
}
\]

bu parametrelerle **teorik algılama sınırına yakın** olur.

Bu nedenle normal MOSRAM çalışma durumunda daha fazla yük kullanmak daha doğru olacaktır.

Örneğin:

\[
N_e=10-100
\]

aralığı çok daha yüksek SNR sağlayabilir.

Tek elektron ise:

\[
\boxed{\text{minimum algılama sınırı}}
\]

olarak tutulabilir.

---

# 12. Optimum yalıtkan kalınlığı

Yalıtkanı inceltmek:

\[
C_{GP}\uparrow
\]

yapar.

Bu kuplajı artırır.

Fakat:

\[
d\downarrow
\]

oldukça:

- gate-prob parazitik coupling artar
- komşu hücre coupling artabilir
- dielectric leakage artabilir
- üretim toleransı önem kazanır
- probun gate üzerindeki etkisi artar

Dolayısıyla teorik olarak:

\[
d\rightarrow0
\]

istenmez.

İlk tasarım taraması için:

\[
\boxed{
d=3,\ 4,\ 5,\ 6,\ 8,\ 10\,nm
}
\]

aralıklarının simülasyonu yapılmalıdır.

Bunun sonucunda:

\[
SNR(d)
\]

ve:

\[
t_{sense}(d)
\]

eğrileri çıkarılmalıdır.

Optimum nokta:

\[
\boxed{
\max_d\left[
\frac{SNR(d)}{t_{sense}(d)}
\right]
}
\]

veya daha doğru olarak çok kriterli:

\[
\boxed{
SNR\ge SNR_{min}
}
\]

koşulunu sağlayan en hızlı \(d\) değeri olacaktır.

---

# 13. Minimum sense süresi

Sense devresinin ilk RC modeli:

\[
t_{RC}=R_{sense}C_{total}
\]

şeklindedir.

Fakat güvenilir dijital karar için:

\[
t_{sense}=K\,R_{sense}C_{total}
\]

alınabilir.

Burada:

\[
K\approx3-10
\]

aralığında tasarım marjı olarak incelenebilir.

Örneğin:

\[
R_{sense}=2\,k\Omega
\]

ve:

\[
C_{total}=0.5\,fF
\]

ise:

\[
t_{RC}=1\,ps
\]

olur.

\[
K=5
\]

alınırsa:

\[
\boxed{
t_{sense}\approx5\,ps
}
\]

elde edilir.

Bu **hücrenin fiziksel sense zamanı**dır.

---

# 14. Gerçek bellek cycle zamanı

Çip düzeyinde:

\[
t_{cycle}
=
t_{address}
+
t_{probe}
+
t_{settle}
+
t_{sense}
+
t_{latch}
+
t_{routing}
\]

olmalıdır.

Örnek 5 nm kontrol mimarisi:

| İşlem | Hedef |
|---|---:|
| Adres/decoder | 5–10 ps |
| Probe pulse | 2–5 ps |
| Elektrostatik settling | 5 ps |
| Sense amplifier | 10–15 ps |
| 64-bit latch | 5–10 ps |
| Local routing | 10–20 ps |
| Güvenlik marjı | 10–20 ps |
| **Toplam** | **47–85 ps** |

Bu durumda:

\[
f_{MOSRAM}
\approx
12-21\,GHz
\]

mertebesinde bir mimari hedef ortaya çıkar.

Bu değer **fiziksel olarak doğrulanmış MOSRAM frekansı değildir**; yukarıdaki varsayımlardan türetilmiş bir ilk tasarım bütçesidir.

---

# 15. 7 nm kontrol mimarisi

7 nm'de benzer bir bütçede:

\[
t_{cycle}\approx60-100\,ps
\]

hedeflenebilir.

Dolayısıyla:

\[
f\approx10-16.7\,GHz
\]

mertebesi ilk araştırma hedefi olabilir.

Burada 5 nm ile 7 nm arasındaki farkın MOSRAM hücresinde dramatik olması gerekmez.

Çünkü hücreyi:

\[
20-30\,nm
\]

gibi daha büyük tasarlayabiliriz.

Asıl avantaj 5 nm'de:

\[
\boxed{
sense/decoder/controller
}
\]

alanının küçülmesi ve daha fazla paralel kanalın aynı alan içine yerleştirilebilmesidir.

---

# 16. 64-bit paralel okuma

MOSRAM'ın temel mimari hedefi:

\[
\boxed{64\ bit/cycle}
\]

olarak alınabilir.

64 hücre aynı anda prob darbesi alır.

```text
 B0   B1   B2   B3   ...   B63
 │    │    │    │           │
 ▼    ▼    ▼    ▼           ▼
 S0   S1   S2   S3   ...   S63
 │    │    │    │           │
 └────┴────┴────┴─────...───┘
              │
          64-bit LATCH
              │
           DATA BUS
```

Burada:

\[
64bit=8byte
\]

olduğu için:

\[
\boxed{
BW=8f
}
\]

olur.

---

# 17. 64-bit MOSRAM için hız senaryoları

### Muhafazakâr senaryo

\[
t_{cycle}=100ps
\]

\[
f=10GHz
\]

\[
BW=10\times8
\]

\[
\boxed{80\,GB/s}
\]

### Orta senaryo

\[
t_{cycle}=70ps
\]

\[
f\approx14.3GHz
\]

\[
\boxed{114\,GB/s}
\]

### İyileştirilmiş senaryo

\[
t_{cycle}=50ps
\]

\[
f=20GHz
\]

\[
\boxed{160\,GB/s}
\]

Burada her değer:

\[
\boxed{8byte/cycle}
\]

üzerinden hesaplanmaktadır.

---

# 18. 4 × 64 mimarisi

Dört adet 64-bit paralel blok:

\[
4\times64=256bit
\]

olur.

Bir cycle'da:

\[
256bit=32byte
\]

aktarılır.

10 GHz'de:

\[
BW=32\times10^{10}
\]

\[
\boxed{320\,GB/s}
\]

20 GHz'de:

\[
\boxed{640\,GB/s}
\]

olur.

---

# 19. 8 × 64 mimarisi

\[
8\times64=512bit
\]

ve:

\[
512bit=64byte
\]

olur.

10 GHz:

\[
\boxed{640\,GB/s}
\]

20 GHz:

\[
\boxed{1.28\,TB/s}
\]

Burada artık hücrenin kendisinden ziyade:

\[
\boxed{
64\times8=512
}
\]

adet sense kanalının:

- güç tüketimi
- clock dağıtımı
- veri yolu
- routing
- ısı
- sense amplifier alanı

önemli hale gelir.

Dolayısıyla MOSRAM ölçeklenirken hızın yeni darboğazı hücre değil **I/O ve sense mimarisi** olacaktır.

---

# 20. MOSRAM'ın kritik mimari avantajı

Klasik destructive-read yaklaşımında:

\[
READ
\rightarrow
DATA\ LOSS/PERTURBATION
\rightarrow
RESTORE
\]

gerekebilir.

MOSRAM'da hedef:

\[
READ
\rightarrow
CAPACITIVE\ SENSE
\rightarrow
LATCH
\]

olduğundan:

\[
\boxed{
READ\rightarrow RESTORE
}
\]

işlemi kaldırılabilir.

Gate gerilimi okuma sırasında kullanılmadığı için ideal durumda:

\[
\Delta Q_G\approx0
\]

olur.

Dolayısıyla:

\[
Q_G(t_{read})\approx Q_G(0)
\]

ve:

\[
\boxed{
N_{read}\rightarrow\infty
}
\]

teorik olarak mümkün hale gelir.

Pratik sınır ise okuma nedeniyle oluşan küçük disturbance ve gate leakage olacaktır.

---

# 21. R_limit'in gerçek görevi

Bu modelde \(R_{limit}\) sürekli olarak gate'i açık tutan eleman değildir.

Yazma sırasında:

\[
V_{write}
\rightarrow
R_{limit}
\rightarrow
Q_G
\]

şeklinde yükleme akımını sınırlar.

Dolayısıyla:

\[
I_{write}\le I_{max}
\]

koşulu sağlanır.

Gate hedef yüke ulaştığında yazma bağlantısı kesilir.

Bu:

\[
\boxed{
R_{limit}=WRITE\ PROTECTION
}
\]

anlamına gelir.

RAM kullanımında gate yükünün uzun yıllar korunması şart değildir.

---

# 22. RAM ve non-volatile MOSRAM ayrımı

Burada iki ayrı teknoloji ortaya çıkar.

### MOSRAM

\[
\boxed{
yüksek hız+
kapasitif okuma+
kısa/orta retention
}
\]

### MOSRAM-NV

\[
\boxed{
yüksek hız+
kapasitif okuma+
charge\ trap+
uzun retention
}
\]

İkinci mimaride gate çevresinde daha güçlü bir elektron tuzağı tasarlanabilir.

Bu çalışma ayrı tutulmalıdır.

Çünkü RAM için gereksiz derecede güçlü charge trapping kullanmak:

\[
WRITE\ speed
\]

ve:

\[
WRITE\ energy
\]

açısından dezavantaj oluşturabilir.

---

# 23. İlk fiziksel tasarım önerisi

Araştırmanın ilk prototipi için:

\[
\boxed{
A_G=20\times20\,nm^2
}
\]

başlangıç değeri önerilebilir.

Prob:

\[
\boxed{
A_P=15-20\,nm\times15-20\,nm
}
\]

Yalıtkan:

\[
\boxed{
d=4-6\,nm
}
\]

İlk tarama:

\[
d=
3,4,5,6,8,10\,nm
\]

Gate yükü:

\[
\boxed{
N_e=10-100
}
\]

Tek elektron:

\[
\boxed{
N_e=1
}
\]

için yalnızca algılama sınırı testi.

Kontrol:

\[
\boxed{5-7\,nm}
\]

Sense bloğu:

\[
\boxed{64bit}
\]

İkinci seviye:

\[
\boxed{4\times64}
\]

Üçüncü seviye:

\[
\boxed{8\times64}
\]

---

# 24. Tasarım optimizasyon fonksiyonu

MOSRAM'ın optimum geometrisi tek bir değişkenle bulunmamalıdır.

Bir optimizasyon fonksiyonu:

\[
F=
\frac{SNR}
{t_{cycle}\,E_{read}}
\]

olarak tanımlanabilir.

Kısıtlar:

\[
SNR\ge SNR_{min}
\]

\[
P_{leak}\le P_{max}
\]

\[
C_{neighbor}/C_{GP}\le\epsilon
\]

\[
\Delta Q_G/Q_G\ll1
\]

olmalıdır.

Böylece:

\[
\boxed{
A_G,\ A_P,\ d,\ N_e,\ R_{sense}
}
\]

aynı anda optimize edilir.

---

# 25. En önemli sonuç

Bu ilk modelde MOSRAM için **5 nm transistor kullanmak zorunlu değildir.**

Daha doğru mimari:

\[
\boxed{
\text{20–30 nm sınıfı optimize edilmiş MOSRAM hücresi}
+
\text{5–7 nm kontrol/sense elektroniği}
}
\]

olabilir.

Böylece hücre:

- daha fazla elektron depolar,
- daha büyük \(\Delta V_G\) oluşturur,
- daha yüksek SNR verir,
- üretim toleransını artırır,

kontrol elektroniği ise:

- daha küçük alan,
- daha hızlı sense,
- daha fazla paralel kanal,
- daha kısa routing

sağlar.

---

# 26. İlk sonuç tablosu

| Parametre | MOSRAM başlangıç hedefi |
|---|---:|
| Kontrol teknolojisi | 5–7 nm |
| MOSRAM hücresi | 20–30 nm sınıfı |
| Gate yükü | 10–100 e⁻ |
| Tek elektron | Algılama sınırı |
| Probe dielectric | 4–6 nm başlangıç |
| Optimum arama aralığı | 3–10 nm |
| Gate-probe coupling | optimize edilecek |
| Toplam sense kapasitesi | <0.5–1 fF hedef |
| Yerel RC | ~1–2 ps |
| Sense | ~10–20 ps |
| 64-bit cycle | ~50–100 ps hedef |
| Frekans | ~10–20 GHz hedef |
| 64-bit bant genişliği | ~80–160 GB/s |
| 4×64 | ~320–640 GB/s |
| 8×64 | ~640 GB/s–1.28 TB/s |
| Read disturb | hedef: ihmal edilebilir |
| Restore | hedef: yok |
| Uzun süreli retention | MOSRAM için öncelik değil |

---

# 27. Modelin şu anki sınırı

Bu hesap henüz **SPICE/TCAD doğrulaması değildir**.

Özellikle şu parametrelerin gerçek proses verileriyle belirlenmesi gerekir:

\[
C_{gate}
\]

\[
C_{fringe}
\]

\[
C_{via}
\]

\[
C_{neighbor}
\]

\[
I_{leak}
\]

\[
V_T
\]

\[
\sigma_{V_T}
\]

\[
\sigma_{noise}
\]

ve:

\[
\alpha_{probe}
\]

Bunlar belirlendiğinde yukarıdaki modelden doğrudan:

\[
\boxed{
d_{opt}
}
\]

\[
\boxed{
N_{e,min}
}
\]

\[
\boxed{
t_{sense,min}
}
\]

ve:

\[
\boxed{
BW_{64},BW_{256},BW_{512}
}
\]

çıkarılabilir.

---

# 28. Sonuç

İlk fiziksel model MOSRAM'ın kritik noktasının **MOSFET'in anahtarlama hızı olmadığını** gösteriyor.

Asıl kritik zincir:

\[
\boxed{
N_e
\rightarrow
Q_G
\rightarrow
\Delta V_G
\rightarrow
\alpha
\rightarrow
\Delta V_{probe}
\rightarrow
SNR
\rightarrow
t_{sense}
\rightarrow
t_{cycle}
}
\]

şeklindedir.

Tek elektron seviyesi teorik algılama sınırını belirlerken, gerçek RAM hücresinde yaklaşık:

\[
10-100e^-
\]

gibi daha büyük bir yük kullanılması sinyal marjını ciddi biçimde artırabilir.

Bu durumda MOSRAM hücresini 5 nm'ye zorlamak yerine, **biraz daha büyük ve elektriksel olarak daha güçlü bir MOSRAM hücresi**, 5/7 nm'de üretilen çok hızlı 64-bit sense/control mimarisiyle birleştirmek daha mantıklı görünmektedir.

İlk tasarım hedefi olarak:

\[
\boxed{
50-100\,ps/64bit
}
\]

aralığı araştırılabilir.

Bu da:

\[
\boxed{
80-160\,GB/s
}
\]

tek 64-bit paralel blok için,

ve:

\[
\boxed{
640\,GB/s-1.28\,TB/s
}
\]

8×64 mimarisi için teorik hedef aralığı verir.

Bunlar henüz performans iddiası değil, **fiziksel tasarım bütçesinden çıkan araştırma hedefleridir**. En kritik sonraki çalışma, bu makaledeki varsayımsal \(C_G\), \(C_{GP}\), \(C_{parasitic}\) ve \(\alpha\) değerlerini gerçek 5/7 nm FinFET geometrileri üzerinden TCAD/SPICE seviyesine indirmektir.

TSMC'nin N5/N7 süreçlerinin gerçek üretim süreçleri olması ve N5'in yüksek yoğunluklu SRAM/logic için optimize edilmiş olması, kontrol elektroniği tarafının bu teknoloji ailesi üzerine kurulmasını gerçekçi bir başlangıç noktası yapıyor.
----


----

## MOSRAM'ın çalışabilirliğini belirleyen **en kritik iki noktadan biri prob kuplajı, diğeri okumanın gate yükünü bozup bozmadığı**. Bunları birbirinden ayırarak netleştirelim.

# 1. Temel hücre

Senin istediğin yapı:

```text
              READ PROBE
                  │
             ┌────┴────┐
             │  Metal  │
             └────┬────┘
                  │
             YALITKAN
                  │
             ┌────┴────┐
             │  GATE  │ ← QG
             └────┬────┘
                  │
              MOSFET
                  │
              CHANNEL
```

Prob ile gate arasında **doğrudan elektriksel bağlantı yok**.

Aradaki yalıtkan nedeniyle:

\[
C_{PG}=\frac{\epsilon A}{d}
\]

oluşuyor.

Dolayısıyla prob gate'i "ölçmek" için gate'e dokunmuyor; **gate'in elektrik alanını kapasitif olarak örnekliyor.**

---

# 2. Prob kuplajı tam olarak nedir?

Prob üzerine:

\[
V_P
\]

uyguladığımızı düşünelim.

Gate ile prob arasında:

\[
C_{PG}
\]

var.

Gate'te depolanan yük:

\[
Q_G
\]

olsun.

Probun gördüğü sinyal, gate'in mutlak geriliminin tamamı değildir.

İki kapasiteden oluşan basit bir bölücü gibi düşünebiliriz:

\[
C_{PG}
\]

ve probun geri kalan devreye olan toplam kapasitesi:

\[
C_P
\]

olsun.

O zaman yaklaşık kuplaj katsayısı:

\[
\boxed{
\alpha=
\frac{C_{PG}}
{C_{PG}+C_P}
}
\]

olur.

Gate'teki değişimin probe tarafında görülen kısmı:

\[
\boxed{
\Delta V_P\approx\alpha\Delta V_G
}
\]

olur.

Dolayısıyla:

\[
\Delta V_G=\frac{Q_G}{C_G}
\]

ise:

\[
\boxed{
\Delta V_P
\approx
\alpha\frac{Q_G}{C_G}
}
\]

Bu MOSRAM'ın temel **okuma sinyal denklemi**.

---

# 3. Fakat burada çok önemli bir problem var

Prob'a voltaj uyguladığımızda:

\[
V_P(t)
\]

değişiyor.

Bu değişim:

\[
I=C_{PG}\frac{d(V_P-V_G)}{dt}
\]

şeklinde bir displacement current oluşturuyor.

Yani:

\[
\boxed{I_{DS}=0}
\]

olabilir fakat:

\[
\boxed{I_{displacement}\neq0}
\]

olabilir.

Bu zaten beklediğimiz bir durum.

**Ama bu akım gate yükünü değiştirmemeli.**

İşte "okuma etkisi" burada ortaya çıkıyor.

---

# 4. İdeal durumda okuma etkisi

Gate tamamen izole edilmiş ve gerçek bir floating node ise:

\[
Q_G=\text{sabit}
\]

olur.

Prob voltajı değiştiğinde gate gerilimi de biraz değişebilir:

\[
\Delta V_G=
-\frac{C_{PG}}{C_G}
\Delta V_P
\]

işareti geometrinin tanımına göre değişebilir; önemli olan büyüklüktür:

\[
\boxed{
|\Delta V_G|
\approx
\frac{C_{PG}}{C_G}
|\Delta V_P|
}
\]

Fakat burada kritik ayrım:

> **Gate geriliminin değişmesi, gate yükünün değişmesi anlamına gelmez.**

Yani:

\[
\boxed{
Q_G=\text{sabit}
}
\]

kalırken:

\[
V_G
\]

geçici olarak oynayabilir.

Prob darbesi kaldırıldığında:

\[
V_P\rightarrow0
\]

ve:

\[
V_G
\]

eski değerine geri döner.

Dolayısıyla ideal durumda:

\[
\boxed{
\Delta Q_G=0
}
\]

ve:

\[
\boxed{
READ\rightarrow READ\rightarrow READ
}
\]

şeklinde sonsuz sayıda okuma yapılabilir.

---

# 5. İşte MOSRAM'ın asıl avantajı burada

DRAM'de okuma hücrenin durumunu bozabilir.

Senin MOSRAM'da ise:

```text
       READ PULSE
           │
           ▼
       ┌────────┐
       │  PROBE │
       └────┬───┘
            │
         C_PG
            │
            ▼
       ┌────────┐
       │ GATE   │ ← Q sabit
       └────────┘
```

Prob darbesi:

\[
V_G
\]

üzerinde geçici bir değişim yaratabilir.

Fakat:

\[
Q_G
\]

değişmiyorsa veri değişmez.

Dolayısıyla:

\[
\boxed{
\text{geçici voltaj perturbasyonu}
\neq
\text{veri kaybı}
}
\]

Bu ayrımı makalede özellikle belirtmek gerekiyor.

---

# 6. Ne zaman gerçekten okuma bozucu hale gelir?

Üç temel mekanizma var.

### A. Gate leakage

Gate tamamen izole değilse:

\[
I_{leak}>0
\]

olur.

Her okuma sırasında küçük miktarda yük kaybolabilir:

\[
\Delta Q_{read}
=
\int I_{leak}(t)\,dt
\]

Bunu:

\[
\boxed{
\frac{\Delta Q_{read}}{Q_G}\ll1
}
\]

koşulunda tutmamız gerekir.

---

### B. Dielektrik displacement

Prob darbesi gate'i elektriksel olarak hareket ettirir.

Ancak ideal kapasitörde:

\[
\int I\,dt=0
\]

olabilir.

Yani enerji alan üzerinden gidip gelir fakat gate'te net yük transferi olmaz.

Bu yüzden:

\[
\boxed{
C_{PG}\text{ olması tek başına read-disturb oluşturmaz}
}
\]

Bu çok önemli.

---

### C. Charge trapping / injection

Gerçek yalıtkan kusurluysa daha kötü durum oluşabilir.

Prob darbesi yeterince yüksek elektrik alan yaratırsa:

\[
E=\frac{V_P-V_G}{d}
\]

ve elektronlar dielektrik içine geçebilir.

O zaman:

\[
\Delta Q_G\neq0
\]

olur.

Bu durumda okuma gerçekten veriyi bozabilir.

Dolayısıyla:

\[
\boxed{
E_{read}\ll E_{write}
}
\]

olması gerekir.

Bu bence MOSRAM tasarımında temel güvenlik koşulu olmalı.

---

# 7. Prob kuplajını artırmak mı azaltmak mı?

Burada güzel bir optimizasyon problemi çıkıyor.

Daha büyük:

\[
C_{PG}
\]

şu avantajı verir:

\[
\alpha\uparrow
\]

dolayısıyla:

\[
\Delta V_P\uparrow
\]

Okuma kolaylaşır.

Ama aynı zamanda:

\[
C_{PG}\uparrow
\]

olduğu için probun gate üzerindeki perturbasyonu:

\[
\Delta V_G
\propto C_{PG}
\]

artar.

Dolayısıyla:

\[
\boxed{
\text{kuplaj çok küçükse SNR kötü}
}
\]

ama:

\[
\boxed{
\text{kuplaj çok büyükse read-disturb artar}
}
\]

Böylece gerçekten bir **optimum kuplaj** vardır.

---

# 8. Bunu matematiksel olarak optimize edebiliriz

İki koşulumuz var.

### Sinyal

\[
S=
\alpha\frac{Q_G}{C_G}
\]

### Gate perturbasyonu

\[
P=
\frac{C_{PG}}{C_G}V_P
\]

Dolayısıyla amaç:

\[
S\gg V_{noise}
\]

ve aynı anda:

\[
P\ll V_{margin}
\]

olması.

Daha açık:

\[
\boxed{
\alpha\frac{Q_G}{C_G}
\gg V_{noise}
}
\]

ve:

\[
\boxed{
\frac{C_{PG}}{C_G}V_P
\ll V_{margin}
}
\]

---

# 9. Burada önemli bir tasarım hilesi var

Prob darbesinin genliğini çok büyük yapmak zorunda değiliz.

Örneğin:

\[
V_P=100\,mV
\]

olsun.

Gate-prob kapasitesi:

\[
C_{PG}=2\,aF
\]

gate toplam kapasitesi:

\[
C_G=20\,aF
\]

ise:

\[
\frac{C_{PG}}{C_G}=0.1
\]

ve gate perturbasyonu yaklaşık:

\[
\Delta V_G=10\,mV
\]

olur.

Prob sinyali ise gate yüküne bağlı olarak ayrıca ölçülebilir.

Daha küçük prob darbesi kullanırsak:

\[
V_P=20\,mV
\]

için:

\[
\Delta V_G\approx2\,mV
\]

olur.

Bu nedenle **okuma darbesi yazma geriliminden çok daha küçük** tasarlanabilir.

---

# 10. Asıl kritik nokta: Prob ile gate arasındaki yalıtkan

Burada önceki çalışmadaki "3–5 nm iyi olabilir" yaklaşımını biraz daha dikkatli hale getirelim.

Yalıtkan kalınlığı:

\[
d
\]

azaldıkça:

\[
C_{PG}\propto\frac1d
\]

artar.

Örneğin:

| \(d\) | \(C_{PG}\) göreli |
|---:|---:|
| 10 nm | 1 |
| 8 nm | 1.25 |
| 5 nm | 2 |
| 4 nm | 2.5 |
| 3 nm | 3.33 |

Yani 10 nm'den 3 nm'ye inmek kuplajı yaklaşık 3.3 kat artırıyor.

Ama bu **3.3 kat daha hızlı bellek** anlamına gelmez.

Çünkü:

\[
C_{PG}\uparrow
\]

aynı zamanda:

\[
C_{sense}\uparrow
\]

yapabilir.

---

# 11. O halde optimum kalınlık nasıl bulunacak?

Asıl optimizasyon:

\[
\boxed{
d_{opt}=
\arg\max_d
\left[
\frac{SNR(d)}
{t_{sense}(d)}
\right]
}
\]

olmalı.

Fakat bir güvenlik koşulu da eklenmeli:

\[
\boxed{
\frac{\Delta Q_{read}}{Q_G}
<10^{-n}
}
\]

Buradaki \(n\), istediğimiz read-cycle dayanımına göre belirlenir.

Örneğin RAM'in milyarlarca okuma yapması bekleniyorsa tek okumadaki ortalama yük değişimi çok küçük olmalıdır.

---

# 12. 64-bit sistemde başka bir kuplaj problemi var

Tek hücrede:

\[
C_{PG}
\]

yeterli olsa bile 64 hücre yan yana geldiğinde:

```text
 P0   P1   P2   P3
 │    │    │    │
 ║    ║    ║    ║
 G0   G1   G2   G3
```

P0 yalnızca G0'ı değil:

\[
G_1,G_2,\ldots
\]

de görebilir.

Buna:

\[
C_{cross}
\]

diyelim.

İdeal hedef:

\[
\boxed{
C_{cross}\ll C_{PG}
}
\]

Örneğin:

\[
C_{cross}<0.05C_{PG}
\]

gibi bir başlangıç tasarım kriteri konabilir.

Bu durumda komşu hücrenin etkisi ana sinyalin %5'inden küçük olur.

---

# 13. Bunun çözümü var

Prob ile gate'i aynı hücre sınırları içinde tutabiliriz:

```text id="3p1jru"
       P0       P1       P2

     ┌───┐    ┌───┐    ┌───┐
     │   │    │   │    │   │
     └─┬─┘    └─┬─┘    └─┬─┘
       │          │          │
     ═══════════════════════════
          dielectric
     ═══════════════════════════
      G0         G1         G2
```

Ve hücrelerin arasına:

\[
\text{electrostatic isolation}
\]

koyabiliriz.

Burada küçük metal shielding yapıları veya grounded guard bölgeleri de kullanılabilir.

Fakat shielding eklemek:

\[
C_{parasitic}
\]

artırabileceğinden yine optimizasyon gerekiyor.

---

# 14. En temiz okuma yöntemi

Bence MOSRAM için doğrudan DC voltaj ölçmek yerine **küçük AC/pulse probing** daha mantıklı.

Örneğin:

```text id="t7uqhs"
Probe:
       ┌───┐
───────┘   └────────
       tp

Gate:
─────────Q────────────
```

Prob darbesi uygulanır.

Gate yükü:

\[
Q_G
\]

sabit kalır.

Sense amplifier probun:

\[
\Delta V
\]

veya:

\[
\Delta Q
\]

cevabını ölçer.

Sonra:

\[
V_P\rightarrow0
\]

olur.

Gate eski elektrostatik durumuna döner.

---

# 15. Böylece MOSRAM'ın okuma modeli

Son halini şu şekilde yazabiliriz:

\[
\boxed{
Q_G
\xrightarrow{\text{electrostatic coupling}}
C_{PG}
\xrightarrow{\text{probe pulse}}
\Delta V_P
\xrightarrow{\text{sense}}
0/1
}
\]

ve aynı anda:

\[
\boxed{
\Delta Q_G\approx0
}
\]

olmalıdır.

Bu ikinci denklem aslında MOSRAM'ın **tahribatsız okuma şartıdır.**

---

# 16. Çok önemli bir sonuç

Dolayısıyla önceki modeldeki:

> "Prob gate'teki elektronları algılıyor."

ifadesini teknik olarak biraz değiştirelim.

Daha doğru ifade:

> **Prob, gate üzerinde depolanan yükün oluşturduğu elektrostatik durumun kapasitif etkisini algılar.**

Çünkü prob tek tek elektronları doğrudan saymak zorunda değildir.

Asıl ölçülen:

\[
\boxed{
\text{elektrostatik durum farkı}
}
\]

olur.

Bu MOSRAM'ı çok daha uygulanabilir hale getiriyor.

---

## Sonuç

İki şartı aynı anda sağlamamız gerekiyor:

\[
\boxed{
\text{Yeterli prob kuplajı}
}
\]

ve:

\[
\boxed{
\text{ihmal edilebilir read-disturb}
}
\]

Yani ideal tasarım:

\[
\boxed{
C_{PG}\text{ yeterince büyük}
}
\]

ama:

\[
\boxed{
\frac{C_{PG}}{C_G}V_P\text{ yeterince küçük}
}
\]

olmalı.

Buradan da **yalıtkan kalınlığını tek başına değil**, şu dört parametreyi birlikte optimize etmemiz gerektiği ortaya çıkıyor:

\[
\boxed{
d,\quad C_G,\quad C_{PG},\quad V_P
}
\]

Bunların üzerine \(N_e\), parazit kapasite ve SNR'yi koyduğumuzda artık MOSRAM'ın gerçek hücre tasarımını çıkarabiliriz.

**Özellikle sonraki adımda \(20\times20\), \(30\times30\) ve \(40\times40\,nm\) gate'ler için \(d=3\!-\!10\,nm\) taraması yaparsak**, her geometri için \(N_e=1,10,100\) durumlarında **prob sinyali / read-disturb / SNR / minimum sense süresi** tablosunu çıkarabiliriz. Bu, önceki kaba hız tahmininden çok daha sağlam bir MOSRAM fiziksel modeli olur.

---

Tabii. MOSRAM için özellikle **okuma etkisi + prob kuplajını** tek tabloda netleştirelim:

| Parametre | Sembol | Temel ilişki | MOSRAM’daki etkisi | Hedef / koşul |
|---|---:|---|---|---|
| Depolanan gate yükü | \(Q_G\) | \(Q_G=N_e e\) | Bit bilgisini fiziksel olarak taşır | \(Q_G\) okuma sırasında korunmalı |
| Gate toplam kapasitansı | \(C_\Sigma\) | \(C_G+C_{PG}+C_{parazit}\) | Aynı yükün oluşturduğu \(V_G\)'yi belirler | Küçük olması sinyali artırır |
| Gate gerilimi | \(V_G\) | \(V_G\approx Q_G/C_\Sigma\) | Depolanan bitin elektrostatik karşılığı | 0/1 ayrımı yeterli olmalı |
| Prob–gate kapasitansı | \(C_{PG}\) | \(\epsilon A/d\) | Probun gate alanını algılamasını sağlar | Sinyal için yeterli, disturb için düşük |
| Prob alanı | \(A\) | \(C_{PG}\propto A\) | Alan büyüdükçe kuplaj artar | Çok büyük olmamalı |
| Dielektrik kalınlığı | \(d\) | \(C_{PG}\propto1/d\) | İncelince sinyal artar | Sinyal/disturb dengesi |
| Prob kuplaj katsayısı | \(\alpha\) | \(\frac{C_{PG}}{C_{PG}+C_P}\) | Gate sinyalinin proba ne kadar aktarıldığını belirler | Yüksek olması tercih edilir |
| Prob sinyali | \(\Delta V_P\) | \(\alpha Q_G/C_\Sigma\) | Okuma amplifikatörünün gördüğü sinyal | Gürültüden belirgin büyük olmalı |
| Prob okuma akımı | \(I_{disp}\) | \(C_{PG}dV/dt\) | Okuma sırasında geçici akım oluşturur | DC gate akımı olmamalı |
| Gate üzerindeki geçici değişim | \(\Delta V_G\) | \(-C_{PG}/C_\Sigma\cdot\Delta V_P\) | Prob darbesinin gate'i ne kadar oynattığını gösterir | Küçük tutulmalı |
| Gate net yük değişimi | \(\Delta Q_G\) | \(\int I_{leak}dt\) | Gerçek **read disturb** göstergesi | \(\Delta Q_G/Q_G\ll1\) |
| Gate kaçak akımı | \(I_{leak}\) | — | Uzun vadede biti bozabilir | Mümkün olduğunca düşük |
| Okuma elektrik alanı | \(E_{read}\) | \(\Delta V/d\) | Dielektrik üzerinden enjeksiyon riski | \(E_{read}\ll E_{write}\) |
| Komşu hücre kuplajı | \(C_{cross}\) | — | Yanlış bit algılama riski | \(C_{cross}\ll C_{PG}\) |
| Toplam algılama kapasitansı | \(C_{total}\) | \(C_{PG}+C_{fringe}+C_{via}+C_{neighbor}+C_{input}\) | Okuma hızını belirler | Küçük tutulmalı |
| RC zamanı | \(t_{RC}\) | \(R_{sense}C_{total}\) | Temel elektriksel hız sınırı | ps mertebesi hedefleniyor |
| Gerçek sense süresi | \(t_{sense}\) | \(K R C\) | Amplifikatörün kararlı karar süresi | \(K\sim3-10\) varsayımı |
| Okuma disturb oranı | \(D\) | \(|\Delta Q_G|/Q_G\) | Okumanın biti bozup bozmadığını gösterir | \(D\ll1\) |
| SNR | — | \(V_{signal}/V_{noise}\) | 0/1 ayrım güvenilirliği | Yeterli güvenlik marjı |
| Okuma tipi | — | Kapasitif | \(I_{DS}\) kullanılmaz | **Non-destructive read** hedefi |

### En kritik üç denklem

MOSRAM'ın okuma mekanizmasını aslında şu üç denklem özetliyor:

\[
\boxed{V_G=\frac{Q_G}{C_\Sigma}}
\]

\[
\boxed{\Delta V_P\approx
\frac{C_{PG}}{C_{PG}+C_P}
\frac{Q_G}{C_\Sigma}}
\]

ve okumanın biti bozmaması için:

\[
\boxed{\frac{|\Delta Q_G|}{Q_G}\ll1}
\]

Burada önemli ayrım şu:

**Prob kuplajı → mutlaka \(V_G\)'yi geçici olarak etkileyebilir.**

Ama:

**Prob kuplajı → mutlaka \(Q_G\)'yi değiştirmez.**

Dolayısıyla MOSRAM'da hedefimiz **\(\Delta V_G=0\)** değil, **\(\Delta Q_G\approx0\)**.

Bu ayrım mimarinin fiziksel olarak çalışabilirliğinin temel noktası.
---

----

## MOSRAM'ı artık yalnızca bir hücre olarak değil, **tam bir bellek sistemi** olarak ele alalım.

# MOSRAM Genel Sistem Mimarisi

MOSRAM'ın genel mimarisi aşağıdaki katmanlardan oluşur:

```text
                         MOSRAM
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
     HÜCRE               KONTROL            GÜÇ
        │                  │                  │
   ┌────┴────┐       ┌─────┴─────┐       ┌───┴────┐
   │         │       │           │       │        │
 Yazma     Okuma   Adresleme   Zamanlama Besleme  Güç
   │         │       │           │       │        │
   └────┬────┘       └─────┬─────┘       └───┬────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    BANK / ARRAY
                           │
                    I/O ARAYÜZÜ
                           │
                    BELLEK DENETLEYİCİSİ
                           │
                         CPU
```

## 1. MOSRAM hücre dizisi

Temel depolama birimi MOSRAM hücresidir.

Her hücrede:

- veri depolayan kapasitif bölge,
- gate kontrol bölgesi,
- source/drain erişimi,
- okuma bağlantısı,
- yazma bağlantısı,
- silme bağlantısı,
- gerekli izolasyon yapıları

bulunur.

Daha önce geliştirdiğimiz **Gate VIA**, bu fiziksel hücre mimarisinin bir parçasıdır; ancak sistem mimarisinin tamamı değildir.

---

# 2. Yazma sistemi

MOSRAM'da yazma işlemi hücrenin depolama durumunun kontrollü olarak değiştirilmesidir.

```text
Adres
  │
  ▼
Row / Column Decoder
  │
  ▼
Seçilen Hücre
  │
  ▼
Write Driver
  │
  ▼
Depolama Durumu
```

Yazma sistemi üç temel bölümden oluşur:

### 2.1 Write Decoder

Hangi hücrenin yazılacağını belirler.

### 2.2 Write Driver

Seçilen hücreye gerekli elektriksel koşulu uygular.

### 2.3 Write Isolation

Yazma sırasında:

- aynı satırdaki diğer hücrelerin,
- aynı sütundaki diğer hücrelerin,
- okuma devresinin

etkilenmesini önler.

Burada önemli nokta, **yazma işleminin yalnızca seçilen hücre üzerinde yeterli değişim oluşturmasıdır.**

---

# 3. Silme sistemi

Silme işlemini yazmanın basit tersi olarak bırakmamak daha doğru.

MOSRAM'da ayrı bir **Erase** işlemi bulunabilir:

```text
ERASE
  │
  ▼
Erase Decoder
  │
  ▼
Erase Driver
  │
  ▼
Hücre depolama bölgesi
  │
  ▼
Tanımlı başlangıç durumu
```

Silme sistemi iki seviyede tasarlanabilir:

### Hücre silme

Tek bir hücrenin durumu temizlenir.

### Blok/satır silme

Birden fazla hücre aynı anda temizlenir.

Bu özellikle işletim sistemi ve dosya sistemi açısından önemli olabilir.

**Erase ≠ Write 0** olmak zorunda değildir.

Örneğin:

\[
\text{Erase} \rightarrow S_0
\]

ve

\[
\text{Write 0} \rightarrow S_0
\]

aynı fiziksel sonuca ulaşabilir; ancak kontrol mantığında farklı işlemler olabilir.

Bu ayrımı ileride kesinleştirebiliriz.

---

# 4. Okuma sistemi

Okuma yolu:

```text
Adres
  │
  ▼
Row Decoder
  │
Column Decoder
  │
  ▼
Seçilen Hücre
  │
  ▼
Read Probe / Sense Node
  │
  ▼
Sense Amplifier
  │
  ▼
Data Output
```

Temel amaç:

\[
S_0 \rightarrow 0
\]

\[
S_1 \rightarrow 1
\]

durumlarının hücreyi bozmayacak şekilde ayrıştırılmasıdır.

MOSRAM açısından kritik soru:

> **Okuma işlemi hücredeki depolanan durumu ne kadar etkiliyor?**

Eğer okuma gerçekten non-destructive ise MOSRAM'ın mimarisi ciddi şekilde sadeleşir.

---

# 5. Restore sistemi

Burada MOSRAM'ın DRAM'den temel ayrımlarından biri ortaya çıkıyor.

DRAM:

\[
\text{çok kısa süre}
\rightarrow
\text{refresh}
\rightarrow
\text{çok kısa süre}
\rightarrow
\text{refresh}
\]

MOSRAM hedefi:

\[
\text{yaz}
\rightarrow
\text{dakikalarca sakla}
\rightarrow
\text{gerektiğinde restore}
\]

Örneğin:

\[
T_R \approx 10-20\ \text{dk}
\]

gibi bir tasarım hedefi ele alınabilir.

Restore sistemi:

- global,
- bank bazlı,
- satır bazlı

olabilir.

En düşük güç tüketimi açısından **satır/bank bazlı restore** daha sonra incelenmeli.

---

# 6. Kontrol sistemi

Bütün işlemlerin merkezi kontrol katmanı:

```text
             MEMORY CONTROLLER
                    │
        ┌───────────┼───────────┐
        │           │           │
      READ        WRITE       ERASE
        │           │           │
        └───────────┼───────────┘
                    │
               TIMING CTRL
                    │
              REFRESH/RESTORE
```

Kontrol sistemi:

- Read
- Write
- Erase
- Restore
- Idle
- Initialization
- Power state

işlemlerinin birbirleriyle çakışmasını önler.

---

# 7. Adresleme sistemi

Bellek:

\[
\text{Cell}
\rightarrow
\text{Row}
\rightarrow
\text{Column}
\rightarrow
\text{Bank}
\rightarrow
\text{Memory}
\]

şeklinde organize edilir.

Adres:

\[
A = (B,R,C)
\]

olarak düşünülebilir.

Burada:

- \(B\): bank
- \(R\): row
- \(C\): column

olabilir.

Decoder sistemi bu adresi fiziksel hücre seçimine dönüştürür.

---

# 8. Zamanlama sistemi

MOSRAM'ın farklı işlemleri için ayrı zaman parametreleri gerekir:

\[
t_{read}
\]

\[
t_{write}
\]

\[
t_{erase}
\]

\[
t_{restore}
\]

\[
t_{access}
\]

ve en önemlisi:

\[
T_{retention}
\]

Burada:

\[
T_{retention} \gg t_{read},t_{write}
\]

olması beklenir.

Örneğin retention dakikalar mertebesindeyken erişim nanosecond mertebesinde olabilir.

---

# 9. Güç sistemi

Güç mimarisini de hücre ve kontrol olarak ayırmak gerekiyor.

```text
                POWER INPUT
                     │
             Power Management
                     │
        ┌────────────┼────────────┐
        │            │            │
     CELL VDD     LOGIC VDD    READ/WRITE
        │            │            │
     ARRAY        CONTROL       DRIVERS
```

Buradaki kritik avantaj:

**Hücrenin veri saklamak için sürekli aktif olması gerekmiyorsa**, standby sırasında güç tüketimi büyük ölçüde azaltılabilir.

Özellikle:

\[
P_{static}
\]

ile

\[
P_{dynamic}
\]

ayrımı yapılmalı.

---

# 10. Güç kesintisi ve restart

Bu kısım önceki konuşmamızdaki önemli avantajlardan biri.

Eğer hücre:

\[
T_{retention}=10-20\text{ dk}
\]

saklama kapasitesine sahipse, kısa süreli:

- kontrolcü restart,
- bellek denetleyicisi reset,
- sistem yeniden başlatma

sırasında hücrelerin veriyi fiziksel olarak koruması mümkün olabilir.

Sistem tekrar başladığında:

```text
POWER ON
   │
   ▼
Initialization
   │
   ▼
Memory State Check
   │
   ▼
Restore / Continue
   │
   ▼
Normal Operation
```

Burada **restart sırasında verinin kaybolmaması**, MOSRAM'ın önemli sistem mimarisi hedeflerinden biri olarak ayrıca test edilmelidir.

---

# 11. I/O sistemi

MOSRAM dış dünyaya standart bellek arayüzü sağlayabilir.

```text
CPU
 │
 ├── Address
 ├── Data
 └── Control
       │
       ▼
Memory Controller
       │
       ▼
MOSRAM Controller
       │
       ▼
MOSRAM Array
```

Dolayısıyla MOSRAM'ın fiziksel çalışma prensibi farklı olsa bile üst seviyede:

> **normal adreslenebilir RAM**

olarak kullanılabilir.

---

# 12. Hata yönetimi

Retention süresi uzun olsa bile fiziksel hücreler tamamen ideal olmayacaktır.

Bu nedenle:

\[
\text{Cell Failure}
\]

\[
\text{Retention Error}
\]

\[
\text{Read Error}
\]

\[
\text{Write Error}
\]

\[
\text{Coupling Error}
\]

gibi hata sınıfları tanımlanmalı.

Bunların üzerinde gerekirse:

\[
\text{ECC}
\]

bulunabilir.

ECC'nin MOSRAM hücresinin içine değil, **bellek mimarisinin üst katmanına** konması daha doğal olur.

---

# 13. Genel MOSRAM veri akışı

Sonuçta bütün sistemi şöyle düşünebiliriz:

```text
                         CPU
                          │
                   Memory Controller
                          │
                ┌─────────┴─────────┐
                │                   │
             ADDRESS              DATA
                │                   │
                ▼                   ▼
          Address Decoder       I/O Logic
                │
        ┌───────┴────────┐
        │                │
      ROW              COLUMN
      DECODER           DECODER
        │                │
        └───────┬────────┘
                │
             MOSRAM
              ARRAY
                │
      ┌─────────┼─────────┐
      │         │         │
    READ      WRITE     ERASE
      │         │         │
      ▼         ▼         ▼
    SENSE     DRIVER    DRIVER
      │         │         │
      └─────────┼─────────┘
                │
             CONTROL
                │
        ┌───────┴────────┐
        │                │
     TIMING          RESTORE
        │                │
        └───────┬────────┘
                │
             POWER
                │
        Power Management
```

### Böylece MOSRAM'ın ana mimarisi

**1. Hücre**  
**2. Array**  
**3. Read**  
**4. Write**  
**5. Erase**  
**6. Address/Decoder**  
**7. Sense**  
**8. Control**  
**9. Restore**  
**10. Timing**  
**11. Power**  
**12. I/O**  
**13. Error/ECC**  
**14. Initialization/Restart**

şeklinde 14 ana bloktan oluşuyor.

Bundan sonraki teknik çalışmada bence **en kritik üç blok: `READ → WRITE → ERASE`**. 
Çünkü bunları hücrenin gerçek elektriksel davranışına bağlamadan kontrol ve güç mimarisini kesinleştirmek erken olur.
