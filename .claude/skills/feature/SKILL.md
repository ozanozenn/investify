---
name: feature
description: Bir özelliği keşif → plan → uygulama → test → inceleme → dokümantasyon → devir akışıyla, subagent'ları orkestre ederek geliştirir.
argument-hint: <özellik açıklaması>
disable-model-invocation: true
---
# Özellik: $ARGUMENTS

Bu akışı sırayla izle. Her aşama sonunda kullanıcıya 1-2 satır durum ver.

## 1. Keşif
Verify agent'ına devret: ilgili modüller, giriş noktaları, etkilenecek
semboller, mevcut benzer örüntüler. Ham çıktıyı değil, özeti kullan.

## 2. Plan
Değişecek dosyalar, adımlar, test stratejisi, riskler. 3+ dosya veya
veri modeli değişikliği varsa planı kullanıcıya sun ve ONAY BEKLE.

## 3. Uygulama
Küçük adımlar. Her mantıklı adımda derlenebilir/çalışır durumda tut.

## 4. Doğrulama
test-runner agent'ını çalıştır. Başarısızsa düzelt, tekrar çalıştır
(en fazla 3 tur; sonra kullanıcıya danış).

## 5. İnceleme
code-reviewer agent'ını çalıştır. "Kritik" maddeleri düzelt.

## 6. Dokümantasyon
docs-keeper agent'ını çalıştır. ADR önerisi gelirse `/adr` öner.

## 7. Devir
`/handoff` skill'ini çalıştır.
