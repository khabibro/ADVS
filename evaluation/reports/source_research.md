# Source Research Report

Research date: 2026-09-09. All sources are public web pages (government portals,
university administrative pages, an official legal-database, and HR/legal
vendor blogs). **No binary file (PDF/PNG/JPG/HWP) was downloaded from any
source** -- every source's disposition is `RECREATE_ONLY` (see
`evaluation/sources/source_registry.json` for the full policy statement and
per-source metadata). Everything in the dataset is a from-scratch recreation
using fictional data, informed by what these sources say about real field
structure and terminology.

## GRADUATION_CERTIFICATE (졸업증명서)

- [대학(교) 졸업(예정)증명서 발급](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13404000009) -- 정부24, issuing authority 교육부 (Ministry of Education). Confirms issuance channels (online/in-person/fax/mail) and same-day processing.
- [대학교 학위수여(예정) 증명](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13404000031) -- 정부24. **학위수여증명서** is a distinct, official title used for graduate-level degree completion -- a real alternate wording for the same underlying credential.
- [증명서 발급](https://www.jbnu.ac.kr/web/academic/certificate.do) -- 전북대학교. Confirms the real taxonomy of certificate types a university issues: 졸업증명서, 재학증명서 (enrollment), 성적증명서 (transcript), 학위수여증명서 (graduate only).
- [증명발급 안내](https://www.hanyang.ac.kr/web/www/diploma_seoul) -- 한양대학교. Cross-validates the same taxonomy.
- [학부생·대학원생 제증명](https://www.konkuk.ac.kr/konkuk/2190/subview.do) -- 건국대학교. Third independent confirmation.

**Why useful**: none of these pages show the certificate's visual layout (Korean universities don't publish blank templates publicly), but they authoritatively confirm (a) the real document-title vocabulary, including a legitimate alternate ("학위수여증명서") not previously in the benchmark, and (b) three real, common, genuinely out-of-scope negative document types (재학증명서, 성적증명서) issued by the same institutions.

**Downloaded**: no files. **Recreated**: yes -- new samples testing "학위수여증명서" as a title variant, and new negative samples for 재학증명서/성적증명서.

## CAREER_CERTIFICATE (경력증명서)

- [재직(퇴직·경력)증명](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=00000000008) -- 정부24. Confirms **there is no single government-mandated visual format** for this document -- it is employer-issued, content-based only.
- [경력증명서 vs 재직증명서 차이](https://blog.greetinghr.com/hr-practical-employment-certificate-guide/) -- GreetingHR (HR SaaS blog). Confirms required content (근무 기간, 직위, 담당 업무 내용, issuer name, company seal) and the real distinction between "currently employed" (재직증명서) and "past work history" (경력증명서).
- [경력증명서 양식/작성가이드](https://help.jobis.co/hc/ko/articles/115004060874) -- Jobis help center.
- [경력증명서 양식](https://lawform.io/magazine/582) -- LawForm.
- [재직증명서, 경력증명서 양식](https://iksun.kr/board/?bmode=view&idx=17769203) -- 노무법인 익선 (labor law firm).

**Why useful**: confirms our existing label choices (재직기간, 직위) match real-world convention, and confirms 재직증명서 is a real, common, genuinely-different negative document -- not previously in the benchmark's negative pool.

**Downloaded**: no files. **Recreated**: yes -- new 재직증명서 negative sample.

## BUSINESS_REGISTRATION_CERTIFICATE (사업자등록증)

- [[별지 제6호서식] 사업자등록증](https://www.law.go.kr/LSW/flDownload.do?flSeq=98965951) -- **국가법령정보센터 (법제처)**, the official Korean legal database. This is the single most authoritative source in this research: the officially annexed form's field list, quoted directly in the search snippet: **①등록번호 ②법인명칭(상호) ③대표자 성명 ④주민등록번호 ⑤주사무소**.
- [[별지 제4호서식(1)] 사업자등록증](https://law.go.kr/flDownload.do?flSeq=61491593) -- 국가법령정보센터. A second official annexed form confirming: 등록번호, 상호, 성명, 개업연월일, 사업장소재지, 사업의종류(업태,종목), 교부사유, 공동사업자, 주류판매신고번호.
- [사업자등록 안내 -- 제출서류 및 교부](https://www.nts.go.kr/nts/ad/cntnts/cntntsView.do?mi=2445) -- 국세청 (NTS).
- [사업자등록증명 발급](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=12100000016) -- 정부24. Confirms **사업자등록증명(원)** is a *different* official document from 사업자등록증 itself (a status-confirmation printout vs. the original certificate) -- same evidentiary purpose, different document.
- [사업자등록증(개인용)](https://www.bizforms.co.kr/form_view/form_4519.asp) -- Bizforms (commercial vendor), corroborating the same official field list.

**Finding #1 (the most concrete, actionable finding of this research)**: the current extractor's label lists (`company_name: ["상호", "상호명"]`, `representative_name: ["대표자", "대표자명"]`) are missing the *exact official label wording* used on the real legally-annexed form: **법인명칭** (for company name) and **대표자 성명** (for representative name, as a compound label rather than "대표자" alone). This is a real, evidence-based vocabulary gap, tested in the new benchmark below (see Error Analysis).

**Downloaded**: no files. **Recreated**: yes -- new samples using "법인명칭" and "대표자 성명" labels; a new near-miss negative using "사업자등록증명원" wording.

## SME_CONFIRMATION_CERTIFICATE (중소기업확인서)

- [중소기업현황정보시스템 (SMINFO)](https://sminfo.mss.go.kr/) -- 중소벤처기업부. The official issuing system.
- [소상공인 확인서](https://sminfo.mss.go.kr/er/er/EER003R2.do) -- SMINFO. Confirms validity-period convention: renewal window opens 3 months after the prior fiscal year's end (informs realistic date generation, did not change the existing fixed-range generator).
- [중소기업확인서 발급방법](https://help.jobis.co/hc/ko/articles/360001545713) -- Jobis help center, cross-validating the SMINFO workflow.
- [중소기업확인서 발급 조회](https://www.gov.kr/portal/service/serviceInfo/142000000077) -- 정부24. Confirms legal basis (「중소기업기본법」 제2조).
- [중소기업 소상공인확인서발급](https://www.smes.go.kr/pageApplyCertificateSme) -- a second official MSS-related domain, cross-validating.

**Why useful**: confirms issuing authority, legal basis, and validity-period logic. Existing label choices (유효기간, 확인번호, 사업자등록번호) already match real-world convention -- no vocabulary gap found here.

**Downloaded**: no files. **Recreated**: no new label variants needed; existing generator's realistic label set already aligns.

## Summary of concrete changes this research motivated

1. New `RECREATED_FROM_PUBLIC_REFERENCE` samples using official-form label wording (법인명칭, 대표자 성명) for BUSINESS_REGISTRATION_CERTIFICATE, explicitly citing `src_business_01`/`src_business_02`.
2. New GRADUATION_CERTIFICATE title-variant sample using "학위수여증명서" (citing `src_graduation_02`).
3. New negative samples: 재학증명서 (already had one; added a second variant), **성적증명서** (new), **재직증명서** (new), **사업자등록증명원** (new, near-miss).

No sample was added merely to inflate a count -- every new sample traces to a specific, cited finding above.
