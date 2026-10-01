#!/usr/bin/env python3
"""Fetch the battle logs players sent as GitHub test reports into logs/ (which is not in git).

    python3 fetch_logs.py                    every issue labelled test-report, open or closed
    python3 fetch_logs.py --no-attachments   do not download cbp_battle_log.txt files dragged into an issue
    then:  python3 battle_logs.py ../logs/*.txt

Writes logs/issue_<number>_<author>.txt: the log lines found in the issue body (the "Battle log" section, fenced
blocks, or pasted bare), in comments by the same author, and in attached .txt files. A comment by someone else goes to
that person's own file. Only lines that have the shape of the log (docs/LOG_FORMAT.md) are kept, so nothing else a
person wrote ends up in logs/. Issues with no log are skipped.

If GitHub refuses a request for the rate limit the run stops there and exits 1. If the comments or an attached file
of an issue could not be read, a file already in logs/ for that issue is left as it is (it may be more complete), a
new one is written from what was read, and the run exits 1 at the end.

Standard library only. The repository is public, so no token is needed; GITHUB_TOKEN is used if set (60 requests an
hour without one, which is about 50 issues with comments).
"""
import json, os, re, sys, urllib.error, urllib.request

REPO = os.environ.get("CBP_REPO", "Spiesky/community-balance-patch")
API = "https://api.github.com/repos/" + REPO
LABEL = "test-report"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
MAX_ATTACHMENT = 5 * 1024 * 1024
# a file dragged into an issue: only GitHub's own attachment addresses, only .txt
ATTACHMENT = re.compile(r"https://github\.com/(?:user-attachments/files|%s/files)/\d+/[A-Za-z0-9._-]+\.txt" % re.escape(REPO))
HEAD = re.compile(r"#[a-z_]+;v\d+;")
UNIT = re.compile(r"[a-z];[0-9?]+;")       # a unit line: one letter, then a number or ?


def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": "cbp-fetch-logs", "Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read(MAX_ATTACHMENT + 1) if raw else r.read()      # the size limit is for attached files only
    if not raw:
        return json.loads(data.decode("utf-8"))
    if len(data) > MAX_ATTACHMENT:
        return ""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):        # re-saved as UTF-16 by an editor
        return data.decode("utf-16", errors="replace")
    return data.decode("utf-8-sig", errors="replace")


class RateLimited(Exception):
    pass


def limited(e):
    return isinstance(e, urllib.error.HTTPError) and e.code in (403, 429)


def log_lines(text):
    """The log blocks in a piece of text: header, unit lines, #end. Diagnostics and everything else are dropped."""
    out, inside = [], False
    for line in (text or "").replace("\r", "\n").split("\n"):
        line = line.strip().strip("\ufeff")
        if line.startswith("#error;") or line.startswith("#debug;"):
            continue
        if HEAD.match(line):
            inside = True
            out.append(line)
        elif inside and line == "#end":
            inside = False
            out.append(line)
        elif inside and UNIT.match(line):
            out.append(line)
    return out


def pieces(issue, attachments=True):
    """(texts, complete): (author, text) for the issue body, its comments and its attached files, and whether all
    of them could be read. Raises RateLimited when the API refuses for the rate limit: the next issues would fail too."""
    author = (issue.get("user") or {}).get("login") or "unknown"
    texts, complete = [(author, issue.get("body") or "")], True
    if issue.get("comments"):
        try:
            page = 1
            while True:
                batch = get(API + "/issues/%d/comments?per_page=100&page=%d" % (issue["number"], page))
                for c in batch:
                    texts.append(((c.get("user") or {}).get("login") or "unknown", c.get("body") or ""))
                if len(batch) < 100:
                    break
                page += 1
        except (urllib.error.URLError, ValueError, OSError) as e:
            if limited(e):
                raise RateLimited("issue %d: comments not read (%s)" % (issue["number"], e))
            complete = False
            print("issue %d: comments not read (%s)" % (issue["number"], e), file=sys.stderr)
    for who, text in list(texts):
        for url in (sorted(set(ATTACHMENT.findall(text))) if attachments else []):
            try:
                texts.append((who, get(url, raw=True)))
            except (urllib.error.URLError, OSError) as e:
                complete = False
                print("issue %d: attachment not read (%s)" % (issue["number"], e), file=sys.stderr)
    return texts, complete


def main():
    attachments = "--no-attachments" not in sys.argv
    issues, page = [], 1
    try:
        while True:
            batch = get(API + "/issues?labels=%s&state=all&per_page=100&page=%d" % (LABEL, page))
            issues += [i for i in batch if "pull_request" not in i]
            if len(batch) < 100:
                break
            page += 1
    except urllib.error.HTTPError as e:
        sys.exit("GitHub answered %s for %s%s" % (e.code, REPO, ": rate limit, set GITHUB_TOKEN or wait an hour" if e.code in (403, 429) else ""))
    except (urllib.error.URLError, ValueError, OSError) as e:
        sys.exit("could not reach GitHub: %s" % e)
    os.makedirs(OUT, exist_ok=True)
    ignore = os.path.join(OUT, ".gitignore")            # players' logs stay out of the repository
    if not os.path.exists(ignore):
        with open(ignore, "w") as fh:
            fh.write("*\n")
    written = kept = partial = 0
    stopped = None
    for issue in sorted(issues, key=lambda i: i.get("number", 0)):
        try:
            texts, complete = pieces(issue, attachments)
        except RateLimited as e:
            stopped = "%s. Rate limit: set GITHUB_TOKEN or wait an hour, then run again." % e
            break
        partial += not complete
        by_author = {}
        for who, text in texts:
            lines = log_lines(text)
            if lines:
                by_author.setdefault(who, []).extend(lines)
        for who, lines in by_author.items():
            name = "issue_%d_%s.txt" % (issue["number"], re.sub(r"[^A-Za-z0-9-]", "-", who))
            path = os.path.join(OUT, name)
            if not complete and os.path.exists(path):   # the file from an earlier run may have more in it
                kept += 1
                print("%s: not all of the issue could be read, the existing file is left as it is" % name)
                continue
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            written += 1
            print("%s: %d blocks%s" % (name, sum(1 for l in lines if l == "#end"), "" if complete else " (incomplete: run again)"))
    print("%d issues labelled %s, %d log files written to %s%s" % (
        len(issues), LABEL, written, OUT, ", %d existing files left as they were" % kept if kept else ""))
    if stopped:
        sys.exit("stopped early: " + stopped)
    if partial:
        sys.exit("%d issues were not read completely (comments or attachments): run again" % partial)


if __name__ == "__main__":
    main()
