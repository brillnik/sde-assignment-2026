import argparse
import os

from .loop import Controller


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--db", default=os.environ.get("CTL_DB", "state/controller.db"))
    ap.add_argument("--view-port", type=int, default=int(os.environ.get("CTL_VIEW_PORT", "8800")))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.db) or ".", exist_ok=True)
    Controller(a.url, a.db, a.view_port).run()


if __name__ == "__main__":
    main()
