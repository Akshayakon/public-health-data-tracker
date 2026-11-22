"""Build interactive Plotly charts (HTML) plus PNG screenshots from the cleaned data."""
import pandas as pd
import plotly.express as px
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "charts"
(OUT / "images").mkdir(exist_ok=True)
df = pd.read_csv(ROOT / "data" / "processed" / "covid_clean.csv", parse_dates=["date", "month"])

CASE_END = df.loc[df["total_cases"].notna(), "date"].max()                  # case data stops here
VAX_END = df.loc[df["pct_fully_vaccinated"].notna(), "date"].max()
end = df[df["date"] == CASE_END]
TOP = end.nlargest(10, "total_cases")["location"].tolist()                  # 10 biggest outbreaks
TOP_REC = end[end["recoveries_reported"]].nlargest(10, "total_cases")["location"].tolist()
top, top_cases = df[df["location"].isin(TOP)], df[df["location"].isin(TOP) & (df["date"] <= CASE_END)]


def save(fig, name, png_fig=None):
    fig.update_layout(template="plotly_white").write_html(OUT / f"{name}.html")
    (png_fig or fig).write_image(OUT / "images" / f"{name}.png", width=1200, height=650)


def line(data, y, name, title, label):
    fig = px.line(data, x="date", y=y, color="location", title=title, labels={y: label, "date": "", "location": "Country"})
    fig.update_layout(hovermode="x unified")
    save(fig, name)
    return fig


# 1-4: trends over time
line(top_cases, "new_cases_7d_avg", "1_cases_over_time", "New cases (7-day average), 10 countries with most cases", "Cases (7-day avg)")
line(top_cases, "cases_per_100k_7d", "2_cases_per_100k", "Cases per 100,000 people (7-day average)", "Cases per 100k")
rec = df[df["location"].isin(TOP_REC) & df["date"].between("2020-04-01", CASE_END)]
fig = line(rec, "recovery_rate_pct", "3_recovery_rate", "Recovery rate (% of total cases recovered)", "Recovery rate (%)")
fig.add_annotation(text="Countries that do not report recoveries (e.g. US, UK) are excluded",
                   xref="paper", yref="paper", x=0, y=-0.15, showarrow=False)
save(fig, "3_recovery_rate")
line(top.dropna(subset=["pct_fully_vaccinated"]), "pct_fully_vaccinated", "4_vaccination_progress",
     "Fully vaccinated population (%)", "% fully vaccinated")

# 5. Latest vaccination ranking, 20 most populous countries
latest = df[(df["date"] == VAX_END) & df["pct_fully_vaccinated"].notna()]
big = latest.nlargest(20, "population").sort_values("pct_fully_vaccinated")
save(px.bar(big, x="pct_fully_vaccinated", y="location", orientation="h",
            title=f"Fully vaccinated (%) as of {VAX_END:%d %b %Y}, 20 most populous countries",
            labels={"pct_fully_vaccinated": "% fully vaccinated", "location": ""}), "5_vaccination_snapshot")

# 6. Vaccination vs death rate, on the last day both datasets cover
snap = end[end["population"] > 5e6].dropna(subset=["pct_fully_vaccinated", "death_rate_pct"])
show = (snap["population"].rank(ascending=False) <= 5) | (snap["death_rate_pct"] > 4.5) | (snap["pct_fully_vaccinated"] > 35)
fig = px.scatter(snap.assign(label=snap["location"].where(show, "")), x="pct_fully_vaccinated", y="death_rate_pct",
                 size="population", hover_name="location", text="label", size_max=45,
                 title=f"Vaccination vs. death rate on {CASE_END:%d %b %Y} (bubble = population)",
                 labels={"pct_fully_vaccinated": "% fully vaccinated", "death_rate_pct": "Deaths per 100 cases"})
fig.update_traces(textposition="top center")
save(fig, "6_vaccination_vs_death_rate")

# 7. Animated monthly timeline over the period both datasets cover (PNG = last month)
m = df[df["date"].between("2020-12-01", CASE_END) & (df["population"] > 20e6)]
m = m.groupby(["location", "month"], as_index=False).agg(
    cases_per_100k=("cases_per_100k_7d", "mean"), vax=("pct_fully_vaccinated", "last"), population=("population", "first"))
m = m.dropna(subset=["vax", "cases_per_100k"]).sort_values(["month", "location"])
m["month"] = m["month"].dt.strftime("%Y-%m")
args = dict(x="vax", y="cases_per_100k", size="population", color="location", hover_name="location",
            size_max=45, range_x=[-3, 60], labels={"vax": "% fully vaccinated", "cases_per_100k": "Cases per 100k"})
fig = px.scatter(m, animation_frame="month", animation_group="location", range_y=[0, m["cases_per_100k"].max() * 1.1],
                 title="Monthly timeline: vaccination vs. case rate (countries over 20M people)", **args)
last = px.scatter(m[m["month"] == m["month"].max()], title=f"Vaccination vs. case rate, {m['month'].max()} (animated in the HTML chart)", **args)
fig.update_layout(showlegend=False), last.update_layout(showlegend=False)
save(fig, "7_animated_timeline", png_fig=last)

print("Charts saved to", OUT)
