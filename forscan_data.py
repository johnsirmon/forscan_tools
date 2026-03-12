from __future__ import annotations

from forscan_models import DtcInfo, SafetyLevel, SourceEvidence, TopicExplanation

GENERIC_DTC_SYSTEM = {
    "P": "Powertrain",
    "B": "Body",
    "C": "Chassis",
    "U": "Network",
}


KNOWN_DTCS: dict[str, DtcInfo] = {
    "P0420": DtcInfo(
        code="P0420",
        title="Catalyst System Efficiency Below Threshold (Bank 1)",
        system="Powertrain",
        severity=SafetyLevel.MEDIUM,
        likely_causes=(
            "Aging catalytic converter",
            "Exhaust leak upstream of catalyst",
            "O2 sensor drift or wiring issue",
        ),
        recommended_steps=(
            "Confirm no exhaust leaks before replacing parts",
            "Capture live O2 sensor data before and after catalyst",
            "Address fuel trim or misfire issues first",
        ),
    ),
    "P0171": DtcInfo(
        code="P0171",
        title="System Too Lean (Bank 1)",
        system="Powertrain",
        severity=SafetyLevel.HIGH,
        likely_causes=(
            "Vacuum leak",
            "Low fuel pressure",
            "MAF sensor contamination",
        ),
        recommended_steps=(
            "Inspect intake and vacuum hoses",
            "Check fuel pressure against Ford spec",
            "Review STFT/LTFT under idle and load",
        ),
    ),
    "U0121": DtcInfo(
        code="U0121",
        title="Lost Communication With Anti-Lock Brake System Module",
        system="Network",
        severity=SafetyLevel.HIGH,
        likely_causes=(
            "ABS module power/ground issue",
            "CAN bus wiring fault",
            "Intermittent module failure",
        ),
        recommended_steps=(
            "Run network test with ignition state noted",
            "Verify ABS module power and grounds under load",
            "Check CAN high/low resistance and continuity",
        ),
    ),
    "B10D7": DtcInfo(
        code="B10D7",
        title="Key Transponder Signal Fault",
        system="Body",
        severity=SafetyLevel.MEDIUM,
        likely_causes=(
            "Weak key battery",
            "Antenna ring issue",
            "PATS programming mismatch",
        ),
        recommended_steps=(
            "Test with a second known-good key",
            "Inspect PATS antenna connector",
            "Check recent key programming history",
        ),
    ),
}


SAFETY_CRITICAL_MODULES = {
    "pcm",
    "tcm",
    "abs",
    "rcm",
    "eps",
    "srs",
}


OFFICIAL_SOURCES: tuple[SourceEvidence, ...] = (
    SourceEvidence(
        title="FORScan Home",
        url="https://forscan.org/home.html",
        category="official",
        last_checked="2026-02-21",
        notes="Core feature, adapter, and platform support statements.",
    ),
    SourceEvidence(
        title="FORScan Products and Release Notes",
        url="https://forscan.org/download.html",
        category="official",
        last_checked="2026-02-21",
        notes="Current versions and recent release history.",
    ),
    SourceEvidence(
        title="FORScan Documentation Hub",
        url="https://forscan.org/documentation.html",
        category="official",
        last_checked="2026-02-21",
        notes="Docs entrypoint; notes that v2 docs are in progress.",
    ),
    SourceEvidence(
        title="FORScan HowTo",
        url="https://forscan.org/howto.html",
        category="official",
        last_checked="2026-02-21",
        notes="Legacy links and redirects to forum-based procedures.",
    ),
    SourceEvidence(
        title="FORScan Supported Modules",
        url="https://forscan.org/modules_list.html",
        category="official",
        last_checked="2026-02-21",
        notes="Large module abbreviation reference useful for tooling.",
    ),
    SourceEvidence(
        title="FORScan Forum Configuration Guidance",
        url="https://forscan.org/forum/viewtopic.php?f=16&t=17208",
        category="official-community",
        last_checked="2026-02-21",
        notes="Pinned practical guidance for module configuration workflows.",
    ),
)


TOPIC_EXPLANATIONS: dict[str, TopicExplanation] = {
    "asbuilt": TopicExplanation(
        topic="As-Built",
        summary=(
            "As-Built is factory configuration data for modules. Once you edit values,"
            " it is no longer factory As-Built."
        ),
        why_it_matters=(
            "Used to restore modules to known factory-state values.",
            "Critical when replacing modules or recovering from bad edits.",
            "Many forum spreadsheets and comparisons are based on As-Built lines.",
        ),
        common_mistakes=(
            "Treating As-Built as universal between different trims/years/modules.",
            "Editing raw hex without a backup and rollback plan.",
            "Assuming every visible block is safe user configuration data.",
        ),
        best_practices=(
            "Export backup before any write and keep timestamped copies.",
            "Prefer human-readable Module Configuration over raw As-Built edits.",
            "Write one change at a time and rescan DTCs after each step.",
        ),
    ),
    "abt": TopicExplanation(
        topic="ABT Files",
        summary=(
            "ABT is FORScan's module configuration backup/export format."
            " Newer FORScan versions use an updated encoding for large block/line values."
        ),
        why_it_matters=(
            "ABT is your practical restore point before risky changes.",
            "Compatibility differs between old and new FORScan versions.",
            "Useful for offline comparison and change audits.",
        ),
        common_mistakes=(
            "Opening old ABT tools against new-encoding ABT content without conversion.",
            "Confusing Motorcraft .AB files with FORScan .ABT backups.",
            "Relying on one backup copy only.",
        ),
        best_practices=(
            "Keep both module-level ABT backups and a whole-session export.",
            "Version your ABT backups by VIN/module/date.",
            "Verify your restore path before making complex edits.",
        ),
    ),
    "ecc": TopicExplanation(
        topic="Economized Central Configuration (ECC)",
        summary=(
            "ECC stores shared vehicle data used across multiple modules"
            " (for example VIN/tire size/axle ratio in newer platforms)."
        ),
        why_it_matters=(
            "ECC changes can affect many modules at once.",
            "Post-change relearn/initialization may be required.",
            "Missed synchronization can trigger U2100/U2101-style faults.",
        ),
        common_mistakes=(
            "Updating ECC values but skipping module initialization/relearn.",
            "Assuming only the edited module is impacted.",
            "Applying values copied from a different platform without validation.",
        ),
        best_practices=(
            "Use official procedure notes for your exact platform and year.",
            "Run relearn synchronization after ECC writes if applicable.",
            "Baseline scan before change and compare DTC deltas after.",
        ),
    ),
    "vid": TopicExplanation(
        topic="PCM VID",
        summary=(
            "VID (Vehicle Identification block) contains crucial PCM-related configuration"
            " and may require checksum-aware/special handling."
        ),
        why_it_matters=(
            "Incorrect VID edits can affect drivability and calibration behavior.",
            "Some older platforms may need special programming/update flow.",
            "Adapter capabilities and stable power become even more critical.",
        ),
        common_mistakes=(
            "Treating VID like ordinary As-Built text edits.",
            "Using low-quality adapters for firmware-related operations.",
            "Attempting VID work without a fully verified fallback plan.",
        ),
        best_practices=(
            "Use dedicated FORScan VID-related procedures where provided.",
            "Confirm adapter requirements before attempting changes.",
            "Do not proceed without power stabilization and complete backups.",
        ),
    ),
    "trid": TopicExplanation(
        topic="TCM TRID",
        summary=("TRID is transmission characterization data and is safety/drivability sensitive."),
        why_it_matters=(
            "Checksum/protection and format constraints can apply.",
            "Bad changes can cause shifting or transmission behavior issues.",
            "Dedicated procedures are safer than raw block edits.",
        ),
        common_mistakes=(
            "Editing TRID through generic As-Built workflows.",
            "Applying copied values without matching hardware/firmware context.",
            "Skipping post-operation validation drive cycles.",
        ),
        best_practices=(
            "Use FORScan Transmission Characterization Update when applicable.",
            "Avoid experimentation in this area unless you have a clear recovery path.",
            "Validate with DTC checks and controlled test drive afterward.",
        ),
    ),
}
