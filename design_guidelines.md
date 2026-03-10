# IPL Cricket Score Prediction App - Design Guidelines

## Design Approach

**Hybrid Approach**: Material Design foundation with sports-energetic customization. This balances utility needs (data-heavy forms and predictions) with the excitement inherent to cricket analytics.

**Key Principles**:
- **Clarity First**: Dense data requires exceptional visual hierarchy
- **Action-Oriented**: Predictions should feel immediate and impactful
- **Cricket Context**: Subtle nods to cricket aesthetics without overwhelming functionality

## Typography

**Font Family**: Inter (primary), Roboto Mono (statistics)

**Hierarchy**:
- Page Title: text-4xl font-bold
- Section Headers: text-2xl font-semibold
- Form Labels: text-sm font-medium uppercase tracking-wide
- Input Text: text-base font-normal
- Prediction Headlines: text-3xl font-bold
- Stats/Numbers: text-5xl font-bold (Roboto Mono)
- Supporting Text: text-sm font-normal

## Layout System

**Spacing Primitives**: Use Tailwind units of 2, 4, 6, 8, 12, and 16 exclusively.

**Container Strategy**:
- Main container: max-w-6xl mx-auto px-4
- Form sections: Two-column on desktop (grid-cols-1 lg:grid-cols-2), single-column mobile
- Prediction results: Full-width cards with internal grid layouts

## Core Components

### Header
- Simple top bar with app title and tagline ("IPL Score Predictor")
- Height: h-16
- Include small IPL logo placeholder (40x40px)

### Input Form Section

**Structure**: Group inputs into logical cards with clear visual separation

**Match State Card**:
- Wickets fallen: Number input with +/- steppers
- Score input: Large number field
- Overs remaining: Slider with numeric display

**Batsmen Details Card** (Repeating component for 2 batsmen):
- Name input field
- Runs scored (number input)
- Balls faced (number input)
- Layout: Compact horizontal arrangement

**Bowling Figures Card**:
- Table layout for multiple bowlers
- Columns: Bowler name, Overs bowled, Runs conceded, Wickets
- Add/Remove bowler buttons

**Venue Selection**:
- Dropdown with all IPL venues
- Include stadium icon placeholder

**Next Over Bowler**:
- Prominent dropdown selection
- Larger than other inputs to emphasize importance

**Submit Button**:
- Full-width on mobile, fixed width (w-64) centered on desktop
- Large padding: px-8 py-4
- Prominent placement with top margin: mt-12

### Prediction Results Section

**Layout**: Three distinct prediction cards displayed in responsive grid (grid-cols-1 md:grid-cols-3 gap-6)

**Final Score Prediction Card**:
- Massive number display for predicted score (text-6xl)
- Confidence indicator below
- Subtle cricket ball icon placeholder (64x64px)

**Wickets Prediction Card**:
- Large wicket count display
- Visual representation (could be wicket stumps icons)
- Supporting text for context

**Next Over Prediction Card**:
- Predicted runs for next over
- Bowler name reminder
- Probability breakdown (dot balls, boundaries likelihood)

## Visual Elements

**Form Styling**:
- Input fields: Prominent borders, rounded corners (rounded-lg)
- Consistent padding: px-4 py-3
- Focus states: Enhanced border visibility
- Number inputs: Larger touch targets for mobile

**Cards**:
- Rounded corners: rounded-xl
- Padding: p-6 to p-8
- Subtle elevation through borders (not shadows for cleaner look)

**Data Tables**:
- Clean borders between rows
- Alternating row treatment for readability
- Fixed header on scroll for bowling figures table

**Icons**:
Use Heroicons via CDN for UI elements (plus/minus, dropdown arrows, etc.)
Cricket-specific placeholder comments for:
- <!-- CUSTOM ICON: Cricket ball -->
- <!-- CUSTOM ICON: Wicket stumps -->
- <!-- CUSTOM ICON: IPL logo -->

## Responsive Behavior

**Mobile (< 768px)**:
- Single column form layout
- Stacked prediction cards
- Full-width inputs and buttons
- Spacing: p-4, gap-4

**Desktop (>= 1024px)**:
- Two-column form where logical
- Three-column prediction display
- Wider spacing: p-8, gap-8
- Max container width prevents excessive stretching

## Interaction States

**Buttons**: Clear hover state with slight scale transform (scale-105)
**Input Focus**: Enhanced border treatment
**Form Validation**: Inline error messages below invalid fields (text-sm, red treatment)
**Loading State**: Spinner overlay during prediction calculation

## Accessibility

- All form inputs have associated labels
- ARIA labels for icon buttons
- Keyboard navigation support throughout
- Sufficient contrast ratios for all text
- Focus indicators clearly visible

## Images

**No hero image** - This is a tool-first application where immediate access to the form is priority.

Small decorative elements only:
- IPL logo in header (40x40px)
- Cricket ball icon in prediction section (64x64px)
- Optional: Subtle cricket field boundary pattern as background texture (very low opacity)