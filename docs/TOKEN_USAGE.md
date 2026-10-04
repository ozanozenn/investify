# Token Kullanımı — Ölçüm ve Bulgular

Bu doküman, Claude Code oturumlarında token tüketiminin nasıl ölçüldüğünü ve
hangi davranışların maliyeti artırdığını kayıt altına alır. Amaç: "çok token
mi harcıyoruz?" sorusuna hissiyatla değil veriyle cevap verebilmek.

## Veri nereden geliyor

Her oturum transkripti `~/.claude/projects/<proje>/<session-id>.jsonl` dosyasında
tutulur. Her asistan mesajında `message.usage` alanı vardır:

| Alan | Anlamı | Maliyet |
|---|---|---|
| `input_tokens` | Önbelleğe alınmamış taze girdi | Tam fiyat |
| `cache_creation_input_tokens` | Bu turda önbelleğe **yazılan** girdi | Taze girdiden pahalı |
| `cache_read_input_tokens` | Önbellekten **okunan** girdi | Çok ucuz |
| `output_tokens` | Üretilen çıktı | En pahalı |

**Ölçüm kuralı:** Aynı mesaj birden fazla satırda tekrarlanır (akış parçaları).
Toplam almadan önce mesaj kimliğine (`message.id`) göre **tekilleştirmek
zorunlu**; tekilleştirilmemiş toplamlar ~2 kat şişirir.

## Bulgular (2026-10-05, tek uzun oturum: 977 benzersiz asistan mesajı)

**1. Bağlam büyüklüğü.** Oturum sonunda bağlam ~600k token. Her tur bu bağlamın
tamamını işler — bu, ucuz da olsa, sürekli bir tabandır.

**2. Asıl maliyet sıçramaları: uzun boşluklar.** Önbellek geçici (birkaç dakika)
olduğundan, boşluk sonrası ilk tur bağlamın tamamını **yeniden yazar** (pahalı).

| Önceki mesajdan boşluk | Büyük yeniden-yazım oranı |
|---|---|
| < 1 dk | %0 (868 mesaj) |
| 1–5 dk | %0 (79 mesaj) |
| 5–30 dk | %10 (20 mesaj) |
| > 30 dk | **%57** (14 mesaj) |

**3. Model değişimi de önbelleği geçersiz kılar.** Opus ↔ Sonnet geçişinde
bağlam sıfırdan yazılır (oturumda iki kez gözlendi).

**4. Tool çıktıları beklenenden küçük.** Metin tool çıktılarının toplamı ~233k
token (oturum boyunca). Görsel okumaları (16 adet) görsel başına piksel
üzerinden faturalanır — karakter sayısından hesaplanan değer gerçek maliyeti
göstermez, yanıltıcıdır.

## Pratik kurallar (bu veriden çıkan)

- **Uzun ara vermeden önce** oturum bağlamı büyükse: ya bilerek devam et
  (maliyeti kabul et), ya da `/handoff` + `/clear` ile küçük bir bağlamla
  yeniden başla. Devir notu ve `session-start` hook'u bu yüzden var: bağlam
  sıfırlansa bile iş kaybolmaz.
- **Oturum ortasında model değiştirme** — önbellek yeniden yazılır. Model
  değişimi gerekiyorsa devir notuyla yeni oturuma geç.
- **Bir oturumu tek konuya ayır.** Konu değiştiğinde yeni oturum, eski
  bağlamın her turda yeniden okunmasını önler.

## Nasıl yeniden ölçülür

1. Oturum JSONL'ini oku, `message.id`'ye göre tekilleştir.
2. Turlar arası `timestamp` farkını hesapla; büyük `cache_creation` (ör. >100k)
   olan turları boşluk süresiyle eşleştir.
3. `tool_use` ↔ `tool_result` eşleşmesiyle en büyük metin çıktılarını bul
   (görselleri ayrı tut).

Bu analizi tekrarlamak için bir script yazılmadı; gerekirse ihtiyaca göre
eklenir. Bu doküman ölçüm kararlarının kaydıdır.

## Sınırlar

- Kota (5 saatlik pencere) hesabının cache okumalarını nasıl ağırlıklandırdığı
  Anthropic'in kendi politikasına bağlı; buradaki sayılar ham token
  dökümüdür, kota yüzdesi değil.
- Tek oturumdan çıkarıldı. Birden fazla oturumda aynı örüntü doğrulanana
  kadar genelleme yapılmaz.
