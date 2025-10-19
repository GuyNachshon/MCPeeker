# User Acceptance Testing Guide
## Feature 002: Testing & UI Improvements for Registry Match Classification

**Target Users**: SOC Analysts
**Test Duration**: 15-20 minutes
**Prerequisites**: Access to MCPeeker Dashboard with sample detection data

---

## Overview

This UAT validates that SOC analysts can:
1. Quickly identify detection classifications using visual indicators
2. Filter detections efficiently without training
3. Understand the new UI components intuitively

---

## Test Scenarios

### Scenario 1: Classification Recognition (SC-003)
**Success Criterion**: Identify classification in < 2 seconds

**Steps**:
1. Navigate to the **Dashboard** page
2. Locate the "Detection Summary" section at the top
3. Observe the three classification cards

**Validation Questions**:
- [ ] Can you identify which color represents "Authorized" detections? (Should be green)
- [ ] Can you identify which color represents "Suspect" detections? (Should be yellow)
- [ ] Can you identify which color represents "Unauthorized" detections? (Should be red)
- [ ] How long did it take you to understand the color scheme? (Target: < 2 seconds)

**Expected Behavior**:
- Green cards/badges = Authorized MCPs (safe, registered)
- Yellow cards/badges = Suspect MCPs (needs review)
- Red cards/badges = Unauthorized MCPs (high risk)

---

### Scenario 2: Detection List with Badges
**Success Criterion**: Quickly scan and identify high-risk detections

**Steps**:
1. Navigate to the **Detections** page
2. Look at the detection list table
3. Find the "Classification" column

**Validation Questions**:
- [ ] Can you quickly spot unauthorized detections in the list?
- [ ] Are the color-coded badges helpful for scanning?
- [ ] Can you distinguish between classification types at a glance?

**Expected Behavior**:
- Each detection row shows a colored badge
- Badges match the color scheme (green/yellow/red)
- Visual scanning is faster than reading text labels

---

### Scenario 3: "Hide Authorized MCPs" Filter (SC-004)
**Success Criterion**: 95% of analysts use filter without training

**Steps**:
1. Stay on the **Detections** page
2. Locate the filter panel at the top
3. Find the "Hide authorized MCPs" checkbox
4. Click the checkbox to enable the filter

**Validation Questions**:
- [ ] Did you find the filter without any help? (Yes/No)
- [ ] Was the filter's purpose immediately clear? (Yes/No)
- [ ] Did the filter work as expected? (Yes/No)
- [ ] How many detections were hidden? (Should show count)

**Expected Behavior**:
- Filter panel shows above the detection list
- Checkbox labeled "Hide authorized MCPs"
- Clicking checkbox hides green/authorized detections
- Count shows "Showing X of Y detections" (filtered vs total)
- Filter reduces noise, focusing on actionable items

---

### Scenario 4: Dashboard Summary Interaction
**Success Criterion**: Understand detection breakdown in < 5 seconds

**Steps**:
1. Return to the **Dashboard** page
2. Look at the "Detection Summary" section
3. Try clicking on one of the classification cards

**Validation Questions**:
- [ ] Can you tell how many detections are in each category?
- [ ] Do the cards clearly show counts and percentages?
- [ ] Are the cards clickable or interactive? (May depend on implementation)

**Expected Behavior**:
- Three cards showing Authorized, Suspect, Unauthorized counts
- Each card displays a count number and badge
- Cards may be clickable to filter detections (optional)

---

### Scenario 5: Score Explanation (T039)
**Success Criterion**: Understand why a detection received its score

**Steps**:
1. Navigate to **Detections** page
2. Click on any detection to view details
3. Locate the "Score Breakdown" or "Explanation Panel"

**Validation Questions**:
- [ ] Can you see a breakdown of the score calculation?
- [ ] Does it explain which evidence contributed to the score?
- [ ] Can you understand why the detection was classified as it was?

**Expected Behavior**:
- Detection detail view shows ScoreBreakdown component
- ExplanationPanel explains the classification logic
- Evidence contributions are clearly listed

---

## Success Criteria Checklist

### SC-003: Rapid Classification Identification
- [ ] **Target**: 100% of testers identify classification in < 2 seconds
- [ ] **Actual**: _____ seconds (average)
- [ ] **Pass/Fail**: _____

### SC-004: Filter Usability Without Training
- [ ] **Target**: 95% of testers use filter without help
- [ ] **Actual**: _____ % used filter successfully
- [ ] **Pass/Fail**: _____

### Overall Usability
- [ ] UI components are intuitive
- [ ] Color scheme is clear and accessible
- [ ] Filtering reduces analyst workload
- [ ] No confusion or errors reported

---

## Feedback Collection

### What Worked Well?
```
(Tester notes)
```

### What Needs Improvement?
```
(Tester notes)
```

### Did You Encounter Any Issues?
```
(Tester notes)
```

### Additional Comments
```
(Tester notes)
```

---

## Test Results

**Tester Name**: _____________________
**Date**: _____________________
**Test Duration**: _____ minutes

**Overall Assessment**:
- [ ] Pass - Ready for production
- [ ] Pass with minor issues - Document and fix
- [ ] Fail - Requires rework

**Signature**: _____________________

---

## For Test Facilitators

### Setup Requirements
1. MCPeeker Dashboard running and accessible
2. Sample detection data loaded (mix of authorized/suspect/unauthorized)
3. At least 10-20 detections visible
4. Test environment matches production

### Testing Tips
- Don't provide guidance unless tester is stuck
- Observe tester behavior without interference
- Time the classification recognition task
- Note any hesitation or confusion
- Ask testers to "think aloud" during tasks

### After Testing
1. Collect completed UAT forms
2. Calculate pass rates for SC-003 and SC-004
3. Document any bugs or UX issues
4. Prioritize improvements based on feedback
5. Schedule follow-up if needed

---

## Appendix: Component Reference

### DetectionBadge
- **Location**: Detection list, Classification column
- **Colors**: Green (authorized), Yellow (suspect), Red (unauthorized)
- **Purpose**: Quick visual classification indicator

### DashboardSummary
- **Location**: Dashboard page, top section
- **Display**: Three interactive cards with counts
- **Purpose**: High-level detection overview

### DetectionFilter
- **Location**: Detections page, above table
- **Controls**: "Hide authorized MCPs" checkbox, search, filters
- **Purpose**: Focus analyst attention on actionable detections

### ScoreBreakdown & ExplanationPanel
- **Location**: Detection detail view
- **Display**: Score calculation breakdown
- **Purpose**: Explain classification reasoning

---

**Document Version**: 1.0
**Last Updated**: 2025-10-19
**Feature**: 002-testing-ui-improvements
