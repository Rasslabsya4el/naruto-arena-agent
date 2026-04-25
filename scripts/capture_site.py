#!/usr/bin/env python3
import argparse
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from playwright.sync_api import Page, sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://www.naruto-arena.site"
CANONICAL_DOMAIN = "www.naruto-arena.site"
CAPTURE_RUNNER_VERSION = "capture_site.py:2"
RAW_RUNTIME_ROOT = REPO_ROOT / "snapshots" / "raw"
DEFAULT_OUT_DIR = RAW_RUNTIME_ROOT / "site_capture" / "latest"
REQUIRED_ENV_VARS = ("NARUTO_ARENA_USERNAME", "NARUTO_ARENA_PASSWORD")
HELP_EPILOG = f"""Authentication:
  - Reads {REQUIRED_ENV_VARS[0]} and {REQUIRED_ENV_VARS[1]} from the environment.
  - Uses an authenticated Playwright login on {BASE_URL} and never writes password material to snapshot artifacts.

Snapshot families:
  - Required: characters, missions, ladders, manual pages.
  - Optional boundary: current-account profile and clan capture (disable with --skip-profile).

Route strategy:
  - Uses authenticated Next data when available.
  - Falls back to rendered __NEXT_DATA__ when a route's Next JSON is missing, broken, or malformed.
  - Writes route-level capture metadata into each saved record and into manifest.routeCapture.

Safe inspection:
  - python scripts/capture_site.py --help
  - python scripts/capture_site.py --print-contract

Output policy:
  - Keep live captures under snapshots/raw/ so runtime artifacts stay out of tracked source paths.
"""


@dataclass(frozen=True)
class CaptureRecord:
    route: str
    source: str
    title: str | None
    page: str | None
    build_id: str | None
    page_props: dict[str, Any]
    captured_at: str
    final_url: str
    requested_url: str
    next_data_url: str | None
    capture_strategy: str
    fallback_used: bool
    fallback_reason: str | None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(REPO_ROOT.resolve(strict=False)).as_posix()
    except ValueError:
        return str(path)


def resolve_output_dir(raw_value: str) -> Path:
    candidate = Path(raw_value)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate

    resolved = candidate.resolve(strict=False)
    runtime_root = RAW_RUNTIME_ROOT.resolve(strict=False)

    try:
        resolved.relative_to(runtime_root)
    except ValueError as exc:
        raise SystemExit(
            f"--out-dir must stay under {display_path(RAW_RUNTIME_ROOT)} to avoid writing live captures into tracked source paths."
        ) from exc

    return resolved


def slugify_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().replace("&", " and ")
    normalized = re.sub(r"[â€™']", "", normalized)
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def summarize_exception(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {exc}"


def build_operator_contract(*, out_dir: Path, skip_profile: bool) -> dict[str, Any]:
    return {
        "captureRunnerVersion": CAPTURE_RUNNER_VERSION,
        "canonicalBaseUrl": BASE_URL,
        "canonicalDomain": CANONICAL_DOMAIN,
        "requiredEnvVars": list(REQUIRED_ENV_VARS),
        "authentication": {
            "mode": "authenticated_playwright_form_login",
            "passwordMaterialPersisted": False,
            "inspectionCommands": [
                "python scripts/capture_site.py --help",
                "python scripts/capture_site.py --print-contract",
            ],
        },
        "output": {
            "selectedOutDir": display_path(out_dir),
            "runtimeRoot": display_path(RAW_RUNTIME_ROOT),
        },
        "snapshotFamilies": {
            "characters": "required",
            "missions": "required",
            "ladders": "required",
            "manual": "required",
            "profile_and_clan": "skipped_by_operator" if skip_profile else "included",
        },
        "routeCapture": {
            "defaultStrategy": "authenticated_next_data_then_browser_fallback",
            "browserOnlyRoutes": ["/ninja-ladder", "/clan-ladder"],
            "fallbackMetadataFields": [
                "source",
                "capture.strategy",
                "capture.requestedUrl",
                "capture.nextDataUrl",
                "capture.fallbackUsed",
                "capture.fallbackReason",
            ],
        },
    }


def extract_next_data(page: Page) -> dict[str, Any]:
    data = page.evaluate(
        """() => {
            const node = document.querySelector('#__NEXT_DATA__');
            return node ? JSON.parse(node.textContent) : null;
        }"""
    )
    if not data:
        raise RuntimeError(f"Route {page.url} did not expose __NEXT_DATA__")
    return data


def route_to_data_path(route: str) -> str:
    stripped = route.strip("/")
    return "index" if not stripped else stripped


def build_authenticated_session(page: Page, username: str, password: str) -> tuple[requests.Session, str]:
    page.goto(BASE_URL, wait_until="networkidle", timeout=60_000)
    page.get_by_placeholder("username").fill(username)
    page.get_by_placeholder("*********").fill(password)
    page.locator('input[type="submit"][value="Login"]').click()
    page.get_by_text(f"Welcome, {username}").wait_for(timeout=20_000)

    next_data = extract_next_data(page)
    build_id = next_data.get("buildId")
    if not build_id:
        raise RuntimeError("Login succeeded but buildId was missing from __NEXT_DATA__")

    session = requests.Session()
    for cookie in page.context.storage_state().get("cookies", []):
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain"),
            path=cookie.get("path"),
        )

    return session, build_id


def capture_route_via_browser(
    page: Page,
    route: str,
    *,
    capture_strategy: str,
    next_data_url: str | None = None,
    fallback_reason: str | None = None,
) -> CaptureRecord:
    requested_url = f"{BASE_URL}{route}"
    page.goto(requested_url, wait_until="domcontentloaded", timeout=60_000)
    page.locator("#__NEXT_DATA__").wait_for(state="attached", timeout=15_000)
    next_data = extract_next_data(page)
    return CaptureRecord(
        route=route,
        source="browser-fallback",
        title=page.title(),
        page=next_data.get("page"),
        build_id=next_data.get("buildId"),
        page_props=next_data.get("props", {}).get("pageProps", {}),
        captured_at=now_iso(),
        final_url=page.url,
        requested_url=requested_url,
        next_data_url=next_data_url,
        capture_strategy=capture_strategy,
        fallback_used=fallback_reason is not None,
        fallback_reason=fallback_reason,
    )


def capture_route(
    session: requests.Session,
    build_id: str,
    route: str,
    browser_page: Page | None = None,
) -> CaptureRecord:
    data_path = route_to_data_path(route)
    data_url = f"{BASE_URL}/_next/data/{build_id}/{data_path}.json"
    requested_url = f"{BASE_URL}{route}"

    try:
        response = session.get(data_url, timeout=60)
        response.raise_for_status()
        payload = response.json()
        page_props = payload.get("pageProps")
        if not isinstance(page_props, dict):
            raise RuntimeError(f"Route {route} returned malformed pageProps payload")
        return CaptureRecord(
            route=route,
            source="next-data",
            title=None,
            page=route,
            build_id=build_id,
            page_props=page_props,
            captured_at=now_iso(),
            final_url=requested_url,
            requested_url=requested_url,
            next_data_url=data_url,
            capture_strategy="authenticated_next_data_then_browser_fallback",
            fallback_used=False,
            fallback_reason=None,
        )
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        if browser_page is None:
            raise
        return capture_route_via_browser(
            browser_page,
            route,
            capture_strategy="authenticated_next_data_then_browser_fallback",
            next_data_url=data_url,
            fallback_reason=summarize_exception(exc),
        )


def save_record(base_dir: Path, relative_path: str, record: CaptureRecord) -> None:
    write_json(
        base_dir / relative_path,
        {
            "route": record.route,
            "source": record.source,
            "final_url": record.final_url,
            "title": record.title,
            "page": record.page,
            "buildId": record.build_id,
            "capturedAt": record.captured_at,
            "pageProps": record.page_props,
            "capture": {
                "strategy": record.capture_strategy,
                "requestedUrl": record.requested_url,
                "nextDataUrl": record.next_data_url,
                "fallbackUsed": record.fallback_used,
                "fallbackReason": record.fallback_reason,
            },
        },
    )


def append_route_capture(
    manifest: dict[str, Any],
    *,
    family: str,
    relative_path: str,
    record: CaptureRecord,
) -> None:
    manifest.setdefault("routeCapture", []).append(
        {
            "family": family,
            "file": relative_path,
            "route": record.route,
            "source": record.source,
            "finalUrl": record.final_url,
            "strategy": record.capture_strategy,
            "requestedUrl": record.requested_url,
            "nextDataUrl": record.next_data_url,
            "fallbackUsed": record.fallback_used,
            "fallbackReason": record.fallback_reason,
        }
    )


def save_record_and_track(
    base_dir: Path,
    relative_path: str,
    record: CaptureRecord,
    manifest: dict[str, Any],
    *,
    family: str,
) -> None:
    save_record(base_dir, relative_path, record)
    append_route_capture(manifest, family=family, relative_path=relative_path, record=record)


def capture_characters(
    session: requests.Session,
    build_id: str,
    page: Page,
    base_dir: Path,
    manifest: dict[str, Any],
) -> None:
    overview = capture_route(session, build_id, "/characters-and-skills", page)
    save_record_and_track(
        base_dir,
        "characters/overview.json",
        overview,
        manifest,
        family="characters_overview",
    )

    detail_files: list[dict[str, Any]] = []
    for index, char in enumerate(overview.page_props.get("chars", [])):
        name = char.get("name", f"character-{index}")
        slug = slugify_name(name) or f"character-{index}"
        relative_path = f"characters/details/{index:03d}-{slug}.json"
        write_json(
            base_dir / relative_path,
            {
                "sourceRoute": overview.route,
                "source": overview.source,
                "buildId": overview.build_id,
                "capturedAt": overview.captured_at,
                "sourceIndex": index,
                "character": char,
            },
        )
        detail_files.append(
            {
                "index": index,
                "name": name,
                "file": relative_path,
            }
        )

    write_json(base_dir / "characters/index.json", detail_files)
    manifest["characters"] = {
        "overview_count": len(overview.page_props.get("chars", [])),
        "detail_files": len(detail_files),
        "detail_source": "overview.pageProps.chars",
    }


def capture_missions(
    session: requests.Session,
    build_id: str,
    page: Page,
    base_dir: Path,
    manifest: dict[str, Any],
) -> None:
    overview = capture_route(session, build_id, "/ninja-missions", page)
    save_record_and_track(
        base_dir,
        "missions/overview.json",
        overview,
        manifest,
        family="missions_overview",
    )

    anime_missions = overview.page_props.get("animeMissions", {})
    group_slugs = sorted(
        value["linkTo"]
        for value in anime_missions.values()
        if isinstance(value, dict) and value.get("linkTo")
    )

    detail_slugs: list[str] = []
    for group_slug in group_slugs:
        group_record = capture_route(session, build_id, f"/missions/{group_slug}", page)
        save_record_and_track(
            base_dir,
            f"missions/groups/{group_slug}.json",
            group_record,
            manifest,
            family="mission_group",
        )
        for item in group_record.page_props.get("animeMissions", []):
            link_to = item.get("linkTo")
            if link_to:
                detail_slugs.append(link_to)

    detail_slugs = sorted(set(detail_slugs))
    for slug in detail_slugs:
        detail_record = capture_route(session, build_id, f"/mission/{slug}", page)
        save_record_and_track(
            base_dir,
            f"missions/details/{slug}.json",
            detail_record,
            manifest,
            family="mission_detail",
        )

    manifest["missions"] = {
        "group_routes": len(group_slugs),
        "detail_routes": len(detail_slugs),
        "group_slugs": group_slugs,
        "detail_slugs": detail_slugs,
    }


def capture_ladders(
    session: requests.Session,
    build_id: str,
    page: Page,
    base_dir: Path,
    manifest: dict[str, Any],
) -> None:
    ninja = capture_route_via_browser(
        page,
        "/ninja-ladder",
        capture_strategy="browser_only_route",
    )
    clan = capture_route_via_browser(
        page,
        "/clan-ladder",
        capture_strategy="browser_only_route",
    )
    save_record_and_track(
        base_dir,
        "ladders/ninja.json",
        ninja,
        manifest,
        family="ninja_ladder",
    )
    save_record_and_track(
        base_dir,
        "ladders/clan.json",
        clan,
        manifest,
        family="clan_ladder",
    )
    manifest["ladders"] = {
        "ninja_rows": len(ninja.page_props.get("topPlayers", [])),
        "clan_rows": len(clan.page_props.get("topPlayers", [])),
    }


def capture_profile(
    session: requests.Session,
    build_id: str,
    page: Page,
    base_dir: Path,
    manifest: dict[str, Any],
    username: str,
) -> None:
    profile_file = slugify_name(username) or username
    profile = capture_route(session, build_id, f"/profile/{quote(username)}", page)
    save_record_and_track(
        base_dir,
        f"profiles/{profile_file}.json",
        profile,
        manifest,
        family="profile",
    )

    clan_name = (
        (profile.page_props.get("userInfor", {}) or {})
        .get("target_account", {})
        .get("clanInfor")
        or {}
    ).get("clanName")

    clan_saved = None
    if clan_name:
        clan_route = f"/clan/{quote(clan_name)}"
        clan_file = slugify_name(clan_name) or quote(clan_name, safe="")
        try:
            clan = capture_route(session, build_id, clan_route, page)
            save_record_and_track(
                base_dir,
                f"clans/{clan_file}.json",
                clan,
                manifest,
                family="clan",
            )
            clan_saved = clan_name
        except requests.RequestException:
            clan_saved = None
        except RuntimeError:
            clan_saved = None

    manifest["profile"] = {
        "status": "captured",
        "profile_file": f"profiles/{profile_file}.json",
        "clan_route_captured": clan_saved,
    }


def capture_manual(
    session: requests.Session,
    build_id: str,
    page: Page,
    base_dir: Path,
    manifest: dict[str, Any],
) -> None:
    basics = capture_route(session, build_id, "/the-basics", page)
    manual = capture_route(session, build_id, "/game-manual", page)
    save_record_and_track(
        base_dir,
        "manual/the-basics.json",
        basics,
        manifest,
        family="manual",
    )
    save_record_and_track(
        base_dir,
        "manual/game-manual.json",
        manual,
        manifest,
        family="manual",
    )
    manifest["manual"] = {
        "captured": ["/the-basics", "/game-manual"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture Naruto Arena site data via authenticated Playwright session.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--out-dir",
        default=display_path(DEFAULT_OUT_DIR),
        help="Directory for captured JSON artifacts. Must stay under snapshots/raw/.",
    )
    parser.add_argument(
        "--skip-profile",
        action="store_true",
        help="Skip current-account profile and clan capture.",
    )
    parser.add_argument(
        "--print-contract",
        action="store_true",
        help="Print the authenticated raw-ingestion contract and exit without requiring login credentials.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = resolve_output_dir(args.out_dir)

    if args.print_contract:
        print(json.dumps(build_operator_contract(out_dir=out_dir, skip_profile=args.skip_profile), ensure_ascii=False, indent=2))
        return

    username = require_env(REQUIRED_ENV_VARS[0])
    password = require_env(REQUIRED_ENV_VARS[1])

    manifest: dict[str, Any] = {
        "baseUrl": BASE_URL,
        "capturedAt": now_iso(),
        "username": username,
        "captureContract": build_operator_contract(out_dir=out_dir, skip_profile=args.skip_profile),
        "routeCapture": [],
    }

    error: Exception | None = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            session, build_id = build_authenticated_session(page, username, password)
            manifest["buildId"] = build_id
            capture_characters(session, build_id, page, out_dir, manifest)
            capture_missions(session, build_id, page, out_dir, manifest)
            capture_ladders(session, build_id, page, out_dir, manifest)
            capture_manual(session, build_id, page, out_dir, manifest)
            if not args.skip_profile:
                capture_profile(session, build_id, page, out_dir, manifest, username)
            else:
                manifest["profile"] = {
                    "status": "skipped",
                    "profile_file": None,
                    "clan_route_captured": None,
                    "reason": "--skip-profile",
                }
        except Exception as exc:
            manifest["error"] = str(exc)
            error = exc
        finally:
            browser.close()

    write_json(out_dir / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

    if error:
        raise error


if __name__ == "__main__":
    main()
