import argparse

from .paths import DATA_DIR


def main():
    ap = argparse.ArgumentParser(prog="fiskpipe", description="FISKEØYE datapipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="kjør hele pipelinen for et område")
    r.add_argument("--area", required=True)
    r.add_argument("--skip-sentinel", action="store_true")
    r.add_argument("--skip-images", action="store_true")
    r.add_argument("--skip-gbif", action="store_true")
    sub.add_parser("index", help="skriv index.json på nytt")
    sub.add_parser("species", help="eksporter species.json fra species.yaml")
    a = ap.parse_args()
    if a.cmd == "run":
        from .area import run_area
        run_area(a.area, a.skip_sentinel, a.skip_images, a.skip_gbif)
    elif a.cmd == "index":
        from .export import write_index
        print(write_index())
    elif a.cmd == "species":
        from .area import load_config
        from .export import species_json
        _, sp = load_config()
        species_json(sp, DATA_DIR / "species.json")
        print("skrev", DATA_DIR / "species.json")
