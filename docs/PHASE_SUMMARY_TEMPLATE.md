# Phase X: [Name]

**Status**: ✅ Completed / 📋 Planning / 🚧 In Progress
**Date**: [Month Day, Year] (e.g., December 18, 2025)
**Goal**: [One sentence - why does this phase exist?]

---

## Overview

[2-3 paragraphs describing what we built at high level]

**Included in this phase**:
- Feature A
- Feature B

**Explicitly excluded** (deferred to Phase X+1):
- Feature C
- Feature D

---

## Key Achievements

1. **Achievement 1 Title**
   - What was built
   - Why it matters
   - Reference: [ADR-003](../architecture/decisions/ADR-003-*.md) or [AWS Guide](./learning/aws.md)

2. **Achievement 2 Title**
   - Details
   - Impact

[As many as needed - keep concise with inline references]

---

## Database Schema

**[Table Name]**:
- Field descriptions (high-level, no SQL)
- Purpose and design rationale
- Indexes and constraints (conceptual)
- Reference: [ADR-XXX](../architecture/decisions/ADR-XXX-*.md) if applicable

[Only include if this phase added/modified database schema]

---

## API Endpoints

**Route**: `[METHOD] /api/path`
- Purpose
- Request/Response structure (high-level)
- Authentication requirements
- Reference: [API Guide](./learning/python-fastapi.md) if applicable

[Only include if this phase added new endpoints]

---

## Highlights

### [Highlight 1 Title]
[Technical details, optimizations, quirks worth documenting]
- Reference: [Deployment Guide](./deployment/GUIDE.md) if applicable

### [Highlight 2 Title]
[Challenges overcome, trade-offs made, clever solutions]

[As many as needed - keep concise with inline references]

---

## Testing & Validation

**Manual Testing**:
- ✅ Test case 1
- ✅ Test case 2
- ✅ Test case 3

**Automated Testing**:
- ✅ Unit tests implemented
- ✅ Integration tests implemented
- Future: End-to-end tests planned

[Split manual vs automated, show what exists vs. planned]

---

## Metrics

- **Metric 1**: Value (e.g., "Tables added: 2")
- **Metric 2**: Value (e.g., "API endpoints: 5")
- **Metric 3**: Value (e.g., "Lines of code: ~1,200")

[As many as relevant]

---

## Next Steps → Phase X+1

[Brief description of what comes next]

**Key Features**:
- Feature 1
- Feature 2

**Target**: [Goal for next phase]

---

## File Structure

```
backend/
├── new_module/
│   ├── __init__.py
│   └── implementation.py
└── existing_module/
    └── updated_file.py

frontend/src/
└── components/
    └── NewComponent.js
```

**Key Files**:
- [implementation.py](../../backend/new_module/implementation.py) - Main implementation
- [NewComponent.js](../../frontend/src/components/NewComponent.js) - UI component

---

## Key Learnings

### [Learning Category]
[Brief insight - 1-2 sentences, link to learning docs for details]

**Reference**: [Topic Guide](./learning/topic.md)

[As many as relevant - keep concise]

---

## References

**External Documentation**:
- [Official Docs](https://example.com) - Description
- [Library Guide](https://example.com/guide) - Description

[Only external web references - internal docs linked inline above]
