# Power BI Guide (Easy Version)

You will build a 2-page dashboard from one file: `data/processed/covid_clean.csv`.
Time: about 45 minutes. You need Power BI Desktop (free).

| Page | What it shows |
|---|---|
| 1. Overview | totals, cases over time, top countries, map |
| 2. Vaccination | vaccination trend and country ranking |

---

## Step 1: Load the data

1. Open Power BI Desktop.
2. Click **Get data > Text/CSV** and choose `covid_clean.csv`.
3. Click **Load**.

Check that `date` shows a calendar icon in the **Data** pane on the right. If it doesn't, click the column > **Column tools > Data type > Date**.

> Some cells are blank on purpose. Case data ends in May 2021 and vaccination data starts in Dec 2020. Leave the blanks alone.

## Step 2: Make `location` work on maps

Click `location` in the Data pane > **Column tools > Data category > Country/Region**.

## Step 3: Add 6 measures

A measure is a small formula. Click **Home > New measure**, paste one formula, press Enter. Repeat for each.

**Why measures?** Columns like `total_cases` are running totals (they grow every day). If you add them up over all days the number is far too big. These formulas take only the latest day.

```DAX
Last Case Date = CALCULATE(MAX(covid_clean[date]), covid_clean[total_cases] <> BLANK())

Last Vax Date = CALCULATE(MAX(covid_clean[date]), covid_clean[pct_fully_vaccinated] <> BLANK())

Total Cases = CALCULATE(SUM(covid_clean[total_cases]), covid_clean[date] = [Last Case Date])

Total Deaths = CALCULATE(SUM(covid_clean[total_deaths]), covid_clean[date] = [Last Case Date])

Total Recovered = CALCULATE(SUM(covid_clean[total_recovered]), covid_clean[date] = [Last Case Date])

Avg % Vaccinated = CALCULATE(AVERAGE(covid_clean[pct_fully_vaccinated]), covid_clean[date] = [Last Vax Date])
```

---

## Step 4: Page 1 (Overview)

For every visual: click an empty spot on the page, click the visual icon in the **Visualizations** pane, then drag fields into the boxes shown.

| # | Visual | Drag these fields | Title |
|---|---|---|---|
| 1 | **Slicer** | `location` | Country |
| 2 | **Slicer** | `date` | Date range |
| 3 | **Card** | `Total Cases` | Total cases |
| 4 | **Card** | `Total Deaths` | Total deaths |
| 5 | **Card** | `Total Recovered` | Total recovered |
| 6 | **Line chart** | X-axis: `date`, Y-axis: `new_cases_7d_avg`, Legend: `location` | New cases (7-day average) |
| 7 | **Bar chart** | Y-axis: `location`, X-axis: `Total Cases` | Top 10 countries by cases |
| 8 | **Filled map** | Location: `location`, Tooltips: `Total Cases` | Cases by country |

**Two small fixes**
- **Slicer 1 (country):** in the slicer's Format settings, set **Style** to **Dropdown**.
- **Line chart:** show only the 10 biggest countries, otherwise there are too many lines.
  1. Open the **Filters** pane and drag `location` into *Filters on this visual*.
  2. Set **Filter type** to **Top N**, enter **10**, and drag `total_cases` into **By value**.
  3. Click **Apply filter**.
  4. Do the same for the bar chart (use `Total Cases` as the value).

**Layout idea**
```
+-------------------------------------------------+
| Title                    [Country v] [Date ---] |
| [Total cases] [Total deaths] [Total recovered]  |
| Cases over time (line)    | Top 10 (bar)        |
| Map                                             |
+-------------------------------------------------+
```

---

## Step 5: Page 2 (Vaccination)

Click **+** at the bottom to add a page, and name it `Vaccination`.

| # | Visual | Drag these fields | Title |
|---|---|---|---|
| 1 | **Card** | `Avg % Vaccinated` | Avg % fully vaccinated |
| 2 | **Line chart** | X-axis: `date`, Y-axis: `pct_fully_vaccinated`, Legend: `location` | Fully vaccinated (%) over time |
| 3 | **Bar chart** | Y-axis: `location`, X-axis: `Avg % Vaccinated` | Fully vaccinated (%), latest |

- **Line chart:** use Top N = 10 by `total_cases`, as in Step 4.
- **Bar chart:** Top N = 20 by `population` (set it to **Maximum**), then sort the bars from high to low using the **...** menu.

---

## Step 6: Finish

1. Select all visuals and use **Format > Align** to line them up.
2. Test it: pick one country in the slicer. Every visual should change. Clear it afterwards.
3. Save as `powerbi/Public_Health_Dashboard.pbix`.
4. Take screenshots of both pages and save them as `powerbi/overview.png` and `powerbi/vaccination.png`. The README already links to these names.

---

## Fixing common problems

| Problem | Fix |
|---|---|
| Numbers are huge | You used a `total_*` column directly. Use the measures from Step 3. |
| Too many lines | Add the Top N filter. |
| Map is empty | Do Step 2 again. |
| Line stops in May 2021 | That is normal: case data ends 29 May 2021. |
| US or UK recoveries are 0 | They never reported recoveries. |
