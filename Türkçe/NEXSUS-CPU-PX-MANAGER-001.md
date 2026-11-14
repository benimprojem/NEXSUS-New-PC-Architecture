# NEXSUS CPU — CodeFlow Yöneticisi ve Kod Yuvası Havuzu (CFM-001)

## 1. Amaç

CodeFlow Manager (CFM; eski PX Manager), görevlerin yürütülebilir kod sayfalarını güvenli biçimde hazırlayan, eşleyen, değiştiren ve serbest bırakan yönetim katmanıdır. OS politika ve öncelikleri belirler; donanım sahiplik, izin, nesil ve aktarım güvenliğini uygular.

## 2. Kod Yuvaları

- CS0–CS7 (eski PX P0–P7), çekirdek başına sekiz eşit fiziksel yuvadır.
- Her yuva 2 KiB; toplam havuz 16 KiB/çekirdek.
- Yuvalar görev kimliği taşıyan sabit bölmeler değildir; dinamik ortak havuzdan tahsis edilir.
- CS0 varsayılan aktif yuva değildir. Komut getirimi herhangi bir eşlenmiş ve READY yuvadan yapılabilir.
- Kod sayfaları register görüntüsü veya görev verisi tutmaz.

## 3. Code Cache ve Execution Buffer

```text
App RAM -> Code Cache C0 (eski L0I, 64 KiB)
        -> Code Slots CS0–CS7 (eski PX, 8 x 2 KiB)
        -> Execution Buffer EB0 (eski SPM0, 2 x 2 KiB)
```

Code Cache (C0) App RAM'den görev/sayfa bazlı, parça parça beslenir. Kaynak adresler ardışık olmak zorunda değildir. Execution Buffer (EB0) iki adet 2 KiB ping-pong bankasıdır: CPU aktif bankayı tüketirken CFM pasif bankayı doldurabilir.

## 4. Sayfa yaşam döngüsü

```text
FREE -> ALLOCATED -> FILLING -> VALIDATED -> READY -> MAPPED
                                             |          |
                                             +-> ACTIVE <-+
                                                    |
                                              RETIRING -> FREE
```

- Kısmi veya eksik aktarım READY olamaz.
- READY yayımlaması atomik olmalıdır.
- Aktarım sürerken kaynak Code Cache girdisi silinemez.
- Aktif fetch veya in-flight referans varken yuva serbest bırakılamaz.
- Görev nesli (generation) kontrolü eski isteklerin geçerli sayfa yayımlamasını engeller.
- Paylaşılan kod yalnızca açık izinle başka göreve görünür.

## 5. Metaveri

PX_NEXT / PX_END (önerilen eş adları CF_NEXT / CF_END) yalnızca CFM tarafından yorumlanan metaveridir. Komut değildir; EB0'a kopyalanmaz ve CPU tarafından decode edilmez. Tam 2 KiB sayfalar normal akışta devam eder; metaveri eksik sayfa/akış sınırlarını belirtir.

## 6. Güvenlik ve geri basınç

CFM, sayfa sınırlarını, izinleri, görev neslini ve geçerli bayt miktarını denetler. Code Cache → Code Slots → Execution Buffer aktarım kuyrukları birbirinden bağımsızdır. Kuyruk doluluğu yalnızca ilgili aşamayı geri basınçla sınırlar; güvenli olduğunda aşamalar örtüşür.

## 7. İlgili belgeler

- [Adlandırma kararı](NEXSUS-CPU-CODEFLOW-NAMING-001.md)
- [OS/CFM/context arayüzü](NEXSUS-CPU-OS-PX-CONTEXT-INTERFACE-001.md)
- [Simülatör mimarisi](NEXSUS-CPU-SIMULATOR-ARCHITECTURE-001.md)
