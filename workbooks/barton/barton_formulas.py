"""Shared Sigma formula snippets for Barton POC workbook controls."""

DATE_BASIS = (
    'Switch([Date-Basis], "Start Date", [Assignments/Start Date], '
    "[Assignments/Assignment Created Date])"
)

PERIOD = (
    "Switch([Date-Segment], "
    f'"year", DateTrunc("year", {DATE_BASIS}), '
    f'"quarter", DateTrunc("quarter", {DATE_BASIS}), '
    f'"week", DateTrunc("week", {DATE_BASIS}), '
    f'DateTrunc("month", {DATE_BASIS}))'
)

TREND_VALUE = (
    "Switch([Trend-Metric], "
    '"Contract Value", Sum([Assignments/Estimated Contract Value]), '
    '"Avg Bill Rate", Avg([Assignments/Bill Rate]), '
    '"Cancellations", Sum([Assignments/Is Cancelled Or Withdrawn]), '
    "CountDistinct([Assignments/Assignment Number]))"
)

DT_PERIOD = {"kind": "datetime", "formatString": "%b %Y"}

KPI_PERIOD = f'DateTrunc("month", {DATE_BASIS})'

PERIOD_COMPARISON = {
    "display": "delta",
    "colorGood": "#007A78",
    "colorBad": "#D64545",
    "fontSize": 13,
}
