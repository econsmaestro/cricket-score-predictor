# Cricket Score Predictor

## Overview
The Cricket Score Predictor is an AI-powered web application designed to forecast cricket match outcomes. It supports four major formats: Men's T20, Women's T20, Men's ODI, and Women's ODI, covering international venues globally. Users can input real-time match data manually or leverage a live game mode to auto-fill details, receiving predictions for the final score, expected wickets, and performance in the next over. The project aims to provide insightful cricket predictions, enhancing the analytical experience for fans and strategists alike.

## User Preferences
I prefer detailed explanations.
I want iterative development.
Ask before making major changes.
I prefer to be asked before you make any changes to the code.
I do not want to change the file `prediction.py`.
Do not make changes to the `t20_players.py` and `u19_players.py` files.
Do not make changes to the folder `templates/` except for the file `templates/index.html`.

## System Architecture
The application is built on a Flask backend, utilizing Flask-SQLAlchemy for database interactions with PostgreSQL. The frontend is developed using Bootstrap 5, Select2, and custom CSS. The core prediction engine employs NumPy-based statistical models configured with historical and format-specific data.

**Key Architectural Components:**
-   **Prediction Engine (`prediction.py`):** Utilizes statistical models to predict final scores, wickets, and next over runs, incorporating phase-specific logic and player performance profiles. Uses multi-window momentum smoothing (`calculate_blended_momentum`) with short/medium/long-term run-rate windows and adaptive exponential smoothing, plus a smoothed batsman SR function (`calculate_smoothed_batsman_sr`) with sample-size-aware career/current weighting to prevent brief slowdowns from distorting projections while still detecting genuine collapses. Includes a **wickets-in-hand acceleration boost** that increases projected RPO for acceleration/finish/death phases when teams are in the middle overs (35-65% of innings in T20, 20-60% in ODI) with 0-3 wickets lost, reflecting the tendency of well-set batting lineups to explode in the later phases. Also applies a **set batsmen boost** (up to 15%) when current batsmen have faced 15+ balls (T20) or 25+ balls (ODI), reflecting how settled batsmen score progressively faster. Conversely, **tailender scoring decay** is steeper at 7+ wickets (0.48→0.38→0.25 quality factor) with increased wicket-fall rates (0.24–0.28/over) to model realistic tail-end collapses.
-   **Data Management:** Database models in `models.py` handle predictions, user feedback, user authentication (OAuth), and player data. Player statistics are managed through `player_data.py`, `t20_players.py`, `u19_players.py`, and `ipl_stats.py`.
-   **UI/UX:** The application features a user-friendly interface with `base.html`, `index.html` (for input), `results.html` (for displaying predictions), and dedicated dashboards for feedback and analytics. UI includes format selectors with color-coded badges, venue-specific pitch indicators, fielding efficiency badges, and a "Match Momentum & Prediction Factors" section on the results page showing three run-rate windows (current batsmen, bowling spells, overall innings) as informational context alongside core prediction factors (CRR, wickets in hand, overs remaining, smoothed SR, momentum multiplier).
-   **Match Insights:** Includes pre-match analysis (`prematch.py`) for surface, weather, and par scores, and an insights engine (`insights.py`) for predicting dismissal modes based on match situation and player profiles.
-   **Authentication:** Replit OAuth is integrated for user login/logout, enhancing personalization and feedback collection.
-   **Communication & Support:** Features an AI-powered email auto-reply system (`email_responder.py`) and a support chat (`email_responder.py`, `support_chat.html`) leveraging OpenAI and Gmail API integration for user support.
-   **Live Data Integration:** A live match scraper (`live_match_scraper.py`) fetches real-time data from Cricbuzz/ESPN for T20 and ODI matches, allowing for auto-filling of match details. Bowler names from live data display as plain text labels (with edit-to-Select2 option) to avoid Select2 rendering issues with dynamically created rows. Innings detection uses dual-score patterns and "won by" result text (since Cricbuzz uses id-based innings markers rather than text-based ones). Flexible score regex handles all-out innings without `/wickets` format. Squad overlap analysis determines batting vs bowling XI, with `bowling_team_squad_idx` passed to routes for accurate fielding team resolution.
-   **Extended Venue & Team Database (`routes.py`):** `ADDITIONAL_VENUE_COUNTRIES` adds ~200 cricket grounds worldwide (grouped by country) to the base 90 venues from `prediction.py`. `ALL_CRICKET_NATIONS` + `ALL_CRICKET_TEAMS` provide men's and women's team options for ~87 nations. Unknown venues from live data are accepted with default prediction factors.

**Core Features:**
-   **Multi-Format Support:** Men's/Women's T20 and ODI with format-specific rules and phase-based scoring logic.
-   **Input Flexibility:** Manual input or live game mode for auto-filling match data.
-   **Detailed Predictions:** Provides final score, expected wickets, next over runs, boundary/dot ball counts, and win probability for chases.
-   **Advanced Analysis:** Includes venue-specific performance analysis (pitch types, bowler effectiveness), fielding team catching efficiency, and phase-segmented player performance (e.g., powerplay specialists, death specialists).
-   **Player Database:** A comprehensive database of over 705 cricketers, including men's, women's, and U19 players, with batting and bowling statistics.
-   **User Engagement:** Features a user feedback system with rating, reasons, and comments, and an AI-powered support chat.

## External Dependencies
-   **PostgreSQL:** Primary database for storing application data.
-   **CricketData.org API:** Used for live player statistics, with a robust local database fallback mechanism.
-   **Cricbuzz/ESPN:** Web scraped for live match data (T20 and ODI).
-   **OpenAI:** Utilized by `email_responder.py` for AI-powered email auto-replies and support chat generation.
-   **Gmail API:** Integrated via Replit connector for sending emails from the application.
-   **Flask-Dance:** Used for Replit OAuth authentication.