from flask import redirect, render_template, request

import markdown
from mdx_bleach.extension import BleachExtension
from mdx_bleach.whitelist import ALLOWED_TAGS
from mdx_bleach.whitelist import ALLOWED_ATTRIBUTES

from gerby.gerby import app
from gerby.database import *

import validators

def sfm(comment):
  attributes = ALLOWED_ATTRIBUTES
  attributes["span"] = ["class"]

  tags = ALLOWED_TAGS
  tags.append("span")

  bleach = BleachExtension(tags=tags, attributes=attributes)
  md = markdown.Markdown(extensions=[bleach])

  # Stacks flavored Markdown: only \ref{tag}, no longer \ref{label}
  references = re.compile(r"\\ref\{([0-9A-Z]{4})\}").findall(comment)
  for reference in references:
    comment = comment.replace("\\ref{" + reference + "}", "[<span class=\"tag\">" + reference + "</a>](/tag/" + reference + ")")
    # TODO use <span class="tag"> here (allow it in Bleach, etc.)

  comment = md.convert(comment)

  return comment

def getBreadcrumb(tag): # TODO get rid of circular dependency and redundant definition
  pieces = tag.ref.split(".")
  refs = [".".join(pieces[0:i]) for i in range(len(pieces) + 1)]

  tags = Tag.select().where(Tag.ref << refs, ~(Tag.type << ["item"]))

  return sorted(tags)

@app.route("/post-comment", methods=["POST"])
def post_comment():
  if not validators.email(request.form["mail"]):
    print("Invalid email address")

  site = request.form["site"]
  # if site is not a valid url just leave empty
  if not validators.url(request.form["site"]):
    site = ""

  if request.form["tag"] != request.form["check"]:
    print("Invalid captcha")


  # TODO what is the best way of knowing which tag page it was sent from?
  comment = Comment.create(
      tag=request.form["tag"],
      author=request.form["name"],
      site=site,
      email=request.form["mail"],
      comment=request.form["comment"])

  return ""

@app.route("/recent-comments.xml")
def show_comments_feed():
  comments = []
  for comment in Comment.select().order_by(Comment.id.desc()).paginate(1, 10):
    comment.comment = sfm(comment.comment)
    comments.append(comment)

  return render_template("comments.xml", comments=comments)


@app.route("/recent-comments", defaults={"page": 1})
@app.route("/recent-comments/<int:page>")
def show_comments(page):
  PERPAGE = 5

  comments = []
  for comment in Comment.select().order_by(Comment.id.desc()).paginate(page, PERPAGE):
    comment.comment = sfm(comment.comment)
    comment.breadcrumb = getBreadcrumb(comment.tag)

    comments.append(comment)

  return render_template(
      "comments.html",
      page=page,
      perpage=PERPAGE,
      comments=comments,
      count=Comment.select().count(),
      tags=Comment.select(Comment.tag).distinct().count())
