import seaborn as sns
import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


medicare_part_d = pd.read_csv('data/Medicare_Pt_D_spending/merged/part_d_drug_2016_2024.csv')
print(medicare_part_d.head())

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