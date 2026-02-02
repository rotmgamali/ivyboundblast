
# Multi-Campaign Implementation Outline

This document outlines the architectural changes required to transform the current single-purpose Ivybound system into a multi-vertical outreach platform supporting **Ivybound (School Admins)**, **Lionheart (Real Estate)**, and **PACStrategy (Political Donors)**.

## 1. Core Architecture Refactoring

### 1.1 Strategy Pattern Implementation
*   **Objective**: Decouple the execution logic from the pipeline to support interchangeable strategies.
*   **What to do**:
    *   Create a base abstract class `CampaignStrategy` in a new `strategies/` module.
    *   Define standard interfaces: `enrich_data()`, `qualify_lead()`, `generate_content()`.
    *   Refactor existing `CampaignManager` to enforce this interface.

### 1.2 Pipeline Routing
*   **Objective**: Automatically route input CSVs to the correct strategy.
*   **What to do**:
    *   Modify `pipeline.py` to accept a `strategy` argument (or auto-detect based on CSV headers).
    *   `Website` column -> Route to **Ivybound**.
    *   `Property Address` column -> Route to **Lionheart**.
    *   `Donation Amount` column -> Route to **PAC**.

### 1.3 Shared Infrastructure
*   **Objective**: Reuse existing robust components.
*   **Reuse**:
    *   `RateLimiter`: Shared across all scrapers (Property sites, FEC, Schools).
    *   `CircuitBreaker`: Protects against blocking on Zillow/FEC/School sites.
    *   `DLQ (Dead Letter Queue)`: Unified error handling for all verticals.

## 2. Campaign-Specific Modules

### 2.1 Ivybound (Existing)
*   **Status**: Production Ready.
*   **Action**: Move existing logic into `strategies/ivybound.py`.
*   **Logic**: Scrape School Website -> Extract Contacts -> Role Match -> Email.

### 2.2 Aspire Realty (Real Estate)
*   **Target**: Recent Homebuyers (6-18 months).
*   **Sender**: Andrew Rollins.
*   **Input Data**: `Owner Name`, `Property Address`, `Sale Date`.
*   **Enrichment scraper (`strategies/aspire.py`)**:
    *   **Source**: Public Assessor Records / Zillow / Redfin.
    *   **Extraction**: Property Age, Square Footage, Purchase Price.
    *   **Logic**:
        *   Calculate `TimeOwned` (Target 6-18mo).
        *   Filter out `LLC` or absentee owners (Investors).
*   **Email Sequence (3 Steps)**:
    1.  **Observation**: Mention property specific (e.g., "built in 1990").
    2.  **Value**: Service relevance (e.g., "maintenance for 30yr old roof").
    3.  **Engagement**: Direct professional invite.

### 2.3 PAC Strategy (Political)
*   **Target**: High-value donors (>$500) with employer data.
*   **Sender**: Mark Greenstein.
*   **Input Data**: `Contributor Name`, `Employer`, `Amount`, `Recipient`.
*   **Enrichment scraper (`strategies/pac.py`)**:
    *   **Source**: OpenSecrets / LinkedIn / Company News.
    *   **Extraction**: Industry sector, recent company news.
    *   **Logic**:
        *   Score `PoliticalEngagement` (Multi-cycle vs One-time).
        *   Link `Donation Sector` to `Professional Role`.
*   **Email Sequence (3 Steps)**:
    1.  **Recognition**: Acknowledge civic engagement/pattern.
    2.  **Context**: Bridge political interest to professional industry.
    3.  **Invitation**: Peer-to-peer business value proposition.

## 3. Configuration & Data

### 3.1 Prompt Engineering
*   **Action**: Create distinct prompt libraries for each strategy in `campaign/prompts.py` (or JSON).
    *   `IVYBOUND_PROMPTS`: Educational focus.
    *   `LIONHEART_PROMPTS`: Property/Homeowner focus (Tone: Neighborly, Helpful).
    *   `PAC_PROMPTS`: Business/Civic focus (Tone: Deferential, Professional).

### 3.2 Input Validation
*   **Action**: Update `pipeline.py` validation to check for different required schemas based on the selected strategy.

## 4. Execution Plan
1.  **Refactor**: Create `strategies/` directory and move Ivybound logic.
2.  **Implement Lionheart**: Create `LionheartStrategy` class with property enrichment stubs.
3.  **Implement PAC**: Create `PACStrategy` class with FEC enrichment stubs.
4.  **Update Config**: Add rate limit domains for Zillow/FEC.
5.  **Verify**: Run pipeline with 3 different input CSVs.
