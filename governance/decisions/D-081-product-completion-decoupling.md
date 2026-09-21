# D-081 — Product completion is decoupled from longitudinal evidence accumulation

status: active
date: 2026-09-21

## Decision

HT-CN product development and longitudinal evidence accumulation are separate tracks after the first real M7 evidence chain is accepted.

- M9 is the development mainline for automation, product integration, reliability, packaging and Stable Product Release.
- M7 continues as a background prospective-evidence track.
- M8 activates when evidence is sufficient for calibration.
- ISSUE-0066 gates statistical/win-rate/alpha/profitability/calibration claims only. It does not gate M9 product development or Stable Product Release.
- A stable product may ship while ISSUE-0066 remains open, provided statistical features clearly report insufficient evidence and no prohibited claim is emitted.
- Daily manual Private-M1/BAT/ZIP work on the user's computer is not project infrastructure. It must be replaced by automated services; user-computer access is exceptional and necessity-gated.

## Why

The first real M7 prospective capture and subsequent M7.5/M7.6 control-plane hardening proved the evidence architecture works. Continuing to use the user's computer every closed session would confuse validation with product operation and could make product completion depend on months or years of natural evidence accumulation.

The project objective is a mature automated A-share harmonic decision-support application, not an indefinitely supervised testing loop.

## Stable Product boundary

Stable Product completion depends on automated data, automated harmonic analysis, end-to-end workbench, background evidence service, reliability/recovery, packaging and zero-CLI normal operation. It does not require ISSUE-0066 to close or a predetermined number of evidence days.

## User-computer necessity test

Before asking for the user's computer, the Agent must document:

1. why hosted CI / repository fixture / agent-controlled runtime cannot substitute;
2. the single bounded local action needed;
3. the maximum number of executions;
4. the unique evidence that only that local action can produce.

Ordinary regression, daily evidence accumulation, same-day revalidation, QFQ/provider tests, browser tests and Project OS/freeze gates never satisfy this necessity test.

## Supersedes interpretation

D-081 does not supersede M7 evidence integrity decisions. It supersedes only the implicit sequential interpretation that M7 and M8 must finish before M9 productization can proceed.
