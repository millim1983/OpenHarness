# RAG Metadata Schema

OpenHarness stores document metadata in `documents.metadata_json` so existing
rows keep working while the schema evolves. New rows should use a layered
payload: common top-level fields for every document, plus one optional nested
object for the detected document type.

## Common Fields

- `metadata_schema_version`: integer schema version, currently `1`.
- `document_type`: one of `announcement`, `regulation`, `technical`, `company_team`, or `unknown`.
- `title`: best available document title.
- `source_file`: uploaded file name.
- `content_hash`: SHA-1 hash of extracted text, supplied by the indexer.
- `uploaded_at`: UTC timestamp when metadata was produced.
- `embedding_profile`: profile used to create chunk embeddings.
- `chunk_count`: number of stored RAG chunks.
- `tags`: short retrieval/filtering labels.
- `language`: detected language hint such as `ko`, `en`, `mixed`, or `unknown`.
- `source_kind`: origin such as `web_mvp_upload`.
- `chat_profile`: profile used for document analysis, when applicable.
- `instruction`: user instruction supplied at upload time, when applicable.
- `has_team_context`: whether team context was supplied at upload time.

Dashboard-oriented summary fields may also appear at the top level when known:
`ministry`, `agency`, `business_type`, `rd_or_non_rd`, and
`submission_deadline`.

## Type-Specific Fields

Announcement metadata lives under `announcement`:

- `ministry`
- `agency`
- `business_type`
- `rd_or_non_rd`
- `program_name`
- `submission_channel`
- `submission_deadline`
- `contacts`
- `related_regulations`
- `eligibility_roles`

Regulation metadata lives under `regulation`:

- `regulation_owner`
- `applies_to_business_type`
- `effective_date`
- `article_scope`
- `related_ministry`
- `related_agency`

Technical document metadata lives under `technical`:

- `technology_domain`
- `product_or_system`
- `version`
- `spec_scope`
- `related_project_or_program`

Company/team document metadata lives under `company_team`:

- `department`
- `owner`
- `responsibility_area`
- `related_task`

## Backfill Policy

When a new metadata field is added, prefer backfilling from stored chunk text
only if the needed evidence is likely to be present in chunks. Fields that
depend on whole-document layout, omitted appendices, or source-file metadata
should be treated as requiring full reprocessing.

The current RAG store persists chunk text but not full extracted text or the
original upload. Reliable future backfills should therefore add one of these
before relying on complex metadata migrations:

- persist full extracted text in a bounded document text table; or
- persist an original-file reference when storage policy allows it; or
- persist both, with full text used for extraction and the original file used
  for parser/schema changes.

Existing rows without these fields remain valid. Readers must default missing
fields to empty strings, empty arrays, `false`, or `unknown` as appropriate.
