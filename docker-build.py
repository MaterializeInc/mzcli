#!/usr/bin/env python3

import subprocess
import datetime

REPO = "materialize/mzcli"


def main():
    now = datetime.date.today().isoformat()
    build()

    response = input("Run docker push [Y/n] ").strip()
    if not response or not response.startswith("n"):
        push()


def build():
    run("docker", "build", "-t", REPO, ".")
    run("docker", "tag", REPO, f"{REPO}:{now}")


def push():
    for tag in "latest", now:
        run("docker", "push", f"{REPO}:{tag}")


def run(*args):
    subprocess.run(args)


if __name__ == "__main__":
    main()
