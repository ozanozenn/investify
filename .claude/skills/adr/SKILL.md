---
name: adr
description: Yeni bir Mimari Karar Kaydı (ADR) oluşturur. Teknoloji seçimi, veri modeli, entegrasyon yaklaşımı gibi geri dönmesi pahalı kararlar alındığında kullan.
argument-hint: <karar başlığı>
---
# ADR oluştur: $ARGUMENTS

1. docs/adr/ içindeki en büyük ADR-NNN numarasını bul, bir artır (3 haneli,
   ör. ADR-007). Mevcut kararları (ADR-001..NNN) bölmemek için her zaman
   docs/adr/ kullan — ayrı bir decisions/ dizini açma.
2. `docs/adr/ADR-NNN-<kebab-baslik>.md` oluştur. Başlık anahtarları
   (`## Status`, `## Context`, `## Decision`, `## Consequences`) HER ZAMAN
   İngilizce kalır — mevcut ADR'lerle (docs/adr/ADR-00X-*.md) aynı
   başlık/biçim düzenini koru. Gövde metni Türkçe veya İngilizce olabilir.
3. Bağlamı bu konuşmadan doldur; bilmediğin alanı uydurma, kullanıcıya sor.
4. Eski bir kararı geçersiz kılıyor veya genişletiyorsa eskisinin
   `## Status` satırına `Amended by: ADR-NNN` veya `Superseded by: ADR-NNN`
   ekle.
