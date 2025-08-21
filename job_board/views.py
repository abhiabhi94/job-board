import math
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from enum import StrEnum

import humanize
import pycountry
from flask import abort
from flask import Flask
from flask import jsonify
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


API_PER_PAGE = 50
VIEWS_PER_PAGE = 12
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


class SortOption(StrEnum):
    SALARY_DESC = "salary_desc"
    POSTED_ON_DESC = "posted_on_desc"
    CREATED_AT_DESC = "created_at_desc"


@app.route("/.json")
@app.route("/")
def get_jobs():
    min_salary = request.args.get("min_salary", type=Decimal, default=Decimal("20000"))
    include_without_salary = request.args.get(
        "include_without_salary", type=bool, default=False
    )
    posted_on = request.args.get("posted_on", type=datetime)
    if not posted_on:
        posted_on = utcnow_naive() - timedelta(days=config.JOB_AGE_LIMIT_DAYS)
    tags = request.args.getlist("tags", type=str)
    is_remote = request.args.get("is_remote", type=bool, default=True)
    location_code = request.args.get("location", type=str)
    if location_code:
        location_code = location_code.upper()
        if not pycountry.countries.get(alpha_2=location_code):
            abort(400, "Invalid location code")

    sort = request.args.get("sort", type=str, default=SortOption.POSTED_ON_DESC)
    match sort:
        case SortOption.SALARY_DESC:
            order_by = Job.max_salary.desc()
        case SortOption.POSTED_ON_DESC:
            order_by = Job.posted_on.desc()
        case SortOption.CREATED_AT_DESC:
            order_by = Job.created_at.desc()
        case _:
            abort(400, "Invalid sort parameter")

    page = request.args.get("page", type=int, default=1)

    api = False
    per_page = VIEWS_PER_PAGE
    if request.url_rule.rule == "/.json":
        api = True
        per_page = API_PER_PAGE

    if page <= 1:
        offset = 0
    else:
        offset = (page - 1) * per_page

    jobs = filter_jobs(
        min_salary=min_salary,
        include_without_salary=include_without_salary,
        posted_on=posted_on,
        tags=tags,
        is_remote=is_remote,
        offset=offset,
        limit=per_page,
        order_by=order_by,
        location_code=location_code,
    )
    total_jobs = count_jobs(
        min_salary=min_salary,
        include_without_salary=include_without_salary,
        posted_on=posted_on,
        tags=tags,
        is_remote=is_remote,
        location_code=location_code,
    )
    total_pages = math.ceil(total_jobs / per_page)
    page = max(1, min(page, total_pages))

    if api:
        return jsonify(
            {
                "total_jobs": total_jobs,
                "per_page": per_page,
                "jobs": [
                    {
                        "id": job.id,
                        "title": job.title,
                        "link": job.link,
                        "min_salary": job.min_salary,
                        "max_salary": job.max_salary,
                        "posted_on": job.posted_on,
                        "tags": job.tags,
                        "is_remote": job.is_remote,
                        "locations": job.locations,
                        "portal_name": job.portal_name,
                        "company_name": job.company_name,
                        "description": job.description,
                    }
                    for job in jobs
                ],
            }
        )

    def get_pagination_url(page_num):
        url_args = {
            "page": page_num,
            "min_salary": request.args.get("min_salary"),
            "is_remote": request.args.get("is_remote"),
            "sort": request.args.get("sort"),
            "posted_on": request.args.get("posted_on"),
            "include_without_salary": request.args.get("include_without_salary"),
            "location": request.args.get("location"),
        }

        if tags := request.args.getlist("tags"):
            url_args["tags"] = tags

        return url_for("get_jobs", **url_args)

    return render_template(
        "jobs/index.html",
        jobs=jobs,
        available_tags=AVAILABLE_TAGS,
        page=page,
        per_page=per_page,
        SortOption=SortOption,
        current_filters={
            "min_salary": max(min_salary, Decimal("0")),
            "include_without_salary": include_without_salary,
            "tags": tags,
            "is_remote": is_remote,
            "posted_on": posted_on,
            "sort": sort,
            "location": location_code,
        },
        countries=[{"code": c.alpha_2, "name": c.name} for c in pycountry.countries],
        pagination={
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_jobs": total_jobs,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "get_url": get_pagination_url,
        },
        ENV=config.ENV,
    )
