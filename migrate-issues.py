#!/usr/bin/env python

import optparse
import sys
import re
import logging
import dateutil.parser

from github2.client import Github

import gdata.projecthosting.client
import gdata.projecthosting.data
import gdata.gauth
import gdata.client
import gdata.data

GITHUB_REQUESTS_PER_SECOND = 0.5
GOOGLE_MAX_RESULTS = 25

logging.basicConfig(level=logging.ERROR)


def output(string):
    sys.stdout.write(string)
    sys.stdout.flush()


def add_issue_to_github(issue):
    id = re.search('\d+$', issue.id.text).group(0)
    title = issue.title.text
    link = issue.link[1].href
    content = issue.content.text
    date = dateutil.parser.parse(issue.published.text).strftime('%B %d, %Y %H:%M:%S')
    body = '%s\n\n\n_Original issue: %s (%s)_' % (content, link, date)

    output('Adding issue %s' % (id))

    github_issue = None

    if options.dry_run is not True:
        github_issue = github.issues.open(github_project, title=title, body=body.encode('utf-8'))
        github.issues.add_label(github_project, github_issue.number, "imported")

    if issue.status.text.lower() in "invalid closed fixed wontfix verified done duplicate".lower():
        if options.dry_run is not True:
            github.issues.close(github_project, github_issue.number)

    # Add any labels
    if len(issue.label) > 0:
        output(', adding labels')
        for label in issue.label:
            if options.dry_run is not True:
                github.issues.add_label(github_project, github_issue.number, label.text.encode('utf-8'))
            output('.')

    # Add any comments
    start_index = 1
    max_results = GOOGLE_MAX_RESULTS
    while True:
        comments_feed = google.get_comments(google_project_name, id, query=gdata.projecthosting.client.Query(start_index=start_index, max_results=max_results))
        comments = filter(lambda e: e.content.text is not None, comments_feed.entry)
        if len(comments) == 0:
            break
        if start_index == 1:
            output(', adding comments')
        for comment in comments:
            add_comment_to_github(comment, github_issue)
            output('.')
        start_index += max_results
    output('\n')


def add_comment_to_github(comment, github_issue):
    id = re.search('\d+$', comment.id.text).group(0)
    author = comment.author[0].name.text
    date = dateutil.parser.parse(comment.published.text).strftime('%B %d, %Y %H:%M:%S')
    content = comment.content.text
    body = '_From %s on %s:_\n%s' % (author, date, content)

    logging.info('Adding comment %s', id)

    if options.dry_run is not True:
        github.issues.comment(github_project, github_issue.number, body.encode('utf-8'))


def process_issues():
    start_index = 1
    max_results = GOOGLE_MAX_RESULTS
    while True:
        issues_feed = google.get_issues(google_project_name, query=gdata.projecthosting.client.Query(start_index=start_index, max_results=max_results))
        if len(issues_feed.entry) == 0:
            break
        for issue in issues_feed.entry:
            add_issue_to_github(issue)
        start_index += max_results


if __name__ == "__main__":
    usage = "usage: %prog [options] <google_project_name> <github_api_token> <github_user_name> <github_project>"
    description = "Migrate all issues from a Google Code project to a Github project."
    parser = optparse.OptionParser(usage=usage, description=description)
    parser.add_option('-d', '--dry-run', action="store_true", dest="dry_run", help="Don't modify anything on Github")
    options, args = parser.parse_args()

    if len(args) != 4:
        parser.print_help()
        sys.exit()

    google_project_name, github_api_token, github_user_name, github_project = args

    google = gdata.projecthosting.client.ProjectHostingClient()
    github = Github(username=github_user_name, api_token=github_api_token, requests_per_second=GITHUB_REQUESTS_PER_SECOND)

    try:
        process_issues()
    except:
        parser.print_help()
        raise
