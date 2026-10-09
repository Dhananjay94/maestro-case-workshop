import type { UiPath, PaginationCursor } from '@uipath/uipath-typescript/core'
import { Entities, QueryFilterOperator } from '@uipath/uipath-typescript/entities'
import { Buckets } from '@uipath/uipath-typescript/buckets'

/** Names only: IDs and folders are discovered at runtime, never hardcoded. */
export const CLAIM_ENTITY = 'MotorInsuranceClaim'
export const BUCKET_NAME = 'MotorInsuranceClaims-Documents'
const NO_FOLDER = '00000000-0000-0000-0000-000000000000'

export const DOCUMENT_SLOTS = [
  { key: 'intimation', label: 'Claim Intimation', required: true },
  { key: 'policy', label: 'Policy Schedule', required: true },
  { key: 'fir', label: 'FIR / Police Accident Report', required: true },
  { key: 'licence', label: 'Driving Licence', required: true },
  { key: 'rc', label: 'Vehicle Registration Certificate', required: true },
  { key: 'evidence', label: 'Accident Evidence', required: true },
  { key: 'estimate', label: 'Repair Estimate (optional now, needed before assessment)', required: false },
] as const

export type SlotKey = (typeof DOCUMENT_SLOTS)[number]['key']

export interface Workspace {
  entityId: string
  folderKey: string
  bucketId: number
  /** Human-readable description so a person can tell two same-named workspaces apart. */
  label: string
}

export interface ClaimForm {
  customerName: string
  policyNumber: string
  vehicleRegistration: string
  vehicleModel: string
  incidentDate: string
  claimAmount: string
  incidentDescription: string
}

/**
 * Finds every folder that has BOTH the claim entity and the bucket. Normally there is one;
 * if several exist (for example an older copy in another folder) the caller must let the user choose.
 */
export async function findWorkspaces(sdk: UiPath): Promise<Workspace[]> {
  const entities = new Entities(sdk)
  const all = await entities.getAll({ includeFolderEntities: true })
  const claims = all.filter((e) => e.name === CLAIM_ENTITY && e.folderId && e.folderId !== NO_FOLDER)
  const buckets = new Buckets(sdk)
  const found: Workspace[] = []
  for (const c of claims) {
    const folderKey = c.folderId as string
    try {
      const bucket = await buckets.getByName(BUCKET_NAME, { folderKey })
      found.push({
        entityId: c.id,
        folderKey,
        bucketId: bucket.id,
        label: `folder ${folderKey.slice(0, 8)}..., entity ${c.id.slice(0, 8)}..., ${c.recordCount ?? 0} claims`,
      })
    } catch {
      // This folder has the entity but no matching bucket: not usable for intake.
    }
  }
  if (found.length === 0) {
    throw new Error(
      `Could not find a folder that contains both the entity "${CLAIM_ENTITY}" and the bucket "${BUCKET_NAME}".`,
    )
  }
  return found
}

/** Unique storage name so uploads never overwrite each other (the bucket has no folders by ClaimId). */
function uniquePath(file: File): string {
  const safe = file.name.replace(/[^A-Za-z0-9._-]/g, '_')
  const rand = Math.random().toString(36).slice(2, 8)
  return `${Date.now()}-${rand}-${safe}`
}

async function uploadOne(sdk: UiPath, ws: Workspace, file: File): Promise<string> {
  const buckets = new Buckets(sdk)
  const path = uniquePath(file)
  const res = await buckets.uploadFile(ws.bucketId, path, file, { folderKey: ws.folderKey })
  if (!res.success) throw new Error(`Upload failed for ${file.name} (HTTP ${res.statusCode})`)
  return path
}

async function findClaim(sdk: UiPath, ws: Workspace, claimId: string) {
  const entities = new Entities(sdk)
  const res = await entities.queryRecordsById(ws.entityId, {
    filterGroup: {
      queryFilters: [{ fieldName: 'ClaimId', operator: QueryFilterOperator.Equals, value: claimId }],
    },
    folderKey: ws.folderKey,
  })
  return res.items[0]
}

const CLAIM_ID_PREFIX = 'CLM-'
const CLAIM_ID_START = 1001

/** The system assigns the claim number: next number after the highest existing CLM-nnnn. */
async function nextClaimId(sdk: UiPath, ws: Workspace): Promise<string> {
  const entities = new Entities(sdk)
  let max = CLAIM_ID_START - 1
  let cursor: PaginationCursor | undefined
  for (;;) {
    const page = await entities.queryRecordsById(ws.entityId, {
      selectedFields: ['ClaimId'],
      folderKey: ws.folderKey,
      pageSize: 200,
      ...(cursor ? { cursor } : {}),
    })
    for (const r of page.items) {
      const m = /^CLM-(\d+)$/.exec(String(r.ClaimId ?? ''))
      if (m) max = Math.max(max, Number(m[1]))
    }
    if (!('hasNextPage' in page) || !page.hasNextPage || !page.nextCursor) break
    cursor = page.nextCursor
  }
  return `${CLAIM_ID_PREFIX}${max + 1}`
}

export async function createClaim(
  sdk: UiPath,
  ws: Workspace,
  form: ClaimForm,
  files: Partial<Record<SlotKey, File>>,
  onProgress: (message: string) => void,
): Promise<string> {
  const refs: string[] = []
  for (const slot of DOCUMENT_SLOTS) {
    const file = files[slot.key]
    if (!file) continue
    onProgress(`Uploading ${slot.label}...`)
    refs.push(await uploadOne(sdk, ws, file))
  }
  onProgress('Registering claim...')
  const entities = new Entities(sdk)
  // ClaimId is unique in Data Fabric, so if two claims race for the same number the loser retries.
  let lastError: unknown
  for (let attempt = 0; attempt < 3; attempt++) {
    const claimId = await nextClaimId(sdk, ws)
    try {
      await entities.insertRecordById(
        ws.entityId,
        {
          ClaimId: claimId,
          CustomerName: form.customerName,
          PolicyNumber: form.policyNumber,
          VehicleRegistration: form.vehicleRegistration,
          VehicleModel: form.vehicleModel,
          IncidentDate: form.incidentDate,
          IncidentDescription: form.incidentDescription,
          ClaimAmount: Number(form.claimAmount),
          DocumentReferences: refs.join(','),
          DocumentIngestionStatus: 'Uploaded',
          ClaimStatus: 'Registered',
          CustomerInformationStatus: 'None',
        },
        { folderKey: ws.folderKey },
      )
      return claimId
    } catch (err) {
      lastError = err
    }
  }
  throw lastError instanceof Error ? lastError : new Error('Could not register the claim.')
}

/** The "customer reply": add a supplemental document to an existing claim and flag it as received. */
export async function addSupplementalDocument(
  sdk: UiPath,
  ws: Workspace,
  claimId: string,
  file: File,
  onProgress: (message: string) => void,
): Promise<void> {
  onProgress('Finding claim...')
  const claim = await findClaim(sdk, ws, claimId)
  if (!claim) throw new Error(`Claim ${claimId} was not found.`)
  onProgress('Uploading document...')
  const path = await uploadOne(sdk, ws, file)
  const existing = String(claim.DocumentReferences ?? '').trim()
  onProgress('Updating claim...')
  const entities = new Entities(sdk)
  await entities.updateRecordById(
    ws.entityId,
    claim.Id,
    {
      DocumentReferences: existing ? `${existing},${path}` : path,
      ReceivedDocumentReference: path,
      CustomerResponseDate: new Date().toISOString().slice(0, 10),
      CustomerInformationStatus: 'Received',
    },
    { folderKey: ws.folderKey },
  )
}
