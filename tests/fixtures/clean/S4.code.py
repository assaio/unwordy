def total(rows):
    """Sum the amount column, skipping rows without an amount."""
    return sum(row.amount for row in rows if row.amount)
