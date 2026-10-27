---
name: adr
description: Yeni bir Mimari Karar Kaydı (ADR) oluşturur. Teknoloji seçimi, veri modeli, entegrasyon yaklaşımı gibi geri dönmesi pahalı kararlar alındığında kullan.
argument-hint: <karar başlığı>
---
# ADR oluştur: $ARGUMENTS

1. `docs/adr/` içindeki en büyük ADR-NNN numarasını bul, bir artır (3 hane).
   Numaralar asla değişmez.
2. `docs/adr/ADR-NNN-<kebab-baslik>.md` oluştur. **Türkçe**, kısa (hedef
   30-50 satır), hikâye değil karar anlatır. Şablon:

   ```
   # ADR-NNN: <Başlık>

   **Durum:** Kabul edildi · YYYY-AA-GG

   ## Bağlam
   2-4 cümle: hangi sorun, hangi kısıt.

   ## Karar
   Maddeler halinde; dosya/sembol adlarıyla.

   ## Alternatifler
   - **<seçenek>** — neden seçilmedi.

   ## Sonuçlar
   Kazandıklarımız, bedeli, açık kalan işler.
   ```
3. Her iddiayı kodla doğrula — dosya, sembol veya ayar yoksa yazma.
   Bilmediğin alanı uydurma, kullanıcıya sor.
4. `docs/adr/README.md` tablosuna satır ekle.
5. Eski bir kararı değiştiriyorsa eskisinin **Durum** satırına
   "değiştirildi: ADR-NNN" ekle ve içeriğini güncel tut.
