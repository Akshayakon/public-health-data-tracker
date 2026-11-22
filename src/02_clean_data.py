"""Clean and merge the two raw datasets into one country-by-day table."""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"

# Make country names match across the two files
NAME_FIX = {
    "US": "United States", "UK": "United Kingdom", "Mainland China": "China", "Czech Republic": "Czechia",
    "Republic of Ireland": "Ireland", "Burma": "Myanmar", "Ivory Coast": "Cote d'Ivoire",
    "Bahamas, The": "Bahamas", "The Bahamas": "Bahamas", "Gambia, The": "Gambia", "The Gambia": "Gambia",
    "East Timor": "Timor", "Timor-Leste": "Timor", "Macau": "Macao", "Cabo Verde": "Cape Verde",
    "Republic of the Congo": "Congo", "Congo (Brazzaville)": "Congo",
    "Congo (Kinshasa)": "Democratic Republic of Congo", "Faroe Islands": "Faeroe Islands",
    "West Bank and Gaza": "Palestine", "occupied Palestinian territory": "Palestine",
    "North Ireland": "Northern Ireland", "Vatican City": "Holy See",
}
NOT_COUNTRIES = ["Others", "Diamond Princess", "MS Zaandam", "('St. Martin',)", "Channel Islands"]
TOTALS = ["total_cases", "total_deaths", "total_recovered"]

# 1. Cases file: one row per province -> one row per country per day
c = pd.read_csv(RAW / "covid_19_data.csv")
c["location"] = c["Country/Region"].str.strip().replace(NAME_FIX)
c = c[~c["location"].isin(NOT_COUNTRIES)]
c["date"] = pd.to_datetime(c["ObservationDate"], format="%m/%d/%Y")
c = c.groupby(["location", "date"], as_index=False)[["Confirmed", "Deaths", "Recovered"]].sum()
c.columns = ["location", "date"] + TOTALS
c[TOTALS] = c.groupby("location")[TOTALS].cummax()          # totals never fall (provinces drop out)
last_case_date = c["date"].max()

# 2. Vaccination file
v = pd.read_csv(RAW / "country_vaccinations.csv", parse_dates=["date"])
v = v.rename(columns={"country": "location"})[["location", "date", "people_vaccinated",
    "people_fully_vaccinated", "people_vaccinated_per_hundred", "people_fully_vaccinated_per_hundred"]]
v["location"] = v["location"].str.strip().replace(NAME_FIX)
v = v.drop_duplicates(["location", "date"]).sort_values(["location", "date"])

# Population is in neither file: estimate it as vaccinated people / vaccinated per hundred
ok = v[v["people_vaccinated_per_hundred"] > 1]
pop = (ok["people_vaccinated"] / ok["people_vaccinated_per_hundred"] * 100).groupby(ok["location"]).median()
pop = pop.round(-3).rename("population")

# 3. Merge on a full daily calendar for countries present in both files
countries = sorted(set(c["location"]) & set(v["location"]))
dates = pd.date_range(min(c["date"].min(), v["date"].min()), max(c["date"].max(), v["date"].max()))
grid = pd.MultiIndex.from_product([countries, dates], names=["location", "date"]).to_frame(index=False)
df = grid.merge(c, how="left").merge(v, how="left").merge(pop, on="location").sort_values(["location", "date"])

# Fill gaps forward within each country; no case data exists after the file ends
fill = TOTALS + [col for col in v.columns if col.startswith("people")]
df[fill] = df.groupby("location")[fill].ffill()
df.loc[df["date"] > last_case_date, TOTALS] = np.nan
df = df[df["date"] >= c["date"].min()]

# 4. Daily numbers from running totals (negative = data correction -> 0)
for new, total in zip(["new_cases", "new_deaths", "new_recovered"], TOTALS):
    df[new] = df.groupby("location")[total].diff().clip(lower=0)

# 5. Metrics
df["new_cases_7d_avg"] = df.groupby("location")["new_cases"].transform(lambda s: s.rolling(7, min_periods=1).mean())
df["cases_per_100k_7d"] = df["new_cases_7d_avg"] / df["population"] * 100_000
df["pct_vaccinated"] = df["people_vaccinated_per_hundred"].clip(upper=100)
df["pct_fully_vaccinated"] = df["people_fully_vaccinated_per_hundred"].clip(upper=100)
df["death_rate_pct"] = df["total_deaths"] / df["total_cases"].where(df["total_cases"] > 0) * 100
df["recovery_rate_pct"] = df["total_recovered"] / df["total_cases"].where(df["total_cases"] > 0) * 100

# Some countries (e.g. US, UK) never reported recoveries: flag them so charts can skip them
final = df[df["date"] == last_case_date].set_index("location")
reported = final["total_recovered"] / final["total_cases"] > 0.2
df["recoveries_reported"] = df["location"].map(reported).fillna(False)
df["year"], df["month"] = df["date"].dt.year, df["date"].dt.to_period("M").dt.to_timestamp()

df = df.dropna(subset=["total_cases", "pct_fully_vaccinated"], how="all")
num = df.select_dtypes("number").columns
df[num] = df[num].round(2)
df.to_csv(OUT / "covid_clean.csv", index=False)

log = [f"Country-day rows from cases file: {len(c):,}", f"Countries in both files: {len(countries)}",
       f"Clean rows: {len(df):,}", f"Countries with usable recovery data: {int(reported.sum())} of {len(reported)}",
       f"Date range: {df['date'].min().date()} to {df['date'].max().date()}",
       f"Cases data ends: {last_case_date.date()} | Vaccination data ends: {v['date'].max().date()}"]
(OUT / "cleaning_log.txt").write_text("\n".join(log))
print("\n".join(log))
