"""Course scheduling tools."""
import json
from langchain_core.tools import tool

with open('data/course_catalog.json') as f:
    CATALOG = json.load(f)

COURSES = {c['course_id']: c for c in CATALOG['courses']}
PROGRAM = CATALOG['program']


@tool
def get_program_requirements() -> str:
    """Return program requirements: core courses, elective courses, and credit targets."""
    core = [c['course_id'] for c in CATALOG['courses'] if c['type'] == 'core']
    elec = [c['course_id'] for c in CATALOG['courses'] if c['type'] == 'elective']
    return (
        f"Program: {PROGRAM['name']}\n"
        f"Total credits required: {PROGRAM['total_credits_required']}\n"
        f"Max courses per term: {PROGRAM['max_courses_per_term']}\n"
        f"Core courses ({len(core)}): {', '.join(core)}\n"
        f"Elective courses ({len(elec)}): {', '.join(elec)}"
    )


@tool
def check_prerequisites(course_id: str, completed_courses: str) -> str:
    """Check if prerequisites and corequisites are met for a course.
    completed_courses should be a comma-separated list of course IDs."""
    if course_id not in COURSES:
        return f"Error: Course {course_id} not found in catalog."
    completed = [c.strip() for c in completed_courses.split(',')] if completed_courses.strip() else []
    course = COURSES[course_id]
    missing_pre = [p for p in course.get('prerequisites', []) if p not in completed]
    missing_co  = [p for p in course.get('corequisites', [])  if p not in completed]
    if not missing_pre and not missing_co:
        return f"OK: All prerequisites and corequisites satisfied for {course_id}."
    parts = []
    if missing_pre:
        parts.append(f"Missing prerequisites: {', '.join(missing_pre)}")
    if missing_co:
        parts.append(f"Missing corequisites: {', '.join(missing_co)}")
    return f"Cannot take {course_id}. " + "; ".join(parts) + "."


@tool
def get_course_availability(course_id: str, term: str) -> str:
    """Check if a course is offered in a specific term (Fall, Winter, or Summer)."""
    if course_id not in COURSES:
        return f"Error: Course {course_id} not found in catalog."
    offered = COURSES[course_id].get('offered_terms', [])
    if term in offered:
        return f"{course_id} IS offered in {term}."
    return f"{course_id} is NOT offered in {term}. Offered in: {', '.join(offered) if offered else 'never'}."


@tool
def check_schedule_conflicts(proposed_courses: str, term: str, completed_courses: str) -> str:
    """Validate a proposed semester schedule.
    proposed_courses: comma-separated course IDs.
    term: Fall, Winter, or Summer.
    completed_courses: comma-separated course IDs already passed."""
    proposed  = [c.strip() for c in proposed_courses.split(',') if c.strip()]
    completed = [c.strip() for c in completed_courses.split(',') if c.strip()]
    errors = []

    if len(proposed) > PROGRAM.get('max_courses_per_term', 5):
        errors.append(f"Too many courses: {len(proposed)} exceeds max {PROGRAM['max_courses_per_term']}.")

    seen = set()
    for c in proposed:
        if c in seen:
            errors.append(f"Duplicate course: {c}.")
        seen.add(c)
        if c in completed:
            errors.append(f"{c} already completed.")
        elif c not in COURSES:
            errors.append(f"{c} not found in catalog.")
        elif term not in COURSES[c].get('offered_terms', []):
            errors.append(f"{c} not offered in {term}.")

    if errors:
        return "Invalid schedule: " + " ".join(errors)
    return f"Valid: Schedule {', '.join(proposed)} is conflict-free for {term}."


ALL_TOOLS = [get_program_requirements, check_prerequisites, get_course_availability, check_schedule_conflicts]
