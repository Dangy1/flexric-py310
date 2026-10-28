# Bibliography lookup for R1.7 (volume / issue / month / pages)

Sources: Crossref REST API (api.crossref.org/works/<DOI>, queried 2026-10-28), doi.org BibTeX content negotiation, arXiv abs pages.
IEEE Xplore pages could not be fetched from this environment (HTTP 418 / empty page; I did not try to evade the block), so IEEE early-access *dates* are NOT verified. Where I give Crossref "created"/"deposited" dates they are only the DOI-registration date, not the Xplore early-access date. Check these three on Xplore by hand (see sections 5, 7, 10).

Summary table

| key | status | vol/issue | month | pages / art. no. |
|---|---|---|---|---|
| singh2025agentic | published (ICC 2026 proceedings) | n/a (conference) | May 2026 | 1-6 |
| chatzistefanidis2025mxai | published (ICC 2026 proceedings) | n/a (conference) | May 2026 | 1-6 |
| li2026multi | published (ICC 2026 proceedings) | n/a (conference) | May 2026 | 1-6 |
| chatzistefanidis2025agoran | published | vol 275, no issue number (Elsevier, article-number journal) | Feb 2026 | art. 111927 |
| elkael2026agentran | early access (per Crossref: no vol/issue) | - | not verified | 1-7 (early-access paging) |
| maxenti2026autoran | published | vol 25, issue 7 | Jul 2026 | 10112-10129 |
| chatzimiltis2026agentic | early access (per Crossref: no vol/issue) | - | not verified | 1-9 (early-access paging) |
| polese2026beyond | published | vol 64, issue 7 | Jul 2026 | 90-95 |
| al2026ran | published | vol 25, issue 7 | Jul 2026 | 10876-10892 |
| navidan2026toward | early access (per Crossref/arXiv; Crossref record last indexed 2026-06-24, so may be stale) | - | not verified | 1-9 (early-access paging) |

---

## 1. singh2025agentic
**Status: published (conference, ICC 2026).** The bib entry cites the arXiv preprint; the published version exists.
- DOI: 10.1109/ICC59461.2026.11587987
- Source: https://api.crossref.org/works/10.1109/icc59461.2026.11587987 ; https://doi.org/10.1109/icc59461.2026.11587987 ; arXiv https://arxiv.org/abs/2510.16144 (v1 only, 17 Oct 2025; no journal-ref or DOI on arXiv page)
- Crossref: ICC 2026 - IEEE International Conference on Communications, Glasgow, UK, 24-28 May 2026, pp. 1-6, publisher IEEE. Conference papers have no volume/issue.
- Mismatches: title and authors match (9 authors, same order; Crossref gives "Shweta M" and "Madhan Raj K" as given+family, bib braces are fine). Year: bib 2025 (arXiv year), published year is 2026. Bib uses journal = "arXiv preprint", should be a proceedings entry.
```bibtex
@inproceedings{singh2025agentic,
  author    = {Singh, Sukhdeep and Bhat, Avinash and {Shweta M} and Singh, Subhash K. and Hong, Moonki and {Madhan Raj K} and Sithamparanathan, Kandeepan and Khowaja, Sunder A. and Dev, Kapal},
  title     = {Agentic {AI} for Ultra-Modern Networks: Multi-Agent Framework for {RAN} Autonomy and Assurance},
  booktitle = {Proc. IEEE Int. Conf. Commun. (ICC)},
  address   = {Glasgow, United Kingdom},
  month     = may,
  year      = {2026},
  pages     = {1--6},
  doi       = {10.1109/ICC59461.2026.11587987}
}
```
(Key is unchanged so \cite still works; the key year 2025 is cosmetic.) Crossref middle initial for Subhash: "Subhash Kumar Singh" vs bib "Subhash K."; either is acceptable.

## 2. chatzistefanidis2025mxai
**Status: published (conference, ICC 2026).**
- DOI: 10.1109/ICC59461.2026.11587665
- Source: https://api.crossref.org/works/10.1109/icc59461.2026.11587665 ; https://doi.org/10.1109/icc59461.2026.11587665 ; arXiv https://arxiv.org/abs/2508.09197 (v1 only, 8 Aug 2025, comment "submitted to the IEEE for possible publication")
- Crossref: ICC 2026, Glasgow, 24-28 May 2026, pp. 1-6.
- Mismatches: title and 8 authors match. Year 2025 -> 2026; arXiv "journal" -> inproceedings.
```bibtex
@inproceedings{chatzistefanidis2025mxai,
  author    = {Chatzistefanidis, Ilias and Leone, Andrea and Yaghoubian, Ali and Irazabal, Mikel and Sehad, Nassim and Bariah, Lina and Debbah, M\'{e}rouane and Nikaein, Navid},
  title     = {{MX-AI}: Agentic Observability and Control Platform for Open and {AI-RAN}},
  booktitle = {Proc. IEEE Int. Conf. Commun. (ICC)},
  address   = {Glasgow, United Kingdom},
  month     = may,
  year      = {2026},
  pages     = {1--6},
  doi       = {10.1109/ICC59461.2026.11587665}
}
```

## 3. li2026multi
**Status: published (conference, ICC 2026).** Bib says "Accepted/In press"; it is now in the proceedings.
- DOI: 10.1109/ICC59461.2026.11587748
- Source: https://api.crossref.org/works/10.1109/icc59461.2026.11587748
- Crossref: ICC 2026, Glasgow, 24-28 May 2026, pp. 1-6. Authors Haiyuan Li, Yulei Wu, Dimitra Simeonidou; title matches.
- Mismatches: none in title/authors/year; only the "Accepted/In press" note and missing pages/month/DOI.
```bibtex
@inproceedings{li2026multi,
  author    = {Li, Haiyuan and Wu, Yulei and Simeonidou, Dimitra},
  title     = {Multi-Agentic {AI} for Conflict-Aware {rApp} Policy Orchestration in Open {RAN}},
  booktitle = {Proc. IEEE Int. Conf. Commun. (ICC)},
  address   = {Glasgow, United Kingdom},
  month     = may,
  year      = {2026},
  pages     = {1--6},
  publisher = {IEEE},
  doi       = {10.1109/ICC59461.2026.11587748}
}
```

## 4. chatzistefanidis2025agoran
**Status: published.** Computer Networks (Elsevier) vol. 275, Feb 2026, article 111927. Elsevier does not use issue numbers for this journal in Crossref (no issue field); online first Dec 2025 (Crossref record created 2025-12-11; the Elsevier copyright line says (c) 2025).
- DOI: 10.1016/j.comnet.2025.111927
- Source: https://api.crossref.org/works/10.1016/j.comnet.2025.111927 ; https://doi.org/10.1016/j.comnet.2025.111927
- Crossref: volume 275, article-number 111927, page 111927, issued/print 2026-02, ISSN 1389-1286.
- Mismatches: title and 8 authors match (Crossref title capitalised "AGORAN"). Year: bib 2025, issue date is 2026 (Feb). Bib lacks volume and month. Issue number is not in Crossref; I could not check ScienceDirect (not tried), so say "no issue" only if ScienceDirect confirms; otherwise omit.
```bibtex
@article{chatzistefanidis2025agoran,
  author    = {Chatzistefanidis, Ilias and Nikaein, Navid and Leone, Andrea and Maatouk, Ali and Tassiulas, Leandros and Morabito, Roberto and Pitsiorlas, Ioannis and Kountouris, Marios},
  title     = {{AGORAN}: An Agentic Open Marketplace for {6G} {RAN} Automation},
  journal   = {Computer Networks},
  volume    = {275},
  month     = feb,
  year      = {2026},
  pages     = {111927},
  doi       = {10.1016/j.comnet.2025.111927},
  publisher = {Elsevier}
}
```

## 5. elkael2026agentran
**Status: early access (not independently confirmed on Xplore).** Crossref has no volume/issue/month; pages "1-7"; the page range 1-7 is the typical IEEE early-access placeholder. Crossref record created 2026-05-14, deposited 2026-05-15, last indexed 2026-10-07 (still no volume/issue as of that index). IEEE Xplore early-access date: NOT verified.
- DOI: 10.1109/MCOM.001.2500563 (Xplore article number 11519587 from Crossref link metadata)
- Source: https://api.crossref.org/works/10.1109/mcom.001.2500563 ; https://doi.org/10.1109/mcom.001.2500563 ; preprint arXiv https://arxiv.org/abs/2508.17778 (v2 listed Feb 2026)
- Mismatches: title and 7 authors match. Journal matches (IEEE Communications Magazine). Year 2026 matches.
- TODO (manual): open https://ieeexplore.ieee.org/document/11519587 and read the "Early Access" publication date; also check whether an issue has since been assigned.
```bibtex
@article{elkael2026agentran,
  author  = {Elkael, Maxime and D'Oro, Salvatore and Bonati, Leonardo and Polese, Michele and Lee, Yunseong and Furueda, Koichiro and Melodia, Tommaso},
  title   = {{AgentRAN}: An Agentic {AI} Architecture for Autonomous Control of Open {6G} Networks},
  journal = {IEEE Commun. Mag.},
  year    = {2026},
  note    = {Early access},
  doi     = {10.1109/MCOM.001.2500563}
}
```
Add `month = ...` only after the early-access date is verified on Xplore.

## 6. maxenti2026autoran
**Status: published.** IEEE Trans. Mobile Computing, vol. 25, no. 7, pp. 10112-10129, July 2026.
- DOI: 10.1109/TMC.2026.3656056
- Source: https://api.crossref.org/works/10.1109/tmc.2026.3656056 ; https://doi.org/10.1109/tmc.2026.3656056
- Mismatches: title and 7 authors match (Crossref capitalises title "Automated and Zero-Touch Open RAN Systems"). Year 2026 matches.
```bibtex
@article{maxenti2026autoran,
  author    = {Maxenti, Stefano and Shirkhani, Ravis and Elkael, Maxime and Bonati, Leonardo and D'Oro, Salvatore and Melodia, Tommaso and Polese, Michele},
  title     = {{AutoRAN}: Automated and Zero-Touch Open {RAN} Systems},
  journal   = {IEEE Trans. Mobile Comput.},
  volume    = {25},
  number    = {7},
  pages     = {10112--10129},
  month     = jul,
  year      = {2026},
  doi       = {10.1109/TMC.2026.3656056}
}
```

## 7. chatzimiltis2026agentic
**Status: early access (not independently confirmed on Xplore).** Crossref: no volume/issue, pages "1-9" (early-access placeholder); record created 2026-04-23, deposited 2026-04-27, last indexed 2026-08-18. IEEE early-access date: NOT verified.
- DOI: 10.1109/MCOMSTD.2026.3681685 (Xplore article number 11494171 from Crossref link metadata)
- Source: https://api.crossref.org/works/10.1109/mcomstd.2026.3681685 ; https://doi.org/10.1109/mcomstd.2026.3681685 ; preprint https://arxiv.org/abs/2512.12400 (v1, first posted ~13 Dec 2025; "submitted to IEEE")
- Mismatches: title and 5 authors match; year 2026 matches; journal name matches (IEEE Communications Standards Magazine).
- TODO (manual): https://ieeexplore.ieee.org/document/11494171 for the early-access date and any later issue assignment.
```bibtex
@article{chatzimiltis2026agentic,
  author  = {Chatzimiltis, Sotiris and Mashhadi, Mahdi Boloursaz and Shojafar, Mohammad and Debbah, M\'{e}rouane and Tafazolli, Rahim},
  title   = {Agentic {AI} for {6G}: A New Paradigm for Autonomous {RAN} Security Compliance},
  journal = {IEEE Commun. Stand. Mag.},
  year    = {2026},
  note    = {Early access},
  doi     = {10.1109/MCOMSTD.2026.3681685}
}
```

## 8. polese2026beyond
**Status: published.** IEEE Communications Magazine, vol. 64, no. 7, pp. 90-95, July 2026.
- DOI: 10.1109/MCOM.001.2500438
- Source: https://api.crossref.org/works/10.1109/mcom.001.2500438 ; https://doi.org/10.1109/mcom.001.2500438
- Mismatches: title and 5 authors match. Year 2026 matches.
```bibtex
@article{polese2026beyond,
  author    = {Polese, Michele and Mohamadi, Niloofar and D'Oro, Salvatore and Bonati, Leonardo and Melodia, Tommaso},
  title     = {Beyond Connectivity: An Open Architecture for {AI-RAN} Convergence in {6G}},
  journal   = {IEEE Commun. Mag.},
  volume    = {64},
  number    = {7},
  pages     = {90--95},
  month     = jul,
  year      = {2026},
  doi       = {10.1109/MCOM.001.2500438}
}
```

## 9. al2026ran
**Status: published.** IEEE Trans. Mobile Computing, vol. 25, no. 7, pp. 10876-10892, July 2026.
- DOI: 10.1109/TMC.2026.3665440
- Source: https://api.crossref.org/works/10.1109/tmc.2026.3665440 ; https://doi.org/10.1109/tmc.2026.3665440
- Mismatches: title matches (Crossref prints "O-RAN Xapps Conflict Prediction Using Graph Convolutional Networks"; bib's "xApps" is the correct technical spelling, keep it). 3 authors match (Al Shami, Yan, Fapi). Year 2026 matches.
```bibtex
@article{al2026ran,
  author    = {Al Shami, Maryam and Yan, Jun and Fapi, Emmanuel Thepie},
  title     = {{O-RAN} x{App}s Conflict Prediction Using Graph Convolutional Networks},
  journal   = {IEEE Trans. Mobile Comput.},
  volume    = {25},
  number    = {7},
  pages     = {10876--10892},
  month     = jul,
  year      = {2026},
  doi       = {10.1109/TMC.2026.3665440}
}
```

## 10. navidan2026toward
**Status: published as IEEE Network early access per Crossref (no vol/issue); the bib still cites the arXiv preprint.** Crossref: pages "1-9", record created 2026-06-23, last indexed 2026-06-24 (old index, so an issue may have been assigned since; check Xplore). arXiv 2602.14117: v1 15 Feb 2026, v2 22 Jun 2026, arXiv page now lists DOI 10.1109/MNET.2026.3701847 and comment "Accepted for publication in the IEEE Network magazine". IEEE early-access date: NOT verified.
- DOI: 10.1109/MNET.2026.3701847 (Xplore article number 11574930 from Crossref link metadata)
- Source: https://api.crossref.org/works/10.1109/mnet.2026.3701847 ; https://doi.org/10.1109/mnet.2026.3701847 ; https://arxiv.org/abs/2602.14117
- Mismatches: title and 8 authors match; year 2026 matches. Venue is wrong in the bib (arXiv instead of IEEE Network).
- TODO (manual): https://ieeexplore.ieee.org/document/11574930 for the early-access date / current issue.
```bibtex
@article{navidan2026toward,
  author  = {Navidan, Hojjat and Cheraghinia, Mohammad and Fontaine, Jaron and Seif, Mohamed and De Poorter, Eli and Poor, H. Vincent and Moerman, Ingrid and Shahid, Adnan},
  title   = {Toward Autonomous {O-RAN}: A Multi-Scale Agentic {AI} Framework for Real-Time Network Control and Management},
  journal = {IEEE Network},
  year    = {2026},
  note    = {Early access},
  doi     = {10.1109/MNET.2026.3701847}
}
```
If Xplore turns out to show an issue, replace note with volume/number/month/pages.

---
Caveats
- Conference entries (ICC) legitimately have no volume/issue; give month + pages + location + DOI. The ICC month is May 2026 (conference 24-28 May 2026; Crossref issued date 2026-05-24).
- The Crossref early-access pages "1-7"/"1-9" are placeholders, not final pagination; do not print them as page ranges for early-access items.
- I did not check publisher pages (ScienceDirect, IEEE Xplore) directly; all published metadata comes from Crossref (the DOI registrar, populated by the publishers) and was cross-checked with arXiv where relevant.
