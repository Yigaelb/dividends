Write python script - upcoming_dividend_announcment_finder.py

Input:
will take csv file as input.
If no input is given will look for most recently updated csv file where the file name includes "Historical_Dividend_Annoucments"
Example input file: Historical_Dividend_Annoucments_ITel_Aviv_125_2022-05-06_to_2025-07-01.csv

Output
a csv file with all the companies which should announce dividends soon.Each row will have: Company Name, Company ticker, X dates for last year (multiple dates in a single cell), X dates for two years ago (multiple dates in a single cell), estimated dividend value estimated according to same time periood last year.

Logic
Only include companies which
Avarage dividend תשואה greater than 3%
Had X date in similer time as today (1 month forward 1 month back), 3 years running.
Did not annonce an X date 1 month forward and 1 month back from today.

Notes:
input CSV file is in hebrew

Itteration 2025-05-20 16:44
