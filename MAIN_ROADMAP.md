# BIST Investment Intelligence Platform

Sen kıdemli bir **Software Architect, Backend Engineer, Data Engineer, Financial Systems Engineer, Frontend Engineer, DevOps Engineer ve AI/LLM Engineer** gibi hareket edeceksin.

Görevin, yalnızca benim kişisel kullanımım için geliştirilecek olan, Türkiye sermaye piyasalarına ve özellikle **Borsa İstanbul şirketlerine** odaklanan kapsamlı bir **Investment Intelligence / Financial Research Platform** tasarlamak ve uçtan uca geliştirmektir.

Bu proje bir trading bot değildir.

Ana amaç:

> Kullanıcının bir BIST şirket kodu girdiğinde, o şirket hakkında mümkün olan en güncel ve güvenilir finansal, temel, makroekonomik, sektörel, haber, KAP, değerleme ve piyasa verilerini toplayarak; geçmişi, bugünü ve geleceğe yönelik kısa/orta/uzun vadeli görünümü anlamasını sağlayacak kapsamlı bir yatırım araştırma ekranı üretmek.

Sistem hiçbir zaman yalnızca:

> AL / SAT / TUT

şeklinde yüzeysel karar üretmemelidir.

Bunun yerine kullanıcıya yatırım kararı verebilmesi için gerekli olan **kanıta dayalı karar destek ortamını** sağlamalıdır.

---

# 1. ANA ÜRÜN FELSEFESİ

Bu sistemin merkezinde şu soru vardır:

> "Bu şirket bugün hangi finansal durumda, geçmiş yıllarda nasıl gelişti, mevcut değerlemesi ne söylüyor, şirketin yatırım tezi nedir ve önümüzdeki kısa, orta ve uzun vadede bu şirketi olumlu veya olumsuz etkileyebilecek faktörler nelerdir?"

Sistem şu zaman ufuklarını ayrı değerlendirmelidir:

### Kısa vade

0–6 ay

### Orta vade

6–24 ay

### Uzun vade

2–5+ yıl

Her ufuk aynı verilerle değerlendirilmemelidir.

Örneğin kısa vadede:

* son finansal sonuçlar
* son KAP açıklamaları
* beklentiler
* makro koşullar
* fiyatlama
* momentum
* yaklaşan katalizörler

önemliyken;

uzun vadede:

* gelir ve kâr büyümesinin sürdürülebilirliği
* ROE
* ROIC
* serbest nakit akışı
* borç yapısı
* sermaye tahsisi
* rekabet avantajı
* pazar büyüklüğü
* şirket stratejisi
* yönetim kalitesi
* CAPEX
* sektör dönüşümü

daha önemli olacaktır.

---

# 2. ÖNEMLİ MİMARİ PRENSİP

LLM finansal hesaplama motoru OLMAYACAKTIR.

LLM:

* veri uydurmayacak
* finansal oranları kendi başına hesaplamayacak
* fiyat uydurmayacak
* hedef fiyatı herhangi bir matematiksel dayanak olmadan üretmeyecek
* kaynak verilmemiş şirket olaylarını gerçekmiş gibi yorumlamayacak

Tüm:

* finansal oranlar
* büyüme hesaplamaları
* değerleme hesapları
* skorlamalar
* trend hesaplamaları
* istatistiksel analizler

deterministik backend servisleri tarafından hesaplanmalıdır.

LLM yalnızca:

> Structured Financial Context

üzerinden yorum üretmelidir.

Örneğin LLM'e şu tür bir yapı verilmelidir:

```json
{
  "ticker": "THYAO",
  "asOf": "2026-08-17",
  "financialQualityScore": 82,
  "growthScore": 78,
  "valuationScore": 74,
  "balanceSheetScore": 68,
  "revenueGrowthYoY": 21.4,
  "ebitdaGrowthYoY": 17.1,
  "roe": 31.7,
  "roic": 24.2,
  "netDebtToEbitda": 1.42,
  "fcfMargin": 8.2,
  "currentPE": 5.1,
  "historicalMedianPE": 6.4,
  "sectorMedianPE": 7.3
}
```

LLM bunun üzerinden finansal yorumu üretmelidir.

---

# 3. TEKNOLOJİ YIĞINI

Tercih edilen teknoloji yığını:

## Backend

Python 3.12+

FastAPI

Pydantic

SQLAlchemy 2.x

Alembic

httpx

Pandas

NumPy

SciPy

scikit-learn

gerekli finansal analiz kütüphaneleri

---

## Database

PostgreSQL

İhtiyaç halinde:

TimescaleDB

kullanılabilir.

JSON içerikler için:

PostgreSQL JSONB

kullan.

---

## Cache / Jobs

Redis

Background jobs için tercihen:

Celery

veya daha uygun modern bir alternatif.

Periodik işler için:

Celery Beat

veya scheduler abstraction kullan.

---

## Frontend

Next.js

React

TypeScript

Tailwind CSS

shadcn/ui

TanStack Query

TanStack Table

---

## Chart

TradingView Lightweight Charts

veya lisans şartlarını araştırarak uygun başka profesyonel bir chart çözümü.

---

## LLM

LLM provider abstraction oluştur.

İlk provider:

OpenAI

olsun.

Fakat business logic doğrudan OpenAI SDK'sına bağımlı olmamalı.

Örneğin:

```text
LLMProvider
    |
    +-- OpenAIProvider
    +-- FutureProvider
```

---

## Deployment

Docker

Docker Compose

Nginx veya Traefik

PostgreSQL

Redis

Backend

Worker

Frontend

tek compose üzerinden ayağa kaldırılabilsin.

---

# 4. MONOREPO YAPISI

Tercihen aşağıdaki gibi bir yapı oluştur:

```text
investment-intelligence/
│
├── apps/
│   ├── api/
│   ├── web/
│   └── worker/
│
├── packages/
│   ├── financial-engine/
│   ├── scoring-engine/
│   ├── valuation-engine/
│   ├── data-providers/
│   ├── llm/
│   └── shared/
│
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   └── monitoring/
│
├── docs/
│
├── scripts/
│
├── docker-compose.yml
└── README.md
```

Daha iyi bir yapı önerebiliyorsan gerekçesiyle değiştir.

---

# 5. DOMAIN MODEL

Domain'i düzgün şekilde modelle.

Minimum aşağıdaki kavramlar bulunmalı:

```text
Company
Ticker
Exchange
Sector
Industry

FinancialStatement
FinancialPeriod
IncomeStatement
BalanceSheet
CashFlowStatement

FinancialMetric

MarketPrice
MarketCandle
CorporateAction

KapDisclosure
NewsArticle

MacroIndicator
MacroObservation

SectorMetric
PeerCompany

ValuationSnapshot

InvestmentAnalysis
InvestmentThesis

Risk
Catalyst

ScoreSnapshot

AnalysisSnapshot

Watchlist
Alert

DataSource
DataFetchLog
```

İlişkileri dikkatlice tasarla.

---

# 6. VERİ KAYNAKLARI

Projeyi geliştirirken kullanılabilecek güncel kaynakları araştır.

Türkiye özelinde özellikle:

## Şirket bildirimleri

KAP

---

## Makro veriler

TCMB EVDS

TÜİK

---

## Piyasa verileri

Borsa İstanbul verileri

lisanslı veya güvenilir üçüncü taraf market-data provider'ları

---

## Finansal tablolar

KAP

gerekirse güvenilir finansal data provider

---

## Haberler

güvenilir ekonomi ve finans haber kaynakları

şirket yatırımcı ilişkileri sayfaları

RSS

haber API'leri

---

Kaynak seçmeden önce:

* kullanım şartlarını
* lisans durumunu
* API olup olmadığını
* scraping izinlerini
* rate limitlerini
* veri gecikmesini
* ücretlendirmeyi

araştır.

Scraping yapılacaksa:

* abstraction arkasına koy
* kolay değiştirilebilir olsun
* provider bağımlılığı business logic'e sızmasın.

---

# 7. DATA PROVIDER ABSTRACTION

Her veri kaynağı interface üzerinden çalışmalı.

Örneğin:

```python
class MarketDataProvider:
    async def get_quote(...)
    async def get_historical_prices(...)
```

```python
class FinancialDataProvider:
    async def get_financial_statements(...)
```

```python
class DisclosureProvider:
    async def get_disclosures(...)
```

```python
class MacroDataProvider:
    async def get_series(...)
```

```python
class NewsProvider:
    async def get_company_news(...)
```

Provider değiştirildiğinde business logic değişmemeli.

---

# 8. ŞİRKET PROFİLİ

Kullanıcı ticker girdiğinde sistem:

```text
THYAO
ASELS
FROTO
TUPRS
SISE
GARAN
AKBNK
EREGL
```

gibi kodları anlayabilmeli.

Company profile ekranında:

* ticker
* şirket adı
* sektör
* alt sektör
* piyasa değeri
* dolaşımdaki pay
* çalışan sayısı varsa
* kuruluş tarihi
* ana faaliyet
* şirket açıklaması
* web sitesi
* yatırımcı ilişkileri linki
* KAP şirket linki

göster.

---

# 9. FİNANSAL TABLO MOTORU

En az:

5 yıllık yıllık

ve

son 8–12 çeyreklik

finansal geçmiş tutulmalı.

Üç temel tablo:

### Income Statement

* Revenue
* Gross Profit
* EBITDA
* EBIT
* Operating Income
* Net Income
* Finance Expense
* Tax
* EPS

### Balance Sheet

* Cash
* Financial Investments
* Receivables
* Inventory
* Total Assets
* Short-Term Debt
* Long-Term Debt
* Total Debt
* Total Liabilities
* Equity

### Cash Flow

* Operating Cash Flow
* Investing Cash Flow
* CAPEX
* Financing Cash Flow
* Free Cash Flow

verilerini mümkün olduğunca normalize et.

---

# 10. FINANCIAL METRIC ENGINE

Aşağıdaki metrikleri hesaplayan deterministic engine geliştir.

## Growth

Revenue YoY

Revenue QoQ

Revenue CAGR 3Y

Revenue CAGR 5Y

EBITDA YoY

EBITDA CAGR

Net Income Growth

EPS Growth

---

## Profitability

Gross Margin

EBITDA Margin

EBIT Margin

Net Margin

ROE

ROA

ROIC

---

## Balance Sheet

Net Debt

Net Debt / EBITDA

Debt / Equity

Current Ratio

Quick Ratio

Cash Ratio

Interest Coverage

---

## Cash Flow

Operating Cash Flow Margin

FCF

FCF Margin

FCF Conversion

CAPEX / Revenue

---

## Efficiency

Asset Turnover

Inventory Turnover

Receivable Days

Payable Days

Cash Conversion Cycle

---

Metriklerin sektörlere göre farklı anlam taşıyabileceğini dikkate al.

Örneğin:

Bankalar

Holdingler

REIT/GYO

Sigorta

Sanayi

Havayolu

Enerji

aynı finansal modelle analiz edilmemelidir.

Architecture içinde:

```text
IndustryAnalysisStrategy
```

gibi bir yapı düşün.

---

# 11. SEKTÖREL ANALİZ

Sistem şirketi yalnız analiz etmemeli.

Peer group oluştur.

Örneğin:

```text
Company
vs
Sector Median
vs
Selected Peers
vs
Historical Company Median
```

karşılaştırmaları yapılmalı.

Göster:

* büyüme
* marj
* ROE
* ROIC
* borç
* F/K
* FD/FAVÖK
* PD/DD
* FCF yield

---

# 12. DEĞERLEME MOTORU

Birden fazla değerleme yöntemi desteklenmeli.

## Relative Valuation

P/E

P/B

EV/EBITDA

EV/EBIT

EV/Sales

FCF Yield

Dividend Yield

---

Karşılaştırmalar:

```text
Current
vs
Company historical median
vs
Sector median
vs
Peers
```

---

# 13. DCF

Discounted Cash Flow Engine oluştur.

Parametreler:

Revenue growth

EBIT margin

Tax

D&A

CAPEX

Working capital

WACC

Terminal growth

Net debt

Share count

Destekle:

```text
Bear
Base
Bull
```

senaryoları.

DCF parametrelerinin kullanıcı tarafından manuel değiştirilebilmesini sağla.

Sensitivity matrix:

```text
WACC
x
Terminal Growth
```

göster.

---

# 14. HEDEF DEĞER

Tek bir kesin hedef fiyat verme.

Bunun yerine:

```text
Bear Fair Value
Base Fair Value
Bull Fair Value
```

oluştur.

Örneğin:

```text
Bear: 260 TL
Base: 330 TL
Bull: 410 TL
```

Sonra mevcut fiyatla karşılaştır:

```text
Current Price: 285 TL

Bear Upside: -8.8%
Base Upside: +15.8%
Bull Upside: +43.9%
```

---

# 15. INVESTMENT THESIS ENGINE

Her şirket için structured yatırım tezi oluştur.

En az:

### Why Invest

Şirkete yatırım yapılmasını destekleyen faktörler.

### Why Not Invest

Yatırıma karşı faktörler.

### Catalysts

Yukarı yönlü potansiyeli tetikleyebilecek olaylar.

### Risks

Aşağı yönlü riskler.

### Thesis Breakers

Yatırım tezini geçersiz kılabilecek gelişmeler.

Örneğin:

```text
Thesis Breaker:

EBITDA margin < %12
Net Debt / EBITDA > 3
FCF negative for 4 consecutive quarters
Management guidance reduced materially
```

---

# 16. KISA / ORTA / UZUN VADE ANALİZİ

Her analiz:

```text
Short Term
Medium Term
Long Term
```

başlıklarına ayrılmalı.

Her biri için:

```text
Outlook
Confidence
Drivers
Risks
Catalysts
Key Metrics
```

bulunsun.

Örneğin:

```json
{
  "horizon": "MEDIUM_TERM",
  "outlook": "POSITIVE",
  "confidence": 0.76,
  "drivers": [],
  "risks": [],
  "catalysts": []
}
```

---

# 17. SCORING ENGINE

100 puan üzerinden çeşitli skorlar oluştur.

Örneğin:

```text
Financial Quality
Growth
Profitability
Balance Sheet
Cash Flow
Valuation
Momentum
Management / Capital Allocation
Macro Risk
Overall
```

Ancak skorların matematiksel olarak açıklanabilir olması zorunlu.

Her skor için:

```text
Score
Contribution
Reason
```

sakla.

Örneğin:

```text
Growth Score = 78

Revenue CAGR     +22
EBITDA Growth    +18
EPS Growth       +16
FCF Growth       +12
Consistency      +10
```

---

# 18. MAKROEKONOMİ MOTORU

Türkiye özelinde makro dashboard oluştur.

Takip edilecek başlıca seriler:

* TÜFE
* ÜFE
* politika faizi
* tahvil faizleri
* USD/TRY
* EUR/TRY
* DXY
* CDS mümkünse
* sanayi üretimi
* işsizlik
* kapasite kullanım
* PMI
* tüketici güven
* reel sektör güven
* cari denge
* rezervler
* kredi büyümesi

Tarihsel grafiklerini göster.

---

# 19. ŞİRKET-MAKRO HASSASİYET MODELİ

Her şirket tüm makro değişkenlerden aynı şekilde etkilenmez.

Örneğin havayolu:

```text
USD
EUR
Oil
Jet Fuel
Tourism
Interest rates
```

otomotiv:

```text
EUR
Domestic demand
Export demand
Credit
Interest
```

bankalar:

```text
Policy Rate
Loan Growth
Deposit Costs
Inflation
Yield Curve
```

Bu nedenle:

```text
CompanyMacroExposure
```

modeli oluştur.

---

# 20. KAP INTELLIGENCE

KAP açıklamalarını yalnız listeleme.

Her açıklamayı:

```text
DisclosureType
Importance
Sentiment
PotentialImpact
TimeHorizon
Summary
```

olarak analiz et.

Örneğin:

```text
NEW_CONTRACT
CAPEX
DIVIDEND
BUYBACK
FINANCIAL_RESULT
MANAGEMENT_CHANGE
LAWSUIT
CREDIT_RATING
INVESTMENT
SUBSIDIARY
M&A
GUIDANCE
```

KAP'ın orijinal linkini sakla.

---

# 21. NEWS INTELLIGENCE

Haber motoru:

* duplicate haberleri tespit etsin
* aynı olayın farklı kaynaklarını gruplayabilsin
* şirket ilişkisini belirlesin
* sentiment çıkarsın
* potansiyel etki belirlesin

Ama LLM sentiment'i tek başına yatırım kararı olarak kullanılmamalı.

Haber altında kaynak linki ve yayın zamanı mutlaka gösterilmeli.

---

# 22. SOURCE TRACEABILITY

Sistemde gösterilen önemli her bilginin:

```text
source
source_url
fetched_at
published_at
```

alanları mümkün olduğu kadar tutulmalı.

UI'da kullanıcı:

> Bu bilgi nereden geldi?

sorusunun cevabını görebilmeli.

---

# 23. DATA FRESHNESS

Her veri için freshness göster.

Örneğin:

```text
Price
Updated 12 min ago

Financial Statements
2026/Q2

Macro
Updated today

KAP
Updated 4 min ago
```

Stale data açık biçimde belirtilmeli.

---

# 24. ANALYSIS SNAPSHOTS

Bu sistemin en önemli özelliklerinden biridir.

Her analiz tarihsel olarak saklanmalı.

Örneğin:

```text
THYAO

2026-08-17
Overall Score: 78
Medium Term: Positive

2026-11-17
Overall Score: 72
Medium Term: Neutral/Positive
```

Sonra değişimi analiz et.

---

# 25. THESIS TRACKING

Sistem eski analiz ile yenisini karşılaştırmalı.

Örneğin:

```text
Since previous analysis:

Revenue growth       24% -> 18%
EBITDA margin        21% -> 18%
Net Debt / EBITDA    0.8 -> 1.4
ROIC                 27% -> 22%
Valuation            cheaper
```

Sonra:

```text
Thesis Strength:
WEAKENED
```

gibi sonuç oluşturabilsin.

---

# 26. CHANGE DETECTION

Kullanıcıya özellikle:

```text
What changed?
```

paneli sun.

Burada yalnız önemli değişiklikleri göster.

Örneğin:

```text
+ New investment announced
+ Revenue guidance increased
- EBITDA margin declined
- Debt increased
```

---

# 27. WATCHLIST

Kullanıcı istediği hisseleri watchlist'e ekleyebilmeli.

Watchlist üzerinde:

```text
Ticker
Price
Overall Score
Valuation
Short Term
Medium Term
Long Term
Latest Important Event
Last Analysis
```

göster.

---

# 28. ALERT ENGINE

Alarm sistemi oluştur.

Örnekler:

```text
New important KAP
New financial report
Score changed > 10
Thesis changed
Valuation became attractive
Debt threshold exceeded
Margin deteriorated
New dividend announcement
New investment
```

İleride:

email

Telegram

push

eklenebilecek abstraction kullan.

---

# 29. TEKNİK ANALİZ

Teknik analiz sistemin ana amacı değildir.

Ancak context amacıyla kullanılmalıdır.

Gösterilebilecek:

SMA 20

SMA 50

SMA 200

EMA

RSI

MACD

ATR

ADX

Volume trends

Support/Resistance

52-week high/low

Historical volatility

---

Teknik veriler özellikle kısa dönem context'ine katkıda bulunmalı.

Uzun vadeli investment thesis'i belirlememeli.

---

# 30. DASHBOARD

Ana dashboard profesyonel ama sade olmalı.

Ana bölümler:

```text
Market Overview

Macro Overview

Watchlist

Latest Important KAP

Major Financial Results

Major Thesis Changes

Interesting Valuation Opportunities

Upcoming Events
```

---

# 31. COMPANY DETAIL SCREEN

Bu sistemin ana ekranı olacak.

Önerilen yapı:

## Header

```text
THYAO
Türk Hava Yolları

Current Price
Market Cap
Sector
Last Updated
```

---

## AI Executive Summary

Kısa fakat güçlü özet.

---

## Investment Outlook

```text
SHORT TERM
MEDIUM TERM
LONG TERM
```

---

## Scorecard

Radar veya score cards:

```text
Quality
Growth
Profitability
Balance Sheet
Cash Flow
Valuation
Risk
```

---

## Investment Thesis

Bull Case

Bear Case

Catalysts

Risks

Thesis Breakers

---

## Financial Performance

Revenue

EBITDA

Net Income

EPS

FCF

grafikleri.

---

## Margins

Gross

EBITDA

Operating

Net

---

## Balance Sheet

Debt

Cash

Net Debt

Equity

---

## Returns

ROE

ROIC

ROA

---

## Valuation

P/E

EV/EBITDA

P/B

FCF Yield

historical bands.

---

## DCF

Bear/Base/Bull.

---

## Peer Comparison

---

## KAP Timeline

---

## News

---

## Macro Exposure

---

## Historical Analysis

---

# 32. DESIGN

Arayüz:

* profesyonel
* finansal terminal hissi veren
* ancak Bloomberg kadar karmaşık olmayan
* veri yoğun
* temiz
* hızlı
* desktop-first

olmalı.

Dark mode ve light mode destekle.

Renkler yalnız anlam taşıdığı yerde kullanılmalı.

Örneğin:

green = positive

red = negative

yellow = warning

Ama bütün UI'ı yeşil/kırmızıya boğma.

---

# 33. RESPONSIVE DESIGN

Desktop öncelikli geliştir.

Ancak tablet ve mobil kullanılabilir olmalı.

---

# 34. SEARCH

Global ticker search oluştur.

Örneğin:

```text
THY
```

girildiğinde:

```text
THYAO
Türk Hava Yolları
```

önerilsin.

---

# 35. API TASARIMI

REST API veya uygun gördüğün modern yaklaşımı kullan.

Örnek endpointler:

```text
GET /companies/search

GET /companies/{ticker}

GET /companies/{ticker}/financials

GET /companies/{ticker}/metrics

GET /companies/{ticker}/valuation

GET /companies/{ticker}/peers

GET /companies/{ticker}/kap

GET /companies/{ticker}/news

GET /companies/{ticker}/analysis

GET /companies/{ticker}/analysis/history

GET /companies/{ticker}/macro-exposure
```

Ayrıca:

```text
POST /analysis/{ticker}/refresh
```

oluşturulabilir.

---

# 36. REFRESH PIPELINE

Ticker refresh edildiğinde aşağıdaki pipeline çalışsın:

```text
Ticker
   ↓
Company Profile
   ↓
Market Data
   ↓
Financial Statements
   ↓
KAP
   ↓
News
   ↓
Macro Context
   ↓
Normalize
   ↓
Financial Metrics
   ↓
Valuation
   ↓
Peer Analysis
   ↓
Scoring
   ↓
Risk / Catalyst Detection
   ↓
Structured Analysis Context
   ↓
LLM Interpretation
   ↓
Persist Analysis Snapshot
   ↓
Frontend
```

Her stage observable olmalı.

---

# 37. FAILURE HANDLING

Bir provider başarısız olduğunda tüm analiz çökmemeli.

Örneğin:

Market Data:

SUCCESS

Financials:

SUCCESS

KAP:

SUCCESS

News:

FAILED

Macro:

SUCCESS

ise sonuç yine üretilebilmeli.

Ancak:

```text
News data unavailable
```

diye belirt.

---

# 38. DATA QUALITY

DataQualityScore tasarla.

Kontrol:

missing fields

stale data

inconsistent periods

duplicate financial reports

unexpected values

provider discrepancies

---

# 39. LLM CONTEXT

LLM'e raw database dump gönderme.

Structured context oluştur.

Örneğin:

```text
CompanyContext

FinancialContext

ValuationContext

SectorContext

MacroContext

KapContext

NewsContext

RiskContext

HistoricalContext
```

---

# 40. LLM OUTPUT

LLM structured JSON dönmeli.

Örneğin:

```json
{
  "executiveSummary": "...",

  "shortTerm": {
    "outlook": "NEUTRAL_POSITIVE",
    "confidence": 0.72,
    "reasoning": [],
    "risks": [],
    "catalysts": []
  },

  "mediumTerm": {},

  "longTerm": {},

  "bullCase": [],
  "bearCase": [],
  "keyRisks": [],
  "keyCatalysts": [],
  "thesisBreakers": [],
  "whatToWatch": []
}
```

Pydantic schema ile validate et.

---

# 41. HALLUCINATION KONTROLÜ

LLM çıktısında bulunan rakamsal iddiaların mümkünse context'te bulunup bulunmadığını validate et.

LLM kendi kaynaklarını uydurmamalı.

Kaynaklar backend tarafından verilmelidir.

---

# 42. PROMPT VERSIONING

LLM promptlarını kod içine gömmek yerine versioned yapıda tut.

Örneğin:

```text
prompts/

company-analysis-v1.md

kap-analysis-v1.md

financial-summary-v1.md
```

Prompt version analysis snapshot içine kaydedilmeli.

---

# 43. AI DISCLAIMER

Kullanıcı kişisel kullanım için sistemi kullanıyor olsa bile:

UI'da açıklama bulunmalı:

> Bu sistem yatırım kararı destek aracıdır. Üretilen analizler yatırım tavsiyesi değildir.

---

# 44. BACKTEST DEĞİL, HISTORICAL VALIDATION

Bu proje trading bot olmadığı için ilk aşamada klasik al/sat backtest'i ana özellik yapma.

Bunun yerine gelecekte:

```text
Analysis Outcome Tracking
```

eklenebilecek.

Örneğin:

3 ay önce:

Medium term positive

3 ay sonra:

Revenue

EBITDA

Price

ROIC

thesis değişimleri

karşılaştırılabilir.

---

# 45. AUTHENTICATION

Tek kullanıcı projesi olsa bile basic authentication ekle.

JWT veya session authentication kullanılabilir.

Local development için dev bypass olabilir.

---

# 46. SECURITY

Environment secrets hiçbir zaman repository'ye yazılmamalı.

`.env.example`

oluştur.

API keys:

encrypted / env based tutulmalı.

Rate limiting ekle.

Input validation uygula.

---

# 47. OBSERVABILITY

Structured logging kullan.

Loglarda:

```text
requestId

provider

ticker

operation

latency

result

error
```

bulunsun.

---

# 48. HEALTH CHECKS

Endpoint:

```text
/health

/health/ready
```

oluştur.

---

# 49. TESTING

Minimum:

unit tests

integration tests

provider contract tests

financial calculation tests

valuation tests

API tests

frontend component tests

---

Finansal hesaplamalar için özellikle deterministic fixture kullan.

---

# 50. DATA FIXTURES

Gerçek data provider olmadığında development yapılabilmesi için:

```text
THYAO
ASELS
FROTO
```

gibi şirketlerden mock fixture üret.

Ancak açık biçimde:

TEST DATA

olarak işaretle.

---

# 51. DATABASE MIGRATIONS

Alembic kullan.

Migration history düzgün tutulmalı.

---

# 52. CACHE

Uygun caching stratejisi tasarla.

Örneğin:

Company Profile:

24 saat

Macro Data:

source frequency

Historical Financials:

rapor açıklanana kadar

KAP:

kısa süre

Market Data:

provider'a göre

---

# 53. JOB SCHEDULING

Scheduler oluştur.

Örneğin:

Macro:

daily

Financial statements:

periodic

KAP:

frequent

News:

frequent

Company profile:

weekly

Ancak gerçek frekansları provider limitlerine göre config yap.

---

# 54. CONFIGURATION

Hardcode kullanma.

Örneğin:

```yaml
analysis:
  short_term_months: 6
  medium_term_months: 24

scoring:
  financial_quality_weight: 0.20
```

gibi config yaklaşımı kullanılabilir.

---

# 55. DOCUMENTATION

Aşağıdaki belgeleri oluştur:

```text
README.md

docs/ARCHITECTURE.md

docs/DATA_SOURCES.md

docs/DATABASE.md

docs/FINANCIAL_ENGINE.md

docs/VALUATION_ENGINE.md

docs/SCORING.md

docs/LLM.md

docs/DEPLOYMENT.md

docs/SECURITY.md

docs/ROADMAP.md
```

---

# 56. ARCHITECTURE DECISION RECORDS

Önemli kararlar için ADR oluştur.

Örneğin:

```text
ADR-001 Backend framework
ADR-002 Market data provider abstraction
ADR-003 LLM separation
ADR-004 Financial normalization
ADR-005 Analysis snapshots
```

---

# 57. GELİŞTİRME STRATEJİSİ

Projeyi tek seferde plansız kodlamaya başlama.

Önce repository'yi incele.

Eğer repository boşsa başlangıç mimarisini oluştur.

Sonra sırayla:

### Phase 1

Architecture + project bootstrap

### Phase 2

Database

### Phase 3

Company domain

### Phase 4

Provider abstraction

### Phase 5

Financial ingestion

### Phase 6

Financial engine

### Phase 7

Valuation

### Phase 8

Macro engine

### Phase 9

KAP + News

### Phase 10

Scoring + Investment thesis

### Phase 11

LLM

### Phase 12

Frontend

### Phase 13

Historical snapshots

### Phase 14

Watchlist + alerts

### Phase 15

Tests

### Phase 16

Docker + deployment

---

# 58. ÇALIŞMA TARZI

Her önemli geliştirme öncesinde:

1. mevcut kodu incele
2. mevcut mimariyle uyumu kontrol et
3. gerekiyorsa refactor et
4. implementation yap
5. test yaz
6. testleri çalıştır
7. edge-case kontrol et
8. documentation güncelle

---

# 59. KOD KALİTESİ

Şunlardan kaçın:

* giant service classes
* duplicate logic
* provider-specific business logic
* hardcoded financial formulas scattered everywhere
* God objects
* frontend'de finansal hesaplama
* LLM içerisinde business rule
* untyped JSON
* undocumented magic numbers

---

# 60. FINANCIAL FORMULA REGISTRY

Tüm finansal metriklerin formüllerini merkezi olarak dokümante et.

Örneğin:

```text
ROE = Net Income / Average Equity

ROIC =
NOPAT /
(Invested Capital)
```

Formülün:

* tanımı
* gerekli inputlar
* edge-case davranışı
* sektör istisnası

belirtilmeli.

---

# 61. BANKALAR İÇİN AYRI ANALİZ

Bankaları sanayi şirketi gibi değerlendirme.

Banka modülü için ileride veya uygun aşamada:

* Net Interest Margin
* Loan Growth
* Deposit Growth
* NPL
* CAR
* Fee Income
* ROE
* Cost/Income
* Loan/Deposit
* provisioning

gibi metrikler kullan.

---

# 62. GYO / REIT

GYO'larda:

* NAV
* NAV discount
* rental income
* occupancy
* debt
* property portfolio

gibi özel metrikler düşün.

---

# 63. HOLDING

Holdinglerde:

SOTP

Net Asset Value

holding discount

yaklaşımı değerlendir.

---

# 64. DATA NORMALIZATION

KAP finansal tablo isimleri zaman veya şirketler arasında farklılaşabiliyorsa mapping layer oluştur.

Örneğin:

```text
Revenue
Sales
Net Sales
Hasılat
```

tek canonical metric'e map edilebilmeli.

Mapping hardcode karmaşasına dönüşmemeli.

---

# 65. CURRENCY

TL

USD

EUR

gibi para birimlerini destekle.

Financial values için:

```text
value
currency
scale
```

tut.

Bin TL / milyon TL hatalarına karşı koruma oluştur.

---

# 66. INFLATION

Türkiye için nominal büyüme her zaman yeterli değildir.

Mümkün olduğunda:

```text
Nominal Growth
Real Growth
```

ayrımını destekle.

Enflasyon etkisinin yorumda belirtilmesini sağla.

---

# 67. FX IMPACT

Şirket için:

```text
Revenue FX Exposure
Debt FX Exposure
Export Share
Import Exposure
```

bulunabiliyorsa sakla.

Kur riskini analizde kullan.

---

# 68. MANAGEMENT GUIDANCE

Şirket guidance açıklıyorsa:

```text
Revenue guidance
EBITDA guidance
CAPEX guidance
Production guidance
```

sakla.

Sonra:

```text
Actual vs Guidance
```

karşılaştırması yap.

---

# 69. CONSENSUS

Güvenilir ve yasal olarak kullanılabilir bir analyst-consensus kaynağı bulunursa abstraction oluştur.

Ancak veri yoksa sistemi buna bağımlı yapma.

---

# 70. DIVIDEND ANALYSIS

Göster:

Dividend Yield

Payout Ratio

Dividend CAGR

Dividend Stability

Dividend History

---

# 71. CAPITAL ALLOCATION

Uzun vadeli analiz için:

Dividend

Buyback

Debt repayment

CAPEX

Acquisition

Capital increase

kararlarını takip et.

---

# 72. QUALITY FLAGS

Şirket için uyarılar üret.

Örneğin:

```text
Revenue rising but cash flow deteriorating

Profit rising due to one-off item

Receivables growing faster than revenue

Debt increasing faster than EBITDA

Share dilution

Margin compression

Negative working capital trend
```

---

# 73. ACCOUNTING ANOMALIES

Basit red-flag motoru oluştur.

İlk versiyonda aşırı karmaşık model gerekmiyor.

Rule-based olabilir.

---

# 74. ONE-OFF ITEMS

Tek seferlik gelir/giderler varsa normalize edilmiş kazanç analizi yapılabilmesi için veri modeli uygun olsun.

---

# 75. CONFIDENCE SCORE

Sistem her görüşe confidence vermeli.

Confidence:

LLM'in keyfi özgüveni olmamalı.

Şunlardan türet:

```text
Data completeness
Data freshness
Metric agreement
Historical consistency
Model coverage
```

---

# 76. EXPLAINABILITY

Her görüşte:

```text
Why?
```

açılabilmeli.

Örneğin:

```text
Medium Term: Positive

because:

+ Revenue CAGR strong
+ ROIC improving
+ valuation below historical median
+ leverage manageable

but:

- FX risk high
- margin slightly declining
```

---

# 77. AS-OF DATE

Her analizde:

```text
Analysis as of:
2026-08-17 21:30 TRT
```

gibi tarih bulunmalı.

LLM'in güncellik iddiası yalnız bu timestamp'e göre yapılmalı.

---

# 78. REPRODUCIBILITY

Bir analysis snapshot yeniden üretilebilmeli.

Sakla:

```text
financial dataset version
market data timestamp
macro snapshot
scoring version
valuation version
prompt version
model
```

---

# 79. VERSIONING

Aşağıdakileri versionla:

Financial Engine

Scoring Engine

Valuation Engine

LLM Prompt

---

# 80. UI — ANALİZ DEĞİŞİMİ

Historical snapshot karşılaştırma ekranı oluştur.

Örneğin:

```text
August vs November

Growth       82 → 75
Quality      79 → 80
Valuation    64 → 78
Debt         85 → 69
```

---

# 81. UI — WHAT MATTERS NOW

Company page üzerinde üst bölümde:

```text
WHAT MATTERS NOW
```

alanı olsun.

Maksimum 5 önemli konu:

```text
Margin decline
New factory investment
Debt rising
Valuation cheap
Strong export growth
```

---

# 82. UI — WHAT TO WATCH

Kullanıcıya sonraki dönem için:

```text
WHAT TO WATCH
```

göster.

Örneğin:

```text
Q3 EBITDA margin

New order backlog

Net debt

EUR/TRY

Upcoming investor presentation
```

---

# 83. AI CHAT

Şirket sayfasında context-aware chat eklenebilir.

Kullanıcı:

> THYAO'nun en büyük riski nedir?

sorarsa yalnız mevcut company context üzerinden cevaplasın.

> Borcu geçen yıla göre nasıl değişmiş?

gibi sorular cevaplanabilsin.

RAG veya structured context kullanılabilir.

Chat internetten kontrolsüz bilgi uydurmamalı.

---

# 84. CITATIONS

AI yanıtlarında mümkün olduğu kadar kaynak göster.

Örneğin:

```text
KAP – 2026 Q2 Financial Report

TCMB EVDS – USD/TRY

Company Investor Presentation
```

UI üzerinden açılabilsin.

---

# 85. PERFORMANCE

Ana ekranlarda gereksiz şekilde her request'te provider çağrısı yapma.

Önce DB/cache kullan.

Refresh işlemi ayrı olsun.

---

# 86. IDEMPOTENCY

Ingestion job'ları idempotent olmalı.

Aynı KAP bildirimi iki defa eklenmemeli.

Aynı financial period duplicate olmamalı.

---

# 87. TIMEZONE

Türkiye için:

```text
Europe/Istanbul
```

canonical timezone kullan.

Database'de timestamps mümkünse UTC sakla.

UI'da TRT göster.

---

# 88. UX PRENSİBİ

Kullanıcı finansal analist olmak zorunda değil.

Bu nedenle her kompleks metriğin:

tooltip

veya:

```text
What does this mean?
```

açıklaması bulunmalı.

Ancak profesyonel kullanıcıya da yeterli detay sunulmalı.

---

# 89. MVP ÖNCELİĞİ

Her şeyi aynı anda mükemmel yapmaya çalışma.

İlk çalışan vertical slice şu olmalı:

```text
Ticker Search

↓

Company Profile

↓

Financial Statements

↓

Financial Metrics

↓

Simple Valuation

↓

KAP

↓

Macro

↓

Scoring

↓

LLM Summary

↓

Company Detail UI
```

Bu akış uçtan uca çalıştıktan sonra genişlet.

---

# 90. İLK DEMO ŞİRKETLERİ

İlk validasyonu mümkünse farklı sektörlerden seç:

```text
THYAO
ASELS
FROTO
TUPRS
GARAN
```

Böylece industry-specific problemlerin erken ortaya çıkmasını sağla.

---

# 91. GELİŞTİRME SIRASINDA BENDEN ONAY BEKLEME

Makul teknik kararları kendin ver.

Bir şey belirsizse:

* mevcut requirement'lardan çıkarım yap
* en sürdürülebilir çözümü seç
* ADR ile belgele

Sadece erişilemeyen credential, ücretli API veya dış servis hesabı gibi gerçekten benim müdahalemi gerektiren durumları açıkça belirt.

Bunun dışında geliştirmeyi durdurma.

---

# 92. EXTERNAL DEPENDENCY POLICY

Ücretli servis gerekliyse önce:

* ücretsiz alternatif
* resmi API
* düşük maliyetli alternatif

araştır.

Sonra gerekli abstraction'ı oluştur.

Credential yoksa:

mock/provider fallback

ile geliştirmeye devam et.

---

# 93. VERİ KAYNAĞI ARAŞTIRMASI

Provider seçerken güncel web araştırması yap.

Eski blog yazılarına güvenme.

Mümkün olduğunca:

* resmi dokümantasyon
* resmi API dokümantasyonu
* provider pricing
* lisans koşulları

kullan.

Kararları:

```text
docs/DATA_SOURCES.md
```

içine yaz.

---

# 94. MALİYET ANALİZİ

Projeyi bitirirken ayrıca tahmini aylık maliyet raporu çıkar.

Şunları ayrı göster:

```text
VPS
Database
Redis
LLM
Market Data
News API
Other
```

Ve:

```text
Budget MVP
Recommended
Advanced
```

senaryoları oluştur.

---

# 95. SON TESLİMAT KRİTERLERİ

Proje sonunda aşağıdakiler bulunmalıdır:

* çalışan frontend
* çalışan backend
* çalışan PostgreSQL schema
* migrations
* provider architecture
* çalışan örnek veri ingestion
* financial calculation engine
* valuation engine
* scoring engine
* macro context
* KAP/news yapısı
* LLM interpretation
* historical analysis snapshots
* tests
* Docker Compose
* environment template
* documentation
* architecture documentation
* veri kaynakları dokümanı
* deployment guide

---

# 96. DEFINITION OF DONE

Bir feature tamamlandı sayılmadan önce:

```text
Implementation
Tests
Error handling
Logging
Types
Documentation
UI states
Loading state
Empty state
Error state
```

tamamlanmış olmalı.

---

# 97. BEKLENEN KULLANICI DENEYİMİ

Nihai deneyim şu olmalıdır:

Ben uygulamayı açıyorum.

Arama alanına:

```text
THYAO
```

yazıyorum.

Sistem bana tek ekranda:

* şirketin ne yaptığını
* finansal durumunu
* geçmiş 5 yıllık gelişimini
* son çeyrek değişimlerini
* gelir/kâr/marj trendlerini
* nakit akışını
* borcunu
* ROE/ROIC değerlerini
* sektör kıyasını
* tarihsel değerlemesini
* DCF senaryolarını
* KAP gelişmelerini
* önemli haberlerini
* şirketin makro hassasiyetlerini
* olumlu yatırım tezini
* karşı yatırım tezini
* riskleri
* katalizörleri
* tezi bozabilecek gelişmeleri
* kısa vadeli görünümü
* orta vadeli görünümü
* uzun vadeli görünümü
* önceki analize göre ne değiştiğini
* bundan sonra hangi verileri takip etmem gerektiğini

tek bir profesyonel yatırım araştırma ekranında göstermelidir.

En önemli prensip:

> Sistem benim yerime kör bir AL/SAT kararı vermek yerine, kaliteli bir analistin bir şirketi değerlendirirken ihtiyaç duyacağı bilgileri organize ederek bana daha iyi karar verebilmem için açık, izlenebilir ve güncel bir analiz ortamı sunmalıdır.

---

# 98. İLK GÖREVİN

Şimdi doğrudan kodlamaya başlamadan önce:

1. Bu gereksinimlerin tamamını analiz et.
2. Eksik veya çelişkili teknik noktaları kendi içinde çöz.
3. Güncel veri kaynaklarını araştır.
4. Projenin hedef mimarisini çıkar.
5. Domain modelini çıkar.
6. Database tasarımını oluştur.
7. Provider architecture'ı oluştur.
8. Financial Engine tasarımını oluştur.
9. Scoring modelini tasarla.
10. Valuation modelini tasarla.
11. LLM architecture'ını tasarla.
12. Frontend bilgi mimarisini çıkar.
13. Güvenlik ve deployment mimarisini çıkar.
14. Implementation roadmap oluştur.
15. Bunları `docs/` altında belgele.
16. Ardından MVP'nin ilk uçtan uca çalışan vertical slice'ını geliştirmeye başla.

Sadece plan üretip durma.

Planlama tamamlandıktan sonra aynı görev içerisinde implementasyona devam et.

Çalışan kod, migration, test ve dokümantasyon üret.

Her aşamada mevcut sistemi çalışır durumda tut.

Mimari borç oluşturacak kısa yolları yalnız gerçekten gerekli olduğunda kullan ve bunları `TODO` bırakmak yerine teknik borç dokümanına açıkça yaz.

Son hedef basit bir dashboard değil:

> Türkiye piyasasına özel, güvenilir veri kaynakları ve deterministik finansal hesaplama altyapısı üzerine kurulmuş, LLM destekli kişisel bir Investment Intelligence Platform üretmektir.
> \


# PHASE 1 — IMPLEMENTATION SCOPE AND EXECUTION RULES

Yukarıdaki gereksinimlerin tamamı projenin **nihai hedef mimarisini ve ürün vizyonunu** tanımlar.

Ancak bu görev kapsamında bütün sistemi tek seferde implement etmeye çalışma.

Öncelikle projenin tamamını anlayacak, gelecekteki fazları bozmayacak şekilde mimariyi tasarlayacak, ancak gerçek implementasyonu yalnızca **Phase 1 MVP Vertical Slice** kapsamıyla sınırlayacaksın.

Amaç:

> Küçük ama mimari olarak doğru, gerçekten çalışan ve ileride genişletilebilecek ilk uçtan uca sürümü üretmek.

Phase 1 sonunda sistem yalnızca demo UI olmamalı.

Gerçek bir:

```text
Ticker
→ Data Provider
→ Persistence
→ Financial Metrics
→ Basic Valuation
→ Structured Analysis
→ LLM Interpretation
→ API
→ Frontend
```

akışı çalışmalıdır.

---

# 1. ÖNCE BÜTÜN PROJEYİ ANLA

Implementasyona başlamadan önce yukarıdaki tüm gereksinimleri değerlendir.

Ancak bütün özellikleri implement etme.

Önce:

1. Nihai sistem mimarisini kavra.
2. Domain sınırlarını belirle.
3. Future phases için genişlemeye açık noktaları belirle.
4. Phase 1 için zorunlu dependency'leri seç.
5. Elzem olmayan özellikleri açıkça sonraki fazlara bırak.
6. Phase 1'in sınırlarını `docs/ROADMAP.md` içinde açık biçimde belgele.

Phase 1 kararları, sonraki fazlarda sistemi baştan yazmayı gerektirmemelidir.

Ancak gelecekte kullanılabilecek her şeyi şimdiden implement etmeye de çalışma.

**YAGNI prensibini uygula.**

---

# 2. PHASE 1'İN ANA HEDEFİ

Phase 1'in ana kullanıcı deneyimi şudur:

Kullanıcı uygulamayı açar.

Ticker aramasına:

```text
THYAO
```

girer.

Sistem şirketi bulur.

Company Detail ekranı açılır.

Ekranda minimum olarak şunlar bulunur:

* şirket temel bilgileri
* veri güncellik bilgisi
* son finansal dönem bilgileri
* temel finansal metrikler
* geçmiş dönem karşılaştırması
* basit değerleme bilgileri
* son önemli KAP kayıtları
* temel makro bağlam
* deterministik skorlar
* LLM tarafından oluşturulmuş kısa/orta/uzun vadeli açıklama
* kullanılan kaynaklar
* analiz timestamp'i

Bu akış gerçek backend üzerinden çalışmalıdır.

Frontend içinde hardcoded finansal veri kullanılmamalıdır.

---

# 3. PHASE 1'DE IMPLEMENT EDİLECEK ZORUNLU MODÜLLER

Aşağıdaki modüller Phase 1 kapsamındadır.

## 3.1 Project Bootstrap

Kur:

* monorepo veya uygun repository yapısı
* backend
* frontend
* PostgreSQL
* Redis yalnız gerçekten gerekiyorsa
* Docker Compose
* environment configuration
* migrations
* temel logging

Projeyi tek komutla ayağa kaldır:

```bash
docker compose up
```

veya eşdeğer basit bir development workflow oluştur.

---

# 3.2 Company Domain

Minimum:

```text
Company
Ticker
Sector
Industry
DataSource
```

modelle.

Ticker search çalışsın.

İlk etapta en az:

```text
THYAO
ASELS
FROTO
TUPRS
GARAN
```

şirketlerini sistem tanıyabilecek yapıda olsun.

Bütün BIST şirketlerini manuel hardcode etme.

Uygun bir bootstrap/import stratejisi oluştur.

---

# 3.3 Provider Architecture

Phase 1'de provider abstraction mutlaka oluştur.

Minimum:

```text
CompanyDataProvider
FinancialDataProvider
DisclosureProvider
MacroDataProvider
MarketDataProvider
```

tanımla.

Ancak her provider için birden fazla implementation yazma.

Phase 1'de her abstraction için yalnızca bir çalışan implementation yeterlidir.

Ücretli veya erişilemeyen provider varsa:

* interface oluştur
* mock/fallback implementation yaz
* problemi dokümante et

ama projeyi durdurma.

---

# 3.4 Financial Statements

Minimum destek:

```text
Income Statement
Balance Sheet
Cash Flow Statement
```

Son:

```text
4–5 yıllık yıllık veri
```

ve mümkünse:

```text
8 çeyrek
```

desteklenecek mimariyi kur.

Phase 1'de veri kaynağının sınırlamaları varsa mevcut en iyi kullanılabilir veriyle ilerle.

Normalize edilmiş canonical field yapısı oluştur.

Minimum alanlar:

### Income Statement

* Revenue
* Gross Profit
* EBITDA
* EBIT
* Net Income

### Balance Sheet

* Cash
* Total Assets
* Total Debt
* Equity

### Cash Flow

* Operating Cash Flow
* CAPEX
* Free Cash Flow

---

# 3.5 Financial Metric Engine

Phase 1'de yalnızca en önemli metrikleri implement et.

Minimum:

```text
Revenue Growth YoY
Revenue CAGR 3Y

EBITDA Growth YoY
EBITDA Margin

Net Income Growth YoY
Net Margin

ROE

Net Debt
Net Debt / EBITDA

Debt / Equity

Operating Cash Flow

Free Cash Flow
FCF Margin
```

Her formül:

* deterministic
* unit tested
* merkezi olarak tanımlı

olmalıdır.

Phase 1'de onlarca finansal oran ekleyerek scope'u şişirme.

---

# 3.6 Basic Valuation Engine

Phase 1'de tam DCF motoru zorunlu değildir.

Minimum destek:

```text
P/E
P/B
EV/EBITDA
```

mümkün olan şirketlerde hesaplanmalı.

Ayrıca mümkünse:

```text
Current valuation
vs
Historical valuation
```

karşılaştırması yap.

Peer valuation Phase 1'de zorunlu değildir.

DCF Phase 2 veya Phase 3'e bırakılabilir.

Ancak valuation engine abstraction'ı DCF eklenmesini engellemeyecek şekilde tasarlanmalıdır.

---

# 3.7 KAP Integration

Phase 1'de şirket için son KAP açıklamalarını getir.

Minimum:

```text
title
published_at
source_url
type
```

sakla.

LLM ile gelişmiş KAP classification zorunlu değildir.

Ancak en azından basit kategoriler oluşturabiliyorsan ekle.

Örneğin:

```text
FINANCIAL_RESULT
DIVIDEND
INVESTMENT
CONTRACT
MANAGEMENT
OTHER
```

---

# 3.8 Macro Context

Phase 1'de tüm Türkiye ekonomi dashboard'unu yapma.

Sadece şirket analizine temel bağlam verecek birkaç makro veri yeterli.

Minimum:

```text
Policy Rate
CPI
USD/TRY
EUR/TRY
```

Mümkünse TCMB/EVDS gibi resmi kaynaklardan çek.

Her seride:

```text
value
observation_date
source
fetched_at
```

tut.

---

# 3.9 Scoring Engine

Phase 1'de basit, açıklanabilir deterministic scoring oluştur.

Minimum:

```text
Growth Score
Profitability Score
Balance Sheet Score
Cash Flow Score
Valuation Score
Overall Score
```

Her skorun katkısı görülebilmeli.

Örneğin:

```text
Growth Score: 76

Revenue Growth       +25
EBITDA Growth        +20
Net Income Growth    +16
Consistency          +15
```

Magic number'ları kod içine rastgele dağıtma.

Config veya merkezi scoring definition kullan.

---

# 3.10 Structured Analysis Context

Backend aşağıdaki gibi LLM-ready structured context üretmeli:

```json
{
  "company": {},
  "financials": {},
  "metrics": {},
  "valuation": {},
  "macro": {},
  "disclosures": [],
  "scores": {},
  "dataQuality": {},
  "asOf": "..."
}
```

LLM doğrudan DB veya provider'a erişmemelidir.

---

# 3.11 LLM Integration

Phase 1'de yalnızca bir ana analiz promptu yeterlidir.

LLM şu alanları üretmelidir:

```text
Executive Summary

Short-Term Outlook
Medium-Term Outlook
Long-Term Outlook

Positive Factors
Negative Factors

Key Risks
Key Catalysts

What To Watch
```

Structured JSON output kullan.

Pydantic ile validate et.

LLM'e numeric hesap yaptırma.

LLM'in bilmediği bilgi konusunda spekülasyon üretmesini engelle.

---

# 3.12 Source Traceability

Phase 1 için bu özellik zorunludur.

Her önemli dış verinin mümkün olduğunca:

```text
source
source_url
published_at
fetched_at
```

bilgisi bulunmalıdır.

UI'da kaynak görüntülenebilmelidir.

---

# 3.13 Data Freshness

Minimum olarak:

```text
Financials updated:
Market data updated:
KAP updated:
Macro updated:
Analysis generated:
```

bilgilerini göster.

---

# 3.14 Company Detail Frontend

Phase 1'de tek ana ekran yeterlidir.

Company Detail ekranında minimum şu section'lar olsun:

### Header

```text
Ticker
Company Name
Sector
Price if available
Market Cap if available
Last Updated
```

### Executive Summary

LLM generated.

### Outlook

```text
Short Term
Medium Term
Long Term
```

### Scorecard

```text
Growth
Profitability
Balance Sheet
Cash Flow
Valuation
Overall
```

### Financial Performance

Minimum grafikler:

```text
Revenue
EBITDA
Net Income
Free Cash Flow
```

### Financial Metrics

Temel metrik tablosu.

### Valuation

P/E

P/B

EV/EBITDA

### Latest KAP

Son önemli açıklamalar.

### Macro Context

Policy rate

Inflation

FX

### What Matters Now

Önemli 3–5 bulgu.

### What To Watch

İleride takip edilmesi gereken 3–5 metrik/olay.

### Sources

Kullanılan kaynaklar.

---

# 4. PHASE 1'DE YAPILMAYACAKLAR

Aşağıdaki özellikler nihai proje kapsamındadır fakat Phase 1'de implement edilmesi zorunlu değildir.

Bunları sırf requirement içinde geçiyor diye şimdi geliştirme.

## Şimdilik ertele:

* gelişmiş DCF
* WACC sensitivity matrix
* Bear/Base/Bull detaylı intrinsic valuation
* gelişmiş peer analysis
* otomatik peer discovery
* tüm sektörlere özel engine'ler
* bankalar için tam özel analiz motoru
* GYO özel analizi
* holding SOTP
* sigorta özel analizi
* gelişmiş news aggregation
* haber duplicate clustering
* gelişmiş sentiment engine
* RAG chat
* company AI chat
* watchlist
* alert engine
* Telegram notification
* email notification
* push notification
* full BIST market dashboard
* gelişmiş teknik analiz
* intraday trading indicators
* backtesting
* prediction model
* ML price prediction
* advanced accounting anomaly detection
* consensus analyst data
* management guidance extraction
* automatic thesis breaker monitoring
* sophisticated capital allocation engine
* historical analysis comparison UI
* advanced thesis tracking
* portfolio management
* user portfolio
* broker integration
* automatic trading
* WebSocket market stream
* Kubernetes
* microservices
* Kafka
* Elasticsearch

Bu özellikler için yalnızca mevcut mimarinin gelecekte eklenmeye engel olmadığını kontrol et.

Placeholder servisler veya boş class'lar oluşturma.

Gerektiğinde daha sonra implement et.

---

# 5. OVERENGINEERING YAPMA

Phase 1 kişisel kullanıma yönelik bir MVP'dir.

Bu nedenle sırf büyük sistemlerde kullanılıyor diye:

```text
Kafka
Kubernetes
Event Sourcing
CQRS
Microservices
Service Mesh
Elasticsearch
GraphQL federation
```

gibi teknolojiler ekleme.

Gerçek ihtiyaç yoksa kullanma.

Başlangıç için mümkün olduğunca:

```text
Modular Monolith
```

tercih et.

Ancak domain sınırlarını düzgün oluştur.

---

# 6. DATABASE PRENSİBİ

Phase 1'de schema'yı gelecekteki bütün feature'ları tahmin ederek yüzlerce tabloya dönüştürme.

Yalnız mevcut vertical slice için gereken tabloları oluştur.

Muhtemel minimum:

```text
companies

financial_periods
financial_values

market_snapshots

kap_disclosures

macro_series
macro_observations

financial_metric_snapshots

valuation_snapshots

score_snapshots

analysis_snapshots

data_sources
data_fetch_logs
```

Daha iyi normalized yapı tasarlayabiliyorsan kullan.

---

# 7. GERÇEK VERİ ÖNCELİĞİ

Phase 1 mümkün olduğunca gerçek veriyle çalışmalıdır.

Ancak veri erişim problemi tüm geliştirmeyi bloklamamalıdır.

Şu sırayı kullan:

```text
Official API
↓
Reliable free provider
↓
Legally usable public source
↓
Mock fixture
```

Mock kullanılan her yer açıkça belirtilmelidir.

Production verisiymiş gibi gösterilmemelidir.

---

# 8. İLK VALIDASYON ŞİRKETİ

İlk vertical slice için:

```text
THYAO
```

kullan.

THYAO uçtan uca çalıştıktan sonra en az:

```text
ASELS
FROTO
```

üzerinde smoke test yap.

Phase 1'i bütün BIST için kusursuz hale getirmeye çalışma.

Architecture genellenebilir olsun fakat ilk validasyon birkaç şirketle yeterlidir.

---

# 9. INDUSTRY-SPECIFIC PROBLEM

Phase 1'de bütün sektörlerin özel finansal analizini çözmeye çalışma.

İlk implementasyon:

```text
non-financial industrial/service companies
```

üzerinden generic financial engine kullanabilir.

Bankalar gibi özel sektörleri algıla ve gerekiyorsa:

```text
Specialized financial analysis not yet supported
```

şeklinde açıkça belirt.

Yanlış generic skor üretmektense unsupported state göster.

---

# 10. DATA QUALITY

Minimum DataQuality modeli oluştur.

Örneğin:

```json
{
  "completeness": 0.91,
  "freshness": 0.95,
  "overall": 0.92,
  "warnings": []
}
```

LLM confidence değerlendirmesine bu veri aktarılabilir.

---

# 11. CONFIDENCE

Phase 1'de confidence değeri:

LLM'in kendi değerlendirmesi olmamalı.

Basit deterministic formülle:

```text
Data Completeness
Data Freshness
Metric Coverage
```

üzerinden üret.

---

# 12. TEST STRATEJİSİ

Phase 1 için özellikle şu testlere önem ver:

### Financial Engine

Her formülü fixture üzerinden doğrula.

### Provider Tests

Provider response parsing doğrula.

### API

Company detail endpoint'ini integration test ile doğrula.

### LLM

LLM çağrısını unit testlerde mockla.

Structured output validation test et.

### Frontend

En az kritik Company Detail state'lerini test et:

```text
loading
success
partial data
error
```

---

# 13. PARTIAL FAILURE

Company analysis pipeline şu durumda çalışmaya devam etmeli:

```text
Financials       SUCCESS
Market Data      SUCCESS
KAP              SUCCESS
Macro            SUCCESS
News             NOT IMPLEMENTED
```

Phase 1'de olmayan bir modül analiz pipeline'ını bozmasın.

---

# 14. REFRESH ENDPOINT

Minimum:

```text
POST /api/companies/{ticker}/refresh
```

oluştur.

Pipeline:

```text
fetch
normalize
persist
calculate
score
analyze
snapshot
```

çalıştırmalı.

Long-running işlem olması halinde uygun background job tasarımı kullanılabilir.

Ancak Phase 1'de gereksiz job architecture karmaşası yaratma.

---

# 15. COMPANY ANALYSIS ENDPOINT

Frontend'in mümkün olduğunca az request ile çalışması için aggregate endpoint düşün.

Örneğin:

```text
GET /api/companies/{ticker}/analysis
```

şunları dönebilir:

```text
company
market
financials
metrics
valuation
scores
macro
disclosures
analysis
sources
freshness
```

Domain endpointlerini ayrıca tutabilirsin.

---

# 16. ANALYSIS SNAPSHOT

Phase 1'de analysis snapshot mutlaka saklanmalı.

Minimum:

```text
ticker
created_at
as_of
input_dataset_hash veya version
financial_engine_version
scoring_version
valuation_version
prompt_version
llm_model
analysis_json
```

Bu ileride historical comparison yapabilmek için temeli oluşturacaktır.

Historical comparison UI Phase 1'de gerekmez.

---

# 17. VERSIONING

Başlangıçtan itibaren minimum versionları kullan:

```text
financial_engine_version = v1
valuation_engine_version = v1
scoring_engine_version = v1
analysis_prompt_version = v1
```

---

# 18. DOKÜMANTASYON

Phase 1 sonunda minimum şu belgeler hazır olmalı:

```text
README.md

docs/ARCHITECTURE.md
docs/PHASE_1_SCOPE.md
docs/DATA_SOURCES.md
docs/DATABASE.md
docs/FINANCIAL_ENGINE.md
docs/SCORING.md
docs/LLM.md
docs/ROADMAP.md
```

`ROADMAP.md` içinde açıkça:

```text
Phase 1
Phase 2
Phase 3
Phase 4
```

ayrımı yap.

---

# 19. PHASE 1 DEFINITION OF DONE

Phase 1 ancak aşağıdakilerin tamamı çalışıyorsa bitmiş kabul edilir:

* uygulama local ortamda ayağa kalkıyor
* database migration başarılı
* frontend açılıyor
* ticker search çalışıyor
* THYAO detail page açılıyor
* backend gerçek veya açıkça belirtilmiş fallback data getiriyor
* finansal veri DB'ye yazılıyor
* finansal metrikler backend tarafından hesaplanıyor
* basit valuation çalışıyor
* KAP verisi geliyor
* temel makro data geliyor
* scoring deterministic şekilde hesaplanıyor
* structured LLM context oluşturuluyor
* LLM analysis üretilebiliyor
* LLM structured response validate ediliyor
* analysis snapshot saklanıyor
* frontend sonuçları gösteriyor
* kaynaklar UI'da görülebiliyor
* stale/missing data kullanıcıya gösteriliyor
* critical unit/integration tests geçiyor
* Docker development setup çalışıyor
* README kurulum adımlarını içeriyor

Bunlardan biri eksikse Phase 1 tamamlanmış değildir.

---

# 20. PHASE 1 SONUNDA DUR

Phase 1 Definition of Done sağlandıktan sonra:

**Phase 2 implementasyonuna otomatik olarak geçme.**

Bunun yerine:

1. Yapılan işleri özetle.
2. Architecture kararlarını belirt.
3. Kullanılan gerçek veri kaynaklarını belirt.
4. Mock/fallback kalan alanları belirt.
5. Çalıştırılan testleri ve sonuçlarını belirt.
6. Bilinen problemleri belirt.
7. Teknik borçları belirt.
8. Phase 2 için önerilen işleri önceliklendir.
9. Repository'nin mevcut durumunu çalışır şekilde bırak.

Phase 2'ye geçmek için yeni görev bekle.

---

# 21. UYGULAMA SIRASI

Phase 1'i aşağıdaki sırayla geliştir:

```text
1. Architecture / repository bootstrap

2. PostgreSQL schema + migrations

3. Company domain + ticker search

4. Provider abstractions

5. Financial data ingestion

6. Financial normalization

7. Financial metric engine

8. Market data integration

9. Basic valuation engine

10. KAP integration

11. Macro integration

12. Scoring engine

13. Structured company analysis context

14. LLM integration

15. Analysis snapshot persistence

16. Aggregate API

17. Company detail frontend

18. Source/freshness UI

19. Tests

20. Docker/developer documentation
```

Bir sonraki katmana geçmeden önce mevcut katmanın temel testlerini çalıştır.

---

# 22. ÖNCELİK SIRASI

Karar verirken öncelik sırası:

```text
Correctness
>
Data Integrity
>
Traceability
>
Maintainability
>
Working Vertical Slice
>
Visual Polish
>
Advanced Features
```

Şık frontend uğruna backend doğruluğundan taviz verme.

Ekstra özellik uğruna vertical slice'ı yarım bırakma.

---

# 23. PHASE 1 BAŞLANGIÇ KOMUTU

Şimdi yukarıdaki bütün ürün gereksinimlerini nihai sistem vizyonu olarak kabul et.

Ancak yalnızca bu bölümde tanımlanan **Phase 1 scope**'unu implement et.

İlk olarak mevcut repository durumunu analiz et ve Phase 1 için gerekli mimari kararları ver.

Ardından implementation'a geç.

Sırf plan hazırlayıp görevi bitirme.

Çalışan Phase 1 vertical slice'ı üret.

Phase 1 dışındaki özellikleri yalnız roadmap'e yaz ve implement etme.



