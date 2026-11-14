# NEXSUS CPU — CodeFlow ve Çalışma Alanları Adlandırma Standardı (Karar 001)

Durum: kanonik terimler; eski kimlikler kaynak/tarihsel bağlamlarda uyumludur.

## Adlandırma kuralı
**Tek örnek varsa sonuna sayı eklenmez.** Sayısal ek yalnızca bağımsız adreslenebilir birden fazla örnek olduğunda kullanılır. Örnek: tek `Execution Buffer`; sekiz `Code Slot CS0–CS7`; dört `Context Pool CP0–CP3`.

## Kod yolu

| Eski kimlik | Kanonik ad | Simge | Görev |
|---|---|---|---|
| PX Manager | CodeFlow Manager (Kod Akış Yöneticisi) | CFM | OS görev/sayfa koordinasyonu ve güvenli sayfa yaşam döngüsü |
| PX P0–P7 | Code Slots (Kod Yuvaları) | CS0–CS7 | Eşit, dinamik tahsisli sekiz adet 2 KiB yürütülebilir sayfa yuvası |
| L0I | Code Cache (Kod Önbelleği) | C0 | 64 KiB görev bazlı App RAM hazırlama/önbellekleme |
| SPM0 | Execution Buffer (Yürütme Tamponu) | EB | CPU'nun kod çalışma alanı; 2 × 2 KiB ping-pong bankası |
| PX → SPM0 | Code Stream Transfer (Kod Akışı Aktarımı) | CST | Pasif yürütme bankasına aktarım |
| PX_NEXT | Code-Flow Continue (Kod Akışı Devamı) | CF_NEXT | Yalnızca yönetici metaverisi |
| PX_END | Code-Flow End (Kod Akışı Sonu) | CF_END | Yalnızca yönetici metaverisi |

## Eski SPM çalışma alanları — ayrı amaçlar, ayrı isimler

| Eski adres/ad | Kanonik ad | Simge | Kapasite | Amaç |
|---|---|---|---:|---|
| SPM1 | OS Workspace (OS Çalışma Alanı) | OW | 8 KiB | OS/kernel çalışma verisi ve kontrolü |
| SPM2 | Task Workspace (Görev Çalışma Alanı) | TW | 8 KiB | Aktif kullanıcı/görev yerel verisi |
| SPM3–SPM6 | Context Pool (Bağlam Havuzu) | CP0–CP3 | 4 × 8 KiB | Korunan görev context görüntüleri; görev kimliği değil havuz girdileri |
| SPM7 | Exception Workspace (İstisna Çalışma Alanı) | XW | 8 KiB | Exception/interrupt giriş scratch alanı ve handler çalışma alanı |

Bunlar tek bir genel bellek sınıfı değildir: sahiplik, yetki, yaşam süresi ve save/restore kuralları farklıdır. Eski SPMx adları mevcut belgeler, kaynak ve geçmiş simülasyon kayıtları için uyumluluk etiketi olarak kalır; yeni mimari metinlerde kanonik ad kullanılmalıdır.

## Kanonik kod yolu

```
App RAM -> Code Cache C0 (eski L0I, 64 KiB)
        -> Code Slots CS0–CS7 (eski PX, 8 × 2 KiB)
        -> Execution Buffer EB (eski SPM0, 2 × 2 KiB bank)
```

App RAM temel tasarımı tek 64-bit okuma hattıdır. C0 görev/sayfa bazlı, ardışık olmayan kaynak adreslerinden doldurulabilir. App RAM→C0, C0→CS ve CS→EB bağımsız kuyruklardır; geçerlilik, sahiplik ve backpressure koşullarıyla örtüşebilir.

## Uyumluluk ve kullanım
- Eski PX/P0–P7/L0I/SPM0–SPM7 kimlikleri silinmez veya sessizce başka anlama çevrilmez.
- Yeni metinde önce kanonik ad, ilk kullanımda eski kimlik parantez içinde yazılır.
- Tek bir birime `0` eklenmez; indeks yalnızca çoğul örneklerde kullanılır.
- CS0 varsayılan aktif yuva değildir; tüm Code Slot'lar eşittir.
- C0 hazırlama/önbellek alanıdır, doğrudan yürütülmez. EB CPU kod tamponudur; register/context görüntüsü tutmaz.
- CP0–CP3 havuz konumlarıdır; görev kimliği context'in hangi havuzda bulunduğundan bağımsızdır.

## Adlandırma gerekçesi
CodeFlow sayfa yaşam döngüsünü; Code Slot fiziksel yerleşimi; Code Cache hazırlama/yeniden kullanımı; Execution Buffer son kod çalışma alanını anlatır. OS Workspace, Task Workspace, Context Pool ve Exception Workspace eski SPM bölgelerini görevlerine göre açıkça ayırır.
