import seaborn as sns
import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px

# import datasets 
medicare_part_d = pd.read_csv('data/Medicare_Pt_D_spending/merged/part_d_drug_2016_2024.csv')
print(medicare_part_d.head())
obesity_by_state = pd.read_csv('data/2_2025-Obesity-by-state.csv')


# -------------------------

# Ethan, 10/18

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

fig.write_html("obesity_by_state.html")
