# Task ID: 7

**Title:** React Frontend Foundation

**Status:** pending

**Dependencies:** None

**Priority:** high

**Description:** Set up the React frontend application with TypeScript, Vite, Tailwind CSS, routing, and state management according to the technical architecture specified in the PRD. Includes foundation for five frontend views: three ML dashboards (predictions, style evolution, endurance) and two data views (Recent Events, Fighter/Database Lookup).

**Details:**

Initialize and configure a React 18 frontend application:

1. Project setup:
   - Initialize with Vite and TypeScript 4.9+
   - Configure ESLint and Prettier
   - Set up directory structure
   ```
   src/
     â”œâ”€â”€ assets/
     â”œâ”€â”€ components/
     â”‚   â”œâ”€â”€ common/
     â”‚   â”œâ”€â”€ layout/
     â”‚   â””â”€â”€ features/
     â”œâ”€â”€ hooks/
     â”œâ”€â”€ pages/
     â”œâ”€â”€ services/
     â”œâ”€â”€ store/
     â”œâ”€â”€ types/
     â”œâ”€â”€ utils/
     â”œâ”€â”€ App.tsx
     â””â”€â”€ main.tsx
   ```

2. Styling setup:
   - Configure Tailwind CSS 3.0
   - Create design tokens (colors, spacing, etc.)
   - Set up dark mode support
   - Create responsive breakpoints (320px, 768px, 1024px, 1440px)

3. Routing configuration:
   - Set up React Router v6
   - Create route definitions
   - Implement lazy loading for routes
   - Add route guards/protection

4. State management:
   - Configure React Context API
   - Set up useReducer for global state
   - Create typed actions and reducers
   - Implement persistence with localStorage

5. API integration:
   - Set up Axios with interceptors
   - Create API service classes
   - Implement request/response types
   - Add error handling

6. Common components:
   - Button, Input, Card components
   - Loading indicators
   - Error boundaries
   - Toast notifications

7. Testing setup:
   - Configure Jest and React Testing Library
   - Set up test utilities
   - Create mock providers

8. Additional frontend views (no ML required):
   a. Recent Events View:
      - Displays the last ~10 UFC events with card results (winner, method, round)
      - Queries event_details joined with fight_results ordered by date_proper DESC
      - Consumes GET /events endpoint
   b. Fighter/Database Lookup View:
      - Search bar for fighter name
      - Shows fighter profile with physical stats from fighter_tott
      - Full fight history with methods and rounds from fight_results
      - Consumes GET /fighters and GET /fighters/{id} endpoints
      - IMPORTANT: Display a prominent note 'Detailed round stats available from 2015+' on fighter profiles, as fight_stats (round-by-round detail) is only reliably available from 2015 onwards

Implement responsive layouts with mobile-first approach and ensure accessibility compliance.

**Test Strategy:**

1. Test component rendering
2. Verify responsive breakpoints
3. Test routing functionality
4. Validate state management
5. Test API service mocks
6. Verify dark mode toggle
7. Test accessibility with axe-core
8. Validate build output and bundle size
9. Test Recent Events view renders event cards with correct winner/method/round data
10. Test Fighter Lookup search functionality and profile display
11. Verify 'Detailed round stats available from 2015+' caveat note appears on fighter profiles
12. Validate that fight history displays correctly for fighters with pre-2015 records

## Subtasks

### 7.1. Project Initialization with Vite, TypeScript, and Tooling

**Status:** pending  
**Dependencies:** None  

Initialize the React 18 frontend project using Vite with TypeScript 4.9+, configure ESLint and Prettier, and establish the complete directory structure as specified in the PRD.

**Details:**

1. Run `npm create vite@latest` with React + TypeScript template
2. Configure tsconfig.json with strict mode, path aliases (e.g., @/components, @/hooks, @/services)
3. Install and configure ESLint with @typescript-eslint, eslint-plugin-react, eslint-plugin-react-hooks
4. Install and configure Prettier with .prettierrc and .prettierignore
5. Create the full directory structure: src/assets/, src/components/common/, src/components/layout/, src/components/features/, src/hooks/, src/pages/, src/services/, src/store/, src/types/, src/utils/
6. Create placeholder index files in each directory
7. Configure Vite with path aliases matching tsconfig
8. Set up .env files (.env, .env.development, .env.production) with VITE_ prefixed variables
9. Configure Jest and React Testing Library: install jest, @testing-library/react, @testing-library/jest-dom, jest-environment-jsdom
10. Create jest.config.ts, setupTests.ts, and a test utilities file with mock providers
11. Add npm scripts: dev, build, preview, lint, format, test

Acceptance Criteria:
- `npm run dev` starts the dev server without errors
- `npm run build` produces a valid dist/ output
- `npm run lint` and `npm run format` execute without errors
- `npm run test` runs successfully with a sample test
- All directories exist with placeholder files
- TypeScript strict mode enabled with no type errors

### 7.2. Tailwind CSS Styling Configuration with Design Tokens and Dark Mode

**Status:** pending  
**Dependencies:** None  

Install and configure Tailwind CSS 3.0 with custom design tokens, dark mode support, and responsive breakpoints aligned with the PRD specifications.

**Details:**

1. Install tailwindcss, postcss, autoprefixer and run `npx tailwindcss init -p`
2. Configure tailwind.config.ts with content paths covering all src files
3. Define custom design tokens in the theme.extend section:
   - Colors: primary, secondary, accent, neutral, success, warning, error palettes
   - Typography: font families, sizes, weights
   - Spacing: custom spacing scale
   - Border radius, shadows, z-index values
4. Configure responsive breakpoints: sm: 320px, md: 768px, lg: 1024px, xl: 1440px
5. Enable dark mode with class strategy: `darkMode: 'class'`
6. Create src/styles/globals.css with @tailwind directives and CSS custom properties for design tokens
7. Create src/styles/tokens.ts exporting design token constants for use in TypeScript
8. Import globals.css in main.tsx
9. Create a ThemeProvider component in src/components/layout/ that manages dark/light mode toggle using localStorage persistence
10. Add a useDarkMode custom hook in src/hooks/
11. Verify Tailwind purging works correctly in production build

Acceptance Criteria:
- Tailwind utility classes apply correctly in components
- Dark mode toggles via class on html element and persists across page reloads
- All four responsive breakpoints work as expected
- Design tokens are accessible both as Tailwind classes and TypeScript constants
- Production build CSS is properly purged and optimized

### 7.3. React Router v6 Configuration with Lazy Loading and Route Guards

**Status:** pending  
**Dependencies:** None  

Set up React Router v6 with all application route definitions including Recent Events and Fighter Lookup views, lazy loading for code splitting, and route guard components for protected routes.

**Details:**

1. Install react-router-dom v6
2. Create src/router/index.tsx with centralized route definitions using createBrowserRouter
3. Define routes for all planned pages:
   - / (Home/Dashboard)
   - /fighters (Fighter/Database Lookup view â€” search bar + fighter profiles)
   - /fighters/:id (Fighter detail with profile, physical stats, fight history)
   - /events (Recent Events view â€” last ~10 UFC events with card results)
   - /events/:id (Event detail)
   - /analytics (Analytics dashboard)
   - /analytics/style-evolution (Style Evolution Timeline - Task 9)
   - /analytics/endurance (Fighter Endurance Dashboard - Task 10)
   - /predictions (Predictions page)
   - /* (404 Not Found)
4. Implement lazy loading for all page components using React.lazy() and Suspense with a loading fallback
5. Create a RouteGuard component in src/components/common/ for future protected routes
6. Create a Layout component in src/components/layout/ with Header, Sidebar/Nav, and Footer slots
7. Create placeholder page components in src/pages/ for each route, including RecentEventsPage and FighterLookupPage
8. Add a NotFound (404) page component
9. Create a LoadingSpinner component used as Suspense fallback
10. Configure RouterProvider in App.tsx
11. Write tests for routing behavior and lazy loading

Acceptance Criteria:
- All defined routes render their respective page components
- Lazy loading splits code into separate chunks (verify in build output)
- Suspense fallback displays during chunk loading
- 404 page renders for unknown routes
- Navigation between routes works without full page reload
- RouteGuard component correctly handles access control logic
- /events and /fighters routes have placeholder pages ready for implementation in subtask 6

### 7.4. State Management with Context API, useReducer, and Persistence

**Status:** pending  
**Dependencies:** None  

Implement global state management using React Context API with useReducer, typed actions and reducers, and localStorage persistence for relevant state slices.

**Details:**

1. Create src/store/index.ts as the main store entry point
2. Define TypeScript interfaces for global state in src/types/store.ts:
   - AppState (theme, notifications, ui state)
   - FilterState (active filters for fighters/events/analytics)
   - UserPreferencesState (dark mode, layout preferences)
3. Create typed action types and action creators in src/store/actions.ts
4. Implement reducers in src/store/reducers/:
   - appReducer.ts
   - filterReducer.ts
   - userPreferencesReducer.ts
5. Create a root reducer combining all reducers
6. Create AppContext and AppProvider in src/store/AppContext.tsx using useReducer
7. Implement localStorage persistence middleware pattern:
   - Create src/utils/localStorage.ts with typed get/set/remove helpers
   - Persist userPreferences and filterState to localStorage
   - Rehydrate state from localStorage on app initialization
8. Create custom hooks for consuming store slices: useAppState, useAppDispatch, useUserPreferences, useFilters in src/hooks/
9. Wrap the app with AppProvider in main.tsx
10. Write unit tests for reducers and custom hooks using mock providers

Acceptance Criteria:
- Global state is accessible from any component via custom hooks
- State updates via dispatch trigger re-renders correctly
- User preferences persist across browser sessions via localStorage
- TypeScript provides full type safety for actions and state
- Reducer tests cover all action types
- No prop drilling required for global state access

### 7.5. API Service Layer, Common Components, and Error Handling

**Status:** pending  
**Dependencies:** None  

Set up Axios with interceptors for API communication, create typed API service classes for all backend endpoints, implement common reusable UI components, and add error boundaries and toast notifications.

**Details:**

1. Install axios
2. Create src/services/api.ts with Axios instance configured with:
   - Base URL from environment variable (VITE_API_BASE_URL)
   - Request interceptor for headers (Content-Type, correlation IDs)
   - Response interceptor for error normalization
   - Timeout configuration
3. Create typed API service classes in src/services/:
   - fightersService.ts (getFighters, getFighterById, getFighterStats)
   - eventsService.ts (getEvents, getEventById)
   - fightsService.ts (getFights, getFightById)
   - analyticsService.ts (getStyleEvolution, getEnduranceData)
   - predictionsService.ts (getPredictions)
4. Create src/types/api.ts with request/response TypeScript interfaces matching backend Pydantic schemas, including:
   - Fighter profile types (physical stats from fighter_tott)
   - Fight result types (winner, method, round from fight_results)
   - Event listing types (event_details joined with fight_results)
5. Implement a custom useApi hook in src/hooks/useApi.ts for data fetching with loading/error/data states
6. Create common components in src/components/common/:
   - Button.tsx (variants: primary, secondary, ghost, danger; sizes: sm, md, lg)
   - Input.tsx (with label, error state, helper text)
   - Card.tsx (with header, body, footer slots)
   - LoadingSpinner.tsx and LoadingSkeleton.tsx
   - ErrorBoundary.tsx (class component with fallback UI)
   - Toast.tsx and ToastContainer.tsx (integrated with app state)
   - Badge.tsx, Modal.tsx, Tooltip.tsx
   - DataCaveatNote.tsx (reusable banner/note component for displaying data availability caveats)
7. Integrate ToastContainer in App.tsx layout
8. Add toast dispatch actions to the store (subtask 4)
9. Write component tests for all common components
10. Ensure all components meet WCAG 2.1 AA accessibility standards (aria labels, keyboard navigation, focus management)

Acceptance Criteria:
- Axios instance correctly sends requests to the configured API base URL
- All service methods return properly typed responses
- Error interceptor normalizes API errors and triggers toast notifications
- All common components render correctly across responsive breakpoints
- ErrorBoundary catches and displays errors gracefully without crashing the app
- Toast notifications appear and auto-dismiss correctly
- DataCaveatNote component renders correctly and is reusable
- Components pass accessibility checks with axe-core
- Component unit tests achieve >80% coverage

### 7.6. Recent Events View and Fighter/Database Lookup View

**Status:** pending  
**Dependencies:** 7.3, 7.4, 7.5  

Implement the two non-ML data views: a Recent Events view showing the last ~10 UFC events with card results, and a Fighter/Database Lookup view with search and full fighter profiles including a data availability caveat for pre-2015 fight stats.

**Details:**

1. Recent Events View (src/pages/RecentEventsPage.tsx):
   - Fetch data via eventsService.getEvents() (GET /events), ordered by date DESC, limit ~10
   - Display each event as a card showing: event name, date, location
   - Within each event card, list fight results: winner name, method (KO/TKO, Submission, Decision, etc.), round
   - Data sourced from event_details joined with fight_results ordered by date_proper DESC
   - Show loading skeletons while fetching
   - Handle empty state and error state gracefully
   - Responsive layout: stacked cards on mobile, grid on desktop

2. Fighter/Database Lookup View (src/pages/FighterLookupPage.tsx and src/pages/FighterDetailPage.tsx):
   - Search bar (Input component) for fighter name with debounced query
   - Fighter list results via fightersService.getFighters(query) (GET /fighters?search=...)
   - Fighter profile page via fightersService.getFighterById(id) (GET /fighters/{id}):
     a. Physical stats section: height, weight, reach, stance, date of birth (from fighter_tott)
     b. Record summary: wins, losses, draws, no contests
     c. Full fight history table: opponent, event, date, result, method, round
     d. IMPORTANT: Display a prominent, accessible caveat note â€” 'Detailed round stats available from 2015+' â€” on all fighter profiles. Use the DataCaveatNote component from subtask 5. This is because fight_stats (round-by-round detail) is only reliably available from 2015 onwards; older fights may show results but lack granular stats.
   - Link fighter search results to individual fighter profile pages (/fighters/:id)
   - Show loading skeletons during data fetch
   - Handle no-results and error states

3. Feature components in src/components/features/:
   - EventCard.tsx (event summary with fight results list)
   - FightResultRow.tsx (single fight result: winner, method, round)
   - FighterSearchBar.tsx (debounced search input)
   - FighterProfileHeader.tsx (name, record, physical stats)
   - FightHistoryTable.tsx (sortable table of fight history)

4. Write tests:
   - Unit tests for EventCard, FightResultRow, FighterSearchBar, FighterProfileHeader, FightHistoryTable
   - Integration tests for RecentEventsPage and FighterLookupPage with mocked API responses
   - Test that DataCaveatNote renders on all fighter profile pages

Acceptance Criteria:
- Recent Events page displays last ~10 events with fight results (winner, method, round)
- Fighter search returns relevant results and links to profile pages
- Fighter profile shows physical stats, record, and full fight history
- 'Detailed round stats available from 2015+' caveat note is always visible on fighter profiles
- Both views are fully responsive (mobile-first)
- Loading and error states are handled gracefully
- No ML logic is involved in either view
- All components pass accessibility checks
