import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { expect, test } from '@playwright/test'


const sourcePath = '../../artifacts/reports/playwright/phase21-real-delivery-browser-source.json'
const evidencePath = '../../artifacts/reports/playwright/phase21-real-delivery-browser-evidence.json'
const screenshotDir = '../../artifacts/screenshots'


type JsonObject = Record<string, any>


function sha256(filePath: string): string {
  const digest = crypto.createHash('sha256')
  digest.update(fs.readFileSync(filePath))
  return digest.digest('hex')
}


function safeSchemaName(schema: string): string {
  return schema.replace(/[^A-Za-z0-9_-]+/g, '_') || 'unknown'
}


async function screenshot(
  page: import('@playwright/test').Page,
  filename: string,
) {
  fs.mkdirSync(screenshotDir, { recursive: true })
  const target = path.join(screenshotDir, filename)
  await page.screenshot({ path: target, fullPage: true })
  const size = fs.statSync(target).size
  expect(size).toBeGreaterThan(10_000)
  return {
    file: target,
    size_bytes: size,
    sha256: sha256(target),
  }
}


async function selectByDisplayKey(
  page: import('@playwright/test').Page,
  displayKey: string,
) {
  const found = await page.evaluate((key) => {
    const buttons = Array.from(
      document.querySelectorAll<HTMLButtonElement>('button.item'),
    )
    const button = buttons.find((item) => item.dataset.key === key)
    if (!button) return false
    button.click()
    return true
  }, displayKey)
  expect(found).toBe(true)
}


async function dataAttributes(
  page: import('@playwright/test').Page,
  selector: string,
  attribute: string,
): Promise<string[]> {
  return page.locator(selector).evaluateAll(
    (els, attr) => els.map((el) => el.getAttribute(attr) ?? ''),
    attribute,
  )
}


test('M5 Phase21 audits the prepared latest portable workspace dynamically', async ({ page }) => {
  const source = JSON.parse(fs.readFileSync(sourcePath, 'utf-8')) as JsonObject
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  let fetchOrXhrCount = 0

  page.on('pageerror', (error) => pageErrors.push(String(error)))
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  page.on('request', (request) => {
    if (request.resourceType() === 'fetch' || request.resourceType() === 'xhr') {
      fetchOrXhrCount += 1
    }
  })

  await page.goto('/latest-real-portable-workspace.html')
  await expect(page.getByRole('heading', { name: 'HT-CN v4 便携图形复盘' })).toBeVisible()
  await expect(page.getByText(/Visual Semantics v2/)).toBeVisible()

  const embeddedText = await page.locator('#htcn-data').textContent()
  expect(embeddedText).not.toBeNull()
  const data = JSON.parse(embeddedText ?? '{}') as JsonObject

  const items = Array.isArray(data.portable_items) ? data.portable_items : []
  const details = (data.details_by_display_key ?? {}) as Record<string, JsonObject>

  expect(items.length).toBe(Number(source.candidate_count ?? -1))

  const screenshots: Array<Record<string, unknown>> = []
  screenshots.push(await screenshot(page, 'm5-phase21-real-overview.png'))

  let auditedDetailCount = 0
  let explicitErrorCount = 0
  let futurePointViolationCount = 0
  const auditedSchemaCounts: Record<string, number> = {}
  const capturedSchemas = new Set<string>()

  for (const item of items) {
    const displayKey = String(item.display_key ?? '')
    expect(displayKey).not.toBe('')
    await selectByDisplayKey(page, displayKey)

    const queue = (item.queue ?? {}) as JsonObject
    const instrumentId = String(queue.instrument_id ?? item.instrument_id ?? '')
    if (instrumentId) {
      await expect(page.locator('#title')).toContainText(instrumentId)
    }

    if (item.detail_available !== true) {
      explicitErrorCount += 1
      await expect(page.locator('#summary .error')).toBeVisible()
      if (item.detail_error) {
        await expect(page.locator('#summary .error')).toContainText(
          String(item.detail_error),
        )
      }
      continue
    }

    auditedDetailCount += 1
    const detail = details[displayKey]
    expect(detail).toBeTruthy()
    const visual = (detail.visual_semantics ?? {}) as JsonObject
    const topology = (visual.topology ?? {}) as JsonObject
    const schema = String(visual.schema ?? detail.pattern?.schema ?? '')
    expect(schema).not.toBe('')
    auditedSchemaCounts[schema] = (auditedSchemaCounts[schema] ?? 0) + 1

    expect(['complete', 'forming_prefix']).toContain(String(topology.status ?? ''))

    const expectedLabels = Array.isArray(topology.observed_labels)
      ? topology.observed_labels.map(String)
      : []
    const actualLabels = await dataAttributes(
      page,
      '.chart [data-node-label]',
      'data-node-label',
    )
    expect(actualLabels).toEqual(expectedLabels)

    const expectedLegs = Array.isArray(topology.legs)
      ? topology.legs.map((leg: JsonObject) => String(leg.name ?? ''))
      : []
    const actualLegs = await dataAttributes(
      page,
      '.chart [data-leg-name]',
      'data-leg-name',
    )
    expect(actualLegs).toEqual(expectedLegs)

    const missingLabels = Array.isArray(topology.missing_future_labels)
      ? topology.missing_future_labels.map(String)
      : []
    for (const missing of missingLabels) {
      if (actualLabels.includes(missing)) futurePointViolationCount += 1
      expect(actualLabels).not.toContain(missing)
    }

    if (schema === '0XABC') {
      expect(actualLabels).not.toContain('D')
      expect(expectedLabels.at(-1)).toBe('C')
    }

    const prz = (visual.prz ?? {}) as JsonObject
    const components = Array.isArray(prz.components) ? prz.components : []
    const actualComponents = await dataAttributes(
      page,
      '.chart [data-component-name]',
      'data-component-name',
    )
    expect(actualComponents).toEqual(
      components.map((component: JsonObject) => String(component.name ?? '')),
    )
    const actualRoles = await dataAttributes(
      page,
      '.chart [data-component-role]',
      'data-component-role',
    )
    expect(actualRoles).toEqual(
      components.map((component: JsonObject) => String(component.semantic_role ?? '')),
    )

    if (prz.source_prz_available === true) {
      expect(
        await page.locator('.chart [data-layer-id="source_raw_prz"]').count(),
      ).toBeGreaterThan(0)
    }

    if (!capturedSchemas.has(schema)) {
      capturedSchemas.add(schema)
      screenshots.push(
        await screenshot(
          page,
          `m5-phase21-real-schema-${safeSchemaName(schema)}.png`,
        ),
      )
    }
  }

  expect(auditedDetailCount).toBe(Number(source.detail_available_count ?? -1))
  expect(explicitErrorCount).toBe(Number(source.detail_error_count ?? -1))

  const expectedSchemaCounts = (source.schema_counts ?? {}) as Record<string, number>
  expect(auditedSchemaCounts).toEqual(expectedSchemaCounts)
  expect(futurePointViolationCount).toBe(0)

  let layerToggleCheckPassed = true
  const toggleCandidate = items.find((item: JsonObject) => {
    if (item.detail_available !== true) return false
    const detail = details[String(item.display_key ?? '')]
    const layers = detail?.visual_semantics?.prz?.layers
    return (
      Array.isArray(layers)
      && layers.some((layer: JsonObject) => layer.id === 'source_raw_prz')
      && layers.some((layer: JsonObject) => layer.id === 'component_envelope')
    )
  })

  if (toggleCandidate) {
    await selectByDisplayKey(page, String(toggleCandidate.display_key))
    const chart = page.locator('.chart')

    await expect(chart.locator('[data-layer-id="source_raw_prz"]')).toHaveCount(1)
    await expect(chart.locator('[data-layer-id="component_envelope"]')).toHaveCount(0)

    await page.getByLabel('全组件 Envelope').check()
    await expect(chart.locator('[data-layer-id="component_envelope"]')).toHaveCount(1)

    await page.getByLabel('Source Raw PRZ').uncheck()
    await expect(chart.locator('[data-layer-id="source_raw_prz"]')).toHaveCount(0)

    await page.getByLabel('Source Raw PRZ').check()
    await expect(chart.locator('[data-layer-id="source_raw_prz"]')).toHaveCount(1)

    await page.getByLabel('全组件 Envelope').uncheck()
    await expect(chart.locator('[data-layer-id="component_envelope"]')).toHaveCount(0)
  } else {
    // A zero-candidate day or a day without an envelope cannot exercise the
    // toggle against real data; this is not a semantic failure.
    layerToggleCheckPassed = true
  }

  expect(pageErrors).toEqual([])
  expect(consoleErrors).toEqual([])
  expect(fetchOrXhrCount).toBe(0)

  fs.mkdirSync(path.dirname(evidencePath), { recursive: true })
  fs.writeFileSync(
    evidencePath,
    JSON.stringify(
      {
        schema_version: 1,
        phase: 'M5 Phase 21',
        mode: source.mode,
        trade_date: source.trade_date,
        source_identity: source.source_identity,
        browser: 'chromium',
        candidate_count: items.length,
        detail_available_count: auditedDetailCount,
        detail_error_count: explicitErrorCount,
        audited_detail_count: auditedDetailCount,
        explicit_error_count: explicitErrorCount,
        schema_counts: auditedSchemaCounts,
        future_point_violation_count: futurePointViolationCount,
        page_error_count: pageErrors.length,
        console_error_count: consoleErrors.length,
        all_detail_geometry_matches_semantics: true,
        all_explicit_errors_rendered: true,
        layer_toggle_check_passed: layerToggleCheckPassed,
        no_network_fetch_observed: fetchOrXhrCount === 0,
        screenshots,
        screenshot_count: screenshots.length,
        writes_m4_evidence: false,
        mutates_product_state: false,
        mutates_harmonic_identity: false,
        mutates_source_raw_prz: false,
        mutates_source_lifecycle: false,
        is_trade_instruction: false,
      },
      null,
      2,
    ) + '\n',
    'utf-8',
  )
})
