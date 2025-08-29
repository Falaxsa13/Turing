# Notion Database Schemas for Canvas Sync

This document outlines the complete structure of your 3 Notion databases and how to properly structure data when integrating with Canvas.

## 🎯 Database Overview

Your academic tracking system consists of **3 interconnected databases**:

1. **Courses** - Core course information with relations to assignments and notes
2. **Assignments/Exams** - Detailed assignment tracking with grading and progress
3. **Notes** - Study materials and notes linked to courses

## 📚 1. Courses Database

**Database ID**: `e84565ef-888d-4b7e-a24b-8a13ef8e369f`

### Properties You Can Set:

```python
# When adding a course entry:
course_data = {
    "title": "Course Name",                    # ✅ REQUIRED (title field)
    "course_code": "CS 7641",                 # ✅ rich_text
    "professor": "Dr. Jane Smith",            # ✅ rich_text
    "term": "Fall 2024",                      # ✅ select (see options below)
    "location": "Room 205, Tech Square",     # ✅ rich_text
    "contact": "+1-555-123-4567",            # ✅ phone_number
    "date": "2024-08-15"                     # ✅ date (course start date)
    # Note: Syllabus (files) can be added later through Notion UI
}
```

### Term Options:

- `Fall 2026`, `Summer 2026`, `Spring 2026`
- `Fall 2025`, `Summer 2025`, `Spring 2025`
- `Fall 2024`, `Summer 2024`, `Spring 2024`
- `Fall 2023`

### Auto-Calculated Fields:

- **Assignments/Exams** (relation) - Links to assignments
- **Notes** (relation) - Links to notes
- **Total Assignments** (rollup) - Count from assignments
- **Completed Assignments** (rollup) - Progress tracking
- **Upcoming Exams** (rollup) - Exam reminders
- **Overall Grade** (rollup) - Grade calculation
- **Status** (formula) - Assignment/exam summary

---

## 📝 2. Assignments/Exams Database

**Database ID**: `8e017e06-b108-4a90-b91a-7a8cf0cc53ba`

### Properties You Can Set:

```python
# When adding an assignment/exam entry:
assignment_data = {
    "title": "Assignment Name",               # ✅ REQUIRED (title field)
    "type": "Assignment",                     # ✅ select: "Assignment" or "Exam"
    "due_date": "2024-12-15",                # ✅ date (ISO format)
    "raw_score": 95,                         # ✅ number (points earned)
    "total_score": 100,                      # ✅ number (total possible points)
    "weighting": 0.25,                       # ✅ number (weight in final grade)
    # Note: Course relation should be set when creating from Canvas
}
```

### Type Options:

- `Assignment`
- `Exam`

### Status Options (managed through Notion UI):

- Various status options for completion tracking

### Auto-Calculated Fields:

- **Percentage** (formula) - raw_score / total_score
- **Overall** (formula) - percentage × weighting
- **Completed Assignment** (formula) - Completion tracking
- **Assignment?** (formula) - Type verification
- **Upcoming Exam** (formula) - Exam deadline tracking
- **Days Left** (formula) - Days until due date

---

## 📖 3. Notes Database

**Database ID**: `061fd583-cad1-4f9f-99b7-dee470105416`

### Properties You Can Set:

```python
# When adding a note entry:
note_data = {
    "title": "Note Title",                    # ✅ REQUIRED (title field)
    "type": "Assignment",                     # ✅ select: "Assignment" or "Exam"
    "next_review": "2024-12-20",             # ✅ date (spaced repetition)
    # Note: Course relation should be set when creating from Canvas
    # Note: Materials (files) can be added later through Notion UI
    # Note: Confidence (status) managed through Notion UI
}
```

### Type Options:

- `Assignment`
- `Exam`

### Auto-Updated Fields:

- **Last Edited** (last_edited_time) - Automatic timestamp
- **Course** (relation) - Link to course
- **Confidence** (status) - Learning confidence level

---

## 🔗 Database Relationships

Your databases are interconnected:

```
Courses ←→ Assignments/Exams
   ↕
 Notes
```

- **Courses** link to both **Assignments/Exams** and **Notes**
- **Assignments/Exams** link back to **Courses**
- **Notes** link back to **Courses**

## 🚀 Canvas Integration Mapping

When Canvas webhook receives data, map it like this:

### Course Creation (from Canvas course):

```python
canvas_course = {
    "id": "12345",
    "name": "Advanced Machine Learning",
    "course_code": "CS 7641",
    "start_at": "2024-08-15T00:00:00Z",
    "end_at": "2024-12-15T00:00:00Z"
}

# Map to Notion:
notion_course = {
    "title": canvas_course["name"],
    "course_code": canvas_course["course_code"],
    "term": "Fall 2024",  # Derive from start_at date
    "date": canvas_course["start_at"][:10],  # "2024-08-15"
}
```

### Assignment Creation (from Canvas assignment):

```python
canvas_assignment = {
    "id": "67890",
    "name": "Neural Networks Project",
    "due_at": "2024-12-15T23:59:59Z",
    "points_possible": 100,
    "submission_types": ["online_upload"]
}

# Map to Notion:
notion_assignment = {
    "title": canvas_assignment["name"],
    "type": "Assignment",  # or "Exam" based on Canvas assignment type
    "due_date": canvas_assignment["due_at"][:10],  # "2024-12-15"
    "total_score": canvas_assignment["points_possible"],
    "weighting": 0.25,  # You'll need to configure this per course
    # Course relation will be set based on Canvas course_id
}
```

## ✅ Testing Your Schema Integration

Use these API endpoints to test:

```bash
# Get all database schemas
curl -X POST "http://localhost:8000/setup/notion/schemas" \
  -H "Content-Type: application/json" \
  -d '{"notion_token": "your_token", "notion_parent_page_id": "your_page_id"}'

# Test course creation
curl -X POST "http://localhost:8000/setup/notion/add-course" \
  -H "Content-Type: application/json" \
  -d '{
    "notion_token": "your_token",
    "notion_parent_page_id": "your_page_id",
    "entry_data": {
      "title": "Test Course",
      "course_code": "TEST 101",
      "professor": "Dr. Test",
      "term": "Fall 2024"
    }
  }'
```

## 🎯 Next Steps

1. **Canvas API Integration**: Set up Canvas webhooks to automatically create entries
2. **Relation Mapping**: Ensure assignments/notes are properly linked to their courses
3. **Grade Sync**: Sync Canvas grades to update raw_score in assignments
4. **File Uploads**: Handle Canvas file attachments (syllabi, materials)

Your Notion workspace is now **fully mapped and ready** for Canvas integration! 🚀
