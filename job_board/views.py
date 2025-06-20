import math
from datetime import datetime
from datetime import timedelta
from decimal import Decimal

import humanize
from flask import abort
from flask import Flask
from flask import render_template
from flask import request
from flask import url_for

from job_board import config
from job_board.models import Job
from job_board.query import count_jobs
from job_board.query import filter_jobs
from job_board.utils import utcnow_naive


app = Flask(__name__)
app.jinja_env.filters["naturaltime"] = humanize.naturaltime

PER_PAGE = 12
AVAILABLE_TAGS = [
    "developer",
    "backend",
    "frontend",
    "full stack",
    "infrastructure",
    "data science",
    "typescript",
    "node.js",
    "react",
    "python",
    "rust",
    "golang",
]


@app.route("/")
def get_jobs():
    min_salary = request.args.get("min_salary", type=Decimal, default=Decimal("20000"))
    include_no_salary = request.args.get("include_no_salary", type=bool, default=False)
    posted_on = request.args.get("posted_on", type=datetime)
    if not posted_on:
        posted_on = utcnow_naive() - timedelta(days=config.JOB_AGE_LIMIT_DAYS)
    tags = request.args.getlist("tags", type=str)
    is_remote = request.args.get("is_remote", type=bool, default=True)

    sort = request.args.get("sort", type=str, default="posted_on_desc")
    match sort:
        case "salary_desc":
            order_by = Job.salary.desc()
        case "posted_on_desc":
            order_by = Job.posted_on.desc()
        case _:
            abort(400, "Invalid sort parameter")

    page = request.args.get("page", type=int, default=1)
    if page <= 1:
        offset = 0
    else:
        offset = (page - 1) * PER_PAGE

    jobs = filter_jobs(
        min_salary=min_salary,
        include_no_salary=include_no_salary,
        posted_on=posted_on,
        tags=tags,
        is_remote=is_remote,
        offset=offset,
        limit=PER_PAGE,
        order_by=order_by,
    )
    total_jobs = count_jobs(
        min_salary=min_salary,
        include_no_salary=include_no_salary,
        posted_on=posted_on,
        tags=tags,
        is_remote=is_remote,
    )
    total_pages = math.ceil(total_jobs / PER_PAGE)
    page = max(1, min(page, total_pages))

    def get_pagination_url(page_num):
        url_args = {
            "page": page_num,
            "min_salary": request.args.get("min_salary"),
            "is_remote": request.args.get("is_remote"),
            "sort": request.args.get("sort"),
            "posted_on": request.args.get("posted_on"),
            "include_no_salary": request.args.get("include_no_salary"),
        }

        if tags := request.args.getlist("tags"):
            url_args["tags"] = tags

        return url_for("get_jobs", **url_args)

    return render_template(
        "jobs/index.html",
        jobs=jobs,
        available_tags=AVAILABLE_TAGS,
        page=page,
        per_page=PER_PAGE,
        current_filters={
            "min_salary": max(min_salary, Decimal("0")),
            "include_no_salary": include_no_salary,
            "tags": tags,
            "is_remote": is_remote,
            "posted_on": posted_on,
            "sort": sort,
        },
        pagination={
            "page": page,
            "per_page": PER_PAGE,
            "total_pages": total_pages,
            "total_jobs": total_jobs,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "get_url": get_pagination_url,
        },
    )
