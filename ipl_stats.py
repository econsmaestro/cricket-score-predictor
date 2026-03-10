"""
IPL Historical Statistics 2008-2024
Data sourced from ESPNcricinfo and verified IPL records
"""

IPL_BATTING_STATS = {
    "Virat Kohli": {"matches": 252, "innings": 244, "runs": 8004, "highest": 113, "avg": 37.24, "sr": 130.02, "fifties": 55, "hundreds": 8, "fours": 744, "sixes": 264},
    "Rohit Sharma": {"matches": 257, "innings": 253, "runs": 6628, "highest": 109, "avg": 29.34, "sr": 130.39, "fifties": 43, "hundreds": 2, "fours": 564, "sixes": 284},
    "Shikhar Dhawan": {"matches": 222, "innings": 220, "runs": 6769, "highest": 106, "avg": 35.08, "sr": 127.26, "fifties": 50, "hundreds": 2, "fours": 779, "sixes": 170},
    "David Warner": {"matches": 184, "innings": 183, "runs": 6565, "highest": 126, "avg": 41.22, "sr": 139.96, "fifties": 55, "hundreds": 4, "fours": 649, "sixes": 260},
    "MS Dhoni": {"matches": 264, "innings": 228, "runs": 5243, "highest": 84, "avg": 39.42, "sr": 135.16, "fifties": 24, "hundreds": 0, "fours": 368, "sixes": 247},
    "KL Rahul": {"matches": 118, "innings": 116, "runs": 4683, "highest": 132, "avg": 45.95, "sr": 134.61, "fifties": 37, "hundreds": 5, "fours": 430, "sixes": 153},
    "Suresh Raina": {"matches": 205, "innings": 193, "runs": 5528, "highest": 100, "avg": 32.51, "sr": 136.75, "fifties": 39, "hundreds": 1, "fours": 489, "sixes": 203},
    "Jos Buttler": {"matches": 107, "innings": 105, "runs": 3582, "highest": 124, "avg": 38.93, "sr": 149.95, "fifties": 22, "hundreds": 5, "fours": 314, "sixes": 188},
    "Faf du Plessis": {"matches": 131, "innings": 128, "runs": 3893, "highest": 96, "avg": 34.37, "sr": 131.50, "fifties": 28, "hundreds": 0, "fours": 388, "sixes": 123},
    "Suryakumar Yadav": {"matches": 161, "innings": 155, "runs": 3964, "highest": 103, "avg": 30.49, "sr": 147.44, "fifties": 22, "hundreds": 1, "fours": 361, "sixes": 192},
    "Rishabh Pant": {"matches": 111, "innings": 106, "runs": 3284, "highest": 128, "avg": 35.31, "sr": 148.77, "fifties": 20, "hundreds": 1, "fours": 270, "sixes": 152},
    "Andre Russell": {"matches": 121, "innings": 107, "runs": 2553, "highest": 88, "avg": 28.36, "sr": 177.88, "fifties": 13, "hundreds": 0, "fours": 163, "sixes": 221},
    "Sanju Samson": {"matches": 163, "innings": 157, "runs": 4399, "highest": 119, "avg": 30.76, "sr": 137.37, "fifties": 25, "hundreds": 3, "fours": 389, "sixes": 181},
    "Quinton de Kock": {"matches": 103, "innings": 102, "runs": 2991, "highest": 140, "avg": 31.82, "sr": 137.80, "fifties": 19, "hundreds": 3, "fours": 307, "sixes": 118},
    "Hardik Pandya": {"matches": 133, "innings": 118, "runs": 2649, "highest": 91, "avg": 27.60, "sr": 146.47, "fifties": 8, "hundreds": 0, "fours": 199, "sixes": 140},
    "Shubman Gill": {"matches": 89, "innings": 88, "runs": 2820, "highest": 129, "avg": 35.69, "sr": 132.88, "fifties": 19, "hundreds": 4, "fours": 269, "sixes": 93},
    "Ruturaj Gaikwad": {"matches": 76, "innings": 74, "runs": 2419, "highest": 108, "avg": 38.39, "sr": 130.49, "fifties": 18, "hundreds": 2, "fours": 252, "sixes": 70},
    "Yashasvi Jaiswal": {"matches": 41, "innings": 41, "runs": 1530, "highest": 124, "avg": 40.26, "sr": 163.64, "fifties": 11, "hundreds": 2, "fours": 153, "sixes": 75},
    "Nicholas Pooran": {"matches": 86, "innings": 76, "runs": 1769, "highest": 87, "avg": 26.80, "sr": 147.54, "fifties": 6, "hundreds": 0, "fours": 132, "sixes": 103},
    "Heinrich Klaasen": {"matches": 34, "innings": 32, "runs": 923, "highest": 104, "avg": 46.15, "sr": 171.39, "fifties": 5, "hundreds": 1, "fours": 65, "sixes": 67},
    "Travis Head": {"matches": 24, "innings": 24, "runs": 684, "highest": 102, "avg": 31.09, "sr": 191.55, "fifties": 5, "hundreds": 2, "fours": 66, "sixes": 55},
    "Glenn Maxwell": {"matches": 130, "innings": 117, "runs": 2505, "highest": 95, "avg": 24.80, "sr": 154.98, "fifties": 12, "hundreds": 0, "fours": 195, "sixes": 158},
    "Tilak Varma": {"matches": 43, "innings": 42, "runs": 1243, "highest": 84, "avg": 34.52, "sr": 148.22, "fifties": 7, "hundreds": 0, "fours": 114, "sixes": 54},
    "Rinku Singh": {"matches": 44, "innings": 40, "runs": 926, "highest": 67, "avg": 40.26, "sr": 158.66, "fifties": 5, "hundreds": 0, "fours": 77, "sixes": 49},
    "Abhishek Sharma": {"matches": 38, "innings": 38, "runs": 872, "highest": 100, "avg": 26.42, "sr": 167.69, "fifties": 6, "hundreds": 1, "fours": 79, "sixes": 62},
    "Ishan Kishan": {"matches": 105, "innings": 102, "runs": 2644, "highest": 99, "avg": 28.73, "sr": 136.58, "fifties": 15, "hundreds": 0, "fours": 252, "sixes": 110},
    "Ravindra Jadeja": {"matches": 240, "innings": 178, "runs": 2868, "highest": 62, "avg": 26.80, "sr": 127.89, "fifties": 5, "hundreds": 0, "fours": 235, "sixes": 97},
    "Devon Conway": {"matches": 35, "innings": 33, "runs": 905, "highest": 92, "avg": 30.16, "sr": 136.91, "fifties": 7, "hundreds": 0, "fours": 83, "sixes": 39},
    "Venkatesh Iyer": {"matches": 41, "innings": 39, "runs": 779, "highest": 67, "avg": 22.91, "sr": 129.18, "fifties": 4, "hundreds": 0, "fours": 74, "sixes": 32},
    "Prithvi Shaw": {"matches": 67, "innings": 67, "runs": 1605, "highest": 99, "avg": 24.31, "sr": 146.57, "fifties": 9, "hundreds": 0, "fours": 197, "sixes": 54},
    "Ajinkya Rahane": {"matches": 186, "innings": 178, "runs": 4583, "highest": 105, "avg": 28.64, "sr": 121.33, "fifties": 30, "hundreds": 2, "fours": 462, "sixes": 82},
    "Shreyas Iyer": {"matches": 115, "innings": 111, "runs": 3127, "highest": 96, "avg": 31.27, "sr": 127.93, "fifties": 20, "hundreds": 0, "fours": 284, "sixes": 99},
    "Devdutt Padikkal": {"matches": 62, "innings": 61, "runs": 1541, "highest": 101, "avg": 27.01, "sr": 126.10, "fifties": 10, "hundreds": 1, "fours": 156, "sixes": 45},
    "Mayank Agarwal": {"matches": 93, "innings": 90, "runs": 2325, "highest": 106, "avg": 27.94, "sr": 134.77, "fifties": 14, "hundreds": 1, "fours": 231, "sixes": 99},
}

IPL_BOWLING_STATS = {
    "Yuzvendra Chahal": {"matches": 157, "innings": 153, "overs": 555.2, "runs": 4327, "wickets": 205, "best": "5/40", "avg": 21.10, "econ": 7.79, "sr": 16.25, "4w": 4, "5w": 1},
    "Jasprit Bumrah": {"matches": 144, "innings": 143, "overs": 549.4, "runs": 4124, "wickets": 172, "best": "5/10", "avg": 23.97, "econ": 7.50, "sr": 19.17, "4w": 3, "5w": 1},
    "Dwayne Bravo": {"matches": 161, "innings": 158, "overs": 550.5, "runs": 4690, "wickets": 183, "best": "4/22", "avg": 25.62, "econ": 8.51, "sr": 18.05, "4w": 6, "5w": 0},
    "Bhuvneshwar Kumar": {"matches": 176, "innings": 173, "overs": 665.5, "runs": 4966, "wickets": 181, "best": "5/19", "avg": 27.43, "econ": 7.45, "sr": 22.06, "4w": 3, "5w": 1},
    "Sunil Narine": {"matches": 177, "innings": 175, "overs": 696.2, "runs": 4768, "wickets": 179, "best": "5/19", "avg": 26.63, "econ": 6.85, "sr": 23.34, "4w": 3, "5w": 1},
    "Amit Mishra": {"matches": 154, "innings": 151, "overs": 571.1, "runs": 4374, "wickets": 166, "best": "5/17", "avg": 26.35, "econ": 7.66, "sr": 20.64, "4w": 5, "5w": 2},
    "Piyush Chawla": {"matches": 165, "innings": 156, "overs": 571.5, "runs": 4536, "wickets": 157, "best": "4/17", "avg": 28.89, "econ": 7.93, "sr": 21.85, "4w": 3, "5w": 0},
    "Ravichandran Ashwin": {"matches": 199, "innings": 191, "overs": 717.1, "runs": 5121, "wickets": 189, "best": "4/34", "avg": 27.09, "econ": 7.14, "sr": 22.76, "4w": 5, "5w": 0},
    "Rashid Khan": {"matches": 108, "innings": 107, "overs": 422.4, "runs": 2777, "wickets": 139, "best": "4/24", "avg": 19.97, "econ": 6.57, "sr": 18.24, "4w": 6, "5w": 0},
    "Harshal Patel": {"matches": 103, "innings": 101, "overs": 366.3, "runs": 3175, "wickets": 136, "best": "5/27", "avg": 23.34, "econ": 8.66, "sr": 16.17, "4w": 2, "5w": 2},
    "Ravindra Jadeja": {"matches": 240, "innings": 191, "overs": 633.1, "runs": 4871, "wickets": 155, "best": "5/16", "avg": 31.42, "econ": 7.69, "sr": 24.51, "4w": 2, "5w": 1},
    "Mohammed Shami": {"matches": 97, "innings": 96, "overs": 355.1, "runs": 2929, "wickets": 106, "best": "4/11", "avg": 27.63, "econ": 8.24, "sr": 20.11, "4w": 3, "5w": 0},
    "Arshdeep Singh": {"matches": 71, "innings": 71, "overs": 253.4, "runs": 2265, "wickets": 86, "best": "5/32", "avg": 26.33, "econ": 8.93, "sr": 17.70, "4w": 1, "5w": 1},
    "Trent Boult": {"matches": 79, "innings": 78, "overs": 287.1, "runs": 2340, "wickets": 96, "best": "4/18", "avg": 24.37, "econ": 8.15, "sr": 17.94, "4w": 3, "5w": 0},
    "Kagiso Rabada": {"matches": 70, "innings": 69, "overs": 268.4, "runs": 2247, "wickets": 97, "best": "4/22", "avg": 23.16, "econ": 8.36, "sr": 16.62, "4w": 5, "5w": 0},
    "Pat Cummins": {"matches": 52, "innings": 51, "overs": 193.2, "runs": 1672, "wickets": 52, "best": "4/34", "avg": 32.15, "econ": 8.65, "sr": 22.31, "4w": 2, "5w": 0},
    "Mitchell Starc": {"matches": 23, "innings": 23, "overs": 89.5, "runs": 742, "wickets": 40, "best": "3/28", "avg": 18.55, "econ": 8.26, "sr": 13.47, "4w": 0, "5w": 0},
    "Varun Chakravarthy": {"matches": 68, "innings": 67, "overs": 260.1, "runs": 2029, "wickets": 92, "best": "5/17", "avg": 22.05, "econ": 7.80, "sr": 16.97, "4w": 3, "5w": 1},
    "Kuldeep Yadav": {"matches": 82, "innings": 80, "overs": 287.3, "runs": 2379, "wickets": 82, "best": "4/43", "avg": 29.01, "econ": 8.27, "sr": 21.03, "4w": 2, "5w": 0},
    "Axar Patel": {"matches": 89, "innings": 80, "overs": 291.2, "runs": 2128, "wickets": 69, "best": "3/21", "avg": 30.84, "econ": 7.30, "sr": 25.34, "4w": 0, "5w": 0},
    "Ravi Bishnoi": {"matches": 55, "innings": 54, "overs": 199.2, "runs": 1625, "wickets": 58, "best": "4/38", "avg": 28.01, "econ": 8.15, "sr": 20.62, "4w": 1, "5w": 0},
    "Matheesha Pathirana": {"matches": 25, "innings": 25, "overs": 85.3, "runs": 716, "wickets": 36, "best": "4/28", "avg": 19.88, "econ": 8.38, "sr": 14.25, "4w": 1, "5w": 0},
    "Mohammed Siraj": {"matches": 90, "innings": 88, "overs": 302.1, "runs": 2741, "wickets": 82, "best": "4/21", "avg": 33.42, "econ": 9.07, "sr": 22.11, "4w": 2, "5w": 0},
    "Deepak Chahar": {"matches": 101, "innings": 98, "overs": 318.1, "runs": 2568, "wickets": 91, "best": "4/13", "avg": 28.21, "econ": 8.07, "sr": 20.98, "4w": 2, "5w": 0},
    "Umesh Yadav": {"matches": 139, "innings": 135, "overs": 465.4, "runs": 4194, "wickets": 119, "best": "4/24", "avg": 35.24, "econ": 9.00, "sr": 23.49, "4w": 2, "5w": 0},
    "Thangarasu Natarajan": {"matches": 38, "innings": 38, "overs": 136.1, "runs": 1182, "wickets": 39, "best": "3/30", "avg": 30.30, "econ": 8.68, "sr": 20.94, "4w": 0, "5w": 0},
    "Sandeep Sharma": {"matches": 104, "innings": 103, "overs": 365.5, "runs": 2946, "wickets": 92, "best": "4/20", "avg": 32.02, "econ": 8.05, "sr": 23.85, "4w": 2, "5w": 0},
    "Anrich Nortje": {"matches": 42, "innings": 42, "overs": 148.3, "runs": 1249, "wickets": 46, "best": "4/10", "avg": 27.15, "econ": 8.41, "sr": 19.37, "4w": 2, "5w": 0},
}

VENUE_HISTORICAL_STATS = {
    # INDIA - IPL Venues
    "M. Chinnaswamy Stadium, Bengaluru": {"matches": 98, "avg_1st_innings": 178, "avg_2nd_innings": 162, "highest": 263, "lowest": 82, "pace_wickets_pct": 0.45, "spin_wickets_pct": 0.42, "country": "India"},
    "Wankhede Stadium, Mumbai": {"matches": 112, "avg_1st_innings": 172, "avg_2nd_innings": 160, "highest": 235, "lowest": 67, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.35, "country": "India"},
    "Eden Gardens, Kolkata": {"matches": 95, "avg_1st_innings": 168, "avg_2nd_innings": 155, "highest": 222, "lowest": 49, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40, "country": "India"},
    "Arun Jaitley Stadium, Delhi": {"matches": 78, "avg_1st_innings": 170, "avg_2nd_innings": 158, "highest": 231, "lowest": 73, "pace_wickets_pct": 0.50, "spin_wickets_pct": 0.38, "country": "India"},
    "MA Chidambaram Stadium, Chennai": {"matches": 102, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 246, "lowest": 79, "pace_wickets_pct": 0.38, "spin_wickets_pct": 0.50, "country": "India"},
    "Rajiv Gandhi International Stadium, Hyderabad": {"matches": 82, "avg_1st_innings": 165, "avg_2nd_innings": 158, "highest": 232, "lowest": 67, "pace_wickets_pct": 0.46, "spin_wickets_pct": 0.42, "country": "India"},
    "Sawai Mansingh Stadium, Jaipur": {"matches": 68, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 226, "lowest": 58, "pace_wickets_pct": 0.44, "spin_wickets_pct": 0.44, "country": "India"},
    "Punjab Cricket Association Stadium, Mohali": {"matches": 76, "avg_1st_innings": 174, "avg_2nd_innings": 162, "highest": 230, "lowest": 92, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "India"},
    "Narendra Modi Stadium, Ahmedabad": {"matches": 42, "avg_1st_innings": 168, "avg_2nd_innings": 160, "highest": 224, "lowest": 80, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40, "country": "India"},
    "DY Patil Stadium, Navi Mumbai": {"matches": 35, "avg_1st_innings": 170, "avg_2nd_innings": 158, "highest": 222, "lowest": 89, "pace_wickets_pct": 0.50, "spin_wickets_pct": 0.38, "country": "India"},
    "Brabourne Stadium, Mumbai": {"matches": 28, "avg_1st_innings": 168, "avg_2nd_innings": 155, "highest": 214, "lowest": 95, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "India"},
    "Maharashtra Cricket Association Stadium, Pune": {"matches": 45, "avg_1st_innings": 172, "avg_2nd_innings": 160, "highest": 228, "lowest": 88, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40, "country": "India"},
    "Himachal Pradesh Cricket Association Stadium, Dharamsala": {"matches": 18, "avg_1st_innings": 178, "avg_2nd_innings": 165, "highest": 226, "lowest": 105, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "India"},
    "Holkar Cricket Stadium, Indore": {"matches": 12, "avg_1st_innings": 175, "avg_2nd_innings": 162, "highest": 218, "lowest": 112, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "India"},
    "JSCA International Stadium Complex, Ranchi": {"matches": 10, "avg_1st_innings": 160, "avg_2nd_innings": 152, "highest": 205, "lowest": 98, "pace_wickets_pct": 0.45, "spin_wickets_pct": 0.43, "country": "India"},
    "Barabati Stadium, Cuttack": {"matches": 8, "avg_1st_innings": 162, "avg_2nd_innings": 155, "highest": 198, "lowest": 102, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40, "country": "India"},
    "Ekana Cricket Stadium, Lucknow": {"matches": 22, "avg_1st_innings": 168, "avg_2nd_innings": 160, "highest": 210, "lowest": 99, "pace_wickets_pct": 0.50, "spin_wickets_pct": 0.38, "country": "India"},
    
    # AUSTRALIA
    "Melbourne Cricket Ground, Melbourne": {"matches": 85, "avg_1st_innings": 168, "avg_2nd_innings": 158, "highest": 243, "lowest": 74, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "Australia"},
    "Sydney Cricket Ground, Sydney": {"matches": 72, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 221, "lowest": 82, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "Australia"},
    "Adelaide Oval, Adelaide": {"matches": 58, "avg_1st_innings": 172, "avg_2nd_innings": 162, "highest": 232, "lowest": 89, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "Australia"},
    "The Gabba, Brisbane": {"matches": 45, "avg_1st_innings": 170, "avg_2nd_innings": 158, "highest": 225, "lowest": 85, "pace_wickets_pct": 0.60, "spin_wickets_pct": 0.28, "country": "Australia"},
    "Perth Stadium, Perth": {"matches": 38, "avg_1st_innings": 175, "avg_2nd_innings": 165, "highest": 238, "lowest": 92, "pace_wickets_pct": 0.62, "spin_wickets_pct": 0.26, "country": "Australia"},
    "Optus Stadium, Perth": {"matches": 25, "avg_1st_innings": 178, "avg_2nd_innings": 168, "highest": 242, "lowest": 95, "pace_wickets_pct": 0.60, "spin_wickets_pct": 0.28, "country": "Australia"},
    "Bellerive Oval, Hobart": {"matches": 22, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 208, "lowest": 78, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "Australia"},
    "Manuka Oval, Canberra": {"matches": 18, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 212, "lowest": 88, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "Australia"},
    
    # ENGLAND
    "Lord's, London": {"matches": 65, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 226, "lowest": 85, "pace_wickets_pct": 0.62, "spin_wickets_pct": 0.26, "country": "England"},
    "The Oval, London": {"matches": 58, "avg_1st_innings": 168, "avg_2nd_innings": 158, "highest": 232, "lowest": 92, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "England"},
    "Edgbaston, Birmingham": {"matches": 52, "avg_1st_innings": 172, "avg_2nd_innings": 162, "highest": 238, "lowest": 88, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "England"},
    "Old Trafford, Manchester": {"matches": 48, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 222, "lowest": 82, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "England"},
    "Headingley, Leeds": {"matches": 42, "avg_1st_innings": 168, "avg_2nd_innings": 158, "highest": 228, "lowest": 78, "pace_wickets_pct": 0.60, "spin_wickets_pct": 0.28, "country": "England"},
    "Trent Bridge, Nottingham": {"matches": 45, "avg_1st_innings": 175, "avg_2nd_innings": 165, "highest": 245, "lowest": 95, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "England"},
    "The Rose Bowl, Southampton": {"matches": 38, "avg_1st_innings": 160, "avg_2nd_innings": 150, "highest": 215, "lowest": 88, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "England"},
    "Sophia Gardens, Cardiff": {"matches": 28, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 218, "lowest": 92, "pace_wickets_pct": 0.56, "spin_wickets_pct": 0.32, "country": "England"},
    "County Ground, Bristol": {"matches": 22, "avg_1st_innings": 168, "avg_2nd_innings": 158, "highest": 222, "lowest": 95, "pace_wickets_pct": 0.54, "spin_wickets_pct": 0.34, "country": "England"},
    
    # SOUTH AFRICA
    "Newlands, Cape Town": {"matches": 62, "avg_1st_innings": 168, "avg_2nd_innings": 158, "highest": 232, "lowest": 82, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "South Africa"},
    "Wanderers Stadium, Johannesburg": {"matches": 58, "avg_1st_innings": 178, "avg_2nd_innings": 168, "highest": 248, "lowest": 92, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "South Africa"},
    "SuperSport Park, Centurion": {"matches": 52, "avg_1st_innings": 175, "avg_2nd_innings": 165, "highest": 242, "lowest": 88, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "South Africa"},
    "Kingsmead, Durban": {"matches": 45, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 225, "lowest": 85, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "South Africa"},
    "St George's Park, Port Elizabeth": {"matches": 38, "avg_1st_innings": 160, "avg_2nd_innings": 150, "highest": 218, "lowest": 78, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "South Africa"},
    "Boland Park, Paarl": {"matches": 22, "avg_1st_innings": 172, "avg_2nd_innings": 162, "highest": 228, "lowest": 95, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "South Africa"},
    
    # NEW ZEALAND
    "Eden Park, Auckland": {"matches": 55, "avg_1st_innings": 168, "avg_2nd_innings": 158, "highest": 235, "lowest": 85, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "New Zealand"},
    "Hagley Oval, Christchurch": {"matches": 42, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 218, "lowest": 82, "pace_wickets_pct": 0.60, "spin_wickets_pct": 0.28, "country": "New Zealand"},
    "Basin Reserve, Wellington": {"matches": 38, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 212, "lowest": 78, "pace_wickets_pct": 0.62, "spin_wickets_pct": 0.26, "country": "New Zealand"},
    "Seddon Park, Hamilton": {"matches": 35, "avg_1st_innings": 172, "avg_2nd_innings": 162, "highest": 228, "lowest": 92, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "New Zealand"},
    "McLean Park, Napier": {"matches": 28, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 222, "lowest": 88, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "New Zealand"},
    "Bay Oval, Mount Maunganui": {"matches": 25, "avg_1st_innings": 175, "avg_2nd_innings": 165, "highest": 232, "lowest": 95, "pace_wickets_pct": 0.50, "spin_wickets_pct": 0.38, "country": "New Zealand"},
    
    # PAKISTAN
    "National Stadium, Karachi": {"matches": 48, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 218, "lowest": 78, "pace_wickets_pct": 0.42, "spin_wickets_pct": 0.46, "country": "Pakistan"},
    "Gaddafi Stadium, Lahore": {"matches": 52, "avg_1st_innings": 168, "avg_2nd_innings": 158, "highest": 228, "lowest": 85, "pace_wickets_pct": 0.45, "spin_wickets_pct": 0.43, "country": "Pakistan"},
    "Rawalpindi Cricket Stadium, Rawalpindi": {"matches": 38, "avg_1st_innings": 175, "avg_2nd_innings": 165, "highest": 235, "lowest": 92, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "Pakistan"},
    "Multan Cricket Stadium, Multan": {"matches": 28, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 222, "lowest": 88, "pace_wickets_pct": 0.40, "spin_wickets_pct": 0.48, "country": "Pakistan"},
    "Arbab Niaz Stadium, Peshawar": {"matches": 18, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 212, "lowest": 82, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40, "country": "Pakistan"},
    
    # SRI LANKA
    "R. Premadasa Stadium, Colombo": {"matches": 65, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 222, "lowest": 75, "pace_wickets_pct": 0.35, "spin_wickets_pct": 0.53, "country": "Sri Lanka"},
    "Pallekele International Cricket Stadium, Kandy": {"matches": 42, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 218, "lowest": 82, "pace_wickets_pct": 0.40, "spin_wickets_pct": 0.48, "country": "Sri Lanka"},
    "Galle International Stadium, Galle": {"matches": 38, "avg_1st_innings": 155, "avg_2nd_innings": 145, "highest": 212, "lowest": 78, "pace_wickets_pct": 0.32, "spin_wickets_pct": 0.56, "country": "Sri Lanka"},
    "Mahinda Rajapaksa International Stadium, Hambantota": {"matches": 25, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 225, "lowest": 88, "pace_wickets_pct": 0.45, "spin_wickets_pct": 0.43, "country": "Sri Lanka"},
    "Sinhalese Sports Club Ground, Colombo": {"matches": 28, "avg_1st_innings": 160, "avg_2nd_innings": 150, "highest": 218, "lowest": 85, "pace_wickets_pct": 0.38, "spin_wickets_pct": 0.50, "country": "Sri Lanka"},
    
    # BANGLADESH
    "Shere Bangla National Stadium, Dhaka": {"matches": 52, "avg_1st_innings": 155, "avg_2nd_innings": 145, "highest": 218, "lowest": 72, "pace_wickets_pct": 0.35, "spin_wickets_pct": 0.53, "country": "Bangladesh"},
    "Zahur Ahmed Chowdhury Stadium, Chattogram": {"matches": 38, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 215, "lowest": 78, "pace_wickets_pct": 0.38, "spin_wickets_pct": 0.50, "country": "Bangladesh"},
    "Sylhet International Cricket Stadium, Sylhet": {"matches": 22, "avg_1st_innings": 152, "avg_2nd_innings": 142, "highest": 208, "lowest": 75, "pace_wickets_pct": 0.40, "spin_wickets_pct": 0.48, "country": "Bangladesh"},
    
    # WEST INDIES
    "Kensington Oval, Bridgetown": {"matches": 48, "avg_1st_innings": 168, "avg_2nd_innings": 158, "highest": 232, "lowest": 85, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "West Indies"},
    "Queen's Park Oval, Port of Spain": {"matches": 45, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 225, "lowest": 82, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40, "country": "West Indies"},
    "Sabina Park, Kingston": {"matches": 38, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 218, "lowest": 78, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "West Indies"},
    "Providence Stadium, Guyana": {"matches": 32, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 212, "lowest": 75, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "West Indies"},
    "Sir Vivian Richards Stadium, Antigua": {"matches": 28, "avg_1st_innings": 172, "avg_2nd_innings": 162, "highest": 228, "lowest": 92, "pace_wickets_pct": 0.50, "spin_wickets_pct": 0.38, "country": "West Indies"},
    "Warner Park, Basseterre": {"matches": 22, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 218, "lowest": 88, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40, "country": "West Indies"},
    "Brian Lara Cricket Academy, Tarouba": {"matches": 18, "avg_1st_innings": 168, "avg_2nd_innings": 158, "highest": 222, "lowest": 95, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "West Indies"},
    
    # ZIMBABWE
    "Harare Sports Club, Harare": {"matches": 42, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 218, "lowest": 78, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "Zimbabwe"},
    "Queens Sports Club, Bulawayo": {"matches": 28, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 212, "lowest": 82, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "Zimbabwe"},
    
    # AFGHANISTAN
    "Kabul International Cricket Stadium, Kabul": {"matches": 25, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 215, "lowest": 82, "pace_wickets_pct": 0.38, "spin_wickets_pct": 0.50, "country": "Afghanistan"},
    "Sharjah Cricket Stadium, Sharjah": {"matches": 85, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 228, "lowest": 75, "pace_wickets_pct": 0.42, "spin_wickets_pct": 0.46, "country": "UAE"},
    
    # IRELAND
    "Malahide Cricket Club Ground, Dublin": {"matches": 28, "avg_1st_innings": 160, "avg_2nd_innings": 150, "highest": 218, "lowest": 85, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "Ireland"},
    "The Village, Dublin": {"matches": 18, "avg_1st_innings": 155, "avg_2nd_innings": 145, "highest": 205, "lowest": 82, "pace_wickets_pct": 0.60, "spin_wickets_pct": 0.28, "country": "Ireland"},
    "Bready Cricket Club, Bready": {"matches": 12, "avg_1st_innings": 152, "avg_2nd_innings": 142, "highest": 198, "lowest": 78, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "Ireland"},
    
    # UAE
    "Dubai International Cricket Stadium, Dubai": {"matches": 72, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 232, "lowest": 78, "pace_wickets_pct": 0.45, "spin_wickets_pct": 0.43, "country": "UAE"},
    "Sheikh Zayed Stadium, Abu Dhabi": {"matches": 58, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 225, "lowest": 82, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40, "country": "UAE"},
    
    # SCOTLAND
    "The Grange, Edinburgh": {"matches": 18, "avg_1st_innings": 155, "avg_2nd_innings": 145, "highest": 205, "lowest": 85, "pace_wickets_pct": 0.60, "spin_wickets_pct": 0.28, "country": "Scotland"},
    
    # NETHERLANDS
    "VRA Cricket Ground, Amstelveen": {"matches": 22, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 212, "lowest": 88, "pace_wickets_pct": 0.58, "spin_wickets_pct": 0.30, "country": "Netherlands"},
    
    # NEPAL
    "Tribhuvan University International Cricket Ground, Kirtipur": {"matches": 15, "avg_1st_innings": 152, "avg_2nd_innings": 142, "highest": 198, "lowest": 78, "pace_wickets_pct": 0.42, "spin_wickets_pct": 0.46, "country": "Nepal"},
    
    # NAMIBIA
    "Wanderers Cricket Ground, Windhoek": {"matches": 18, "avg_1st_innings": 165, "avg_2nd_innings": 155, "highest": 218, "lowest": 92, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "Namibia"},
    "Namibia Cricket Ground": {"matches": 12, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 210, "lowest": 88, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "Namibia"},
    
    # OMAN
    "Oman Cricket Academy Ground, Muscat": {"matches": 25, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 212, "lowest": 85, "pace_wickets_pct": 0.45, "spin_wickets_pct": 0.43, "country": "Oman"},
    "Al Amerat Cricket Ground, Muscat": {"matches": 28, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 218, "lowest": 82, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40, "country": "Oman"},
    
    # USA
    "Grand Prairie Stadium, Texas": {"matches": 12, "avg_1st_innings": 168, "avg_2nd_innings": 158, "highest": 222, "lowest": 95, "pace_wickets_pct": 0.50, "spin_wickets_pct": 0.38, "country": "USA"},
    "Nassau County International Cricket Stadium, New York": {"matches": 8, "avg_1st_innings": 145, "avg_2nd_innings": 135, "highest": 195, "lowest": 78, "pace_wickets_pct": 0.62, "spin_wickets_pct": 0.26, "country": "USA"},
    "Broward County Stadium, Florida": {"matches": 15, "avg_1st_innings": 172, "avg_2nd_innings": 162, "highest": 228, "lowest": 92, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40, "country": "USA"},
    
    # CANADA
    "Maple Leaf Cricket Club Ground, King City": {"matches": 12, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 208, "lowest": 88, "pace_wickets_pct": 0.55, "spin_wickets_pct": 0.33, "country": "Canada"},
    
    # HONG KONG
    "Tin Kwong Road Recreation Ground, Hong Kong": {"matches": 18, "avg_1st_innings": 155, "avg_2nd_innings": 145, "highest": 205, "lowest": 82, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40, "country": "Hong Kong"},
    
    # KENYA
    "Nairobi Gymkhana, Nairobi": {"matches": 15, "avg_1st_innings": 162, "avg_2nd_innings": 152, "highest": 212, "lowest": 85, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "Kenya"},
    
    # UGANDA
    "Lugogo Cricket Oval, Kampala": {"matches": 12, "avg_1st_innings": 158, "avg_2nd_innings": 148, "highest": 205, "lowest": 82, "pace_wickets_pct": 0.50, "spin_wickets_pct": 0.38, "country": "Uganda"},
    
    # PAPUA NEW GUINEA
    "Amini Park, Port Moresby": {"matches": 10, "avg_1st_innings": 155, "avg_2nd_innings": 145, "highest": 198, "lowest": 78, "pace_wickets_pct": 0.52, "spin_wickets_pct": 0.36, "country": "Papua New Guinea"},
}


VENUE_WEATHER_PROFILES = {
    "India": {"humidity": "high", "dew_factor": 0.8, "typical_conditions": "hot_humid", "swing_window": "first_6", "description": "Hot and humid; dew in evening games reduces swing and grip for spinners"},
    "Australia": {"humidity": "low", "dew_factor": 0.2, "typical_conditions": "dry_warm", "swing_window": "first_10", "description": "Dry conditions with good carry; bounce is a major factor"},
    "England": {"humidity": "high", "dew_factor": 0.4, "typical_conditions": "overcast_cool", "swing_window": "all_innings", "description": "Overcast skies assist swing bowling throughout the innings"},
    "South Africa": {"humidity": "medium", "dew_factor": 0.3, "typical_conditions": "dry_warm", "swing_window": "first_6", "description": "Good carry and bounce; altitude at Johannesburg adds pace"},
    "New Zealand": {"humidity": "high", "dew_factor": 0.5, "typical_conditions": "overcast_cool", "swing_window": "first_10", "description": "Green surfaces and overcast skies assist seam and swing"},
    "Pakistan": {"humidity": "medium", "dew_factor": 0.6, "typical_conditions": "hot_dry", "swing_window": "first_6", "description": "Dry heat with reverse swing later; dew under lights"},
    "Sri Lanka": {"humidity": "high", "dew_factor": 0.7, "typical_conditions": "hot_humid", "swing_window": "first_4", "description": "Tropical humidity; pitches deteriorate and assist spin significantly"},
    "Bangladesh": {"humidity": "high", "dew_factor": 0.8, "typical_conditions": "hot_humid", "swing_window": "first_4", "description": "Low, slow pitches with heavy dew in evening; spin dominant"},
    "West Indies": {"humidity": "high", "dew_factor": 0.5, "typical_conditions": "hot_humid", "swing_window": "first_6", "description": "Caribbean heat and humidity; variable bounce at some venues"},
    "Zimbabwe": {"humidity": "medium", "dew_factor": 0.3, "typical_conditions": "dry_warm", "swing_window": "first_6", "description": "Moderate conditions with decent pace and bounce"},
    "Afghanistan": {"humidity": "low", "dew_factor": 0.2, "typical_conditions": "hot_dry", "swing_window": "first_4", "description": "Dry, dusty pitches that assist spin; minimal swing"},
    "Ireland": {"humidity": "high", "dew_factor": 0.5, "typical_conditions": "overcast_cool", "swing_window": "all_innings", "description": "Green pitches with persistent cloud cover; swing throughout"},
    "UAE": {"humidity": "medium", "dew_factor": 0.7, "typical_conditions": "hot_dry", "swing_window": "first_6", "description": "Slow pitches that tire; heavy dew in evening; spin grips early"},
    "Scotland": {"humidity": "high", "dew_factor": 0.5, "typical_conditions": "overcast_cool", "swing_window": "all_innings", "description": "Cool and damp; swing-friendly conditions"},
    "Netherlands": {"humidity": "high", "dew_factor": 0.4, "typical_conditions": "overcast_cool", "swing_window": "all_innings", "description": "European conditions favouring seam movement"},
    "Nepal": {"humidity": "medium", "dew_factor": 0.4, "typical_conditions": "temperate", "swing_window": "first_6", "description": "Altitude effect at Kirtipur; spin plays a role"},
    "Namibia": {"humidity": "low", "dew_factor": 0.2, "typical_conditions": "dry_warm", "swing_window": "first_6", "description": "Dry, warm; good pace and bounce on harder surfaces"},
    "Oman": {"humidity": "medium", "dew_factor": 0.6, "typical_conditions": "hot_dry", "swing_window": "first_6", "description": "Hot and dry; slower pitches with dew factor in evening"},
    "USA": {"humidity": "medium", "dew_factor": 0.3, "typical_conditions": "varied", "swing_window": "first_6", "description": "Drop-in pitches with variable behavior; seam-friendly in NY"},
    "Canada": {"humidity": "medium", "dew_factor": 0.3, "typical_conditions": "temperate", "swing_window": "first_6", "description": "Temperate conditions; moderate swing early"},
    "Hong Kong": {"humidity": "high", "dew_factor": 0.6, "typical_conditions": "hot_humid", "swing_window": "first_4", "description": "Subtropical humidity; slow pitches"},
    "Kenya": {"humidity": "medium", "dew_factor": 0.3, "typical_conditions": "temperate", "swing_window": "first_6", "description": "Highland altitude; pleasant conditions with some swing"},
    "Uganda": {"humidity": "medium", "dew_factor": 0.3, "typical_conditions": "tropical", "swing_window": "first_6", "description": "Tropical; variable surfaces with some movement"},
    "Papua New Guinea": {"humidity": "high", "dew_factor": 0.5, "typical_conditions": "hot_humid", "swing_window": "first_4", "description": "Tropical heat; low and slow pitches"},
}


VENUE_PITCH_TEMPO = {
    "high_bounce": ["Melbourne Cricket Ground, Melbourne", "Perth Stadium, Perth", "Optus Stadium, Perth",
                     "The Gabba, Brisbane", "Wanderers Stadium, Johannesburg", "SuperSport Park, Centurion",
                     "WACA Ground, Perth", "Bellerive Oval, Hobart", "Nassau County International Cricket Stadium, New York"],
    "low_slow": ["MA Chidambaram Stadium, Chennai", "R. Premadasa Stadium, Colombo", "Galle International Stadium, Galle",
                 "Shere Bangla National Stadium, Dhaka", "National Stadium, Karachi", "Multan Cricket Stadium, Multan",
                 "Zahur Ahmed Chowdhury Stadium, Chattogram", "Pallekele International Cricket Stadium, Kandy",
                 "Sinhalese Sports Club Ground, Colombo", "Sylhet International Cricket Stadium, Sylhet",
                 "Dubai International Cricket Stadium, Dubai", "Sheikh Zayed Stadium, Abu Dhabi",
                 "Sharjah Cricket Stadium, Sharjah", "Kabul International Cricket Stadium, Kabul",
                 "Tribhuvan University International Cricket Ground, Kirtipur"],
    "true_pace": ["Lord's, London", "Headingley, Leeds", "Trent Bridge, Nottingham", "The Rose Bowl, Southampton",
                  "Old Trafford, Manchester", "Basin Reserve, Wellington", "Hagley Oval, Christchurch",
                  "Newlands, Cape Town", "Kingsmead, Durban", "Sabina Park, Kingston",
                  "Himachal Pradesh Cricket Association Stadium, Dharamsala", "Punjab Cricket Association Stadium, Mohali",
                  "Rawalpindi Cricket Stadium, Rawalpindi",
                  "Malahide Cricket Club Ground, Dublin", "The Grange, Edinburgh", "VRA Cricket Ground, Amstelveen"],
    "batting_road": ["M. Chinnaswamy Stadium, Bengaluru", "Wankhede Stadium, Mumbai",
                     "Trent Bridge, Nottingham", "Bay Oval, Mount Maunganui", "Seddon Park, Hamilton",
                     "Sir Vivian Richards Stadium, Antigua", "Adelaide Oval, Adelaide",
                     "Holkar Cricket Stadium, Indore", "Grand Prairie Stadium, Texas",
                     "Broward County Stadium, Florida", "Narendra Modi Stadium, Ahmedabad"],
}


VENUE_DISMISSAL_PATTERNS = {
    "pace": {
        "high_bounce": {"caught_boundary": 0.30, "caught_infield": 0.18, "bowled": 0.22, "lbw": 0.14, "run_out": 0.10, "stumped": 0.06},
        "low_slow": {"caught_boundary": 0.22, "caught_infield": 0.24, "bowled": 0.20, "lbw": 0.16, "run_out": 0.12, "stumped": 0.06},
        "true_pace": {"caught_boundary": 0.26, "caught_infield": 0.20, "bowled": 0.24, "lbw": 0.16, "run_out": 0.08, "stumped": 0.06},
        "batting_road": {"caught_boundary": 0.34, "caught_infield": 0.18, "bowled": 0.16, "lbw": 0.10, "run_out": 0.12, "stumped": 0.10},
        "default": {"caught_boundary": 0.28, "caught_infield": 0.22, "bowled": 0.20, "lbw": 0.13, "run_out": 0.10, "stumped": 0.07},
    },
    "spin": {
        "high_bounce": {"caught_boundary": 0.22, "caught_infield": 0.26, "bowled": 0.16, "lbw": 0.14, "run_out": 0.08, "stumped": 0.14},
        "low_slow": {"caught_boundary": 0.18, "caught_infield": 0.24, "bowled": 0.18, "lbw": 0.16, "run_out": 0.06, "stumped": 0.18},
        "true_pace": {"caught_boundary": 0.24, "caught_infield": 0.22, "bowled": 0.14, "lbw": 0.12, "run_out": 0.10, "stumped": 0.18},
        "batting_road": {"caught_boundary": 0.30, "caught_infield": 0.20, "bowled": 0.14, "lbw": 0.10, "run_out": 0.10, "stumped": 0.16},
        "default": {"caught_boundary": 0.24, "caught_infield": 0.22, "bowled": 0.16, "lbw": 0.14, "run_out": 0.08, "stumped": 0.16},
    }
}


def get_venue_weather(venue):
    stats = VENUE_HISTORICAL_STATS.get(venue, {})
    country = stats.get("country", "")
    return VENUE_WEATHER_PROFILES.get(country, {
        "humidity": "medium", "dew_factor": 0.3, "typical_conditions": "varied",
        "swing_window": "first_6", "description": "Standard conditions"
    })


def get_pitch_tempo(venue):
    for tempo, venues in VENUE_PITCH_TEMPO.items():
        if venue in venues:
            return tempo
    return "default"


def get_bowler_venue_dismissal_pattern(bowler_type, venue):
    tempo = get_pitch_tempo(venue)
    patterns = VENUE_DISMISSAL_PATTERNS.get(bowler_type, VENUE_DISMISSAL_PATTERNS["pace"])
    return patterns.get(tempo, patterns["default"]), tempo


BATTING_PHASE_PROFILES = {
    "powerplay_specialist": {"powerplay": 1.15, "consolidation": 0.90, "acceleration": 0.95, "finish": 0.85},
    "anchor": {"powerplay": 0.90, "consolidation": 1.10, "acceleration": 1.00, "finish": 0.85},
    "finisher": {"powerplay": 0.80, "consolidation": 0.95, "acceleration": 1.15, "finish": 1.30},
    "all_phase": {"powerplay": 1.05, "consolidation": 1.00, "acceleration": 1.05, "finish": 1.10},
    "default": {"powerplay": 1.00, "consolidation": 1.00, "acceleration": 1.00, "finish": 1.00},
}

PLAYER_BATTING_PHASE_TYPE = {
    "Rohit Sharma": "powerplay_specialist", "David Warner": "powerplay_specialist",
    "Shikhar Dhawan": "powerplay_specialist", "Jason Roy": "powerplay_specialist",
    "Prithvi Shaw": "powerplay_specialist", "Quinton de Kock": "powerplay_specialist",
    "Jos Buttler": "all_phase", "Babar Azam": "anchor",
    "Virat Kohli": "anchor", "KL Rahul": "anchor",
    "Shubman Gill": "anchor", "Ruturaj Gaikwad": "anchor",
    "Kane Williamson": "anchor", "Devon Conway": "anchor",
    "Shreyas Iyer": "anchor", "Faf du Plessis": "anchor",
    "MS Dhoni": "finisher", "Hardik Pandya": "finisher",
    "Andre Russell": "finisher", "Rinku Singh": "finisher",
    "Dinesh Karthik": "finisher", "Nicholas Pooran": "finisher",
    "Heinrich Klaasen": "finisher", "Marcus Stoinis": "finisher",
    "Glenn Maxwell": "finisher", "Liam Livingstone": "finisher",
    "Suryakumar Yadav": "all_phase", "Rishabh Pant": "all_phase",
    "Travis Head": "all_phase", "Tilak Varma": "all_phase",
    "Sanju Samson": "all_phase", "Abhishek Sharma": "powerplay_specialist",
    "Yashasvi Jaiswal": "powerplay_specialist", "Ishan Kishan": "powerplay_specialist",
}

BOWLING_PHASE_PROFILES = {
    "powerplay_specialist": {"powerplay": 0.85, "consolidation": 1.05, "acceleration": 1.10, "finish": 1.15},
    "middle_overs_spinner": {"powerplay": 1.10, "consolidation": 0.80, "acceleration": 0.90, "finish": 1.15},
    "death_specialist": {"powerplay": 1.10, "consolidation": 1.05, "acceleration": 0.90, "finish": 0.80},
    "all_phase": {"powerplay": 0.95, "consolidation": 0.95, "acceleration": 0.95, "finish": 0.95},
    "default": {"powerplay": 1.00, "consolidation": 1.00, "acceleration": 1.00, "finish": 1.00},
}

PLAYER_BOWLING_PHASE_TYPE = {
    "Jasprit Bumrah": "all_phase", "Mitchell Starc": "powerplay_specialist",
    "Trent Boult": "powerplay_specialist", "Bhuvneshwar Kumar": "powerplay_specialist",
    "Josh Hazlewood": "powerplay_specialist", "Shaheen Afridi": "powerplay_specialist",
    "Deepak Chahar": "powerplay_specialist", "Marco Jansen": "powerplay_specialist",
    "Yuzvendra Chahal": "middle_overs_spinner", "Rashid Khan": "middle_overs_spinner",
    "Ravichandran Ashwin": "middle_overs_spinner", "Sunil Narine": "middle_overs_spinner",
    "Ravindra Jadeja": "middle_overs_spinner", "Kuldeep Yadav": "middle_overs_spinner",
    "Axar Patel": "middle_overs_spinner", "Adil Rashid": "middle_overs_spinner",
    "Adam Zampa": "middle_overs_spinner", "Shadab Khan": "middle_overs_spinner",
    "Harshal Patel": "death_specialist", "Dwayne Bravo": "death_specialist",
    "Arshdeep Singh": "death_specialist", "Mohammed Shami": "death_specialist",
    "Kagiso Rabada": "death_specialist", "Pat Cummins": "death_specialist",
    "Anrich Nortje": "death_specialist", "Lockie Ferguson": "death_specialist",
    "Mohammed Siraj": "all_phase", "Jofra Archer": "all_phase",
}


def get_batting_phase_modifier(player_name: str, phase: str) -> float:
    phase_type = PLAYER_BATTING_PHASE_TYPE.get(player_name, "default")
    profile = BATTING_PHASE_PROFILES.get(phase_type, BATTING_PHASE_PROFILES["default"])
    return profile.get(phase, 1.0)


def get_bowling_phase_modifier(player_name: str, phase: str) -> float:
    phase_type = PLAYER_BOWLING_PHASE_TYPE.get(player_name, "default")
    profile = BOWLING_PHASE_PROFILES.get(phase_type, BOWLING_PHASE_PROFILES["default"])
    return profile.get(phase, 1.0)


PHASE_RUN_RATES = {
    "powerplay": {
        "overs": "1-6",
        "overs_range": (0, 6),
        "avg_runs_per_over": 8.5,
        "avg_wickets": 1.2,
        "boundary_rate": 0.24,
        "dot_ball_rate": 0.32,
        "six_rate": 0.08,
        "four_rate": 0.16,
        "wicket_per_over": 0.20,
        "fielders_outside_circle": 2,
        "strike_rate": 142,
        "avg_economy": 8.5,
        "risk_factor": 1.15,
        "description": "Attacking phase with only 2 fielders outside 30-yard circle"
    },
    "consolidation": {
        "overs": "7-14",
        "overs_range": (6, 14),
        "avg_runs_per_over": 7.4,
        "avg_wickets": 2.8,
        "boundary_rate": 0.13,
        "dot_ball_rate": 0.40,
        "six_rate": 0.04,
        "four_rate": 0.09,
        "wicket_per_over": 0.35,
        "fielders_outside_circle": 4,
        "strike_rate": 124,
        "avg_economy": 7.4,
        "risk_factor": 0.88,
        "description": "Rebuild/consolidation with 4 fielders outside the circle, spin-dominated"
    },
    "acceleration": {
        "overs": "15-17",
        "overs_range": (14, 17),
        "avg_runs_per_over": 9.8,
        "avg_wickets": 1.5,
        "boundary_rate": 0.22,
        "dot_ball_rate": 0.30,
        "six_rate": 0.09,
        "four_rate": 0.13,
        "wicket_per_over": 0.50,
        "fielders_outside_circle": 4,
        "strike_rate": 155,
        "avg_economy": 9.8,
        "risk_factor": 1.25,
        "description": "Transition phase where set batsmen begin attacking, 4 fielders outside"
    },
    "finish": {
        "overs": "18-20",
        "overs_range": (17, 20),
        "avg_runs_per_over": 11.8,
        "avg_wickets": 1.5,
        "boundary_rate": 0.30,
        "dot_ball_rate": 0.23,
        "six_rate": 0.14,
        "four_rate": 0.16,
        "wicket_per_over": 0.60,
        "fielders_outside_circle": 4,
        "strike_rate": 172,
        "avg_economy": 11.8,
        "risk_factor": 1.45,
        "description": "Final assault with maximum risk batting and death bowling yorkers"
    },
}

def get_current_phase(overs_completed: float) -> str:
    if overs_completed < 6:
        return "powerplay"
    elif overs_completed < 14:
        return "consolidation"
    elif overs_completed < 17:
        return "acceleration"
    else:
        return "finish"

def get_remaining_phase_overs(overs_completed: float) -> dict:
    remaining = {}
    
    if overs_completed < 6:
        remaining["powerplay"] = 6 - overs_completed
        remaining["consolidation"] = 8
        remaining["acceleration"] = 3
        remaining["finish"] = 3
    elif overs_completed < 14:
        remaining["consolidation"] = 14 - overs_completed
        remaining["acceleration"] = 3
        remaining["finish"] = 3
    elif overs_completed < 17:
        remaining["acceleration"] = 17 - overs_completed
        remaining["finish"] = 3
    else:
        remaining["finish"] = 20 - overs_completed
    
    return remaining

def calculate_phase_projected_runs(overs_completed: float, wickets: int, current_run_rate: float) -> dict:
    remaining = get_remaining_phase_overs(overs_completed)
    projections = {}
    
    for phase, overs_left in remaining.items():
        if overs_left > 0:
            phase_data = PHASE_RUN_RATES[phase]
            base_rpo = phase_data["avg_runs_per_over"]
            
            wicket_factor = max(0.5, 1 - (wickets * 0.08))
            
            if current_run_rate > 0:
                momentum_factor = min(1.2, max(0.8, current_run_rate / 8.0))
            else:
                momentum_factor = 1.0
            
            adjusted_rpo = base_rpo * wicket_factor * momentum_factor
            projections[phase] = {
                "overs": overs_left,
                "projected_runs": round(adjusted_rpo * overs_left),
                "projected_wickets": round(phase_data["wicket_per_over"] * overs_left * (1 / wicket_factor), 1),
                "boundary_expected": round(phase_data["boundary_rate"] * 6 * overs_left)
            }
    
    return projections

def get_comprehensive_batting_stats(name):
    return IPL_BATTING_STATS.get(name, None)

def get_comprehensive_bowling_stats(name):
    return IPL_BOWLING_STATS.get(name, None)

def get_venue_stats(venue):
    return VENUE_HISTORICAL_STATS.get(venue, {
        "matches": 50, "avg_1st_innings": 165, "avg_2nd_innings": 155, 
        "highest": 220, "lowest": 80, "pace_wickets_pct": 0.48, "spin_wickets_pct": 0.40
    })

def calculate_matchup_factor(batsman_name, bowler_name):
    bat_stats = IPL_BATTING_STATS.get(batsman_name)
    bowl_stats = IPL_BOWLING_STATS.get(bowler_name)
    
    if not bat_stats or not bowl_stats:
        return 1.0
    
    bat_sr_factor = bat_stats["sr"] / 130.0
    bowl_econ_factor = 8.0 / bowl_stats["econ"]
    
    return (bat_sr_factor + bowl_econ_factor) / 2

def predict_phase_score(current_over, wickets, venue):
    venue_stats = get_venue_stats(venue)
    phase = get_current_phase(current_over)
    phase_data = PHASE_RUN_RATES[phase]
    phase_end = phase_data["overs_range"][1]
    remaining_phase_overs = phase_end - current_over
    
    wicket_factor = max(0.5, 1 - (wickets * 0.08))
    
    expected_runs = phase_data["avg_runs_per_over"] * remaining_phase_overs * wicket_factor
    return int(expected_runs)
