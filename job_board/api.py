import math
from datetime import datetime
from decimal import Decimal

from flask import Flask
from flask import render_template
from flask import request
from flask import url_for

from job_board.query import count_jobs
from job_board.query import filter_jobs


app = Flask(__name__)

PER_PAGE = 12
AVAILABLE_TAGS = [
    "backend",
    "frontend",
    "data science",
    "node",
    "typescript",
    "python",
    "go",
    "react",
    "flask",
]


@app.route("/")
def get_jobs():
    salary = request.args.get("salary", type=Decimal, default=Decimal("20000"))
    posted_on = request.args.get("posted_on", type=datetime)
    tags = request.args.getlist("tags", type=str)
    if not tags:
        tags = ["backend"]
    is_remote = request.args.get("is_remote", type=bool, default=True)
    page = request.args.get("page", type=int, default=1)

    if page < 1:
        offset = 0
    else:
        offset = ((page - 1) * PER_PAGE) + 1

    jobs = filter_jobs(
        salary=salary,
        posted_on=posted_on,
        tags=tags,
        is_remote=is_remote,
        offset=offset,
        limit=PER_PAGE,
    )
    total_jobs = count_jobs(
        salary=salary,
        posted_on=posted_on,
        tags=tags,
        is_remote=is_remote,
    )
    total_pages = math.ceil(total_jobs / PER_PAGE)
    page = max(1, min(page, total_pages if total_pages > 0 else 1))

    def get_pagination_url(page_num):
        url_args = {
            "page": page_num,
            "salary": request.args.get("salary"),
            "is_remote": request.args.get("is_remote"),
        }

        if tags := request.args.getlist("tags"):
            url_args["tags"] = tags

        return url_for("get_jobs", **url_args)

    # Render template with jobs and filters
    return render_template(
        "jobs/index.html",
        jobs=jobs,
        available_tags=AVAILABLE_TAGS,
        page=page,
        per_page=PER_PAGE,
        current_filters={
            "salary": salary if salary > 0 else "",
            "tags": tags,
            "is_remote": is_remote,
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
