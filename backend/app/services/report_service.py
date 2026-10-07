from datetime import date

from fastapi import HTTPException


def validate_date_range(start_date: date, end_date: date) -> None:
	if end_date < start_date:
		raise HTTPException(status_code=422, detail="End date must be on or after start date")
	if (end_date - start_date).days > 366:
		raise HTTPException(status_code=422, detail="Report range cannot exceed 367 days")
