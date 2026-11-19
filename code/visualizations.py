import seaborn as sns
import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import us


# import datasets 
medicare_part_d = pd.read_csv('data/Medicare_Pt_D_spending/merged/part_d_drug_2016_2024.csv')
print(medicare_part_d.head())

obesity_by_state = pd.read_csv('data/2_2025-Obesity-by-state.csv')

sdud = pd.read_csv("data/state_drug_utilization/state_year_glp1_vs_all.csv")

glp1 = pd.read_csv("data/state_drug_utilization/glp1_state_product_year_type.csv")

all_drugs = pd.read_csv("data/state_drug_utilization/all_drugs_state_year_type.csv")

stocks = pd.read_csv(
    "data/master_glp_1_2017_2026/stock_prices.csv",
    parse_dates=["date"]
).sort_values("date")

folder = "data/NVO_financials_2021_2025"
workbooks = {
    2021: "Q4-2021-financial-workbook.xlsx",
    2022: "Q4-2022-financial-data.xlsx",
    2023: "q4-2023-financial-data.xlsx",
    2024: "Q4-2024-financial-workbook.xlsx",
    2025: "Q4-2025-financial-workbook.xlsx",
}

sales_rows = {
    2021: (81, [111], 132),  # Full-year block of Sales Q4
    2022: (13, [43, 45], 68),
    2023: (15, [45, 47], 70),
    2024: (15, [47, 49], 72),
    2025: (15, [47, 49], 72),
}


# -------------------------

# Ethan's code

# vis 1
# Total medicare spending on Ozempic over time

ozempic_total_spending_trend = duckdb.sql("""SELECT year, brand_name, total_spending
                                FROM medicare_part_d
                                WHERE brand_name = 'Ozempic'""").df()

sns.lineplot(ozempic_total_spending_trend, x='year', y = 'total_spending', marker = "o")

plt.xlabel('Year')
plt.ylabel('Total Spending (in tens of billions)')
plt.title('Total Medicare Spending on Ozempic from 2018 to 2022')
plt.show()

# vis 2
# Average spending per dose of Ozempic over time

ozempic_avg_spending_per_dosage_unit = duckdb.sql("""SELECT year, brand_name, avg_spending_per_dosage_unit
                                FROM medicare_part_d
                                WHERE brand_name = 'Ozempic'""").df()

sns.lineplot(ozempic_avg_spending_per_dosage_unit, x='year', y = 'avg_spending_per_dosage_unit', marker = "o")

plt.xlabel('Year')
plt.ylabel('Average Spending per Dose of Ozempic')
plt.title('Average Spending per Dose of Ozempic from 2018 to 2022')
plt.show()                    

# vis 3
# Total spending of all semaglutides over time

semaglutide_total_spending_trend = duckdb.sql("""SELECT year, generic_name, SUM(total_spending) AS sum_total_spending
                                FROM medicare_part_d
                                WHERE generic_name = 'Semaglutide'
                                GROUP BY year, generic_name
                                ORDER BY year""").df()

sns.lineplot(semaglutide_total_spending_trend, x='year', y = 'sum_total_spending', marker='o')

plt.xlabel('Year')
plt.ylabel('Total Spending (in billions)')
plt.title('Total Medicare Spending on Semaglutides from 2018 to 2022')
plt.show()        

# vis 4
# Average spending of one dose of semaglutide over time
# to-do: check for any outliers which may be affecting the average

semaglutide_avg_cost_per_dose_trend = duckdb.sql("""SELECT year, generic_name, MEAN(avg_spending_per_dosage_unit) AS avg_spending
                                FROM medicare_part_d
                                WHERE generic_name = 'Semaglutide'
                                GROUP BY year, generic_name
                                ORDER BY year""").df()

sns.lineplot(semaglutide_avg_cost_per_dose_trend, x='year', y = 'avg_spending', marker = "o")

plt.xlabel('Year')
plt.ylabel('Average Spending on One Dose of Semaglutide')
plt.title('Average Spending on One Dose of Semaglutide from 2018 to 2022')
plt.show()        

# vis 5
# GLP-1 spending as a percentage of total medicare part D spending

glp_1_percentage_total = duckdb.sql("""
    SELECT
        year,

        SUM(CASE
            WHEN generic_name IN (
                'Semaglutide',
                'Tirzepatide',
                'Dulaglutide',
                'Liraglutide',
                'Exenatide',
                'Lixisenatide'
            )
            THEN total_spending
            ELSE 0
        END) AS glp1_spending,

        SUM(total_spending) AS total_part_d_spending,

        100.0 * SUM(CASE
            WHEN generic_name IN (
                'Semaglutide',
                'Tirzepatide',
                'Dulaglutide',
                'Liraglutide',
                'Exenatide',
                'Lixisenatide'
            )
            THEN total_spending
            ELSE 0
        END) / SUM(total_spending) AS glp1_percentage

    FROM medicare_part_d
    GROUP BY year
    ORDER BY year
""").df()

sns.lineplot(glp_1_percentage_total, x='year', y='glp1_percentage', marker='o')

plt.xlabel('Year')
plt.ylabel('Share of Total Part D Spending (%)')
plt.title('GLP-1 Share of Medicare Part D Spending (2016–2024)')

plt.xticks(range(2016, 2025))
plt.ylim(bottom=0)
plt.grid(alpha=0.3)

plt.show()

# interactive obesity by state map

state_codes = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ",
    "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "Florida": "FL",
    "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI",
    "Wyoming": "WY", "District of Columbia": "DC"
}

obesity_by_state["Code"] =obesity_by_state["State"].map(state_codes)

obesity_by_state["Prevalence"] = pd.to_numeric(obesity_by_state["Prevalence"], errors="coerce")

fig = px.choropleth(
    obesity_by_state,
    locations="Code",
    locationmode="USA-states",
    color="Prevalence",
    scope="usa",
    hover_name="State",
    hover_data={
        "Code": False,
        "Prevalence": ":.1f",
        "95% CI": True
    },
    color_continuous_scale="Blues",
    range_color=(20, 42),
    labels={"Prevalence": "Obesity (%)"},
    title="Adult Obesity Prevalence by State (2025)"
)

fig.update_layout(
    height=600,
    margin=dict(l=0, r=0, t=50, b=0)
)

fig.show()
#fig.write_html("obesity_by_state.html")


# does obesity correlate with higher GLP-1 drug utilization?
# scatterplot

obesity_by_state["StateCode"] = obesity_by_state["State"].apply(
    lambda x: us.states.lookup(x).abbr if us.states.lookup(x) else None
)
obesity_by_state["Prevalence"] = pd.to_numeric(obesity_by_state["Prevalence"], errors="coerce")

valid_states = [s.abbr for s in us.states.STATES] + ["DC"]

sdud_2024 = sdud[
    (sdud["Year"] == 2024) &
    (sdud["State"].isin(valid_states))
].copy()

sdud_2024["GLP1_Share"] = (
    sdud_2024["glp1_prescriptions_observed"] /
    sdud_2024["all_prescriptions_observed"] * 100
)

df = obesity_by_state.merge(sdud_2024, left_on="StateCode", right_on="State")

df = df.dropna(subset=["Prevalence", "GLP1_Share"])

corr = df["Prevalence"].corr(df["GLP1_Share"])
print("Correlation:", corr)

fig = px.scatter(
    df,
    x="Prevalence",
    y="GLP1_Share",
    hover_name="State_x",
    hover_data={
        "Prevalence": True,
        "GLP1_Share": True,
        "glp1_prescriptions_observed": True,
        "all_prescriptions_observed": True
    },
    labels={
        "Prevalence": "Adult Obesity Prevalence (%)",
        "GLP1_Share": "GLP-1 Share of Medicaid Prescriptions (%)",
        "State_x": "State"
    },
    title=f"Obesity Prevalence vs. Medicaid GLP-1 Utilization Share (Correlation = {corr:.2f})",
    trendline="ols"
)

fig.update_traces(marker=dict(size=10))
fig.show()
#fig.write_html("obesity_prevalence_vs_glp_utilization.html")


# Novo Nordisk and Eli Lilly stock prices over time
# measures the closing price 


plt.figure(figsize=(10, 5))

for ticker, history in stocks.groupby("ticker"):
    plt.plot(history["date"], history["close"], label=ticker)

plt.title("Stock prices of Eli Lilly and Novo Nordisk")
plt.xlabel("Year")
plt.ylabel("Closing price (USD)")
plt.legend()
plt.show()

# Novo Nordisk revenue composition (sums to 100%) from 2021 to 2025
# Blue: Diabetes GLP-1
# Orange: Obesity GLP-1
# Green: All other drugs


brands = ["Ozempic", "Rybelsus", "Victoza"]

# U.S. sales column and Excel row numbers in brand order.
us_sales_rows = {
    2021: ("J", [77, 75, 79]),
    2022: ("J", [9, 7, 11]),
    2023: ("F", [9, 13, 11]),
    2024: ("F", [9, 13, 11]),
}

records = []
us_sales = {}
for year, filename in workbooks.items():
    sheet = "Sales Q4" if year == 2021 else "Sales - YTD"
    columns = "D"
    if year in us_sales_rows:
        us_column, rows = us_sales_rows[year]
        columns = f"D,{us_column}"

    sales_data = pd.read_excel(
        f"{folder}/{filename}", sheet_name=sheet, header=None, usecols=columns
    )
    sales = sales_data.iloc[:, 0]

    if year in us_sales_rows:
        us_sales[year] = sales_data.iloc[[row - 1 for row in rows], 1].tolist()

for year, filename in workbooks.items():
    sheet = "Sales Q4" if year == 2021 else "Sales - YTD"
    sales = pd.read_excel(
        f"{folder}/{filename}", sheet_name=sheet, header=None, usecols="D"
    ).iloc[:, 0]

    diabetes_row, obesity_rows, total_row = sales_rows[year]
    diabetes = sales.iloc[diabetes_row - 1]
    obesity = sum(sales.iloc[row - 1] for row in obesity_rows)
    total = sales.iloc[total_row - 1]

    records.append({
        "Year": year,
        "Diabetes GLP-1": 100 * diabetes / total,
        "Obesity GLP-1": 100 * obesity / total,
        "All other sales": 100 * (total - diabetes - obesity) / total,
    })

mix = pd.DataFrame(records).set_index("Year")

ax = mix.plot.bar(
    stacked=True, figsize=(9, 5), width=0.65, rot=0,
)

glp1_share = mix["Diabetes GLP-1"] + mix["Obesity GLP-1"]
for position, share in enumerate(glp1_share):
    ax.text(position, share + 1.5, f"{share:.1f}%",
            ha="center", va="bottom", fontweight="bold")

ax.set_title("Novo Nordisk annual revenue mix")
ax.set_xlabel("Fiscal year")
ax.set_ylabel("Share of company net sales (%)")
ax.set_ylim(0, 100)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15),
          ncol=3, frameon=False)

plt.show()

# US medicare claims vs company GLP-1 sales
# medicare claims are for that specific drug (ozempic, victoza, etc.)
# Index = 100 * (current year value/2021 value), so an index of 200 would be 2x and 50 would be 0.5x


part_d_claims = (
    medicare_part_d.assign(
        brand_name=medicare_part_d["brand_name"].replace({
            "Victoza 2-Pak": "Victoza",
            "Victoza 3-Pak": "Victoza",
        })
    )
    .groupby(["year", "brand_name"])["total_claims"]
    .sum()
    .unstack()
    .loc[list(us_sales), brands]
)

us_sales = pd.DataFrame.from_dict(us_sales, orient="index", columns=brands)

fig, axes = plt.subplots(1, 3, figsize=(11, 4), sharey=True)

for ax, brand in zip(axes, brands):
    ax.plot(part_d_claims.index, 100 * part_d_claims[brand] / part_d_claims.loc[2021, brand],
            marker="o", label="Medicare Part D claims")
    ax.plot(us_sales.index, 100 * us_sales[brand] / us_sales.loc[2021, brand],
            marker="s", label="Novo U.S. sales")
    ax.axhline(100, color="0.75", linewidth=1)
    ax.set_title(brand)
    ax.set_xticks(us_sales.index)

axes[0].set_ylabel("Index (2021 = 100)")
axes[-1].legend(frameon=False)
fig.suptitle("Medicare Claims and Novo Nordisk U.S. sales")
plt.show()

# ---------------------------------------------------