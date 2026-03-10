"""IPL player data sourced from ESPNcricinfo.

Contains squad rosters for all IPL franchises, career batting and bowling
statistics, and helper functions for player lookup and filtering.
All players are verified professional cricketers with records on cricinfo.
"""

IPL_PLAYERS = [
    # Chennai Super Kings
    {"name": "Ruturaj Gaikwad", "team": "CSK", "role": "Batter", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "MS Dhoni", "team": "CSK", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    {"name": "Ajinkya Rahane", "team": "CSK", "role": "Top order Batter", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    {"name": "Devon Conway", "team": "CSK", "role": "Wicketkeeper Batter", "batting_style": "Left hand", "bowling_style": "Right arm Medium"},
    {"name": "Moeen Ali", "team": "CSK", "role": "Batting Allrounder", "batting_style": "Left hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Shivam Dube", "team": "CSK", "role": "Allrounder", "batting_style": "Left hand", "bowling_style": "Right arm Medium"},
    {"name": "Ravindra Jadeja", "team": "CSK", "role": "Allrounder", "batting_style": "Left hand", "bowling_style": "Slow Left arm Orthodox"},
    {"name": "Daryl Mitchell", "team": "CSK", "role": "Batting Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    {"name": "Rachin Ravindra", "team": "CSK", "role": "Batting Allrounder", "batting_style": "Left hand", "bowling_style": "Slow Left arm Orthodox"},
    {"name": "Mitchell Santner", "team": "CSK", "role": "Bowling Allrounder", "batting_style": "Left hand", "bowling_style": "Slow Left arm Orthodox"},
    {"name": "Deepak Chahar", "team": "CSK", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    {"name": "Tushar Deshpande", "team": "CSK", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Right arm Medium"},
    {"name": "Matheesha Pathirana", "team": "CSK", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast"},
    {"name": "Mustafizur Rahman", "team": "CSK", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Left arm Medium fast"},
    {"name": "Shaik Rasheed", "team": "CSK", "role": "Batter", "batting_style": "Right hand", "bowling_style": "Legbreak"},
    {"name": "Sameer Rizvi", "team": "CSK", "role": "Batter", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    
    # Mumbai Indians
    {"name": "Rohit Sharma", "team": "MI", "role": "Top order Batter", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Ishan Kishan", "team": "MI", "role": "Wicketkeeper Batter", "batting_style": "Left hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Suryakumar Yadav", "team": "MI", "role": "Batter", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    {"name": "Hardik Pandya", "team": "MI", "role": "Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Medium fast"},
    {"name": "Tim David", "team": "MI", "role": "Middle order Batter", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Tilak Varma", "team": "MI", "role": "Batting Allrounder", "batting_style": "Left hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Jasprit Bumrah", "team": "MI", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast"},
    {"name": "Piyush Chawla", "team": "MI", "role": "Bowling Allrounder", "batting_style": "Left hand", "bowling_style": "Legbreak"},
    {"name": "Dewald Brevis", "team": "MI", "role": "Middle order Batter", "batting_style": "Right hand", "bowling_style": "Legbreak"},
    {"name": "Mohammad Nabi", "team": "MI", "role": "Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Romario Shepherd", "team": "MI", "role": "Bowling Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Nehal Wadhera", "team": "MI", "role": "Top order Batter", "batting_style": "Left hand", "bowling_style": "Legbreak"},
    {"name": "Gerald Coetzee", "team": "MI", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast"},
    {"name": "Akash Madhwal", "team": "MI", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Medium fast"},
    {"name": "Nuwan Thushara", "team": "MI", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    
    # Royal Challengers Bengaluru
    {"name": "Virat Kohli", "team": "RCB", "role": "Top order Batter", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    {"name": "Faf du Plessis", "team": "RCB", "role": "Middle order Batter", "batting_style": "Right hand", "bowling_style": "Legbreak"},
    {"name": "Glenn Maxwell", "team": "RCB", "role": "Batting Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Rajat Patidar", "team": "RCB", "role": "Top order Batter", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Dinesh Karthik", "team": "RCB", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Cameron Green", "team": "RCB", "role": "Batting Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Will Jacks", "team": "RCB", "role": "Batting Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Mahipal Lomror", "team": "RCB", "role": "Allrounder", "batting_style": "Left hand", "bowling_style": "Slow Left arm Orthodox"},
    {"name": "Tom Curran", "team": "RCB", "role": "Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Mohammed Siraj", "team": "RCB", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Akash Deep", "team": "RCB", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Lockie Ferguson", "team": "RCB", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast"},
    {"name": "Alzarri Joseph", "team": "RCB", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast"},
    {"name": "Karn Sharma", "team": "RCB", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Legbreak Googly"},
    {"name": "Yash Dayal", "team": "RCB", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Left arm Medium fast"},
    {"name": "Anuj Rawat", "team": "RCB", "role": "Wicketkeeper Batter", "batting_style": "Left hand", "bowling_style": None},
    
    # Kolkata Knight Riders
    {"name": "Shreyas Iyer", "team": "KKR", "role": "Top order Batter", "batting_style": "Right hand", "bowling_style": "Legbreak Googly"},
    {"name": "Nitish Rana", "team": "KKR", "role": "Batting Allrounder", "batting_style": "Left hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Venkatesh Iyer", "team": "KKR", "role": "Batting Allrounder", "batting_style": "Left hand", "bowling_style": "Right arm Medium"},
    {"name": "Andre Russell", "team": "KKR", "role": "Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Fast"},
    {"name": "Sunil Narine", "team": "KKR", "role": "Bowling Allrounder", "batting_style": "Left hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Rinku Singh", "team": "KKR", "role": "Middle order Batter", "batting_style": "Left hand", "bowling_style": None},
    {"name": "Phil Salt", "team": "KKR", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Rahmanullah Gurbaz", "team": "KKR", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Mitchell Starc", "team": "KKR", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Left arm Fast"},
    {"name": "Varun Chakravarthy", "team": "KKR", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Harshit Rana", "team": "KKR", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Vaibhav Arora", "team": "KKR", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Medium fast"},
    {"name": "Ramandeep Singh", "team": "KKR", "role": "Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Medium fast"},
    {"name": "Angkrish Raghuvanshi", "team": "KKR", "role": "Top order Batter", "batting_style": "Right hand", "bowling_style": None},
    
    # Rajasthan Royals
    {"name": "Sanju Samson", "team": "RR", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Jos Buttler", "team": "RR", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Yashasvi Jaiswal", "team": "RR", "role": "Top order Batter", "batting_style": "Left hand", "bowling_style": "Legbreak"},
    {"name": "Riyan Parag", "team": "RR", "role": "Middle order Batter", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Shimron Hetmyer", "team": "RR", "role": "Middle order Batter", "batting_style": "Left hand", "bowling_style": None},
    {"name": "Dhruv Jurel", "team": "RR", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Ravichandran Ashwin", "team": "RR", "role": "Bowling Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Trent Boult", "team": "RR", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Left arm Fast"},
    {"name": "Yuzvendra Chahal", "team": "RR", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Legbreak Googly"},
    {"name": "Sandeep Sharma", "team": "RR", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    {"name": "Nandre Burger", "team": "RR", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Left arm Fast medium"},
    {"name": "Avesh Khan", "team": "RR", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Kuldeep Sen", "team": "RR", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Rovman Powell", "team": "RR", "role": "Middle order Batter", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    
    # Sunrisers Hyderabad
    {"name": "Travis Head", "team": "SRH", "role": "Top order Batter", "batting_style": "Left hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Abhishek Sharma", "team": "SRH", "role": "Batting Allrounder", "batting_style": "Left hand", "bowling_style": "Slow Left arm Orthodox"},
    {"name": "Heinrich Klaasen", "team": "SRH", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Aiden Markram", "team": "SRH", "role": "Batting Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Rahul Tripathi", "team": "SRH", "role": "Top order Batter", "batting_style": "Right hand", "bowling_style": "Legbreak"},
    {"name": "Abdul Samad", "team": "SRH", "role": "Middle order Batter", "batting_style": "Right hand", "bowling_style": "Legbreak"},
    {"name": "Nitish Reddy", "team": "SRH", "role": "Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Medium fast"},
    {"name": "Pat Cummins", "team": "SRH", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast"},
    {"name": "Bhuvneshwar Kumar", "team": "SRH", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    {"name": "T Natarajan", "team": "SRH", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Left arm Medium fast"},
    {"name": "Jaydev Unadkat", "team": "SRH", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Left arm Medium fast"},
    {"name": "Mayank Markande", "team": "SRH", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Legbreak Googly"},
    {"name": "Shahbaz Ahmed", "team": "SRH", "role": "Allrounder", "batting_style": "Left hand", "bowling_style": "Slow Left arm Orthodox"},
    
    # Delhi Capitals
    {"name": "David Warner", "team": "DC", "role": "Top order Batter", "batting_style": "Left hand", "bowling_style": "Legbreak Googly"},
    {"name": "Rishabh Pant", "team": "DC", "role": "Wicketkeeper Batter", "batting_style": "Left hand", "bowling_style": None},
    {"name": "Prithvi Shaw", "team": "DC", "role": "Top order Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Axar Patel", "team": "DC", "role": "Bowling Allrounder", "batting_style": "Left hand", "bowling_style": "Slow Left arm Orthodox"},
    {"name": "Tristan Stubbs", "team": "DC", "role": "Middle order Batter", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Mitchell Marsh", "team": "DC", "role": "Batting Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Medium fast"},
    {"name": "Shai Hope", "team": "DC", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Anrich Nortje", "team": "DC", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast"},
    {"name": "Kuldeep Yadav", "team": "DC", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Left arm Chinaman"},
    {"name": "Mukesh Kumar", "team": "DC", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Medium fast"},
    {"name": "Khaleel Ahmed", "team": "DC", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Left arm Medium fast"},
    {"name": "Ishant Sharma", "team": "DC", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast"},
    {"name": "Lalit Yadav", "team": "DC", "role": "Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Abishek Porel", "team": "DC", "role": "Wicketkeeper Batter", "batting_style": "Left hand", "bowling_style": None},
    {"name": "Sumit Kumar", "team": "DC", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    
    # Punjab Kings
    {"name": "Shikhar Dhawan", "team": "PBKS", "role": "Top order Batter", "batting_style": "Left hand", "bowling_style": None},
    {"name": "Jonny Bairstow", "team": "PBKS", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Liam Livingstone", "team": "PBKS", "role": "Batting Allrounder", "batting_style": "Right hand", "bowling_style": "Legbreak"},
    {"name": "Sam Curran", "team": "PBKS", "role": "Allrounder", "batting_style": "Left hand", "bowling_style": "Left arm Medium fast"},
    {"name": "Jitesh Sharma", "team": "PBKS", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Prabhsimran Singh", "team": "PBKS", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Shashank Singh", "team": "PBKS", "role": "Middle order Batter", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    {"name": "Kagiso Rabada", "team": "PBKS", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Right arm Fast"},
    {"name": "Arshdeep Singh", "team": "PBKS", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Left arm Medium fast"},
    {"name": "Rahul Chahar", "team": "PBKS", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Legbreak Googly"},
    {"name": "Harshal Patel", "team": "PBKS", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    {"name": "Nathan Ellis", "team": "PBKS", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Rishi Dhawan", "team": "PBKS", "role": "Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Medium fast"},
    {"name": "Harpreet Brar", "team": "PBKS", "role": "Allrounder", "batting_style": "Left hand", "bowling_style": "Slow Left arm Orthodox"},
    {"name": "Chris Woakes", "team": "PBKS", "role": "Bowling Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    
    # Lucknow Super Giants
    {"name": "KL Rahul", "team": "LSG", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Quinton de Kock", "team": "LSG", "role": "Wicketkeeper Batter", "batting_style": "Left hand", "bowling_style": None},
    {"name": "Nicholas Pooran", "team": "LSG", "role": "Wicketkeeper Batter", "batting_style": "Left hand", "bowling_style": None},
    {"name": "Marcus Stoinis", "team": "LSG", "role": "Batting Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Medium fast"},
    {"name": "Ayush Badoni", "team": "LSG", "role": "Middle order Batter", "batting_style": "Right hand", "bowling_style": "Legbreak Googly"},
    {"name": "Deepak Hooda", "team": "LSG", "role": "Batting Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Krunal Pandya", "team": "LSG", "role": "Bowling Allrounder", "batting_style": "Left hand", "bowling_style": "Slow Left arm Orthodox"},
    {"name": "Mark Wood", "team": "LSG", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast"},
    {"name": "Ravi Bishnoi", "team": "LSG", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Legbreak Googly"},
    {"name": "Naveen-ul-Haq", "team": "LSG", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Yash Thakur", "team": "LSG", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Medium fast"},
    {"name": "Mohsin Khan", "team": "LSG", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Left arm Fast medium"},
    {"name": "Amit Mishra", "team": "LSG", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Legbreak Googly"},
    {"name": "Devdutt Padikkal", "team": "LSG", "role": "Top order Batter", "batting_style": "Left hand", "bowling_style": None},
    
    # Gujarat Titans
    {"name": "Shubman Gill", "team": "GT", "role": "Top order Batter", "batting_style": "Right hand", "bowling_style": "Legbreak"},
    {"name": "Wriddhiman Saha", "team": "GT", "role": "Wicketkeeper Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "David Miller", "team": "GT", "role": "Middle order Batter", "batting_style": "Left hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Vijay Shankar", "team": "GT", "role": "Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Medium"},
    {"name": "Rahul Tewatia", "team": "GT", "role": "Allrounder", "batting_style": "Left hand", "bowling_style": "Legbreak Googly"},
    {"name": "Rashid Khan", "team": "GT", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Legbreak Googly"},
    {"name": "Mohammed Shami", "team": "GT", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Noor Ahmad", "team": "GT", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Left arm Chinaman"},
    {"name": "Umesh Yadav", "team": "GT", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Azmatullah Omarzai", "team": "GT", "role": "Allrounder", "batting_style": "Right hand", "bowling_style": "Right arm Medium fast"},
    {"name": "Darshan Nalkande", "team": "GT", "role": "Bowler", "batting_style": "Right hand", "bowling_style": "Right arm Fast medium"},
    {"name": "Sai Sudharsan", "team": "GT", "role": "Middle order Batter", "batting_style": "Left hand", "bowling_style": None},
    {"name": "Matthew Wade", "team": "GT", "role": "Wicketkeeper Batter", "batting_style": "Left hand", "bowling_style": None},
    {"name": "Kane Williamson", "team": "GT", "role": "Top order Batter", "batting_style": "Right hand", "bowling_style": "Right arm Offbreak"},
    {"name": "Shahrukh Khan", "team": "GT", "role": "Middle order Batter", "batting_style": "Right hand", "bowling_style": None},
    {"name": "Spencer Johnson", "team": "GT", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Left arm Fast"},
    {"name": "Josh Little", "team": "GT", "role": "Bowler", "batting_style": "Left hand", "bowling_style": "Left arm Fast medium"},
]

IPL_TEAMS = {
    "CSK": "Chennai Super Kings",
    "MI": "Mumbai Indians", 
    "RCB": "Royal Challengers Bengaluru",
    "KKR": "Kolkata Knight Riders",
    "RR": "Rajasthan Royals",
    "SRH": "Sunrisers Hyderabad",
    "DC": "Delhi Capitals",
    "PBKS": "Punjab Kings",
    "LSG": "Lucknow Super Giants",
    "GT": "Gujarat Titans"
}

def get_all_players():
    """Return the full list of IPL player dicts."""
    return IPL_PLAYERS

def get_batsmen():
    """Return players whose role includes 'Batter' or 'Allrounder'."""
    return [p for p in IPL_PLAYERS if "Batter" in p["role"] or "Allrounder" in p["role"]]

def get_bowlers():
    """Return players whose role includes 'Bowler' or 'Allrounder'."""
    return [p for p in IPL_PLAYERS if "Bowler" in p["role"] or "Allrounder" in p["role"]]

def get_player_by_name(name):
    """Look up a player by exact name (case-insensitive). Returns None if not found."""
    for player in IPL_PLAYERS:
        if player["name"].lower() == name.lower():
            return player
    return None

def search_players(query):
    """Return players whose name contains the query substring (case-insensitive)."""
    query = query.lower()
    return [p for p in IPL_PLAYERS if query in p["name"].lower()]

PLAYER_CAREER_STATS = {
    "Virat Kohli": {"matches": 237, "runs": 7263, "avg": 37.24, "sr": 130.02, "fifties": 50, "hundreds": 7, "balls_faced": 5585},
    "Rohit Sharma": {"matches": 243, "runs": 6211, "avg": 29.95, "sr": 130.39, "fifties": 42, "hundreds": 2, "balls_faced": 4764},
    "MS Dhoni": {"matches": 250, "runs": 5243, "avg": 39.42, "sr": 135.16, "fifties": 24, "hundreds": 0, "balls_faced": 3879},
    "Suryakumar Yadav": {"matches": 143, "runs": 3375, "avg": 31.54, "sr": 147.44, "fifties": 20, "hundreds": 1, "balls_faced": 2289},
    "Faf du Plessis": {"matches": 117, "runs": 3403, "avg": 34.37, "sr": 131.50, "fifties": 25, "hundreds": 1, "balls_faced": 2588},
    "Jos Buttler": {"matches": 89, "runs": 2831, "avg": 38.26, "sr": 150.00, "fifties": 18, "hundreds": 4, "balls_faced": 1887},
    "Shikhar Dhawan": {"matches": 206, "runs": 6617, "avg": 35.19, "sr": 127.36, "fifties": 47, "hundreds": 2, "balls_faced": 5195},
    "KL Rahul": {"matches": 109, "runs": 4683, "avg": 45.46, "sr": 134.61, "fifties": 37, "hundreds": 4, "balls_faced": 3478},
    "David Warner": {"matches": 176, "runs": 6565, "avg": 41.54, "sr": 139.96, "fifties": 55, "hundreds": 4, "balls_faced": 4690},
    "Rishabh Pant": {"matches": 98, "runs": 2838, "avg": 35.02, "sr": 148.77, "fifties": 18, "hundreds": 0, "balls_faced": 1907},
    "Glenn Maxwell": {"matches": 122, "runs": 2377, "avg": 23.77, "sr": 157.44, "fifties": 12, "hundreds": 0, "balls_faced": 1510},
    "Hardik Pandya": {"matches": 120, "runs": 2335, "avg": 27.14, "sr": 146.47, "fifties": 6, "hundreds": 0, "balls_faced": 1594},
    "Ravindra Jadeja": {"matches": 226, "runs": 2692, "avg": 27.19, "sr": 127.92, "fifties": 5, "hundreds": 0, "balls_faced": 2104},
    "Ruturaj Gaikwad": {"matches": 67, "runs": 2302, "avg": 38.36, "sr": 130.41, "fifties": 17, "hundreds": 1, "balls_faced": 1766},
    "Shubman Gill": {"matches": 76, "runs": 2383, "avg": 35.56, "sr": 128.76, "fifties": 18, "hundreds": 3, "balls_faced": 1851},
    "Yashasvi Jaiswal": {"matches": 32, "runs": 1113, "avg": 37.10, "sr": 161.13, "fifties": 10, "hundreds": 0, "balls_faced": 691},
    "Sanju Samson": {"matches": 150, "runs": 4005, "avg": 29.67, "sr": 135.89, "fifties": 21, "hundreds": 1, "balls_faced": 2947},
    "Ishan Kishan": {"matches": 89, "runs": 2325, "avg": 28.35, "sr": 136.26, "fifties": 13, "hundreds": 0, "balls_faced": 1706},
    "Quinton de Kock": {"matches": 92, "runs": 2573, "avg": 29.91, "sr": 137.80, "fifties": 16, "hundreds": 2, "balls_faced": 1867},
    "Nicholas Pooran": {"matches": 75, "runs": 1440, "avg": 25.71, "sr": 147.54, "fifties": 5, "hundreds": 1, "balls_faced": 976},
    "Heinrich Klaasen": {"matches": 27, "runs": 738, "avg": 46.12, "sr": 171.39, "fifties": 5, "hundreds": 0, "balls_faced": 431},
    "Tilak Varma": {"matches": 34, "runs": 944, "avg": 32.55, "sr": 145.37, "fifties": 6, "hundreds": 0, "balls_faced": 649},
    "Rinku Singh": {"matches": 36, "runs": 759, "avg": 42.16, "sr": 155.10, "fifties": 4, "hundreds": 0, "balls_faced": 489},
    "Andre Russell": {"matches": 115, "runs": 2367, "avg": 28.51, "sr": 177.17, "fifties": 11, "hundreds": 0, "balls_faced": 1336},
    "Travis Head": {"matches": 21, "runs": 567, "avg": 31.50, "sr": 191.55, "fifties": 4, "hundreds": 1, "balls_faced": 296},
    "Abhishek Sharma": {"matches": 31, "runs": 748, "avg": 28.76, "sr": 167.26, "fifties": 5, "hundreds": 1, "balls_faced": 447},
}

BOWLER_CAREER_STATS = {
    "Jasprit Bumrah": {"matches": 133, "wickets": 163, "avg": 23.67, "econ": 7.39, "overs": 521.2, "best": "5/10"},
    "Yuzvendra Chahal": {"matches": 142, "wickets": 205, "avg": 22.15, "econ": 7.59, "overs": 525.4, "best": "5/40"},
    "Ravichandran Ashwin": {"matches": 186, "wickets": 180, "avg": 26.35, "econ": 6.95, "overs": 693.3, "best": "4/34"},
    "Rashid Khan": {"matches": 99, "wickets": 127, "avg": 20.46, "econ": 6.46, "overs": 400.5, "best": "4/24"},
    "Harshal Patel": {"matches": 95, "wickets": 128, "avg": 23.71, "econ": 8.61, "overs": 346.5, "best": "5/27"},
    "Arshdeep Singh": {"matches": 65, "wickets": 76, "avg": 26.56, "econ": 8.84, "overs": 227.5, "best": "5/32"},
    "Mohammed Siraj": {"matches": 78, "wickets": 72, "avg": 31.55, "econ": 8.95, "overs": 252.3, "best": "4/21"},
    "Kagiso Rabada": {"matches": 63, "wickets": 89, "avg": 23.17, "econ": 8.25, "overs": 249.3, "best": "4/22"},
    "Trent Boult": {"matches": 74, "wickets": 90, "avg": 24.00, "econ": 7.88, "overs": 273.5, "best": "4/18"},
    "Bhuvneshwar Kumar": {"matches": 169, "wickets": 181, "avg": 26.57, "econ": 7.30, "overs": 655.4, "best": "5/19"},
    "Pat Cummins": {"matches": 46, "wickets": 47, "avg": 32.17, "econ": 8.62, "overs": 174.5, "best": "4/34"},
    "Mitchell Starc": {"matches": 19, "wickets": 34, "avg": 19.58, "econ": 8.17, "overs": 81.2, "best": "3/28"},
    "Varun Chakravarthy": {"matches": 60, "wickets": 84, "avg": 22.14, "econ": 7.60, "overs": 243.5, "best": "5/17"},
    "Ravindra Jadeja": {"matches": 226, "wickets": 151, "avg": 30.81, "econ": 7.61, "overs": 609.3, "best": "5/16"},
    "Sunil Narine": {"matches": 177, "wickets": 178, "avg": 26.35, "econ": 6.73, "overs": 696.2, "best": "5/19"},
    "Deepak Chahar": {"matches": 92, "wickets": 83, "avg": 26.48, "econ": 7.86, "overs": 279.3, "best": "4/13"},
    "Mohammed Shami": {"matches": 85, "wickets": 92, "avg": 27.24, "econ": 8.18, "overs": 305.4, "best": "4/11"},
    "Kuldeep Yadav": {"matches": 73, "wickets": 74, "avg": 28.10, "econ": 8.06, "overs": 259.4, "best": "4/43"},
    "Axar Patel": {"matches": 80, "wickets": 65, "avg": 30.73, "econ": 7.10, "overs": 280.3, "best": "3/21"},
    "Ravi Bishnoi": {"matches": 47, "wickets": 51, "avg": 27.41, "econ": 7.99, "overs": 174.5, "best": "4/38"},
    "Matheesha Pathirana": {"matches": 19, "wickets": 28, "avg": 20.32, "econ": 8.22, "overs": 69.2, "best": "4/28"},
}

DEFAULT_BOWLER_BATTING_STATS = {
    "matches": 50, "runs": 200, "avg": 8.5, "sr": 95.0, "fifties": 0, "hundreds": 0, "balls_faced": 210
}

BOWLER_BATTING_STATS = {
    "Mitchell Starc": {"matches": 52, "runs": 165, "avg": 8.68, "sr": 108.55, "fifties": 0, "hundreds": 0, "balls_faced": 152},
    "Jasprit Bumrah": {"matches": 133, "runs": 42, "avg": 6.0, "sr": 75.0, "fifties": 0, "hundreds": 0, "balls_faced": 56},
    "Pat Cummins": {"matches": 46, "runs": 135, "avg": 12.27, "sr": 118.42, "fifties": 0, "hundreds": 0, "balls_faced": 114},
    "Kagiso Rabada": {"matches": 63, "runs": 89, "avg": 7.41, "sr": 102.30, "fifties": 0, "hundreds": 0, "balls_faced": 87},
    "Trent Boult": {"matches": 74, "runs": 45, "avg": 5.62, "sr": 90.0, "fifties": 0, "hundreds": 0, "balls_faced": 50},
    "Mohammed Shami": {"matches": 85, "runs": 52, "avg": 5.78, "sr": 86.67, "fifties": 0, "hundreds": 0, "balls_faced": 60},
    "Mohammed Siraj": {"matches": 78, "runs": 28, "avg": 4.67, "sr": 70.0, "fifties": 0, "hundreds": 0, "balls_faced": 40},
    "Josh Hazlewood": {"matches": 35, "runs": 18, "avg": 4.5, "sr": 72.0, "fifties": 0, "hundreds": 0, "balls_faced": 25},
    "Arshdeep Singh": {"matches": 65, "runs": 12, "avg": 3.0, "sr": 60.0, "fifties": 0, "hundreds": 0, "balls_faced": 20},
    "Yuzvendra Chahal": {"matches": 142, "runs": 35, "avg": 3.5, "sr": 58.33, "fifties": 0, "hundreds": 0, "balls_faced": 60},
    "Rashid Khan": {"matches": 99, "runs": 352, "avg": 13.54, "sr": 142.11, "fifties": 0, "hundreds": 0, "balls_faced": 248},
    "Adam Zampa": {"matches": 40, "runs": 15, "avg": 3.75, "sr": 62.5, "fifties": 0, "hundreds": 0, "balls_faced": 24},
    "Varun Chakravarthy": {"matches": 60, "runs": 8, "avg": 2.67, "sr": 53.33, "fifties": 0, "hundreds": 0, "balls_faced": 15},
    "Kuldeep Yadav": {"matches": 73, "runs": 18, "avg": 3.0, "sr": 60.0, "fifties": 0, "hundreds": 0, "balls_faced": 30},
    "Ravi Bishnoi": {"matches": 47, "runs": 5, "avg": 2.5, "sr": 50.0, "fifties": 0, "hundreds": 0, "balls_faced": 10},
}

def get_batsman_stats(name, use_api=True):
    """Retrieve batting stats for a player, trying API, IPL stats, then local career data."""
    from ipl_stats import get_comprehensive_batting_stats
    
    if use_api:
        try:
            from cricket_api import get_player_batting_stats, is_api_configured
            if is_api_configured():
                api_stats = get_player_batting_stats(name)
                if api_stats:
                    return api_stats
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"API lookup failed for {name}: {e}")
    
    comprehensive = get_comprehensive_batting_stats(name)
    if comprehensive:
        return comprehensive
    if name in PLAYER_CAREER_STATS:
        return PLAYER_CAREER_STATS.get(name)
    if name in BOWLER_BATTING_STATS:
        return BOWLER_BATTING_STATS.get(name)
    if name in BOWLER_CAREER_STATS:
        return DEFAULT_BOWLER_BATTING_STATS.copy()
    return None

def get_bowler_stats(name, use_api=True):
    """Retrieve bowling stats for a player, trying API, IPL stats, then local career data."""
    from ipl_stats import get_comprehensive_bowling_stats
    
    if use_api:
        try:
            from cricket_api import get_player_bowling_stats, is_api_configured
            if is_api_configured():
                api_stats = get_player_bowling_stats(name)
                if api_stats:
                    return api_stats
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"API lookup failed for {name}: {e}")
    
    comprehensive = get_comprehensive_bowling_stats(name)
    if comprehensive:
        return comprehensive
    return BOWLER_CAREER_STATS.get(name, None)

def get_player_form_rating(name):
    """Compute a 0-100 form rating from strike rate and average (batting) or economy and average (bowling)."""
    bat_stats = PLAYER_CAREER_STATS.get(name)
    bowl_stats = BOWLER_CAREER_STATS.get(name)
    
    if bat_stats:
        sr_rating = min(1.0, bat_stats["sr"] / 150)
        avg_rating = min(1.0, bat_stats["avg"] / 45)
        return (sr_rating * 0.6 + avg_rating * 0.4) * 100
    
    if bowl_stats:
        econ_rating = max(0, 1 - (bowl_stats["econ"] - 6) / 4)
        avg_rating = max(0, 1 - (bowl_stats["avg"] - 20) / 20)
        return (econ_rating * 0.5 + avg_rating * 0.5) * 100
    
    return 50.0
