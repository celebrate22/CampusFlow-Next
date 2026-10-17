"""F6 - totals and breakdowns by status, priority and category, plus resolution insight."""

STATUS_ORDER = ("open", "in_progress", "resolved")
PRIORITY_ORDER = ("critical", "high", "medium", "low")
CATEGORY_ORDER = ("Network", "Hardware", "Software", "Other")


def build_summary(all_tickets_list):
    """Pure calculation: count tickets. Safe for an empty list.

    Every ticket is counted exactly once per breakdown, by its CURRENT status.
    """
    status_counts = {name: 0 for name in STATUS_ORDER}
    priority_counts = {name: 0 for name in PRIORITY_ORDER}
    category_counts = {name: 0 for name in CATEGORY_ORDER}

    for ticket in all_tickets_list:
        status = str(ticket.get("status") or "open").lower()
        priority = str(ticket.get("priority") or "low").lower()
        category = str(ticket.get("category") or "Other").capitalize()
        status_counts[status] = status_counts.get(status, 0) + 1
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1

    total = len(all_tickets_list)
    resolved = status_counts["resolved"]
    unresolved = status_counts["open"] + status_counts["in_progress"]
    resolution_percentage = round(resolved / total * 100, 1) if total else 0.0

    return {
        "total": total,
        "status": status_counts,
        "priority": priority_counts,
        "category": category_counts,
        "unresolved": unresolved,
        "resolved": resolved,
        "resolution_percentage": resolution_percentage,
    }


def generate_system_summary_report(all_tickets_list, display=True):
    """Build the summary, optionally print it, and return the numbers."""
    summary = build_summary(all_tickets_list)

    if display:
        print("\n" + "=" * 35)
        print("        SYSTEM METRICS REPORT")
        print("=" * 35)
        print(f"Total Tickets Logged: {summary['total']}")
        print(f"Unresolved (Open + In Progress): {summary['unresolved']}")
        print(f"Resolved: {summary['resolved']}")
        print(f"Resolution Rate: {summary['resolution_percentage']:.1f}%")
        print("-" * 35)
        print("Breakdown by Status:")
        for status, count in summary["status"].items():
            print(f"  - {status.replace('_', ' ').title()}: {count}")
        print("-" * 35)
        print("Breakdown by Priority:")
        for priority, count in summary["priority"].items():
            print(f"  - {priority.title()}: {count}")
        print("-" * 35)
        print("Breakdown by Category:")
        for category, count in summary["category"].items():
            print(f"  - {category}: {count}")
        print("=" * 35 + "\n")

    return summary