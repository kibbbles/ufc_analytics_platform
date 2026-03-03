# Greco Scraper Reference

**Source:** https://github.com/Greco1899/scrape_ufc_stats
**File:** `scrape_ufc_stats_library.py`

This document describes exactly what Greco queries from UFCStats.com for each output table, the precise HTML selectors used, and how data is cleaned and structured. Use this as the specification for `live_scraper.py`.

---

## Overview: Scraping Flow

```
1. events listing page  →  event_details
2. each event detail page  →  fight_details  (visits each fight URL for BOUT)
3. each fight detail page  →  fight_results + fight_stats
4. fighter listing pages (A–Z)  →  fighter_details
5. each fighter profile page  →  fighter_tott
```

---

## Table 1: `event_details`

**Source URL:** `http://ufcstats.com/statistics/events/completed?page=all`
**Function:** `parse_event_details(soup)`

| Column | HTML Selector | Notes |
|--------|--------------|-------|
| `EVENT` | `<a class="b-link b-link_style_black">` → `.text.strip()` | Event name |
| `URL` | `<a class="b-link b-link_style_black">` → `['href']` | Event detail page URL |
| `DATE` | `<span class="b-statistics__date">` → `.text.strip()` | First element removed (upcoming event) |
| `LOCATION` | `<td class="b-statistics__table-col b-statistics__table-col_style_big-top-padding">` → `.text.strip()` | First element removed |

**Key detail:** The first element of both `DATE` and `LOCATION` lists is dropped because it represents the upcoming (not yet completed) event at the top of the page.

---

## Table 2: `fight_details`

**Source URL:** Each event detail page — `http://ufcstats.com/event-details/...`
**Functions:** `parse_fight_details(soup)`

| Column | HTML Selector | Notes |
|--------|--------------|-------|
| `EVENT` | `<h2 class="b-content__title">` → `.text.strip()` | On the event detail page |
| `BOUT` | For each fight URL: visit fight page → `<a class="b-link b-fight-details__person-link">` → `.text.strip()` → join as `"Fighter A vs. Fighter B"` | Requires N+1 requests |
| `URL` | `<tr class="b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click">` → `['data-link']` | Fight detail page URL, on `<tr>` attribute |

**Key detail:** Greco does **not** parse the event listing table cells at all for BOUT. He only uses `data-link` on `<tr>` tags to get fight URLs, then visits each individual fight page to extract fighter names via `b-fight-details__person-link`.

---

## Table 3: `fight_results`

**Source URL:** Each individual fight detail page — `http://ufcstats.com/fight-details/...`
**Functions:** `parse_fight_results(soup)` → `organise_fight_results(results, column_names)`

### Raw parsing (`parse_fight_results`)

| Field | HTML Selector | Raw value |
|-------|--------------|-----------|
| EVENT | `<h2 class="b-content__title">` → `.text` | Event name |
| Fighter A | `<a class="b-link b-fight-details__person-link">` [0] → `.text.strip()` | Fighter A name |
| Fighter B | `<a class="b-link b-fight-details__person-link">` [1] → `.text.strip()` | Fighter B name |
| Outcome A | `<div class="b-fight-details__person">` [0] → find_all `<i>` → `.text` | `"W"` / `"L"` / `"D"` / `"NC"` |
| Outcome B | `<div class="b-fight-details__person">` [1] → find_all `<i>` → `.text` | `"W"` / `"L"` / `"D"` / `"NC"` |
| WEIGHTCLASS | `<div class="b-fight-details__fight-head">` → `.text` | e.g. `"Flyweight Bout"` |
| METHOD | `<i class="b-fight-details__text-item_first">` → `.text` | e.g. `"Method: KO/TKO"` |
| ROUND | `<p class="b-fight-details__text">` [0] → `<i class="b-fight-details__text-item">` [0] → `.text.strip()` | e.g. `"Round: 2"` |
| TIME | same [1] | e.g. `"Time: 4:47"` |
| TIME FORMAT | same [2] | e.g. `"Time format: 3 Rnd (5-5-5)"` |
| REFEREE | same [3] | e.g. `"Referee: Herb Dean"` |
| DETAILS | `<p class="b-fight-details__text">` [1] → `.get_text()` | Finish description or scorecard |
| URL | Appended separately as `"URL:" + url` | |

**Cleaning applied:** `.replace('\n', '').replace('  ', '')` on every element.

### Organisation (`organise_fight_results`)

The raw list is restructured into a single-row DataFrame:

| Column | Derived from |
|--------|-------------|
| `EVENT` | `results[0]` |
| `BOUT` | `' vs. '.join(results[1:3])` — Fighter A + Fighter B |
| `OUTCOME` | `'/'.join(results[3:5])` — e.g. `"W/L"` or `"L/W"` |
| `WEIGHTCLASS` → `METHOD` → `ROUND` → `TIME` → `TIME FORMAT` → `REFEREE` → `DETAILS` → `URL` | `re.sub('^(.+?): ?', '', text)` strips the label prefix from `results[5:]` |

---

## Table 4: `fight_stats`

**Source URL:** Same individual fight detail page as `fight_results`
**Functions:** `parse_fight_stats(soup)` → `organise_fight_stats(stats)` → `convert_fight_stats_to_df(...)` → `combine_fighter_stats_dfs(...)`

### Step 1 — p-tag parity extraction (`parse_fight_stats`)

```python
for tag in soup.find_all('td', class_='b-fight-details__table-col'):
    for index, p_text in enumerate(tag.find_all('p')):
        if index % 2 == 0:
            fighter_a_stats.append(p_text.text.strip())
        else:
            fighter_b_stats.append(p_text.text.strip())
```

- Iterates **all** `<td class="b-fight-details__table-col">` on the page — this spans both stat tables (Totals and Significant Strikes) in one pass.
- Each `<td>` contains **two `<p>` tags**: `p[0]` = Fighter A, `p[1]` = Fighter B.
- Even index → Fighter A's flat list. Odd index → Fighter B's flat list.
- Both lists are returned separately.

The resulting flat list for each fighter is structured as:
```
[fighter_name, KD, SIG.STR., SIG.STR.%, TOTAL STR., TD, TD%, SUB.ATT, REV., CTRL,  ← All Rounds (Totals summary)
 fighter_name, KD, SIG.STR., SIG.STR.%, TOTAL STR., TD, TD%, SUB.ATT, REV., CTRL,  ← Round 1 Totals
 fighter_name, KD, SIG.STR., SIG.STR.%, TOTAL STR., TD, TD%, SUB.ATT, REV., CTRL,  ← Round 2 Totals
 ...
 fighter_name, SIG.STR., SIG.STR.%, HEAD, BODY, LEG, DISTANCE, CLINCH, GROUND,      ← All Rounds (Sig Strikes summary)
 fighter_name, SIG.STR., SIG.STR.%, HEAD, BODY, LEG, DISTANCE, CLINCH, GROUND,      ← Round 1 Sig Strikes
 fighter_name, SIG.STR., SIG.STR.%, HEAD, BODY, LEG, DISTANCE, CLINCH, GROUND,      ← Round 2 Sig Strikes
 ...]
```

### Step 2 — Group by fighter name (`organise_fight_stats`)

```python
for name, stats in itertools.groupby(stats_from_soup, lambda x: x == stats_from_soup[0]):
```

Groups the flat list into sublists, splitting wherever the fighter's name repeats. Each sublist is one row (one round, or the "All Rounds" summary).

Result structure:
```
[[All Rounds Totals], [Round 1 Totals], [Round 2 Totals], ...,
 [All Rounds Sig Strikes], [Round 1 Sig Strikes], [Round 2 Sig Strikes], ...]
```

### Step 3 — Convert to DataFrame (`convert_fight_stats_to_df`)

```python
number_of_rounds = int((len(clean_fighter_stats) - 2) / 2)
# -2 removes the two summary rows (one per table); /2 splits totals vs sig strikes halves

for round in range(number_of_rounds):
    totals_df.loc[...] = ['Round ' + str(round+1)] + clean_fighter_stats[round+1]
    sig_strikes_df.loc[...] = ['Round ' + str(round+1)] + clean_fighter_stats[round+1 + len/2]
```

- Summary rows (`clean_fighter_stats[0]` and `clean_fighter_stats[len/2]`) are **skipped** — only per-round data is kept.
- Totals columns: `ROUND, FIGHTER, KD, SIG.STR., SIG.STR. %, TOTAL STR., TD, TD %, SUB.ATT, REV., CTRL`
- Sig Strikes columns: `ROUND, FIGHTER, SIG.STR., SIG.STR. %, HEAD, BODY, LEG, DISTANCE, CLINCH, GROUND`
- Merged on inner join (both tables share `ROUND`, `FIGHTER`, `SIG.STR.`, `SIG.STR. %`).

### Step 4 — Add EVENT and BOUT (`combine_fighter_stats_dfs`)

- `EVENT`: `<h2 class="b-content__title">` → `.text.strip()`
- `BOUT`: `<a class="b-link b-fight-details__person-link">` → joined as `"Fighter A vs. Fighter B"`
- Both fighters' DataFrames are concatenated (stack rows).

### Final `fight_stats` columns

```
EVENT, BOUT, ROUND, FIGHTER, KD, SIG.STR., SIG.STR. %, TOTAL STR., TD, TD %,
SUB.ATT, REV., CTRL, HEAD, BODY, LEG, DISTANCE, CLINCH, GROUND
```

---

## Table 5: `fighter_details`

**Source URLs:** `http://ufcstats.com/statistics/fighters?char=a&page=all` through `...char=z&page=all` (26 pages)
**Functions:** `generate_alphabetical_urls()` → `parse_fighter_details(soup, column_names)`

| Column | HTML Selector | Notes |
|--------|--------------|-------|
| `FIRST` | `<a class="b-link b-link_style_black">` → `.text.strip()` → every 3rd starting at [0] | First name |
| `LAST` | same → every 3rd starting at [1] | Last name |
| `NICKNAME` | same → every 3rd starting at [2] | Nickname (blank if none) |
| `URL` | `<a class="b-link b-link_style_black">` → `['href']` → every 3rd starting at [0] | Fighter profile URL |

**Key detail:** Each fighter row on the page has three `<a class="b-link b-link_style_black">` tags (first, last, nickname). Results are zipped in sets of 3: `zip(names[0::3], names[1::3], names[2::3], urls[0::3])`.

---

## Table 6: `fighter_tott`

**Source URL:** Each fighter profile page — `http://ufcstats.com/fighter-details/...`
**Functions:** `parse_fighter_tott(soup)` → `organise_fighter_tott(tott, column_names, url)`

### Raw parsing (`parse_fighter_tott`)

| Field | HTML Selector | Raw value |
|-------|--------------|-----------|
| FIGHTER | `<span class="b-content__title-highlight">` → `.text` | e.g. `"Fighter:Jon Jones"` |
| HEIGHT | `<ul class="b-list__box-list">` [0] → `<i>` [0] → `.text.strip()` + `.next_sibling.strip()` | e.g. `"Height:6' 4\""` |
| WEIGHT | `<i>` [1] | e.g. `"Weight:205 lbs."` |
| REACH | `<i>` [2] | e.g. `"Reach:84\""` |
| STANCE | `<i>` [3] | e.g. `"Stance:Orthodox"` |
| DOB | `<i>` [4] | e.g. `"DOB:Jul 19, 1987"` |

**Cleaning:** `.replace('\n', '').replace('  ', '')` on all elements.

### Organisation (`organise_fighter_tott`)

Label prefix stripped with `re.sub('^(.+?): ?', '', text)` — e.g. `"Height:6' 4\""` → `"6' 4\""`.
URL appended as the final column.

### Final `fighter_tott` columns

```
FIGHTER, HEIGHT, WEIGHT, REACH, STANCE, DOB, URL
```

---

## Summary: Selectors by Table

| Table | Source Page | Key Selector |
|-------|------------|-------------|
| `event_details` | `/statistics/events/completed?page=all` | `<a class="b-link b-link_style_black">` for name+URL; `<span class="b-statistics__date">` for date |
| `fight_details` | `/event-details/...` | `<tr data-link="...">` for fight URLs; visits each fight page for `<a class="b-link b-fight-details__person-link">` |
| `fight_results` | `/fight-details/...` | `<div class="b-fight-details__fight-head">` for weight class; `<i class="b-fight-details__text-item_first">` for method; `<p class="b-fight-details__text">` for round/time |
| `fight_stats` | `/fight-details/...` (same page) | `<td class="b-fight-details__table-col">` → `<p>` tags with even/odd parity |
| `fighter_details` | `/statistics/fighters?char=X&page=all` | `<a class="b-link b-link_style_black">` in sets of 3 |
| `fighter_tott` | `/fighter-details/...` | `<ul class="b-list__box-list">[0]` → `<i>` tags + `.next_sibling` |

---

## Notes on `live_scraper.py` Alignment

The following methods already match Greco's approach:
- `_parse_stat_table_by_parity` — implements p-tag parity from `parse_fight_stats`
- `_parse_fighter_tott` — implements the fight-page TOTT block (different from Greco's full fighter profile TOTT)

The following should be updated to match Greco's approach:
- `scrape_event_fights` — should only extract `data-link` from `<tr>` + outcome from `b-flag` class; **all fight metadata should come from the individual fight detail page**
- Fight metadata (fighter names, weight class, method, round, time) should be extracted on the fight detail page using Greco's `parse_fight_results` selectors, not from the event listing table
