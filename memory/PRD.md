# Analytics Engine - Product Requirements Document

## Original Problem Statement
Professional advanced data analysis web application capable of processing any dataset (financial or not), regardless of size or structure. Transform raw data (Excel, CSV, JSON) into intelligent, dynamic dashboards comparable to professional tools (Tableau, Power BI, Palantir Foundry).

## User Choices
- **AI Model**: Claude Sonnet 4.5 for insights
- **Authentication**: None for MVP
- **File Storage**: Local storage
- **Design**: Professional sober style (JP Morgan/Morgan Stanley)

## User Personas
1. **Business Analyst**: Needs quick insights from data without technical setup
2. **Data Scientist**: Wants automated EDA and pattern detection
3. **Executive**: Requires high-level KPIs and exportable reports

## Core Requirements (Static)
- Import files: CSV, Excel (.xlsx), JSON
- Auto-detect column types (numeric, temporal, categorical)
- Auto-generate dashboards with KPIs, charts
- AI-powered insights and recommendations
- Export reports (Text, CSV, JSON)
- Light/Dark theme toggle
- Professional institutional UI design

## What's Been Implemented

### April 7, 2026 - MVP
- File upload with multi-format support
- Automatic column type detection
- Dashboard generation with KPIs and charts
- AI insights using Claude Sonnet 4.5
- Report generation (Text, CSV, JSON)
- Light/Dark theme toggle

### April 7, 2026 - Iteration 2
- **KPI Number Formatting**: Large numbers display with K/M/B/T suffixes
- **Chart Download**: Export each chart as PNG image
- **Dataset Merge**: Combine datasets via concat, left_join, inner_join

### April 8, 2026 - Iteration 3 (AI-Powered Analysis)
- **Intelligent Domain Detection**: AI identifies data type (finance, sales, HR, customers, etc.)
- **Smart KPI Generation**: KPIs automatically adapted to domain context
- **Contextual Visualizations**: Charts selected based on data meaning, not just structure
- **AI Insights Banner**: Dedicated section showing key findings from AI analysis
- **French Language Support**: AI generates insights in French when appropriate
- **Cached Analysis**: AI analysis cached for performance optimization

## Prioritized Backlog

### P0 (Critical) - DONE
- File upload ✓
- AI-powered dashboard generation ✓
- Domain-specific KPIs ✓
- Contextual visualizations ✓
- Dataset merge/cross ✓

### P1 (High Priority) - Future
- PDF/PowerPoint export (server-side generation)
- Multi-sheet Excel support
- Drag & drop dashboard customization
- Calculated columns/fields
- Pivot tables

### P2 (Medium Priority) - Future
- User authentication
- Project saving/loading
- Custom chart configurations
- Data validation rules

### P3 (Nice to Have) - Future
- Real-time data connections
- Collaborative features
- Advanced ML predictions
- Natural language queries

## Next Tasks List
1. Add PDF/PPTX export using server-side generation
2. Implement multi-sheet Excel support
3. Add pivot table functionality
4. Create calculated columns feature
5. Add drag & drop dashboard customization
