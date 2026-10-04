---
name: handoff
description: Mevcut oturumun durumunu docs/handoff/CURRENT.md dosyasına yazar ki sonraki oturum (veya başka bir agent) kaldığı yerden devam edebilsin. Bir iş bloğu bittiğinde, oturum kapanırken veya bağlam dolmaya yaklaştığında kullan.
---
# Devir notu yaz

1. docs/handoff/CURRENT.md varsa ve içeriği farklı bir işe aitse önce
   `docs/handoff/archive/YYYY-MM-DD-<kisa-konu>.md` olarak arşivle.
2. CURRENT.md'yi aşağıdaki şablonla YENİDEN yaz (ekleme yapma, güncelle).
   Toplam 60 satırı geçme. Somut ol: dosya yolları, sembol adları, komutlar.

```markdown
# Devir Notu
_Güncelleme: <tarih> · Branch: <branch>_

## Hedef
<Şu an üzerinde çalışılan iş, 1-2 cümle>

## Tamamlanan
- 

## Devam eden / yarım kalan
- <ne, hangi dosyada, hangi durumda>

## Sıradaki adımlar
1. 

## Alınan kararlar
- <karar — neden> (kalıcıysa ADR'ye bağla)

## Açık sorular / riskler
- 

## Dikkat
<Tuzaklar, denenip başarısız olanlar, kırılgan yerler>
```

3. Kullanıcıya CURRENT.md'nin özetini 3 satırda göster.
