def total(rows):
    """Sum the amount column.

    Rows without an amount are skipped. Rows with a negative amount
    are kept, because refunds are negative amounts and they count
    towards the total the same way.
    """
    return sum(row.amount for row in rows if row.amount)
