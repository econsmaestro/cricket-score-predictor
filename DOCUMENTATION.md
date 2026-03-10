# Cricket Score Predictor - Full Documentation

## Project Overview

**Cricket Match Intelligence** is an AI-powered web application that predicts cricket match outcomes based on current match state. Built with Flask and PostgreSQL, it serves cricket enthusiasts who want real-time predictions during live matches.

### Key Highlights
- Supports **4 match formats**: Men's T20, Women's T20, Men's ODI, Women's ODI
- **530+ international players** from 20+ countries (men's, women's, and U19 youth)
- **100+ cricket venues** worldwide
- **Live match integration** with auto-fill functionality
- **User authentication** via Replit OAuth
- **Feedback system** with testimonials display and admin analytics
- **Pre-Match Insights** with venue analysis, weather, and par scores
- **Match Insights** with dismissal mode prediction
- **AI-powered Support Chat** with conversation history
- **AI email auto-replies** for feedback and bug reports via Gmail API

---

## Features

### 1. Multi-Format Support
- **Men's T20**: 20 overs, max 4 overs per bowler
- **Women's T20**: 20 overs, max 4 overs per bowler
- **Men's ODI**: 50 overs, max 10 overs per bowler
- **Women's ODI**: 50 overs, max 10 overs per bowler

Each format has different phase-based scoring logic:
- **T20 Phases**: Powerplay (1-6), Middle (7-15), Death (16-20)
- **ODI Phases**: Powerplay (1-10), Middle 1 (11-30), Middle 2 (31-40), Death (41-50)

### 2. Input Modes
- **Manual Input**: Enter all match details manually
- **Live Game Mode**: Select from live matches to auto-fill score, wickets, overs

### 3. Prediction Outputs
- Final score prediction
- Expected wickets to fall
- Next over runs prediction
- Boundary and dot ball counts
- Win probability (for 2nd innings chases)

### 4. Venue-Specific Analysis
- Pitch type classification: pace-friendly, spin-friendly, batting-paradise, balanced
- Bowler type detection (pace vs spin) based on bowling style
- Venue-based effectiveness modifiers (+/-10% impact)

### 5. Pre-Match Insights
- Weather conditions at venue (temperature, humidity, wind)
- Bat first vs chase historical records
- Countdown timer to match start
- Surface description and pitch conditions
- Par score analysis based on venue history
- Phase-by-phase scoring expectations

### 6. Match Insights (Dismissal Mode Prediction)
- Predicts likelihood of dismissal modes: caught boundary/infield, bowled, LBW, run out, stumped
- Considers match situation, venue pitch type, bowler type (pace/spin)
- Analyzes batsman profile and pressure indicators

### 7. User Authentication
- Replit OAuth integration (Google, GitHub, email login)
- User profile display in navigation
- Login/logout functionality
- Post-login redirect to feedback page when coming from predictions

### 8. Feedback & Bug Reports
- Thumbs up/down ratings on predictions
- Checkbox reasons for negative feedback
- Text comments (max 300 characters)
- Public testimonials on homepage
- Admin dashboard for all feedback with Excel export
- Dedicated Feedback/Bug Report page with:
  - Category pills (Bug, Feature Request, Improvement, Account, Other)
  - Screenshot upload support
  - System diagnostics toggle
  - Character counters
  - Cricket-themed success animation

### 9. AI Email Auto-Replies
- Automatic AI-generated email replies to user feedback and bug reports
- Powered by OpenAI (gpt-5-nano) and Gmail API via Replit connector
- Professional HTML email templates with CricPredictor branding
- Sent from cricpredict.team@gmail.com ("CricPredictor (no-reply)")
- Comprehensive email validation (client-side and server-side)

### 10. AI Support Chat
- Web-based chat interface with AI-powered assistant
- Conversation history stored in database (SupportChat model)
- CSRF protection on all chat API endpoints
- Quick prompt suggestions for common questions
- Typing indicator animation
- New chat/clear session functionality
- AI assistant knowledgeable about cricket and app features

### 11. Analytics Dashboard
- Page views tracking
- Unique visitors count
- Device and browser statistics
- Top pages analysis
- Daily trends visualization

---

## Technical Architecture

### Technology Stack
| Component | Technology |
|-----------|------------|
| Backend | Flask, Flask-SQLAlchemy |
| Database | PostgreSQL (Neon-backed) |
| Frontend | Bootstrap 5, Select2, Custom CSS |
| Authentication | Replit OAuth, Flask-Dance, Flask-Login |
| Prediction Engine | NumPy-based statistical models |
| AI Integration | OpenAI (gpt-5-nano) via Replit AI Integrations |
| Email | Gmail API via Replit connector |
| External API | CricketData.org (optional) |
| Web Scraping | BeautifulSoup, Requests |

### Project Structure
```
├── app.py                  # Flask app setup and database configuration
├── main.py                 # Application entry point
├── routes.py               # Route handlers for form, predictions, chat, feedback
├── models.py               # Database models (Prediction, User, OAuth, Feedback, PageView, SupportChat, BugReport)
├── replit_auth.py          # Replit OAuth authentication with Flask-Dance
├── prediction.py           # Score prediction engine with statistical models
├── player_data.py          # Player career statistics and form ratings
├── t20_players.py          # Comprehensive player database (530+ players)
├── u19_players.py          # U19 youth player database from 2024 and 2026 World Cups
├── ipl_stats.py            # IPL 2008-2024 + International venue historical statistics
├── stats_scraper.py        # Player stats scraper from ESPNCricinfo
├── prematch.py             # Pre-match analysis engine (par scores, surface, weather)
├── insights.py             # Dismissal mode prediction engine
├── gmail_helper.py         # Gmail API integration via Replit connector
├── email_responder.py      # AI-powered email auto-reply and support chat generator
├── live_match_scraper.py   # Live match scraper for T20/ODI from Cricbuzz/ESPN
├── gunicorn.conf.py        # Gunicorn configuration (timeout=60 for AI operations)
├── templates/
│   ├── base.html           # Base template with header/footer/navigation
│   ├── index.html          # Input form with format selector and live game mode
│   ├── results.html        # Prediction results display with feedback
│   ├── prematch.html       # Pre-match insights with weather, surface, par score
│   ├── insights.html       # Match insights - dismissal mode analysis
│   ├── support_chat.html   # AI-powered support chat with conversation history
│   ├── bug_report.html     # Feedback/bug report form
│   ├── feedback_dashboard.html  # Admin feedback dashboard
│   ├── analytics_dashboard.html # Traffic analytics
│   └── 403.html            # Authentication error page
├── static/
│   └── css/
│       └── style.css       # Custom styling
├── design_guidelines.md    # Frontend design specifications
└── DOCUMENTATION.md        # This file
```

### Database Models
1. **User**: Stores authenticated user information (id, email, name, profile image)
2. **OAuth**: Manages OAuth tokens for Replit Auth
3. **Prediction**: Stores prediction history
4. **Player**: Player statistics cache
5. **HistoricalMatch**: Historical match data
6. **MatchPerformance**: Player performances in historical matches
7. **VenueStats**: Venue-specific statistics
8. **PredictionFeedback**: User feedback with ratings, comments, and email
9. **PageView**: Traffic analytics data
10. **PlayerStatsCache**: Cached player stats from external APIs
11. **DiscoveredPlayer**: Dynamically discovered player statistics from ESPNcricinfo
12. **BugReport**: User-submitted bug reports with category, screenshot, and diagnostics
13. **SupportChat**: AI chat conversation history (session_id, role, message)

---

## Challenges Faced & Solutions

### Challenge 1: Late-Innings Prediction Accuracy
**Problem**: When 8+ wickets had fallen, the prediction engine was overestimating final scores because it assumed all remaining overs would be played.

**Solution**: Implemented "effective overs remaining" calculation that considers:
- Tail-ender wicket rates (0.22 per over vs 0.12 for regular batsmen)
- Survival probability capped at 50% when 8+ wickets down
- Dynamic adjustment based on wickets in hand

```python
effective_overs_remaining = min(overs_remaining, expected_overs_to_allout)
```

### Challenge 2: Live Match Bowler Extraction
**Problem**: When scraping live matches, bowlers from both innings were being mixed together, causing incorrect data auto-fill.

**Solution**: Implemented innings-aware filtering that:
- Identifies which innings is currently active
- Filters bowlers to only show those bowling in the current innings
- Properly handles innings transitions

### Challenge 3: Player Selection Flexibility
**Problem**: Initially, players were categorized as either batsmen OR bowlers, but in cricket anyone can bat (and sometimes bowl).

**Solution**: 
- Made all 530+ players selectable as either batsmen or bowlers
- Added batting statistics for bowlers (tail-ender averages)
- Implemented form validation to prevent duplicate player selection

### Challenge 4: Multi-Format Support
**Problem**: T20 and ODI have different rules (overs, bowling limits, powerplay phases), requiring significant logic changes.

**Solution**: Created format-specific configuration:
```python
FORMAT_CONFIG = {
    'mens_t20': {'total_overs': 20, 'max_bowler_overs': 4, ...},
    'womens_t20': {'total_overs': 20, 'max_bowler_overs': 4, ...},
    'mens_odi': {'total_overs': 50, 'max_bowler_overs': 10, ...},
    'womens_odi': {'total_overs': 50, 'max_bowler_overs': 10, ...}
}
```

### Challenge 5: Database Schema Migrations
**Problem**: Adding new columns (user_id, username) to existing tables caused runtime errors because the database schema was out of sync.

**Solution**: 
- Used SQL ALTER TABLE commands to add missing columns
- Created new tables (users, flask_dance_oauth) with proper constraints
- Ensured OAuth model table name matched Flask-Dance expectations

### Challenge 6: Venue-Specific Performance Analysis
**Problem**: Predictions didn't account for pitch conditions affecting bowler performance differently.

**Solution**: Implemented pitch type classification system:
- Categorized venues as pace-friendly, spin-friendly, batting-paradise, or balanced
- Detected bowler type (pace vs spin) from bowling style
- Applied +/-10% effectiveness modifiers based on venue-bowler compatibility

### Challenge 7: Authentication Integration
**Problem**: Needed user login to associate feedback with usernames while keeping the app accessible to anonymous users.

**Solution**: 
- Integrated Replit OAuth using Flask-Dance
- Made feedback submission require authentication
- Displayed login prompt on results page for unauthenticated users
- Stored username with feedback for testimonial display
- Post-login redirect to feedback page via `/login-redirect` route

### Challenge 8: AI Email Auto-Reply with Gmail Connector Limitations
**Problem**: The Replit Gmail connector only provides send permissions (gmail.send scope), not read permissions. This prevented implementing a two-way email conversation system.

**Solution**:
- Used Gmail connector for sending AI-generated email replies to feedback and bug reports
- Built a web-based AI support chat as the conversation channel instead of email
- Email footer directs users to the website for further communication
- OpenAI's gpt-5-nano model generates contextual replies (discovered that max_completion_tokens parameter causes empty responses — must be omitted)

### Challenge 9: Email Validation
**Problem**: Users could submit invalid email addresses (e.g., numeric-only domains), causing email delivery failures.

**Solution**:
- Client-side validation with HTML5 pattern attribute
- Server-side regex validation: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]*[a-zA-Z][a-zA-Z0-9.-]*\.[a-zA-Z]{2,6}$`
- Requires domain to contain at least one letter and TLD of 2-6 characters

### Challenge 10: CSRF Protection for Chat API
**Problem**: JSON-based chat endpoints were vulnerable to cross-site request forgery.

**Solution**:
- Session-based CSRF token generated on chat page load
- Token included in all fetch requests from the client
- Server validates token on every POST to `/api/support-chat` and `/api/support-chat/clear`

### Challenge 11: Live Match Venue Name Mismatch
**Problem**: When selecting a live match, the venue name scraped from external sources (e.g., "R.Premadasa Stadium, Colombo") didn't exactly match the valid venue list (e.g., "R. Premadasa Stadium, Colombo" — note the space after the period). This caused form validation to fail with "Please select a valid cricket venue" for all live matches where venue naming differed even slightly.

**Solution**:
- Refactored venue matching logic out of the timezone conversion block so it runs independently for all live matches, not just those with start times
- Added normalization step that expands abbreviations like "R." to "R. " (inserting space after period) before comparison
- Improved word-overlap scoring in fallback matching, using set intersection and stripping punctuation for better fuzzy matching
- Backend now writes the matched valid venue name back into `match_data['venue']` so the frontend always receives an exact match
- Frontend JavaScript venue matching also improved with normalized comparison and multi-word fallback scoring

### Challenge 12: Support Chat Page Navigation Links
**Problem**: When users asked the AI support chatbot for help finding a feature or page, the AI had no knowledge of the app's page structure and could not direct users with clickable links. Users had to manually navigate to find pages.

**Solution**:
- Added a complete App Pages Directory to the AI system prompt listing all user-facing pages with their exact URL paths
- Instructed the AI to always include markdown-format links (`[Page Name](/path)`) when directing users to pages
- AI explicitly told to say "I cannot find that page" if a requested page doesn't exist, rather than guessing
- Created a custom Jinja2 filter (`markdown_links`) in `app.py` that converts markdown links to styled `<a>` tags for server-rendered chat history
- Added client-side markdown link parsing in the JavaScript `appendMessage` function for real-time assistant replies
- Links are styled with the app's color scheme and only match internal paths (starting with `/`) for security

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page with prediction form |
| `/predict` | POST | Submit prediction request |
| `/prematch` | GET/POST | Pre-match insights form and results |
| `/insights` | GET/POST | Match insights (dismissal mode analysis) |
| `/support-chat` | GET | AI-powered support chat page |
| `/bug-report` | GET/POST | Feedback/bug report form |
| `/login-redirect` | GET | Login with redirect to specified page |
| `/api/live-matches` | GET | Get live match list |
| `/api/live-matches/refresh` | POST | Force refresh live matches |
| `/api/live-match/<id>` | GET | Get match details for auto-fill |
| `/api/players` | GET | Search player database (530+ players) |
| `/api/player/<name>` | GET | Get player statistics |
| `/api/cricket-api/status` | GET | Check external API status |
| `/api/cricket-api/search` | GET | Search players via CricketData.org |
| `/api/support-chat` | POST | Send chat message and get AI reply (CSRF protected) |
| `/api/support-chat/clear` | POST | Start new chat session (CSRF protected) |
| `/feedback/submit` | POST | Submit user feedback (requires login) |
| `/feedback` | GET | Admin feedback dashboard |
| `/feedback/export` | GET | Export feedback to Excel |
| `/analytics` | GET | Traffic analytics dashboard |
| `/auth/login` | GET | Initiate Replit OAuth login |
| `/auth/logout` | GET | Logout user |

---

## Player Database Coverage

### Men's Cricket (350+ players)
- **India**: Kohli, Rohit, Bumrah, Jadeja, Pandya, etc.
- **Australia**: Smith, Warner, Cummins, Starc, etc.
- **England**: Root, Stokes, Buttler, Archer, etc.
- **Pakistan**: Babar, Rizwan, Shaheen, etc.
- **Other nations**: South Africa, New Zealand, West Indies, Sri Lanka, Bangladesh, Afghanistan, Zimbabwe, Ireland, Netherlands, Scotland, USA, UAE, Nepal, Namibia

### Women's Cricket (80+ players)
- **Australia**: Perry, Lanning, Healy, etc.
- **England**: Knight, Sciver-Brunt, Ecclestone, etc.
- **India**: Mandhana, Kaur, Sharma, etc.
- **Other nations**: South Africa, West Indies, New Zealand, Pakistan, Sri Lanka, Bangladesh

### U19 Youth Players (90+ players)
- From ICC U19 World Cup 2024 (South Africa) and 2026 (Zimbabwe/Namibia)
- **Countries**: India, England, Australia, South Africa, Pakistan, Afghanistan, Bangladesh, Sri Lanka, West Indies, New Zealand
- **Key players**: Vaibhav Suryavanshi, Sam Konstas, Kwena Maphaka, Musheer Khan, Ben Mayes, Uday Saharan

---

## Venue Database

100+ international cricket grounds across:

### Test-Playing Nations
India, Australia, England, South Africa, New Zealand, Pakistan, West Indies, Sri Lanka, Bangladesh, Zimbabwe, Afghanistan, Ireland

### ICC Associate Members
USA, Scotland, Netherlands, Nepal, Namibia, Oman, Canada, Hong Kong, Kenya, Uganda, Papua New Guinea, UAE

---

## Running the Application

### Local Development
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `SESSION_SECRET`: Flask session secret key
- `REPL_ID`: Replit environment identifier (auto-set)
- `CRICKET_API_KEY`: (Optional) CricketData.org API key
- `GMAIL_SENDER_EMAIL`: Email sender address (cricpredict.team@gmail.com)
- `AI_INTEGRATIONS_OPENAI_BASE_URL`: OpenAI API base URL (auto-set by Replit)
- `AI_INTEGRATIONS_OPENAI_API_KEY`: OpenAI API key (auto-set by Replit)

---

## Development Timeline

| Date | Milestone |
|------|-----------|
| December 11, 2025 | Initial implementation with prediction engine and UI |
| December 11, 2025 | Win probability calculation for 2nd innings chases |
| January 18, 2026 | Multi-format support (T20 + ODI, Men's + Women's) |
| January 18, 2026 | Live game scraping with auto-fill |
| January 18, 2026 | Expanded to 100+ venues, 80+ women's players |
| January 25, 2026 | Player flexibility (all can bat/bowl), CricketData.org API |
| January 30, 2026 | Venue-specific performance analysis, feedback system |
| February 2, 2026 | Replit OAuth authentication, analytics dashboard |
| February 7, 2026 | U19 youth players database (90+ players) |
| February 17, 2026 | Pre-Match Insights (weather, par scores, surface analysis) |
| February 17, 2026 | Match Insights (dismissal mode prediction) |
| February 18, 2026 | Feedback/Bug Report page with categories and screenshots |
| February 18, 2026 | AI email auto-replies via Gmail API and OpenAI |
| February 18, 2026 | AI Support Chat with conversation history in database |
| February 18, 2026 | Post-login redirect to feedback page |

---

## Future Improvements

1. **Machine Learning Models**: Train on historical match data for improved accuracy
2. **Weather Integration**: Real-time weather API for live conditions during matches
3. **Player Form Tracking**: Real-time form updates based on recent performances
4. **Push Notifications**: Alert users when live matches are available
5. **Historical Accuracy Tracking**: Compare predictions vs actual outcomes
6. **Mobile App**: Native iOS/Android applications
7. **Gmail Read Access**: Enable full two-way email conversations when connector scopes expand

---

## Credits

Built with Flask, PostgreSQL, Bootstrap 5, OpenAI, and powered by statistical cricket analysis models.

**Data Sources**:
- Player statistics: Local database + CricketData.org API
- Live matches: Cricbuzz/ESPN web scraping
- Venue data: Compiled from international cricket records

**Email**: cricpredict.team@gmail.com

---

*Last Updated: February 18, 2026*
