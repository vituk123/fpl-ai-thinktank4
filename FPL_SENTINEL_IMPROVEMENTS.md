# FPL Sentinel System - Improvement Recommendations

## Current Issues Identified

1. **Timeout Problems**: Many accounts timing out (FPLUpdates, PrasFPL, FPLGuidance, etc.)
2. **Low Tweet Collection**: Only 8 tweets from 7 experts in 3 days
3. **Zero Recommendations**: Sentiment analyzer found 0 actionable recommendations
4. **Date Filtering Too Strict**: Many tweets filtered out as "out of range"
5. **Player Name Matching**: May miss variations or partial mentions
6. **Intent Detection**: Regex patterns may be too strict for implicit recommendations

---

## Recommended Improvements

### 1. **Improve Scraper Reliability** (High Priority)

#### A. Add Retry Logic with Exponential Backoff
- Retry failed requests 2-3 times with increasing delays
- Handle session expiration gracefully
- Add request timeout configuration

#### B. Better Error Handling
- Catch and log specific error types (timeout, network, element not found)
- Continue scraping other accounts even if one fails
- Save partial results periodically

#### C. Increase Timeout Values
- Increase page load timeout from 15s to 30s
- Add configurable timeout per account type
- Use longer waits for slow-loading accounts

### 2. **Enhance Tweet Collection** (High Priority)

#### A. Improve Scrolling Strategy
- Scroll more aggressively (increase max_scrolls to 30-50)
- Add "scroll to load" detection (wait for new content)
- Scroll in smaller increments to catch lazy-loaded content
- Add scroll position tracking to avoid infinite loops

#### B. Better Date Parsing
- Be more lenient with date filtering (include tweets with unparseable dates)
- Add fuzzy date matching (e.g., "recent" = last 3 days)
- Log date parsing failures for debugging
- Include tweets from "today" even if exact time unknown

#### C. Collect More Tweet Types
- Include replies and quote tweets (not just main tweets)
- Extract thread tweets (multi-part tweets)
- Capture engagement metrics (likes, retweets) for ranking

### 3. **Improve Sentiment Analysis** (High Priority)

#### A. Enhanced Player Name Matching
- Use fuzzy string matching (e.g., `fuzzywuzzy` or `rapidfuzz`)
- Handle common misspellings and variations
- Match partial names (e.g., "Haaland" in "Haaland (C) is essential")
- Add team name matching (e.g., "City striker" → Haaland)
- Include position-based matching (e.g., "Chelsea defender" → specific player)

#### B. More Flexible Intent Detection
- Detect implicit recommendations:
  - "Player X is essential" → Buy
  - "Avoid Player Y" → Sell
  - "Player Z is a must-have" → Buy
  - "Player A is injured" → Sell
- Add context-aware detection:
  - "GW15 captain" → Captain intent
  - "Triple captain Player X" → Captain intent
  - "Transfer Player Y out" → Sell intent
- Use NLP techniques (if available) for better intent classification

#### C. Improve Sentiment Scoring
- Weight recommendations by expert tier (Tier 1 > Tier 2 > Tier 3)
- Consider engagement metrics (more engagement = higher weight)
- Add recency weighting (newer tweets = higher weight)
- Combine multiple signals (sentiment + intent + engagement)

### 4. **Better Data Quality** (Medium Priority)

#### A. Tweet Content Enhancement
- Extract URLs and follow them for full content (threads, articles)
- Parse images/attachments for text (OCR if needed)
- Handle emoji and special characters better
- Clean and normalize tweet text

#### B. Metadata Collection
- Store tweet engagement metrics
- Track which expert made the recommendation
- Add timestamp precision
- Include tweet type (original, reply, quote, thread)

### 5. **Performance Optimizations** (Medium Priority)

#### A. Parallel Scraping
- Scrape multiple accounts in parallel (with rate limiting)
- Use async/await for non-blocking operations
- Implement connection pooling

#### B. Caching
- Cache player name mappings
- Store recent tweets to avoid re-scraping
- Use Redis or similar for session management

### 6. **Configuration & Monitoring** (Low Priority)

#### A. Make Parameters Configurable
- Days to look back (currently hardcoded to 3)
- Number of scrolls per account
- Timeout values
- Retry attempts

#### B. Add Monitoring & Logging
- Track success/failure rates per account
- Log scraping performance metrics
- Alert on repeated failures
- Generate scraping reports

---

## Quick Wins (Easy to Implement)

1. **Increase days_back to 7 days** - More tweets to analyze
2. **Include tweets with unparseable dates** - Don't filter them out
3. **Add more player nicknames** - Expand the nickname mapping
4. **Relax intent detection patterns** - Add more flexible regex
5. **Add "essential", "must-have", "avoid" keywords** - Common FPL terms
6. **Increase scroll count** - From 20 to 30-40
7. **Add retry logic** - Simple retry for timeouts

---

## Implementation Priority

1. **Phase 1 (Quick Wins)**: 
   - Increase days_back, include unparseable dates, add more keywords
   - **Expected Impact**: 2-3x more tweets, better recommendation detection

2. **Phase 2 (Reliability)**:
   - Add retry logic, improve error handling, increase timeouts
   - **Expected Impact**: 50%+ reduction in timeouts, more complete data

3. **Phase 3 (Intelligence)**:
   - Enhanced player matching, better intent detection, fuzzy matching
   - **Expected Impact**: 5-10x more recommendations detected

4. **Phase 4 (Scale)**:
   - Parallel scraping, caching, performance optimization
   - **Expected Impact**: Faster execution, better scalability

---

## Expected Outcomes

After implementing improvements:
- **Tweet Collection**: 20-50 tweets per run (vs current 8)
- **Recommendations**: 5-15 actionable recommendations (vs current 0)
- **Reliability**: 90%+ success rate (vs current ~40%)
- **Coverage**: All 18 accounts scraped successfully (vs current 7)

