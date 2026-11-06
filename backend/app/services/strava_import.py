import csv
import gzip
import hashlib
import io
import re
import stat
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath
from typing import BinaryIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import fitdecode
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

MAX_ARCHIVE_BYTES = 250 * 1024 * 1024
MAX_ENTRIES = 10_000
MAX_MEMBER_BYTES = 100 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1000
MAX_CSV_ROWS = 50_000
MAX_SAMPLES_PER_ACTIVITY = 20_000
MAX_SAMPLES_PER_ARCHIVE = 250_000
MAX_GZIP_MEMBER_BYTES = 100 * 1024 * 1024
MAX_CSV_FIELD_SIZE = 256 * 1024
csv.field_size_limit(MAX_CSV_FIELD_SIZE)

ACTIVITY_TYPE_MAP = {
    "run": "run",
    "trailrun": "run",
    "virtualrun": "run",
    "walk": "walk",
    "hike": "hike",
    "ride": "ride",
    "virtualride": "ride",
    "ebikeride": "ride",
    "gravelride": "ride",
    "mountainbikeride": "ride",
    "swim": "swim",
    "weighttraining": "strength",
    "strengthtraining": "strength",
    "yoga": "yoga",
    "workout": "other",
    "other": "other",
}


class StravaArchiveError(ValueError):
    """The upload is not a safe, supported Strava activity archive."""


@dataclass
class ParsedSample:
    sample_index: int
    latitude: Decimal
    longitude: Decimal
    recorded_at: datetime | None = None
    elevation_m: Decimal | None = None
    heart_rate: int | None = None
    cadence: Decimal | None = None


@dataclass
class ParsedActivity:
    item_index: int
    source_key: str
    fallback_fingerprint: str
    external_activity_id: str | None
    status: str
    selected: bool
    title: str
    activity_type: str | None
    source_activity_type: str | None
    started_at: datetime | None
    duration_seconds: int | None
    moving_duration_seconds: int | None
    distance_m: Decimal | None
    elevation_gain_m: Decimal | None
    average_speed_mps: Decimal | None
    max_speed_mps: Decimal | None
    average_heart_rate: int | None
    max_heart_rate: int | None
    average_cadence: Decimal | None
    calories: int | None
    description: str | None
    source_metadata: dict = field(default_factory=dict)
    samples: list[ParsedSample] = field(default_factory=list)
    error_message: str | None = None


@dataclass
class ParsedArchive:
    activities: list[ParsedActivity]
    total_rows: int
    duplicates_in_archive: int = 0
    errors: list[str] = field(default_factory=list)


def parse_strava_archive(archive_bytes: bytes, timezone_name: str) -> ParsedArchive:
    if not archive_bytes or len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise StravaArchiveError("Archive is empty or exceeds the 250 MiB upload limit")
    try:
        local_timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise StravaArchiveError("Choose a valid IANA timezone for Strava's local activity dates") from None

    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except (zipfile.BadZipFile, OSError):
        raise StravaArchiveError("The uploaded file is not a valid ZIP archive") from None

    with archive:
        members = _validate_archive(archive)
        member_lookup = {name.casefold(): info for name, info in members.items()}
        csv_candidates = []
        for normalized_name, info in members.items():
            if not normalized_name.casefold().endswith(".csv") or info.file_size > MAX_MEMBER_BYTES:
                continue
            try:
                with archive.open(info) as stream:
                    header_text = stream.read(1024 * 1024).decode("utf-8-sig", errors="replace")
                headers = next(csv.reader(io.StringIO(header_text)), [])
            except (OSError, UnicodeError, csv.Error, StopIteration):
                continue
            normalized_headers = {_header_key(header) for header in headers}
            if {"activityname", "activitytype", "activitydate"} <= normalized_headers or {
                "activityname", "type", "activitydate"
            } <= normalized_headers:
                if "activityid" in normalized_headers or "filename" in normalized_headers:
                    csv_candidates.append((normalized_name, info, headers))

        if not csv_candidates:
            raise StravaArchiveError("No activity CSV with recognizable Strava activity columns was found")
        csv_candidates.sort(key=lambda candidate: (PurePosixPath(candidate[0]).name.casefold() != "activities.csv", candidate[0].casefold()))

        parsed: list[ParsedActivity] = []
        all_errors: list[str] = []
        total_rows = 0
        seen_keys: set[str] = set()
        duplicates = 0
        total_samples = 0

        for csv_name, info, discovered_headers in csv_candidates:
            with archive.open(info) as binary_stream:
                text_stream = io.TextIOWrapper(binary_stream, encoding="utf-8-sig", errors="replace", newline="")
                reader = csv.reader(text_stream)
                headers = next(reader, [])
                indexes = _header_indexes(headers)
                row_count = 0
                for row in reader:
                    row_count += 1
                    total_rows += 1
                    if total_rows > MAX_CSV_ROWS:
                        raise StravaArchiveError(f"Activity CSV exceeds the {MAX_CSV_ROWS} row limit")
                    item = _parse_csv_row(row, indexes, row_count, csv_name, local_timezone)
                    if item.source_key in seen_keys:
                        duplicates += 1
                        continue
                    seen_keys.add(item.source_key)

                    track_name = _find_track_member(item.source_metadata.get("source_filename"), item.external_activity_id, member_lookup)
                    if track_name:
                        track_info = member_lookup[track_name.casefold()]
                        item.source_metadata["track_filename"] = track_name
                        item.source_metadata["track_format"] = _track_format(track_name)
                        if total_samples >= MAX_SAMPLES_PER_ARCHIVE:
                            item.source_metadata["route_samples_skipped_global_limit"] = True
                        else:
                            try:
                                route_bytes = _read_member_bounded(archive, track_info, MAX_MEMBER_BYTES)
                                track_samples, track_started_at = _parse_track(track_name, route_bytes)
                                if track_started_at is not None and item.source_metadata.get("csv_start_local"):
                                    item.started_at = _localize_csv_date(
                                        item.source_metadata["csv_start_local"],
                                        local_timezone,
                                        reference_utc=track_started_at,
                                    ) or item.started_at
                                available = MAX_SAMPLES_PER_ARCHIVE - total_samples
                                item.samples = track_samples[: min(MAX_SAMPLES_PER_ACTIVITY, available)]
                                total_samples += len(item.samples)
                                item.source_metadata["track_samples_truncated"] = len(item.samples) < len(track_samples)
                            except (StravaArchiveError, DefusedXmlException, fitdecode.FitError, OSError, ValueError, gzip.BadGzipFile, EOFError) as error:
                                item.source_metadata["track_error"] = _safe_error(error)
                    parsed.append(item)
                text_stream.detach()

        if not parsed:
            raise StravaArchiveError("No activity rows were found in the Strava CSV")
        return ParsedArchive(activities=parsed, total_rows=total_rows, duplicates_in_archive=duplicates, errors=all_errors)


def _validate_archive(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    if len(infos) > MAX_ENTRIES:
        raise StravaArchiveError(f"Archive has too many entries (maximum {MAX_ENTRIES})")
    total_size = 0
    members: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        normalized = _safe_member_name(info.filename)
        if info.is_dir():
            continue
        if info.flag_bits & 0x1:
            raise StravaArchiveError("Encrypted ZIP entries are not supported")
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            raise StravaArchiveError("ZIP symbolic links are not supported")
        if info.file_size > MAX_MEMBER_BYTES:
            raise StravaArchiveError("An archive member exceeds the 100 MiB member limit")
        if info.file_size and not info.compress_size:
            raise StravaArchiveError("Archive contains an invalid compressed entry")
        if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
            raise StravaArchiveError("Archive contains a suspicious compression ratio")
        total_size += info.file_size
        if total_size > MAX_TOTAL_UNCOMPRESSED:
            raise StravaArchiveError("Archive exceeds the 1 GiB expanded-data limit")
        key = normalized.casefold()
        if key in members:
            raise StravaArchiveError("Archive contains duplicate member paths")
        members[key] = info
    return members


def _safe_member_name(filename: str) -> str:
    if not filename or "\x00" in filename or "\\" in filename:
        raise StravaArchiveError("Archive contains an invalid member path")
    path = PurePosixPath(filename)
    if path.is_absolute() or any(part in {"..", ""} for part in path.parts) or re.match(r"^[A-Za-z]:", filename):
        raise StravaArchiveError("Archive contains an unsafe member path")
    return str(path)


def _header_key(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.strip().casefold())


def _header_indexes(headers: list[str]) -> dict[str, list[int]]:
    indexes: dict[str, list[int]] = {}
    for index, header in enumerate(headers):
        indexes.setdefault(_header_key(header), []).append(index)
    return indexes


def _cell(row: list[str], indexes: dict[str, list[int]], *keys: str, prefer_last: bool = False) -> str:
    positions: list[int] = []
    for key in keys:
        positions.extend(indexes.get(_header_key(key), []))
    if prefer_last:
        positions.reverse()
    for position in positions:
        if position < len(row) and row[position].strip():
            return row[position].strip()
    return ""


def _parse_decimal(value: str) -> Decimal | None:
    if not value:
        return None
    try:
        result = Decimal(value.strip())
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _parse_seconds(value: str) -> int | None:
    number = _parse_decimal(value)
    if number is not None and number >= 0:
        return int(number)
    parts = value.strip().split(":")
    try:
        if len(parts) == 3:
            return int(Decimal(parts[0]) * 3600 + Decimal(parts[1]) * 60 + Decimal(parts[2]))
        if len(parts) == 2:
            return int(Decimal(parts[0]) * 60 + Decimal(parts[1]))
    except (InvalidOperation, ValueError):
        return None
    return None


def _parse_date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    iso_value = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(iso_value)
    except ValueError:
        pass
    for format_string in ("%b %d, %Y, %I:%M:%S %p", "%B %d, %Y, %I:%M:%S %p"):
        try:
            return datetime.strptime(value, format_string)
        except ValueError:
            continue
    return None


def _localize_csv_date(value: str, local_timezone: ZoneInfo, reference_utc: datetime | None = None) -> datetime | None:
    parsed = _parse_date(value)
    if parsed is None:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc)
    candidates = [parsed.replace(tzinfo=local_timezone, fold=fold).astimezone(timezone.utc) for fold in (0, 1)]
    if reference_utc is not None and candidates[0] != candidates[1]:
        reference = reference_utc.astimezone(timezone.utc)
        return min(candidates, key=lambda candidate: abs((candidate - reference).total_seconds()))
    return candidates[0]


def _activity_type(source_type: str) -> tuple[str, bool]:
    normalized = re.sub(r"[^a-z]", "", source_type.casefold())
    mapped = ACTIVITY_TYPE_MAP.get(normalized)
    return (mapped or "other", mapped is not None)


def _fallback_fingerprint(activity_type: str, started_at: datetime | None, duration: int | None, distance: Decimal | None) -> str:
    normalized_start = None
    if started_at is not None:
        normalized_start = started_at.replace(tzinfo=timezone.utc) if started_at.tzinfo is None else started_at.astimezone(timezone.utc)
    normalized_distance = format(distance.quantize(Decimal("0.01")), "f") if distance is not None else ""
    payload = "|".join((activity_type.casefold(), normalized_start.isoformat(timespec="seconds") if normalized_start else "", str(int(duration or 0)), normalized_distance))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def activity_fingerprint(activity_type: str, started_at: datetime | None, duration: int | None, distance: Decimal | None) -> str:
    return _fallback_fingerprint(activity_type, started_at, duration, distance)


def _parse_csv_row(row: list[str], indexes: dict[str, list[int]], row_number: int, csv_name: str, local_timezone: ZoneInfo) -> ParsedActivity:
    external_id = _cell(row, indexes, "Activity ID", "ID") or None
    title = _cell(row, indexes, "Activity Name", "Name")[:160] or (f"Strava activity {external_id}" if external_id else "Unnamed Strava activity")
    source_type = _cell(row, indexes, "Activity Type", "Type")
    activity_type, is_supported = _activity_type(source_type)
    local_date = _cell(row, indexes, "Activity Date", "Start Date", "Date")
    started_at = _localize_csv_date(local_date, local_timezone)
    elapsed = _parse_seconds(_cell(row, indexes, "Elapsed Time", "Duration"))
    moving = _parse_seconds(_cell(row, indexes, "Moving Time"))
    distance_columns = indexes.get("distance", [])
    distance = None
    if distance_columns:
        distance = _parse_decimal(row[distance_columns[-1]]) if distance_columns[-1] < len(row) else None
        if distance is None and len(distance_columns) == 1:
            distance = _parse_decimal(row[distance_columns[0]])
            if distance is not None:
                speed = _parse_decimal(_cell(row, indexes, "Average Speed"))
                seconds = moving or elapsed
                if speed is not None and seconds:
                    meters_error = abs(float(distance) / seconds - float(speed))
                    km_error = abs(float(distance) * 1000 / seconds - float(speed))
                    if km_error < meters_error:
                        distance *= 1000
    distance = distance if distance is not None and distance > 0 else None
    elevation = _parse_decimal(_cell(row, indexes, "Elevation Gain", "Total Elevation Gain"))
    average_hr = _parse_integer(_cell(row, indexes, "Average Heart Rate", "Avg Heart Rate"))
    max_hr = _parse_integer(_cell(row, indexes, "Max Heart Rate", "Maximum Heart Rate"))
    calories = _parse_integer(_cell(row, indexes, "Calories"))
    average_speed = _parse_decimal(_cell(row, indexes, "Average Speed"))
    max_speed = _parse_decimal(_cell(row, indexes, "Max Speed", "Maximum Speed"))
    cadence = _parse_decimal(_cell(row, indexes, "Average Cadence", "Avg Cadence"))
    description = _cell(row, indexes, "Activity Description", "Description")[:4000] or None
    source_filename = _cell(row, indexes, "Filename")
    fingerprint = _fallback_fingerprint(activity_type, started_at, elapsed, distance)
    key = f"strava:{external_id}" if external_id else f"fingerprint:{fingerprint}"
    invalid = started_at is None or elapsed is None or elapsed <= 0 or not title
    unsupported = not is_supported
    status = "invalid" if invalid else "unsupported" if unsupported else "ready"
    errors = []
    if started_at is None:
        errors.append("Activity date could not be parsed")
    if elapsed is None or elapsed <= 0:
        errors.append("Elapsed duration is missing or invalid")
    metadata = {
        "csv_source": PurePosixPath(csv_name).name,
        "source_filename": source_filename,
        "timezone": str(local_timezone),
        "csv_start_local": local_date,
        "source_type_fallback": unsupported,
        "distance_columns": len(distance_columns),
        "distance_unit_inferred": len(distance_columns) == 1,
    }
    return ParsedActivity(
        item_index=row_number,
        source_key=key,
        fallback_fingerprint=fingerprint,
        external_activity_id=external_id,
        status=status,
        selected=status == "ready",
        title=title,
        activity_type=activity_type,
        source_activity_type=source_type or None,
        started_at=started_at,
        duration_seconds=elapsed,
        moving_duration_seconds=moving,
        distance_m=distance,
        elevation_gain_m=elevation if elevation is not None and elevation >= 0 else None,
        average_speed_mps=average_speed if average_speed is not None and average_speed >= 0 else None,
        max_speed_mps=max_speed if max_speed is not None and max_speed >= 0 else None,
        average_heart_rate=average_hr,
        max_heart_rate=max_hr,
        average_cadence=cadence if cadence is not None and cadence >= 0 else None,
        calories=calories if calories is not None and calories >= 0 else None,
        description=description,
        source_metadata=metadata,
        error_message="; ".join(errors) or None,
    )


def _parse_integer(value: str) -> int | None:
    number = _parse_decimal(value)
    return int(number) if number is not None and number >= 0 else None


def _find_track_member(source_filename: str | None, external_id: str | None, members: dict[str, zipfile.ZipInfo]) -> str | None:
    if source_filename:
        try:
            requested = _safe_member_name(source_filename.replace("\\", "/")).casefold()
        except StravaArchiveError:
            requested = ""
        if requested in members:
            return requested
        basename = PurePosixPath(requested).name
        matches = [name for name in members if PurePosixPath(name).name.casefold() == basename]
        if len(matches) == 1:
            return matches[0]
    if external_id:
        matches = [name for name in members if _track_stem(name) == external_id]
        if len(matches) == 1:
            return matches[0]
    return None


def _track_stem(filename: str) -> str:
    basename = PurePosixPath(filename).name.casefold()
    for suffix in (".fit.gz", ".tcx.gz", ".gpx.gz", ".fit", ".tcx", ".gpx"):
        if basename.endswith(suffix):
            return basename[: -len(suffix)]
    return ""


def _track_format(filename: str) -> str:
    lower = filename.casefold()
    for suffix, format_name in ((".fit.gz", "fit"), (".fit", "fit"), (".tcx.gz", "tcx"), (".tcx", "tcx"), (".gpx.gz", "gpx"), (".gpx", "gpx")):
        if lower.endswith(suffix):
            return format_name
    raise StravaArchiveError("Track file format is unsupported")


def _read_member_bounded(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
    output = bytearray()
    with archive.open(info) as stream:
        while chunk := stream.read(64 * 1024):
            output.extend(chunk)
            if len(output) > limit:
                raise StravaArchiveError("Activity track file exceeds the per-file size limit")
    data = bytes(output)
    if info.filename.casefold().endswith(".gz"):
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            expanded = bytearray()
            while chunk := stream.read(64 * 1024):
                expanded.extend(chunk)
                if len(expanded) > MAX_GZIP_MEMBER_BYTES:
                    raise StravaArchiveError("Compressed activity track expands beyond the 100 MiB limit")
            return bytes(expanded)
    return data


def _parse_track(filename: str, payload: bytes) -> tuple[list[ParsedSample], datetime | None]:
    format_name = _track_format(filename)
    if format_name == "gpx":
        samples = _parse_gpx(payload)
    elif format_name == "tcx":
        samples = _parse_tcx(payload)
    elif format_name == "fit":
        samples = _parse_fit(payload)
    else:
        raise StravaArchiveError("Track file format is unsupported")
    if any(sample.recorded_at is not None for sample in samples):
        samples.sort(key=lambda sample: (sample.recorded_at is None, sample.recorded_at or datetime.max.replace(tzinfo=timezone.utc), sample.sample_index))
        for sample_index, sample in enumerate(samples):
            sample.sample_index = sample_index
    if len(samples) > MAX_SAMPLES_PER_ACTIVITY:
        samples = samples[:MAX_SAMPLES_PER_ACTIVITY]
    start = next((sample.recorded_at for sample in samples if sample.recorded_at is not None), None)
    return samples, start


def _parse_gpx(payload: bytes) -> list[ParsedSample]:
    samples = []
    for _, element in ElementTree.iterparse(io.BytesIO(payload), events=("end",)):
        if _local_name(element.tag) != "trkpt":
            continue
        sample = _sample_from_coordinates(element.attrib.get("lat"), element.attrib.get("lon"), element)
        if sample is not None:
            sample.sample_index = len(samples)
            samples.append(sample)
            if len(samples) > MAX_SAMPLES_PER_ACTIVITY:
                return samples
        element.clear()
    return samples


def _parse_tcx(payload: bytes) -> list[ParsedSample]:
    samples = []
    for _, element in ElementTree.iterparse(io.BytesIO(payload), events=("end",)):
        if _local_name(element.tag) != "Trackpoint":
            continue
        values = {_local_name(child.tag): child.text for child in element.iter() if child is not element and child.text}
        latitude = values.get("LatitudeDegrees")
        longitude = values.get("LongitudeDegrees")
        sample = _sample_from_values(latitude, longitude, values)
        if sample is not None:
            sample.sample_index = len(samples)
            samples.append(sample)
            if len(samples) > MAX_SAMPLES_PER_ACTIVITY:
                return samples
        element.clear()
    return samples


def _parse_fit(payload: bytes) -> list[ParsedSample]:
    samples = []
    with fitdecode.FitReader(io.BytesIO(payload), processor=fitdecode.StandardUnitsDataProcessor()) as reader:
        for frame in reader:
            if not isinstance(frame, fitdecode.FitDataMessage) or frame.name != "record":
                continue
            latitude = _fit_value(frame, "position_lat")
            longitude = _fit_value(frame, "position_long")
            if latitude is None or longitude is None:
                continue
            sample = _sample_from_values(
                latitude,
                longitude,
                {
                    "timestamp": _fit_value(frame, "timestamp"),
                    "altitude": _fit_value(frame, "enhanced_altitude") or _fit_value(frame, "altitude"),
                    "heart_rate": _fit_value(frame, "heart_rate"),
                    "cadence": _fit_value(frame, "cadence"),
                },
            )
            if sample is not None:
                sample.sample_index = len(samples)
                samples.append(sample)
                if len(samples) > MAX_SAMPLES_PER_ACTIVITY:
                    return samples
    return samples


def _fit_value(frame: fitdecode.FitDataMessage, name: str):
    return frame.get_value(name) if frame.has_field(name) else None


def _sample_from_coordinates(latitude: str | None, longitude: str | None, element) -> ParsedSample | None:
    values = {_local_name(child.tag): child.text for child in element.iter() if child is not element and child.text}
    return _sample_from_values(latitude, longitude, values)


def _sample_from_values(latitude, longitude, values: dict) -> ParsedSample | None:
    lat = _parse_decimal(str(latitude)) if latitude is not None else None
    lon = _parse_decimal(str(longitude)) if longitude is not None else None
    if lat is None or lon is None or lat < -90 or lat > 90 or lon < -180 or lon > 180:
        return None
    timestamp = _parse_date(str(values.get("time") or values.get("Time") or values.get("timestamp") or ""))
    if timestamp is not None and timestamp.tzinfo is None:
        return None
    elevation = _parse_decimal(str(values.get("ele") or values.get("AltitudeMeters") or values.get("altitude") or ""))
    heart_rate = _parse_integer(str(values.get("hr") or values.get("HeartRateBpm") or values.get("Value") or values.get("heart_rate") or ""))
    cadence = _parse_decimal(str(values.get("cad") or values.get("Cadence") or values.get("RunCadence") or ""))
    return ParsedSample(
        sample_index=0,
        latitude=lat,
        longitude=lon,
        recorded_at=timestamp.astimezone(timezone.utc) if timestamp else None,
        elevation_m=elevation,
        heart_rate=heart_rate,
        cadence=cadence,
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _safe_error(error: Exception) -> str:
    message = str(error).replace("\r", " ").replace("\n", " ")
    return message[:500] or error.__class__.__name__