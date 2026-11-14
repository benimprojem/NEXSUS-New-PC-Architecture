# NEXSUS CPU Kod Yolu Terimleri — Adlandırma Kararı 001

Durum: önerilen kanonik terimler (uygulama kimlikleri geriye dönük uyumlu kalır)

## Kanonik adlar

| Eski ad | Mimari ad | Kısa simge | Sorumluluk |
|---|---|---|---|
| PX Manager | CodeFlow Manager (Kod Akış Yöneticisi) | CFM | OS görev/sayfa koordinasyonu ve güvenli sayfa yaşam döngüsü |
| PX P0–P7 | Code Slots (Kod Yuvaları) | CS0–CS7 | Eşit, dinamik tahsisli sekiz adet 2 KiB yürütülebilir sayfa yuvası |
| L0I | Code Cache (Kod Önbelleği) | C0 | 64 KiB görev bazlı App RAM hazırlama/önbellekleme alanı |
| SPM0 | Execution Buffer (Yürütme Tamponu) | EB0 | CPU kod çalışma alanı; iki adet 2 KiB ping-pong bankası |
| PX → SPM0 | Code Stream (Kod Akışı) | CST | Sayfanın pasif yürütme bankasına aktarılması |
| PX_NEXT | Code-Flow Continue (Kod Akışı Devamı) | CF_NEXT | Yönetici tarafından yorumlanan devam metaverisi |
| PX_END | Code-Flow End (Kod Akışı Sonu) | CF_END | Yönetici tarafından yorumlanan kod akışı sonu metaverisi |

## Geriye dönük uyumluluk

PX, P0–P7, L0I, SPM0, PX_NEXT ve PX_END mevcut kaynak kodunda, simülasyon çıktılarında ve tarihsel belgelerde geçerliliğini korur. Yukarıdaki adlar açıklayıcı eş adlardır; kırıcı bir yeniden adlandırma değildir. Yeni metinlerde ilk kullanımda kanonik ad ve eski simge birlikte yazılır: **Code Cache (C0; eski L0I)**.

CS0 varsayılan aktif yuva değildir. Tüm Code Slot'lar eşittir; komut getirimi herhangi bir eşlenmiş yuvadan yapılabilir. Code Cache (C0) hazırlama alanıdır, doğrudan yürütülemez. Execution Buffer (EB0) aktif kod çalışma alanıdır; register görüntülerini tutmaz.

## Kod yolu

```text
App RAM -> Code Cache C0 (L0I, 64 KiB)
        -> Code Slots CS0–CS7 (PX, 8 x 2 KiB)
        -> Execution Buffer EB0 (SPM0, 2 x 2 KiB)
```

App RAM temel tasarımı tek 64-bit okuma hattıdır. Code Cache görev/sayfa bazlı ve ardışık olmayan kaynak adreslerinden doldurulabilir. Üç aktarım kuyruğı bağımsızdır; veri geçerliliği, sahiplik ve geri basınç koşulları sağlandığında örtüşebilir.

## Adlandırma gerekçesi

- **CodeFlow**, opak PX adından farklı olarak görev bazlı kod sayfası yaşam döngüsünü anlatır.
- **Code Slot**, görev kimliği veya öncelik ima etmeden fiziksel sayfa yuvasını tanımlar.
- **Code Cache**, artımlı doldurma ve yeniden kullanım amacını anlatır.
- **Execution Buffer**, CPU'nun son kod çalışma alanını register/context belleğinden ayırır.
- **Code Stream**, metaveriyi komut baytları gibi göstermeden aktarım/devam kavramını adlandırır.
